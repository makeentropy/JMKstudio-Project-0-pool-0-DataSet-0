"""内置 JS agent 接口。

JS agent 运行于 H5 IDE / 浏览器侧（或 Node 子进程），通过 HTTP 与后端 llama 引擎通信。
本模块提供：

- :class:`JsAgentConfig` —— JS agent 运行时配置；
- :class:`JsAgentClient` —— 后端侧调用 JS agent 的客户端（支持 ``http`` 与 ``stub``）；
- :class:`JsAgentProtocol` —— JS agent 与后端约定的消息协议（便于前端实现）。
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ai_llm_agent_crawler.llm_engine.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
)


@dataclass
class JsAgentConfig:
    """JS agent 配置。"""

    mode: str = "stub"  # http | stub
    endpoint: str = "http://127.0.0.1:7878/agent/run"
    api_key: str | None = None
    timeout: float = 30.0
    agent_name: str = "trae-js-agent"
    tools: list[str] = field(default_factory=lambda: ["search", "calc", "fetch"])


class JsAgentProtocol:
    """JS agent 与后端的消息协议常量与辅助方法。"""

    ACTION_CHAT = "chat"
    ACTION_TOOL_CALL = "tool_call"
    ACTION_AUDIT = "audit"
    ACTION_ITERATE = "iterate"

    @staticmethod
    def envelope(action: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent": "js",
            "action": action,
            "payload": payload,
            "ts": time.time(),
            "trace_id": uuid.uuid4().hex,
        }

    @staticmethod
    def validate(msg: dict[str, Any]) -> None:
        for key in ("action", "payload"):
            if key not in msg:
                raise ValueError(f"JS agent 消息缺少字段: {key}")


class JsAgentClient:
    """后端侧调用 JS agent 的客户端。"""

    def __init__(self, config: JsAgentConfig | None = None) -> None:
        self.cfg: JsAgentConfig = config or JsAgentConfig()
        self._http: Any = None

    # ------------------------------------------------------------------ chat
    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "messages": [m.to_dict() for m in messages],
            "tools": tools or self.cfg.tools,
            "agent_name": self.cfg.agent_name,
        }
        return self._invoke(JsAgentProtocol.ACTION_CHAT, payload)

    # ------------------------------------------------------------------ tool
    def call_tool(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        return self._invoke(
            JsAgentProtocol.ACTION_TOOL_CALL,
            {"tool": tool, "args": args},
        )

    # ------------------------------------------------------------------ audit
    def audit(self, target: str, context: dict[str, Any]) -> dict[str, Any]:
        return self._invoke(
            JsAgentProtocol.ACTION_AUDIT,
            {"target": target, "context": context},
        )

    # ------------------------------------------------------------------ iterate
    def iterate(self, baseline: dict[str, Any]) -> dict[str, Any]:
        return self._invoke(JsAgentProtocol.ACTION_ITERATE, {"baseline": baseline})

    # ------------------------------------------------------------------ invoke
    def _invoke(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        envelope = JsAgentProtocol.envelope(action, payload)
        if self.cfg.mode == "http":
            return self._invoke_http(envelope)
        return self._invoke_stub(envelope)

    def _invoke_http(self, envelope: dict[str, Any]) -> dict[str, Any]:
        client = self._ensure_http()
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        resp = client.post(
            self.cfg.endpoint,
            data=json.dumps(envelope),
            headers=headers,
            timeout=self.cfg.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _invoke_stub(self, envelope: dict[str, Any]) -> dict[str, Any]:
        action = envelope["action"]
        payload = envelope["payload"]
        ts = envelope["ts"]
        if action == JsAgentProtocol.ACTION_CHAT:
            text = (
                f"[js-agent stub] 已处理 {len(payload['messages'])} 条消息，"
                f"可用工具: {payload['tools']}。"
            )
            return {"ok": True, "text": text, "trace_id": envelope["trace_id"]}
        if action == JsAgentProtocol.ACTION_TOOL_CALL:
            return {
                "ok": True,
                "tool": payload["tool"],
                "result": {"stub": True, "args": payload["args"]},
                "trace_id": envelope["trace_id"],
            }
        if action == JsAgentProtocol.ACTION_AUDIT:
            return {
                "ok": True,
                "target": payload["target"],
                "summary": "stub 审计：未发现高风险问题",
                "issues": [],
                "trace_id": envelope["trace_id"],
            }
        if action == JsAgentProtocol.ACTION_ITERATE:
            return {
                "ok": True,
                "version": "stub-iter-0",
                "savings_ratio": 0.0,
                "changes": [],
                "trace_id": envelope["trace_id"],
            }
        return {"ok": False, "error": f"未知 action: {action}"}

    def _ensure_http(self) -> Any:
        if self._http is not None:
            return self._http
        import requests  # type: ignore

        self._http = requests
        return self._http

    def health(self) -> dict[str, Any]:
        return {
            "agent": self.cfg.agent_name,
            "mode": self.cfg.mode,
            "endpoint": self.cfg.endpoint,
            "tools": self.cfg.tools,
        }
