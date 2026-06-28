"""
反爬虫策略和代理池模块

提供：
- 代理池管理（支持多种代理来源）
- User-Agent轮换
- 请求头轮换
- 速率限制和自适应延迟
- 反检测策略
- Cookie池管理
- 指纹隐藏
"""

import asyncio
import hashlib
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import aiohttp
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ProxyType(str, Enum):
    """代理类型枚举"""
    
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(str, Enum):
    """代理状态枚举"""
    
    ACTIVE = "active"          # 可用
    INACTIVE = "inactive"      # 不可用
    TESTING = "testing"        # 正在测试
    BLOCKED = "blocked"        # 被封锁
    EXPIRED = "expired"        # 已过期


class Proxy(BaseModel):
    """代理模型"""
    
    # 代理信息
    host: str = Field(description="代理主机")
    port: int = Field(description="代理端口")
    proxy_type: ProxyType = Field(default=ProxyType.HTTP, description="代理类型")
    
    # 认证信息
    username: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    
    # 状态信息
    status: ProxyStatus = Field(default=ProxyStatus.ACTIVE, description="状态")
    
    # 性能指标
    latency: float = Field(default=0.0, description="延迟（秒）")
    success_rate: float = Field(default=100.0, description="成功率")
    last_used: Optional[str] = Field(default=None, description="最后使用时间")
    last_success: Optional[str] = Field(default=None, description="最后成功时间")
    last_failure: Optional[str] = Field(default=None, description="最后失败时间")
    
    # 使用统计
    total_requests: int = Field(default=0, description="总请求次数")
    success_requests: int = Field(default=0, description="成功请求次数")
    failed_requests: int = Field(default=0, description="失败请求次数")
    
    # 元数据
    country: Optional[str] = Field(default=None, description="国家")
    city: Optional[str] = Field(default=None, description="城市")
    provider: Optional[str] = Field(default=None, description="提供商")
    expire_time: Optional[str] = Field(default=None, description="过期时间")
    
    # 其他信息
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他信息")
    
    def get_url(self) -> str:
        """
        获取代理URL
        
        Returns:
            代理URL字符串
        """
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"
    
    def record_success(self, latency: float = 0.0) -> None:
        """记录成功使用"""
        self.total_requests += 1
        self.success_requests += 1
        self.last_used = datetime.now().isoformat()
        self.last_success = datetime.now().isoformat()
        
        if latency > 0:
            # 更新平均延迟
            self.latency = (
                (self.latency * (self.success_requests - 1) + latency)
                / self.success_requests
            )
        
        # 更新成功率
        self.success_rate = (self.success_requests / self.total_requests) * 100
        
        # 更新状态
        if self.status == ProxyStatus.TESTING:
            self.status = ProxyStatus.ACTIVE
    
    def record_failure(self) -> None:
        """记录失败"""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_used = datetime.now().isoformat()
        self.last_failure = datetime.now().isoformat()
        
        # 更新成功率
        self.success_rate = (self.success_requests / self.total_requests) * 100
        
        # 检查是否需要标记为不可用
        if self.success_rate < 20 and self.total_requests > 5:
            self.status = ProxyStatus.INACTIVE
    
    def is_available(self) -> bool:
        """检查是否可用"""
        if self.status == ProxyStatus.BLOCKED or self.status == ProxyStatus.EXPIRED:
            return False
        
        if self.expire_time:
            expire_dt = datetime.fromisoformat(self.expire_time)
            if datetime.now() > expire_dt:
                self.status = ProxyStatus.EXPIRED
                return False
        
        return self.status in [ProxyStatus.ACTIVE, ProxyStatus.TESTING]


class UserAgent(BaseModel):
    """User-Agent模型"""
    
    ua_string: str = Field(description="User-Agent字符串")
    browser: str = Field(default="", description="浏览器类型")
    browser_version: str = Field(default="", description="浏览器版本")
    os: str = Field(default="", description="操作系统")
    os_version: str = Field(default="", description="操作系统版本")
    device_type: str = Field(default="desktop", description="设备类型")
    popularity: float = Field(default=1.0, description="流行度权重")
    last_used: Optional[str] = Field(default=None, description="最后使用时间")
    use_count: int = Field(default=0, description="使用次数")


