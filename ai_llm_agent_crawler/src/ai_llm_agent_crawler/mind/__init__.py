"""
Mind数据集与数据池模块

提供Mind数据集生成、数据池管理、向量存储、特征提取等功能。

主要组件:
- Mind模型 (models): Mind数据结构、向量定义、数据池模型
- Mind数据集生成 (generator): 原理数据集、生成模型数据集
- 数据池管理 (pool): 数据池存储、索引、检索
- 特征编码器 (encoder): 文本、数值、序列等特征编码
- 向量存储 (vector_store): 向量索引、相似度搜索
"""

from ai_llm_agent_crawler.mind.models import (
    MindDataType,
    MindVectorType,
    DataSourceType,
    QualityGrade,
    MindVector,
    MindDataRecord,
    MindDataset,
    DataPool,
    PoolConfig,
    MindDatasetMeta,
    DataSource,
    EmbeddingConfig,
    VectorIndexConfig,
)

from ai_llm_agent_crawler.mind.generator import (
    PrincipleDatasetGenerator,
    GenerativeDatasetGenerator,
    MindDatasetGenerator,
    SyntheticDataAugmentor,
    EntropyDrivenGenerator,
)

from ai_llm_agent_crawler.mind.pool import (
    DataPoolManager,
    PoolIndex,
    PoolRetriever,
    PoolUpdater,
    MultiPoolRouter,
)

from ai_llm_agent_crawler.mind.encoder import (
    TextEncoder,
    NumericEncoder,
    SequenceEncoder,
    MultimodalEncoder,
    FeaturePipeline,
)

from ai_llm_agent_crawler.mind.vector_store import (
    VectorStore,
    VectorIndex,
    VectorSearchResult,
    HNSWIndex,
    FlatIndex,
    IVFIndex,
)

__all__ = [
    # 模型
    "MindDataType",
    "MindVectorType",
    "DataSourceType",
    "QualityGrade",
    "MindVector",
    "MindDataRecord",
    "MindDataset",
    "DataPool",
    "PoolConfig",
    "MindDatasetMeta",
    "DataSource",
    "EmbeddingConfig",
    "VectorIndexConfig",
    # 数据集生成
    "PrincipleDatasetGenerator",
    "GenerativeDatasetGenerator",
    "MindDatasetGenerator",
    "SyntheticDataAugmentor",
    "EntropyDrivenGenerator",
    # 数据池
    "DataPoolManager",
    "PoolIndex",
    "PoolRetriever",
    "PoolUpdater",
    "MultiPoolRouter",
    # 编码器
    "TextEncoder",
    "NumericEncoder",
    "SequenceEncoder",
    "MultimodalEncoder",
    "FeaturePipeline",
    # 向量存储
    "VectorStore",
    "VectorIndex",
    "VectorSearchResult",
    "HNSWIndex",
    "FlatIndex",
    "IVFIndex",
]
