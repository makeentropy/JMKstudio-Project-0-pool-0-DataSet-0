"""llm_engine 模块测试。"""

from __future__ import annotations

import pytest

from ai_llm_agent_crawler.llm_engine import (
    ChatMessage,
    ChatRole,
    CompletionRequest,
    EfficiencyIteration,
    FullAuditAgent,
    JsAgentClient,
    JsAgentConfig,
    LlamaCppAdapter,
    LlamaCppConfig,
)


@pytest.fixture
def stub_engine() -> LlamaCppAdapter:
    return LlamaCppAdapter(LlamaCppConfig(mode="stub"))


@pytest.fixture
def stub_js_agent() -> JsAgentClient:
    return JsAgentClient(JsAgentConfig(mode="stub"))


class TestModels:
    def test_chat_message_roundtrip(self) -> None:
        m = ChatMessage(role=ChatRole.USER, content="hello")
        d = m.to_dict()
        assert d["role"] == "user"
        m2 = ChatMessage.from_dict(d)
        assert m2.role == ChatRole.USER
        assert m2.content == "hello"

    def test_completion_request_to_dict(self) -> None:
        req = CompletionRequest(messages=[ChatMessage(role=ChatRole.SYSTEM, content="s")])
        d = req.to_dict()
        assert d["model"] == "llama"
        assert d["messages"][0]["role"] == "system"

    def test_efficiency_iteration_speedup(self) -> None:
        it = EfficiencyIteration(
            version="v1", baseline_ms=100.0, optimized_ms=50.0, savings_ratio=0.5
        )
        assert it.speedup == pytest.approx(2.0)


class TestLlamaCppAdapter:
    def test_stub_complete(self, stub_engine: LlamaCppAdapter) -> None:
        req = CompletionRequest(
            messages=[ChatMessage(role=ChatRole.USER, content="hi")]
        )
        resp = stub_engine.complete(req)
        assert "stub" in resp.text
        assert resp.elapsed_ms >= 0
        assert resp.usage["prompt_tokens"] >= 0

    def test_chat_with_dicts(self, stub_engine: LlamaCppAdapter) -> None:
        resp = stub_engine.chat([{"role": "user", "content": "ping"}])
        assert "stub" in resp.text

    def test_health(self, stub_engine: LlamaCppAdapter) -> None:
        h = stub_engine.health()
        assert h["engine"] == "llama.cpp"
        assert h["mode"] == "stub"

    def test_invalid_mode(self) -> None:
        with pytest.raises(ValueError):
            LlamaCppConfig(mode="invalid")

    def test_local_requires_model_path(self) -> None:
        eng = LlamaCppAdapter(LlamaCppConfig(mode="local"))
        req = CompletionRequest(messages=[ChatMessage(role=ChatRole.USER, content="x")])
        with pytest.raises(ValueError):
            eng.complete(req)


class TestJsAgent:
    def test_chat_stub(self, stub_js_agent: JsAgentClient) -> None:
        out = stub_js_agent.chat([ChatMessage(role=ChatRole.USER, content="hi")])
        assert out["ok"] is True
        assert "stub" in out["text"]

    def test_tool_call_stub(self, stub_js_agent: JsAgentClient) -> None:
        out = stub_js_agent.call_tool("calc", {"x": 1})
        assert out["ok"] is True
        assert out["tool"] == "calc"

    def test_audit_stub(self, stub_js_agent: JsAgentClient) -> None:
        out = stub_js_agent.audit("target", {"k": 1})
        assert out["ok"] is True
        assert out["target"] == "target"

    def test_iterate_stub(self, stub_js_agent: JsAgentClient) -> None:
        out = stub_js_agent.iterate({"ms": 100})
        assert out["ok"] is True
        assert "version" in out


class TestFullAuditAgent:
    def test_audit_returns_report(self, stub_engine: LlamaCppAdapter) -> None:
        agent = FullAuditAgent(stub_engine)
        report = agent.audit("dataset.csv", "col1,col2\n1,2")
        assert report.target == "dataset.csv"
        assert isinstance(report.summary, str)

    def test_iterate_records(self, stub_engine: LlamaCppAdapter) -> None:
        agent = FullAuditAgent(stub_engine)
        it = agent.iterate(100.0)
        assert it.baseline_ms == 100.0
        assert len(agent.iterations) == 1

    def test_summary(self, stub_engine: LlamaCppAdapter) -> None:
        agent = FullAuditAgent(stub_engine)
        agent.iterate(100.0)
        s = agent.summary()
        assert s["iterations"] == 1
        assert s["engine"] == "llama.cpp"
