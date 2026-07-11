"""llama.cpp 引擎适配器。

支持三种后端模式：
1. ``local``  —— 通过 ``llama_cpp`` Python 绑定本地加载 GGUF 模型；
2. ``remote`` —— 调用 llama.cpp / OpenAI 兼容的 HTTP 服务端；
3. ``stub``   —— 无依赖的确定性占位实现，用于离线演示与测试。

绑定与 HTTP 客户端均采用懒加载，避免在未安装时拖累整个包。
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ai_llm_agent_crawler.llm_engine.base import BaseLLMEngine
from ai_llm_agent_crawler.llm_engine.models import (
    CompletionRequest,
    CompletionResponse,
)


@dataclass
class LlamaCppConfig:
    """llama.cpp 适配器配置。"""

    mode: str = "stub"  # local | remote | stub
    model_path: str | None = None  # GGUF 文件路径（mode=local）
    n_ctx: int = 4096
    n_threads: int | None = None
    n_gpu_layers: int = 0
    remote_base_url: str = "http://127.0.0.1:8080"
    remote_api_key: str | None = None
    timeout: float = 60.0
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.mode = self.mode.lower()
        if self.mode not in ("local", "remote", "stub"):
            raise ValueError(f"未知模式: {self.mode}")


class LlamaCppAdapter(BaseLLMEngine):
    """llama.cpp 适配器。"""

    name = "llama.cpp"

    def __init__(self, config: LlamaCppConfig | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg: LlamaCppConfig = config or LlamaCppConfig()
        self._llm: Any = None  # 本地模型实例
        self._http: Any = None  # 远程 HTTP 客户端

    # ------------------------------------------------------------------ public
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.perf_counter()
        if self.cfg.mode == "local":
            text = self._complete_local(request)
        elif self.cfg.mode == "remote":
            text = self._complete_remote(request)
        else:
            text = self._complete_stub(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return CompletionResponse(
            text=text,
            model=request.model or self.name,
            usage={
                "prompt_tokens": _approx_tokens(request),
                "completion_tokens": _approx_tokens_text(text),
            },
            elapsed_ms=round(elapsed_ms, 3),
            finish_reason="stop",
            request_id=uuid.uuid4().hex,
        )

    def health(self) -> dict[str, Any]:
        base = super().health()
        base.update({"mode": self.cfg.mode, "model_path": self.cfg.model_path})
        if self.cfg.mode == "local" and self._llm is None:
            base["status"] = "unloaded"
        elif self.cfg.mode == "remote":
            base["status"] = "configured"
        return base

    # ------------------------------------------------------------------ local
    def _complete_local(self, request: CompletionRequest) -> str:
        llm = self._ensure_local_model()
        prompt = _messages_to_prompt(request.messages)
        out = llm(
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop or None,
        )
        if isinstance(out, dict):
            return str(out.get("choices", [{}])[0].get("text", ""))
        return str(out)

    def _ensure_local_model(self) -> Any:
        if self._llm is not None:
            return self._llm
        if not self.cfg.model_path:
            raise ValueError("local 模式需要配置 model_path（GGUF 文件路径）")
        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "未安装 llama_cpp，请执行 `pip install llama-cpp-python`"
            ) from exc
        self._llm = Llama(
            model_path=self.cfg.model_path,
            n_ctx=self.cfg.n_ctx,
            n_threads=self.cfg.n_threads,
            n_gpu_layers=self.cfg.n_gpu_layers,
            verbose=False,
        )
        return self._llm

    # ------------------------------------------------------------------ remote
    def _complete_remote(self, request: CompletionRequest) -> str:
        client = self._ensure_http()
        payload = request.to_dict()
        resp = client.post(
            f"{self.cfg.remote_base_url}/v1/chat/completions",
            json=payload,
            timeout=self.cfg.timeout,
            headers=self._remote_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _remote_headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.cfg.remote_api_key:
            h["Authorization"] = f"Bearer {self.cfg.remote_api_key}"
        return h

    def _ensure_http(self) -> Any:
        if self._http is not None:
            return self._http
        import requests  # type: ignore

        self._http = requests
        return self._http

    # ------------------------------------------------------------------ stub
    def _complete_stub(self, request: CompletionRequest) -> str:
        """确定性占位输出，用于无依赖演示。"""
        prompt = _messages_to_prompt(request.messages)
        preview = prompt.strip().splitlines()[-1][:80] if prompt.strip() else ""
        return (
            f"[llama.cpp stub] 已收到 {len(request.messages)} 条消息。"
            f"最后输入预览: {preview!r}。"
            f"如需真实推理，请将 LlamaCppConfig.mode 设为 'local' 或 'remote'。"
        )


def _messages_to_prompt(messages: list[Any]) -> str:
    parts: list[str] = []
    for m in messages:
        role = getattr(m, "role", None)
        content = getattr(m, "content", "")
        role_val = role.value if hasattr(role, "value") else str(role)
        parts.append(f"<|{role_val}|>{content}")
    return "\n".join(parts)


def _approx_tokens(request: CompletionRequest) -> int:
    return sum(len(getattr(m, "content", "").split()) for m in request.messages)


def _approx_tokens_text(text: str) -> int:
    return len(text.split())
