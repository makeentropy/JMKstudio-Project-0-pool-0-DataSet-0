"""
OKR 领域模型与注册模块

JMKstudio Workparty Group Project OKR 管理：
- Objective: 目标（O1~O5）
- KeyResult: 关键结果（KR）
- Task: 可执行子任务
- OKRRegistry: 注册与进度追踪
- OKRReporter: 报告生成
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.config import get_settings
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class OKRStatus(str, Enum):
    """OKR 状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AT_RISK = "at_risk"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OKRPeriod(str, Enum):
    """OKR 周期"""
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    YEARLY = "yearly"
    CUSTOM = "custom"


class KeyResult(BaseModel):
    """关键结果"""
    kr_id: str = Field(..., description="KR 编号，如 KR 1.1.1")
    title: str = Field(..., description="KR 标题")
    description: str = Field(default="", description="详细描述")
    status: OKRStatus = Field(default=OKRStatus.NOT_STARTED)
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="完成度 0~1")
    metric_target: Optional[float] = Field(default=None, description="指标目标值")
    metric_current: Optional[float] = Field(default=None, description="指标当前值")
    metric_unit: str = Field(default="", description="指标单位")
    owner: str = Field(default="", description="负责人")
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)
    notes: str = Field(default="")

    def mark(self, progress: float, status: Optional[OKRStatus] = None) -> None:
        self.progress = max(0.0, min(1.0, progress))
        if status:
            self.status = status
        elif self.progress >= 1.0:
            self.status = OKRStatus.COMPLETED
            self.completed_at = datetime.now()
        elif self.progress > 0:
            self.status = OKRStatus.IN_PROGRESS
        self.updated_at = datetime.now()


class Objective(BaseModel):
    """目标"""
    obj_id: str = Field(..., description="目标编号，如 O1")
    title: str = Field(..., description="目标名称")
    description: str = Field(default="", description="目标描述")
    period: OKRPeriod = Field(default=OKRPeriod.Q3)
    status: OKRStatus = Field(default=OKRStatus.NOT_STARTED)
    owner_domain: str = Field(default="", description="负责人域")
    key_results: List[KeyResult] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def progress(self) -> float:
        if not self.key_results:
            return 0.0
        return sum(kr.progress for kr in self.key_results) / len(self.key_results)

    def add_kr(self, kr: KeyResult) -> None:
        self.key_results.append(kr)
        self.updated_at = datetime.now()

    def get_kr(self, kr_id: str) -> Optional[KeyResult]:
        for kr in self.key_results:
            if kr.kr_id == kr_id:
                return kr
        return None


class OKRTask(BaseModel):
    """可执行子任务"""
    task_id: str = Field(..., description="任务编号，如 T1.1")
    title: str = Field(..., description="任务名称")
    description: str = Field(default="")
    linked_obj: str = Field(default="", description="关联 O 编号")
    linked_kr: str = Field(default="", description="关联 KR 编号")
    status: OKRStatus = Field(default=OKRStatus.NOT_STARTED)
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    phase: int = Field(default=1, ge=1, le=7, description="所属阶段（1~7）")
    depends_on: List[str] = Field(default_factory=list)
    owner: str = Field(default="")
    files: List[str] = Field(default_factory=list, description="关联文件路径")
    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class OKRProgressEntry(BaseModel):
    """进度日志条目"""
    timestamp: datetime = Field(default_factory=datetime.now)
    obj_id: Optional[str] = None
    kr_id: Optional[str] = None
    task_id: Optional[str] = None
    old_progress: float
    new_progress: float
    status: Optional[OKRStatus] = None
    note: str = ""
    author: str = "system"


