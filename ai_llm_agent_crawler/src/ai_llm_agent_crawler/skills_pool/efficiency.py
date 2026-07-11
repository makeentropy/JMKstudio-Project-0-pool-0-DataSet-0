"""省效率跟踪器。"""

from __future__ import annotations

import threading
from dataclasses import asdict
from typing import Any

from ai_llm_agent_crawler.llm_engine.models import EfficiencyIteration


class EfficiencyTracker:
    """跟踪迭代省效率版本，汇总加速比与累计节省。

    与 :class:`ai_llm_agent_crawler.llm_engine.FullAuditAgent` 协同：
    full agent 生成的 :class:`EfficiencyIteration` 沉淀到此 tracker，
    形成「开放性能效率 POOL」的效率视图。
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._iterations: list[EfficiencyIteration] = []

    def record(self, iteration: EfficiencyIteration) -> EfficiencyIteration:
        with self._lock:
            self._iterations.append(iteration)
            return iteration

    def record_raw(
        self,
        version: str,
        baseline_ms: float,
        optimized_ms: float,
        changes: list[str] | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> EfficiencyIteration:
        savings = (
            (baseline_ms - optimized_ms) / baseline_ms if baseline_ms > 0 else 0.0
        )
        it = EfficiencyIteration(
            version=version,
            baseline_ms=baseline_ms,
            optimized_ms=optimized_ms,
            savings_ratio=round(savings, 4),
            changes=changes or [],
            snapshot=snapshot or {},
        )
        return self.record(it)

    # ------------------------------------------------------------------ query
    def list_iterations(self) -> list[EfficiencyIteration]:
        with self._lock:
            return list(self._iterations)

    def best_speedup(self) -> float:
        with self._lock:
            return max((it.speedup for it in self._iterations), default=0.0)

    def total_savings_ms(self) -> float:
        with self._lock:
            return sum(it.baseline_ms - it.optimized_ms for it in self._iterations)

    def avg_savings_ratio(self) -> float:
        with self._lock:
            if not self._iterations:
                return 0.0
            return sum(it.savings_ratio for it in self._iterations) / len(self._iterations)

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "count": len(self._iterations),
                "best_speedup": round(self.best_speedup(), 4),
                "total_savings_ms": round(self.total_savings_ms(), 3),
                "avg_savings_ratio": round(self.avg_savings_ratio(), 4),
                "iterations": [asdict(it) for it in self._iterations],
            }
