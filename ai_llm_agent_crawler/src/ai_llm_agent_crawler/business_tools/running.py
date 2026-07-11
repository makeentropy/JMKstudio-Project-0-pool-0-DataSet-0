"""跑步追踪工具。"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class RunRecord:
    """一次跑步记录。"""

    distance_km: float
    duration_s: float
    avg_heart_rate: int = 0
    weight_kg: float = 65.0
    timestamp: float = field(default_factory=time.time)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    note: str = ""

    @property
    def pace_sec_per_km(self) -> float:
        return self.duration_s / self.distance_km if self.distance_km > 0 else 0.0

    @property
    def speed_kmh(self) -> float:
        return (self.distance_km / self.duration_s) * 3600 if self.duration_s > 0 else 0.0

    @property
    def calories(self) -> float:
        """基于体重与距离的近似卡路里消耗。"""
        if self.avg_heart_rate > 0:
            # 简化估算：0.634 * HR - 0.4505 (per minute) + 距离系数
            minutes = self.duration_s / 60.0
            return round(
                (0.634 * self.avg_heart_rate - 0.4505) * self.weight_kg * minutes / 200 + 1.0,
                2,
            )
        return round(self.distance_km * self.weight_kg * 1.03, 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pace_sec_per_km"] = round(self.pace_sec_per_km, 2)
        d["speed_kmh"] = round(self.speed_kmh, 2)
        d["calories"] = self.calories
        return d


class RunningTracker:
    """跑步追踪器。"""

    def __init__(self) -> None:
        self._records: list[RunRecord] = []

    def add(self, record: RunRecord) -> RunRecord:
        if record.distance_km <= 0:
            raise ValueError("distance_km 必须为正")
        if record.duration_s <= 0:
            raise ValueError("duration_s 必须为正")
        self._records.append(record)
        return record

    def add_simple(self, distance_km: float, duration_s: float, **kwargs: Any) -> RunRecord:
        return self.add(RunRecord(distance_km=distance_km, duration_s=duration_s, **kwargs))

    def list_runs(self) -> list[RunRecord]:
        return list(self._records)

    def summary(self) -> dict[str, Any]:
        if not self._records:
            return {"count": 0, "total_km": 0.0, "total_calories": 0.0}
        total_km = sum(r.distance_km for r in self._records)
        total_s = sum(r.duration_s for r in self._records)
        total_cal = sum(r.calories for r in self._records)
        avg_pace = total_s / total_km if total_km > 0 else 0.0
        return {
            "count": len(self._records),
            "total_km": round(total_km, 3),
            "total_duration_s": round(total_s, 1),
            "total_calories": round(total_cal, 2),
            "avg_pace_sec_per_km": round(avg_pace, 2),
        }

    def to_dict(self) -> dict[str, Any]:
        return {"runs": [r.to_dict() for r in self._records], "summary": self.summary()}
