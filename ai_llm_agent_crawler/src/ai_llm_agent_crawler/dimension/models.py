"""
维度空间质能质量子奇点系统 - 核心数据模型

定义维度类型、质量指标、奇点检测等核心数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field


class DimensionType(str, Enum):
    """数据维度类型枚举"""
    CONTENT = "content"  # 内容维度：文本内容、结构、格式
    TEMPORAL = "temporal"  # 时间维度：创建时间、更新时间、时效性
    SPATIAL = "spatial"  # 空间维度：地理位置、来源位置
    SEMANTIC = "semantic"  # 语义维度：主题、情感、意图
    STRUCTURAL = "structural"  # 结构维度：数据结构、格式、模式
    STATISTICAL = "statistical"  # 统计维度：数值特征、分布特征
    RELATIONAL = "relational"  # 关系维度：关联、引用、依赖
    QUALITY = "quality"  # 质量维度：完整性、准确性等质量指标


class QualityMetricType(str, Enum):
    """数据质量指标类型枚举"""
    COMPLETENESS = "completeness"  # 完整性
    ACCURACY = "accuracy"  # 准确性
    CONSISTENCY = "consistency"  # 一致性
    TIMELINESS = "timeliness"  # 时效性
    VALIDITY = "validity"  # 有效性
    UNIQUENSS = "uniqueness"  # 唯一性
    RELEVANCE = "relevance"  # 相关性


class SingularityType(str, Enum):
    """奇点类型枚举"""
    QUALITY_THRESHOLD = "quality_threshold"  # 质量阈值奇点
    DIMENSION_COLLAPSE = "dimension_collapse"  # 维度坍缩奇点
    DATA_ANOMALY = "data_anomaly"  # 数据异常奇点
    CRITICAL_POINT = "critical_point"  # 临界点奇点
    ENERGY_SINGULARITY = "energy_singularity"  # 质能奇点
    QUANTUM_ENTANGLEMENT = "quantum_entanglement"  # 量子纠缠点


class SingularitySeverity(str, Enum):
    """奇点严重程度枚举"""
    LOW = "low"  # 低：轻微异常
    MEDIUM = "medium"  # 中：需要关注
    HIGH = "high"  # 高：需要立即处理
    CRITICAL = "critical"  # 严重：系统级问题


class DimensionFeature(BaseModel):
    """维度特征模型"""
    dimension_type: DimensionType
    feature_name: str
    feature_value: Union[float, str, List[Any], Dict[str, Any]]
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class DimensionVector(BaseModel):
    """维度向量模型 - 多维数据的向量表示"""
    features: List[DimensionFeature] = Field(default_factory=list)
    vector_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组"""
        return np.array([f.feature_value for f in self.features
                        if isinstance(f.feature_value, (int, float))])

    def get_dimension_features(self, dimension_type: DimensionType) -> List[DimensionFeature]:
        """获取特定维度的特征"""
        return [f for f in self.features if f.dimension_type == dimension_type]


class QualityMetric(BaseModel):
    """数据质量指标模型"""
    metric_type: QualityMetricType
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    @property
    def is_acceptable(self) -> bool:
        """判断质量是否可接受"""
        return self.score >= self.threshold

    class Config:
        use_enum_values = True


class QualityAssessment(BaseModel):
    """数据质量评估结果模型"""
    metrics: List[QualityMetric] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    assessment_time: datetime = Field(default_factory=datetime.now)
    data_source: Optional[str] = None
    record_count: int = Field(default=0, ge=0)

    def get_metric(self, metric_type: QualityMetricType) -> Optional[QualityMetric]:
        """获取特定类型的质量指标"""
        for metric in self.metrics:
            if metric.metric_type == metric_type:
                return metric
        return None

    def calculate_weighted_score(self) -> float:
        """计算加权质量分数"""
        if not self.metrics:
            return 0.0
        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(m.score * m.weight for m in self.metrics)
        return weighted_sum / total_weight

    class Config:
        use_enum_values = True


@dataclass
class SingularityPoint:
    """奇点模型 - 数据质量临界点"""
    singularity_type: SingularityType
    severity: SingularitySeverity
    location: Tuple[int, ...]  # 奇点位置（可以是多维坐标）
    dimension: DimensionType
    quality_score: float
    threshold: float
    detected_at: datetime = field(default_factory=datetime.now)
    description: str = ""
    affected_records: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_critical(self) -> bool:
        """判断是否为严重奇点"""
        return self.severity in (SingularitySeverity.HIGH, SingularitySeverity.CRITICAL)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "singularity_type": self.singularity_type.value,
            "severity": self.severity.value,
            "location": self.location,
            "dimension": self.dimension.value,
            "quality_score": self.quality_score,
            "threshold": self.threshold,
            "detected_at": self.detected_at.isoformat(),
            "description": self.description,
            "affected_records": self.affected_records,
            "metadata": self.metadata,
        }


