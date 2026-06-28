"""
质能质量子奇点检测模块

提供数据质量临界点和奇点检测功能，识别质量异常、维度坍缩、质能失衡等奇点现象。
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ai_llm_agent_crawler.dimension.models import (
    DataMassEnergy,
    DimensionType,
    QualityAssessment,
    SingularityDetectionResult,
    SingularityPoint,
    SingularitySeverity,
    SingularityType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SingularityRule:
    """奇点检测规则"""
    singularity_type: SingularityType
    threshold: float
    detection_method: str  # threshold, statistical, pattern, hybrid
    conditions: Dict[str, Any]
    severity_mapping: Dict[str, SingularitySeverity]  # 条件到严重程度的映射


class SingularityDetector:
    """
    质能质量子奇点检测器

    检测数据质量的临界点和奇点现象，包括：
    - 质量阈值奇点：质量指标低于临界阈值
    - 维度坍缩奇点：维度分布异常集中
    - 数据异常奇点：数据值异常（离群点等）
    - 临界点奇点：数据状态即将发生重大变化
    - 质能奇点：数据质能关系失衡
    - 量子纠缠点：数据间存在异常关联
    """

    DEFAULT_RULES: Dict[SingularityType, SingularityRule] = {
        SingularityType.QUALITY_THRESHOLD: SingularityRule(
            singularity_type=SingularityType.QUALITY_THRESHOLD,
            threshold=0.5,
            detection_method="threshold",
            conditions={
                "min_score": 0.3,
                "consecutive_low": 3,
            },
            severity_mapping={
                "score_below_0.3": SingularitySeverity.CRITICAL,
                "score_below_0.5": SingularitySeverity.HIGH,
                "score_below_0.7": SingularitySeverity.MEDIUM,
            },
        ),
        SingularityType.DIMENSION_COLLAPSE: SingularityRule(
            singularity_type=SingularityType.DIMENSION_COLLAPSE,
            threshold=0.8,
            detection_method="statistical",
            conditions={
                "max_dimension_ratio": 0.6,
                "min_dimensions": 2,
            },
            severity_mapping={
                "single_dimension": SingularitySeverity.CRITICAL,
                "ratio_above_0.6": SingularitySeverity.HIGH,
                "ratio_above_0.4": SingularitySeverity.MEDIUM,
            },
        ),
        SingularityType.DATA_ANOMALY: SingularityRule(
            singularity_type=SingularityType.DATA_ANOMALY,
            threshold=3.0,  # Z-score阈值
            detection_method="statistical",
            conditions={
                "zscore_threshold": 3.0,
                "iqr_factor": 1.5,
                "min_anomaly_ratio": 0.05,
            },
            severity_mapping={
                "zscore_above_5": SingularitySeverity.CRITICAL,
                "zscore_above_3": SingularitySeverity.HIGH,
                "zscore_above_2": SingularitySeverity.MEDIUM,
            },
        ),
        SingularityType.CRITICAL_POINT: SingularityRule(
            singularity_type=SingularityType.CRITICAL_POINT,
            threshold=0.9,
            detection_method="hybrid",
            conditions={
                "change_rate_threshold": 0.2,
                "stability_threshold": 0.05,
            },
            severity_mapping={
                "rapid_change": SingularitySeverity.HIGH,
                "instability": SingularitySeverity.MEDIUM,
            },
        ),
        SingularityType.ENERGY_SINGULARITY: SingularityRule(
            singularity_type=SingularityType.ENERGY_SINGULARITY,
            threshold=0.5,
            detection_method="threshold",
            conditions={
                "mass_energy_ratio_range": (0.5, 2.0),
                "entropy_threshold": 5.0,
            },
            severity_mapping={
                "ratio_extreme": SingularitySeverity.CRITICAL,
                "ratio_abnormal": SingularitySeverity.HIGH,
                "entropy_high": SingularitySeverity.MEDIUM,
            },
        ),
        SingularityType.QUANTUM_ENTANGLEMENT: SingularityRule(
            singularity_type=SingularityType.QUANTUM_ENTANGLEMENT,
            threshold=0.8,
            detection_method="statistical",
            conditions={
                "correlation_threshold": 0.95,
                "min_fields": 2,
            },
            severity_mapping={
                "perfect_correlation": SingularitySeverity.CRITICAL,
                "high_correlation": SingularitySeverity.HIGH,
                "moderate_correlation": SingularitySeverity.MEDIUM,
            },
        ),
    }

    def __init__(
        self,
        custom_rules: Optional[Dict[SingularityType, SingularityRule]] = None,
        enable_parallel: bool = True,
        max_workers: int = 4,
        sensitivity: float = 0.8,
    ):
        """
        初始化奇点检测器

        Args:
            custom_rules: 自定义检测规则
            enable_parallel: 是否启用并行处理
            max_workers: 最大并行工作线程数
            sensitivity: 检测敏感度（0-1）
        """
        self.rules = dict(self.DEFAULT_RULES)
        if custom_rules:
            self.rules.update(custom_rules)

        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.sensitivity = sensitivity

        logger.info(f"奇点检测器初始化完成，加载 {len(self.rules)} 条规则，敏感度: {sensitivity}")

    def detect(
        self,
        df: pd.DataFrame,
        assessment: Optional[QualityAssessment] = None,
        dimension_distribution: Optional[Dict[DimensionType, int]] = None,
        mass_energy: Optional[DataMassEnergy] = None,
    ) -> SingularityDetectionResult:
        """
        执行奇点检测

        Args:
            df: 数据DataFrame
            assessment: 质量评估结果
            dimension_distribution: 维度分布
            mass_energy: 数据质能模型

        Returns:
            奇点检测结果
        """
        start_time = time.time()
        result = SingularityDetectionResult()

        # 检测质量阈值奇点
        if assessment:
            quality_singularities = self._detect_quality_threshold_singularities(
                df, assessment
            )
            for s in quality_singularities:
                result.add_singularity(s)

        # 检测维度坍缩奇点
        if dimension_distribution:
            dimension_singularities = self._detect_dimension_collapse_singularities(
                df, dimension_distribution
            )
            for s in dimension_singularities:
                result.add_singularity(s)

        # 检测数据异常奇点
        anomaly_singularities = self._detect_data_anomaly_singularities(df)
        for s in anomaly_singularities:
            result.add_singularity(s)

        # 检测临界点奇点
        critical_singularities = self._detect_critical_point_singularities(df, assessment)
        for s in critical_singularities:
            result.add_singularity(s)

        # 检测质能奇点
        if mass_energy:
            energy_singularities = self._detect_energy_singularities(df, mass_energy)
            for s in energy_singularities:
                result.add_singularity(s)

        # 检测量子纠缠点
        entanglement_singularities = self._detect_quantum_entanglement_singularities(df)
        for s in entanglement_singularities:
            result.add_singularity(s)

        end_time = time.time()
        result.detection_duration_ms = (end_time - start_time) * 1000

        logger.info(
            f"奇点检测完成，共检测到 {result.total_singularity_count} 个奇点，"
            f"其中 {result.critical_count} 个为严重级别，耗时 {result.detection_duration_ms:.2f}ms"
        )

        return result

    def detect_field_singularities(
        self,
        field_name: str,
        values: pd.Series,
        field_type: Optional[str] = None,
    ) -> List[SingularityPoint]:
        """
        对单个字段检测奇点

        Args:
            field_name: 字段名称
            values: 字段值序列
            field_type: 字段类型

        Returns:
            检测到的奇点列表
        """
        singularities = []

        if len(values) == 0:
            return singularities

        # 完整性奇点检测
        null_ratio = values.isna().sum() / len(values)
        if null_ratio > 0.5:
            severity = SingularitySeverity.CRITICAL if null_ratio > 0.7 else SingularitySeverity.HIGH
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.QUALITY_THRESHOLD,
                severity=severity,
                location=(0,),
                dimension=DimensionType.QUALITY,
                quality_score=1 - null_ratio,
                threshold=0.5,
                description=f"字段 '{field_name}' 完整性奇点：{null_ratio:.2%} 缺失",
                affected_records=int(values.isna().sum()),
            ))

        # 数据异常奇点检测
        if values.dtype in ['int64', 'float64', 'int32', 'float32']:
            non_null_values = values.dropna()
            if len(non_null_values) > 10:
                anomaly_singularities = self._detect_numeric_anomalies(
                    field_name, non_null_values
                )
                singularities.extend(anomaly_singularities)

        # 唯一性奇点检测
        unique_ratio = values.nunique() / len(values)
        if unique_ratio < 0.01 and len(values) > 100:
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.DATA_ANOMALY,
                severity=SingularitySeverity.MEDIUM,
                location=(0,),
                dimension=DimensionType.STATISTICAL,
                quality_score=unique_ratio,
                threshold=0.01,
                description=f"字段 '{field_name}' 唯一性奇点：极低多样性",
                affected_records=len(values),
            ))

        return singularities

    def detect_record_singularities(
        self,
        record: Dict[str, Any],
        record_index: int,
        quality_score: Optional[float] = None,
    ) -> List[SingularityPoint]:
        """
        对单条记录检测奇点

        Args:
            record: 数据记录
            record_index: 记录索引
            quality_score: 记录质量评分

        Returns:
            检测到的奇点列表
        """
        singularities = []

        # 空记录奇点
        if not record or all(v is None or (isinstance(v, str) and v.strip() == "") for v in record.values()):
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.QUALITY_THRESHOLD,
                severity=SingularitySeverity.CRITICAL,
                location=(record_index,),
                dimension=DimensionType.QUALITY,
                quality_score=0.0,
                threshold=0.5,
                description=f"记录 {record_index} 为完全空记录",
                affected_records=1,
            ))
            return singularities

        # 低质量记录奇点
        if quality_score is not None and quality_score < 0.5:
            severity = SingularitySeverity.CRITICAL if quality_score < 0.3 else SingularitySeverity.HIGH
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.QUALITY_THRESHOLD,
                severity=severity,
                location=(record_index,),
                dimension=DimensionType.QUALITY,
                quality_score=quality_score,
                threshold=0.5,
                description=f"记录 {record_index} 质量评分过低: {quality_score:.2f}",
                affected_records=1,
            ))

        return singularities

    def _detect_quality_threshold_singularities(
        self,
        df: pd.DataFrame,
        assessment: QualityAssessment,
    ) -> List[SingularityPoint]:
        """检测质量阈值奇点"""
        singularities = []

        for metric in assessment.metrics:
            if not metric.is_acceptable:
                # 根据评分差距确定严重程度
                deficit_ratio = metric.threshold - metric.score
                if deficit_ratio > 0.4:
                    severity = SingularitySeverity.CRITICAL
                elif deficit_ratio > 0.2:
                    severity = SingularitySeverity.HIGH
                else:
                    severity = SingularitySeverity.MEDIUM

                # 根据敏感度调整阈值
                adjusted_threshold = metric.threshold * self.sensitivity

                singularities.append(SingularityPoint(
                    singularity_type=SingularityType.QUALITY_THRESHOLD,
                    severity=severity,
                    location=(0,),  # 数据集级别
                    dimension=DimensionType.QUALITY,
                    quality_score=metric.score,
                    threshold=adjusted_threshold,
                    description=f"质量指标 '{metric.metric_type}' 低于阈值: {metric.score:.2f} < {adjusted_threshold:.2f}",
                    affected_records=assessment.record_count,
                    metadata={"metric_type": metric.metric_type},
                ))

        return singularities

    def _detect_dimension_collapse_singularities(
        self,
        df: pd.DataFrame,
        dimension_distribution: Dict[DimensionType, int],
    ) -> List[SingularityPoint]:
        """检测维度坍缩奇点"""
        singularities = []

        total_fields = sum(dimension_distribution.values())
        if total_fields == 0:
            return singularities

        # 计算维度集中度
        max_count = max(dimension_distribution.values())
        max_ratio = max_count / total_fields

        # 检测单一维度主导
        if max_ratio > 0.6:
            severity = SingularitySeverity.CRITICAL if max_ratio > 0.8 else SingularitySeverity.HIGH

            dominant_dimension = max(dimension_distribution, key=dimension_distribution.get)

            singularities.append(SingularityPoint(
                singularity_type=SingularityType.DIMENSION_COLLAPSE,
                severity=severity,
                location=(0,),
                dimension=dominant_dimension,
                quality_score=max_ratio,
                threshold=0.6,
                description=f"维度坍缩奇点：{dominant_dimension.value} 维度占比 {max_ratio:.2%} 过高",
                affected_records=len(df),
                metadata={
                    "dominant_dimension": dominant_dimension.value,
                    "dimension_distribution": {d.value: c for d, c in dimension_distribution.items()},
                },
            ))

        # 检测维度缺失
        missing_dimensions = [dim.value for dim in DimensionType if dim not in dimension_distribution]
        if len(missing_dimensions) > len(DimensionType) * 0.5:
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.DIMENSION_COLLAPSE,
                severity=SingularitySeverity.MEDIUM,
                location=(0,),
                dimension=DimensionType.STRUCTURAL,
                quality_score=len(dimension_distribution) / len(DimensionType),
                threshold=0.5,
                description=f"维度缺失奇点：缺少 {len(missing_dimensions)} 个维度类型",
                affected_records=len(df),
                metadata={"missing_dimensions": missing_dimensions},
            ))

        return singularities

    def _detect_data_anomaly_singularities(
        self,
        df: pd.DataFrame,
    ) -> List[SingularityPoint]:
        """检测数据异常奇点"""
        singularities = []

        # 对数值字段检测异常值
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            non_null_values = df[col].dropna()
            if len(non_null_values) < 10:
                continue

            anomalies = self._detect_numeric_anomalies(col, non_null_values)
            singularities.extend(anomalies)

        # 对文本字段检测异常模式
        text_cols = df.select_dtypes(include=['object']).columns
        for col in text_cols:
            non_null_values = df[col].dropna()
            if len(non_null_values) < 10:
                continue

            anomalies = self._detect_text_anomalies(col, non_null_values)
            singularities.extend(anomalies)

        return singularities

    def _detect_numeric_anomalies(
        self,
        field_name: str,
        values: pd.Series,
    ) -> List[SingularityPoint]:
        """检测数值异常"""
        singularities = []

        try:
            # Z-score检测
            mean = values.mean()
            std = values.std()

            if std > 0:
                z_scores = np.abs((values - mean) / std)
                extreme_outliers = z_scores > 5
                moderate_outliers = z_scores > 3

                extreme_count = extreme_outliers.sum()
                moderate_count = moderate_outliers.sum()

                if extreme_count > 0:
                    singularities.append(SingularityPoint(
                        singularity_type=SingularityType.DATA_ANOMALY,
                        severity=SingularitySeverity.CRITICAL,
                        location=(extreme_count,),
                        dimension=DimensionType.STATISTICAL,
                        quality_score=1 - extreme_count / len(values),
                        threshold=3.0,
                        description=f"字段 '{field_name}' 发现 {extreme_count} 个极端异常值（Z-score > 5）",
                        affected_records=int(extreme_count),
                        metadata={"zscore_max": float(z_scores.max())},
                    ))

                elif moderate_count > len(values) * 0.05:
                    singularities.append(SingularityPoint(
                        singularity_type=SingularityType.DATA_ANOMALY,
                        severity=SingularitySeverity.HIGH,
                        location=(moderate_count,),
                        dimension=DimensionType.STATISTICAL,
                        quality_score=1 - moderate_count / len(values),
                        threshold=3.0,
                        description=f"字段 '{field_name}' 发现 {moderate_count} 个异常值（Z-score > 3）",
                        affected_records=int(moderate_count),
                        metadata={"anomaly_ratio": float(moderate_count / len(values))},
                    ))

            # IQR检测
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1

            if iqr > 0:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr

                iqr_outliers = ((values < lower_bound) | (values > upper_bound)).sum()

                if iqr_outliers > len(values) * 0.1:
                    singularities.append(SingularityPoint(
                        singularity_type=SingularityType.DATA_ANOMALY,
                        severity=SingularitySeverity.MEDIUM,
                        location=(iqr_outliers,),
                        dimension=DimensionType.STATISTICAL,
                        quality_score=1 - iqr_outliers / len(values),
                        threshold=0.1,
                        description=f"字段 '{field_name}' 发现 {iqr_outliers} 个IQR异常值",
                        affected_records=int(iqr_outliers),
                        metadata={"iqr_bounds": [lower_bound, upper_bound]},
                    ))

        except Exception as e:
            logger.warning(f"数值异常检测失败 '{field_name}': {e}")

        return singularities

    def _detect_text_anomalies(
        self,
        field_name: str,
        values: pd.Series,
    ) -> List[SingularityPoint]:
        """检测文本异常"""
        singularities = []

        try:
            # 长度异常检测
            lengths = values.str.len()
            mean_len = lengths.mean()
            std_len = lengths.std()

            if std_len > 0:
                extreme_short = lengths < mean_len - 3 * std_len
                extreme_long = lengths > mean_len + 3 * std_len

                abnormal_count = (extreme_short | extreme_long).sum()

                if abnormal_count > len(values) * 0.05:
                    singularities.append(SingularityPoint(
                        singularity_type=SingularityType.DATA_ANOMALY,
                        severity=SingularitySeverity.MEDIUM,
                        location=(abnormal_count,),
                        dimension=DimensionType.CONTENT,
                        quality_score=1 - abnormal_count / len(values),
                        threshold=0.05,
                        description=f"字段 '{field_name}' 发现 {abnormal_count} 个长度异常值",
                        affected_records=int(abnormal_count),
                        metadata={
                            "avg_length": float(mean_len),
                            "std_length": float(std_len),
                        },
                    ))

            # 模式异常检测（空字符串过多）
            empty_count = (values.str.strip() == "").sum()
            if empty_count > len(values) * 0.3:
                singularities.append(SingularityPoint(
                    singularity_type=SingularityType.DATA_ANOMALY,
                    severity=SingularitySeverity.HIGH,
                    location=(empty_count,),
                    dimension=DimensionType.CONTENT,
                    quality_score=1 - empty_count / len(values),
                    threshold=0.3,
                    description=f"字段 '{field_name}' 发现 {empty_count} 个空字符串",
                    affected_records=int(empty_count),
                ))

        except Exception as e:
            logger.warning(f"文本异常检测失败 '{field_name}': {e}")

        return singularities

    def _detect_critical_point_singularities(
        self,
        df: pd.DataFrame,
        assessment: Optional[QualityAssessment],
    ) -> List[SingularityPoint]:
        """检测临界点奇点"""
        singularities = []

        # 检测数据量临界点
        if len(df) < 100:
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.CRITICAL_POINT,
                severity=SingularitySeverity.MEDIUM,
                location=(len(df),),
                dimension=DimensionType.STATISTICAL,
                quality_score=len(df) / 100.0,
                threshold=100,
                description=f"数据量临界点：仅 {len(df)} 条记录",
                affected_records=len(df),
            ))

        # 检测字段数临界点
        if len(df.columns) < 3:
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.CRITICAL_POINT,
                severity=SingularitySeverity.MEDIUM,
                location=(len(df.columns),),
                dimension=DimensionType.STRUCTURAL,
                quality_score=len(df.columns) / 3.0,
                threshold=3,
                description=f"字段数临界点：仅 {len(df.columns)} 个字段",
                affected_records=len(df),
            ))

        # 检测质量临界点
        if assessment:
            critical_metrics = [
                m for m in assessment.metrics
                if m.threshold - m.score < 0.1 and not m.is_acceptable
            ]
            if critical_metrics:
                singularities.append(SingularityPoint(
                    singularity_type=SingularityType.CRITICAL_POINT,
                    severity=SingularitySeverity.HIGH,
                    location=(0,),
                    dimension=DimensionType.QUALITY,
                    quality_score=min(m.score for m in critical_metrics),
                    threshold=0.1,
                    description=f"质量临界点：{len(critical_metrics)} 个指标接近阈值",
                    affected_records=assessment.record_count,
                    metadata={"critical_metrics": [m.metric_type for m in critical_metrics]},
                ))

        return singularities

    def _detect_energy_singularities(
        self,
        df: pd.DataFrame,
        mass_energy: DataMassEnergy,
    ) -> List[SingularityPoint]:
        """检测质能奇点"""
        singularities = []

        # 检测质能失衡
        ratio = mass_energy.mass_energy_ratio
        if ratio < 0.3 or ratio > 3.0:
            severity = SingularitySeverity.CRITICAL if ratio < 0.1 or ratio > 5.0 else SingularitySeverity.HIGH

            singularities.append(SingularityPoint(
                singularity_type=SingularityType.ENERGY_SINGULARITY,
                severity=severity,
                location=(0,),
                dimension=DimensionType.STATISTICAL,
                quality_score=min(ratio / 0.5, 3.0 / ratio),
                threshold=0.5,
                description=f"质能失衡奇点：质能比 {ratio:.2f} 异常",
                affected_records=len(df),
                metadata={
                    "data_mass": mass_energy.data_mass,
                    "data_energy": mass_energy.data_energy,
                    "mass_energy_ratio": ratio,
                },
            ))

        # 检测熵值奇点
        if mass_energy.entropy > 8.0:
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.ENERGY_SINGULARITY,
                severity=SingularitySeverity.MEDIUM,
                location=(0,),
                dimension=DimensionType.STATISTICAL,
                quality_score=mass_energy.entropy / 10.0,
                threshold=5.0,
                description=f"熵值奇点：数据熵 {mass_energy.entropy:.2f} 过高",
                affected_records=len(df),
            ))

        # 检测密度奇点
        if mass_energy.density > 95:
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.ENERGY_SINGULARITY,
                severity=SingularitySeverity.MEDIUM,
                location=(0,),
                dimension=DimensionType.STATISTICAL,
                quality_score=mass_energy.density / 100.0,
                threshold=95,
                description=f"密度奇点：数据密度 {mass_energy.density:.2f} 过高",
                affected_records=len(df),
            ))

        # 检测奇点风险
        singularity_risk = mass_energy.calculate_singularity_risk()
        if singularity_risk > 0.7:
            singularities.append(SingularityPoint(
                singularity_type=SingularityType.ENERGY_SINGULARITY,
                severity=SingularitySeverity.HIGH if singularity_risk > 0.8 else SingularitySeverity.MEDIUM,
                location=(0,),
                dimension=DimensionType.QUALITY,
                quality_score=1 - singularity_risk,
                threshold=0.7,
                description=f"奇点风险奇点：风险指数 {singularity_risk:.2f} 高",
                affected_records=len(df),
                metadata={"singularity_risk": singularity_risk},
            ))

        return singularities

    def _detect_quantum_entanglement_singularities(
        self,
        df: pd.DataFrame,
    ) -> List[SingularityPoint]:
        """检测量子纠缠点（异常相关性）"""
        singularities = []

        # 检测数值字段间的高度相关性
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return singularities

        try:
            # 计算相关矩阵
            corr_matrix = df[numeric_cols].corr()

            # 检测极高相关性（接近1或-1）
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols):
                    if i < j:
                        corr_value = abs(corr_matrix.loc[col1, col2])
                        if pd.isna(corr_value):
                            continue

                        if corr_value > 0.98:
                            singularities.append(SingularityPoint(
                                singularity_type=SingularityType.QUANTUM_ENTANGLEMENT,
                                severity=SingularitySeverity.CRITICAL,
                                location=(i, j),
                                dimension=DimensionType.RELATIONAL,
                                quality_score=corr_value,
                                threshold=0.95,
                                description=f"量子纠缠点：'{col1}' 与 '{col2}' 近乎完全相关 ({corr_value:.3f})",
                                affected_records=len(df),
                                metadata={
                                    "correlation": corr_value,
                                    "fields": [col1, col2],
                                },
                            ))

                        elif corr_value > 0.95:
                            singularities.append(SingularityPoint(
                                singularity_type=SingularityType.QUANTUM_ENTANGLEMENT,
                                severity=SingularitySeverity.HIGH,
                                location=(i, j),
                                dimension=DimensionType.RELATIONAL,
                                quality_score=corr_value,
                                threshold=0.95,
                                description=f"高相关性纠缠点：'{col1}' 与 '{col2}' 高度相关 ({corr_value:.3f})",
                                affected_records=len(df),
                                metadata={
                                    "correlation": corr_value,
                                    "fields": [col1, col2],
                                },
                            ))

        except Exception as e:
            logger.warning(f"量子纠缠检测失败: {e}")

        return singularities

    def generate_singularity_report(
        self,
        result: SingularityDetectionResult,
    ) -> Dict[str, Any]:
        """
        生成奇点检测报告

        Args:
            result: 奇点检测结果

        Returns:
            详细报告字典
        """
        report = {
            "summary": {
                "total_singularities": result.total_singularity_count,
                "critical_count": result.critical_count,
                "high_count": len(result.get_singularities_by_severity(SingularitySeverity.HIGH)),
                "medium_count": len(result.get_singularities_by_severity(SingularitySeverity.MEDIUM)),
                "low_count": len(result.get_singularities_by_severity(SingularitySeverity.LOW)),
                "detection_duration_ms": result.detection_duration_ms,
            },
            "by_type": {},
            "by_severity": {},
            "singularities": [],
            "recommendations": [],
        }

        # 按类型统计
        for singularity_type in SingularityType:
            singularities = result.get_singularities_by_type(singularity_type)
            report["by_type"][singularity_type.value] = {
                "count": len(singularities),
                "severity_distribution": {
                    s.value: sum(1 for sing in singularities if sing.severity == s)
                    for s in SingularitySeverity
                },
            }

        # 按严重程度统计
        for severity in SingularitySeverity:
            singularities = result.get_singularities_by_severity(severity)
            report["by_severity"][severity.value] = {
                "count": len(singularities),
                "types": list(set(s.singularity_type.value for s in singularities)),
            }

        # 详细奇点列表
        for singularity in result.singularities:
            report["singularities"].append(singularity.to_dict())

        # 生成建议
        report["recommendations"] = self._generate_recommendations(result)

        return report

    def _generate_recommendations(self, result: SingularityDetectionResult) -> List[str]:
        """生成奇点处理建议"""
        recommendations = []

        # 根据奇点类型生成建议
        type_counts = {}
        for s in result.singularities:
            type_counts[s.singularity_type.value] = type_counts.get(s.singularity_type.value, 0) + 1

        for singularity_type, count in type_counts.items():
            if singularity_type == SingularityType.QUALITY_THRESHOLD.value:
                recommendations.append(f"发现 {count} 个质量阈值奇点，建议检查并修正低质量数据")
            elif singularity_type == SingularityType.DIMENSION_COLLAPSE.value:
                recommendations.append(f"发现 {count} 个维度坍缩奇点，建议增加数据维度多样性")
            elif singularity_type == SingularityType.DATA_ANOMALY.value:
                recommendations.append(f"发现 {count} 个数据异常奇点，建议处理异常值和离群点")
            elif singularity_type == SingularityType.CRITICAL_POINT.value:
                recommendations.append(f"发现 {count} 个临界点奇点，建议扩充数据量或字段数")
            elif singularity_type == SingularityType.ENERGY_SINGULARITY.value:
                recommendations.append(f"发现 {count} 个质能奇点，建议优化数据质量和信息密度")
            elif singularity_type == SingularityType.QUANTUM_ENTANGLEMENT.value:
                recommendations.append(f"发现 {count} 个量子纠缠点，建议检查数据冗余或添加新字段")

        # 根据严重程度添加紧急建议
        critical_count = result.critical_count
        if critical_count > 0:
            recommendations.insert(0, f"警告：发现 {critical_count} 个严重级别奇点，需要立即处理！")

        return recommendations


class SingularityMonitor:
    """
    奇点监控器

    提供持续监控奇点变化的功能，跟踪奇点演化轨迹。
    """

    def __init__(
        self,
        detector: SingularityDetector,
        history_size: int = 100,
        alert_threshold: int = 5,
    ):
        """
        初始化奇点监控器

        Args:
            detector: 奇点检测器
            history_size: 历史记录大小
            alert_threshold: 告警阈值（连续出现严重奇点的次数）
        """
        self.detector = detector
        self.history_size = history_size
        self.alert_threshold = alert_threshold

        self._history: List[SingularityDetectionResult] = []
        self._critical_history: List[int] = []  # 每次检测的严重奇点数量

        logger.info(f"奇点监控器初始化完成，历史大小: {history_size}")

    def monitor(
        self,
        df: pd.DataFrame,
        assessment: Optional[QualityAssessment] = None,
        dimension_distribution: Optional[Dict[DimensionType, int]] = None,
        mass_energy: Optional[DataMassEnergy] = None,
    ) -> Tuple[SingularityDetectionResult, Dict[str, Any]]:
        """
        执行监控检测

        Args:
            df: 数据DataFrame
            assessment: 质量评估结果
            dimension_distribution: 维度分布
            mass_energy: 数据质能模型

        Returns:
            检测结果和监控状态
        """
        # 执行检测
        result = self.detector.detect(df, assessment, dimension_distribution, mass_energy)

        # 记录历史
        self._history.append(result)
        self._critical_history.append(result.critical_count)

        # 保持历史大小
        if len(self._history) > self.history_size:
            self._history = self._history[-self.history_size:]
            self._critical_history = self._critical_history[-self.history_size:]

        # 分析趋势
        trend_analysis = self._analyze_trend()

        # 检查告警条件
        alert_status = self._check_alert()

        return result, {
            "trend_analysis": trend_analysis,
            "alert_status": alert_status,
            "history_size": len(self._history),
        }

    def _analyze_trend(self) -> Dict[str, Any]:
        """分析奇点趋势"""
        if len(self._history) < 2:
            return {"trend": "insufficient_data"}

        recent_results = self._history[-10:]
        recent_counts = [r.total_singularity_count for r in recent_results]
        recent_criticals = [r.critical_count for r in recent_results]

        # 计算趋势方向
        if recent_counts[-1] > recent_counts[0]:
            trend = "increasing"
        elif recent_counts[-1] < recent_counts[0]:
            trend = "decreasing"
        else:
            trend = "stable"

        # 计算变化率
        count_change = recent_counts[-1] - recent_counts[0]
        critical_change = recent_criticals[-1] - recent_criticals[0]

        return {
            "trend": trend,
            "total_singularity_change": count_change,
            "critical_change": critical_change,
            "avg_singularity_count": np.mean(recent_counts),
            "avg_critical_count": np.mean(recent_criticals),
        }

    def _check_alert(self) -> Dict[str, Any]:
        """检查告警状态"""
        if len(self._critical_history) < self.alert_threshold:
            return {"status": "normal", "consecutive_critical": 0}

        # 检查连续严重奇点
        recent_criticals = self._critical_history[-self.alert_threshold:]
        consecutive_count = sum(1 for c in recent_criticals if c > 0)

        if consecutive_count >= self.alert_threshold:
            return {
                "status": "alert",
                "consecutive_critical": consecutive_count,
                "message": f"连续 {consecutive_count} 次检测发现严重奇点，需要立即处理",
            }

        return {"status": "normal", "consecutive_critical": consecutive_count}

    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录摘要"""
        return [
            {
                "total_singularities": r.total_singularity_count,
                "critical_count": r.critical_count,
                "detection_time": r.detection_time.isoformat(),
                "detection_duration_ms": r.detection_duration_ms,
            }
            for r in self._history
        ]