class RequestHeader(BaseModel):
    """请求头模板"""
    
    name: str = Field(description="模板名称")
    headers: Dict[str, str] = Field(description="请求头字典")
    priority: float = Field(default=1.0, description="优先级权重")
    last_used: Optional[str] = Field(default=None, description="最后使用时间")
    use_count: int = Field(default=0, description="使用次数")


class ProxyPoolConfig(BaseModel):
    """代理池配置"""
    
    # 代理池大小
    max_proxies: int = Field(default=100, description="最大代理数量")
    min_proxies: int = Field(default=5, description="最小可用代理数量")
    
    # 测试配置
    test_url: str = Field(
        default="http://httpbin.org/ip",
        description="代理测试URL",
    )
    test_timeout: int = Field(default=10, description="测试超时时间")
    test_interval: int = Field(default=300, description="测试间隔（秒）")
    
    # 选择策略
    selection_strategy: str = Field(
        default="random",
        description="代理选择策略（random/round_robin/weighted/least_used）",
    )
    
    # 健康检查配置
    health_check_enabled: bool = Field(default=True, description="启用健康检查")
    health_check_interval: int = Field(default=60, description="健康检查间隔")
    
    # 代理来源配置
    auto_fetch_proxies: bool = Field(default=False, description="自动获取代理")
    proxy_api_url: Optional[str] = Field(default=None, description="代理API URL")
    proxy_api_key: Optional[str] = Field(default=None, description="代理API Key")


class UserAgentPoolConfig(BaseModel):
    """User-Agent池配置"""
    
    # 池大小
    max_user_agents: int = Field(default=50, description="最大User-Agent数量")
    
    # 轮换策略
    rotation_strategy: str = Field(
        default="random",
        description="轮换策略（random/round_robin/weighted/device_based）",
    )
    
    # 设备类型权重
    device_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "desktop": 0.6,
            "mobile": 0.3,
            "tablet": 0.1,
        },
        description="设备类型权重",
    )
    
    # 更新频率
    rotation_interval: int = Field(default=1, description="轮换间隔（每次请求）")


class RateLimitConfig(BaseModel):
    """速率限制配置"""
    
    # 基础限制
    requests_per_second: float = Field(default=1.0, description="每秒请求限制")
    requests_per_minute: int = Field(default=30, description="每分钟请求限制")
    requests_per_hour: int = Field(default=500, description="每小时请求限制")
    requests_per_day: int = Field(default=10000, description="每天请求限制")
    
    # 自适应限制
    adaptive_enabled: bool = Field(default=True, description="启用自适应限制")
    min_delay: float = Field(default=0.5, description="最小延迟")
    max_delay: float = Field(default=30.0, description="最大延迟")
    backoff_factor: float = Field(default=2.0, description="退避因子")
    
    # 基于响应调整
    adjust_on_429: bool = Field(default=True, description="429响应时调整")
    adjust_on_timeout: bool = Field(default=True, description="超时时调整")
    adjust_on_error: bool = Field(default=True, description="错误时调整")


