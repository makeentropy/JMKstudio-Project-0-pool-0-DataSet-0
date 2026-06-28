"""
爬虫模块

提供多种爬虫实现，包括：
- 同步/异步HTTP爬虫
- Internet API搜索爬虫
- 微信聊天记录爬虫（模拟）
- 微信公众号文章爬虫
- 反爬虫策略和代理池支持
- 任务调度系统
"""

from ai_llm_agent_crawler.crawler.base import (
    BaseCrawler,
    CrawlerCapability,
    CrawlerConfig,
    CrawlError,
    CrawlResult,
    DataSourceType,
    SourceSpecificCrawler,
)
from ai_llm_agent_crawler.crawler.http_crawler import AsyncHTTPCrawler, HTTPCrawler
from ai_llm_agent_crawler.crawler.internet_api_crawler import (
    InternetAPICrawler,
    InternetAPICrawlerConfig,
    SearchEngineType,
    SearchResult,
    SearchResponse,
)
from ai_llm_agent_crawler.crawler.wechat_crawler import (
    WeChatChatCrawler,
    WeChatChatCrawlerConfig,
    WeChatChatSession,
    WeChatChatType,
    WeChatMessage,
    WeChatMessageType,
    WeChatArticle,
    WeChatArticleCrawler,
    WeChatArticleCrawlerConfig,
)
from ai_llm_agent_crawler.crawler.anti_detection import (
    AntiDetectionManager,
    Proxy,
    ProxyPool,
    ProxyPoolConfig,
    ProxyStatus,
    ProxyType,
    RateLimiter,
    RateLimitConfig,
    RequestHeaderPool,
    UserAgent,
    UserAgentPool,
    UserAgentPoolConfig,
)
from ai_llm_agent_crawler.crawler.scheduler import (
    AsyncTaskManager,
    CrawlerTask,
    SchedulerConfig,
    TaskPriority,
    TaskQueue,
    TaskResult,
    TaskScheduler,
    TaskStatus,
)

__all__ = [
    # Base classes
    "BaseCrawler",
    "SourceSpecificCrawler",
    "CrawlerConfig",
    "CrawlError",
    "CrawlResult",
    "DataSourceType",
    "CrawlerCapability",
    # HTTP Crawlers
    "HTTPCrawler",
    "AsyncHTTPCrawler",
    # Internet API Crawler
    "InternetAPICrawler",
    "InternetAPICrawlerConfig",
    "SearchEngineType",
    "SearchResult",
    "SearchResponse",
    # WeChat Crawlers
    "WeChatChatCrawler",
    "WeChatChatCrawlerConfig",
    "WeChatChatSession",
    "WeChatChatType",
    "WeChatMessage",
    "WeChatMessageType",
    "WeChatArticle",
    "WeChatArticleCrawler",
    "WeChatArticleCrawlerConfig",
    # Anti Detection
    "AntiDetectionManager",
    "Proxy",
    "ProxyPool",
    "ProxyPoolConfig",
    "ProxyStatus",
    "ProxyType",
    "RateLimiter",
    "RateLimitConfig",
    "RequestHeaderPool",
    "UserAgent",
    "UserAgentPool",
    "UserAgentPoolConfig",
    # Scheduler
    "AsyncTaskManager",
    "CrawlerTask",
    "SchedulerConfig",
    "TaskPriority",
    "TaskQueue",
    "TaskResult",
    "TaskScheduler",
    "TaskStatus",
]