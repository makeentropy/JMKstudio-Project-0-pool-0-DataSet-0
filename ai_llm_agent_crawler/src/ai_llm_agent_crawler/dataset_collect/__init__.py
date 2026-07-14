"""
数据集收集与合成模块

提供数据收集、蒸馏、清洗、清算双层迭代流水线,
向量检索、领域Skills生成、SFT数据集构建等功能。

核心功能:
- 数据收集: 多源数据统一接入
- 双层迭代: 蒸馏-清洗-清算流水线
- 向量检索: FAISS索引构建与查询
- Skills生成: 28个领域标准化技能
- SFT生成: 标准化训练数据集输出
"""

from ai_llm_agent_crawler.dataset_collect.collector import (
    DataSource,
    CollectionConfig,
    CollectedData,
    DataCollector,
    MultiSourceCollector,
    CherryTreeCollector,
    ESP32DataCollector,
    InternetAPICollector,
)
from ai_llm_agent_crawler.dataset_collect.pipeline import (
    PipelineStage,
    DistillConfig,
    CleanConfig,
    AuditConfig,
    IterationConfig,
    DistillLayer,
    CleanLayer,
    AuditLayer,
    DoubleLayerPipeline,
    PipelineResult,
)
from ai_llm_agent_crawler.dataset_collect.vector_store import (
    VectorConfig,
    VectorEmbedding,
    VectorIndex,
    VectorStore,
    FAISSVectorStore,
)
from ai_llm_agent_crawler.dataset_collect.sft_generator import (
    SFTSchema,
    SFTSample,
    SFTGenerator,
    SFTBatchGenerator,
)

__all__ = [
    # Collector
    "DataSource",
    "CollectionConfig",
    "CollectedData",
    "DataCollector",
    "MultiSourceCollector",
    "CherryTreeCollector",
    "ESP32DataCollector",
    "InternetAPICollector",
    # Pipeline
    "PipelineStage",
    "DistillConfig",
    "CleanConfig",
    "AuditConfig",
    "IterationConfig",
    "DistillLayer",
    "CleanLayer",
    "AuditLayer",
    "DoubleLayerPipeline",
    "PipelineResult",
    # Vector Store
    "VectorConfig",
    "VectorEmbedding",
    "VectorIndex",
    "VectorStore",
    "FAISSVectorStore",
    # SFT Generator
    "SFTSchema",
    "SFTSample",
    "SFTGenerator",
    "SFTBatchGenerator",
]