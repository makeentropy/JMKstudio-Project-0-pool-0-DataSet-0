"""LLM 引擎基类。"""

from __future__ import annotations

import abc
from typing import Any

from ai_llm_agent_crawler.llm_engine.models import (
    CompletionRequest,
    CompletionResponse,
)


class BaseLLMEngine(abc.ABC):
    """LLM 引擎抽象基类。

    所有引擎适配器（llama.cpp、OpenAI 兼容 API 等）需实现 :meth:`complete`。
    """

    name: str = "base"

    def __init__(self, **kwargs: Any) -> None:
        self.config: dict[str, Any] = kwargs

    @abc.abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """执行一次补全请求。"""

    def chat(self, messages: list[Any]) -> CompletionResponse:
        """便捷聊天接口。"""
        from ai_llm_agent_crawler.llm_engine.models import ChatMessage, CompletionRequest

        normalized: list[ChatMessage] = []
        for m in messages:
            if isinstance(m, ChatMessage):
                normalized.append(m)
            elif isinstance(m, dict):
                normalized.append(ChatMessage.from_dict(m))
            else:
                raise TypeError(f"不支持的消息类型: {type(m)}")
        req = CompletionRequest(messages=normalized, model=self.name)
        return self.complete(req)

    def health(self) -> dict[str, Any]:
        """健康检查。"""
        return {"engine": self.name, "status": "ok", "config_keys": list(self.config.keys())}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
