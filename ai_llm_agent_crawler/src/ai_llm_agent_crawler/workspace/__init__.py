"""
Workspace 快照管理模块

提供 Workspace 级别的统一快照与版本控制：
- WorkspaceSnapshotManager: 全量/增量快照、回滚、Tag/Branch
- RetentionPolicy: GFS 风格快照保留策略
- RefsIndex: Tag/Branch 引用索引
- WorkspaceDiff: Workspace diff 计算工具
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger
from ai_llm_agent_crawler.versioning.snapshot_manager import (
    SnapshotManager,
    SnapshotMetadata,
    SnapshotType,
    CompressionType,
)

logger = get_logger(__name__)


class WSSnapshotStatus(str, Enum):
    PENDING = "pending"
    PROTECT = "protect"  # 回滚保护快照
    ACTIVE = "active"
    ARCHIVED = "archived"


class RefType(str, Enum):
    TAG = "tag"
    BRANCH = "branch"


class RefEntry(BaseModel):
    name: str
    ref_type: RefType
    snapshot_id: str
    workspace_id: str
    description: str = ""
    created_by: str = "system"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True


class RefsIndex(BaseModel):
    """Tag/Branch 引用索引（类似 git refs）"""
    workspace_id: str
    tags: Dict[str, RefEntry] = Field(default_factory=dict)
    branches: Dict[str, RefEntry] = Field(default_factory=dict)
    head_branch: Optional[str] = None  # 当前检出分支

    class Config:
        arbitrary_types_allowed = True

    # ---------- Tag ----------
    def create_tag(self, name: str, snapshot_id: str, description: str = "",
                   created_by: str = "system") -> RefEntry:
        entry = RefEntry(
            name=name, ref_type=RefType.TAG,
            snapshot_id=snapshot_id, workspace_id=self.workspace_id,
            description=description, created_by=created_by,
        )
        self.tags[name] = entry
        return entry

    def delete_tag(self, name: str) -> bool:
        return self.tags.pop(name, None) is not None

    def get_tag(self, name: str) -> Optional[RefEntry]:
        return self.tags.get(name)

    # ---------- Branch ----------
    def create_branch(self, name: str, snapshot_id: str, description: str = "",
                      created_by: str = "system") -> RefEntry:
        entry = RefEntry(
            name=name, ref_type=RefType.BRANCH,
            snapshot_id=snapshot_id, workspace_id=self.workspace_id,
            description=description, created_by=created_by,
        )
        self.branches[name] = entry
        if self.head_branch is None:
            self.head_branch = name
        return entry

    def update_branch(self, name: str, snapshot_id: str) -> Optional[RefEntry]:
        entry = self.branches.get(name)
        if entry:
            entry.snapshot_id = snapshot_id
            entry.updated_at = datetime.now()
        return entry

    def delete_branch(self, name: str) -> bool:
        if self.head_branch == name:
            self.head_branch = None
        return self.branches.pop(name, None) is not None

    def get_branch(self, name: str) -> Optional[RefEntry]:
        return self.branches.get(name)

    def list_all(self) -> List[RefEntry]:
        return list(self.tags.values()) + list(self.branches.values())


class RetentionTier(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RetentionPolicy(BaseModel):
    """GFS 风格快照保留策略"""
    keep_hourly: int = 24     # 保留最近 24 小时的每小时快照
    keep_daily: int = 7       # 保留最近 7 天的每天快照
    keep_weekly: int = 4      # 保留最近 4 周的每周快照
    keep_monthly: int = 12    # 保留最近 12 月的每月快照
    keep_yearly: int = 3      # 保留最近 3 年的每年快照
    always_keep_full: bool = True  # 始终保留完整快照链
    always_keep_tagged: bool = True  # 始终保留带 tag 的快照

    def should_keep(self, snap: SnapshotMetadata, all_snaps: List[SnapshotMetadata],
                    tag_snapshot_ids: set) -> Tuple[bool, RetentionTier | None]:
        # 规则 0: 带 tag 的始终保留
        if self.always_keep_tagged and snap.snapshot_id in tag_snapshot_ids:
            return True, None
        # 规则 1: 完整快照链保护
        if self.always_keep_full and snap.snapshot_type == SnapshotType.FULL:
            return True, None
        # 规则 2: 时间分桶（GFS 风格）
        now = datetime.now()
        created = snap.created_at if isinstance(snap.created_at, datetime) else datetime.fromisoformat(str(snap.created_at))
        age = now - created

        # 按时间分桶优先级
        tiers = [
            (RetentionTier.HOURLY, self.keep_hourly, timedelta(hours=1), timedelta(hours=self.keep_hourly)),
            (RetentionTier.DAILY, self.keep_daily, timedelta(days=1), timedelta(days=self.keep_daily)),
            (RetentionTier.WEEKLY, self.keep_weekly, timedelta(weeks=1), timedelta(weeks=self.keep_weekly)),
            (RetentionTier.MONTHLY, self.keep_monthly, timedelta(days=30), timedelta(days=30 * self.keep_monthly)),
            (RetentionTier.YEARLY, self.keep_yearly, timedelta(days=365), timedelta(days=365 * self.keep_yearly)),
        ]

        for tier, keep_count, bucket_size, max_age in tiers:
            if age > max_age:
                continue
            # 同一时间桶内，只保留最新的
            bucket_start = self._bucket_start(created, bucket_size)
            same_bucket = [
                s for s in all_snaps
                if self._bucket_start(
                    s.created_at if isinstance(s.created_at, datetime) else datetime.fromisoformat(str(s.created_at)),
                    bucket_size,
                ) == bucket_start
            ]
            same_bucket.sort(key=lambda s: s.created_at if isinstance(s.created_at, datetime) else datetime.fromisoformat(str(s.created_at)), reverse=True)
            if same_bucket and same_bucket[0].snapshot_id == snap.snapshot_id:
                return True, tier

        return False, None

    @staticmethod
    def _bucket_start(dt: datetime, size: timedelta) -> datetime:
        ts = dt.timestamp()
        size_s = size.total_seconds()
        bucket_ts = (ts // size_s) * size_s
        return datetime.fromtimestamp(bucket_ts)

    def apply(self, all_snaps: List[SnapshotMetadata],
              tag_snapshot_ids: set) -> List[SnapshotMetadata]:
        """返回应该删除的快照列表"""
        to_delete = []
        for snap in all_snaps:
            keep, _ = self.should_keep(snap, all_snaps, tag_snapshot_ids)
            if not keep:
                to_delete.append(snap)
        return to_delete


class WorkspaceSnapshotManager:
    """Workspace 快照管理器（封装 SnapshotManager + Refs + Retention）"""

    def __init__(self, workspace_id: str, workspace_root: Path,
                 snapshots_root: Optional[Path] = None):
        self.workspace_id = workspace_id
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        self.snapshots_root = Path(snapshots_root or (self.workspace_root / ".ws_snapshots"))
        self.snapshots_root.mkdir(parents=True, exist_ok=True)

        self.inner = SnapshotManager(max_snapshots=10000)
        self.inner.storage.storage_path = self.snapshots_root

        self.refs = RefsIndex(workspace_id=workspace_id)
        self.retention = RetentionPolicy()
        self.audit_log: List[Dict[str, Any]] = []
        self._load_refs()
        self._load_audit()

    # ---------- 快照创建 ----------
    def create_full(self, tag: Optional[str] = None, description: str = "",
                    created_by: str = "system",
                    compression: CompressionType = CompressionType.NONE) -> SnapshotMetadata:
        meta = self.inner.create_full_snapshot(
            entity_id=self.workspace_id,
            source_path=self.workspace_root,
            name=tag or f"ws_full_{self.workspace_id}",
            description=description,
            compression_type=compression,
            created_by=created_by,
        )
        self._add_audit("create_full", snapshot_id=meta.snapshot_id, actor=created_by)
        if tag:
            self.tag(tag, meta.snapshot_id, created_by=created_by)
        return meta

    def create_incremental(self, tag: Optional[str] = None, description: str = "",
                           created_by: str = "system",
                           parent_snapshot_id: Optional[str] = None,
                           compression: CompressionType = CompressionType.NONE) -> SnapshotMetadata:
        meta = self.inner.create_incremental_snapshot(
            entity_id=self.workspace_id,
            source_path=self.workspace_root,
            parent_snapshot_id=parent_snapshot_id,
            name=tag or f"ws_incr_{self.workspace_id}",
            description=description,
            compression_type=compression,
            created_by=created_by,
        )
        self._add_audit("create_incremental", snapshot_id=meta.snapshot_id, actor=created_by)
        if tag:
            self.tag(tag, meta.snapshot_id, created_by=created_by)
        return meta

    # ---------- 回滚 ----------
    def restore(self, snapshot_id_or_tag: str, create_protect: bool = True,
                actor: str = "system") -> bool:
        # 支持 tag 解析
        target_snap_id = self._resolve_ref(snapshot_id_or_tag)
        if target_snap_id is None:
            logger.error(f"找不到快照或 tag: {snapshot_id_or_tag}")
            return False

        # 先创建保护快照
        protect_snap = None
        if create_protect:
            protect_snap = self.inner.create_full_snapshot(
                entity_id=self.workspace_id,
                source_path=self.workspace_root,
                name=f"protect_before_restore_{target_snap_id}",
                description=f"回滚 {target_snap_id} 前的保护快照",
                compression_type=CompressionType.NONE,
                created_by=actor,
            )
            logger.info(f"已创建保护快照: {protect_snap.snapshot_id}")

        # 清理当前 workspace 内容（保留 .ws_snapshots）
        for item in self.workspace_root.iterdir():
            if item.name == self.snapshots_root.name:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # 恢复
        ok = self.inner.restore_snapshot(
            entity_id=self.workspace_id,
            snapshot_id=target_snap_id,
            output_path=self.workspace_root,
        )
        self._add_audit(
            "restore",
            snapshot_id=target_snap_id,
            protect_snapshot_id=protect_snap.snapshot_id if protect_snap else None,
            actor=actor,
            ok=ok,
        )
        return ok

    # ---------- Tag & Branch ----------
    def tag(self, name: str, snapshot_id: Optional[str] = None,
            description: str = "", created_by: str = "system") -> Optional[RefEntry]:
        sid = snapshot_id
        if sid is None:
            latest = self.inner.get_latest_snapshot(self.workspace_id)
            if latest:
                sid = latest.snapshot_id
            else:
                return None
        entry = self.refs.create_tag(name, sid, description, created_by)
        self._save_refs()
        return entry

    def list_tags(self) -> List[RefEntry]:
        return list(self.refs.tags.values())

    def branch(self, name: str, snapshot_id: Optional[str] = None,
               description: str = "", created_by: str = "system") -> Optional[RefEntry]:
        sid = snapshot_id
        if sid is None:
            latest = self.inner.get_latest_snapshot(self.workspace_id)
            if latest:
                sid = latest.snapshot_id
            else:
                return None
        entry = self.refs.create_branch(name, sid, description, created_by)
        self._save_refs()
        return entry

    def list_branches(self) -> List[RefEntry]:
        return list(self.refs.branches.values())

    def checkout_branch(self, name: str, actor: str = "system") -> bool:
        b = self.refs.get_branch(name)
        if not b:
            return False
        self.refs.head_branch = name
        self._save_refs()
        return self.restore(b.snapshot_id, create_protect=True, actor=actor)

    # ---------- 列表与查询 ----------
    def list_snapshots(self) -> List[SnapshotMetadata]:
        return self.inner.list_snapshots(self.workspace_id)

    def get(self, snapshot_id_or_tag: str) -> Optional[SnapshotMetadata]:
        sid = self._resolve_ref(snapshot_id_or_tag)
        return self.inner.get_snapshot(self.workspace_id, sid) if sid else None

    def stats(self) -> Dict[str, Any]:
        return self.inner.get_snapshot_statistics(self.workspace_id)

    # ---------- 保留策略清理 ----------
    def apply_retention(self, dry_run: bool = False) -> List[SnapshotMetadata]:
        all_snaps = self.list_snapshots()
        tag_ids = {e.snapshot_id for e in self.refs.list_all()}
        to_delete = self.retention.apply(all_snaps, tag_ids)
        if not dry_run:
            for s in to_delete:
                self.inner.delete_snapshot(self.workspace_id, s.snapshot_id, force=True)
            self._add_audit("retention_cleanup", deleted_count=len(to_delete))
        return to_delete

    # ---------- Diff ----------
    def diff(self, left_id_or_tag: str, right_id_or_tag: str) -> Dict[str, Any]:
        left_id = self._resolve_ref(left_id_or_tag)
        right_id = self._resolve_ref(right_id_or_tag)
        if not left_id or not right_id:
            return {"error": "找不到快照"}
        left = self.inner.get_snapshot(self.workspace_id, left_id)
        right = self.inner.get_snapshot(self.workspace_id, right_id)
        if not left or not right:
            return {"error": "快照元数据加载失败"}

        return {
            "left": left_id,
            "right": right_id,
            "added_size": max(0, right.original_size - left.original_size),
            "delta_files_count": (
                len(getattr(right, "added_files", []) or [])
                + len(getattr(right, "changed_files", []) or [])
                + len(getattr(right, "deleted_files", []) or [])
            ),
        }

    # ---------- 内部工具 ----------
    def _resolve_ref(self, ref: str) -> Optional[str]:
        t = self.refs.get_tag(ref)
        if t:
            return t.snapshot_id
        b = self.refs.get_branch(ref)
        if b:
            return b.snapshot_id
        # 可能就是 snapshot_id
        if self.inner.get_snapshot(self.workspace_id, ref):
            return ref
        return None

    def _add_audit(self, action: str, **kwargs) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "workspace_id": self.workspace_id,
            **kwargs,
        }
        self.audit_log.append(entry)
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
        self._save_audit()

    def _save_refs(self) -> None:
        try:
            p = self.snapshots_root / "refs_index.json"
            p.write_text(json.dumps(self.refs.model_dump(), ensure_ascii=False, indent=2, default=str))
        except Exception as e:
            logger.error(f"保存 refs 失败: {e}")

    def _load_refs(self) -> None:
        p = self.snapshots_root / "refs_index.json"
        if not p.exists():
            return
        try:
            self.refs = RefsIndex(**json.loads(p.read_text()))
        except Exception as e:
            logger.error(f"加载 refs 失败: {e}")

    def _save_audit(self) -> None:
        try:
            p = self.snapshots_root / "audit_log.json"
            p.write_text(json.dumps(self.audit_log[-10000:], ensure_ascii=False, indent=2, default=str))
        except Exception as e:
            logger.error(f"保存审计日志失败: {e}")

    def _load_audit(self) -> None:
        p = self.snapshots_root / "audit_log.json"
        if not p.exists():
            return
        try:
            self.audit_log = json.loads(p.read_text())
        except Exception as e:
            logger.error(f"加载审计日志失败: {e}")


__all__ = [
    "WSSnapshotStatus",
    "RefType",
    "RefEntry",
    "RefsIndex",
    "RetentionTier",
    "RetentionPolicy",
    "WorkspaceSnapshotManager",
]
