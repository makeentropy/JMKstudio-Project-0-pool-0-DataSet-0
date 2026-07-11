"""Full Agent —— 全量审计审查与省效率迭代。

组合 llama.cpp 引擎与 JS agent，对目标（代码、数据集、pipeline）执行：
1. 全量分析（结构、性能、安全、数据质量）；
2. 审计审查（识别问题、风险、改进点）；
3. 生成不断迭代的省效率版本（记录基线、优化、加速比）。
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ai_llm_agent_crawler.llm_engine.base import BaseLLMEngine
from ai_llm_agent_crawler.llm_engine.js_agent import JsAgentClient
from ai_llm_agent_crawler.llm_engine.models import (
    AuditReport,
    ChatMessage,
    ChatRole,
    CompletionRequest,
    EfficiencyIteration,
)


_AUDIT_SYSTEM_PROMPT = (
    "你是全量审计审查 agent。对给定目标进行结构与性能审计，输出 JSON："
    '{"summary": str, "issues": [{"id","severity","category","detail"}], '
    '"metrics": {"k": v}, "recommendations": [str]}。'
    "severity 取值：info|low|medium|high|critical。只输出 JSON。"
)

_ITERATE_SYSTEM_PROMPT = (
    "你是省效率迭代 agent。基于基线指标生成优化方案，输出 JSON："
    '{"version": str, "changes": [str], "expected_savings_ratio": float}。'
    "savings_ratio 为 0..1 之间。只输出 JSON。"
)


class FullAuditAgent:
    """全量审计审查 + 省效率迭代 agent。"""

    def __init__(
        self,
        engine: BaseLLMEngine,
        js_agent: JsAgentClient | None = None,
    ) -> None:
        self.engine: BaseLLMEngine = engine
        self.js_agent: JsAgentClient | None = js_agent
        self.iterations: list[EfficiencyIteration] = []

    # ------------------------------------------------------------------ audit
    def audit(
        self,
        target: str,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> AuditReport:
        """对目标内容执行全量审计审查。"""
        ctx = context or {}
        user_payload = (
            f"目标: {target}\n上下文: {ctx}\n内容:\n{content[:4000]}\n请输出审计 JSON。"
        )
        req = CompletionRequest(
            messages=[
                ChatMessage(role=ChatRole.SYSTEM, content=_AUDIT_SYSTEM_PROMPT),
                ChatMessage(role=ChatRole.USER, content=user_payload),
            ],
            model=self.engine.name,
            temperature=0.2,
            max_tokens=1024,
        )
        resp = self.engine.complete(req)
        parsed = _safe_parse_json(resp.text)
        report = AuditReport(
            target=target,
            summary=parsed.get("summary", resp.text[:200]),
            issues=parsed.get("issues", []),
            metrics=parsed.get("metrics", {}),
            recommendations=parsed.get("recommendations", []),
            severity=_aggregate_severity(parsed.get("issues", [])),
        )
        # 同步 JS agent 审计（若可用）
        if self.js_agent is not None:
            try:
                js_out = self.js_agent.audit(target, {"content": content[:1000], **ctx})
                if js_out.get("ok"):
                    report.metrics["js_agent"] = 1.0
            except Exception:  # noqa: BLE001
                report.metrics["js_agent"] = 0.0
        return report

    # ------------------------------------------------------------------ iterate
    def iterate(
        self,
        baseline_ms: float,
        baseline_payload: dict[str, Any] | None = None,
    ) -> EfficiencyIteration:
        """生成一个省效率迭代版本。"""
        payload = baseline_payload or {}
        user_payload = (
            f"基线耗时(ms): {baseline_ms}\n基线指标: {payload}\n"
            "请输出迭代方案 JSON。"
        )
        req = CompletionRequest(
            messages=[
                ChatMessage(role=ChatRole.SYSTEM, content=_ITERATE_SYSTEM_PROMPT),
                ChatMessage(role=ChatRole.USER, content=user_payload),
            ],
            model=self.engine.name,
            temperature=0.3,
            max_tokens=512,
        )
        resp = self.engine.complete(req)
        parsed = _safe_parse_json(resp.text)
        savings = float(parsed.get("expected_savings_ratio", 0.1))
        optimized_ms = baseline_ms * (1.0 - savings) if savings < 1.0 else baseline_ms * 0.5
        version = parsed.get("version", f"v{len(self.iterations) + 1}")
        iteration = EfficiencyIteration(
            version=version,
            baseline_ms=baseline_ms,
            optimized_ms=round(optimized_ms, 3),
            savings_ratio=round(savings, 4),
            changes=parsed.get("changes", []),
            snapshot=payload,
        )
        self.iterations.append(iteration)
        return iteration

    # ------------------------------------------------------------------ summary
    def summary(self) -> dict[str, Any]:
        return {
            "engine": self.engine.name,
            "iterations": len(self.iterations),
            "total_savings": sum(it.savings_ratio for it in self.iterations),
            "best_speedup": max((it.speedup for it in self.iterations), default=0.0),
            "js_agent": self.js_agent.health() if self.js_agent else None,
        }


def _safe_parse_json(text: str) -> dict[str, Any]:
    """从 LLM 输出中尽力解析 JSON。"""
    if not text:
        return {}
    # 尝试直接解析
    try:
        return _coerce_dict(__import__("json").loads(text))
    except Exception:  # noqa: BLE001
        pass
    # 提取第一个 {...} 块
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return _coerce_dict(__import__("json").loads(match.group(0)))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {"summary": str(value)}


def _aggregate_severity(issues: list[dict[str, Any]]) -> str:
    order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    worst = 0
    for it in issues:
        sev = str(it.get("severity", "info")).lower()
        worst = max(worst, order.get(sev, 0))
    for name, rank in order.items():
        if rank == worst:
            return name
    return "info"