class OKRRegistry:
    """OKR 注册表与进度追踪器"""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = Path(storage_path) if storage_path is not None else (Path(get_settings().dataset_output_dir) / "okr")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.objectives: Dict[str, Objective] = {}
        self.tasks: Dict[str, OKRTask] = {}
        self.progress_log: List[OKRProgressEntry] = []
        self._listeners: List[Callable[[OKRProgressEntry], None]] = []
        self._load()

    # ---------- 目标管理 ----------
    def register_objective(self, obj: Objective) -> Objective:
        self.objectives[obj.obj_id] = obj
        self._save()
        logger.info(f"[OKR] 注册目标 {obj.obj_id}: {obj.title}")
        return obj

    def list_objectives(self) -> List[Objective]:
        return sorted(self.objectives.values(), key=lambda o: o.obj_id)

    def get_objective(self, obj_id: str) -> Optional[Objective]:
        return self.objectives.get(obj_id)

    # ---------- KR 管理 ----------
    def update_kr(self, kr_id: str, progress: float,
                  status: Optional[OKRStatus] = None, note: str = "",
                  author: str = "system") -> Optional[KeyResult]:
        for obj in self.objectives.values():
            kr = obj.get_kr(kr_id)
            if kr:
                old = kr.progress
                kr.mark(progress, status)
                entry = OKRProgressEntry(
                    obj_id=obj.obj_id, kr_id=kr_id,
                    old_progress=old, new_progress=kr.progress,
                    status=kr.status, note=note, author=author,
                )
                self.progress_log.append(entry)
                for l in self._listeners:
                    l(entry)
                self._save()
                logger.info(f"[OKR] KR {kr_id} 进度: {old:.0%} → {kr.progress:.0%} ({kr.status.value})")
                return kr
        return None

    # ---------- 任务管理 ----------
    def register_task(self, task: OKRTask) -> OKRTask:
        self.tasks[task.task_id] = task
        self._save()
        return task

    def update_task(self, task_id: str, progress: float,
                    status: Optional[OKRStatus] = None, note: str = "",
                    author: str = "system") -> Optional[OKRTask]:
        task = self.tasks.get(task_id)
        if not task:
            return None
        old = task.progress
        task.progress = max(0.0, min(1.0, progress))
        if status:
            task.status = status
        elif task.progress >= 1.0:
            task.status = OKRStatus.COMPLETED
        elif task.progress > 0:
            task.status = OKRStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        task.notes = (task.notes + "\n" + note).strip() if note else task.notes

        entry = OKRProgressEntry(
            task_id=task_id, linked_obj=task.linked_obj, linked_kr=task.linked_kr,
            old_progress=old, new_progress=task.progress,
            status=task.status, note=note, author=author,
        )
        self.progress_log.append(entry)
        self._save()
        return task

    def list_tasks_by_phase(self, phase: int) -> List[OKRTask]:
        return sorted(
            [t for t in self.tasks.values() if t.phase == phase],
            key=lambda t: t.task_id,
        )

    # ---------- 报告 ----------
    def generate_report(self) -> Dict[str, Any]:
        objectives = self.list_objectives()
        total_kr = sum(len(o.key_results) for o in objectives)
        completed_kr = sum(
            1 for o in objectives for kr in o.key_results
            if kr.status == OKRStatus.COMPLETED
        )
        avg_progress = (
            sum(o.progress for o in objectives) / len(objectives)
            if objectives else 0.0
        )

        tasks_total = len(self.tasks)
        tasks_completed = sum(
            1 for t in self.tasks.values() if t.status == OKRStatus.COMPLETED
        )

        by_phase: Dict[int, Dict[str, int]] = {}
        for t in self.tasks.values():
            p = t.phase
            if p not in by_phase:
                by_phase[p] = {"total": 0, "completed": 0}
            by_phase[p]["total"] += 1
            if t.status == OKRStatus.COMPLETED:
                by_phase[p]["completed"] += 1

        return {
            "summary": {
                "total_objectives": len(objectives),
                "total_key_results": total_kr,
                "completed_key_results": completed_kr,
                "average_progress": avg_progress,
                "total_tasks": tasks_total,
                "completed_tasks": tasks_completed,
                "task_completion_rate": tasks_completed / tasks_total if tasks_total else 0,
            },
            "objectives": [
                {
                    "id": o.obj_id,
                    "title": o.title,
                    "period": o.period.value,
                    "status": o.status.value,
                    "progress": o.progress,
                    "owner_domain": o.owner_domain,
                    "key_results": [
                        {
                            "id": kr.kr_id,
                            "title": kr.title,
                            "status": kr.status.value,
                            "progress": kr.progress,
                            "owner": kr.owner,
                        }
                        for kr in o.key_results
                    ],
                }
                for o in objectives
            ],
            "phases": by_phase,
            "recent_updates": [
                e.model_dump() for e in self.progress_log[-20:]
            ],
        }

    # ---------- 持久化 ----------
    def _save(self) -> None:
        try:
            data = {
                "objectives": {k: v.model_dump() for k, v in self.objectives.items()},
                "tasks": {k: v.model_dump() for k, v in self.tasks.items()},
                "progress_log": [e.model_dump() for e in self.progress_log[-1000:]],
            }
            f = self.storage_path / "okr_registry.json"
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        except Exception as e:
            logger.error(f"保存 OKR 注册表失败: {e}")

    def _load(self) -> None:
        f = self.storage_path / "okr_registry.json"
        if not f.exists():
            return
        try:
            data = json.loads(f.read_text())
            for k, v in data.get("objectives", {}).items():
                krs = [KeyResult(**kr) for kr in v.get("key_results", [])]
                v["key_results"] = krs
                self.objectives[k] = Objective(**v)
            for k, v in data.get("tasks", {}).items():
                self.tasks[k] = OKRTask(**v)
            for e in data.get("progress_log", []):
                self.progress_log.append(OKRProgressEntry(**e))
            logger.info(
                f"加载 OKR 注册表: {len(self.objectives)} 目标, "
                f"{len(self.tasks)} 任务, {len(self.progress_log)} 日志"
            )
        except Exception as e:
            logger.error(f"加载 OKR 注册表失败: {e}")

    def add_listener(self, listener: Callable[[OKRProgressEntry], None]) -> None:
        self._listeners.append(listener)


