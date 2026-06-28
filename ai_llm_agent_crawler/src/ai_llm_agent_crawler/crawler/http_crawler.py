"""
HTTP爬虫模块

基于 aiohttp 和 requests 实现的同步/异步HTTP爬虫。
"""

from typing import Any, Dict, List, Optional

import aiohttp
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_llm_agent_crawler.crawler.base import (
    BaseCrawler,
    CrawlerConfig,
    CrawlError,
    CrawlResult,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class HTTPCrawler(BaseCrawler):
    """
    同步HTTP爬虫
    
    基于 requests 库实现的同步爬虫。
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        super().__init__(config)
        self._session: Optional[requests.Session] = None
    
    def _on_start(self) -> None:
        """启动时创建Session"""
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": self.config.user_agent, **self.config.headers}
        )
        if self.config.cookies:
            self._session.cookies.update(self.config.cookies)
        logger.info("HTTPCrawler已启动")
    
    def _on_stop(self) -> None:
        """停止时关闭Session"""
        if self._session:
            self._session.close()
            self._session = None
        logger.info("HTTPCrawler已停止")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch(self, url: str, **kwargs) -> CrawlResult:
        """
        同步获取单个URL（异步包装）
        
        Args:
            url: 目标URL
            **kwargs: 额外参数
            
        Returns:
            爬取结果
        """
        if not self._session:
            self.start()
        
        if not self.validate_url(url):
            raise CrawlError(f"Invalid URL: {url}", url=url)
        
        try:
            response = self._session.request(
                "GET",
                url,
                timeout=kwargs.get("timeout", self.config.timeout),
                proxies={"http": self.config.proxy, "https": self.config.proxy}
                if self.config.proxy
                else None,
                **kwargs,
            )
            response.raise_for_status()
            
            return CrawlResult(
                url=url,
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers),
                cookies=dict(response.cookies),
                elapsed_time=response.elapsed.total_seconds(),
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {url}, 错误: {e}")
            raise CrawlError(str(e), url=url)
    
    async def fetch_many(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """
        同步批量获取多个URL（异步包装）
        
        Args:
            urls: 目标URL列表
            **kwargs: 额外参数
            
        Returns:
            爬取结果列表
        """
        results = []
        for url in urls:
            try:
                result = await self.fetch(url, **kwargs)
                results.append(result)
            except CrawlError as e:
                logger.warning(f"跳过失败的URL: {e.url}")
                continue
        return results


class AsyncHTTPCrawler(BaseCrawler):
    """
    异步HTTP爬虫
    
    基于 aiohttp 库实现的异步爬虫，支持高并发。
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
    
    def _on_start(self) -> None:
        """启动时创建Session"""
        self._connector = aiohttp.TCPConnector(
            limit=self.config.concurrent_requests,
            limit_per_host=self.config.concurrent_requests // 2,
        )
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            headers={"User-Agent": self.config.user_agent, **self.config.headers},
            cookies=self.config.cookies or None,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
        )
        logger.info("AsyncHTTPCrawler已启动")
    
    def _on_stop(self) -> None:
        """停止时关闭Session"""
        if self._session:
            import asyncio

            asyncio.create_task(self._session.close())
            self._session = None
        if self._connector:
            self._connector = None
        logger.info("AsyncHTTPCrawler已停止")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch(self, url: str, **kwargs) -> CrawlResult:
        """
        异步获取单个URL
        
        Args:
            url: 目标URL
            **kwargs: 额外参数，支持 method, params, data, json, headers 等
            
        Returns:
            爬取结果
        """
        if not self._session:
            self.start()
        
        if not self.validate_url(url):
            raise CrawlError(f"Invalid URL: {url}", url=url)
        
        method = kwargs.pop("method", "GET")
        timeout = kwargs.pop("timeout", self.config.timeout)
        
        try:
            async with self._session.request(
                method,
                url,
                proxy=self.config.proxy,
                timeout=aiohttp.ClientTimeout(total=timeout),
                **kwargs,
            ) as response:
                content = await response.text()
                
                return CrawlResult(
                    url=str(response.url),
                    status_code=response.status,
                    content=content,
                    headers=dict(response.headers),
                    cookies=dict(response.cookies),
                    elapsed_time=response.request_info.headers.get("X-Elapsed-Time", 0.0),
                )
                
        except aiohttp.ClientError as e:
            logger.error(f"请求失败: {url}, 错误: {e}")
            raise CrawlError(str(e), url=url)
    
    async def fetch_many(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """
        异步批量获取多个URL
        
        Args:
            urls: 目标URL列表
            **kwargs: 额外参数
            
        Returns:
            爬取结果列表
        """
        import asyncio
        
        if not self._session:
            self.start()
        
        tasks = [self.fetch(url, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤失败的结果
        return [r for r in results if isinstance(r, CrawlResult)]