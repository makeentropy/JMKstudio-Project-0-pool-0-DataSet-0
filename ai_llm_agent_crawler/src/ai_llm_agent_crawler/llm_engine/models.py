"""LLM 引擎数据模型。"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChatRole(str, Enum):
    """对话角色。"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """对话消息。"""

    role: ChatRole
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatMessage:
        return cls(
            role=ChatRole(data["role"]),
            content=data["content"],
            name=data.get("name"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CompletionRequest:
    """补全请求。"""

    messages: list[ChatMessage]
    model: str = "llama"
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 0.9
    stream: bool = False
    stop: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "stream": self.stream,
            "stop": self.stop,
            **self.extra,
        }


@dataclass
class CompletionResponse:
    """补全响应。"""

    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    elapsed_ms: float = 0.0
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class AuditReport:
    """全量审计审查报告。"""

    target: str
    summary: str
    issues: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    severity: str = "info"

    @property
    def passed(self) -> bool:
        return self.severity in ("info", "low") and not any(
            i.get("severity") in ("high", "critical") for i in self.issues
        )


@dataclass
class EfficiencyIteration:
    """省效率迭代版本。"""

    version: str
    baseline_ms: float
    optimized_ms: float
    savings_ratio: float
    changes: list[str] = field(default_factory=list)
    snapshot: dict[str, Any] = field(default_factory=dict)

    @property
    def speedup(self) -> float:
        return self.baseline_ms / self.optimized_ms if self.optimized_ms > 0 else 0.0
