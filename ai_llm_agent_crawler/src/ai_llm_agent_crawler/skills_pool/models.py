"""Skills Pool 数据模型。"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class PerformanceMetric:
    """性能指标快照。"""

    elapsed_ms: float
    tokens: int = 0
    memory_mb: float = 0.0
    cpu_pct: float = 0.0
    extra: dict[str, float] = field(default_factory=dict)


@dataclass
class Skill:
    """可沉淀的 skill 条目。"""

    name: str
    description: str = ""
    code: str = ""
    tags: list[str] = field(default_factory=list)
    skill_id: str = field(default_factory=_new_id)
    author: str = "anonymous"
    created_at: float = field(default_factory=time.time)
    likes: int = 0  # 集赞数
    metrics: PerformanceMetric | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "tags": list(self.tags),
            "author": self.author,
            "created_at": self.created_at,
            "likes": self.likes,
            "extra": self.extra,
        }
        if self.metrics:
            d["metrics"] = {
                "elapsed_ms": self.metrics.elapsed_ms,
                "tokens": self.metrics.tokens,
                "memory_mb": self.metrics.memory_mb,
                "cpu_pct": self.metrics.cpu_pct,
            }
        return d


@dataclass
class DatasetEntry:
    """数据集条目（与 skill 关联）。"""

    name: str
    format: str = "json"
    rows: int = 0
    size_bytes: int = 0
    schema: dict[str, Any] = field(default_factory=dict)
    entry_id: str = field(default_factory=_new_id)
    source: str = "manual"
    quality_score: float = 0.0
    created_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "name": self.name,
            "format": self.format,
            "rows": self.rows,
            "size_bytes": self.size_bytes,
            "schema": self.schema,
            "source": self.source,
            "quality_score": self.quality_score,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "extra": self.extra,
        }


@dataclass
class PoolEntry:
    """POOL 中的统一条目（skill 或 dataset）。"""

    kind: str  # "skill" | "dataset"
    ref_id: str
    payload: dict[str, Any]
    likes: int = 0
    added_at: float = field(default_factory=time.time)
    entry_id: str = field(default_factory=_new_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind,
            "ref_id": self.ref_id,
            "likes": self.likes,
            "added_at": self.added_at,
            "payload": self.payload,
        }
