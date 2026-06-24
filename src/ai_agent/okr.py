"""
OKR system for the AI LLM autonomous agent.

Implements Objectives and Key Results for goal tracking.
The agent's autonomous consciousness uses OKRs to measure
progress toward its goals.
"""

import time
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


class OKRStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class KeyResult:
    kr_id: str
    title: str
    description: str = ""
    target_value: float = 1.0
    current_value: float = 0.0
    unit: str = "count"
    status: OKRStatus = OKRStatus.NOT_STARTED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def progress(self) -> float:
        if self.target_value == 0:
            return 1.0 if self.current_value >= 0 else 0.0
        return min(1.0, self.current_value / self.target_value)

    def update_value(self, value: float) -> None:
        self.current_value = value
        self.updated_at = time.time()
        self._update_status()

    def increment(self, amount: float = 1.0) -> None:
        self.current_value += amount
        self.updated_at = time.time()
        self._update_status()

    def _update_status(self) -> None:
        pct = self.progress
        if pct >= 1.0:
            self.status = OKRStatus.COMPLETED
        elif pct >= 0.7:
            self.status = OKRStatus.ON_TRACK
        elif pct >= 0.3:
            self.status = OKRStatus.IN_PROGRESS
        elif pct > 0:
            self.status = OKRStatus.AT_RISK
        else:
            self.status = OKRStatus.NOT_STARTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kr_id": self.kr_id,
            "title": self.title,
            "description": self.description,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "progress": round(self.progress * 100, 1),
            "status": self.status.value,
        }


@dataclass
class Objective:
    obj_id: str
    title: str
    description: str = ""
    key_results: List[KeyResult] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None

    @property
    def progress(self) -> float:
        if not self.key_results:
            return 0.0
        return sum(kr.progress for kr in self.key_results) / len(self.key_results)

    @property
    def status(self) -> OKRStatus:
        if not self.key_results:
            return OKRStatus.NOT_STARTED
        avg = self.progress
        if avg >= 1.0:
            return OKRStatus.COMPLETED
        elif avg >= 0.7:
            return OKRStatus.ON_TRACK
        elif avg >= 0.3:
            return OKRStatus.IN_PROGRESS
        elif avg > 0:
            return OKRStatus.AT_RISK
        return OKRStatus.NOT_STARTED

    def add_key_result(self, kr: KeyResult) -> None:
        self.key_results.append(kr)

    def find_kr(self, kr_id: str) -> Optional[KeyResult]:
        for kr in self.key_results:
            if kr.kr_id == kr_id:
                return kr
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obj_id": self.obj_id,
            "title": self.title,
            "description": self.description,
            "progress": round(self.progress * 100, 1),
            "status": self.status.value,
            "key_results": [kr.to_dict() for kr in self.key_results],
            "deadline": self.deadline,
        }


class OKR:
    """
    OKR management for the autonomous agent.

    Tracks objectives and key results, allowing the agent to
    measure progress toward its goals. Ties into the consciousness
    loop for continuous evaluation.
    """

    def __init__(self, owner: str = "agent"):
        self.owner = owner
        self._objectives: List[Objective] = []
        self._counter = 0

    @property
    def objectives(self) -> List[Objective]:
        return list(self._objectives)

    def create_objective(self, title: str, description: str = "",
                         deadline: Optional[float] = None) -> Objective:
        self._counter += 1
        obj = Objective(
            obj_id=f"obj_{self._counter:04d}",
            title=title,
            description=description,
            deadline=deadline,
        )
        self._objectives.append(obj)
        return obj

    def add_key_result(self, obj_id: str, title: str,
                       target_value: float = 1.0,
                       description: str = "",
                       unit: str = "count") -> Optional[KeyResult]:
        obj = self.find_objective(obj_id)
        if not obj:
            return None
        self._counter += 1
        kr = KeyResult(
            kr_id=f"kr_{self._counter:04d}",
            title=title,
            description=description,
            target_value=target_value,
            unit=unit,
        )
        obj.add_key_result(kr)
        return kr

    def find_objective(self, obj_id: str) -> Optional[Objective]:
        for obj in self._objectives:
            if obj.obj_id == obj_id:
                return obj
        return None

    def update_key_result(self, kr_id: str,
                          value: Optional[float] = None,
                          increment: Optional[float] = None) -> bool:
        for obj in self._objectives:
            kr = obj.find_kr(kr_id)
            if kr:
                if value is not None:
                    kr.update_value(value)
                if increment is not None:
                    kr.increment(increment)
                return True
        return False

    @property
    def overall_progress(self) -> float:
        if not self._objectives:
            return 0.0
        return sum(o.progress for o in self._objectives) / len(self._objectives)

    def summary(self) -> Dict[str, Any]:
        return {
            "owner": self.owner,
            "objectives": len(self._objectives),
            "key_results": sum(len(o.key_results) for o in self._objectives),
            "overall_progress": round(self.overall_progress * 100, 1),
            "objectives_detail": [o.to_dict() for o in self._objectives],
        }
