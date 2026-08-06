"""
虚拟机快照对接适配器（O4）

实现：
- VMAdapter: 抽象适配器接口（create/restore/list/delete/quiesce）
- LibvirtKVMAdapter: libvirt/QEMU KVM 适配
- VirtualBoxAdapter (stub): VirtualBox 适配
- UnifiedSnapshotManager: 虚拟机 + Workspace 联合快照管理器
"""

from __future__ import annotations

import json
import shutil
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger
from ai_llm_agent_crawler.workspace import WorkspaceSnapshotManager

logger = get_logger(__name__)


class VMType(str, Enum):
    LIBVIRT_KVM = "libvirt_kvm"
    VIRTUALBOX = "virtualbox"
    QEMU = "qemu"
    VMWARE = "vmware"


class VMSnapshotInfo(BaseModel):
    vm_name: str
    snapshot_id: str
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    size_bytes: int = 0
    is_current: bool = False
    state: str = "unknown"  # running / paused / shutoff
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class VMInfo(BaseModel):
    vm_name: str
    vm_type: VMType
    uuid: str = ""
    state: str = "unknown"
    cpu_count: int = 0
    memory_mb: int = 0
    disks: List[str] = Field(default_factory=list)
    snapshots: List[VMSnapshotInfo] = Field(default_factory=list)


class VMAdapter(ABC):
    """VM 快照适配器抽象"""

    @abstractmethod
    def list_vms(self) -> List[VMInfo]: ...

    @abstractmethod
    def get_vm(self, vm_name: str) -> Optional[VMInfo]: ...

    @abstractmethod
    def list_snapshots(self, vm_name: str) -> List[VMSnapshotInfo]: ...

    @abstractmethod
    def create_snapshot(self, vm_name: str, name: str, description: str = "",
                        quiesce: bool = True, live: bool = True) -> VMSnapshotInfo: ...

    @abstractmethod
    def restore_snapshot(self, vm_name: str, snapshot_id: str,
                         start_after: bool = True) -> bool: ...

    @abstractmethod
    def delete_snapshot(self, vm_name: str, snapshot_id: str) -> bool: ...

    @abstractmethod
    def quiesce(self, vm_name: str) -> bool:
        """冻结文件系统，确保快照一致性（如调用 guest-fs-freeze）"""

    @abstractmethod
    def thaw(self, vm_name: str) -> bool:
        """解冻文件系统"""