# ---------- 默认 OKR 初始化 ----------
def bootstrap_default_okr(registry: OKRRegistry) -> None:
    """初始化 JMKstudio Workparty 默认 OKR"""
    if registry.objectives:
        return  # 已初始化

    # O1
    o1 = Objective(
        obj_id="O1",
        title="建立 Workspace 统一快照与版本控制体系",
        description="覆盖 Workspace 全量/增量快照、Tag/Branch、回滚、保留策略",
        period=OKRPeriod.Q3,
        owner_domain="workspace/versioning",
    )
    o1_krs = [
        ("KR 1.1.1", "手动创建完整快照返回 snapshot_id/tag/checksum", "workspace"),
        ("KR 1.1.2", "增量快照自动计算 added/changed/deleted 文件清单", "workspace"),
        ("KR 1.1.3", "Tag/Branch 元数据写入 refs 版本索引", "workspace"),
        ("KR 1.1.4", "支持按 tag 回滚、按 branch diff", "workspace"),
        ("KR 1.2.1", "回滚前自动创建当前状态保护快照", "workspace"),
        ("KR 1.2.2", "回滚操作审计日志（audit log）", "security"),
        ("KR 1.2.3", "GFS 风格保留策略（小时/天/周/月层级）", "workspace"),
        ("KR 1.2.4", "快照链完整性保护（不截断完整链）", "workspace"),
    ]
    for kid, title, owner in o1_krs:
        o1.add_kr(KeyResult(kr_id=kid, title=title, owner=owner))
    registry.register_objective(o1)

    # O2
    o2 = Objective(
        obj_id="O2",
        title="构建 virtual-fs-container 虚拟文件系统容器框架",
        description="OverlayFS / 纯用户态 COW 双实现 + NAS/S3 多后端",
        period=OKRPeriod.Q3,
        owner_domain="storage/fs-container",
    )
    o2_krs = [
        ("KR 2.1.1", "Container 抽象层 create/destroy/mount/umount", "fs_container"),
        ("KR 2.1.2", "Layer Stack 抽象 lower/upper/workdir/merged", "fs_container"),
        ("KR 2.1.3", "commit 生成新只读层", "fs_container"),
        ("KR 2.2.1", "OverlayFS 后端（kernel native）", "fs_container"),
        ("KR 2.2.2", "纯用户态 COW 后端（无特权跨平台）", "fs_container"),
        ("KR 2.2.3", "双后端 API 完全一致（LSP 原则）", "fs_container"),
        ("KR 2.3.1", "NAS NFS 后端 nas:// URI 支持", "storage"),
        ("KR 2.3.2", "S3 兼容后端 s3:// URI + 本地缓存", "storage"),
    ]
    for kid, title, owner in o2_krs:
        o2.add_kr(KeyResult(kr_id=kid, title=title, owner=owner))
    registry.register_objective(o2)

    # O3
    o3 = Objective(
        obj_id="O3",
        title="落地端到端数据保全与安全校验链（GPG+CA+Merkle+隐写）",
        description="Merkle 树 + GPG CA + baseXOR-prober 隐写 + HashChain 账本",
        period=OKRPeriod.Q3,
        owner_domain="security/datachain",
    )
    o3_krs = [
        ("KR 3.1.1", "文件块级 Merkle Tree 构建与证明", "security"),
        ("KR 3.1.2", "目录级 / 快照级 Merkle root 聚合", "security"),
        ("KR 3.1.3", "root_hash 写入快照元数据", "versioning"),
        ("KR 3.2.1", "项目 CA：根证书 / 成员证书签发", "security"),
        ("KR 3.2.2", "成员私钥签名快照", "security"),
        ("KR 3.2.3", "CA→签名→Merkle→块哈希 四级验签", "security"),
        ("KR 3.3.1", "baseXOR-prober 锚点注入（哈希+链序号+CA指纹）", "security"),
        ("KR 3.3.2", "prober scan 分布式扫描数据块", "security"),
        ("KR 3.3.3", "缺失/错位/篡改块检测 + 审计报告", "security"),
        ("KR 3.4.1", "HashChain 轻量账本 append/verify/sync", "security"),
        ("KR 3.4.2", "跨成员一致性对比 + 多数签名仲裁", "security"),
    ]
    for kid, title, owner in o3_krs:
        o3.add_kr(KeyResult(kr_id=kid, title=title, owner=owner))
    registry.register_objective(o3)

    # O4
    o4 = Objective(
        obj_id="O4",
        title="打通 VM 快照与项目快照，实现环境+数据联合可复现",
        description="UnifiedSnapshotManager + libvirt/KVM 适配",
        period=OKRPeriod.Q4,
        owner_domain="vm/snapshot",
    )
    o4_krs = [
        ("KR 4.1.1", "UnifiedSnapshotManager create_unified/restore_unified", "vm_snapshot"),
        ("KR 4.1.2", "VM quiesce→VM snap→WS snap→绑定 unified_id 流程", "vm_snapshot"),
        ("KR 4.1.3", "联合回滚：保护→回滚→自检", "vm_snapshot"),
        ("KR 4.2.1", "VM Adapter 抽象接口定义", "vm_snapshot"),
        ("KR 4.2.2", "libvirt/KVM Adapter 实现", "vm_snapshot"),
        ("KR 4.2.3", "VirtualBox Adapter 实现（可选）", "vm_snapshot"),
    ]
    for kid, title, owner in o4_krs:
        o4.add_kr(KeyResult(kr_id=kid, title=title, owner=owner))
    registry.register_objective(o4)

    # O5
    o5 = Objective(
        obj_id="O5",
        title="接入 NAS/S3 多后端存储池，形成数据保全底座",
        description="StoragePool 抽象 + 3 副本 + 纠删码",
        period=OKRPeriod.Q3,
        owner_domain="storage/nas-pool",
    )
    o5_krs = [
        ("KR 5.1.1", "StoragePool 统一 put/get/stat/list/delete/verify/replicate", "storage"),
        ("KR 5.1.2", "LocalPool 实现", "storage"),
        ("KR 5.1.3", "NASNfsPool / NASSmbPool 实现", "storage"),
        ("KR 5.1.4", "S3Pool 实现", "storage"),
        ("KR 5.2.1", "三副本跨池复制（关键数据）", "storage"),
        ("KR 5.2.2", "Reed-Solomon (4+2) 纠删码编解码+重建", "storage"),
    ]
    for kid, title, owner in o5_krs:
        o5.add_kr(KeyResult(kr_id=kid, title=title, owner=owner))
    registry.register_objective(o5)

    # ---------- 默认 Tasks ----------
    tasks_spec = [
        # Phase 1
        ("T1.1", 1, "O1", "", "创建 OKR spec/checklist/tasks 文档", True),
        ("T1.2", 1, "O1", "", "创建 okr/ 模块：OKR 领域模型与注册"),
        ("T1.3", 1, "O1", "KR 1.1.1", "创建 workspace/ 模块骨架：WorkspaceSnapshotManager 接口"),
        ("T1.4", 1, "O2", "KR 2.1.1", "创建 fs_container/ 模块骨架：VFS Container 接口"),
        ("T1.5", 1, "O4", "KR 4.2.1", "创建 vm_snapshot/ 模块骨架：VM Adapter + UnifiedSnapshotManager"),
        ("T1.6", 1, "O3", "KR 3.1.1", "security 扩展骨架：MerkleTree/BaseXORProber/HashChainLedger"),
        ("T1.7", 1, "O5", "KR 5.1.1", "storage 扩展骨架：NASPool/S3Pool/ErasureCoding"),
        # Phase 2
        ("T2.1", 2, "O1", "KR 1.1.1", "WorkspaceSnapshotManager: create_full_snapshot"),
        ("T2.2", 2, "O1", "KR 1.1.2", "WorkspaceSnapshotManager: create_incremental_snapshot + diff"),
        ("T2.3", 2, "O1", "KR 1.1.3", "Tag/Branch refs 元数据索引"),
        ("T2.4", 2, "O1", "KR 1.2.1", "restore_snapshot：保护快照 + 回滚 + audit log"),
        ("T2.5", 2, "O1", "KR 1.2.3", "GFS 风格保留策略 RetentionPolicy"),
        # Phase 3
        ("T3.1", 3, "O2", "KR 2.1.1", "Container 抽象层 + Layer Stack 数据结构"),
        ("T3.2", 3, "O2", "KR 2.2.1", "OverlayFSBackend 实现"),
        ("T3.3", 3, "O2", "KR 2.2.2", "UserSpaceCOWBackend 纯用户态实现"),
        ("T3.4", 3, "O2", "KR 2.1.3", "commit 生成只读层 + 层 GC"),
        ("T3.5", 3, "O2", "KR 2.3.1", "NASNfsBackend / S3Backend 存储后端接入"),
        # Phase 4
        ("T4.1", 4, "O3", "KR 3.1.1", "MerkleTree：块级树 + 根哈希 + 包含性证明"),
        ("T4.2", 4, "O3", "KR 3.2.1", "ProjectCA：根证书 + 成员证书 + 证书链验证"),
        ("T4.3", 4, "O3", "KR 3.2.2", "SnapshotSigner：成员签名 + CA 链验签"),
        ("T4.4", 4, "O3", "KR 3.3.1", "BaseXORProber：锚点编解码 + 注入提取"),
        ("T4.5", 4, "O3", "KR 3.3.2", "DistributedProber：多 worker 扫描 + 审计报告"),
        ("T4.6", 4, "O3", "KR 3.4.1", "HashChainLedger：append-only + sync + 仲裁"),
        # Phase 5
        ("T5.1", 5, "O4", "KR 4.2.1", "VM Adapter 接口 create/restore/list/delete"),
        ("T5.2", 5, "O4", "KR 4.2.2", "LibvirtKVMAdapter 实现"),
        ("T5.3", 5, "O4", "KR 4.1.2", "UnifiedSnapshotManager.create_unified"),
        ("T5.4", 5, "O4", "KR 4.1.3", "UnifiedSnapshotManager.restore_unified"),
        # Phase 6
        ("T6.1", 6, "O5", "KR 5.1.1", "StoragePool 接口 + LocalPool"),
        ("T6.2", 6, "O5", "KR 5.1.3", "NASNfsPool / NASSmbPool"),
        ("T6.3", 6, "O5", "KR 5.1.4", "S3Pool（Boto3/Minio SDK）"),
        ("T6.4", 6, "O5", "KR 5.2.1", "ReplicationManager：3 副本跨池复制"),
        ("T6.5", 6, "O5", "KR 5.2.2", "ReedSolomonCodec：(4+2) 纠删码 + 重建"),
        # Phase 7
        ("T7.1", 7, "O3", "", "WS→snapshot→Merkle+GPG→HashChain 闭环测试"),
        ("T7.2", 7, "O2", "", "Container 创建→写入→commit→还原 测试"),
        ("T7.3", 7, "O4", "", "VM+Workspace 联合快照回滚测试"),
        ("T7.4", 7, "O3", "KR 3.3.3", "Prober 扫描 + 篡改检测 + 审计报告生成"),
    ]
    for tid, phase, obj, kr, title, *done in tasks_spec:
        t = OKRTask(
            task_id=tid, phase=phase, linked_obj=obj, linked_kr=kr,
            title=title, status=OKRStatus.COMPLETED if done and done[0] else OKRStatus.NOT_STARTED,
            progress=1.0 if done and done[0] else 0.0,
        )
        registry.register_task(t)

    # 标记 T1.1 已完成
    registry.update_task("T1.1", 1.0, status=OKRStatus.COMPLETED, note="spec/checklist/tasks 文档已生成")

    logger.info("[OKR] 默认 OKR 初始化完成: 5 目标, 38 KR, 32 任务")


__all__ = [
    "OKRStatus",
    "OKRPeriod",
    "KeyResult",
    "Objective",
    "OKRTask",
    "OKRProgressEntry",
    "OKRRegistry",
    "bootstrap_default_okr",
]
