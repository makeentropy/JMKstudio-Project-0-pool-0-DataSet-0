"""
维度空间数据表系统 - 任务表、事件逻辑表、效率审计表、质能质量子奇点维度空间拓扑数据表

定义数据管理与分析的核心数据表结构，支持任务调度、事件驱动、效率审计和拓扑分析。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(str, Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """任务类型枚举"""
    DATA_CRAWL = "data_crawl"
    DATA_PROCESS = "data_process"
    DATA_VALIDATION = "data_validation"
    DIMENSION_ANALYSIS = "dimension_analysis"
    QUALITY_ASSESSMENT = "quality_assessment"
    SINGULARITY_DETECTION = "singularity_detection"
    MODEL_TRAINING = "model_training"
    SKILL_GENERATION = "skill_generation"
    REPORT_GENERATION = "report_generation"
    CLEANUP = "cleanup"


class EventType(str, Enum):
    """事件类型枚举"""
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"
    DATA_ARRIVAL = "data_arrival"
    QUALITY_ALERT = "quality_alert"
    SINGULARITY_DETECTED = "singularity_detected"
    DIMENSION_SHIFT = "dimension_shift"
    SCHEDULE_TRIGGER = "schedule_trigger"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"


class LogicOperator(str, Enum):
    """逻辑运算符枚举"""
    AND = "and"
    OR = "or"
    XOR = "xor"
    NOT = "not"
    NAND = "nand"
    NOR = "nor"


class AuditLevel(str, Enum):
    """审计级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TopologyType(str, Enum):
    """拓扑结构类型枚举"""
    LINEAR = "linear"
    TREE = "tree"
    GRID = "grid"
    RING = "ring"
    STAR = "star"
    MESH = "mesh"
    HYPERCUBE = "hypercube"
    FRACTAL = "fractal"
    DYNAMIC = "dynamic"


class SingularityConnectionType(str, Enum):
    """奇点连接类型枚举"""
    ENTANGLEMENT = "entanglement"
    RESONANCE = "resonance"
    CASCADE = "cascade"
    REPULSION = "repulsion"
    BALANCE = "balance"


