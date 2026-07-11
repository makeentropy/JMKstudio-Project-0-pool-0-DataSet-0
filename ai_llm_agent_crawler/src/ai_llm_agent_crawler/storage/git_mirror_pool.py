"""
Git 镜像池管理模块 (pool/img 方案)

管理一组开源仓库的本地镜像, 支持:
- clone / pull (拉取/更新开源仓库, 镜像方式 --mirror)
- 版本控制 (记录每个镜像的 commit/分支/tag 快照)
- push 到 github.com (将本地镜像池作为分发/备份推送到远程)
- 池索引与状态查询

镜像采用 git 的 bare mirror 仓库形式, 保留所有引用 (refs),
便于离线分发与版本回溯。
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class MirrorStatus(str, Enum):
    """镜像状态。"""

    INIT = "init"  # 初始化中
    READY = "ready"  # 就绪
    CLONING = "cloning"  # 克隆中
    PULLING = "pulling"  # 拉取中
    PUSHING = "pushing"  # 推送中
    FAILED = "failed"  # 失败
    STALE = "stale"  # 过期


@dataclass
class MirrorEntry:
    """单个镜像条目。"""

    name: str  # 镜像名称 (池内唯一)
    source_url: str  # 上游开源仓库 URL
    mirror_path: str  # 本地镜像路径 (bare mirror)
    github_remote: Optional[str] = None  # github.com 推送目标 URL
    status: str = MirrorStatus.INIT.value
    last_commit: Optional[str] = None  # 最近同步的 commit
    last_sync_at: Optional[str] = None  # 最近同步时间
    branches: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sync_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MirrorEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class GitMirrorPool:
    """
    Git 镜像池管理器

    Args:
        pool_root: 镜像池根目录 (存放所有 bare mirror 仓库)
        index_path: 池索引文件路径
        default_github_remote: 默认 github.com 推送目标前缀
            (如 https://github.com/myorg/ 会拼接为 <prefix><name>.git)
    """

    def __init__(
        self,
        pool_root: Optional[Path] = None,
        index_path: Optional[Path] = None,
        default_github_remote: Optional[str] = None,
    ) -> None:
        self.pool_root = pool_root or Path("git_mirror_pool")
        self.pool_root.mkdir(parents=True, exist_ok=True)
        self.index_path = index_path or (self.pool_root / "pool_index.json")
        self.default_github_remote = default_github_remote
        self.entries: Dict[str, MirrorEntry] = {}
        self._load_index()

    # ---------- 索引持久化 ----------

    def _load_index(self) -> None:
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                for name, entry_data in data.get("entries", {}).items():
                    self.entries[name] = MirrorEntry.from_dict(entry_data)
                logger.info(f"加载镜像池索引: {len(self.entries)} 个镜像")
            except Exception as e:
                logger.error(f"加载镜像池索引失败: {e}")

    def _save_index(self) -> None:
        data = {
            "pool_root": str(self.pool_root),
            "updated_at": datetime.now().isoformat(),
            "entries": {n: e.to_dict() for n, e in self.entries.items()},
        }
        self.index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- git 命令封装 ----------

    def _run_git(self, args: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """运行 git 命令, 返回结果。失败时抛出。"""
        cmd = ["git"] + args
        logger.debug(f"git run: {cmd} (cwd={cwd})")
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} 失败 (code={result.returncode}): {result.stderr.strip()}"
            )
        return result

    def _mirror_path_for(self, name: str) -> Path:
        return self.pool_root / f"{name}.git"

    # ---------- 公共 API ----------

    def add_mirror(
        self,
        name: str,
        source_url: str,
        github_remote: Optional[str] = None,
        description: str = "",
        clone_now: bool = False,
    ) -> MirrorEntry:
        """
        注册一个新镜像 (可选立即 clone)。

        Args:
            name: 镜像名称
            source_url: 上游开源仓库 URL
            github_remote: github.com 推送目标 (None 时使用 default_github_remote + name)
            description: 描述
            clone_now: 是否立即克隆
        """
        if name in self.entries:
            raise ValueError(f"镜像已存在: {name}")

        mirror_path = self._mirror_path_for(name)
        if github_remote is None and self.default_github_remote:
            github_remote = f"{self.default_github_remote.rstrip('/')}/{name}.git"

        entry = MirrorEntry(
            name=name,
            source_url=source_url,
            mirror_path=str(mirror_path),
            github_remote=github_remote,
            description=description,
            status=MirrorStatus.INIT.value,
        )
        self.entries[name] = entry
        self._save_index()

        if clone_now:
            self.clone(name)
        return entry

    def clone(self, name: str) -> MirrorEntry:
        """克隆镜像 (git clone --mirror)。"""
        entry = self._require(name)
        mirror_path = Path(entry.mirror_path)
        if mirror_path.exists():
            raise FileExistsError(f"镜像目录已存在: {mirror_path}, 请使用 pull 更新")
        entry.status = MirrorStatus.CLONING.value
        entry.last_error = None
        self._save_index()
        try:
            self._run_git(["clone", "--mirror", entry.source_url, str(mirror_path)])
            self._refresh_refs(entry)
            entry.status = MirrorStatus.READY.value
            entry.last_sync_at = datetime.now().isoformat()
            entry.sync_count += 1
            logger.info(f"克隆镜像成功: {name}")
        except Exception as e:
            entry.status = MirrorStatus.FAILED.value
            entry.last_error = str(e)
            logger.error(f"克隆镜像失败 {name}: {e}")
            raise
        finally:
            self._save_index()
        return entry

    def pull(self, name: str) -> MirrorEntry:
        """拉取最新 (git remote update / fetch --all)。"""
        entry = self._require(name)
        mirror_path = Path(entry.mirror_path)
        if not mirror_path.exists():
            logger.warning(f"镜像不存在, 改为 clone: {name}")
            return self.clone(name)
        entry.status = MirrorStatus.PULLING.value
        entry.last_error = None
        self._save_index()
        try:
            # mirror 仓库用 remote update 同步所有引用
            self._run_git(["remote", "update", "--prune"], cwd=mirror_path)
            self._refresh_refs(entry)
            entry.status = MirrorStatus.READY.value
            entry.last_sync_at = datetime.now().isoformat()
            entry.sync_count += 1
            logger.info(f"拉取镜像成功: {name} @ {entry.last_commit}")
        except Exception as e:
            entry.status = MirrorStatus.FAILED.value
            entry.last_error = str(e)
            logger.error(f"拉取镜像失败 {name}: {e}")
            raise
        finally:
            self._save_index()
        return entry

    def pull_all(self) -> Dict[str, bool]:
        """拉取所有镜像, 返回每个镜像的成功状态。"""
        results: Dict[str, bool] = {}
        for name in list(self.entries.keys()):
            try:
                self.pull(name)
                results[name] = True
            except Exception:
                results[name] = False
        return results

    def push_to_github(self, name: str, set_remote: bool = True) -> MirrorEntry:
        """
        将镜像推送到 github.com。

        Args:
            name: 镜像名称
            set_remote: 是否先设置 github remote (若未设置)
        """
        entry = self._require(name)
        if not entry.github_remote:
            raise ValueError(f"镜像 {name} 未配置 github_remote")
        mirror_path = Path(entry.mirror_path)
        if not mirror_path.exists():
            raise FileNotFoundError(f"镜像不存在: {mirror_path}, 请先 clone")
        entry.status = MirrorStatus.PUSHING.value
        entry.last_error = None
        self._save_index()
        try:
            if set_remote:
                # 确保 github remote 存在 (失败不致命)
                self._run_git(["remote", "remove", "github"], cwd=mirror_path)
            self._run_git(
                ["remote", "add", "github", entry.github_remote], cwd=mirror_path
            )
            # 推送所有引用 (mirror 推送)
            self._run_git(["push", "--mirror", "github"], cwd=mirror_path)
            entry.status = MirrorStatus.READY.value
            entry.last_sync_at = datetime.now().isoformat()
            logger.info(f"推送到 github 成功: {name} -> {entry.github_remote}")
        except Exception as e:
            entry.status = MirrorStatus.FAILED.value
            entry.last_error = str(e)
            logger.error(f"推送到 github 失败 {name}: {e}")
            raise
        finally:
            self._save_index()
        return entry

    def push_all_to_github(self) -> Dict[str, bool]:
        """推送所有镜像到 github。"""
        results: Dict[str, bool] = {}
        for name in list(self.entries.keys()):
            entry = self.entries[name]
            if not entry.github_remote:
                results[name] = False
                continue
            try:
                self.push_to_github(name)
                results[name] = True
            except Exception:
                results[name] = False
        return results

    def remove_mirror(self, name: str, delete_files: bool = True) -> bool:
        """移除镜像 (可选删除本地文件)。"""
        entry = self.entries.get(name)
        if entry is None:
            return False
        if delete_files:
            mirror_path = Path(entry.mirror_path)
            if mirror_path.exists():
                import shutil

                shutil.rmtree(mirror_path, ignore_errors=True)
        del self.entries[name]
        self._save_index()
        logger.info(f"移除镜像: {name}")
        return True

    def get_entry(self, name: str) -> Optional[MirrorEntry]:
        return self.entries.get(name)

    def list_entries(self) -> List[MirrorEntry]:
        return list(self.entries.values())

    def pool_status(self) -> Dict[str, Any]:
        """池整体状态。"""
        statuses: Dict[str, int] = {}
        for e in self.entries.values():
            statuses[e.status] = statuses.get(e.status, 0) + 1
        return {
            "pool_root": str(self.pool_root),
            "total_mirrors": len(self.entries),
            "by_status": statuses,
            "github_configured": self.default_github_remote is not None,
            "updated_at": datetime.now().isoformat(),
        }

    # ---------- 内部辅助 ----------

    def _require(self, name: str) -> MirrorEntry:
        entry = self.entries.get(name)
        if entry is None:
            raise KeyError(f"镜像不存在: {name}")
        return entry

    def _refresh_refs(self, entry: MirrorEntry) -> None:
        """刷新镜像的分支/tag/commit 信息。"""
        mirror_path = Path(entry.mirror_path)
        try:
            # 当前 HEAD commit
            head = self._run_git(["rev-parse", "HEAD"], cwd=mirror_path)
            entry.last_commit = head.stdout.strip() if head.returncode == 0 else None
        except Exception:
            entry.last_commit = None
        try:
            branches_res = self._run_git(["for-each-ref", "--format=%(refname:short)", "refs/heads"], cwd=mirror_path)
            entry.branches = [b.strip() for b in branches_res.stdout.splitlines() if b.strip()]
        except Exception:
            entry.branches = []
        try:
            tags_res = self._run_git(["for-each-ref", "--format=%(refname:short)", "refs/tags"], cwd=mirror_path)
            entry.tags = [t.strip() for t in tags_res.stdout.splitlines() if t.strip()]
        except Exception:
            entry.tags = []


# 便捷工厂
def create_git_mirror_pool(
    pool_root: str,
    default_github_remote: Optional[str] = None,
) -> GitMirrorPool:
    """创建 git 镜像池。"""
    return GitMirrorPool(
        pool_root=Path(pool_root),
        default_github_remote=default_github_remote,
    )


__all__ = [
    "MirrorStatus",
    "MirrorEntry",
    "GitMirrorPool",
    "create_git_mirror_pool",
]
