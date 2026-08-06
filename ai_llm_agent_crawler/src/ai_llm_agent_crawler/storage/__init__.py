"""
NAS存储管理模块

提供分布式存储、文件管理和数据备份功能。

模块组成:
- backends: 存储后端抽象和实现（本地、S3/MinIO等）
- allocation: 数据池自动分配策略
- replication: 数据冗余备份机制
- monitor: 存储池监控和容量管理
- pool: NAS存储池管理器（整合所有功能）
"""

# 存储后端
from ai_llm_agent_crawler.storage.backends import (
    StorageBackend,
    StorageBackendConfig,
    StorageBackendType,
    StorageInfo,
    LocalStorageBackend,
    S3StorageBackend,
)

# 数据池分配
from ai_llm_agent_crawler.storage.allocation import (
    AllocationPolicy,
    AllocationRequest,
    AllocationResult,
    AllocationStrategy,
    BackendMetrics,
    DataPoolAllocator,
)

# 数据冗余备份
from ai_llm_agent_crawler.storage.replication import (
    ConsistencyCheckResult,
    ConsistencyLevel,
    ReplicaInfo,
    ReplicationManager,
    ReplicationMode,
    ReplicationResult,
)

# 存储监控
from ai_llm_agent_crawler.storage.monitor import (
    Alert,
    AlertLevel,
    CapacityManager,
    CapacityThreshold,
    MonitoringReport,
    MetricType,
    StorageMetric,
    StorageMonitor,
)

# NAS存储池管理器
from ai_llm_agent_crawler.storage.pool import (
    NASStoragePool,
    NASStoragePoolConfig,
    create_nas_pool,
)

# 多后端存储池 + 副本复制 + 纠删码（O5）
from ai_llm_agent_crawler.storage.pools import (
    PoolType,
    ObjectInfo,
    IntegrityReport,
    StoragePool,
    LocalPool,
    NASNfsPool,
    NASSmbPool,
    S3Pool,
    ReplicationResult,
    ReplicationManager,
    ReedSolomonCodec,
    gf_mul,
    gf_div,
)

__all__ = [
    # 存储后端
    "StorageBackend",
    "StorageBackendConfig",
    "StorageBackendType",
    "StorageInfo",
    "LocalStorageBackend",
    "S3StorageBackend",
    
    # 数据池分配
    "AllocationPolicy",
    "AllocationRequest",
    "AllocationResult",
    "AllocationStrategy",
    "BackendMetrics",
    "DataPoolAllocator",
    
    # 数据冗余备份
    "ConsistencyCheckResult",
    "ConsistencyLevel",
    "ReplicaInfo",
    "ReplicationManager",
    "ReplicationMode",
    "ReplicationResult",
    
    # 存储监控
    "Alert",
    "AlertLevel",
    "CapacityManager",
    "CapacityThreshold",
    "MonitoringReport",
    "MetricType",
    "StorageMetric",
    "StorageMonitor",
    
    # NAS存储池管理器
    "NASStoragePool",
    "NASStoragePoolConfig",
    "create_nas_pool",
    # 多后端存储池 + 副本复制 + 纠删码（O5）
    "PoolType",
    "ObjectInfo",
    "IntegrityReport",
    "StoragePool",
    "LocalPool",
    "NASNfsPool",
    "NASSmbPool",
    "S3Pool",
    "ReplicationResult",
    "ReplicationManager",
    "ReedSolomonCodec",
    "gf_mul",
    "gf_div",
]