class TaskRecord(BaseModel):
    """任务记录 - 任务表单条记录"""
    task_id: str = Field(..., description="任务唯一标识")
    task_name: str = Field(..., description="任务名称")
    task_type: TaskType = Field(default=TaskType.DATA_PROCESS, description="任务类型")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="任务优先级")

    description: str = Field(default="", description="任务描述")
    tags: List[str] = Field(default_factory=list, description="任务标签")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    deadline: Optional[datetime] = Field(default=None, description="截止时间")
    timeout_seconds: Optional[int] = Field(default=None, ge=0, description="超时时间（秒）")

    executor: str = Field(default="system", description="执行者")
    assignee: Optional[str] = Field(default=None, description="指派负责人")

    dependencies: List[str] = Field(default_factory=list, description="依赖任务ID列表")
    parent_task_id: Optional[str] = Field(default=None, description="父任务ID")
    subtask_ids: List[str] = Field(default_factory=list, description="子任务ID列表")

    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="输出数据")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="任务参数")

    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="进度百分比")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")

    dimension_ref: Optional[str] = Field(default=None, description="关联维度空间ID")
    singularity_ref: Optional[str] = Field(default=None, description="关联奇点ID")
    dataset_ref: Optional[str] = Field(default=None, description="关联数据集ID")

    error_message: Optional[str] = Field(default=None, description="错误信息")
    error_traceback: Optional[str] = Field(default=None, description="错误堆栈")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        use_enum_values = True

    @property
    def duration_seconds(self) -> Optional[float]:
        """任务持续时间（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_active(self) -> bool:
        """任务是否处于活跃状态"""
        return self.status in (TaskStatus.RUNNING, TaskStatus.PAUSED)

    @property
    def is_finished(self) -> bool:
        """任务是否已结束"""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMEOUT,
        )

    def can_start(self, completed_dependencies: List[str]) -> bool:
        """检查任务是否可以启动（所有依赖已完成）"""
        if self.status != TaskStatus.PENDING:
            return False
        return all(dep in completed_dependencies for dep in self.dependencies)


class TaskTable(BaseModel):
    """任务表 - 任务管理与调度数据表"""
    table_id: str = Field(default="task_table_default", description="任务表ID")
    table_name: str = Field(default="任务表", description="任务表名称")
    tasks: Dict[str, TaskRecord] = Field(default_factory=dict, description="任务字典 {task_id: task}")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="表级元数据")

    class Config:
        use_enum_values = True

    def add_task(self, task: TaskRecord) -> None:
        """添加任务"""
        self.tasks[task.task_id] = task
        self.updated_at = datetime.now()

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """获取任务"""
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs) -> bool:
        """更新任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        task.status = status
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.now()
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT):
            task.completed_at = datetime.now()
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self.updated_at = datetime.now()
        return True

    def get_tasks_by_status(self, status: TaskStatus) -> List[TaskRecord]:
        """按状态获取任务列表"""
        return [t for t in self.tasks.values() if t.status == status]

    def get_tasks_by_type(self, task_type: TaskType) -> List[TaskRecord]:
        """按类型获取任务列表"""
        return [t for t in self.tasks.values() if t.task_type == task_type]

    def get_tasks_by_priority(self, priority: TaskPriority) -> List[TaskRecord]:
        """按优先级获取任务列表"""
        return [t for t in self.tasks.values() if t.priority == priority]

    def get_ready_tasks(self) -> List[TaskRecord]:
        """获取可启动的任务（依赖已满足）"""
        completed_ids = {
            tid for tid, t in self.tasks.items()
            if t.status == TaskStatus.COMPLETED
        }
        return [
            t for t in self.tasks.values()
            if t.can_start(list(completed_ids))
        ]

    def get_task_hierarchy(self, task_id: str) -> Dict[str, Any]:
        """获取任务层级结构"""
        task = self.tasks.get(task_id)
        if not task:
            return {}
        return {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "status": task.status,
            "parent": self.get_task_hierarchy(task.parent_task_id) if task.parent_task_id else None,
            "subtasks": [
                self.get_task_hierarchy(stid) for stid in task.subtask_ids
            ],
        }

    @property
    def total_count(self) -> int:
        """总任务数"""
        return len(self.tasks)

    @property
    def completed_count(self) -> int:
        """已完成任务数"""
        return len(self.get_tasks_by_status(TaskStatus.COMPLETED))

    @property
    def success_rate(self) -> float:
        """成功率"""
        finished = [t for t in self.tasks.values() if t.is_finished]
        if not finished:
            return 0.0
        success = [t for t in finished if t.status == TaskStatus.COMPLETED]
        return len(success) / len(finished)


class EventCondition(BaseModel):
    """事件触发条件"""
    event_type: EventType = Field(..., description="事件类型")
    source: Optional[str] = Field(default=None, description="事件来源")
    attribute_filters: Dict[str, Any] = Field(default_factory=dict, description="属性过滤条件")
    threshold: Optional[float] = Field(default=None, description="阈值条件")
    custom_rule: Optional[str] = Field(default=None, description="自定义规则表达式")

    class Config:
        use_enum_values = True


class EventLogicNode(BaseModel):
    """事件逻辑节点"""
    node_id: str = Field(..., description="节点ID")
    node_type: str = Field(default="condition", description="节点类型: condition, operator, action")
    operator: Optional[LogicOperator] = Field(default=None, description="逻辑运算符")
    condition: Optional[EventCondition] = Field(default=None, description="条件（条件节点）")
    children: List[str] = Field(default_factory=list, description="子节点ID列表")
    action: Optional[str] = Field(default=None, description="触发动作（动作节点）")
    description: str = Field(default="", description="节点描述")

    class Config:
        use_enum_values = True


class EventRecord(BaseModel):
    """事件记录"""
    event_id: str = Field(..., description="事件唯一标识")
    event_type: EventType = Field(..., description="事件类型")
    source: str = Field(default="system", description="事件来源")
    timestamp: datetime = Field(default_factory=datetime.now, description="发生时间")

    severity: AuditLevel = Field(default=AuditLevel.INFO, description="事件严重程度")
    title: str = Field(default="", description="事件标题")
    description: str = Field(default="", description="事件描述")

    payload: Dict[str, Any] = Field(default_factory=dict, description="事件数据载荷")
    related_task_id: Optional[str] = Field(default=None, description="关联任务ID")
    related_singularity_id: Optional[str] = Field(default=None, description="关联奇点ID")
    related_dimension: Optional[str] = Field(default=None, description="关联维度")

    processed: bool = Field(default=False, description="是否已处理")
    processed_at: Optional[datetime] = Field(default=None, description="处理时间")
    processing_result: Optional[str] = Field(default=None, description="处理结果")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        use_enum_values = True

    def mark_processed(self, result: str = "success") -> None:
        """标记为已处理"""
        self.processed = True
        self.processed_at = datetime.now()
        self.processing_result = result


