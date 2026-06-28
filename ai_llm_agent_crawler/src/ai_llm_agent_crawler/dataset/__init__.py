"""
数据集生成模块

提供数据集的生成、处理和管理功能。
"""

from ai_llm_agent_crawler.dataset.generator import (
    DatasetConfig,
    DatasetGenerator,
    JSONDatasetGenerator,
    CSVFlatDatasetGenerator,
)
from ai_llm_agent_crawler.dataset.processor import DataProcessor

# 新增模块
from ai_llm_agent_crawler.dataset.schema import (
    DatasetFormat,
    DatasetType,
    DataQuality,
    AnnotationMethod,
    DataType,
    FieldSchema,
    LabelSchema,
    DatasetSchema,
    DatasetRecord,
    DatasetSplit,
    DatasetPipeline,
    DatasetVersion,
    DatasetMetadata,
    DataFormatConverter,
)
from ai_llm_agent_crawler.dataset.annotator import (
    AnnotationResult,
    AnnotationBatch,
    BaseAnnotator,
    RuleBasedAnnotator,
    PatternRuleAnnotator,
    KeywordRuleAnnotator,
    ModelBasedAnnotator,
    HeuristicAnnotator,
    AutoAnnotator,
    AnnotationRuleBuilder,
)
from ai_llm_agent_crawler.dataset.quality_validator import (
    ValidationLevel,
    ValidationError,
    ValidationReport,
    BaseValidator,
    SchemaValidator,
    CompletenessValidator,
    ConsistencyValidator,
    RangeValidator,
    PatternValidator,
    UniquenessValidator,
    OutlierValidator,
    DistributionValidator,
    QualityValidator,
    DataCleaner,
)
from ai_llm_agent_crawler.dataset.skill_engine import (
    SkillType,
    SkillStatus,
    SkillMetadata,
    SkillTemplate,
    GeneratedSkill,
    SkillGenerationConfig,
    SkillCodeGenerator,
    SkillEngine,
)
from ai_llm_agent_crawler.dataset.skill_optimizer import (
    FeedbackType,
    OptimizationStrategy,
    SkillFeedback,
    OptimizationRecord,
    OptimizationConfig,
    PerformanceMetrics,
    FeedbackCollector,
    SkillOptimizer,
    FeedbackLoopManager,
    SkillEvolutionSystem,
)
from ai_llm_agent_crawler.dataset.metadata_manager import (
    ChangeType,
    ChangeRecord,
    MetadataSearchQuery,
    MetadataSearchResult,
    MetadataStore,
    MetadataManager,
    DatasetLifecycleManager,
)

__all__ = [
    # 原有导出
    "DatasetConfig",
    "DatasetGenerator",
    "JSONDatasetGenerator",
    "CSVFlatDatasetGenerator",
    "DataProcessor",
    # Schema
    "DatasetFormat",
    "DatasetType",
    "DataQuality",
    "AnnotationMethod",
    "DataType",
    "FieldSchema",
    "LabelSchema",
    "DatasetSchema",
    "DatasetRecord",
    "DatasetSplit",
    "DatasetPipeline",
    "DatasetVersion",
    "DatasetMetadata",
    "DataFormatConverter",
    # Annotator
    "AnnotationResult",
    "AnnotationBatch",
    "BaseAnnotator",
    "RuleBasedAnnotator",
    "PatternRuleAnnotator",
    "KeywordRuleAnnotator",
    "ModelBasedAnnotator",
    "HeuristicAnnotator",
    "AutoAnnotator",
    "AnnotationRuleBuilder",
    # Quality Validator
    "ValidationLevel",
    "ValidationError",
    "ValidationReport",
    "BaseValidator",
    "SchemaValidator",
    "CompletenessValidator",
    "ConsistencyValidator",
    "RangeValidator",
    "PatternValidator",
    "UniquenessValidator",
    "OutlierValidator",
    "DistributionValidator",
    "QualityValidator",
    "DataCleaner",
    # Skill Engine
    "SkillType",
    "SkillStatus",
    "SkillMetadata",
    "SkillTemplate",
    "GeneratedSkill",
    "SkillGenerationConfig",
    "SkillCodeGenerator",
    "SkillEngine",
    # Skill Optimizer
    "FeedbackType",
    "OptimizationStrategy",
    "SkillFeedback",
    "OptimizationRecord",
    "OptimizationConfig",
    "PerformanceMetrics",
    "FeedbackCollector",
    "SkillOptimizer",
    "FeedbackLoopManager",
    "SkillEvolutionSystem",
    # Metadata Manager
    "ChangeType",
    "ChangeRecord",
    "MetadataSearchQuery",
    "MetadataSearchResult",
    "MetadataStore",
    "MetadataManager",
    "DatasetLifecycleManager",
]