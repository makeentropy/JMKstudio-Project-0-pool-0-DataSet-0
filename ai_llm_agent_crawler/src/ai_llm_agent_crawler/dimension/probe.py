"""
维度空间探针模块

提供统一的多维数据探测入口，整合质量、结构、统计、内容和关系五大维度的探测分析，
生成完整的探测报告和优化建议。
"""

import hashlib
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dimension.models import QualityMetricType
from ai_llm_agent_crawler.dimension.quality import QualityAssessor
from ai_llm_agent_crawler.dimension.singularity import SingularityDetector
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ProbeDimension(str, Enum):
    """探针探测维度枚举"""
    QUALITY = "quality"
    STRUCTURAL = "structural"
    STATISTICAL = "statistical"
    CONTENT = "content"
    RELATIONAL = "relational"


class DimensionProbeResult(BaseModel):
    """单维度探测结果模型"""
    dimension: ProbeDimension
    quantitative_metrics: Dict[str, float] = Field(default_factory=dict)
    qualitative_description: str = ""
    anomalies_found: int = 0
    singularities: List[Dict[str, Any]] = Field(default_factory=list)
    health_score: float = Field(default=0.0, ge=0.0, le=1.0)
    probe_depth: int = 1
    execution_time_ms: float = 0.0

    class Config:
        use_enum_values = True


class ProbeReport(BaseModel):
    """完整探测报告模型"""
    report_id: str
    dataset_name: str
    record_count: int = Field(default=0, ge=0)
    field_count: int = Field(default=0, ge=0)
    overall_health_score: float = Field(default=0.0, ge=0.0, le=1.0)
    dimension_results: Dict[str, DimensionProbeResult] = Field(default_factory=dict)
    critical_issues: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    probe_time: datetime = Field(default_factory=datetime.now)
    total_duration_ms: float = 0.0

    class Config:
        use_enum_values = True


class PathProbePoint(BaseModel):
    """路径探测点模型"""
    position: float = Field(default=0.0, ge=0.0, le=1.0)
    density: float = Field(default=0.0, ge=0.0)
    value: float = 0.0
    is_critical: bool = False
    anomaly_score: float = 0.0
    description: str = ""


class PathProbeResult(BaseModel):
    """路径探测结果模型"""
    dimension: str = ""
    path_points: List[PathProbePoint] = Field(default_factory=list)
    distribution: Dict[str, float] = Field(default_factory=dict)
    critical_points: List[PathProbePoint] = Field(default_factory=list)
    anomaly_regions: List[Dict[str, Any]] = Field(default_factory=list)
    step_size: float = 0.05
    total_depth: int = 1
    execution_time_ms: float = 0.0


class DimensionTopology(BaseModel):
    """维度空间拓扑模型"""
    num_dimensions: int = Field(default=0, ge=0)
    distance_matrix: Optional[List[List[float]]] = None
    density_distribution: Dict[str, float] = Field(default_factory=dict)
    centroid: Dict[str, float] = Field(default_factory=dict)
    boundary_points: List[Dict[str, Any]] = Field(default_factory=list)
    cluster_count: int = Field(default=0, ge=0)
    cluster_info: List[Dict[str, Any]] = Field(default_factory=list)


