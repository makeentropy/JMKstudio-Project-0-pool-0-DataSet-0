"""
维度量化函数模块

提供单一维度的直观量化功能，将复杂的多维数据空间抽象为可理解的量化指标。
核心功能：
- 单一维度量化：将维度数据转换为直观的数值指标
- 维度空间映射：将多维数据映射到单一量化空间
- 质能量化：基于数据质能模型的维度量化
- 熵量化：基于信息熵的维度复杂度量化
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ai_llm_agent_crawler.dimension.models import (
    DataMassEnergy,
    DimensionType,
    DimensionVector,
    QualityAssessment,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DimensionQuantizationResult:
    """维度量化结果"""
    dimension_type: DimensionType
    raw_score: float = 0.0
    normalized_score: float = 0.0
    entropy: float = 0.0
    density: float = 0.0
    variance: float = 0.0
    coverage: float = 0.0
    quality_factor: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    quantized_at: datetime = field(default_factory=datetime.now)

    @property
    def effective_score(self) -> float:
        """有效量化分数 = 归一化分数 * 质量因子"""
        return self.normalized_score * self.quality_factor

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dimension_type": self.dimension_type.value,
            "raw_score": self.raw_score,
            "normalized_score": self.normalized_score,
            "effective_score": self.effective_score,
            "entropy": self.entropy,
            "density": self.density,
            "variance": self.variance,
            "coverage": self.coverage,
            "quality_factor": self.quality_factor,
            "metadata": self.metadata,
            "quantized_at": self.quantized_at.isoformat(),
        }


@dataclass
class QuantizationConfig:
    """量化配置"""
    score_range: Tuple[float, float] = (0.0, 1.0)
    entropy_weight: float = 0.3
    density_weight: float = 0.2
    variance_weight: float = 0.2
    coverage_weight: float = 0.3
    quality_threshold: float = 0.7
    enable_smoothing: bool = True
    smoothing_factor: float = 0.1
    max_entropy: float = 10.0
    min_entropy: float = 0.01


class DimensionQuantizer:
    """
    维度量化器

    将单一维度的数据转换为直观的量化指标，支持多种量化策略：
    - 统计量化：基于均值、方差等统计特征
    - 熵量化：基于信息熵的复杂度度量
    - 密度量化：基于数据密度的量化
    - 覆盖率量化：基于值空间覆盖率的量化
    """

    def __init__(
        self,
        config: Optional[QuantizationConfig] = None,
        custom_metrics: Optional[Dict[str, Callable]] = None,
    ):
        """
        初始化维度量化器

        Args:
            config: 量化配置
            custom_metrics: 自定义量化指标函数
        """
        self.config = config or QuantizationConfig()
        self.custom_metrics = custom_metrics or {}

        logger.info(f"维度量化器初始化完成")

    def quantize(
        self,
        dimension_type: DimensionType,
        values: pd.Series,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DimensionQuantizationResult:
        """
        量化单一维度

        Args:
            dimension_type: 维度类型
            values: 维度值序列
            metadata: 额外元数据

        Returns:
            量化结果
        """
        if len(values) == 0:
            return DimensionQuantizationResult(
                dimension_type=dimension_type,
                metadata=metadata or {},
            )

        non_null_values = values.dropna()
        if len(non_null_values) == 0:
            return DimensionQuantizationResult(
                dimension_type=dimension_type,
                coverage=0.0,
                metadata=metadata or {},
            )

        raw_score = self._calculate_raw_score(non_null_values, dimension_type)
        entropy = self._calculate_entropy(non_null_values)
        density = self._calculate_density(non_null_values)
        variance = self._calculate_variance(non_null_values)
        coverage = self._calculate_coverage(values)

        normalized_score = self._normalize_score(
            raw_score, entropy, density, variance, coverage
        )

        result = DimensionQuantizationResult(
            dimension_type=dimension_type,
            raw_score=raw_score,
            normalized_score=normalized_score,
            entropy=entropy,
            density=density,
            variance=variance,
            coverage=coverage,
            metadata=metadata or {},
        )

        logger.debug(
            f"维度量化完成: {dimension_type.value}, "
            f"raw={raw_score:.4f}, normalized={normalized_score:.4f}, "
            f"entropy={entropy:.4f}, density={density:.4f}"
        )

        return result

    def quantize_field(
        self,
        field_name: str,
        values: pd.Series,
        field_type: Optional[str] = None,
        dimension_type: Optional[DimensionType] = None,
    ) -> DimensionQuantizationResult:
        """
        量化数据字段

        Args:
            field_name: 字段名称
            values: 字段值序列
            field_type: 字段类型
            dimension_type: 维度类型（可选，自动推断）

        Returns:
            量化结果
        """
        if dimension_type is None:
            dimension_type = self._infer_dimension_type(field_name, values, field_type)

        metadata = {
            "field_name": field_name,
            "field_type": field_type or str(values.dtype),
            "sample_size": len(values),
            "non_null_count": values.notna().sum(),
        }

        return self.quantize(dimension_type, values, metadata)

    def quantize_dimension_vector(
        self,
        vector: DimensionVector,
    ) -> Dict[DimensionType, DimensionQuantizationResult]:
        """
        量化维度向量

        Args:
            vector: 维度向量

        Returns:
            各维度的量化结果字典
        """
        results = {}
        for feature in vector.features:
            values = pd.Series([feature.feature_value])
            result = self.quantize(
                feature.dimension_type,
                values,
                {
                    "feature_name": feature.feature_name,
                    "weight": feature.weight,
                    "confidence": feature.confidence,
                },
            )
            results[feature.dimension_type] = result

        return results

    def quantize_dataframe(
        self,
        df: pd.DataFrame,
        dimension_mapping: Optional[Dict[str, DimensionType]] = None,
    ) -> Dict[str, DimensionQuantizationResult]:
        """
        量化DataFrame的所有字段

        Args:
            df: 数据DataFrame
            dimension_mapping: 字段到维度类型的映射

        Returns:
            各字段的量化结果字典
        """
        results = {}
        for col in df.columns:
            dim_type = dimension_mapping.get(col) if dimension_mapping else None
            result = self.quantize_field(col, df[col], dimension_type=dim_type)
            results[col] = result

        return results

    def quantize_with_mass_energy(
        self,
        dimension_type: DimensionType,
        values: pd.Series,
        mass_energy: DataMassEnergy,
    ) -> DimensionQuantizationResult:
        """
        结合质能模型进行维度量化

        Args:
            dimension_type: 维度类型
            values: 维度值序列
            mass_energy: 数据质能模型

        Returns:
            量化结果（包含质能校正）
        """
        result = self.quantize(dimension_type, values)

        result.quality_factor = mass_energy.quality_factor
        result.metadata.update({
            "data_mass": mass_energy.data_mass,
            "data_energy": mass_energy.data_energy,
            "mass_energy_ratio": mass_energy.mass_energy_ratio,
            "singularity_risk": mass_energy.calculate_singularity_risk(),
        })

        return result

    def _calculate_raw_score(
        self,
        values: pd.Series,
        dimension_type: DimensionType,
    ) -> float:
        """计算原始量化分数"""
        if dimension_type in (DimensionType.STATISTICAL, DimensionType.QUALITY):
            return self._quantize_numeric(values)
        elif dimension_type == DimensionType.CONTENT:
            return self._quantize_text(values)
        elif dimension_type == DimensionType.TEMPORAL:
            return self._quantize_temporal(values)
        elif dimension_type == DimensionType.SPATIAL:
            return self._quantize_spatial(values)
        elif dimension_type == DimensionType.SEMANTIC:
            return self._quantize_semantic(values)
        elif dimension_type == DimensionType.STRUCTURAL:
            return self._quantize_structural(values)
        elif dimension_type == DimensionType.RELATIONAL:
            return self._quantize_relational(values)
        else:
            return self._quantize_generic(values)

    def _quantize_numeric(self, values: pd.Series) -> float:
        """量化数值维度"""
        try:
            numeric_values = pd.to_numeric(values, errors='coerce').dropna()
            if len(numeric_values) == 0:
                return 0.0

            mean_val = numeric_values.mean()
            std_val = numeric_values.std()

            if std_val == 0:
                return 0.5

            cv = std_val / abs(mean_val) if mean_val != 0 else 1.0
            normalized_cv = min(cv, 10.0) / 10.0

            return 0.5 + normalized_cv * 0.5
        except Exception:
            return 0.5

    def _quantize_text(self, values: pd.Series) -> float:
        """量化文本维度"""
        try:
            text_values = values.astype(str)
            lengths = text_values.str.len()
            avg_length = lengths.mean()
            std_length = lengths.std()

            if avg_length == 0:
                return 0.0

            length_score = min(avg_length / 1000.0, 1.0)
            diversity_score = text_values.nunique() / len(text_values)

            return (length_score + diversity_score) / 2.0
        except Exception:
            return 0.5

    def _quantize_temporal(self, values: pd.Series) -> float:
        """量化时间维度"""
        try:
            time_values = pd.to_datetime(values, errors='coerce').dropna()
            if len(time_values) == 0:
                return 0.0

            now = datetime.now()
            ages = (now - time_values).dt.days
            avg_age = ages.mean()

            if avg_age <= 7:
                return 1.0
            elif avg_age <= 30:
                return 0.85
            elif avg_age <= 90:
                return 0.7
            elif avg_age <= 365:
                return 0.5
            else:
                return 0.3
        except Exception:
            return 0.5

    def _quantize_spatial(self, values: pd.Series) -> float:
        """量化空间维度"""
        try:
            valid_count = 0
            for val in values:
                if pd.isna(val):
                    continue
                val_str = str(val)
                if (
                    (',' in val_str and len(val_str.split(',')) == 2)
                    or ('lat' in val_str.lower() and 'lng' in val_str.lower())
                ):
                    valid_count += 1

            return valid_count / len(values)
        except Exception:
            return 0.5

    def _quantize_semantic(self, values: pd.Series) -> float:
        """量化语义维度"""
        try:
            text_values = values.astype(str)
            unique_ratio = text_values.nunique() / len(text_values)
            avg_length = text_values.str.len().mean()

            semantic_density = min(avg_length / 50.0, 1.0)
            information_content = unique_ratio * semantic_density

            return information_content
        except Exception:
            return 0.5

    def _quantize_structural(self, values: pd.Series) -> float:
        """量化结构维度"""
        try:
            type_consistency = len(set(type(v).__name__ for v in values.dropna()))
            if type_consistency <= 1:
                type_score = 1.0
            elif type_consistency == 2:
                type_score = 0.8
            else:
                type_score = 0.5

            format_consistency = 1.0
            if values.dtype == 'object':
                lengths = values.astype(str).str.len()
                if lengths.std() > 0:
                    format_consistency = 1 - min(lengths.std() / lengths.mean(), 1.0)

            return (type_score + format_consistency) / 2.0
        except Exception:
            return 0.5

    def _quantize_relational(self, values: pd.Series) -> float:
        """量化关系维度"""
        try:
            unique_ratio = values.nunique() / len(values)
            non_null_ratio = values.notna().sum() / len(values)

            return (unique_ratio + non_null_ratio) / 2.0
        except Exception:
            return 0.5

    def _quantize_generic(self, values: pd.Series) -> float:
        """通用量化方法"""
        try:
            non_null_ratio = values.notna().sum() / len(values)
            unique_ratio = values.nunique() / len(values)

            return (non_null_ratio + unique_ratio) / 2.0
        except Exception:
            return 0.5

    def _calculate_entropy(self, values: pd.Series) -> float:
        """计算信息熵"""
        if len(values) == 0:
            return 0.0

        try:
            if values.dtype == 'object':
                value_counts = values.value_counts(normalize=True)
                entropy = -sum(p * np.log2(p + 1e-10) for p in value_counts)
            else:
                bins = min(20, len(values.unique()))
                hist, _ = np.histogram(values, bins=bins)
                hist_norm = hist / hist.sum()
                entropy = -sum(p * np.log2(p + 1e-10) for p in hist_norm if p > 0)

            return entropy
        except Exception:
            return 0.0

    def _calculate_density(self, values: pd.Series) -> float:
        """计算数据密度"""
        if len(values) == 0:
            return 0.0

        try:
            if values.dtype == 'object':
                unique_ratio = values.nunique() / len(values)
                return unique_ratio * 100
            else:
                numeric_values = pd.to_numeric(values, errors='coerce').dropna()
                if len(numeric_values) == 0:
                    return 0.0

                range_val = numeric_values.max() - numeric_values.min()
                if range_val == 0:
                    return 100.0

                density = len(numeric_values) / range_val if range_val > 0 else 0
                return min(density * 10, 100.0)
        except Exception:
            return 50.0

    def _calculate_variance(self, values: pd.Series) -> float:
        """计算方差"""
        if len(values) == 0:
            return 0.0

        try:
            numeric_values = pd.to_numeric(values, errors='coerce').dropna()
            if len(numeric_values) == 0:
                return 0.0

            return numeric_values.var()
        except Exception:
            return 0.0

    def _calculate_coverage(self, values: pd.Series) -> float:
        """计算值空间覆盖率"""
        if len(values) == 0:
            return 0.0

        non_null_count = values.notna().sum()
        return non_null_count / len(values)

    def _normalize_score(
        self,
        raw_score: float,
        entropy: float,
        density: float,
        variance: float,
        coverage: float,
    ) -> float:
        """归一化量化分数"""
        config = self.config

        entropy_norm = (entropy - config.min_entropy) / (config.max_entropy - config.min_entropy)
        entropy_norm = max(0.0, min(1.0, entropy_norm))

        density_norm = density / 100.0

        variance_norm = min(variance / 100.0, 1.0) if variance > 0 else 0.5

        weighted_sum = (
            raw_score * 0.4
            + entropy_norm * config.entropy_weight
            + density_norm * config.density_weight
            + variance_norm * config.variance_weight
            + coverage * config.coverage_weight
        )

        normalized = (weighted_sum - config.score_range[0]) / (
            config.score_range[1] - config.score_range[0]
        )
        normalized = max(0.0, min(1.0, normalized))

        if config.enable_smoothing:
            normalized = normalized * (1 - config.smoothing_factor) + 0.5 * config.smoothing_factor

        return normalized

    def _infer_dimension_type(
        self,
        field_name: str,
        values: pd.Series,
        field_type: Optional[str] = None,
    ) -> DimensionType:
        """推断字段的维度类型"""
        name_lower = field_name.lower()

        if any(keyword in name_lower for keyword in ['time', 'date', 'timestamp', 'created', 'updated']):
            return DimensionType.TEMPORAL
        elif any(keyword in name_lower for keyword in ['lat', 'lng', 'location', 'geo', 'coord']):
            return DimensionType.SPATIAL
        elif any(keyword in name_lower for keyword in ['text', 'content', 'desc', 'title', 'body']):
            return DimensionType.CONTENT
        elif any(keyword in name_lower for keyword in ['category', 'tag', 'label', 'topic']):
            return DimensionType.SEMANTIC
        elif any(keyword in name_lower for keyword in ['id', 'key', 'index', 'ref', 'link']):
            return DimensionType.RELATIONAL
        elif values.dtype in ['int64', 'float64', 'int32', 'float32']:
            return DimensionType.STATISTICAL
        elif field_type and field_type.lower() in ['datetime', 'date']:
            return DimensionType.TEMPORAL
        elif field_type and field_type.lower() in ['string', 'text']:
            return DimensionType.CONTENT
        else:
            return DimensionType.STRUCTURAL

    def generate_quantization_report(
        self,
        results: Dict[str, DimensionQuantizationResult],
    ) -> Dict[str, Any]:
        """
        生成量化报告

        Args:
            results: 量化结果字典

        Returns:
            详细的量化报告
        """
        if not results:
            return {"error": "No quantization results"}

        report = {
            "summary": {
                "field_count": len(results),
                "avg_score": sum(r.normalized_score for r in results.values()) / len(results),
                "avg_effective_score": sum(r.effective_score for r in results.values()) / len(results),
                "avg_entropy": sum(r.entropy for r in results.values()) / len(results),
                "avg_density": sum(r.density for r in results.values()) / len(results),
            },
            "dimension_distribution": {},
            "fields": {},
            "recommendations": [],
        }

        for field_name, result in results.items():
            dim_type = result.dimension_type.value
            report["dimension_distribution"][dim_type] = (
                report["dimension_distribution"].get(dim_type, 0) + 1
            )

            report["fields"][field_name] = result.to_dict()

        report["recommendations"] = self._generate_recommendations(results)

        return report

    def _generate_recommendations(
        self,
        results: Dict[str, DimensionQuantizationResult],
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        low_score_fields = [
            name for name, result in results.items()
            if result.normalized_score < 0.5
        ]
        if low_score_fields:
            recommendations.append(
                f"发现 {len(low_score_fields)} 个低量化分数字段: {', '.join(low_score_fields)}"
            )

        high_entropy_fields = [
            name for name, result in results.items()
            if result.entropy > 8.0
        ]
        if high_entropy_fields:
            recommendations.append(
                f"发现 {len(high_entropy_fields)} 个高熵字段，信息复杂度较高"
            )

        low_coverage_fields = [
            name for name, result in results.items()
            if result.coverage < 0.7
        ]
        if low_coverage_fields:
            recommendations.append(
                f"发现 {len(low_coverage_fields)} 个低覆盖率字段，建议补充数据"
            )

        return recommendations


class MultiDimensionQuantizer:
    """
    多维量化器

    同时量化多个维度，并提供跨维度的综合分析。
    """

    def __init__(self, quantizer: Optional[DimensionQuantizer] = None):
        """
        初始化多维量化器

        Args:
            quantizer: 维度量化器实例
        """
        self.quantizer = quantizer or DimensionQuantizer()

    def quantize_all_dimensions(
        self,
        df: pd.DataFrame,
        dimension_mapping: Optional[Dict[str, DimensionType]] = None,
    ) -> Dict[DimensionType, List[DimensionQuantizationResult]]:
        """
        量化所有维度

        Args:
            df: 数据DataFrame
            dimension_mapping: 字段到维度类型的映射

        Returns:
            按维度类型分组的量化结果
        """
        field_results = self.quantizer.quantize_dataframe(df, dimension_mapping)

        dimension_results: Dict[DimensionType, List[DimensionQuantizationResult]] = {}
        for field_name, result in field_results.items():
            dim_type = result.dimension_type
            if dim_type not in dimension_results:
                dimension_results[dim_type] = []
            dimension_results[dim_type].append(result)

        return dimension_results

    def calculate_dimension_importance(
        self,
        df: pd.DataFrame,
        dimension_mapping: Optional[Dict[str, DimensionType]] = None,
    ) -> Dict[DimensionType, float]:
        """
        计算各维度的重要性权重

        Args:
            df: 数据DataFrame
            dimension_mapping: 字段到维度类型的映射

        Returns:
            各维度的重要性权重
        """
        dimension_results = self.quantize_all_dimensions(df, dimension_mapping)

        importance: Dict[DimensionType, float] = {}
        total_score = 0.0

        for dim_type, results in dimension_results.items():
            avg_score = sum(r.effective_score for r in results) / len(results)
            field_count = len(results)
            importance[dim_type] = avg_score * field_count
            total_score += importance[dim_type]

        if total_score > 0:
            for dim_type in importance:
                importance[dim_type] /= total_score

        return importance

    def create_quantization_vector(
        self,
        df: pd.DataFrame,
        dimension_mapping: Optional[Dict[str, DimensionType]] = None,
    ) -> np.ndarray:
        """
        创建量化向量

        Args:
            df: 数据DataFrame
            dimension_mapping: 字段到维度类型的映射

        Returns:
            量化向量（各维度有效分数的归一化表示）
        """
        importance = self.calculate_dimension_importance(df, dimension_mapping)

        vector = np.zeros(len(DimensionType))
        for i, dim_type in enumerate(DimensionType):
            vector[i] = importance.get(dim_type, 0.0)

        return vector

    def compare_dimensions(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        dimension_mapping: Optional[Dict[str, DimensionType]] = None,
    ) -> Dict[DimensionType, float]:
        """
        比较两个数据集的维度量化差异

        Args:
            df1: 第一个数据集
            df2: 第二个数据集
            dimension_mapping: 字段到维度类型的映射

        Returns:
            各维度的差异分数（正值表示df1更好，负值表示df2更好）
        """
        importance1 = self.calculate_dimension_importance(df1, dimension_mapping)
        importance2 = self.calculate_dimension_importance(df2, dimension_mapping)

        diff: Dict[DimensionType, float] = {}
        for dim_type in DimensionType:
            diff[dim_type] = importance1.get(dim_type, 0.0) - importance2.get(dim_type, 0.0)

        return diff