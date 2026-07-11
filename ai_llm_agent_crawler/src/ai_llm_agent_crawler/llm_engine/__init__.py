"""
LLM 引擎模块

提供 llama.cpp 引擎适配、内置 JS agent HTTP 接口、以及 full agent 全量审计审查能力。
支持生成不断迭代的省效率版本，并与 skills_pool 协同沉淀。
"""

from ai_llm_agent_crawler.llm_engine.models import (
    ChatMessage,
    ChatRole,
    CompletionRequest,
    CompletionResponse,
    AuditReport,
    EfficiencyIteration,
)
from ai_llm_agent_crawler.llm_engine.base import BaseLLMEngine
from ai_llm_agent_crawler.llm_engine.llama_cpp_adapter import LlamaCppAdapter, LlamaCppConfig
from ai_llm_agent_crawler.llm_engine.js_agent import JsAgentClient, JsAgentConfig
from ai_llm_agent_crawler.llm_engine.full_agent import FullAuditAgent

__all__ = [
    # 模型
    "ChatMessage",
    "ChatRole",
    "CompletionRequest",
    "CompletionResponse",
    "AuditReport",
    "EfficiencyIteration",
    # 引擎
    "BaseLLMEngine",
    "LlamaCppAdapter",
    "LlamaCppConfig",
    # JS agent
    "JsAgentClient",
    "JsAgentConfig",
    # full agent
    "FullAuditAgent",
]