class EventLogicTable(BaseModel):
    """事件逻辑表 - 事件驱动逻辑与流程控制表"""
    table_id: str = Field(default="event_logic_table_default", description="事件逻辑表ID")
    table_name: str = Field(default="事件逻辑表", description="事件逻辑表名称")

    events: Dict[str, EventRecord] = Field(default_factory=dict, description="事件记录字典")
    logic_nodes: Dict[str, EventLogicNode] = Field(default_factory=dict, description="逻辑节点字典")

    event_handlers: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="事件类型到处理动作的映射 {event_type: [action_ids]}"
    )

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="表级元数据")

    class Config:
        use_enum_values = True

    def add_event(self, event: EventRecord) -> None:
        """添加事件记录"""
        self.events[event.event_id] = event
        self.updated_at = datetime.now()

    def add_logic_node(self, node: EventLogicNode) -> None:
        """添加逻辑节点"""
        self.logic_nodes[node.node_id] = node
        self.updated_at = datetime.now()

    def register_handler(self, event_type: EventType, action_id: str) -> None:
        """注册事件处理器"""
        if event_type.value not in self.event_handlers:
            self.event_handlers[event_type.value] = []
        if action_id not in self.event_handlers[event_type.value]:
            self.event_handlers[event_type.value].append(action_id)
        self.updated_at = datetime.now()

    def evaluate_condition(self, condition: EventCondition, event: EventRecord) -> bool:
        """评估条件是否满足"""
        if event.event_type != condition.event_type:
            return False

        if condition.source and event.source != condition.source:
            return False

        for key, expected_value in condition.attribute_filters.items():
            actual_value = event.payload.get(key)
            if actual_value != expected_value:
                return False

        if condition.threshold is not None:
            value = event.payload.get("value", 0)
            if isinstance(value, (int, float)):
                if value < condition.threshold:
                    return False

        return True

    def evaluate_logic_node(self, node_id: str, event: EventRecord) -> bool:
        """评估逻辑节点"""
        node = self.logic_nodes.get(node_id)
        if not node:
            return False

        if node.node_type == "condition" and node.condition:
            return self.evaluate_condition(node.condition, event)

        if node.node_type == "operator" and node.operator:
            child_results = [
                self.evaluate_logic_node(child_id, event)
                for child_id in node.children
            ]
            if node.operator == LogicOperator.AND:
                return all(child_results)
            elif node.operator == LogicOperator.OR:
                return any(child_results)
            elif node.operator == LogicOperator.XOR:
                return sum(child_results) == 1
            elif node.operator == LogicOperator.NOT:
                return not child_results[0] if child_results else False
            elif node.operator == LogicOperator.NAND:
                return not all(child_results)
            elif node.operator == LogicOperator.NOR:
                return not any(child_results)

        return False

    def get_unprocessed_events(self) -> List[EventRecord]:
        """获取未处理事件"""
        return [e for e in self.events.values() if not e.processed]

    def get_events_by_type(self, event_type: EventType) -> List[EventRecord]:
        """按类型获取事件"""
        return [e for e in self.events.values() if e.event_type == event_type]

    def get_events_by_severity(self, severity: AuditLevel) -> List[EventRecord]:
        """按严重程度获取事件"""
        return [e for e in self.events.values() if e.severity == severity]

    @property
    def total_events(self) -> int:
        """总事件数"""
        return len(self.events)

    @property
    def unprocessed_count(self) -> int:
        """未处理事件数"""
        return len(self.get_unprocessed_events())


