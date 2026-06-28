"""
爬虫基类模块

定义爬虫的基本接口和公共功能，支持多种数据源类型。
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.config import get_settings


class DataSourceType(str, Enum):
    """数据源类型枚举"""
    
    INTERNET_API = "internet_api"          # Internet API搜索
    WECHAT_CHAT = "wechat_chat"            # 微信聊天记录
    WECHAT_ARTICLE = "wechat_article"      # 微信公众号文章
    WEB_PAGE = "web_page"                  # 网页爬取
    DATABASE = "database"                  # 数据库
    FILE_SYSTEM = "file_system"            # 文件系统
    RSS_FEED = "rss_feed"                  # RSS订阅
    CUSTOM = "custom"                      # 自定义数据源


class CrawlerCapability(str, Enum):
    """爬虫能力枚举"""
    
    ASYNC_FETCH = "async_fetch"            # 异步抓取
    BATCH_FETCH = "batch_fetch"           # 批量抓取
    INCREMENTAL = "incremental"            # 增量爬取
    AUTH_REQUIRED = "auth_required"        # 需要认证
    RATE_LIMIT = "rate_limit"              # 速率限制
    PROXY_SUPPORT = "proxy_support"        # 代理支持
    JS_RENDERING = "js_rendering"          # JavaScript渲染
    CAPTCHA_HANDLING = "captcha_handling"  # 验证码处理


class CrawlerConfig(BaseModel):
    """爬虫配置"""
    
    # 基础配置
    user_agent: str = Field(
        default_factory=lambda: get_settings().crawler_user_agent,
        description="User-Agent字符串",
    )
    timeout: int = Field(
        default_factory=lambda: get_settings().crawler_timeout,
        description="请求超时时间（秒）",
    )
    max_retries: int = Field(
        default_factory=lambda: get_settings().crawler_max_retries,
        description="最大重试次数",
    )
    delay: float = Field(
        default_factory=lambda: get_settings().crawler_delay,
        description="请求延迟（秒）",
    )
    concurrent_requests: int = Field(
        default_factory=lambda: get_settings().crawler_concurrent_requests,
        description="并发请求数",
    )
    
    # 请求配置
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头")
    cookies: Dict[str, str] = Field(default_factory=dict, description="Cookies")
    proxy: Optional[str] = Field(default=None, description="代理服务器")
    
    # 数据源配置
    source_type: DataSourceType = Field(
        default=DataSourceType.WEB_PAGE,
        description="数据源类型",
    )
    
    # 反爬虫配置
    enable_anti_detection: bool = Field(default=True, description="启用反检测")
    rotate_user_agent: bool = Field(default=False, description="轮换User-Agent")
    rotate_headers: bool = Field(default=False, description="轮换请求头")
    use_proxy_pool: bool = Field(default=False, description="使用代理池")
    
    # 速率限制配置
    rate_limit_requests: int = Field(default=10, description="速率限制请求数")
    rate_limit_period: int = Field(default=60, description="速率限制周期（秒）")
    
    # 重试配置
    retry_delay: float = Field(default=1.0, description="重试延迟（秒）")
    retry_backoff_factor: float = Field(default=2.0, description="重试退避因子")
    retry_status_codes: List[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="需要重试的状态码",
    )
    
    # 认证配置
    auth_enabled: bool = Field(default=False, description="启用认证")
    auth_token: Optional[str] = Field(default=None, description="认证令牌")
    auth_username: Optional[str] = Field(default=None, description="用户名")
    auth_password: Optional[str] = Field(default=None, description="密码")


# 泛型类型变量，用于不同数据源的结果类型
T = TypeVar('T')


class CrawlResult(BaseModel):
    """爬取结果"""
    
    # 基础信息
    url: str = Field(description="请求URL")
    status_code: int = Field(default=200, description="HTTP状态码")
    content: Any = Field(default="", description="页面内容或数据")
    
    # 响应信息
    headers: Dict[str, str] = Field(default_factory=dict, description="响应头")
    cookies: Dict[str, str] = Field(default_factory=dict, description="响应Cookies")
    elapsed_time: float = Field(default=0.0, description="耗时（秒）")
    
    # 数据源信息
    source_type: DataSourceType = Field(
        default=DataSourceType.WEB_PAGE,
        description="数据源类型",
    )
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    # 爬取状态
    success: bool = Field(default=True, description="是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    retry_count: int = Field(default=0, description="重试次数")
    
    # 时间戳
    crawled_at: Optional[str] = Field(default=None, description="爬取时间")
    
    class Config:
        use_enum_values = True


class CrawlError(Exception):
    """爬取错误"""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        source_type: Optional[DataSourceType] = None,
        **kwargs,
    ):
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.source_type = source_type
        self.details = kwargs


class BaseCrawler(ABC, Generic[T]):
    """
    爬虫基类（泛型）
    
    所有爬虫实现都应继承此类并实现抽象方法。
    支持多种数据源类型和爬虫能力。
    """
    
    # 子类应定义支持的数据源类型和能力
    supported_source_types: List[DataSourceType] = []
    capabilities: List[CrawlerCapability] = []
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """
        初始化爬虫
        
        Args:
            config: 爬虫配置，默认使用全局配置
        """
        self.config = config or CrawlerConfig()
        self._is_running = False
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0
    
    @abstractmethod
    async def fetch(self, url: str, **kwargs) -> CrawlResult:
        """
        异步获取单个URL
        
        Args:
            url: 目标URL
            **kwargs: 额外参数
            
        Returns:
            爬取结果
            
        Raises:
            CrawlError: 爬取失败
        """
        pass
    
    @abstractmethod
    async def fetch_many(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """
        异步批量获取多个URL
        
        Args:
            urls: 目标URL列表
            **kwargs: 额外参数
            
        Returns:
            爬取结果列表
            
        Raises:
            CrawlError: 爬取失败
        """
        pass
    
    def start(self) -> None:
        """启动爬虫"""
        if self._is_running:
            return
        self._is_running = True
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0
        self._on_start()
    
    def stop(self) -> None:
        """停止爬虫"""
        if not self._is_running:
            return
        self._is_running = False
        self._on_stop()
    
    def is_running(self) -> bool:
        """检查爬虫是否正在运行"""
        return self._is_running
    
    def _on_start(self) -> None:
        """启动时的回调"""
        pass
    
    def _on_stop(self) -> None:
        """停止时的回调"""
        pass
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取爬虫统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "request_count": self._request_count,
            "success_count": self._success_count,
            "error_count": self._error_count,
        }
    
    def has_capability(self, capability: CrawlerCapability) -> bool:
        """
        检查爬虫是否具有某项能力
        
        Args:
            capability: 爬虫能力
            
        Returns:
            是否具有该能力
        """
        return capability in self.capabilities
    
    def supports_source_type(self, source_type: DataSourceType) -> bool:
        """
        检查爬虫是否支持某数据源类型
        
        Args:
            source_type: 数据源类型
            
        Returns:
            是否支持该数据源
        """
        return source_type in self.supported_source_types
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        验证URL是否有效
        
        Args:
            url: 要验证的URL
            
        Returns:
            是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def get_domain(url: str) -> str:
        """
        获取URL的域名
        
        Args:
            url: URL字符串
            
        Returns:
            域名
        """
        parsed = urlparse(url)
        return parsed.netloc
    
    def _record_success(self) -> None:
        """记录成功请求"""
        self._request_count += 1
        self._success_count += 1
    
    def _record_error(self) -> None:
        """记录失败请求"""
        self._request_count += 1
        self._error_count += 1


class SourceSpecificCrawler(BaseCrawler[T]):
    """
    数据源特定爬虫基类
    
    为特定数据源提供额外的功能和接口。
    """
    
    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        source_type: Optional[DataSourceType] = None,
    ):
        """
        初始化数据源特定爬虫
        
        Args:
            config: 爬虫配置
            source_type: 数据源类型
        """
        super().__init__(config)
        self.source_type = source_type or self.config.source_type
    
    @abstractmethod
    async def crawl(self, target: str, **kwargs) -> T:
        """
        执行爬取任务（数据源特定）
        
        Args:
            target: 目标标识（URL、关键词等）
            **kwargs: 额外参数
            
        Returns:
            爬取的数据
        """
        pass
    
    async def search(self, query: str, **kwargs) -> List[T]:
        """
        搜索数据（可选实现）
        
        Args:
            query: 搜索查询
            **kwargs: 额外参数
            
        Returns:
            搜索结果列表
        """
        raise NotImplementedError("This crawler does not support search")
    
    async def get_item(self, item_id: str, **kwargs) -> Optional[T]:
        """
        获取单个项目（可选实现）
        
        Args:
            item_id: 项目ID
            **kwargs: 额外参数
            
        Returns:
            项目数据，不存在则返回None
        """
        raise NotImplementedError("This crawler does not support get_item")
    
    async def list_items(
        self,
        page: int = 1,
        page_size: int = 20,
        **kwargs,
    ) -> List[T]:
        """
        列出项目（可选实现）
        
        Args:
            page: 页码
            page_size: 每页数量
            **kwargs: 额外参数
            
        Returns:
            项目列表
        """
        raise NotImplementedError("This crawler does not support list_items")