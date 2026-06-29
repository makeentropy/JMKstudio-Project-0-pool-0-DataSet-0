"""
维度空间质能质量子奇点系统模块

提供多维数据空间管理、质能质量计算和量子奇点分析功能。

主要组件:
- 数据模型 (models): 定义维度类型、质量指标、奇点等核心数据结构
- 维度分类器 (classifier): 支持内容、时间、空间、语义等多维数据分析
- 质量评估器 (quality): 完整性、准确性、一致性、时效性等多维度质量评估
- 奇点检测器 (singularity): 识别数据质量的临界点和奇点
- 数据预处理器 (preprocessor): 清洗、转换、标准化等多种预处理操作
"""

from ai_llm_agent_crawler.dimension.models import (
    DataMassEnergy,
    DimensionClassificationResult,
    DimensionFeature,
    DimensionSpaceConfig,
    DimensionType,
    DimensionVector,
    PreprocessingConfig,
    PreprocessingResult,
    QualityAssessment,
    QualityMetric,
    QualityMetricType,
    SingularityDetectionResult,
    SingularityPoint,
    SingularitySeverity,
    SingularityType,
)

from ai_llm_agent_crawler.dimension.classifier import (
    DimensionClassifier,
    DimensionRule,
    SemanticDimensionAnalyzer,
    SpatialDimensionAnalyzer,
    TemporalDimensionAnalyzer,
)

from ai_llm_agent_crawler.dimension.quality import (
    DataMassEnergyCalculator,
    QualityAssessor,
    QualityDimensionAnalyzer,
)

from ai_llm_agent_crawler.dimension.singularity import (
    SingularityDetector,
    SingularityMonitor,
    SingularityRule,
)

from ai_llm_agent_crawler.dimension.preprocessor import (
    CleaningRule,
    DataPipeline,
    DataPreprocessor,
    DataValidator,
    FieldTransformRule,
    FieldTransformer,
)

from ai_llm_agent_crawler.dimension.probe import (
    DimensionProbeResult,
    DimensionSpaceProbe,
    DimensionTopology,
    PathProbePoint,
    PathProbeResult,
    ProbeDimension,
    ProbeReport,
)

__all__ = [
    # 数据模型
    "DimensionType",
    "DimensionFeature",
    "DimensionVector",
    "QualityMetricType",
    "QualityMetric",
    "QualityAssessment",
    "SingularityType",
    "SingularitySeverity",
    "SingularityPoint",
    "SingularityDetectionResult",
    "DimensionClassificationResult",
    "DataMassEnergy",
    "PreprocessingConfig",
    "PreprocessingResult",
    "DimensionSpaceConfig",

    # 维度分类器
    "DimensionClassifier",
    "DimensionRule",
    "TemporalDimensionAnalyzer",
    "SpatialDimensionAnalyzer",
    "SemanticDimensionAnalyzer",

    # 质量评估器
    "QualityAssessor",
    "DataMassEnergyCalculator",
    "QualityDimensionAnalyzer",

    # 奇点检测器
    "SingularityDetector",
    "SingularityMonitor",
    "SingularityRule",

    # 数据预处理器
    "DataPreprocessor",
    "CleaningRule",
    "FieldTransformRule",
    "FieldTransformer",
    "DataValidator",
    "DataPipeline",

    # 维度空间探针
    "ProbeDimension",
    "DimensionProbeResult",
    "ProbeReport",
    "DimensionSpaceProbe",
    "PathProbePoint",
    "PathProbeResult",
    "DimensionTopology",
]