class ResourceUsage(BaseModel):
    """资源使用情况"""
    cpu_usage_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="CPU使用率%")
    memory_usage_mb: float = Field(default=0.0, ge=0.0, description="内存使用量(MB)")
    memory_usage_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="内存使用率%")
    disk_io_read_mb: float = Field(default=0.0, ge=0.0, description="磁盘读(MB)")
    disk_io_write_mb: float = Field(default=0.0, ge=0.0, description="磁盘写(MB)")
    network_io_in_mb: float = Field(default=0.0, ge=0.0, description="网络入站(MB)")
    network_io_out_mb: float = Field(default=0.0, ge=0.0, description="网络出站(MB)")
    gpu_usage_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="GPU使用率%")

    class Config:
        use_enum_values = True

    @property
    def total_io_mb(self) -> float:
        """总IO量"""
        return (
            self.disk_io_read_mb + self.disk_io_write_mb
            + self.network_io_in_mb + self.network_io_out_mb
        )


class QualityMetrics(BaseModel):
    """质量指标摘要"""
    data_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="数据质量评分")
    completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="完整性")
    accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="准确性")
    consistency: float = Field(default=0.0, ge=0.0, le=1.0, description="一致性")
    efficiency_score: float = Field(default=0.0, ge=0.0, le=1.0, description="效率评分")

    class Config:
        use_enum_values = True


class EfficiencyAuditRecord(BaseModel):
    """效率审计记录"""
    audit_id: str = Field(..., description="审计唯一标识")
    audit_level: AuditLevel = Field(default=AuditLevel.INFO, description="审计级别")
    target_type: str = Field(default="task", description="审计目标类型: task, event, dataset, dimension, singularity")
    target_id: str = Field(..., description="审计目标ID")
    target_name: str = Field(default="", description="审计目标名称")

    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    ended_at: Optional[datetime] = Field(default=None, description="结束时间")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="持续时间（秒）")

    resource_usage: ResourceUsage = Field(default_factory=ResourceUsage, description="资源使用情况")
    peak_resource: ResourceUsage = Field(default_factory=ResourceUsage, description="资源峰值")

    input_count: int = Field(default=0, ge=0, description="输入数据量")
    output_count: int = Field(default=0, ge=0, description="输出数据量")
    error_count: int = Field(default=0, ge=0, description="错误数量")
    warning_count: int = Field(default=0, ge=0, description="警告数量")

    quality_metrics: QualityMetrics = Field(default_factory=QualityMetrics, description="质量指标")

    success: bool = Field(default=True, description="是否成功")
    status: str = Field(default="completed", description="状态")

    efficiency_ratio: float = Field(default=0.0, description="效率比率（产出/投入）")
    cost_effectiveness: float = Field(default=0.0, description="成本效益")
    throughput: float = Field(default=0.0, description="吞吐量（单位时间处理量）")

    bottlenecks: List[str] = Field(default_factory=list, description="瓶颈点列表")
    optimization_suggestions: List[str] = Field(default_factory=list, description="优化建议")

    operator: str = Field(default="system", description="操作人员")
    description: str = Field(default="", description="审计描述")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        use_enum_values = True

    @model_validator(mode="after")
    def calculate_derived(self) -> "EfficiencyAuditRecord":
        """计算派生指标"""
        if self.ended_at and not self.duration_seconds:
            self.duration_seconds = (self.ended_at - self.started_at).total_seconds()

        if self.duration_seconds > 0 and self.output_count > 0:
            self.throughput = self.output_count / self.duration_seconds

        if self.input_count > 0:
            self.efficiency_ratio = self.output_count / self.input_count

        return self

    def complete(self, success: bool = True, **kwargs) -> None:
        """完成审计记录"""
        self.ended_at = datetime.now()
        self.duration_seconds = (self.ended_at - self.started_at).total_seconds()
        self.success = success
        self.status = "completed" if success else "failed"
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class EfficiencyAuditTable(BaseModel):
    """效率审计表 - 性能监控与效率审计数据表"""
    table_id: str = Field(default="efficiency_audit_table_default", description="效率审计表ID")
    table_name: str = Field(default="效率审计表", description="效率审计表名称")

    audits: Dict[str, EfficiencyAuditRecord] = Field(default_factory=dict, description="审计记录字典")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="表级元数据")

    class Config:
        use_enum_values = True

    def add_audit(self, audit: EfficiencyAuditRecord) -> None:
        """添加审计记录"""
        self.audits[audit.audit_id] = audit
        self.updated_at = datetime.now()

    def get_audit(self, audit_id: str) -> Optional[EfficiencyAuditRecord]:
        """获取审计记录"""
        return self.audits.get(audit_id)

    def get_audits_by_target(self, target_id: str) -> List[EfficiencyAuditRecord]:
        """按目标ID获取审计记录"""
        return [a for a in self.audits.values() if a.target_id == target_id]

    def get_audits_by_target_type(self, target_type: str) -> List[EfficiencyAuditRecord]:
        """按目标类型获取审计记录"""
        return [a for a in self.audits.values() if a.target_type == target_type]

    def get_audits_by_level(self, level: AuditLevel) -> List[EfficiencyAuditRecord]:
        """按审计级别获取记录"""
        return [a for a in self.audits.values() if a.audit_level == level]

    def get_average_duration(self, target_type: Optional[str] = None) -> float:
        """获取平均持续时间"""
        audits = list(self.audits.values())
        if target_type:
            audits = [a for a in audits if a.target_type == target_type]
        if not audits:
            return 0.0
        return sum(a.duration_seconds for a in audits) / len(audits)

    def get_average_efficiency(self, target_type: Optional[str] = None) -> float:
        """获取平均效率比率"""
        audits = list(self.audits.values())
        if target_type:
            audits = [a for a in audits if a.target_type == target_type]
        if not audits:
            return 0.0
        return sum(a.efficiency_ratio for a in audits) / len(audits)

    def get_success_rate(self, target_type: Optional[str] = None) -> float:
        """获取成功率"""
        audits = list(self.audits.values())
        if target_type:
            audits = [a for a in audits if a.target_type == target_type]
        if not audits:
            return 0.0
        success = [a for a in audits if a.success]
        return len(success) / len(audits)

    def get_bottlenecks_summary(self, top_n: int = 10) -> Dict[str, int]:
        """获取瓶颈点统计"""
        counter: Dict[str, int] = {}
        for audit in self.audits.values():
            for bottleneck in audit.bottlenecks:
                counter[bottleneck] = counter.get(bottleneck, 0) + 1
        sorted_bottlenecks = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_bottlenecks[:top_n])

    @property
    def total_audits(self) -> int:
        """总审计记录数"""
        return len(self.audits)


