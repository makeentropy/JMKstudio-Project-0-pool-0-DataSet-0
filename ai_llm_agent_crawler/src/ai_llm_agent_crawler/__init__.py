"""
AI LLM Agent Crawler - 智能爬虫与数据集生成系统

这是一个功能强大的智能爬虫系统，集成了：
- 据点管理（种子URL）
- 连线载点（图网络可视化）
- 拉注意力（LLM Agent智能评分）
- 窗口（GUI图形界面）
- 数据集生成
- 维度空间质能质量子奇点系统
- 安全加密
- NAS存储管理
- 版本控制
"""

__version__ = "0.2.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from ai_llm_agent_crawler.utils.logging import get_logger, setup_logging
from ai_llm_agent_crawler.utils.config import get_settings
from ai_llm_agent_crawler.seed import SeedManager, SeedPoint, SeedCategory
from ai_llm_agent_crawler.graph import CrawlGraph, CrawlNode, CrawlEdge
from ai_llm_agent_crawler.agent import (
    CrawlAgent,
    AttentionScorer,
    AttentionConfig,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "get_logger",
    "setup_logging",
    "get_settings",
    "SeedManager",
    "SeedPoint",
    "SeedCategory",
    "CrawlGraph",
    "CrawlNode",
    "CrawlEdge",
    "CrawlAgent",
    "AttentionScorer",
    "AttentionConfig",
]