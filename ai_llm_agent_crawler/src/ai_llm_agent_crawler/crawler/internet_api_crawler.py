"""
Internet API搜索爬虫模块

集成多种搜索API，包括：
- DuckDuckGo（免费，无需API Key）
- Bing Search API（需要API Key）
- Google Custom Search API（需要API Key）
- 百度搜索API（需要API Key）

支持统一的搜索接口和结果格式。
"""

import asyncio
import random
import urllib.parse
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.crawler.base import (
    CrawlerCapability,
    CrawlerConfig,
    CrawlError,
    CrawlResult,
    DataSourceType,
    SourceSpecificCrawler,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class SearchEngineType(str, Enum):
    """搜索引擎类型枚举"""
    
    DUCKDUCKGO = "duckduckgo"
    BING = "bing"
    GOOGLE = "google"
    BAIDU = "baidu"


class SearchResult(BaseModel):
    """搜索结果"""
    
    # 基本信息
    title: str = Field(description="标题")
    url: str = Field(description="URL")
    snippet: str = Field(default="", description="摘要")
    
    # 来源信息
    engine: SearchEngineType = Field(description="搜索引擎")
    source_type: DataSourceType = Field(
        default=DataSourceType.INTERNET_API,
        description="数据源类型",
    )
    
    # 元数据
    rank: int = Field(default=0, description="排名")
    published_date: Optional[str] = Field(default=None, description="发布日期")
    author: Optional[str] = Field(default=None, description="作者")
    
    # 原始数据
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="原始API返回数据")
    
    # 时间戳
    searched_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="搜索时间",
    )