class DimensionTopologyNode(BaseModel):
    """维度拓扑节点"""
    node_id: str = Field(..., description="节点ID")
    dimension_type: str = Field(..., description="维度类型")
    coordinates: List[float] = Field(default_factory=list, description="维度空间坐标")
    mass: float = Field(default=1.0, ge=0.0, description="节点质量（数据量）")
    energy: float = Field(default=0.0, ge=0.0, description="节点能量（信息价值）")
    entropy: float = Field(default=0.0, ge=0.0, description="熵值")
    stability: float = Field(default=1.0, ge=0.0, le=1.0, description="稳定性")
    singularity_ids: List[str] = Field(default_factory=list, description="关联奇点ID列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        use_enum_values = True

    @property
    def effective_mass(self) -> float:
        """有效质量 = 质量 × 稳定性"""
        return self.mass * self.stability

    @property
    def mass_energy_ratio(self) -> float:
        """质能比"""
        if self.mass == 0:
            return 0.0
        return self.energy / self.mass


class SingularityTopologyNode(BaseModel):
    """奇点拓扑节点"""
    singularity_id: str = Field(..., description="奇点ID")
    singularity_type: str = Field(..., description="奇点类型")
    severity: str = Field(default="medium", description="严重程度")
    position: List[float] = Field(default_factory=list, description="维度空间位置")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="奇点强度")
    radius: float = Field(default=1.0, ge=0.0, description="影响半径")
    mass: float = Field(default=0.0, ge=0.0, description="奇点质量")
    energy: float = Field(default=0.0, ge=0.0, description="奇点能量")
    spin: float = Field(default=0.0, description="自旋值")
    charge: float = Field(default=0.0, description="电荷值")
    connected_singularities: List[str] = Field(default_factory=list, description="连接的奇点ID列表")
    affected_dimensions: List[str] = Field(default_factory=list, description="受影响的维度ID列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        use_enum_values = True

    @property
    def influence_area(self) -> float:
        """影响面积（πr²）"""
        return 3.141592653589793 * self.radius ** 2


class SingularityConnection(BaseModel):
    """奇点连接关系"""
    connection_id: str = Field(..., description="连接ID")
    source_id: str = Field(..., description="源奇点ID")
    target_id: str = Field(..., description="目标奇点ID")
    connection_type: SingularityConnectionType = Field(
        default=SingularityConnectionType.ENTANGLEMENT,
        description="连接类型"
    )
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="连接强度")
    distance: float = Field(default=0.0, ge=0.0, description="空间距离")
    resonance_frequency: float = Field(default=0.0, ge=0.0, description="共振频率")
    phase_shift: float = Field(default=0.0, description="相位偏移")
    bidirectional: bool = Field(default=True, description="是否双向")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        use_enum_values = True