class ProxyPool:
    """
    代理池管理器
    
    功能：
    - 代理获取和管理
    - 代理健康检查
    - 代理选择策略
    - 代理性能统计
    """
    
    def __init__(self, config: Optional[ProxyPoolConfig] = None):
        self.config = config or ProxyPoolConfig()
        self._proxies: List[Proxy] = []
        self._lock = asyncio.Lock()
        self._last_health_check: float = 0
    
    async def add_proxy(
        self,
        host: str,
        port: int,
        proxy_type: ProxyType = ProxyType.HTTP,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ) -> Proxy:
        """
        添加代理
        
        Args:
            host: 代理主机
            port: 代理端口
            proxy_type: 代理类型
            username: 用户名
            password: 密码
            **kwargs: 其他参数
            
        Returns:
            添加的代理对象
        """
        proxy = Proxy(
            host=host,
            port=port,
            proxy_type=proxy_type,
            username=username,
            password=password,
            **kwargs,
        )
        
        async with self._lock:
            # 检查是否已存在
            existing = [
                p for p in self._proxies
                if p.host == host and p.port == port
            ]
            if existing:
                logger.warning(f"代理已存在: {host}:{port}")
                return existing[0]
            
            # 添加到池中
            self._proxies.append(proxy)
            logger.info(f"添加代理: {host}:{port}")
            
            # 测试代理
            if self.config.health_check_enabled:
                await self.test_proxy(proxy)
        
        return proxy
    
    async def add_proxies_from_list(
        self,
        proxy_list: List[str],
        proxy_type: ProxyType = ProxyType.HTTP,
    ) -> List[Proxy]:
        """
        从列表批量添加代理
        
        Args:
            proxy_list: 代理列表（格式: host:port 或 user:pass@host:port）
            proxy_type: 代理类型
            
        Returns:
            添加的代理列表
        """
        added_proxies = []
        
        for proxy_str in proxy_list:
            try:
                # 解析代理字符串
                if "@" in proxy_str:
                    auth, host_port = proxy_str.split("@")
                    username, password = auth.split(":")
                    host, port = host_port.split(":")
                else:
                    username = None
                    password = None
                    host, port = proxy_str.split(":")
                
                proxy = await self.add_proxy(
                    host=host,
                    port=int(port),
                    proxy_type=proxy_type,
                    username=username,
                    password=password,
                )
                added_proxies.append(proxy)
                
            except Exception as e:
                logger.warning(f"解析代理失败: {proxy_str}, 错误: {e}")
        
        return added_proxies
    
    async def get_proxy(
        self,
        exclude: Optional[List[Proxy]] = None,
    ) -> Optional[Proxy]:
        """
        获取可用代理
        
        Args:
            exclude: 排除的代理列表
            
        Returns:
            可用的代理，无可用代理时返回None
        """
        async with self._lock:
            # 过滤可用代理
            available = [
                p for p in self._proxies
                if p.is_available() and (exclude is None or p not in exclude)
            ]
            
            if not available:
                logger.warning("无可用代理")
                return None
            
            # 根据策略选择代理
            selected = self._select_proxy(available)
            
            return selected
    
    def _select_proxy(self, proxies: List[Proxy]) -> Proxy:
        """
        根据策略选择代理
        
        Args:
            proxies: 可用代理列表
            
        Returns:
            选中的代理
        """
        strategy = self.config.selection_strategy
        
        if strategy == "random":
            return random.choice(proxies)
        
        elif strategy == "round_robin":
            # 选择使用次数最少的
            return min(proxies, key=lambda p: p.use_count)
        
        elif strategy == "weighted":
            # 根据成功率和延迟加权选择
            weights = []
            for proxy in proxies:
                # 成功率权重（越高越好）
                success_weight = proxy.success_rate / 100
                # 延迟权重（越低越好）
                latency_weight = 1 / (1 + proxy.latency)
                # 综合权重
                weight = success_weight * 0.7 + latency_weight * 0.3
                weights.append(weight)
            
            # 加权随机选择
            total_weight = sum(weights)
            r = random.uniform(0, total_weight)
            cumulative = 0
            for i, weight in enumerate(weights):
                cumulative += weight
                if r <= cumulative:
                    return proxies[i]
            
            return proxies[-1]
        
        elif strategy == "least_used":
            # 选择最近使用时间最早的
            proxies_with_time = [
                p for p in proxies
                if p.last_used
            ]
            if proxies_with_time:
                return min(proxies_with_time, key=lambda p: p.last_used)
            return random.choice(proxies)
        
        else:
            return random.choice(proxies)
    
    async def test_proxy(self, proxy: Proxy) -> bool:
        """
        测试代理
        
        Args:
            proxy: 待测试的代理
            
        Returns:
            是否可用
        """
        proxy.status = ProxyStatus.TESTING
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config.test_url,
                    proxy=proxy.get_url(),
                    timeout=aiohttp.ClientTimeout(total=self.config.test_timeout),
                ) as response:
                    if response.status == 200:
                        latency = time.time() - start_time
                        proxy.record_success(latency)
                        logger.info(
                            f"代理测试成功: {proxy.host}:{proxy.port}, "
                            f"延迟: {latency:.2f}s"
                        )
                        return True
                    else:
                        proxy.record_failure()
                        logger.warning(
                            f"代理测试失败: {proxy.host}:{proxy.port}, "
                            f"状态码: {response.status}"
                        )
                        return False
                        
        except Exception as e:
            proxy.record_failure()
            logger.warning(
                f"代理测试异常: {proxy.host}:{proxy.port}, "
                f"错误: {e}"
            )
            return False
    
    async def health_check(self) -> Dict[str, int]:
        """
        执行健康检查
        
        Returns:
            健康检查结果统计
        """
        now = time.time()
        if now - self._last_health_check < self.config.health_check_interval:
            return {}
        
        self._last_health_check = now
        
        results = {
            "total": len(self._proxies),
            "active": 0,
            "inactive": 0,
            "testing": 0,
            "blocked": 0,
        }
        
        # 测试所有代理
        for proxy in self._proxies:
            await self.test_proxy(proxy)
            results[proxy.status.value] += 1
        
        logger.info(f"健康检查完成: {results}")
        return results
    
    async def remove_proxy(self, proxy: Proxy) -> bool:
        """
        移除代理
        
        Args:
            proxy: 要移除的代理
            
        Returns:
            是否成功移除
        """
        async with self._lock:
            if proxy in self._proxies:
                self._proxies.remove(proxy)
                logger.info(f"移除代理: {proxy.host}:{proxy.port}")
                return True
            return False
    
    async def remove_inactive_proxies(self) -> int:
        """
        移除所有不可用代理
        
        Returns:
            移除的数量
        """
        async with self._lock:
            inactive = [
                p for p in self._proxies
                if not p.is_available()
            ]
            for proxy in inactive:
                self._proxies.remove(proxy)
            
            logger.info(f"移除不可用代理: {len(inactive)}个")
            return len(inactive)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取代理池统计
        
        Returns:
            统计信息
        """
        return {
            "total_proxies": len(self._proxies),
            "active_proxies": len([p for p in self._proxies if p.is_available()]),
            "avg_latency": sum(p.latency for p in self._proxies) / len(self._proxies)
            if self._proxies else 0,
            "avg_success_rate": sum(p.success_rate for p in self._proxies) / len(self._proxies)
            if self._proxies else 0,
        }


class UserAgentPool:
    """
    User-Agent池管理器
    
    功能：
    - User-Agent轮换
    - 设备类型匹配
    - 流行度权重
    """
    
    # 预置User-Agent列表
    DEFAULT_USER_AGENTS = [
        # Chrome Desktop
        UserAgent(
            ua_string="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            browser="Chrome",
            browser_version="120.0",
            os="Windows",
            os_version="10.0",
            device_type="desktop",
            popularity=0.9,
        ),
        UserAgent(
            ua_string="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            browser="Chrome",
            browser_version="120.0",
            os="Mac OS X",
            os_version="10_15_7",
            device_type="desktop",
            popularity=0.8,
        ),
        # Firefox Desktop
        UserAgent(
            ua_string="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            browser="Firefox",
            browser_version="121.0",
            os="Windows",
            os_version="10.0",
            device_type="desktop",
            popularity=0.7,
        ),
        UserAgent(
            ua_string="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            browser="Firefox",
            browser_version="121.0",
            os="Mac OS X",
            os_version="10.15",
            device_type="desktop",
            popularity=0.6,
        ),
        # Safari Desktop
        UserAgent(
            ua_string="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            browser="Safari",
            browser_version="17.2",
            os="Mac OS X",
            os_version="10_15_7",
            device_type="desktop",
            popularity=0.5,
        ),
        # Chrome Mobile (Android)
        UserAgent(
            ua_string="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            browser="Chrome Mobile",
            browser_version="120.0",
            os="Android",
            os_version="13",
            device_type="mobile",
            popularity=0.85,
        ),
        UserAgent(
            ua_string="Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            browser="Chrome Mobile",
            browser_version="120.0",
            os="Android",
            os_version="13",
            device_type="mobile",
            popularity=0.8,
        ),
        # Safari Mobile (iPhone)
        UserAgent(
            ua_string="Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            browser="Safari Mobile",
            browser_version="17.2",
            os="iOS",
            os_version="17_2",
            device_type="mobile",
            popularity=0.9,
        ),
        UserAgent(
            ua_string="Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            browser="Safari Mobile",
            browser_version="17.2",
            os="iOS",
            os_version="17_2",
            device_type="tablet",
            popularity=0.4,
        ),
        # Edge Desktop
        UserAgent(
            ua_string="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            browser="Edge",
            browser_version="120.0",
            os="Windows",
            os_version="10.0",
            device_type="desktop",
            popularity=0.65,
        ),
    ]
    
    def __init__(self, config: Optional[UserAgentPoolConfig] = None):
        self.config = config or UserAgentPoolConfig()
        self._user_agents: List[UserAgent] = list(self.DEFAULT_USER_AGENTS)
        self._last_rotation_time: float = 0
        self._rotation_count: int = 0
    
    def add_user_agent(self, user_agent: UserAgent) -> None:
        """添加自定义User-Agent"""
        self._user_agents.append(user_agent)
        logger.info(f"添加User-Agent: {user_agent.browser}")
    
    def get_user_agent(
        self,
        device_type: Optional[str] = None,
        exclude: Optional[List[UserAgent]] = None,
    ) -> UserAgent:
        """
        获取User-Agent
        
        Args:
            device_type: 设备类型限制
            exclude: 排除的User-Agent
            
        Returns:
            选中的User-Agent
        """
        # 过滤
        candidates = self._user_agents
        if device_type:
            candidates = [
                ua for ua in candidates
                if ua.device_type == device_type
            ]
        if exclude:
            candidates = [
                ua for ua in candidates
                if ua not in exclude
            ]
        
        if not candidates:
            candidates = self._user_agents
        
        # 根据策略选择
        strategy = self.config.rotation_strategy
        
        if strategy == "random":
            selected = random.choice(candidates)
        
        elif strategy == "weighted":
            # 根据流行度加权
            weights = [ua.popularity for ua in candidates]
            total = sum(weights)
            r = random.uniform(0, total)
            cumulative = 0
            for i, ua in enumerate(candidates):
                cumulative += ua.popularity
                if r <= cumulative:
                    selected = ua
                    break
        
        elif strategy == "round_robin":
            # 按使用次数选择
            selected = min(candidates, key=lambda ua: ua.use_count)
        
        elif strategy == "device_based":
            # 先根据设备权重选择设备类型，再随机选择该类型的UA
            device_weights = self.config.device_weights
            devices = list(device_weights.keys())
            weights = list(device_weights.values())
            chosen_device = random.choices(devices, weights=weights)[0]
            
            device_candidates = [
                ua for ua in candidates
                if ua.device_type == chosen_device
            ]
            if device_candidates:
                selected = random.choice(device_candidates)
            else:
                selected = random.choice(candidates)
        
        else:
            selected = random.choice(candidates)
        
        # 更新使用统计
        selected.use_count += 1
        selected.last_used = datetime.now().isoformat()
        self._rotation_count += 1
        
        return selected
    
    def get_ua_string(
        self,
        device_type: Optional[str] = None,
    ) -> str:
        """
        获取User-Agent字符串
        
        Args:
            device_type: 设备类型
            
        Returns:
            User-Agent字符串
        """
        ua = self.get_user_agent(device_type)
        return ua.ua_string
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_user_agents": len(self._user_agents),
            "rotation_count": self._rotation_count,
            "by_device": {
                device: len([
                    ua for ua in self._user_agents
                    if ua.device_type == device
                ])
                for device in ["desktop", "mobile", "tablet"]
            },
        }


class RequestHeaderPool:
    """
    请求头池管理器
    
    功能：
    - 请求头模板管理
    - 智能轮换
    - 反检测优化
    """
    
    # 预置请求头模板
    DEFAULT_HEADERS = [
        RequestHeader(
            name="chrome_desktop",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
            priority=1.0,
        ),
        RequestHeader(
            name="chrome_mobile",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
            priority=0.9,
        ),
        RequestHeader(
            name="firefox_desktop",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            },
            priority=0.8,
        ),
        RequestHeader(
            name="safari_desktop",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh-Hans;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            priority=0.7,
        ),
        RequestHeader(
            name="safari_mobile",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh-Hans;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            },
            priority=0.85,
        ),
    ]
    
    def __init__(self):
        self._headers: List[RequestHeader] = list(self.DEFAULT_HEADERS)
    
    def add_header_template(self, template: RequestHeader) -> None:
        """添加请求头模板"""
        self._headers.append(template)
        logger.info(f"添加请求头模板: {template.name}")
    
    def get_headers(
        self,
        base_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        获取请求头
        
        Args:
            base_headers: 基础请求头
            
        Returns:
            合并后的请求头字典
        """
        # 加权随机选择模板
        weights = [h.priority for h in self._headers]
        total = sum(weights)
        r = random.uniform(0, total)
        cumulative = 0
        selected = self._headers[-1]
        for header in self._headers:
            cumulative += header.priority
            if r <= cumulative:
                selected = header
                break
        
        # 更新统计
        selected.use_count += 1
        selected.last_used = datetime.now().isoformat()
        
        # 合并请求头
        result = dict(selected.headers)
        if base_headers:
            result.update(base_headers)
        
        return result


