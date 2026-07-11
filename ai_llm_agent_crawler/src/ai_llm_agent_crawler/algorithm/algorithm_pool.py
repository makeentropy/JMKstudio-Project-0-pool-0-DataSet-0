"""
算法 POOL 模块

注册表式算法池, 管理可调用算法:
- 用装饰器或显式注册算法, 携带元数据 (类别/标签/复杂度/准确率/版本)
- 按类别/标签/名称检索
- 按指标 (准确率/复杂度) 排序选择最优算法
- 执行追踪 (调用次数/平均耗时/成功失败统计)

适用场景: 为 agent skills gen 提供算法选择能力, 在数据清算/
维度分析等场景按需挑选最合适的算法实现。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class AlgorithmStatus(str, Enum):
    """算法状态。"""

    ACTIVE = "active"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


@dataclass
class ExecutionStat:
    """执行统计。"""

    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0  # 秒
    last_executed_at: Optional[str] = None
    last_error: Optional[str] = None

    @property
    def avg_duration(self) -> float:
        return self.total_duration / self.call_count if self.call_count else 0.0

    @property
    def success_rate(self) -> float:
        return self.success_count / self.call_count if self.call_count else 0.0


@dataclass
class AlgorithmEntry:
    """算法条目。"""

    name: str
    func: Callable[..., Any]
    category: str = "general"
    description: str = ""
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    complexity: str = "O(n)"  # 复杂度标注 (字符串, 用于排序/展示)
    accuracy: float = 0.0  # 准确率/质量分 (0-1, 越高越优)
    priority: int = 0  # 优先级 (越高越优先)
    status: str = AlgorithmStatus.ACTIVE.value
    metadata: Dict[str, Any] = field(default_factory=dict)
    stat: ExecutionStat = field(default_factory=ExecutionStat)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "version": self.version,
            "tags": list(self.tags),
            "complexity": self.complexity,
            "accuracy": self.accuracy,
            "priority": self.priority,
            "status": self.status,
            "metadata": dict(self.metadata),
            "stat": {
                "call_count": self.stat.call_count,
                "success_count": self.stat.success_count,
                "failure_count": self.stat.failure_count,
                "avg_duration": self.stat.avg_duration,
                "success_rate": self.stat.success_rate,
                "last_executed_at": self.stat.last_executed_at,
            },
        }


class AlgorithmPool:
    """
    算法 POOL 注册表

    Example:
        >>> pool = AlgorithmPool()
        >>> @pool.register("dedup_hash", category="dedup", accuracy=0.95)
        ... def dedup_hash(data):
        ...     return list(set(data))
        >>> result = pool.execute("dedup_hash", [1,1,2,3])
        >>> best = pool.select_best(category="dedup")
    """

    def __init__(self) -> None:
        self._entries: Dict[str, AlgorithmEntry] = {}

    # ---------- 注册 ----------

    def register(
        self,
        name: str,
        *,
        category: str = "general",
        description: str = "",
        version: str = "1.0.0",
        tags: Optional[List[str]] = None,
        complexity: str = "O(n)",
        accuracy: float = 0.0,
        priority: int = 0,
        status: str = AlgorithmStatus.ACTIVE.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """装饰器: 注册算法到池中。"""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            entry = AlgorithmEntry(
                name=name,
                func=func,
                category=category,
                description=description or func.__doc__ or "",
                version=version,
                tags=tags or [],
                complexity=complexity,
                accuracy=accuracy,
                priority=priority,
                status=status,
                metadata=metadata or {},
            )
            self.add(entry)
            return func

        return decorator

    def add(self, entry: AlgorithmEntry) -> None:
        """显式添加算法条目。"""
        if entry.name in self._entries:
            logger.warning(f"算法已存在, 覆盖: {entry.name}")
        self._entries[entry.name] = entry
        logger.debug(f"注册算法: {entry.name} (category={entry.category})")

    def remove(self, name: str) -> bool:
        return self._entries.pop(name, None) is not None

    def get(self, name: str) -> Optional[AlgorithmEntry]:
        return self._entries.get(name)

    # ---------- 检索 ----------

    def list_all(self) -> List[AlgorithmEntry]:
        return list(self._entries.values())

    def list_names(self) -> List[str]:
        return list(self._entries.keys())

    def by_category(self, category: str) -> List[AlgorithmEntry]:
        return [e for e in self._entries.values() if e.category == category]

    def by_tag(self, tag: str) -> List[AlgorithmEntry]:
        return [e for e in self._entries.values() if tag in e.tags]

    def search(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
    ) -> List[AlgorithmEntry]:
        """组合条件检索。"""
        results = list(self._entries.values())
        if category:
            results = [e for e in results if e.category == category]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        if status:
            results = [e for e in results if e.status == status]
        return results

    def select_best(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metric: str = "accuracy",  # accuracy | priority
    ) -> Optional[AlgorithmEntry]:
        """
        选择最优算法。

        metric:
        - accuracy: 按 accuracy 降序, 同分按 priority
        - priority: 按 priority 降序, 同分按 accuracy
        仅在 ACTIVE 状态算法中选择。
        """
        candidates = self.search(category=category, tags=tags, status=AlgorithmStatus.ACTIVE.value)
        if not candidates:
            return None
        if metric == "priority":
            return max(candidates, key=lambda e: (e.priority, e.accuracy))
        return max(candidates, key=lambda e: (e.accuracy, e.priority))

    # ---------- 执行 ----------

    def execute(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """执行算法并记录统计。"""
        entry = self._entries.get(name)
        if entry is None:
            raise KeyError(f"算法不存在: {name}")
        if entry.status in (AlgorithmStatus.DISABLED.value, AlgorithmStatus.DEPRECATED.value):
            logger.warning(f"算法 {name} 状态为 {entry.status}, 仍执行")

        start = time.perf_counter()
        try:
            result = entry.func(*args, **kwargs)
            entry.stat.success_count += 1
            entry.stat.last_error = None
            return result
        except Exception as e:
            entry.stat.failure_count += 1
            entry.stat.last_error = str(e)
            logger.error(f"算法 {name} 执行失败: {e}")
            raise
        finally:
            duration = time.perf_counter() - start
            entry.stat.call_count += 1
            entry.stat.total_duration += duration
            entry.stat.last_executed_at = datetime.now().isoformat()

    # ---------- 报告 ----------

    def pool_report(self) -> Dict[str, Any]:
        """池报告。"""
        by_category: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        total_calls = 0
        for e in self._entries.values():
            by_category[e.category] = by_category.get(e.category, 0) + 1
            by_status[e.status] = by_status.get(e.status, 0) + 1
            total_calls += e.stat.call_count
        return {
            "total_algorithms": len(self._entries),
            "by_category": by_category,
            "by_status": by_status,
            "total_calls": total_calls,
            "generated_at": datetime.now().isoformat(),
        }


# 模块级默认池, 便于全局注册
_default_pool = AlgorithmPool()


def register_algorithm(name: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """便捷函数: 注册到默认池。"""
    return _default_pool.register(name, **kwargs)


def get_default_pool() -> AlgorithmPool:
    """获取默认池。"""
    return _default_pool


__all__ = [
    "AlgorithmStatus",
    "ExecutionStat",
    "AlgorithmEntry",
    "AlgorithmPool",
    "register_algorithm",
    "get_default_pool",
]