class TopologyMetrics(BaseModel):
    """拓扑度量指标"""
    total_dimensions: int = Field(default=0, description="总维度节点数")
    total_singularities: int = Field(default=0, description="总奇点数")
    total_connections: int = Field(default=0, description="总连接数")
    connectivity: float = Field(default=0.0, ge=0.0, le=1.0, description="连通度")
    average_degree: float = Field(default=0.0, description="平均度数")
    diameter: float = Field(default=0.0, description="拓扑直径")
    density: float = Field(default=0.0, ge=0.0, description="空间密度")
    entropy: float = Field(default=0.0, ge=0.0, description="系统熵")
    total_mass: float = Field(default=0.0, ge=0.0, description="总质量")
    total_energy: float = Field(default=0.0, ge=0.0, description="总能量")
    stability_index: float = Field(default=1.0, ge=0.0, le=1.0, description="稳定指数")
    singularity_density: float = Field(default=0.0, description="奇点密度")
    criticality: float = Field(default=0.0, ge=0.0, le=1.0, description="临界度（接近奇点的程度）")

    class Config:
        use_enum_values = True


class MassEnergySingularityTopologyTable(BaseModel):
    """质能质量子奇点维度空间拓扑数据表

    管理维度空间中奇点的拓扑结构、质能分布和连接关系。
    """
    table_id: str = Field(
        default="mass_energy_singularity_topology_default",
        description="拓扑数据表ID"
    )
    table_name: str = Field(
        default="质能质量子奇点维度空间拓扑数据表",
        description="表名称"
    )
    topology_type: TopologyType = Field(default=TopologyType.DYNAMIC, description="拓扑结构类型")
    dimension_count: int = Field(default=3, ge=1, description="空间维度数")

    dimension_nodes: Dict[str, DimensionTopologyNode] = Field(
        default_factory=dict, description="维度节点字典 {node_id: node}"
    )
    singularity_nodes: Dict[str, SingularityTopologyNode] = Field(
        default_factory=dict, description="奇点节点字典 {singularity_id: node}"
    )
    connections: Dict[str, SingularityConnection] = Field(
        default_factory=dict, description="连接关系字典 {connection_id: connection}"
    )

    metrics: TopologyMetrics = Field(default_factory=TopologyMetrics, description="拓扑度量指标")
    boundaries: List[Tuple[float, float]] = Field(
        default_factory=list,
        description="各维度边界 [(min, max), ...]"
    )
    center: List[float] = Field(default_factory=list, description="空间中心点坐标")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="表级元数据")

    class Config:
        use_enum_values = True

    def add_dimension_node(self, node: DimensionTopologyNode) -> None:
        """添加维度节点"""
        self.dimension_nodes[node.node_id] = node
        self._recalculate_metrics()
        self.updated_at = datetime.now()

    def add_singularity_node(self, node: SingularityTopologyNode) -> None:
        """添加奇点节点"""
        self.singularity_nodes[node.singularity_id] = node
        self._recalculate_metrics()
        self.updated_at = datetime.now()

    def add_connection(self, connection: SingularityConnection) -> None:
        """添加奇点连接"""
        self.connections[connection.connection_id] = connection
        if connection.source_id in self.singularity_nodes:
            src = self.singularity_nodes[connection.source_id]
            if connection.target_id not in src.connected_singularities:
                src.connected_singularities.append(connection.target_id)
        if connection.target_id in self.singularity_nodes and connection.bidirectional:
            tgt = self.singularity_nodes[connection.target_id]
            if connection.source_id not in tgt.connected_singularities:
                tgt.connected_singularities.append(connection.source_id)
        self._recalculate_metrics()
        self.updated_at = datetime.now()

    def remove_singularity(self, singularity_id: str) -> bool:
        """移除奇点及其连接"""
        if singularity_id not in self.singularity_nodes:
            return False
        del self.singularity_nodes[singularity_id]
        to_remove = [
            cid for cid, conn in self.connections.items()
            if conn.source_id == singularity_id or conn.target_id == singularity_id
        ]
        for cid in to_remove:
            del self.connections[cid]
        for node in self.singularity_nodes.values():
            if singularity_id in node.connected_singularities:
                node.connected_singularities.remove(singularity_id)
        self._recalculate_metrics()
        self.updated_at = datetime.now()
        return True

    def get_singularities_by_type(self, singularity_type: str) -> List[SingularityTopologyNode]:
        """按类型获取奇点"""
        return [s for s in self.singularity_nodes.values() if s.singularity_type == singularity_type]

    def get_singularities_by_severity(self, severity: str) -> List[SingularityTopologyNode]:
        """按严重程度获取奇点"""
        return [s for s in self.singularity_nodes.values() if s.severity == severity]

    def get_connections_for_singularity(self, singularity_id: str) -> List[SingularityConnection]:
        """获取奇点的所有连接"""
        return [
            c for c in self.connections.values()
            if c.source_id == singularity_id or c.target_id == singularity_id
        ]

    def calculate_distance(
        self, pos1: List[float], pos2: List[float]
    ) -> float:
        """计算两点间的欧氏距离"""
        if len(pos1) != len(pos2):
            return float('inf')
        return float(np.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2))))

    def find_nearby_singularities(
        self, position: List[float], radius: float
    ) -> List[Tuple[SingularityTopologyNode, float]]:
        """查找指定范围内的奇点"""
        nearby = []
        for node in self.singularity_nodes.values():
            dist = self.calculate_distance(position, node.position)
            if dist <= radius:
                nearby.append((node, dist))
        nearby.sort(key=lambda x: x[1])
        return nearby

    def get_adjacency_matrix(self) -> np.ndarray:
        """获取邻接矩阵"""
        singularity_ids = list(self.singularity_nodes.keys())
        n = len(singularity_ids)
        matrix = np.zeros((n, n), dtype=float)
        id_to_idx = {sid: i for i, sid in enumerate(singularity_ids)}

        for conn in self.connections.values():
            i = id_to_idx.get(conn.source_id)
            j = id_to_idx.get(conn.target_id)
            if i is not None and j is not None:
                matrix[i][j] = conn.strength
                if conn.bidirectional:
                    matrix[j][i] = conn.strength

        return matrix

    def _recalculate_metrics(self) -> None:
        """重新计算拓扑度量指标"""
        metrics = self.metrics
        metrics.total_dimensions = len(self.dimension_nodes)
        metrics.total_singularities = len(self.singularity_nodes)
        metrics.total_connections = len(self.connections)

        if metrics.total_singularities > 0:
            total_degree = sum(
                len(s.connected_singularities) for s in self.singularity_nodes.values()
            )
            metrics.average_degree = total_degree / metrics.total_singularities
            max_connections = metrics.total_singularities * (metrics.total_singularities - 1)
            if max_connections > 0:
                metrics.connectivity = (
                    metrics.total_connections * 2 / max_connections
                    if metrics.total_connections > 0 else 0.0
                )

        metrics.total_mass = sum(n.mass for n in self.dimension_nodes.values()) + sum(
            s.mass for s in self.singularity_nodes.values()
        )
        metrics.total_energy = sum(n.energy for n in self.dimension_nodes.values()) + sum(
            s.energy for s in self.singularity_nodes.values()
        )

        high_severity = [s for s in self.singularity_nodes.values() if s.severity in ("high", "critical")]
        metrics.criticality = min(
            len(high_severity) / max(metrics.total_singularities, 1), 1.0
        )

        avg_stability = (
            sum(n.stability for n in self.dimension_nodes.values()) / metrics.total_dimensions
            if metrics.total_dimensions > 0 else 1.0
        )
        metrics.stability_index = max(0.0, min(1.0, avg_stability * (1.0 - metrics.criticality * 0.5)))

    @property
    def is_critical(self) -> bool:
        """系统是否处于临界状态"""
        return self.metrics.criticality > 0.7

    @property
    def critical_singularity_count(self) -> int:
        """严重奇点数量"""
        return len([
            s for s in self.singularity_nodes.values()
            if s.severity in ("high", "critical")
        ])