class DimensionSpaceProbe:
    """
    维度空间探针类

    提供统一的多维数据探测入口，整合质量、结构、统计、内容和关系五大维度的探测分析，
    生成完整的探测报告和优化建议。
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化维度空间探针

        Args:
            config: 配置字典，可选
        """
        self.config = config or {}
        self.quality_assessor = QualityAssessor(
            custom_thresholds=self.config.get("quality_thresholds")
        )
        self.singularity_detector = SingularityDetector(
            sensitivity=self.config.get("sensitivity", 0.8)
        )
        self.probe_depth = self.config.get("probe_depth", 2)
        logger.info(f"维度空间探针初始化完成，探测深度: {self.probe_depth}")

    def probe(self, df: pd.DataFrame, dataset_name: str = "dataset") -> ProbeReport:
        """
        对数据集进行全维度探测

        Args:
            df: 要探测的DataFrame
            dataset_name: 数据集名称

        Returns:
            完整探测报告
        """
        start_time = time.time()
        logger.info(f"开始对数据集 '{dataset_name}' 进行全维度探测，记录数: {len(df)}, 字段数: {len(df.columns)}")

        dimension_results: Dict[str, DimensionProbeResult] = {}

        dimension_results[ProbeDimension.QUALITY.value] = self.probe_quality(df)
        dimension_results[ProbeDimension.STRUCTURAL.value] = self.probe_structural(df)
        dimension_results[ProbeDimension.STATISTICAL.value] = self.probe_statistical(df)
        dimension_results[ProbeDimension.CONTENT.value] = self.probe_content(df)
        dimension_results[ProbeDimension.RELATIONAL.value] = self.probe_relational(df)

        singularities = self.detect_singularities(df)

        overall_health = self._calculate_overall_health(dimension_results)

        critical_issues, warnings = self._collect_issues(dimension_results, singularities)

        recommendations = self._generate_recommendations(dimension_results)

        report_id = self._generate_report_id()

        total_duration = (time.time() - start_time) * 1000

        report = ProbeReport(
            report_id=report_id,
            dataset_name=dataset_name,
            record_count=len(df),
            field_count=len(df.columns),
            overall_health_score=overall_health,
            dimension_results=dimension_results,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations,
            probe_time=datetime.now(),
            total_duration_ms=total_duration,
        )

        logger.info(
            f"数据集 '{dataset_name}' 探测完成，整体健康度: {overall_health:.2f}, "
            f"严重问题: {len(critical_issues)}, 警告: {len(warnings)}, "
            f"耗时: {total_duration:.2f}ms"
        )

        return report

    def probe_quality(self, df: pd.DataFrame) -> DimensionProbeResult:
        """
        质量维度探测

        Args:
            df: 要探测的DataFrame

        Returns:
            质量维度探测结果
        """
        start_time = time.time()
        logger.debug("开始质量维度探测")

        assessment = self.quality_assessor.assess_dataframe(df)

        quantitative_metrics: Dict[str, float] = {}
        for metric in assessment.metrics:
            metric_name = metric.metric_type.value if hasattr(metric.metric_type, 'value') else str(metric.metric_type)
            quantitative_metrics[metric_name] = metric.score

        low_metrics = [m for m in assessment.metrics if not m.is_acceptable]
        anomalies_found = len(low_metrics)

        qualitative_parts = []
        if assessment.overall_score >= 0.8:
            qualitative_parts.append("数据质量整体良好")
        elif assessment.overall_score >= 0.6:
            qualitative_parts.append("数据质量中等，存在一定改进空间")
        else:
            qualitative_parts.append("数据质量较低，需要重点关注")

        if low_metrics:
            metric_names = [m.metric_type.value if hasattr(m.metric_type, 'value') else str(m.metric_type) for m in low_metrics]
            qualitative_parts.append(f"以下指标低于阈值: {', '.join(metric_names)}")

        qualitative_description = "。".join(qualitative_parts) + "。"

        singularities = []
        for metric in low_metrics:
            metric_name = metric.metric_type.value if hasattr(metric.metric_type, 'value') else str(metric.metric_type)
            singularities.append({
                "type": "quality_threshold",
                "metric": metric_name,
                "score": metric.score,
                "threshold": metric.threshold,
                "severity": "high" if metric.score < metric.threshold * 0.7 else "medium",
            })

        result = DimensionProbeResult(
            dimension=ProbeDimension.QUALITY,
            quantitative_metrics=quantitative_metrics,
            qualitative_description=qualitative_description,
            anomalies_found=anomalies_found,
            singularities=singularities,
            health_score=assessment.overall_score,
            probe_depth=self.probe_depth,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

        logger.debug(f"质量维度探测完成，健康度: {result.health_score:.2f}, 异常数: {anomalies_found}")
        return result

    def probe_structural(self, df: pd.DataFrame) -> DimensionProbeResult:
        """
        结构维度探测

        Args:
            df: 要探测的DataFrame

        Returns:
            结构维度探测结果
        """
        start_time = time.time()
        logger.debug("开始结构维度探测")

        field_count = len(df.columns)
        record_count = len(df)

        type_distribution: Dict[str, int] = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            type_distribution[dtype] = type_distribution.get(dtype, 0) + 1

        type_count = len(type_distribution)

        nested_level = 1
        for col in df.columns:
            if df[col].dtype == 'object':
                sample_values = df[col].dropna().head(10)
                for val in sample_values:
                    if isinstance(val, (dict, list)):
                        nested_level = max(nested_level, 2)
                        break

        sparsity = 0.0
        if record_count > 0 and field_count > 0:
            total_cells = record_count * field_count
            null_cells = df.isna().sum().sum()
            sparsity = null_cells / total_cells

        quantitative_metrics = {
            "field_count": float(field_count),
            "record_count": float(record_count),
            "type_count": float(type_count),
            "nested_level": float(nested_level),
            "sparsity": sparsity,
        }

        anomalies_found = 0
        singularities = []

        if field_count < 3:
            anomalies_found += 1
            singularities.append({
                "type": "structural_anomaly",
                "issue": "too_few_fields",
                "field_count": field_count,
                "severity": "high" if field_count < 2 else "medium",
            })

        if type_count == 1 and field_count > 3:
            anomalies_found += 1
            singularities.append({
                "type": "structural_anomaly",
                "issue": "single_type_dominance",
                "type_count": type_count,
                "severity": "medium",
            })

        if sparsity > 0.5:
            anomalies_found += 1
            singularities.append({
                "type": "structural_anomaly",
                "issue": "high_sparsity",
                "sparsity": sparsity,
                "severity": "high" if sparsity > 0.7 else "medium",
            })

        qualitative_parts = []
        qualitative_parts.append(f"数据集包含 {field_count} 个字段，{record_count} 条记录")
        qualitative_parts.append(f"字段类型共 {type_count} 种")
        qualitative_parts.append(f"数据稀疏度为 {sparsity:.1%}")

        if nested_level > 1:
            qualitative_parts.append("存在嵌套结构")

        qualitative_description = "，".join(qualitative_parts) + "。"

        health_score = 1.0
        if field_count < 3:
            health_score *= 0.7
        if sparsity > 0.3:
            health_score *= (1 - sparsity * 0.5)
        if type_count == 1 and field_count > 3:
            health_score *= 0.8

        health_score = max(0.0, min(1.0, health_score))

        result = DimensionProbeResult(
            dimension=ProbeDimension.STRUCTURAL,
            quantitative_metrics=quantitative_metrics,
            qualitative_description=qualitative_description,
            anomalies_found=anomalies_found,
            singularities=singularities,
            health_score=health_score,
            probe_depth=self.probe_depth,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

        logger.debug(f"结构维度探测完成，健康度: {result.health_score:.2f}, 异常数: {anomalies_found}")
        return result

    def probe_statistical(self, df: pd.DataFrame) -> DimensionProbeResult:
        """
        统计维度探测

        Args:
            df: 要探测的DataFrame

        Returns:
            统计维度探测结果
        """
        start_time = time.time()
        logger.debug("开始统计维度探测")

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        quantitative_metrics: Dict[str, float] = {}
        anomalies_found = 0
        singularities = []

        if len(numeric_cols) > 0:
            overall_mean_list = []
            overall_std_list = []
            overall_skew_list = []
            overall_kurt_list = []
            total_outlier_ratio = 0.0

            for col in numeric_cols:
                values = df[col].dropna()
                if len(values) < 2:
                    continue

                col_mean = values.mean()
                col_std = values.std()

                overall_mean_list.append(col_mean)
                overall_std_list.append(col_std)

                if col_std > 0:
                    col_skew = values.skew()
                    col_kurt = values.kurtosis()
                    overall_skew_list.append(col_skew)
                    overall_kurt_list.append(col_kurt)

                    z_scores = np.abs((values - col_mean) / col_std)
                    outlier_ratio = (z_scores > 3).sum() / len(values)
                    total_outlier_ratio += outlier_ratio

                    if outlier_ratio > 0.1:
                        anomalies_found += 1
                        singularities.append({
                            "type": "statistical_anomaly",
                            "field": col,
                            "outlier_ratio": float(outlier_ratio),
                            "severity": "high" if outlier_ratio > 0.2 else "medium",
                        })

                    if abs(col_skew) > 2:
                        anomalies_found += 1
                        singularities.append({
                            "type": "statistical_anomaly",
                            "field": col,
                            "skewness": float(col_skew),
                            "issue": "high_skewness",
                            "severity": "medium",
                        })

            quantitative_metrics = {
                "numeric_field_count": float(len(numeric_cols)),
                "avg_mean": float(np.mean(overall_mean_list)) if overall_mean_list else 0.0,
                "avg_std": float(np.mean(overall_std_list)) if overall_std_list else 0.0,
                "avg_skewness": float(np.mean(np.abs(overall_skew_list))) if overall_skew_list else 0.0,
                "avg_kurtosis": float(np.mean(overall_kurt_list)) if overall_kurt_list else 0.0,
                "avg_outlier_ratio": float(total_outlier_ratio / len(numeric_cols)) if len(numeric_cols) > 0 else 0.0,
            }
        else:
            quantitative_metrics = {
                "numeric_field_count": 0.0,
                "avg_mean": 0.0,
                "avg_std": 0.0,
                "avg_skewness": 0.0,
                "avg_kurtosis": 0.0,
                "avg_outlier_ratio": 0.0,
            }

        qualitative_parts = []
        if len(numeric_cols) > 0:
            qualitative_parts.append(f"包含 {len(numeric_cols)} 个数值字段")
            avg_skew = quantitative_metrics.get("avg_skewness", 0)
            if avg_skew > 1.5:
                qualitative_parts.append("数据分布呈现较高偏度")
            elif avg_skew > 0.5:
                qualitative_parts.append("数据分布存在一定偏度")
            else:
                qualitative_parts.append("数据分布相对对称")

            avg_outlier = quantitative_metrics.get("avg_outlier_ratio", 0)
            if avg_outlier > 0.1:
                qualitative_parts.append(f"平均离群点比例较高 ({avg_outlier:.1%})")
            elif avg_outlier > 0.05:
                qualitative_parts.append(f"存在一定比例的离群点 ({avg_outlier:.1%})")
            else:
                qualitative_parts.append("离群点较少")
        else:
            qualitative_parts.append("无数值字段")

        qualitative_description = "，".join(qualitative_parts) + "。"

        health_score = 1.0
        if len(numeric_cols) == 0:
            health_score = 0.5
        else:
            avg_outlier = quantitative_metrics.get("avg_outlier_ratio", 0)
            avg_skew = quantitative_metrics.get("avg_skewness", 0)
            health_score = max(0.0, 1.0 - avg_outlier * 2 - abs(avg_skew) * 0.1)

        health_score = max(0.0, min(1.0, health_score))

        result = DimensionProbeResult(
            dimension=ProbeDimension.STATISTICAL,
            quantitative_metrics=quantitative_metrics,
            qualitative_description=qualitative_description,
            anomalies_found=anomalies_found,
            singularities=singularities,
            health_score=health_score,
            probe_depth=self.probe_depth,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

        logger.debug(f"统计维度探测完成，健康度: {result.health_score:.2f}, 异常数: {anomalies_found}")
        return result

    def probe_content(self, df: pd.DataFrame) -> DimensionProbeResult:
        """
        内容维度探测

        Args:
            df: 要探测的DataFrame

        Returns:
            内容维度探测结果
        """
        start_time = time.time()
        logger.debug("开始内容维度探测")

        text_cols = df.select_dtypes(include=['object']).columns
        quantitative_metrics: Dict[str, float] = {}
        anomalies_found = 0
        singularities = []

        total_avg_length = 0.0
        total_null_ratio = 0.0
        total_duplicate_ratio = 0.0
        total_unique_ratio = 0.0
        text_field_count = 0

        for col in df.columns:
            values = df[col]
            total_count = len(values)

            if total_count == 0:
                continue

            null_ratio = values.isna().sum() / total_count
            total_null_ratio += null_ratio

            if values.dtype == 'object':
                text_field_count += 1
                non_null_values = values.dropna().astype(str)
                if len(non_null_values) > 0:
                    avg_length = non_null_values.str.len().mean()
                    total_avg_length += avg_length

                unique_ratio = values.nunique() / total_count
                total_unique_ratio += unique_ratio

                duplicate_ratio = 1.0 - unique_ratio
                total_duplicate_ratio += duplicate_ratio

                if null_ratio > 0.3:
                    anomalies_found += 1
                    singularities.append({
                        "type": "content_anomaly",
                        "field": col,
                        "null_ratio": float(null_ratio),
                        "issue": "high_null_ratio",
                        "severity": "high" if null_ratio > 0.5 else "medium",
                    })

                if duplicate_ratio > 0.8:
                    anomalies_found += 1
                    singularities.append({
                        "type": "content_anomaly",
                        "field": col,
                        "duplicate_ratio": float(duplicate_ratio),
                        "issue": "high_duplicate_ratio",
                        "severity": "medium",
                    })

        field_count = len(df.columns)
        if field_count > 0:
            quantitative_metrics = {
                "text_field_count": float(text_field_count),
                "avg_text_length": float(total_avg_length / text_field_count) if text_field_count > 0 else 0.0,
                "avg_null_ratio": float(total_null_ratio / field_count),
                "avg_duplicate_ratio": float(total_duplicate_ratio / text_field_count) if text_field_count > 0 else 0.0,
                "avg_unique_ratio": float(total_unique_ratio / text_field_count) if text_field_count > 0 else 0.0,
            }
        else:
            quantitative_metrics = {
                "text_field_count": 0.0,
                "avg_text_length": 0.0,
                "avg_null_ratio": 0.0,
                "avg_duplicate_ratio": 0.0,
                "avg_unique_ratio": 0.0,
            }

        qualitative_parts = []
        qualitative_parts.append(f"包含 {text_field_count} 个文本字段")
        avg_null = quantitative_metrics.get("avg_null_ratio", 0)
        if avg_null > 0.3:
            qualitative_parts.append(f"平均空值率较高 ({avg_null:.1%})")
        elif avg_null > 0.1:
            qualitative_parts.append(f"存在一定空值 ({avg_null:.1%})")
        else:
            qualitative_parts.append("空值较少")

        avg_dup = quantitative_metrics.get("avg_duplicate_ratio", 0)
        if avg_dup > 0.7:
            qualitative_parts.append(f"重复值率较高 ({avg_dup:.1%})")
        elif avg_dup > 0.5:
            qualitative_parts.append(f"存在一定重复 ({avg_dup:.1%})")
        else:
            qualitative_parts.append("数据多样性较好")

        qualitative_description = "，".join(qualitative_parts) + "。"

        health_score = 1.0
        avg_null = quantitative_metrics.get("avg_null_ratio", 0)
        avg_dup = quantitative_metrics.get("avg_duplicate_ratio", 0)
        health_score = max(0.0, 1.0 - avg_null * 0.8 - avg_dup * 0.3)

        health_score = max(0.0, min(1.0, health_score))

        result = DimensionProbeResult(
            dimension=ProbeDimension.CONTENT,
            quantitative_metrics=quantitative_metrics,
            qualitative_description=qualitative_description,
            anomalies_found=anomalies_found,
            singularities=singularities,
            health_score=health_score,
            probe_depth=self.probe_depth,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

        logger.debug(f"内容维度探测完成，健康度: {result.health_score:.2f}, 异常数: {anomalies_found}")
        return result

    def probe_relational(self, df: pd.DataFrame) -> DimensionProbeResult:
        """
        关系维度探测

        Args:
            df: 要探测的DataFrame

        Returns:
            关系维度探测结果
        """
        start_time = time.time()
        logger.debug("开始关系维度探测")

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        quantitative_metrics: Dict[str, float] = {}
        anomalies_found = 0
        singularities = []

        high_correlation_pairs = 0
        total_pairs = 0
        independence_score = 1.0

        if len(numeric_cols) >= 2:
            try:
                corr_matrix = df[numeric_cols].corr()
                total_pairs = len(numeric_cols) * (len(numeric_cols) - 1) // 2

                corr_values = []
                for i, col1 in enumerate(numeric_cols):
                    for j, col2 in enumerate(numeric_cols):
                        if i < j:
                            corr_value = abs(corr_matrix.loc[col1, col2])
                            if pd.isna(corr_value):
                                continue
                            corr_values.append(corr_value)

                            if corr_value > 0.9:
                                high_correlation_pairs += 1
                                anomalies_found += 1
                                singularities.append({
                                    "type": "relational_anomaly",
                                    "fields": [col1, col2],
                                    "correlation": float(corr_value),
                                    "issue": "high_correlation",
                                    "severity": "high" if corr_value > 0.95 else "medium",
                                })

                if corr_values:
                    avg_corr = np.mean(corr_values)
                    independence_score = 1.0 - avg_corr
            except Exception as e:
                logger.warning(f"相关性计算失败: {e}")
                independence_score = 0.5

        quantitative_metrics = {
            "numeric_field_count": float(len(numeric_cols)),
            "total_field_pairs": float(total_pairs),
            "high_correlation_pairs": float(high_correlation_pairs),
            "independence_score": float(independence_score),
        }

        qualitative_parts = []
        if len(numeric_cols) >= 2:
            qualitative_parts.append(f"数值字段间共 {total_pairs} 对关系")
            if high_correlation_pairs > 0:
                qualitative_parts.append(f"发现 {high_correlation_pairs} 对高度相关字段")
            else:
                qualitative_parts.append("字段间独立性较好")
        else:
            qualitative_parts.append("数值字段不足，无法分析关系")

        qualitative_description = "，".join(qualitative_parts) + "。"

        health_score = max(0.0, min(1.0, independence_score))
        if len(numeric_cols) < 2:
            health_score = 0.5

        result = DimensionProbeResult(
            dimension=ProbeDimension.RELATIONAL,
            quantitative_metrics=quantitative_metrics,
            qualitative_description=qualitative_description,
            anomalies_found=anomalies_found,
            singularities=singularities,
            health_score=health_score,
            probe_depth=self.probe_depth,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

        logger.debug(f"关系维度探测完成，健康度: {result.health_score:.2f}, 异常数: {anomalies_found}")
        return result

    def detect_singularities(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        使用SingularityDetector进行奇点检测

        Args:
            df: 要探测的DataFrame

        Returns:
            奇点摘要列表
        """
        logger.debug("开始奇点检测")

        assessment = self.quality_assessor.assess_dataframe(df)
        result = self.singularity_detector.detect(df, assessment=assessment)

        singularities_summary = []
        for singularity in result.singularities:
            singularities_summary.append({
                "type": singularity.singularity_type.value if hasattr(singularity.singularity_type, 'value') else str(singularity.singularity_type),
                "severity": singularity.severity.value if hasattr(singularity.severity, 'value') else str(singularity.severity),
                "dimension": singularity.dimension.value if hasattr(singularity.dimension, 'value') else str(singularity.dimension),
                "description": singularity.description,
                "quality_score": singularity.quality_score,
                "affected_records": singularity.affected_records,
            })

        logger.debug(f"奇点检测完成，共 {len(singularities_summary)} 个奇点")
        return singularities_summary

    def _generate_recommendations(self, results: Dict[str, DimensionProbeResult]) -> List[str]:
        """
        基于各维度探测结果生成优化建议

        Args:
            results: 各维度探测结果字典

        Returns:
            优化建议列表
        """
        recommendations = []

        quality_result = results.get(ProbeDimension.QUALITY.value)
        if quality_result and quality_result.health_score < 0.7:
            recommendations.append("建议优先提升数据质量，重点关注完整性和有效性指标")
            if quality_result.anomalies_found > 0:
                for sing in quality_result.singularities:
                    metric = sing.get("metric", "")
                    if metric == QualityMetricType.COMPLETENESS.value:
                        recommendations.append("建议检查缺失值并采用填充或删除策略")
                    elif metric == QualityMetricType.ACCURACY.value:
                        recommendations.append("建议完善验证规则并修正不符合的数据")
                    elif metric == QualityMetricType.CONSISTENCY.value:
                        recommendations.append("建议标准化数据格式，确保一致性")
                    elif metric == QualityMetricType.VALIDITY.value:
                        recommendations.append("建议清洗无效数据，修正异常值")
                    elif metric == QualityMetricType.UNIQUENSS.value:
                        recommendations.append("建议去重处理，删除或标记重复数据")

        structural_result = results.get(ProbeDimension.STRUCTURAL.value)
        if structural_result and structural_result.health_score < 0.7:
            recommendations.append("建议优化数据结构，增加字段多样性")
            sparsity = structural_result.quantitative_metrics.get("sparsity", 0)
            if sparsity > 0.5:
                recommendations.append("建议处理高稀疏度问题，考虑合并或删除稀疏字段")

        statistical_result = results.get(ProbeDimension.STATISTICAL.value)
        if statistical_result and statistical_result.health_score < 0.7:
            recommendations.append("建议检查数据统计分布，处理异常值")
            outlier_ratio = statistical_result.quantitative_metrics.get("avg_outlier_ratio", 0)
            if outlier_ratio > 0.1:
                recommendations.append("建议对离群点进行分析和处理，可采用IQR或Z-score方法")

        content_result = results.get(ProbeDimension.CONTENT.value)
        if content_result and content_result.health_score < 0.7:
            recommendations.append("建议优化数据内容质量")
            null_ratio = content_result.quantitative_metrics.get("avg_null_ratio", 0)
            if null_ratio > 0.3:
                recommendations.append("建议补充缺失数据或采用填充策略")
            dup_ratio = content_result.quantitative_metrics.get("avg_duplicate_ratio", 0)
            if dup_ratio > 0.7:
                recommendations.append("建议增加数据多样性，避免重复内容")

        relational_result = results.get(ProbeDimension.RELATIONAL.value)
        if relational_result and relational_result.health_score < 0.7:
            recommendations.append("建议检查字段间关系，处理高度冗余字段")
            high_corr = relational_result.quantitative_metrics.get("high_correlation_pairs", 0)
            if high_corr > 0:
                recommendations.append("建议对高度相关字段进行特征选择或降维处理")

        if not recommendations:
            recommendations.append("数据质量整体良好，建议持续监控维护")

        return recommendations

    def _calculate_overall_health(self, results: Dict[str, DimensionProbeResult]) -> float:
        """
        计算整体健康度（各维度加权平均）

        质量权重 0.3，其他各 0.175

        Args:
            results: 各维度探测结果字典

        Returns:
            整体健康度评分
        """
        weights = {
            ProbeDimension.QUALITY.value: 0.3,
            ProbeDimension.STRUCTURAL.value: 0.175,
            ProbeDimension.STATISTICAL.value: 0.175,
            ProbeDimension.CONTENT.value: 0.175,
            ProbeDimension.RELATIONAL.value: 0.175,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for dim_key, weight in weights.items():
            result = results.get(dim_key)
            if result:
                weighted_sum += result.health_score * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0

        return min(1.0, max(0.0, weighted_sum / total_weight))

    def _collect_issues(
        self,
        results: Dict[str, DimensionProbeResult],
        singularities: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        收集严重问题和警告

        Args:
            results: 各维度探测结果
            singularities: 奇点列表

        Returns:
            (严重问题列表, 警告列表)
        """
        critical_issues = []
        warnings = []

        for dim_key, result in results.items():
            for sing in result.singularities:
                issue = {
                    "dimension": dim_key,
                    "type": sing.get("type", "unknown"),
                    "description": sing.get("issue", str(sing)),
                    "severity": sing.get("severity", "medium"),
                }
                if sing.get("severity") == "high":
                    critical_issues.append(issue)
                else:
                    warnings.append(issue)

        for sing in singularities:
            severity = sing.get("severity", "medium")
            if severity in ("high", "critical"):
                critical_issues.append({
                    "dimension": sing.get("dimension", "unknown"),
                    "type": sing.get("type", "singularity"),
                    "description": sing.get("description", ""),
                    "severity": severity,
                })
            else:
                warnings.append({
                    "dimension": sing.get("dimension", "unknown"),
                    "type": sing.get("type", "singularity"),
                    "description": sing.get("description", ""),
                    "severity": severity,
                })

        return critical_issues, warnings

    def get_probe_summary(self, report: ProbeReport) -> Dict[str, Any]:
        """
        生成探测报告的摘要信息

        Args:
            report: 探测报告

        Returns:
            摘要信息字典
        """
        all_issues = report.critical_issues + report.warnings
        top_issues = all_issues[:3]

        return {
            "report_id": report.report_id,
            "dataset_name": report.dataset_name,
            "overall_health_score": report.overall_health_score,
            "record_count": report.record_count,
            "field_count": report.field_count,
            "total_issues": len(report.critical_issues) + len(report.warnings),
            "critical_issue_count": len(report.critical_issues),
            "warning_count": len(report.warnings),
            "top_issues": top_issues,
            "key_recommendations": report.recommendations[:3],
            "probe_time": report.probe_time.isoformat(),
            "total_duration_ms": report.total_duration_ms,
        }

    def _generate_report_id(self) -> str:
        """
        生成报告ID

        Returns:
            报告ID字符串
        """
        timestamp = int(time.time() * 1000)
        random_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"probe_{timestamp}_{random_hash}"

    def probe_path(self, df: pd.DataFrame, field_name: str, step_size: float = 0.05) -> PathProbeResult:
        """
        沿指定字段进行路径探测

        将数据排序后按步长分段扫描，每段计算密度、平均值、异常分数，
        识别临界点和异常区域。

        Args:
            df: 要探测的DataFrame
            field_name: 要探测的字段名
            step_size: 步长（百分位分段大小，0.05表示20段）

        Returns:
            路径探测结果
        """
        start_time = time.time()
        logger.debug(f"开始对字段 '{field_name}' 进行路径探测，步长: {step_size}")

        if field_name not in df.columns:
            logger.warning(f"字段 '{field_name}' 不存在于数据集中")
            return PathProbeResult(
                dimension=field_name,
                step_size=step_size,
                total_depth=self.probe_depth,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        values = df[field_name].dropna()

        if not pd.api.types.is_numeric_dtype(values):
            logger.debug(f"字段 '{field_name}' 非数值类型，使用频次统计降级处理")
            return self._probe_path_categorical(df, field_name, step_size, start_time)

        if len(values) < 2:
            logger.debug(f"字段 '{field_name}' 有效数据不足，返回空结果")
            return PathProbeResult(
                dimension=field_name,
                step_size=step_size,
                total_depth=self.probe_depth,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        sorted_values = values.sort_values().reset_index(drop=True)
        n = len(sorted_values)

        overall_mean = sorted_values.mean()
        overall_std = sorted_values.std()

        num_steps = max(int(1.0 / step_size), 2)
        step_size_actual = 1.0 / num_steps

        path_points: List[PathProbePoint] = []
        densities: List[float] = []

        for i in range(num_steps):
            start_pct = i * step_size_actual
            end_pct = (i + 1) * step_size_actual
            position = (start_pct + end_pct) / 2

            start_idx = int(start_pct * n)
            end_idx = int(end_pct * n)
            if end_idx == start_idx:
                end_idx = min(start_idx + 1, n)

            segment = sorted_values.iloc[start_idx:end_idx]
            segment_size = len(segment)

            if segment_size == 0:
                density = 0.0
                seg_mean = 0.0
                anomaly_score = 0.0
            else:
                density = segment_size / n
                seg_mean = segment.mean()
                if overall_std > 0:
                    anomaly_score = abs(seg_mean - overall_mean) / overall_std
                else:
                    anomaly_score = 0.0

            densities.append(density)

            is_critical = False
            description = ""

            if anomaly_score > 2.0:
                is_critical = True
                description = f"异常值区域，z分数: {anomaly_score:.2f}"

            if i > 0 and densities[i - 1] > 0:
                density_change = abs(density - densities[i - 1]) / densities[i - 1]
                if density_change > 0.5:
                    is_critical = True
                    if description:
                        description += "；"
                    description += f"密度突变，变化率: {density_change:.2f}"

            point = PathProbePoint(
                position=position,
                density=density,
                value=float(seg_mean),
                is_critical=is_critical,
                anomaly_score=float(anomaly_score),
                description=description,
            )
            path_points.append(point)

        critical_points = [p for p in path_points if p.is_critical]

        anomaly_regions = self.find_anomaly_regions(path_points)

        distribution = self._compute_distribution_stats(sorted_values)

        result = PathProbeResult(
            dimension=field_name,
            path_points=path_points,
            distribution=distribution,
            critical_points=critical_points,
            anomaly_regions=anomaly_regions,
            step_size=step_size_actual,
            total_depth=self.probe_depth,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

        logger.debug(
            f"字段 '{field_name}' 路径探测完成，探测点数: {len(path_points)}, "
            f"临界点: {len(critical_points)}, 异常区域: {len(anomaly_regions)}"
        )
        return result

    def _probe_path_categorical(
        self, df: pd.DataFrame, field_name: str, step_size: float, start_time: float
    ) -> PathProbeResult:
        """
        对非数值字段进行路径探测的降级处理（按频次排序）

        Args:
            df: DataFrame
            field_name: 字段名
            step_size: 步长
            start_time: 开始时间

        Returns:
            路径探测结果
        """
        values = df[field_name].dropna()
        n = len(values)

        if n == 0:
            return PathProbeResult(
                dimension=field_name,
                step_size=step_size,
                total_depth=self.probe_depth,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        value_counts = values.value_counts()
        total_unique = len(value_counts)

        num_steps = max(int(1.0 / step_size), 2)
        step_size_actual = 1.0 / num_steps

        path_points: List[PathProbePoint] = []
        cumulative = 0.0

        for i in range(num_steps):
            start_pct = i * step_size_actual
            end_pct = (i + 1) * step_size_actual
            position = (start_pct + end_pct) / 2

            start_idx = int(start_pct * total_unique)
            end_idx = int(end_pct * total_unique)
            if end_idx == start_idx:
                end_idx = min(start_idx + 1, total_unique)

            segment_counts = value_counts.iloc[start_idx:end_idx]
            segment_total = segment_counts.sum()
            density = segment_total / n if n > 0 else 0.0

            point = PathProbePoint(
                position=position,
                density=density,
                value=float(len(segment_counts)),
                is_critical=False,
                anomaly_score=0.0,
                description=f"类别数: {len(segment_counts)}",
            )
            path_points.append(point)

        distribution = {
            "unique_count": float(total_unique),
            "total_count": float(n),
            "most_frequent": float(value_counts.iloc[0]) if total_unique > 0 else 0.0,
        }

        return PathProbeResult(
            dimension=field_name,
            path_points=path_points,
            distribution=distribution,
            critical_points=[],
            anomaly_regions=[],
            step_size=step_size_actual,
            total_depth=self.probe_depth,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    def probe_path_multi(
        self, df: pd.DataFrame, field_names: List[str], step_size: float = 0.05
    ) -> Dict[str, PathProbeResult]:
        """
        多维度组合路径探测

        对每个指定字段分别进行路径探测，返回字段名到结果的映射。

        Args:
            df: 要探测的DataFrame
            field_names: 要探测的字段名列表
            step_size: 步长

        Returns:
            字段名到路径探测结果的映射
        """
        logger.info(f"开始多维度路径探测，字段数: {len(field_names)}")

        results: Dict[str, PathProbeResult] = {}
        for field_name in field_names:
            results[field_name] = self.probe_path(df, field_name, step_size)

        logger.info(f"多维度路径探测完成，共 {len(results)} 个字段")
        return results

    def analyze_topology(self, df: pd.DataFrame) -> DimensionTopology:
        """
        分析维度空间拓扑结构

        计算质心、密度分布、边界点、聚类，以及字段间距离矩阵。

        Args:
            df: 要分析的DataFrame

        Returns:
            维度空间拓扑描述
        """
        start_time = time.time()
        logger.info(f"开始维度空间拓扑分析，记录数: {len(df)}, 字段数: {len(df.columns)}")

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        num_dimensions = len(numeric_cols)

        density_distribution: Dict[str, float] = {}
        centroid: Dict[str, float] = {}
        boundary_points: List[Dict[str, Any]] = []

        for col in numeric_cols:
            values = df[col].dropna()
            n = len(values)
            if n > 0:
                total_range = values.max() - values.min()
                density = n / total_range if total_range > 0 else 0.0
                density_distribution[col] = float(density)
                centroid[col] = float(values.mean())
                boundary_points.append({
                    "field": col,
                    "min": float(values.min()),
                    "max": float(values.max()),
                    "range": float(total_range),
                })

        distance_matrix = None
        if num_dimensions >= 2:
            distance_matrix = self.compute_distance_matrix(df)

        cluster_info = self.detect_clusters(df)
        cluster_count = len(cluster_info)

        result = DimensionTopology(
            num_dimensions=num_dimensions,
            distance_matrix=distance_matrix,
            density_distribution=density_distribution,
            centroid=centroid,
            boundary_points=boundary_points,
            cluster_count=cluster_count,
            cluster_info=cluster_info,
        )

        logger.info(
            f"维度空间拓扑分析完成，维度数: {num_dimensions}, "
            f"聚类数: {cluster_count}, 耗时: {(time.time() - start_time) * 1000:.2f}ms"
        )
        return result

    def find_critical_points(self, values: pd.Series, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """
        在数值序列中查找临界点

        临界点包括密度突变点、极值点、离群点。

        Args:
            values: 数值序列
            threshold: 异常分数阈值

        Returns:
            临界点列表（位置、值、类型、严重程度）
        """
        logger.debug(f"查找临界点，数据量: {len(values)}, 阈值: {threshold}")

        values_clean = values.dropna()
        if len(values_clean) < 3:
            return []

        sorted_vals = values_clean.sort_values().reset_index(drop=True)
        n = len(sorted_vals)
        mean_val = sorted_vals.mean()
        std_val = sorted_vals.std()

        critical_points: List[Dict[str, Any]] = []

        if std_val > 0:
            z_scores = (sorted_vals - mean_val) / std_val
            outlier_mask = z_scores.abs() > threshold
            outlier_indices = sorted_vals.index[outlier_mask].tolist()

            for idx in outlier_indices:
                position = idx / n
                z = z_scores.iloc[idx]
                severity = "high" if abs(z) > 3 else "medium"
                critical_points.append({
                    "position": float(position),
                    "value": float(sorted_vals.iloc[idx]),
                    "type": "outlier",
                    "severity": severity,
                    "z_score": float(z),
                })

        if n >= 10:
            window = max(n // 20, 2)
            densities = []
            for i in range(n):
                start = max(0, i - window)
                end = min(n, i + window + 1)
                local_count = end - start
                local_range = sorted_vals.iloc[end - 1] - sorted_vals.iloc[start]
                if local_range > 0:
                    density = local_count / local_range
                else:
                    density = float(local_count)
                densities.append(density)

            if len(densities) >= 3:
                density_arr = np.array(densities)
                mean_density = density_arr.mean()
                std_density = density_arr.std()

                if std_density > 0:
                    density_z = (density_arr - mean_density) / std_density
                    for i in range(n):
                        if abs(density_z[i]) > threshold:
                            position = i / n
                            severity = "high" if abs(density_z[i]) > 3 else "medium"
                            critical_points.append({
                                "position": float(position),
                                "value": float(sorted_vals.iloc[i]),
                                "type": "density_change",
                                "severity": severity,
                                "density_z_score": float(density_z[i]),
                            })

        logger.debug(f"找到 {len(critical_points)} 个临界点")
        return critical_points

    def find_anomaly_regions(
        self, points: List[PathProbePoint], min_consecutive: int = 3
    ) -> List[Dict[str, Any]]:
        """
        从路径探测点中识别连续异常区域

        异常定义：anomaly_score > 2.0，且连续 min_consecutive 个点。

        Args:
            points: 路径探测点列表
            min_consecutive: 最小连续异常点数

        Returns:
            异常区域列表（起始位置、结束位置、严重程度、描述）
        """
        logger.debug(f"识别异常区域，探测点数: {len(points)}, 最小连续: {min_consecutive}")

        if len(points) < min_consecutive:
            return []

        anomaly_threshold = 2.0
        anomaly_regions: List[Dict[str, Any]] = []

        i = 0
        while i < len(points):
            if points[i].anomaly_score > anomaly_threshold:
                start_idx = i
                max_score = points[i].anomaly_score

                while i < len(points) and points[i].anomaly_score > anomaly_threshold:
                    max_score = max(max_score, points[i].anomaly_score)
                    i += 1

                end_idx = i - 1
                consecutive_count = end_idx - start_idx + 1

                if consecutive_count >= min_consecutive:
                    start_pos = points[start_idx].position
                    end_pos = points[end_idx].position
                    severity = "high" if max_score >= 3 else "medium"
                    description = (
                        f"连续 {consecutive_count} 个异常点，"
                        f"位置 {start_pos:.3f}-{end_pos:.3f}，"
                        f"最大异常分数 {max_score:.2f}"
                    )

                    anomaly_regions.append({
                        "start": float(start_pos),
                        "end": float(end_pos),
                        "severity": severity,
                        "description": description,
                        "consecutive_count": consecutive_count,
                        "max_anomaly_score": float(max_score),
                    })
            else:
                i += 1

        logger.debug(f"找到 {len(anomaly_regions)} 个异常区域")
        return anomaly_regions

    def compute_distance_matrix(self, df: pd.DataFrame) -> List[List[float]]:
        """
        计算数值字段间的距离矩阵

        距离 = 1 - abs(相关系数)

        Args:
            df: 要计算的DataFrame

        Returns:
            对称距离矩阵
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        n_cols = len(numeric_cols)

        if n_cols < 2:
            return [[0.0]] if n_cols == 1 else []

        logger.debug(f"计算距离矩阵，数值字段数: {n_cols}")

        corr_matrix = df[numeric_cols].corr().fillna(0.0)
        distance_matrix: List[List[float]] = []

        for i in range(n_cols):
            row = []
            for j in range(n_cols):
                if i == j:
                    distance = 0.0
                else:
                    corr = abs(corr_matrix.iloc[i, j])
                    distance = 1.0 - min(corr, 1.0)
                row.append(float(distance))
            distance_matrix.append(row)

        return distance_matrix

    def detect_clusters(self, df: pd.DataFrame, n_clusters: int = 3) -> List[Dict[str, Any]]:
        """
        对数据进行简单聚类分析

        使用分位数聚类方法，不依赖外部机器学习库。

        Args:
            df: 要聚类的DataFrame
            n_clusters: 聚类数量

        Returns:
            每个聚类的信息：大小、中心、特征描述
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) == 0 or len(df) < n_clusters:
            logger.debug("数据不足，无法聚类")
            return []

        n_clusters = min(n_clusters, len(df))
        logger.debug(f"检测聚类，数值字段: {len(numeric_cols)}, 目标聚类数: {n_clusters}")

        primary_col = numeric_cols[0]
        values = df[primary_col].dropna()
        if len(values) < n_clusters:
            return []

        sorted_vals = values.sort_values()
        n = len(sorted_vals)
        cluster_size = n // n_clusters

        clusters = []
        for k in range(n_clusters):
            start_idx = k * cluster_size
            end_idx = (k + 1) * cluster_size if k < n_clusters - 1 else n

            cluster_vals = sorted_vals.iloc[start_idx:end_idx]
            cluster_center = cluster_vals.mean()

            feature_desc = {}
            for col in numeric_cols:
                col_vals = df.loc[cluster_vals.index, col].dropna()
                if len(col_vals) > 0:
                    feature_desc[col] = {
                        "mean": float(col_vals.mean()),
                        "min": float(col_vals.min()),
                        "max": float(col_vals.max()),
                        "std": float(col_vals.std()) if len(col_vals) > 1 else 0.0,
                    }

            clusters.append({
                "cluster_id": k,
                "size": int(len(cluster_vals)),
                "center": {primary_col: float(cluster_center)},
                "feature_description": feature_desc,
                "range": {
                    "min": float(cluster_vals.min()),
                    "max": float(cluster_vals.max()),
                },
            })

        return clusters

    def generate_density_histogram(
        self, values: pd.Series, bins: int = 20
    ) -> Dict[str, Any]:
        """
        生成数据密度直方图数据

        Args:
            values: 数值序列
            bins: 分箱数量

        Returns:
            包含bin边界、计数、密度值、峰值位置的字典
        """
        logger.debug(f"生成密度直方图，数据量: {len(values)}, 分箱数: {bins}")

        values_clean = values.dropna()
        if len(values_clean) == 0:
            return {
                "bin_edges": [],
                "counts": [],
                "densities": [],
                "peak_position": None,
                "peak_value": 0.0,
                "total_count": 0,
            }

        if len(values_clean) < bins:
            bins = max(len(values_clean), 1)

        counts, bin_edges = np.histogram(values_clean, bins=bins)
        densities = counts / len(values_clean) if len(values_clean) > 0 else counts.astype(float)

        peak_idx = int(np.argmax(counts))
        peak_position = (bin_edges[peak_idx] + bin_edges[peak_idx + 1]) / 2
        peak_value = float(counts[peak_idx])

        return {
            "bin_edges": bin_edges.tolist(),
            "counts": counts.tolist(),
            "densities": densities.tolist(),
            "peak_position": float(peak_position),
            "peak_value": peak_value,
            "total_count": int(len(values_clean)),
        }

    def _compute_distribution_stats(self, values: pd.Series) -> Dict[str, float]:
        """
        计算分布统计量

        Args:
            values: 数值序列

        Returns:
            分布统计字典
        """
        if len(values) == 0:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "skew": 0.0,
                "kurtosis": 0.0,
            }

        result = {
            "min": float(values.min()),
            "max": float(values.max()),
            "mean": float(values.mean()),
            "median": float(values.median()),
            "std": float(values.std()) if len(values) > 1 else 0.0,
        }

        if len(values) > 1 and values.std() > 0:
            result["skew"] = float(values.skew())
            result["kurtosis"] = float(values.kurtosis())
        else:
            result["skew"] = 0.0
            result["kurtosis"] = 0.0

        return result
