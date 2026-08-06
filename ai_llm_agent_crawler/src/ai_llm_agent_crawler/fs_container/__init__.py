"""
virtual-fs-container 虚拟文件系统容器框架

提供容器化的文件系统抽象，支持：
- Container: 容器实体，封装层栈 + 挂载点
- LayerStack: lower/upper/workdir/merged 层模型
- OverlayFSBackend: Linux 内核 overlayfs 后端（高性能）
- UserSpaceCOWBackend: 纯用户态 COW（跨平台、无特权）
- StorageBackendAdapter: NAS/S3 多后端适配层
- ContainerManager: 容器生命周期管理
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class BackendType(str, Enum):
    OVERLAYFS = "overlayfs"      # Linux 内核 overlayfs
    USERSPACE_COW = "userspace"  # 纯用户态 COW


class ContainerStatus(str, Enum):
    CREATED = "created"
    MOUNTED = "mounted"
    UNMOUNTED = "unmounted"
    DAMAGED = "damaged"


class LayerInfo(BaseModel):
    layer_id: str
    parent_id: Optional[str] = None
    lower_layer_ids: List[str] = Field(default_factory=list)
    path: Path
    size_bytes: int = 0
    is_readonly: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class LayerStack(BaseModel):
    """层栈模型：[lower layers (read-only)] -> upper (writable) -> merged"""
    lowers: List[LayerInfo] = Field(default_factory=list)
    upper: Optional[LayerInfo] = None
    workdir: Optional[Path] = None
    merged: Optional[Path] = None

    class Config:
        arbitrary_types_allowed = True

    @property
    def all_layer_ids(self) -> List[str]:
        return [l.layer_id for l in self.lowers] + ([self.upper.layer_id] if self.upper else [])


class ContainerSpec(BaseModel):
    """容器规格"""
    name: str
    container_id: str
    backend: BackendType = BackendType.USERSPACE_COW
    source_path: Path  # 初始数据源路径
    storage_root: Path  # 容器存储根目录
    storage_uri: str = ""  # nas:// / s3:// 等 URI
    description: str = ""
    labels: Dict[str, str] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class ContainerInfo(BaseModel):
    spec: ContainerSpec
    status: ContainerStatus = ContainerStatus.CREATED
    layers: LayerStack = Field(default_factory=LayerStack)
    mount_point: Optional[Path] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    mounted_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


# ---------------- FS Backend 抽象 ----------------
class FSBackend(ABC):
    """文件系统后端抽象"""

    @abstractmethod
    def mount(self, container: ContainerInfo) -> Path:
        """执行挂载，返回 merged 目录路径"""

    @abstractmethod
    def unmount(self, container: ContainerInfo) -> bool:
        """执行卸载"""

    @abstractmethod
    def is_mounted(self, container: ContainerInfo) -> bool:
        """检查是否已挂载"""

    @abstractmethod
    def commit_layer(self, container: ContainerInfo, layer_name: str = "") -> LayerInfo:
        """将 upper 提交为新只读层"""


# ---------------- OverlayFS 后端 ----------------
class OverlayFSBackend(FSBackend):
    """
    Linux 内核 OverlayFS 后端
    依赖：Linux 内核支持 overlay + 有 mount 权限（或 CAP_SYS_ADMIN / user namespace）
    """

    def __init__(self, sudo: bool = False):
        self.sudo = sudo
        self._check_support()

    def _check_support(self) -> bool:
        try:
            import platform
            if platform.system() != "Linux":
                return False
            with open("/proc/filesystems") as f:
                if "overlay" not in f.read():
                    return False
            return True
        except Exception:
            return False

    def _run(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        prefix = ["sudo"] if self.sudo else []
        return subprocess.run(prefix + args, capture_output=True, text=True, check=check)

    def mount(self, container: ContainerInfo) -> Path:
        stack = container.layers
        if not stack.merged or not stack.workdir:
            raise RuntimeError("Container 层栈未初始化")

        lower_dirs = ":".join(str(l.path) for l in reversed(stack.lowers))  # overlay 需要 lower1:lower2:...
        upper_dir = str(stack.upper.path) if stack.upper else ""
        work_dir = str(stack.workdir)
        merged_dir = str(stack.merged)

        options_parts = []
        if stack.lowers:
            options_parts.append(f"lowerdir={lower_dirs}")
        if upper_dir:
            options_parts.append(f"upperdir={upper_dir}")
        options_parts.append(f"workdir={work_dir}")
        options = ",".join(options_parts)

        Path(merged_dir).mkdir(parents=True, exist_ok=True)

        try:
            self._run(["mount", "-t", "overlay", "overlay", "-o", options, merged_dir])
            container.status = ContainerStatus.MOUNTED
            container.mount_point = Path(merged_dir)
            container.mounted_at = datetime.now()
            logger.info(f"[OverlayFS] 挂载成功: {merged_dir}")
            return Path(merged_dir)
        except subprocess.CalledProcessError as e:
            logger.error(f"[OverlayFS] 挂载失败: {e.stderr}")
            raise

    def unmount(self, container: ContainerInfo) -> bool:
        if not container.mount_point:
            return True
        try:
            self._run(["umount", str(container.mount_point)])
            container.status = ContainerStatus.UNMOUNTED
            container.mount_point = None
            container.mounted_at = None
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"[OverlayFS] 卸载失败: {e.stderr}")
            return False

    def is_mounted(self, container: ContainerInfo) -> bool:
        if not container.mount_point:
            return False
        try:
            with open("/proc/mounts") as f:
                return any(str(container.mount_point) in line for line in f)
        except Exception:
            return False

    def commit_layer(self, container: ContainerInfo, layer_name: str = "") -> LayerInfo:
        """将 upper 层提交为新的只读层"""
        if not container.layers.upper:
            raise RuntimeError("没有可提交的 upper 层")
        upper = container.layers.upper
        size = sum(f.stat().st_size for f in upper.path.rglob("*") if f.is_file())
        # 标记只读
        committed_path = upper.path.parent / (layer_name or f"layer_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        if committed_path != upper.path:
            shutil.move(str(upper.path), str(committed_path))
        # 设置只读标志
        try:
            for p in committed_path.rglob("*"):
                if p.is_file():
                    os.chmod(p, 0o444)
        except Exception:
            pass
        info = LayerInfo(
            layer_id=committed_path.name,
            path=committed_path,
            size_bytes=size,
            is_readonly=True,
            parent_id=container.layers.lowers[-1].layer_id if container.layers.lowers else None,
        )
        container.layers.lowers.append(info)
        # 新建空的 upper
        new_upper_path = committed_path.parent / "upper"
        new_upper_path.mkdir(exist_ok=True)
        container.layers.upper = LayerInfo(
            layer_id="upper", path=new_upper_path,
        )
        container.updated_at = datetime.now()
        return info


# ---------------- 纯用户态 COW 后端 ----------------
class UserSpaceCOWBackend(FSBackend):
    """
    纯用户态 COW（Copy-On-Write）后端
    无特权、跨平台。

    原理：
    - 读：优先从 upper 读，不存在则从最近 lower 读
    - 写：先从 lower 复制到 upper，再在 upper 上修改
    - 删：在 upper 中创建 whiteout 文件（.wh_ 前缀）
    """

    WHT_PREFIX = ".wh_"

    def mount(self, container: ContainerInfo) -> Path:
        """挂载：只需确保 merged 目录存在，用户态实现 merged 通过 API 访问"""
        if not container.layers.merged:
            merged = container.spec.storage_root / "merged"
            merged.mkdir(parents=True, exist_ok=True)
            container.layers.merged = merged
        container.status = ContainerStatus.MOUNTED
        container.mount_point = container.layers.merged
        container.mounted_at = datetime.now()
        logger.info(f"[UserSpaceCOW] 挂载成功: {container.layers.merged}")
        return container.layers.merged

    def unmount(self, container: ContainerInfo) -> bool:
        container.status = ContainerStatus.UNMOUNTED
        container.mount_point = None
        container.mounted_at = None
        return True

    def is_mounted(self, container: ContainerInfo) -> bool:
        return container.status == ContainerStatus.MOUNTED and container.mount_point is not None

    # ------ 读写访问 API（用户态 COW 核心） ------
    def resolve_path(self, container: ContainerInfo, relative: str) -> Optional[Path]:
        """解析读路径：upper -> lower[last] -> ... -> lower[first]"""
        rel = relative.lstrip("/")
        # whiteout？
        wh = Path(self.WHT_PREFIX + rel)
        if container.layers.upper:
            if (container.layers.upper.path / wh).exists():
                return None
            f = container.layers.upper.path / rel
            if f.exists():
                return f
        for layer in reversed(container.layers.lowers):
            f = layer.path / rel
            if f.exists():
                return f
        return None

    def list_dir(self, container: ContainerInfo, relative: str = "") -> List[str]:
        """列出目录内容（合并上下层 + 处理 whiteout）"""
        rel = relative.lstrip("/")
        items: set = set()
        # 收集 lower
        for layer in container.layers.lowers:
            d = layer.path / rel
            if d.is_dir():
                for p in d.iterdir():
                    items.add(p.name)
        # 收集 upper，处理 whiteout
        if container.layers.upper:
            d = container.layers.upper.path / rel
            if d.is_dir():
                for p in d.iterdir():
                    if p.name.startswith(self.WHT_PREFIX):
                        original = p.name[len(self.WHT_PREFIX):]
                        items.discard(original)
                    else:
                        items.add(p.name)
        return sorted(items)

    def write_path(self, container: ContainerInfo, relative: str) -> Path:
        """获取可写路径（触发 COW）"""
        if not container.layers.upper:
            raise RuntimeError("没有可写的 upper 层")
        rel = relative.lstrip("/")
        target = container.layers.upper.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        # 若 lower 存在且 upper 不存在 → copy-up
        if not target.exists():
            src = None
            for layer in reversed(container.layers.lowers):
                f = layer.path / rel
                if f.exists():
                    src = f
                    break
            if src is not None:
                if src.is_dir():
                    shutil.copytree(src, target)
                else:
                    shutil.copy2(src, target)
        # 移除 whiteout（若存在）
        wh = container.layers.upper.path / (self.WHT_PREFIX + rel)
        if wh.exists():
            wh.unlink()
        return target

    def delete_path(self, container: ContainerInfo, relative: str) -> bool:
        """删除：写 whiteout 到 upper"""
        if not container.layers.upper:
            return False
        rel = relative.lstrip("/")
        # 先删 upper 里的
        up = container.layers.upper.path / rel
        if up.exists():
            if up.is_dir():
                shutil.rmtree(up)
            else:
                up.unlink()
        # 写 whiteout
        wh = container.layers.upper.path / (self.WHT_PREFIX + rel)
        wh.parent.mkdir(parents=True, exist_ok=True)
        wh.touch()
        return True

    def commit_layer(self, container: ContainerInfo, layer_name: str = "") -> LayerInfo:
        """提交 upper 为新只读层"""
        if not container.layers.upper:
            raise RuntimeError("没有可提交的 upper 层")
        upper = container.layers.upper
        size = sum(f.stat().st_size for f in upper.path.rglob("*") if f.is_file())
        committed_path = upper.path.parent / (layer_name or f"layer_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        shutil.move(str(upper.path), str(committed_path))
        info = LayerInfo(
            layer_id=committed_path.name,
            path=committed_path,
            size_bytes=size,
            is_readonly=True,
            parent_id=container.layers.lowers[-1].layer_id if container.layers.lowers else None,
        )
        container.layers.lowers.append(info)
        new_upper = committed_path.parent / "upper"
        new_upper.mkdir(exist_ok=True)
        container.layers.upper = LayerInfo(layer_id="upper", path=new_upper)
        container.updated_at = datetime.now()
        return info


# ---------------- NAS / S3 存储适配 ----------------
class StorageAdapter(ABC):
    """外部存储适配：允许层数据存放在 NAS / S3"""
    @abstractmethod
    def fetch_layer(self, layer_id: str, local_dir: Path) -> bool: ...
    @abstractmethod
    def push_layer(self, layer_id: str, local_dir: Path) -> bool: ...
    @abstractmethod
    def exists(self, layer_id: str) -> bool: ...


class LocalStorageAdapter(StorageAdapter):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _lp(self, lid: str) -> Path:
        return self.root / lid

    def fetch_layer(self, layer_id: str, local_dir: Path) -> bool:
        src = self._lp(layer_id)
        if not src.exists():
            return False
        if local_dir.exists():
            shutil.rmtree(local_dir)
        shutil.copytree(src, local_dir)
        return True

    def push_layer(self, layer_id: str, local_dir: Path) -> bool:
        tgt = self._lp(layer_id)
        if tgt.exists():
            shutil.rmtree(tgt)
        shutil.copytree(local_dir, tgt)
        return True

    def exists(self, layer_id: str) -> bool:
        return self._lp(layer_id).exists()


class NASStorageAdapter(LocalStorageAdapter):
    """NAS 适配器：NFS/SMB 已在本地挂载，直接使用本地路径语义"""
    def __init__(self, nas_mount_point: Path):
        super().__init__(Path(nas_mount_point) / "vfs_layers")


class S3StorageAdapter(StorageAdapter):
    """S3 兼容对象存储适配器（基于 boto3/minio）"""
    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str, prefix: str = "vfs_layers"):
        try:
            import boto3
            self.client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
        except Exception as e:
            raise RuntimeError(f"boto3 初始化失败: {e}")
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")

    def _key(self, lid: str) -> str:
        return f"{self.prefix}/{lid}"

    def exists(self, layer_id: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(layer_id) + "/.marker")
            return True
        except Exception:
            return False

    def push_layer(self, layer_id: str, local_dir: Path) -> bool:
        try:
            for f in Path(local_dir).rglob("*"):
                if f.is_file():
                    rel = f.relative_to(local_dir)
                    self.client.upload_file(str(f), self.bucket, f"{self._key(layer_id)}/{rel}")
            # marker
            marker = Path(local_dir) / ".marker"
            marker.write_text(layer_id)
            self.client.upload_file(str(marker), self.bucket, f"{self._key(layer_id)}/.marker")
            marker.unlink(missing_ok=True)
            return True
        except Exception as e:
            logger.error(f"S3 push_layer 失败: {e}")
            return False

    def fetch_layer(self, layer_id: str, local_dir: Path) -> bool:
        try:
            if local_dir.exists():
                shutil.rmtree(local_dir)
            local_dir.mkdir(parents=True, exist_ok=True)
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=self._key(layer_id) + "/"):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    rel = key[len(self._key(layer_id)) + 1:]
                    if not rel or rel == ".marker":
                        continue
                    tgt = local_dir / rel
                    tgt.parent.mkdir(parents=True, exist_ok=True)
                    self.client.download_file(self.bucket, key, str(tgt))
            return True
        except Exception as e:
            logger.error(f"S3 fetch_layer 失败: {e}")
            return False


# ---------------- Container Manager ----------------
class ContainerManager:
    """容器生命周期管理"""

    def __init__(self, storage_root: Path, default_backend: BackendType = BackendType.USERSPACE_COW):
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.default_backend = default_backend
        self.containers: Dict[str, ContainerInfo] = {}
        self.storage_adapters: Dict[str, StorageAdapter] = {}
        self._load_registry()
        self._auto_detect_adapters()

    # ---- 注册适配器 ----
    def register_adapter(self, name: str, adapter: StorageAdapter) -> None:
        self.storage_adapters[name] = adapter

    def _auto_detect_adapters(self) -> None:
        self.storage_adapters["local"] = LocalStorageAdapter(self.storage_root / "layers_pool")

    # ---- 创建 / 删除 ----
    def create(self, name: str, source_path: Path,
               backend: Optional[BackendType] = None,
               description: str = "",
               labels: Optional[Dict[str, str]] = None,
               storage_uri: str = "") -> ContainerInfo:
        backend = backend or self.default_backend
        cid = f"vfs_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        croot = self.storage_root / cid
        croot.mkdir(parents=True, exist_ok=True)
        spec = ContainerSpec(
            name=name, container_id=cid, backend=backend,
            source_path=Path(source_path), storage_root=croot,
            description=description, labels=labels or {},
            storage_uri=storage_uri,
        )
        # 初始化层
        lower_dir = croot / "layer_0_base"
        shutil.copytree(source_path, lower_dir)
        base_layer = LayerInfo(
            layer_id="layer_0_base", path=lower_dir,
            size_bytes=sum(f.stat().st_size for f in lower_dir.rglob("*") if f.is_file()),
            is_readonly=True,
        )
        upper_dir = croot / "upper"
        work_dir = croot / "work"
        merged_dir = croot / "merged"
        for d in (upper_dir, work_dir, merged_dir):
            d.mkdir(exist_ok=True)
        upper = LayerInfo(layer_id="upper", path=upper_dir)
        stack = LayerStack(lowers=[base_layer], upper=upper, workdir=work_dir, merged=merged_dir)
        info = ContainerInfo(spec=spec, layers=stack)
        self.containers[cid] = info
        self._save_registry()
        logger.info(f"[vfs] 创建容器: {name} ({cid}) backend={backend.value}")
        return info

    def remove(self, cid: str, force: bool = False) -> bool:
        info = self.containers.get(cid)
        if not info:
            return False
        if info.status == ContainerStatus.MOUNTED and not force:
            raise RuntimeError("容器仍处于挂载状态，需要先卸载或使用 force=True")
        if info.mount_point:
            self._get_backend(info).unmount(info)
        try:
            if info.spec.storage_root.exists():
                shutil.rmtree(info.spec.storage_root)
        except Exception as e:
            logger.error(f"删除容器存储失败: {e}")
        del self.containers[cid]
        self._save_registry()
        return True

    # ---- 挂载 / 卸载 ----
    def mount(self, cid: str) -> Path:
        info = self._require(cid)
        backend = self._get_backend(info)
        return backend.mount(info)

    def unmount(self, cid: str) -> bool:
        info = self._require(cid)
        backend = self._get_backend(info)
        return backend.unmount(info)

    def commit(self, cid: str, layer_name: str = "") -> LayerInfo:
        info = self._require(cid)
        backend = self._get_backend(info)
        layer = backend.commit_layer(info, layer_name)
        # 推送到外部存储
        if layer_name:
            for name, adapter in self.storage_adapters.items():
                if name == "local":
                    continue
                adapter.push_layer(layer.layer_id, layer.path)
        self._save_registry()
        return layer

    # ---- 访问 API ----
    def get(self, cid: str) -> Optional[ContainerInfo]:
        return self.containers.get(cid)

    def list(self) -> List[ContainerInfo]:
        return list(self.containers.values())

    def resolve(self, cid: str, relative: str) -> Optional[Path]:
        info = self._require(cid)
        backend = self._get_backend(info)
        if isinstance(backend, UserSpaceCOWBackend):
            return backend.resolve_path(info, relative)
        # overlayfs: 直接拼接 merged
        if info.mount_point:
            p = info.mount_point / relative.lstrip("/")
            return p if p.exists() else None
        return None

    # ---- 内部 ----
    def _require(self, cid: str) -> ContainerInfo:
        info = self.containers.get(cid)
        if not info:
            raise KeyError(f"容器 {cid} 不存在")
        return info

    def _get_backend(self, info: ContainerInfo) -> FSBackend:
        if info.spec.backend == BackendType.OVERLAYFS:
            return OverlayFSBackend()
        return UserSpaceCOWBackend()

    def _save_registry(self) -> None:
        try:
            p = self.storage_root / "container_registry.json"
            data = {cid: info.model_dump() for cid, info in self.containers.items()}
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        except Exception as e:
            logger.error(f"保存容器注册表失败: {e}")

    def _load_registry(self) -> None:
        p = self.storage_root / "container_registry.json"
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            for cid, raw in data.items():
                try:
                    self.containers[cid] = ContainerInfo(**raw)
                except Exception as e:
                    logger.warning(f"跳过损坏的容器记录 {cid}: {e}")
        except Exception as e:
            logger.error(f"加载容器注册表失败: {e}")


__all__ = [
    "BackendType",
    "ContainerStatus",
    "LayerInfo",
    "LayerStack",
    "ContainerSpec",
    "ContainerInfo",
    "FSBackend",
    "OverlayFSBackend",
    "UserSpaceCOWBackend",
    "StorageAdapter",
    "LocalStorageAdapter",
    "NASStorageAdapter",
    "S3StorageAdapter",
    "ContainerManager",
]
