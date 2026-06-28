"""
数据池自动分配策略模块

实现智能存储空间分配算法，包括容量均衡、优先级分配、标签匹配等策略。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ai_llm_agent_crawler.storage.backends import StorageBackend, StorageBackendConfig, StorageInfo
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class AllocationStrategy(Enum):
    """分配策略类型枚举"""
    ROUND_ROBIN = "round_robin"  # 轮询分配
    LEAST_USED = "least_used"  # 最少使用优先
    PRIORITY = "priority"  # 优先级分配
    WEIGHTED = "weighted"  # 权重分配
    TAG_MATCH = "tag_match"  # 标签匹配
    CAPACITY_BALANCED = "capacity_balanced"  # 容量均衡
    LATENCY_OPTIMIZED = "latency_optimized"  # 延迟优化


@dataclass
class AllocationRequest:
    """分配请求"""
    size: int  # 请求的数据大小（字节）
    path: str  # 文件路径
    tags: Optional[Dict[str, str]] = None  # 标签要求
    min_replicas: int = 1  # 最小副本数
    preferred_backend: Optional[str] = None  # 首选后端名称
    exclude_backends: Optional[List[str]] = None  # 排除的后端列表
    priority: int = 0  # 请求优先级


@dataclass
class AllocationResult:
    """分配结果"""
    success: bool  # 是否成功
    allocated_backends: List[str]  # 分配到的后端列表
    paths: Dict[str, str]  # 每个后端对应的路径
    total_available: int  # 总可用空间
    message: str  # 结果消息


@dataclass
class BackendMetrics:
    """后端指标"""
    name: str
    available_space: int
    usage_percent: float
    priority: int
    latency: Optional[float] = None  # 响应延迟（毫秒）
    bandwidth: Optional[float] = None  # 带宽（MB/s）
    error_rate: Optional[float] = None  # 错误率
    last_used: Optional[float] = None  # 最后使用时间戳
    tags: Optional[Dict[str, str]] = None


class AllocationPolicy:
    """
    分配策略
    
    根据不同的策略算法选择合适的存储后端进行数据分配。
    """
    
    def __init__(self, strategy: AllocationStrategy = AllocationStrategy.CAPACITY_BALANCED):
        """
        初始化分配策略
        
        Args:
            strategy: 分配策略类型
        """
        self.strategy = strategy
        self.logger = get_logger(f"{__name__}.AllocationPolicy")
    
    def select_backend(
        self,
        request: AllocationRequest,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> Optional[StorageBackend]:
        """
        根据策略选择最合适的存储后端
        
        Args:
            request: 分配请求
            backends: 可用后端列表
            metrics: 后端指标字典
            
        Returns:
            选中的后端，如果没有合适的返回None
        """
        if not backends:
            return None
        
        # 过滤符合条件的后端
        eligible = self._filter_eligible_backends(request, backends, metrics)
        
        if not eligible:
            self.logger.warning(f"没有符合条件的后端用于分配: {request.path}")
            return None
        
        # 根据策略选择
        selected = self._apply_strategy(request, eligible, metrics)
        
        return selected
    
    def select_multiple_backends(
        self,
        request: AllocationRequest,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics],
        count: int
    ) -> List[StorageBackend]:
        """
        选择多个后端用于副本存储
        
        Args:
            request: 分配请求
            backends: 可用后端列表
            metrics: 后端指标字典
            count: 需要的后端数量
            
        Returns:
            选中的后端列表
        """
        eligible = self._filter_eligible_backends(request, backends, metrics)
        
        if len(eligible) < count:
            self.logger.warning(
                f"可用后端数量({len(eligible)})小于请求副本数({count})"
            )
            return eligible
        
        # 按策略排序并选择前count个
        sorted_backends = self._sort_by_strategy(eligible, metrics)
        return sorted_backends[:count]
    
    def _filter_eligible_backends(
        self,
        request: AllocationRequest,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> List[StorageBackend]:
        """
        过滤符合条件的后端
        
        Args:
            request: 分配请求
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            符合条件的后端列表
        """
        eligible = []
        
        for backend in backends:
            name = backend.config.name
            
            # 检查连接状态
            if not backend.is_connected():
                continue
            
            # 检查读写权限
            if backend.config.read_only:
                continue
            
            # 检查容量
            if not backend.can_write(request.size):
                continue
            
            # 检查排除列表
            if request.exclude_backends and name in request.exclude_backends:
                continue
            
            # 检查首选后端
            if request.preferred_backend and name != request.preferred_backend:
                # 如果指定了首选后端且该后端可用，只使用首选后端
                if request.preferred_backend in [b.config.name for b in backends]:
                    continue
            
            # 检查标签匹配
            if request.tags:
                backend_tags = backend.config.tags or {}
                if not self._match_tags(request.tags, backend_tags):
                    continue
            
            eligible.append(backend)
        
        return eligible
    
    def _match_tags(self, required_tags: Dict[str, str], backend_tags: Dict[str, str]) -> bool:
        """
        检查标签是否匹配
        
        Args:
            required_tags: 要求的标签
            backend_tags: 后端标签
            
        Returns:
            是否匹配
        """
        for key, value in required_tags.items():
            if key not in backend_tags or backend_tags[key] != value:
                return False
        return True
    
    def _apply_strategy(
        self,
        request: AllocationRequest,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> StorageBackend:
        """
        应用分配策略选择后端
        
        Args:
            request: 分配请求
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            选中的后端
        """
        sorted_backends = self._sort_by_strategy(backends, metrics)
        return sorted_backends[0]
    
    def _sort_by_strategy(
        self,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> List[StorageBackend]:
        """
        根据策略排序后端
        
        Args:
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            排序后的后端列表
        """
        if self.strategy == AllocationStrategy.ROUND_ROBIN:
            return self._sort_round_robin(backends, metrics)
        elif self.strategy == AllocationStrategy.LEAST_USED:
            return self._sort_least_used(backends, metrics)
        elif self.strategy == AllocationStrategy.PRIORITY:
            return self._sort_priority(backends, metrics)
        elif self.strategy == AllocationStrategy.WEIGHTED:
            return self._sort_weighted(backends, metrics)
        elif self.strategy == AllocationStrategy.CAPACITY_BALANCED:
            return self._sort_capacity_balanced(backends, metrics)
        elif self.strategy == AllocationStrategy.LATENCY_OPTIMIZED:
            return self._sort_latency_optimized(backends, metrics)
        else:
            return backends
    
    def _sort_round_robin(
        self,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> List[StorageBackend]:
        """
        轮询排序 - 根据最后使用时间排序
        
        Args:
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            排序后的后端列表
        """
        def get_last_used(backend: StorageBackend) -> float:
            m = metrics.get(backend.config.name)
            return m.last_used if m and m.last_used else 0.0
        
        return sorted(backends, key=get_last_used)
    
    def _sort_least_used(
        self,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> List[StorageBackend]:
        """
        最少使用优先排序
        
        Args:
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            排序后的后端列表
        """
        def get_usage(backend: StorageBackend) -> float:
            m = metrics.get(backend.config.name)
            return m.usage_percent if m else 100.0
        
        return sorted(backends, key=get_usage)
    
    def _sort_priority(
        self,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> List[StorageBackend]:
        """
        优先级排序
        
        Args:
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            排序后的后端列表
        """
        def get_priority(backend: StorageBackend) -> int:
            m = metrics.get(backend.config.name)
            return m.priority if m else backend.config.priority
        
        return sorted(backends, key=get_priority, reverse=True)
    
    def _sort_weighted(
        self,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> List[StorageBackend]:
        """
        权重排序 - 综合考虑多个因素
        
        Args:
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            排序后的后端列表
        """
        def calculate_score(backend: StorageBackend) -> float:
            m = metrics.get(backend.config.name)
            if not m:
                return 0.0
            
            # 权重配置
            priority_weight = 0.3
            available_weight = 0.4
            usage_weight = 0.2
            latency_weight = 0.1
            
            # 计算各因素得分（归一化到0-1）
            priority_score = m.priority / 100.0 if m.priority else backend.config.priority / 100.0
            
            # 可用空间得分（越大越好）
            max_space = max((bm.available_space for bm in metrics.values() if bm), default=1)
            available_score = m.available_space / max_space if max_space > 0 else 0
            
            # 使用率得分（越低越好）
            usage_score = 1.0 - (m.usage_percent / 100.0)
            
            # 延迟得分（越低越好）
            latency_score = 1.0
            if m.latency and m.latency > 0:
                max_latency = max((bm.latency for bm in metrics.values() if bm and bm.latency), default=100)
                latency_score = 1.0 - (m.latency / max_latency) if max_latency > 0 else 0
            
            return (
                priority_score * priority_weight +
                available_score * available_weight +
                usage_score * usage_weight +
                latency_score * latency_weight
            )
        
        return sorted(backends, key=calculate_score, reverse=True)
    
    def _sort_capacity_balanced(
        self,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> List[StorageBackend]:
        """
        容量均衡排序 - 选择可用空间最大的
        
        Args:
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            排序后的后端列表
        """
        def get_available(backend: StorageBackend) -> int:
            m = metrics.get(backend.config.name)
            return m.available_space if m else 0
        
        return sorted(backends, key=get_available, reverse=True)
    
    def _sort_latency_optimized(
        self,
        backends: List[StorageBackend],
        metrics: Dict[str, BackendMetrics]
    ) -> List[StorageBackend]:
        """
        延迟优化排序
        
        Args:
            backends: 后端列表
            metrics: 后端指标
            
        Returns:
            排序后的后端列表
        """
        def get_latency(backend: StorageBackend) -> float:
            m = metrics.get(backend.config.name)
            return m.latency if m and m.latency else 1000.0
        
        return sorted(backends, key=get_latency)


class DataPoolAllocator:
    """
    数据池分配器
    
    负责管理数据池的智能分配，包括空间规划、负载均衡等。
    """
    
    def __init__(
        self,
        policy: Optional[AllocationPolicy] = None,
        min_replicas: int = 1,
        max_replicas: int = 3,
        reserved_space_percent: float = 10.0
    ):
        """
        初始化数据池分配器
        
        Args:
            policy: 分配策略
            min_replicas: 默认最小副本数
            max_replicas: 最大副本数
            reserved_space_percent: 保留空间百分比
        """
        self.policy = policy or AllocationPolicy(AllocationStrategy.CAPACITY_BALANCED)
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.reserved_space_percent = reserved_space_percent
        self._backends: Dict[str, StorageBackend] = {}
        self._metrics: Dict[str, BackendMetrics] = {}
        self.logger = get_logger(f"{__name__}.DataPoolAllocator")
    
    def register_backend(self, backend: StorageBackend) -> bool:
        """
        注册存储后端
        
        Args:
            backend: 存储后端
            
        Returns:
            注册是否成功
        """
        name = backend.config.name
        if name in self._backends:
            self.logger.warning(f"后端已存在: {name}")
            return False
        
        if not backend.connect():
            self.logger.error(f"后端连接失败: {name}")
            return False
        
        self._backends[name] = backend
        self._update_metrics(name, backend)
        self.logger.info(f"注册后端成功: {name}")
        return True
    
    def unregister_backend(self, name: str) -> bool:
        """
        注销存储后端
        
        Args:
            name: 后端名称
            
        Returns:
            注销是否成功
        """
        if name not in self._backends:
            return False
        
        backend = self._backends[name]
        backend.disconnect()
        del self._backends[name]
        del self._metrics[name]
        self.logger.info(f"注销后端: {name}")
        return True
    
    def get_backend(self, name: str) -> Optional[StorageBackend]:
        """
        获取指定后端
        
        Args:
            name: 后端名称
            
        Returns:
            存储后端
        """
        return self._backends.get(name)
    
    def get_all_backends(self) -> List[StorageBackend]:
        """
        获取所有后端
        
        Returns:
            后端列表
        """
        return list(self._backends.values())
    
    def allocate(
        self,
        path: str,
        size: int,
        tags: Optional[Dict[str, str]] = None,
        replicas: Optional[int] = None,
        preferred_backend: Optional[str] = None,
        exclude_backends: Optional[List[str]] = None
    ) -> AllocationResult:
        """
        分配存储空间
        
        Args:
            path: 文件路径
            size: 数据大小
            tags: 标签要求
            replicas: 副本数
            preferred_backend: 首选后端
            exclude_backends: 排除的后端
            
        Returns:
            分配结果
        """
        # 构建分配请求
        request = AllocationRequest(
            size=size,
            path=path,
            tags=tags,
            min_replicas=replicas or self.min_replicas,
            preferred_backend=preferred_backend,
            exclude_backends=exclude_backends
        )
        
        # 获取可用后端
        backends = self.get_all_backends()
        if not backends:
            return AllocationResult(
                success=False,
                allocated_backends=[],
                paths={},
                total_available=0,
                message="没有可用的存储后端"
            )
        
        # 更新指标
        self._refresh_metrics()
        
        # 选择后端
        replica_count = min(request.min_replicas, self.max_replicas, len(backends))
        selected = self.policy.select_multiple_backends(
            request, backends, self._metrics, replica_count
        )
        
        if not selected:
            return AllocationResult(
                success=False,
                allocated_backends=[],
                paths={},
                total_available=0,
                message="没有符合条件的存储后端"
            )
        
        # 计算可用空间
        total_available = sum(
            self._metrics.get(b.config.name, BackendMetrics(b.config.name, 0, 0, 0)).available_space
            for b in selected
        )
        
        # 生成分配路径
        paths = {backend.config.name: path for backend in selected}
        
        return AllocationResult(
            success=True,
            allocated_backends=[b.config.name for b in selected],
            paths=paths,
            total_available=total_available,
            message=f"成功分配到{len(selected)}个后端"
        )
    
    def get_allocation_status(self) -> Dict[str, Any]:
        """
        获取分配状态
        
        Returns:
            状态字典
        """
        self._refresh_metrics()
        
        status = {
            "backend_count": len(self._backends),
            "total_capacity": 0,
            "total_used": 0,
            "total_available": 0,
            "backends": {}
        }
        
        for name, metrics in self._metrics.items():
            status["total_capacity"] += metrics.available_space + int(
                metrics.available_space * metrics.usage_percent / (100 - metrics.usage_percent)
                if metrics.usage_percent < 100 else 0
            )
            status["total_used"] += int(metrics.available_space * metrics.usage_percent / 100)
            status["total_available"] += metrics.available_space
            
            status["backends"][name] = {
                "available_space": metrics.available_space,
                "usage_percent": metrics.usage_percent,
                "priority": metrics.priority,
                "tags": metrics.tags or {},
                "connected": self._backends[name].is_connected() if name in self._backends else False
            }
        
        return status
    
    def _update_metrics(self, name: str, backend: StorageBackend) -> None:
        """
        更新后端指标
        
        Args:
            name: 后端名称
            backend: 存储后端
        """
        info = backend.get_info()
        
        self._metrics[name] = BackendMetrics(
            name=name,
            available_space=info.available_size,
            usage_percent=info.usage_percent,
            priority=backend.config.priority,
            tags=backend.config.tags
        )
    
    def _refresh_metrics(self) -> None:
        """
        刷新所有后端指标
        """
        for name, backend in self._backends.items():
            self._update_metrics(name, backend)
    
    def can_allocate(self, size: int, replicas: int = 1) -> bool:
        """
        检查是否可以分配指定大小的空间
        
        Args:
            size: 数据大小
            replicas: 副本数
            
        Returns:
            是否可以分配
        """
        self._refresh_metrics()
        
        # 计算需要的总空间（考虑副本）
        required_total = size * replicas
        
        # 计算总可用空间（考虑保留空间）
        total_available = 0
        for metrics in self._metrics.values():
            # 保留一部分空间
            reserved = int(metrics.available_space * self.reserved_space_percent / 100)
            usable = metrics.available_space - reserved
            total_available += max(0, usable)
        
        return total_available >= required_total
    
    def get_best_backend_for_size(self, size: int) -> Optional[str]:
        """
        获取最适合存储指定大小数据的后端
        
        Args:
            size: 数据大小
            
        Returns:
            后端名称
        """
        request = AllocationRequest(size=size, path="")
        
        backends = self.get_all_backends()
        self._refresh_metrics()
        
        selected = self.policy.select_backend(request, backends, self._metrics)
        
        return selected.config.name if selected else None
    
    def balance_load(self) -> Dict[str, Any]:
        """
        负载均衡 - 在后端之间迁移数据
        
        Returns:
            均衡结果
        """
        self._refresh_metrics()
        
        # 计算平均使用率
        usage_rates = [m.usage_percent for m in self._metrics.values()]
        avg_usage = sum(usage_rates) / len(usage_rates) if usage_rates else 0
        
        # 识别过载和空闲的后端
        overloaded = []
        underloaded = []
        
        threshold = 20.0  # 使用率差异阈值
        
        for name, metrics in self._metrics.items():
            if metrics.usage_percent > avg_usage + threshold:
                overloaded.append(name)
            elif metrics.usage_percent < avg_usage - threshold:
                underloaded.append(name)
        
        return {
            "average_usage": avg_usage,
            "overloaded_backends": overloaded,
            "underloaded_backends": underloaded,
            "needs_balance": len(overloaded) > 0 and len(underloaded) > 0
        }