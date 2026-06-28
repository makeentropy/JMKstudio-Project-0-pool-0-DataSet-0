"""
NAS存储池管理器

整合存储后端、数据池分配、冗余备份和监控模块，提供统一的NAS存储管理接口。
"""

from typing import Any, Callable, Dict, List, Optional, Union

from ai_llm_agent_crawler.storage.allocation import (
    AllocationPolicy,
    AllocationResult,
    AllocationStrategy,
    DataPoolAllocator,
)
from ai_llm_agent_crawler.storage.backends import (
    LocalStorageBackend,
    S3StorageBackend,
    StorageBackend,
    StorageBackendConfig,
    StorageBackendType,
    StorageInfo,
)
from ai_llm_agent_crawler.storage.monitor import (
    Alert,
    AlertLevel,
    CapacityManager,
    CapacityThreshold,
    MonitoringReport,
    StorageMonitor,
)
from ai_llm_agent_crawler.storage.replication import (
    ConsistencyCheckResult,
    ConsistencyLevel,
    ReplicationManager,
    ReplicationMode,
    ReplicationResult,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class NASStoragePoolConfig:
    """
    NAS存储池配置
    
    定义存储池的全局配置参数。
    """
    
    def __init__(
        self,
        default_replicas: int = 3,
        max_replicas: int = 5,
        min_replicas: int = 1,
        default_replication_mode: ReplicationMode = ReplicationMode.SYNC,
        default_consistency_level: ConsistencyLevel = ConsistencyLevel.QUORUM,
        default_allocation_strategy: AllocationStrategy = AllocationStrategy.CAPACITY_BALANCED,
        auto_balance: bool = True,
        auto_monitoring: bool = True,
        monitoring_interval_seconds: int = 60,
        capacity_warning_threshold: float = 70.0,
        capacity_error_threshold: float = 85.0,
        capacity_critical_threshold: float = 95.0,
        reserved_space_percent: float = 10.0,
        checksum_algorithm: str = "md5"
    ):
        """
        初始化NAS存储池配置
        
        Args:
            default_replicas: 默认副本数
            max_replicas: 最大副本数
            min_replicas: 最小副本数
            default_replication_mode: 默认复制模式
            default_consistency_level: 默认一致性级别
            default_allocation_strategy: 默认分配策略
            auto_balance: 是否自动负载均衡
            auto_monitoring: 是否自动监控
            monitoring_interval_seconds: 监控间隔（秒）
            capacity_warning_threshold: 容量警告阈值（百分比）
            capacity_error_threshold: 容量错误阈值（百分比）
            capacity_critical_threshold: 容量严重阈值（百分比）
            reserved_space_percent: 保留空间百分比
            checksum_algorithm: 校验和算法
        """
        self.default_replicas = default_replicas
        self.max_replicas = max_replicas
        self.min_replicas = min_replicas
        self.default_replication_mode = default_replication_mode
        self.default_consistency_level = default_consistency_level
        self.default_allocation_strategy = default_allocation_strategy
        self.auto_balance = auto_balance
        self.auto_monitoring = auto_monitoring
        self.monitoring_interval_seconds = monitoring_interval_seconds
        self.capacity_warning_threshold = capacity_warning_threshold
        self.capacity_error_threshold = capacity_error_threshold
        self.capacity_critical_threshold = capacity_critical_threshold
        self.reserved_space_percent = reserved_space_percent
        self.checksum_algorithm = checksum_algorithm


class NASStoragePool:
    """
    NAS存储池管理器
    
    提供统一的NAS存储管理接口，整合多个存储后端、智能分配、
    数据冗余备份和容量监控功能。
    """
    
    def __init__(self, config: Optional[NASStoragePoolConfig] = None):
        """
        初始化NAS存储池
        
        Args:
            config: 存储池配置
        """
        self.config = config or NASStoragePoolConfig()
        
        # 初始化各子模块
        self._allocator = self._create_allocator()
        self._replicator = self._create_replicator()
        self._monitor = self._create_monitor()
        self._capacity_manager = CapacityManager(self._monitor)
        
        self._backends: Dict[str, StorageBackend] = {}
        self.logger = get_logger(f"{__name__}.NASStoragePool")
    
    def _create_allocator(self) -> DataPoolAllocator:
        """创建数据池分配器"""
        policy = AllocationPolicy(self.config.default_allocation_strategy)
        return DataPoolAllocator(
            policy=policy,
            min_replicas=self.config.min_replicas,
            max_replicas=self.config.max_replicas,
            reserved_space_percent=self.config.reserved_space_percent
        )
    
    def _create_replicator(self) -> ReplicationManager:
        """创建复制管理器"""
        return ReplicationManager(
            default_mode=self.config.default_replication_mode,
            default_replicas=self.config.default_replicas,
            consistency_level=self.config.default_consistency_level,
            checksum_algorithm=self.config.checksum_algorithm
        )
    
    def _create_monitor(self) -> StorageMonitor:
        """创建存储监控器"""
        threshold = CapacityThreshold(
            warning_percent=self.config.capacity_warning_threshold,
            error_percent=self.config.capacity_error_threshold,
            critical_percent=self.config.capacity_critical_threshold,
            check_interval_seconds=self.config.monitoring_interval_seconds
        )
        return StorageMonitor(threshold=threshold)
    
    def add_backend(
        self,
        backend_type: StorageBackendType,
        name: str,
        root_path: str,
        max_size: Optional[int] = None,
        read_only: bool = False,
        priority: int = 0,
        tags: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> bool:
        """
        添加存储后端
        
        Args:
            backend_type: 后端类型
            name: 后端名称
            root_path: 根路径
            max_size: 最大容量限制
            read_only: 是否只读
            priority: 优先级
            tags: 标签
            **kwargs: 其他配置参数
            
        Returns:
            添加是否成功
        """
        if name in self._backends:
            self.logger.warning(f"后端已存在: {name}")
            return False
        
        # 创建后端配置
        backend_config = StorageBackendConfig(
            backend_type=backend_type,
            name=name,
            root_path=root_path,
            max_size=max_size,
            read_only=read_only,
            priority=priority,
            tags=tags,
            **kwargs
        )
        
        # 创建对应的后端实例
        backend = self._create_backend(backend_config)
        
        if not backend:
            self.logger.error(f"无法创建后端: {backend_type}")
            return False
        
        # 连接后端
        if not backend.connect():
            self.logger.error(f"后端连接失败: {name}")
            return False
        
        # 注册到所有子模块
        self._backends[name] = backend
        self._allocator.register_backend(backend)
        self._replicator.register_backend(backend)
        self._monitor.register_backend(backend)
        
        self.logger.info(f"添加后端成功: {name} ({backend_type.value})")
        return True
    
    def _create_backend(self, config: StorageBackendConfig) -> Optional[StorageBackend]:
        """
        创建存储后端实例
        
        Args:
            config: 后端配置
            
        Returns:
            存储后端实例
        """
        if config.backend_type == StorageBackendType.LOCAL:
            return LocalStorageBackend(config)
        elif config.backend_type in [StorageBackendType.S3, StorageBackendType.MINIO]:
            return S3StorageBackend(config)
        else:
            # 其他类型暂不支持，返回本地存储作为默认
            self.logger.warning(f"不支持的后端类型 {config.backend_type}, 使用本地存储")
            return LocalStorageBackend(config)
    
    def remove_backend(self, name: str) -> bool:
        """
        移除存储后端
        
        Args:
            name: 后端名称
            
        Returns:
            移除是否成功
        """
        if name not in self._backends:
            return False
        
        # 从所有子模块注销
        self._allocator.unregister_backend(name)
        self._replicator.unregister_backend(name)
        self._monitor.unregister_backend(name)
        
        del self._backends[name]
        
        self.logger.info(f"移除后端: {name}")
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
    
    def list_backends(self) -> List[str]:
        """
        列出所有后端
        
        Returns:
            后端名称列表
        """
        return list(self._backends.keys())
    
    def write(
        self,
        path: str,
        data: Union[bytes, str],
        replicas: Optional[int] = None,
        preferred_backend: Optional[str] = None,
        exclude_backends: Optional[List[str]] = None,
        overwrite: bool = False,
        tags: Optional[Dict[str, str]] = None
    ) -> ReplicationResult:
        """
        写入数据
        
        Args:
            path: 文件路径
            data: 数据内容
            replicas: 副本数
            preferred_backend: 首选后端
            exclude_backends: 排除的后端列表
            overwrite: 是否覆盖
            tags: 数据标签
            
        Returns:
            复制结果
        """
        # 分配存储空间
        size = len(data) if isinstance(data, bytes) else len(data.encode("utf-8"))
        
        allocation = self._allocator.allocate(
            path=path,
            size=size,
            tags=tags,
            replicas=replicas,
            preferred_backend=preferred_backend,
            exclude_backends=exclude_backends
        )
        
        if not allocation.success:
            return ReplicationResult(
                success=False,
                total_replicas=replicas or self.config.default_replicas,
                successful_replicas=0,
                failed_backends=[],
                message=allocation.message
            )
        
        # 使用复制管理器写入数据
        result = self._replicator.write_with_replication(
            path=path,
            data=data,
            replicas=len(allocation.allocated_backends),
            mode=self.config.default_replication_mode,
            backends=allocation.allocated_backends,
            overwrite=overwrite
        )
        
        return result
    
    def read(
        self,
        path: str,
        prefer_backend: Optional[str] = None
    ) -> Optional[bytes]:
        """
        读取数据
        
        Args:
            path: 文件路径
            prefer_backend: 首选后端
            
        Returns:
            数据内容
        """
        return self._replicator.read_with_replication(path, prefer_backend)
    
    def delete(
        self,
        path: str,
        delete_all_replicas: bool = True
    ) -> Dict[str, bool]:
        """
        删除数据
        
        Args:
            path: 文件路径
            delete_all_replicas: 是否删除所有副本
            
        Returns:
            每个后端的删除结果
        """
        return self._replicator.delete_with_replication(path, delete_all_replicas)
    
    def exists(self, path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            path: 文件路径
            
        Returns:
            是否存在
        """
        # 检查副本信息
        replicas = self._replicator.get_replica_info(path)
        if replicas:
            return True
        
        # 检查所有后端
        for backend in self._backends.values():
            if backend.is_connected() and backend.exists(path):
                return True
        
        return False
    
    def list_files(self, path: str = "", recursive: bool = False) -> List[str]:
        """
        列出文件
        
        Args:
            path: 基础路径
            recursive: 是否递归
            
        Returns:
            文件路径列表
        """
        files = set()
        
        for backend in self._backends.values():
            if backend.is_connected():
                backend_files = backend.list_files(path, recursive)
                files.update(backend_files)
        
        return sorted(list(files))
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            path: 文件路径
            
        Returns:
            文件信息字典
        """
        info = {
            "path": path,
            "exists": False,
            "replicas": [],
            "total_size": 0,
            "checksum": None,
            "backends": {}
        }
        
        replicas = self._replicator.get_replica_info(path)
        
        if replicas:
            info["exists"] = True
            info["replicas"] = [
                {
                    "backend": r.backend_name,
                    "synced": r.synced,
                    "size": r.size,
                    "checksum": r.checksum
                }
                for r in replicas
            ]
            
            # 取第一个副本的信息
            if replicas[0].size:
                info["total_size"] = replicas[0].size
            if replicas[0].checksum:
                info["checksum"] = replicas[0].checksum
        
        # 从各后端获取详细信息
        for name, backend in self._backends.items():
            if backend.is_connected() and backend.exists(path):
                metadata = backend.get_file_metadata(path)
                if metadata:
                    info["backends"][name] = metadata
        
        return info
    
    def sync_replicas(self, path: str, force: bool = False) -> ReplicationResult:
        """
        同步副本
        
        Args:
            path: 文件路径
            force: 是否强制同步
            
        Returns:
            同步结果
        """
        return self._replicator.sync_replicas(path, force)
    
    def check_consistency(self, paths: Optional[List[str]] = None) -> ConsistencyCheckResult:
        """
        检查一致性
        
        Args:
            paths: 文件路径列表
            
        Returns:
            一致性检查结果
        """
        return self._replicator.check_consistency(paths)
    
    def repair_consistency(self, path: str) -> ReplicationResult:
        """
        修复一致性
        
        Args:
            path: 文件路径
            
        Returns:
            修复结果
        """
        return self._replicator.repair_consistency(path)
    
    def get_storage_status(self) -> Dict[str, Any]:
        """
        获取存储状态
        
        Returns:
            状态字典
        """
        return {
            "allocator": self._allocator.get_allocation_status(),
            "replicator": self._replicator.get_replication_status(),
            "monitor": self._monitor.get_current_status(),
            "capacity": self._capacity_manager.get_capacity_summary()
        }
    
    def get_monitoring_report(self) -> MonitoringReport:
        """
        获取监控报告
        
        Returns:
            监控报告
        """
        return self._monitor.generate_report()
    
    def check_capacity(self) -> List[Alert]:
        """
        检查容量
        
        Returns:
            告警列表
        """
        return self._monitor.check_capacity()
    
    def plan_capacity(
        self,
        required_size: int,
        replicas: int = 1,
        growth_factor: float = 1.5
    ) -> Dict[str, Any]:
        """
        容量规划
        
        Args:
            required_size: 需求大小
            replicas: 副本数
            growth_factor: 增长因子
            
        Returns:
            规划结果
        """
        return self._capacity_manager.plan_capacity(required_size, replicas, growth_factor)
    
    def balance_load(self) -> Dict[str, Any]:
        """
        负载均衡
        
        Returns:
            均衡结果
        """
        return self._allocator.balance_load()
    
    def can_allocate(self, size: int, replicas: int = 1) -> bool:
        """
        检查是否可以分配
        
        Args:
            size: 数据大小
            replicas: 副本数
            
        Returns:
            是否可以分配
        """
        return self._allocator.can_allocate(size, replicas)
    
    def get_best_backend(self, size: int) -> Optional[str]:
        """
        获取最佳后端
        
        Args:
            size: 数据大小
            
        Returns:
            后端名称
        """
        return self._allocator.get_best_backend_for_size(size)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        添加告警处理函数
        
        Args:
            handler: 处理函数
        """
        self._monitor.add_alert_handler(handler)
    
    def cleanup_storage(
        self,
        backend_name: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, int]:
        """
        清理存储
        
        Args:
            backend_name: 后端名称
            force: 是否强制清理
            
        Returns:
            清理结果
        """
        return self._capacity_manager.cleanup_storage(backend_name, force)
    
    def migrate_data(
        self,
        path: str,
        source_backend: str,
        target_backend: str
    ) -> bool:
        """
        迁移数据
        
        Args:
            path: 文件路径
            source_backend: 源后端名称
            target_backend: 目标后端名称
            
        Returns:
            是否成功
        """
        source = self._backends.get(source_backend)
        target = self._backends.get(target_backend)
        
        if not source or not target:
            self.logger.error("源或目标后端不存在")
            return False
        
        if not source.is_connected() or not target.is_connected():
            self.logger.error("源或目标后端未连接")
            return False
        
        # 读取数据
        data = source.read(path)
        if not data:
            self.logger.error(f"无法从源读取数据: {path}")
            return False
        
        # 写入目标
        if not target.write(path, data, overwrite=True):
            self.logger.error(f"无法写入目标: {path}")
            return False
        
        # 更新副本信息
        replicas = self._replicator.get_replica_info(path)
        
        # 如果源后端在副本列表中，移除它
        # 如果目标后端不在副本列表中，添加它
        
        self.logger.info(f"数据迁移成功: {path} 从 {source_backend} 到 {target_backend}")
        return True
    
    def get_config(self) -> NASStoragePoolConfig:
        """
        获取配置
        
        Returns:
            配置对象
        """
        return self.config
    
    def update_config(self, config: NASStoragePoolConfig) -> None:
        """
        更新配置
        
        Args:
            config: 新配置
        """
        self.config = config
        
        # 更新子模块配置
        # 这里需要重新创建子模块或更新它们的配置
        # 为了简化，我们只更新一些关键配置
        
        self._allocator.min_replicas = config.min_replicas
        self._allocator.max_replicas = config.max_replicas
        self._allocator.reserved_space_percent = config.reserved_space_percent
        
        self._replicator.default_replicas = config.default_replicas
        self._replicator.default_mode = config.default_replication_mode
        self._replicator.consistency_level = config.default_consistency_level
        self._replicator.checksum_algorithm = config.checksum_algorithm
        
        self._monitor.threshold.warning_percent = config.capacity_warning_threshold
        self._monitor.threshold.error_percent = config.capacity_error_threshold
        self._monitor.threshold.critical_percent = config.capacity_critical_threshold
        
        self.logger.info("配置已更新")


def create_nas_pool(
    backend_configs: Optional[List[Dict[str, Any]]] = None,
    pool_config: Optional[NASStoragePoolConfig] = None
) -> NASStoragePool:
    """
    创建NAS存储池
    
    Args:
        backend_configs: 后端配置列表
        pool_config: 存储池配置
        
    Returns:
        NAS存储池实例
    """
    pool = NASStoragePool(pool_config)
    
    if backend_configs:
        for config in backend_configs:
            backend_type = StorageBackendType(config.get("backend_type", "local"))
            name = config.get("name", "default")
            root_path = config.get("root_path", "/tmp/nas_storage")
            
            pool.add_backend(
                backend_type=backend_type,
                name=name,
                root_path=root_path,
                max_size=config.get("max_size"),
                read_only=config.get("read_only", False),
                priority=config.get("priority", 0),
                tags=config.get("tags"),
                **config.get("extra", {})
            )
    
    return pool