class SearchResponse(BaseModel):
    """搜索响应"""
    
    query: str = Field(description="搜索查询")
    engine: SearchEngineType = Field(description="搜索引擎")
    results: List[SearchResult] = Field(default_factory=list, description="搜索结果列表")
    total_results: int = Field(default=0, description="总结果数")
    elapsed_time: float = Field(default=0.0, description="耗时（秒）")
    success: bool = Field(default=True, description="是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class InternetAPICrawlerConfig(CrawlerConfig):
    """Internet API爬虫配置"""
    
    # 搜索引擎配置
    default_engine: SearchEngineType = Field(
        default=SearchEngineType.DUCKDUCKGO,
        description="默认搜索引擎",
    )
    
    # API Keys
    bing_api_key: Optional[str] = Field(default=None, description="Bing API Key")
    google_api_key: Optional[str] = Field(default=None, description="Google API Key")
    google_cx: Optional[str] = Field(default=None, description="Google Custom Search CX")
    baidu_api_key: Optional[str] = Field(default=None, description="百度 API Key")
    
    # 搜索配置
    max_results: int = Field(default=10, description="最大返回结果数")
    search_language: str = Field(default="zh-cn", description="搜索语言")
    search_region: str = Field(default="cn", description="搜索区域")
    safe_search: bool = Field(default=True, description="安全搜索")
    
    # 自动选择配置
    auto_select_engine: bool = Field(
        default=True,
        description="当默认引擎不可用时自动选择其他引擎",
    )


class InternetAPICrawler(SourceSpecificCrawler[SearchResult]):
    """
    Internet API搜索爬虫
    
    支持多种搜索引擎API的统一封装，提供一致的搜索接口。
    """
    
    supported_source_types = [DataSourceType.INTERNET_API]
    capabilities = [
        CrawlerCapability.ASYNC_FETCH,
        CrawlerCapability.BATCH_FETCH,
        CrawlerCapability.RATE_LIMIT,
        CrawlerCapability.PROXY_SUPPORT,
    ]
    
    # 搜索引擎API配置
    ENGINE_CONFIGS = {
        SearchEngineType.DUCKDUCKGO: {
            "requires_key": False,
            "base_url": "https://api.duckduckgo.com/",
            "rate_limit": 30,  # 每分钟请求限制
        },
        SearchEngineType.BING: {
            "requires_key": True,
            "base_url": "https://api.bing.microsoft.com/v7.0/search",
            "rate_limit": 1000,  # 每月限制（取决于订阅）
        },
        SearchEngineType.GOOGLE: {
            "requires_key": True,
            "base_url": "https://www.googleapis.com/customsearch/v1",
            "rate_limit": 100,  # 每天限制（免费版）
        },
        SearchEngineType.BAIDU: {
            "requires_key": True,
            "base_url": "https://api.baidu.com/json/sms/v3/SearchService",
            "rate_limit": 100,  # 每天限制
        },
    }
    
    def __init__(self, config: Optional[InternetAPICrawlerConfig] = None):
        super().__init__(config or InternetAPICrawlerConfig(), DataSourceType.INTERNET_API)
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_timestamps: Dict[str, List[float]] = {}
    
    def _on_start(self) -> None:
        """启动时初始化Session"""
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent},
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
        )
        logger.info("InternetAPICrawler已启动")
    
    def _on_stop(self) -> None:
        """停止时关闭Session"""
        if self._session:
            asyncio.create_task(self._session.close())
            self._session = None
        logger.info("InternetAPICrawler已停止")
    
    def _check_rate_limit(self, engine: SearchEngineType) -> bool:
        """
        检查是否达到速率限制
        
        Args:
            engine: 搜索引擎类型
            
        Returns:
            是否可以继续请求
        """
        engine_config = self.ENGINE_CONFIGS.get(engine, {})
        rate_limit = engine_config.get("rate_limit", 60)
        period = 60  # 60秒周期
        
        key = engine.value
        now = asyncio.get_event_loop().time()
        
        if key not in self._request_timestamps:
            self._request_timestamps[key] = []
        
        # 移除过期的时间戳
        self._request_timestamps[key] = [
            ts for ts in self._request_timestamps[key]
            if now - ts < period
        ]
        
        return len(self._request_timestamps[key]) < rate_limit
    
    def _record_request(self, engine: SearchEngineType) -> None:
        """记录请求时间戳"""
        key = engine.value
        now = asyncio.get_event_loop().time()
        self._request_timestamps[key].append(now)
    
    async def search(
        self,
        query: str,
        engine: Optional[SearchEngineType] = None,
        **kwargs,
    ) -> SearchResponse:
        """
        执行搜索
        
        Args:
            query: 搜索查询字符串
            engine: 搜索引擎类型，默认使用配置的默认引擎
            **kwargs: 额外参数
            
        Returns:
            搜索响应
        """
        if not self._session:
            self.start()
        
        # 选择搜索引擎
        selected_engine = engine or self.config.default_engine
        
        # 检查API Key是否可用
        if self.ENGINE_CONFIGS[selected_engine]["requires_key"]:
            if not self._has_api_key(selected_engine):
                if self.config.auto_select_engine:
                    selected_engine = self._select_available_engine()
                    logger.info(f"切换到可用引擎: {selected_engine}")
                else:
                    return SearchResponse(
                        query=query,
                        engine=selected_engine,
                        success=False,
                        error_message=f"API Key未配置: {selected_engine}",
                    )
        
        # 检查速率限制
        if not self._check_rate_limit(selected_engine):
            if self.config.auto_select_engine:
                backup_engine = self._select_available_engine(exclude=[selected_engine])
                if backup_engine:
                    selected_engine = backup_engine
                    logger.info(f"速率限制，切换引擎: {selected_engine}")
                else:
                    await asyncio.sleep(self.config.delay)
            else:
                await asyncio.sleep(self.config.delay)
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # 根据引擎类型执行搜索
            if selected_engine == SearchEngineType.DUCKDUCKGO:
                results = await self._search_duckduckgo(query, **kwargs)
            elif selected_engine == SearchEngineType.BING:
                results = await self._search_bing(query, **kwargs)
            elif selected_engine == SearchEngineType.GOOGLE:
                results = await self._search_google(query, **kwargs)
            elif selected_engine == SearchEngineType.BAIDU:
                results = await self._search_baidu(query, **kwargs)
            else:
                raise CrawlError(f"不支持的搜索引擎: {selected_engine}")
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            
            self._record_request(selected_engine)
            self._record_success()
            
            return SearchResponse(
                query=query,
                engine=selected_engine,
                results=results,
                total_results=len(results),
                elapsed_time=elapsed_time,
                success=True,
            )
            
        except Exception as e:
            logger.error(f"搜索失败: {query}, 错误: {e}")
            self._record_error()
            
            return SearchResponse(
                query=query,
                engine=selected_engine,
                success=False,
                error_message=str(e),
            )
    
    async def _search_duckduckgo(self, query: str, **kwargs) -> List[SearchResult]:
        """
        DuckDuckGo搜索（免费，无需API Key）
        
        Args:
            query: 搜索查询
            **kwargs: 额外参数
            
        Returns:
            搜索结果列表
        """
        # DuckDuckGo Instant Answer API
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        
        # 添加语言设置
        if self.config.search_language:
            params["kl"] = self.config.search_language
        
        # 添加区域设置
        if self.config.search_region:
            params["region"] = self.config.search_region
        
        try:
            async with self._session.get(
                "https://api.duckduckgo.com/",
                params=params,
                proxy=self.config.proxy,
            ) as response:
                data = await response.json()
                
                results = []
                
                # 解析相关主题
                related_topics = data.get("RelatedTopics", [])
                for i, topic in enumerate(related_topics[:self.config.max_results]):
                    if isinstance(topic, dict) and "FirstURL" in topic:
                        results.append(SearchResult(
                            title=topic.get("Text", "").split(" - ")[0] if "Text" in topic else "",
                            url=topic.get("FirstURL", ""),
                            snippet=topic.get("Text", ""),
                            engine=SearchEngineType.DUCKDUCKGO,
                            rank=i + 1,
                            raw_data=topic,
                        ))
                
                # 解析抽象结果（如果有）
                abstract = data.get("Abstract", "")
                abstract_url = data.get("AbstractURL", "")
                if abstract and abstract_url:
                    results.insert(0, SearchResult(
                        title=data.get("AbstractSource", ""),
                        url=abstract_url,
                        snippet=abstract,
                        engine=SearchEngineType.DUCKDUCKGO,
                        rank=0,
                        raw_data={"Abstract": abstract, "AbstractURL": abstract_url},
                    ))
                
                return results
                
        except aiohttp.ClientError as e:
            raise CrawlError(f"DuckDuckGo搜索失败: {e}", source_type=DataSourceType.INTERNET_API)
    
    async def _search_bing(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Bing搜索
        
        Args:
            query: 搜索查询
            **kwargs: 额外参数
            
        Returns:
            搜索结果列表
        """
        api_key = self.config.bing_api_key
        if not api_key:
            raise CrawlError("Bing API Key未配置", source_type=DataSourceType.INTERNET_API)
        
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query,
            "count": self.config.max_results,
            "offset": kwargs.get("offset", 0),
            "mkt": f"{self.config.search_language}-{self.config.search_region}",
            "safeSearch": "Strict" if self.config.safe_search else "Off",
        }
        
        try:
            async with self._session.get(
                "https://api.bing.microsoft.com/v7.0/search",
                params=params,
                headers=headers,
                proxy=self.config.proxy,
            ) as response:
                data = await response.json()
                
                results = []
                web_pages = data.get("webPages", {}).get("value", [])
                
                for i, page in enumerate(web_pages[:self.config.max_results]):
                    results.append(SearchResult(
                        title=page.get("name", ""),
                        url=page.get("url", ""),
                        snippet=page.get("snippet", ""),
                        engine=SearchEngineType.BING,
                        rank=i + 1,
                        published_date=page.get("dateLastCrawled"),
                        raw_data=page,
                    ))
                
                return results
                
        except aiohttp.ClientError as e:
            raise CrawlError(f"Bing搜索失败: {e}", source_type=DataSourceType.INTERNET_API)
    
    async def _search_google(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Google Custom Search
        
        Args:
            query: 搜索查询
            **kwargs: 额外参数
            
        Returns:
            搜索结果列表
        """
        api_key = self.config.google_api_key
        cx = self.config.google_cx
        
        if not api_key or not cx:
            raise CrawlError("Google API Key或CX未配置", source_type=DataSourceType.INTERNET_API)
        
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": self.config.max_results,
            "start": kwargs.get("start", 1),
            "hl": self.config.search_language,
            "gl": self.config.search_region,
            "safe": "active" if self.config.safe_search else "off",
        }
        
        try:
            async with self._session.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params,
                proxy=self.config.proxy,
            ) as response:
                data = await response.json()
                
                results = []
                items = data.get("items", [])
                
                for i, item in enumerate(items[:self.config.max_results]):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        engine=SearchEngineType.GOOGLE,
                        rank=i + 1,
                        published_date=item.get("pagemap", {}).get("metatags", [{}])[0].get("date"),
                        raw_data=item,
                    ))
                
                return results
                
        except aiohttp.ClientError as e:
            raise CrawlError(f"Google搜索失败: {e}", source_type=DataSourceType.INTERNET_API)
    
    async def _search_baidu(self, query: str, **kwargs) -> List[SearchResult]:
        """
        百度搜索
        
        Args:
            query: 搜索查询
            **kwargs: 额外参数
            
        Returns:
            搜索结果列表
        """
        api_key = self.config.baidu_api_key
        if not api_key:
            raise CrawlError("百度 API Key未配置", source_type=DataSourceType.INTERNET_API)
        
        # 百度搜索API参数
        params = {
            "apikey": api_key,
            "q": query,
            "rn": self.config.max_results,
            "pn": kwargs.get("pn", 0),
        }
        
        try:
            async with self._session.post(
                "https://api.baidu.com/json/sms/v3/SearchService",
                json=params,
                proxy=self.config.proxy,
            ) as response:
                data = await response.json()
                
                results = []
                items = data.get("results", [])
                
                for i, item in enumerate(items[:self.config.max_results]):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("abstract", ""),
                        engine=SearchEngineType.BAIDU,
                        rank=i + 1,
                        raw_data=item,
                    ))
                
                return results
                
        except aiohttp.ClientError as e:
            raise CrawlError(f"百度搜索失败: {e}", source_type=DataSourceType.INTERNET_API)
    
    def _has_api_key(self, engine: SearchEngineType) -> bool:
        """检查是否配置了API Key"""
        if engine == SearchEngineType.DUCKDUCKGO:
            return True  # DuckDuckGo不需要API Key
        elif engine == SearchEngineType.BING:
            return bool(self.config.bing_api_key)
        elif engine == SearchEngineType.GOOGLE:
            return bool(self.config.google_api_key) and bool(self.config.google_cx)
        elif engine == SearchEngineType.BAIDU:
            return bool(self.config.baidu_api_key)
        return False
    
    def _select_available_engine(
        self,
        exclude: Optional[List[SearchEngineType]] = None,
    ) -> Optional[SearchEngineType]:
        """选择可用的搜索引擎"""
        exclude = exclude or []
        
        # 优先顺序：DuckDuckGo（免费） > Bing > Google > 百度
        priority_order = [
            SearchEngineType.DUCKDUCKGO,
            SearchEngineType.BING,
            SearchEngineType.GOOGLE,
            SearchEngineType.BAIDU,
        ]
        
        for engine in priority_order:
            if engine not in exclude and self._has_api_key(engine):
                return engine
        
        return None
    
    async def fetch(self, url: str, **kwargs) -> CrawlResult:
        """
        获取单个URL内容
        
        Args:
            url: 目标URL
            **kwargs: 额外参数
            
        Returns:
            爬取结果
        """
        if not self._session:
            self.start()
        
        try:
            async with self._session.get(
                url,
                proxy=self.config.proxy,
            ) as response:
                content = await response.text()
                
                self._record_success()
                
                return CrawlResult(
                    url=str(response.url),
                    status_code=response.status,
                    content=content,
                    headers=dict(response.headers),
                    source_type=DataSourceType.INTERNET_API,
                    elapsed_time=asyncio.get_event_loop().time() - asyncio.get_event_loop().time(),
                )
                
        except aiohttp.ClientError as e:
            self._record_error()
            raise CrawlError(f"请求失败: {url}, 错误: {e}", url=url)
    
    async def fetch_many(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """
        批量获取多个URL
        
        Args:
            urls: 目标URL列表
            **kwargs: 额外参数
            
        Returns:
            爬取结果列表
        """
        tasks = [self.fetch(url, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, CrawlResult)]
    
    async def crawl(self, target: str, **kwargs) -> SearchResult:
        """
        执行爬取任务
        
        Args:
            target: 搜索查询或URL
            **kwargs: 额外参数
            
        Returns:
            搜索结果
        """
        # 如果是URL，获取内容
        if self.validate_url(target):
            result = await self.fetch(target, **kwargs)
            return SearchResult(
                title=target,
                url=target,
                snippet=result.content[:200] if result.content else "",
                engine=SearchEngineType.DUCKDUCKGO,
                raw_data={"content": result.content[:500]},
            )
        
        # 否则执行搜索
        response = await self.search(target, **kwargs)
        if response.results:
            return response.results[0]
        
        raise CrawlError(f"搜索无结果: {target}")
    
    async def multi_search(
        self,
        query: str,
        engines: Optional[List[SearchEngineType]] = None,
        **kwargs,
    ) -> Dict[SearchEngineType, SearchResponse]:
        """
        多引擎搜索
        
        Args:
            query: 搜索查询
            engines: 搜索引擎列表，默认使用所有可用引擎
            **kwargs: 额外参数
            
        Returns:
            各引擎的搜索响应字典
        """
        if engines is None:
            engines = [
                e for e in SearchEngineType
                if self._has_api_key(e)
            ]
        
        tasks = {
            engine: self.search(query, engine=engine, **kwargs)
            for engine in engines
        }
        
        results = {}
        for engine, task in tasks.items():
            results[engine] = await task
        
        return results
    
    async def aggregate_search(
        self,
        query: str,
        engines: Optional[List[SearchEngineType]] = None,
        **kwargs,
    ) -> List[SearchResult]:
        """
        聚合多引擎搜索结果
        
        Args:
            query: 搜索查询
            engines: 搜索引擎列表
            **kwargs: 额外参数
            
        Returns:
            聚合后的搜索结果列表（按相关性排序）
        """
        multi_results = await self.multi_search(query, engines, **kwargs)
        
        all_results = []
        for engine, response in multi_results.items():
            if response.success:
                all_results.extend(response.results)
        
        # 去重（基于URL）
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        # 按排名排序
        unique_results.sort(key=lambda r: r.rank)
        
        return unique_results[:self.config.max_results]