class RateLimiter:
    """
    速率限制器
    
    功能：
    - 多维度速率限制
    - 自适应延迟调整
    - 响应状态感知
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        # 时间戳记录
        self._timestamps: Dict[str, List[float]] = {
            "second": [],
            "minute": [],
            "hour": [],
            "day": [],
        }
        
        # 自适应延迟
        self._current_delay: float = self.config.min_delay
        self._consecutive_errors: int = 0
        self._consecutive_success: int = 0
    
    async def acquire(self) -> None:
        """
        获取请求许可
        
        根据配置的速率限制等待适当时间。
        """
        now = time.time()
        
        # 检查各时间窗口的限制
        # 每秒限制
        if self.config.requests_per_second > 0:
            second_requests = [
                ts for ts in self._timestamps["second"]
                if now - ts < 1
            ]
            if len(second_requests) >= self.config.requests_per_second:
                wait_time = 1 - (now - min(second_requests))
                await asyncio.sleep(wait_time)
        
        # 每分钟限制
        if self.config.requests_per_minute > 0:
            minute_requests = [
                ts for ts in self._timestamps["minute"]
                if now - ts < 60
            ]
            if len(minute_requests) >= self.config.requests_per_minute:
                wait_time = 60 - (now - min(minute_requests))
                await asyncio.sleep(wait_time)
        
        # 每小时限制
        if self.config.requests_per_hour > 0:
            hour_requests = [
                ts for ts in self._timestamps["hour"]
                if now - ts < 3600
            ]
            if len(hour_requests) >= self.config.requests_per_hour:
                wait_time = 3600 - (now - min(hour_requests))
                await asyncio.sleep(wait_time)
        
        # 每天限制
        if self.config.requests_per_day > 0:
            day_requests = [
                ts for ts in self._timestamps["day"]
                if now - ts < 86400
            ]
            if len(day_requests) >= self.config.requests_per_day:
                wait_time = 86400 - (now - min(day_requests))
                await asyncio.sleep(wait_time)
        
        # 自适应延迟
        if self.config.adaptive_enabled:
            await asyncio.sleep(self._current_delay)
        
        # 记录时间戳
        now = time.time()
        self._timestamps["second"].append(now)
        self._timestamps["minute"].append(now)
        self._timestamps["hour"].append(now)
        self._timestamps["day"].append(now)
        
        # 清理过期时间戳
        self._cleanup_timestamps(now)
    
    def _cleanup_timestamps(self, now: float) -> None:
        """清理过期的时间戳"""
        for key in self._timestamps:
            max_age = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400,
            }
            self._timestamps[key] = [
                ts for ts in self._timestamps[key]
                if now - ts < max_age[key]
            ]
    
    def adjust_on_response(self, status_code: int, success: bool) -> None:
        """
        根据响应调整速率
        
        Args:
            status_code: HTTP状态码
            success: 是否成功
        """
        if not self.config.adaptive_enabled:
            return
        
        if success:
            self._consecutive_success += 1
            self._consecutive_errors = 0
            
            # 成功后逐渐降低延迟
            if self._consecutive_success > 10:
                self._current_delay = max(
                    self.config.min_delay,
                    self._current_delay * 0.9,
                )
        
        else:
            self._consecutive_errors += 1
            self._consecutive_success = 0
            
            # 根据错误类型调整
            if status_code == 429 and self.config.adjust_on_429:
                # 速率限制错误，显著增加延迟
                self._current_delay = min(
                    self.config.max_delay,
                    self._current_delay * self.config.backoff_factor * 2,
                )
                logger.warning(f"收到429响应，延迟调整为: {self._current_delay}s")
            
            elif status_code in [502, 503, 504] and self.config.adjust_on_error:
                # 服务器错误，适度增加延迟
                self._current_delay = min(
                    self.config.max_delay,
                    self._current_delay * self.config.backoff_factor,
                )
                logger.warning(f"收到服务器错误，延迟调整为: {self._current_delay}s")
            
            else:
                # 其他错误，轻微增加延迟
                self._current_delay = min(
                    self.config.max_delay,
                    self._current_delay + 1,
                )
    
    def get_current_delay(self) -> float:
        """获取当前延迟"""
        return self._current_delay
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        now = time.time()
        return {
            "requests_last_second": len([
                ts for ts in self._timestamps["second"]
                if now - ts < 1
            ]),
            "requests_last_minute": len([
                ts for ts in self._timestamps["minute"]
                if now - ts < 60
            ]),
            "requests_last_hour": len([
                ts for ts in self._timestamps["hour"]
                if now - ts < 3600
            ]),
            "requests_last_day": len([
                ts for ts in self._timestamps["day"]
                if now - ts < 86400
            ]),
            "current_delay": self._current_delay,
            "consecutive_errors": self._consecutive_errors,
            "consecutive_success": self._consecutive_success,
        }


class AntiDetectionManager:
    """
    反检测管理器
    
    综合管理代理池、User-Agent池、请求头池和速率限制器，
    提供一站式反爬虫解决方案。
    """
    
    def __init__(
        self,
        proxy_config: Optional[ProxyPoolConfig] = None,
        ua_config: Optional[UserAgentPoolConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        self.proxy_pool = ProxyPool(proxy_config)
        self.ua_pool = UserAgentPool(ua_config)
        self.header_pool = RequestHeaderPool()
        self.rate_limiter = RateLimiter(rate_limit_config)
        
        # Cookie池
        self._cookies: Dict[str, Dict[str, str]] = {}
    
    async def get_request_config(
        self,
        domain: Optional[str] = None,
        use_proxy: bool = True,
    ) -> Dict[str, Any]:
        """
        获取完整的请求配置
        
        Args:
            domain: 目标域名（用于Cookie选择）
            use_proxy: 是否使用代理
            
        Returns:
            包含headers、proxy、cookies的配置字典
        """
        # 等待速率限制
        await self.rate_limiter.acquire()
        
        # 获取User-Agent
        ua = self.ua_pool.get_user_agent()
        
        # 获取请求头
        headers = self.header_pool.get_headers({"User-Agent": ua.ua_string})
        
        # 获取代理
        proxy = None
        if use_proxy:
            proxy_obj = await self.proxy_pool.get_proxy()
            if proxy_obj:
                proxy = proxy_obj.get_url()
        
        # 获取Cookie
        cookies = {}
        if domain and domain in self._cookies:
            cookies = self._cookies[domain]
        
        return {
            "headers": headers,
            "proxy": proxy,
            "cookies": cookies,
            "user_agent_info": {
                "browser": ua.browser,
                "device_type": ua.device_type,
            },
        }
    
    def record_response(
        self,
        status_code: int,
        success: bool,
        proxy_url: Optional[str] = None,
        domain: Optional[str] = None,
        cookies: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        记录响应结果
        
        Args:
            status_code: HTTP状态码
            success: 是否成功
            proxy_url: 使用的代理URL
            domain: 响应域名
            cookies: 响应Cookies
        """
        # 调整速率限制
        self.rate_limiter.adjust_on_response(status_code, success)
        
        # 更新代理状态
        if proxy_url:
            for proxy in self.proxy_pool._proxies:
                if proxy.get_url() == proxy_url:
                    if success:
                        proxy.record_success()
                    else:
                        proxy.record_failure()
                    break
        
        # 保存Cookie
        if domain and cookies:
            self._cookies[domain] = cookies
    
    def add_cookie(self, domain: str, cookies: Dict[str, str]) -> None:
        """添加Cookie"""
        self._cookies[domain] = cookies
        logger.info(f"添加Cookie: {domain}")
    
    async def setup_proxies(
        self,
        proxy_list: List[str],
        proxy_type: ProxyType = ProxyType.HTTP,
    ) -> int:
        """
        设置代理池
        
        Args:
            proxy_list: 代理列表
            proxy_type: 代理类型
            
        Returns:
            成功添加的数量
        """
        proxies = await self.proxy_pool.add_proxies_from_list(proxy_list, proxy_type)
        return len(proxies)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        return {
            "proxy_pool": self.proxy_pool.get_stats(),
            "ua_pool": self.ua_pool.get_stats(),
            "rate_limiter": self.rate_limiter.get_stats(),
            "cookies_count": len(self._cookies),
        }