class SingularityDetectionResult(BaseModel):
    """奇点检测结果模型"""
    singularities: List[SingularityPoint] = Field(default_factory=list)
    total_singularity_count: int = Field(default=0)
    critical_count: int = Field(default=0)
    detection_time: datetime = Field(default_factory=datetime.now)
    detection_duration_ms: float = Field(default=0.0)

    def add_singularity(self, singularity: SingularityPoint) -> None:
        """添加奇点"""
        self.singularities.append(singularity)
        self.total_singularity_count = len(self.singularities)
        if singularity.is_critical:
            self.critical_count += 1

    def get_singularities_by_type(self, singularity_type: SingularityType) -> List[SingularityPoint]:
        """获取特定类型的奇点"""
        return [s for s in self.singularities if s.singularity_type == singularity_type]

    def get_singularities_by_severity(self, severity: SingularitySeverity) -> List[SingularityPoint]:
        """获取特定严重程度的奇点"""
        return [s for s in self.singularities if s.severity == severity]

    def get_critical_singularities(self) -> List[SingularityPoint]:
        """获取所有严重奇点"""
        return [s for s in self.singularities if s.is_critical]


class DimensionClassificationResult(BaseModel):
    """维度分类结果模型"""
    dimension_type: DimensionType
    confidence: float = Field(ge=0.0, le=1.0)
    features: List[DimensionFeature] = Field(default_factory=list)
    sub_dimensions: List[str] = Field(default_factory=list)
    classification_time: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class DataMassEnergy(BaseModel):
    """数据质能模型 - 数据的"质量"与"能量"概念"""
    data_mass: float = Field(default=0.0, ge=0.0)  # 数据量（大小、记录数等）
    data_energy: float = Field(default=0.0, ge=0.0)  # 数据能量（信息价值、活跃度等）
    quality_factor: float = Field(default=1.0, ge=0.0)  # 质量因子
    density: float = Field(default=0.0, ge=0.0)  # 数据密度
    entropy: float = Field(default=0.0, ge=0.0)  # 数据熵

    @property
    def effective_mass(self) -> float:
        """有效质量 = 数据质量 * 数据量"""
        return self.data_mass * self.quality_factor

    @property
    def mass_energy_ratio(self) -> float:
        """质能比"""
        if self.data_mass == 0:
            return 0.0
        return self.data_energy / self.data_mass

    def calculate_singularity_risk(self) -> float:
        """计算奇点风险指数"""
        # 基于密度、熵和质能比计算风险
        density_risk = min(self.density / 100.0, 1.0)  # 高密度可能触发奇点
        entropy_risk = min(self.entropy / 10.0, 1.0)  # 高熵值表示不确定性
        ratio_risk = min(abs(self.mass_energy_ratio - 1.0), 1.0)  # 质能失衡风险

        return (density_risk * 0.4 + entropy_risk * 0.3 + ratio_risk * 0.3)


class PreprocessingConfig(BaseModel):
    """预处理配置模型"""
    remove_duplicates: bool = Field(default=True)
    handle_missing_values: bool = Field(default=True)
    missing_value_strategy: str = Field(default="mean")  # mean, median, mode, drop, fill
    missing_value_fill: Optional[Any] = None
    normalize_values: bool = Field(default=False)
    normalization_method: str = Field(default="minmax")  # minmax, zscore, robust
    remove_outliers: bool = Field(default=False)
    outlier_method: str = Field(default="iqr")  # iqr, zscore, isolation
    outlier_threshold: float = Field(default=1.5)
    standardize_formats: bool = Field(default=True)
    encoding: str = Field(default="utf-8")
    custom_rules: Dict[str, Any] = Field(default_factory=dict)


class PreprocessingResult(BaseModel):
    """预处理结果模型"""
    original_record_count: int = Field(default=0)
    processed_record_count: int = Field(default=0)
    removed_duplicates: int = Field(default=0)
    handled_missing: int = Field(default=0)
    normalized_fields: List[str] = Field(default_factory=list)
    removed_outliers: int = Field(default=0)
    processing_time_ms: float = Field(default=0.0)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    output_data: Optional[Any] = None


class DimensionSpaceConfig(BaseModel):
    """维度空间配置模型"""
    enabled_dimensions: List[DimensionType] = Field(default_factory=lambda: list(DimensionType))
    quality_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "completeness": 0.8,
            "accuracy": 0.9,
            "consistency": 0.85,
            "timeliness": 0.7,
            "validity": 0.95,
            "uniqueness": 0.9,
            "relevance": 0.75,
        }
    )
    singularity_detection_enabled: bool = Field(default=True)
    auto_preprocessing: bool = Field(default=True)
    preprocessing_config: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    batch_size: int = Field(default=10000, ge=1)
    parallel_workers: int = Field(default=4, ge=1)

    class Config:
        use_enum_values = True