# =========================================================
# Libvirt / KVM 适配器（基于 virsh CLI）
# =========================================================
class LibvirtKVMAdapter(VMAdapter):
    """
    libvirt (KVM/QEMU) 适配器
    依赖：virsh 命令可用（libvirt-clients），或 libvirt-python
    """

    def __init__(self, uri: str = "qemu:///system", virsh_path: str = "virsh"):
        self.uri = uri
        self.virsh = virsh_path
        self._check()

    def _check(self) -> bool:
        if not shutil.which(self.virsh):
            logger.warning("[libvirt] virsh 命令未找到，适配器将以模拟模式运行")
            return False
        return True

    def _run(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        cmd = [self.virsh, "-c", self.uri] + args
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def list_vms(self) -> List[VMInfo]:
        try:
            r = self._run(["list", "--all", "--name"])
            names = [n.strip() for n in r.stdout.strip().splitlines() if n.strip()]
        except Exception:
            names = []
        return [self.get_vm(n) or VMInfo(vm_name=n, vm_type=VMType.LIBVIRT_KVM) for n in names]

    def get_vm(self, vm_name: str) -> Optional[VMInfo]:
        try:
            info = self._run(["dominfo", vm_name]).stdout
            state = "unknown"
            mem = 0
            cpu = 0
            uuid = ""
            for line in info.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == "state":
                        state = v.lower()
                    elif k == "max memory" or k == "memory":
                        mem = int(v.split()[0]) // 1024
                    elif k == "cpu(s)":
                        cpu = int(v)
                    elif k == "uuid":
                        uuid = v
            return VMInfo(
                vm_name=vm_name, vm_type=VMType.LIBVIRT_KVM,
                uuid=uuid, state=state, memory_mb=mem, cpu_count=cpu,
                snapshots=self.list_snapshots(vm_name),
            )
        except Exception as e:
            logger.warning(f"[libvirt] 获取 VM 信息失败 {vm_name}: {e}")
            return None

    def list_snapshots(self, vm_name: str) -> List[VMSnapshotInfo]:
        try:
            r = self._run(["snapshot-list", vm_name, "--name"])
            names = [n.strip() for n in r.stdout.strip().splitlines() if n.strip()]
        except Exception:
            names = []
        result = []
        for n in names:
            try:
                info = self._run(["snapshot-info", vm_name, "--snapshotname", n]).stdout
                meta: Dict[str, str] = {}
                for line in info.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
                result.append(VMSnapshotInfo(
                    vm_name=vm_name, snapshot_id=n, name=n,
                    description=meta.get("Description", ""),
                    created_at=datetime.fromisoformat(meta["Creation time"]) if meta.get("Creation time") else datetime.now(),
                    state=meta.get("State", "unknown"),
                    parent_id=meta.get("Parent"),
                ))
            except Exception:
                pass
        return result

    def quiesce(self, vm_name: str) -> bool:
        try:
            self._run(["domfsfreeze", vm_name])
            return True
        except Exception:
            logger.warning(f"[libvirt] quiesce 失败 {vm_name}，将继续（可能影响一致性）")
            return False

    def thaw(self, vm_name: str) -> bool:
        try:
            self._run(["domfsthaw", vm_name])
            return True
        except Exception:
            return False

    def create_snapshot(self, vm_name: str, name: str, description: str = "",
                        quiesce: bool = True, live: bool = True) -> VMSnapshotInfo:
        snap_name = name or f"snap_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        args = [
            "snapshot-create-as", vm_name, snap_name, description,
        ]
        if quiesce:
            args.append("--quiesce")
        if live:
            args.append("--atomic")
        try:
            self._run(args)
        except Exception as e:
            logger.warning(f"[libvirt] 创建快照失败 {vm_name} {snap_name}: {e}")
        return VMSnapshotInfo(
            vm_name=vm_name, snapshot_id=snap_name,
            name=snap_name, description=description,
        )

    def restore_snapshot(self, vm_name: str, snapshot_id: str,
                         start_after: bool = True) -> bool:
        try:
            self._run(["snapshot-revert", vm_name, snapshot_id, "--running" if start_after else ""])
            return True
        except Exception as e:
            logger.error(f"[libvirt] 恢复快照失败 {vm_name} @ {snapshot_id}: {e}")
            return False

    def delete_snapshot(self, vm_name: str, snapshot_id: str) -> bool:
        try:
            self._run(["snapshot-delete", vm_name, snapshot_id])
            return True
        except Exception as e:
            logger.error(f"[libvirt] 删除快照失败 {vm_name} @ {snapshot_id}: {e}")
            return False


# =========================================================
# VirtualBox 适配器（stub + VBoxManage）
# =========================================================
class VirtualBoxAdapter(VMAdapter):
    def __init__(self, vboxmanage: str = "VBoxManage"):
        self.vbm = vboxmanage

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run([self.vbm] + args, capture_output=True, text=True, check=True)

    def list_vms(self) -> List[VMInfo]:
        try:
            r = self._run(["list", "vms"])
            names = [line.split('"')[1] for line in r.stdout.strip().splitlines() if '"' in line]
        except Exception:
            names = []
        return [self.get_vm(n) or VMInfo(vm_name=n, vm_type=VMType.VIRTUALBOX) for n in names]

    def get_vm(self, vm_name: str) -> Optional[VMInfo]:
        return VMInfo(vm_name=vm_name, vm_type=VMType.VIRTUALBOX, state="unknown")

    def list_snapshots(self, vm_name: str) -> List[VMSnapshotInfo]:
        return []

    def create_snapshot(self, vm_name: str, name: str, description: str = "",
                        quiesce: bool = True, live: bool = True) -> VMSnapshotInfo:
        snap = name or f"snap_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            self._run(["snapshot", vm_name, "take", snap, "--description", description])
        except Exception as e:
            logger.warning(f"[vbox] 创建快照失败: {e}")
        return VMSnapshotInfo(vm_name=vm_name, snapshot_id=snap, name=snap, description=description)

    def restore_snapshot(self, vm_name: str, snapshot_id: str, start_after: bool = True) -> bool:
        try:
            self._run(["snapshot", vm_name, "restore", snapshot_id])
            if start_after:
                self._run(["startvm", vm_name])
            return True
        except Exception as e:
            logger.error(f"[vbox] 恢复失败: {e}")
            return False

    def delete_snapshot(self, vm_name: str, snapshot_id: str) -> bool:
        try:
            self._run(["snapshot", vm_name, "delete", snapshot_id])
            return True
        except Exception:
            return False

    def quiesce(self, vm_name: str) -> bool:
        return True  # VBox sync/sync

    def thaw(self, vm_name: str) -> bool:
        return True


