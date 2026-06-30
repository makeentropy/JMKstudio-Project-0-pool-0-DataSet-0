"""
LLM Agent 指导模块

使用AI大语言模型指导爬虫的爬取策略，实现
"拉注意力"机制——智能判断哪些页面/节点值得
优先爬取，动态调整爬取方向。
"""

from ai_llm_agent_crawler.agent.attention import (
    AttentionScorer,
    AttentionConfig,
    ScoringStrategy,
)
from ai_llm_agent_crawler.agent.crawl_agent import (
    CrawlAgent,
    AgentConfig,
    CrawlDecision,
    AgentMode,
)

__all__ = [
    "AttentionScorer",
    "AttentionConfig",
    "ScoringStrategy",
    "CrawlAgent",
    "AgentConfig",
    "CrawlDecision",
    "AgentMode",
]
