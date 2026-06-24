from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Generator
from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    role: Role
    content: str
    name: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"role": self.role.value, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class LLMResponse:
    content: str
    model: str = ""
    usage: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class BaseLLM(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def chat(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    def chat_stream(self, messages: List[ChatMessage], **kwargs) -> Generator[str, None, None]:
        pass

    def _build_messages(self, messages: List[ChatMessage]) -> List[dict]:
        return [m.to_dict() for m in messages]