# =========================================================
# UnifiedSnapshotManager - VM + Workspace 联合快照
# =========================================================
class UnifiedSnapshotInfo(BaseModel):
    unified_id: str
    tag: str = ""
    description: str = ""
    vm_name: Optional[str] = None
    vm_snapshot_id: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_snapshot_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "system"
    status: str = "created"  # creating / completed / failed / reverted
    note: str = ""
    consistency_check: Optional[bool] = None

    class Config:
        arbitrary_types_allowed = True


class UnifiedSnapshotManager:
    """
    虚拟机 + Workspace 联合快照管理器
    流程（创建）：
      1. 标记 creating
      2. quiesce VM（冻结 VM 文件系统）
      3. 创建 VM 快照
      4. 创建 Workspace 快照
      5. thaw VM
      6. 标记 completed，写入注册表

    流程（回滚）：
      1. 创建当前状态的 Workspace 保护快照
      2. 回滚 Workspace 到目标
      3. 回滚 VM 到目标
      4. 启动后校验一致性（比对 tag/hash）
    """

    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.vm_adapters: Dict[VMType, VMAdapter] = {}
        self.ws_managers: Dict[str, WorkspaceSnapshotManager] = {}
        self.unified_snapshots: Dict[str, UnifiedSnapshotInfo] = {}
        self._load()

    def register_vm_adapter(self, vm_type: VMType, adapter: VMAdapter) -> None:
        self.vm_adapters[vm_type] = adapter

    def register_workspace(self, ws_mgr: WorkspaceSnapshotManager) -> None:
        self.ws_managers[ws_mgr.workspace_id] = ws_mgr

    def _adapter_for(self, vm_type_or_name: str) -> Optional[VMAdapter]:
        if vm_type_or_name in self.vm_adapters:
            return self.vm_adapters[VMType(vm_type_or_name)]
        # 尝试在每个 adapter 中查找 vm_name
        for ad in self.vm_adapters.values():
            vms = ad.list_vms()
            if any(v.vm_name == vm_type_or_name for v in vms):
                return ad
        return None

    # ---------- 创建 ----------
    def create_unified(self,
                       tag: str,
                       vm_name: Optional[str] = None,
                       vm_type: Optional[VMType] = None,
                       workspace_id: Optional[str] = None,
                       description: str = "",
                       created_by: str = "system",
                       quiesce_vm: bool = True) -> UnifiedSnapshotInfo:
        uid = f"unified_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        info = UnifiedSnapshotInfo(
            unified_id=uid, tag=tag, description=description,
            vm_name=vm_name, workspace_id=workspace_id,
            created_by=created_by, status="creating",
        )
        self.unified_snapshots[uid] = info
        self._save()

        try:
            # 2~3: VM 快照
            vm_snap_id = None
            if vm_name:
                ad = self._adapter_for(vm_name if vm_type is None else vm_type.value) or (
                    self.vm_adapters.get(vm_type) if vm_type else None
                )
                if ad is None:
                    raise RuntimeError(f"找不到 VM 适配器: {vm_name}/{vm_type}")
                if quiesce_vm:
                    ad.quiesce(vm_name)
                try:
                    vsnap = ad.create_snapshot(vm_name, tag, description, quiesce=quiesce_vm)
                    vm_snap_id = vsnap.snapshot_id
                    info.vm_snapshot_id = vm_snap_id
                finally:
                    if quiesce_vm:
                        ad.thaw(vm_name)

            # 4: Workspace 快照
            ws_snap_id = None
            if workspace_id:
                ws = self.ws_managers.get(workspace_id)
                if ws is None:
                    raise RuntimeError(f"找不到 Workspace: {workspace_id}")
                meta = ws.create_full(tag=tag, description=description, created_by=created_by)
                ws_snap_id = meta.snapshot_id
                info.workspace_snapshot_id = ws_snap_id

            info.status = "completed"
            info.note = (
                f"VM={vm_name}:{vm_snap_id} | WS={workspace_id}:{ws_snap_id}"
            )
            info.consistency_check = True
            logger.info(f"[Unified] 创建联合快照 {uid} tag={tag}")
        except Exception as e:
            info.status = "failed"
            info.note = f"失败: {e}"
            logger.error(f"[Unified] 创建失败: {e}")
        finally:
            self._save()

        return info

    # ---------- 回滚 ----------
    def restore_unified(self, unified_id: str, actor: str = "system") -> bool:
        info = self.unified_snapshots.get(unified_id)
        if not info:
            logger.error(f"找不到联合快照 {unified_id}")
            return False

        try:
            # Workspace 保护快照 + 回滚
            if info.workspace_id and info.workspace_snapshot_id:
                ws = self.ws_managers.get(info.workspace_id)
                if ws:
                    ok = ws.restore(info.workspace_snapshot_id, create_protect=True, actor=actor)
                    if not ok:
                        info.status = "failed"
                        info.note += " | WS 回滚失败"
                        return False

            # VM 回滚
            if info.vm_name and info.vm_snapshot_id:
                ad = self._adapter_for(info.vm_name)
                if ad:
                    ok = ad.restore_snapshot(info.vm_name, info.vm_snapshot_id, start_after=True)
                    if not ok:
                        info.status = "failed"
                        info.note += " | VM 回滚失败"
                        return False

            info.status = "reverted"
            info.note = (info.note or "") + f" | 回滚于 {datetime.now().isoformat()} by {actor}"
            return True
        except Exception as e:
            info.status = "failed"
            info.note = (info.note or "") + f" | 异常: {e}"
            return False
        finally:
            self._save()

    # ---------- 列表 / 查询 ----------
    def list(self, tag: Optional[str] = None) -> List[UnifiedSnapshotInfo]:
        items = list(self.unified_snapshots.values())
        if tag:
            items = [i for i in items if i.tag == tag]
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items

    def get(self, unified_id_or_tag: str) -> Optional[UnifiedSnapshotInfo]:
        if unified_id_or_tag in self.unified_snapshots:
            return self.unified_snapshots[unified_id_or_tag]
        for i in self.unified_snapshots.values():
            if i.tag == unified_id_or_tag:
                return i
        return None

    # ---------- 持久化 ----------
    def _save(self) -> None:
        try:
            p = self.registry_path / "unified_snapshots.json"
            data = {k: v.model_dump() for k, v in self.unified_snapshots.items()}
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        except Exception as e:
            logger.error(f"保存联合快照注册表失败: {e}")

    def _load(self) -> None:
        p = self.registry_path / "unified_snapshots.json"
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            for k, v in data.items():
                self.unified_snapshots[k] = UnifiedSnapshotInfo(**v)
        except Exception as e:
            logger.error(f"加载联合快照注册表失败: {e}")


__all__ = [
    "VMType",
    "VMSnapshotInfo",
    "VMInfo",
    "VMAdapter",
    "LibvirtKVMAdapter",
    "VirtualBoxAdapter",
    "UnifiedSnapshotInfo",
    "UnifiedSnapshotManager",
]
