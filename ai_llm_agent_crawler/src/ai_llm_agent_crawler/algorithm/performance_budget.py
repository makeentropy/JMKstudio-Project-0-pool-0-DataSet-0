"""
系统性能预算模块

对系统资源 (CPU / 内存 / 磁盘 IO / 网络) 建立预算与跟踪:
- 为每类资源设定预算上限 (budget)
- 记录实际使用 (usage), 判定状态 (normal/warning/exceeded)
- 汇总预算健康度报告, 触发告警回调
- 支持预留 (reserve) 与超支检查

不依赖运行时采样库, 通过外部调用 record() 上报指标,
便于在爬虫/数据处理管线中集成。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ResourceKind(str, Enum):
    """资源种类。"""

    CPU = "cpu"  # CPU 使用率 (%)
    MEMORY = "memory"  # 内存 (bytes)
    DISK = "disk"  # 磁盘空间 (bytes)
    DISK_IO = "disk_io"  # 磁盘 IO 吞吐 (bytes/s)
    NETWORK = "network"  # 网络带宽 (bytes/s)
    CONCURRENCY = "concurrency"  # 并发数 (整数)
    FILE_HANDLES = "file_handles"  # 文件句柄数 (整数)


class BudgetStatus(str, Enum):
    """预算状态。"""

    NORMAL = "normal"  # 正常 (低于 warning 阈值)
    WARNING = "warning"  # 警告 (达到 warning, 未超过 limit)
    EXCEEDED = "exceeded"  # 超支 (超过 limit)
    UNKNOWN = "unknown"  # 未知


@dataclass
class ResourceBudget:
    """
    单类资源预算

    Args:
        kind: 资源种类
        limit: 硬上限 (超过即为 exceeded)
        warning: 警告阈值 (默认 limit 的 80%)
        reserve: 预留量 (实际可用 = limit - reserve)
        unit: 单位标签 (仅用于展示)
    """

    kind: ResourceKind
    limit: float
    warning: Optional[float] = None
    reserve: float = 0.0
    unit: str = ""

    def __post_init__(self) -> None:
        if self.warning is None:
            self.warning = self.limit * 0.8

    @property
    def usable(self) -> float:
        """实际可用 = limit - reserve。"""
        return max(0.0, self.limit - self.reserve)

    def evaluate(self, usage: float) -> BudgetStatus:
        """根据使用量评估状态。"""
        if usage >= self.limit:
            return BudgetStatus.EXCEEDED
        if usage >= (self.warning or self.limit):
            return BudgetStatus.WARNING
        return BudgetStatus.NORMAL


class UsageRecord(BaseModel):
    """单次使用记录。"""

    kind: ResourceKind
    usage: float = Field(..., description="使用量")
    timestamp: datetime = Field(default_factory=datetime.now)
    label: str = Field(default="", description="来源标签")
    status: BudgetStatus = Field(default=BudgetStatus.UNKNOWN)


class PerformanceBudget:
    """
    性能预算管理器

    管理多类资源的预算, 记录使用, 评估状态, 触发告警。

    Example:
        >>> pb = PerformanceBudget()
        >>> pb.set_budget(ResourceKind.CPU, limit=80.0, unit="%")
        >>> pb.set_budget(ResourceKind.MEMORY, limit=8 * 1024**3, unit="bytes")
        >>> status = pb.record(ResourceKind.CPU, 75.0, label="crawler")
        >>> report = pb.health_report()
    """

    def __init__(self) -> None:
        self._budgets: Dict[ResourceKind, ResourceBudget] = {}
        self._history: Dict[ResourceKind, List[UsageRecord]] = {}
        self._alerts: List[UsageRecord] = []
        self._alert_handlers: List[Callable[[UsageRecord], None]] = []
        self._latest: Dict[ResourceKind, UsageRecord] = {}

    # ---------- 预算配置 ----------

    def set_budget(
        self,
        kind: ResourceKind,
        limit: float,
        warning: Optional[float] = None,
        reserve: float = 0.0,
        unit: str = "",
    ) -> ResourceBudget:
        """设置/更新某类资源预算。"""
        budget = ResourceBudget(kind=kind, limit=limit, warning=warning, reserve=reserve, unit=unit)
        self._budgets[kind] = budget
        self._history.setdefault(kind, [])
        logger.debug(f"设置预算: {kind.value} limit={limit} {unit}")
        return budget

    def get_budget(self, kind: ResourceKind) -> Optional[ResourceBudget]:
        return self._budgets.get(kind)

    def remove_budget(self, kind: ResourceKind) -> bool:
        return self._budgets.pop(kind, None) is not None

    # ---------- 使用记录 ----------

    def record(self, kind: ResourceKind, usage: float, label: str = "") -> BudgetStatus:
        """
        记录一次资源使用, 返回评估状态。

        若未设置预算, 状态为 UNKNOWN。
        超出 warning/exceeded 时触发告警回调。
        """
        budget = self._budgets.get(kind)
        if budget is None:
            status = BudgetStatus.UNKNOWN
        else:
            status = budget.evaluate(usage)

        rec = UsageRecord(kind=kind, usage=usage, label=label, status=status)
        self._history.setdefault(kind, []).append(rec)
        self._latest[kind] = rec

        if status in (BudgetStatus.WARNING, BudgetStatus.EXCEEDED):
            self._alerts.append(rec)
            for handler in self._alert_handlers:
                try:
                    handler(rec)
                except Exception as e:
                    logger.error(f"告警回调失败: {e}")
            logger.warning(f"预算告警: {kind.value} usage={usage} status={status.value}")

        return status

    def latest(self, kind: ResourceKind) -> Optional[UsageRecord]:
        return self._latest.get(kind)

    def history(self, kind: ResourceKind, limit: Optional[int] = None) -> List[UsageRecord]:
        h = self._history.get(kind, [])
        if limit:
            return h[-limit:]
        return list(h)

    # ---------- 告警 ----------

    def add_alert_handler(self, handler: Callable[[UsageRecord], None]) -> None:
        self._alert_handlers.append(handler)

    def alerts(self, clear: bool = False) -> List[UsageRecord]:
        alerts = list(self._alerts)
        if clear:
            self._alerts.clear()
        return alerts

    # ---------- 报告 ----------

    def health_report(self) -> Dict[str, Any]:
        """整体预算健康度报告。"""
        resources: List[Dict[str, Any]] = []
        worst = BudgetStatus.NORMAL
        severity = {BudgetStatus.NORMAL: 0, BudgetStatus.WARNING: 1, BudgetStatus.EXCEEDED: 2, BudgetStatus.UNKNOWN: -1}
        for kind, budget in self._budgets.items():
            latest = self._latest.get(kind)
            status = latest.status if latest else BudgetStatus.UNKNOWN
            usage = latest.usage if latest else 0.0
            if severity.get(status, -1) > severity.get(worst, -1):
                worst = status
            resources.append({
                "kind": kind.value,
                "limit": budget.limit,
                "warning": budget.warning,
                "reserve": budget.reserve,
                "usable": budget.usable,
                "usage": usage,
                "unit": budget.unit,
                "status": status.value,
                "utilization": (usage / budget.limit) if budget.limit else 0.0,
            })
        return {
            "overall_status": worst.value,
            "resource_count": len(self._budgets),
            "alert_count": len(self._alerts),
            "resources": resources,
            "generated_at": datetime.now().isoformat(),
        }

    def check_can_allocate(self, kind: ResourceKind, amount: float) -> bool:
        """检查是否还能分配 amount 资源 (基于最新使用量)。"""
        budget = self._budgets.get(kind)
        if budget is None:
            return True
        latest = self._latest.get(kind)
        current = latest.usage if latest else 0.0
        return (current + amount) <= budget.usable

    def remaining(self, kind: ResourceKind) -> Optional[float]:
        """返回剩余可用 (limit - reserve - current)。"""
        budget = self._budgets.get(kind)
        if budget is None:
            return None
        latest = self._latest.get(kind)
        current = latest.usage if latest else 0.0
        return max(0.0, budget.usable - current)


__all__ = [
    "ResourceKind",
    "BudgetStatus",
    "ResourceBudget",
    "UsageRecord",
    "PerformanceBudget",
]
