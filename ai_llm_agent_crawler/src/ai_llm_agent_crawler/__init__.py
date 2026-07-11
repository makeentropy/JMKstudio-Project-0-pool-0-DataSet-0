"""
AI LLM Agent Crawler - 智能爬虫与数据集生成系统

这是一个功能强大的智能爬虫系统，集成了数据集生成、维度空间质能质量子奇点系统、
安全加密、NAS存储管理和版本管理等模块。
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from ai_llm_agent_crawler.utils.logging import get_logger, setup_logging
from ai_llm_agent_crawler.utils.config import get_settings
from ai_llm_agent_crawler import algorithm
from ai_llm_agent_crawler import storage

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "get_logger",
    "setup_logging",
    "get_settings",
    "algorithm",
    "storage",
]