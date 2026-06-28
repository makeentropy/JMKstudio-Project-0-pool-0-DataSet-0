"""
数据质量评估模块

提供完整性、准确性、一致性、时效性等多维度数据质量评估算法。
"""

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd

from ai_llm_agent_crawler.dimension.models import (
    DataMassEnergy,
    DimensionType,
    QualityAssessment,
    QualityMetric,
    QualityMetricType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class QualityAssessor:
    """
    数据质量评估器

    提供多维度数据质量评估功能，包括：
    - 完整性评估（缺失值检测）
    - 准确性评估（数据正确性检测）
    - 一致性评估（数据一致性检测）
    - 时效性评估（数据时效性检测）
    - 有效性评估（格式和规则检测）
    - 唯一性评估（重复数据检测）
    - 相关性评估（数据相关性检测）
    """

    def __init__(
        self,
        custom_thresholds: Optional[Dict[str, float]] = None,
        custom_validators: Optional[Dict[str, Callable]] = None,
    ):
        """
        初始化质量评估器

        Args:
            custom_thresholds: 自定义质量阈值
            custom_validators: 自定义验证函数
        """
        self.thresholds = {
            QualityMetricType.COMPLETENESS: 0.8,
            QualityMetricType.ACCURACY: 0.9,
            QualityMetricType.CONSISTENCY: 0.85,
            QualityMetricType.TIMELINESS: 0.7,
            QualityMetricType.VALIDITY: 0.95,
            QualityMetricType.UNIQUENSS: 0.9,
            QualityMetricType.RELEVANCE: 0.75,
        }

        if custom_thresholds:
            for metric_name, threshold in custom_thresholds.items():
                try:
                    metric_type = QualityMetricType(metric_name)
                    self.thresholds[metric_type] = threshold
                except ValueError:
                    logger.warning(f"未知的质量指标类型: {metric_name}")

        self.custom_validators = custom_validators or {}
        logger.info(f"质量评估器初始化完成，阈值: {self.thresholds}")

    def assess_dataframe(
        self,
        df: pd.DataFrame,
        data_source: Optional[str] = None,
        time_field: Optional[str] = None,
        validation_rules: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> QualityAssessment:
        """
        对DataFrame进行综合质量评估

        Args:
            df: 要评估的DataFrame
            data_source: 数据源标识
            time_field: 时间字段名（用于时效性评估）
            validation_rules: 字段验证规则

        Returns:
            质量评估结果
        """
        metrics: List[QualityMetric] = []

        # 评估完整性
        completeness = self._assess_completeness(df)
        metrics.append(QualityMetric(
            metric_type=QualityMetricType.COMPLETENESS,
            score=completeness,
            threshold=self.thresholds[QualityMetricType.COMPLETENESS],
            weight=1.0,
            details={"method": "null_ratio"},
        ))

        # 评估准确性
        accuracy = self._assess_accuracy(df, validation_rules)
        metrics.append(QualityMetric(
            metric_type=QualityMetricType.ACCURACY,
            score=accuracy,
            threshold=self.thresholds[QualityMetricType.ACCURACY],
            weight=1.0,
            details={"method": "validation_rules"},
        ))

        # 评估一致性
        consistency = self._assess_consistency(df)
        metrics.append(QualityMetric(
            metric_type=QualityMetricType.CONSISTENCY,
            score=consistency,
            threshold=self.thresholds[QualityMetricType.CONSISTENCY],
            weight=0.8,
            details={"method": "format_consistency"},
        ))

        # 评估时效性
        timeliness = self._assess_timeliness(df, time_field)
        metrics.append(QualityMetric(
            metric_type=QualityMetricType.TIMELINESS,
            score=timeliness,
            threshold=self.thresholds[QualityMetricType.TIMELINESS],
            weight=0.7,
            details={"method": "time_decay"},
        ))

        # 评估有效性
        validity = self._assess_validity(df, validation_rules)
        metrics.append(QualityMetric(
            metric_type=QualityMetricType.VALIDITY,
            score=validity,
            threshold=self.thresholds[QualityMetricType.VALIDITY],
            weight=0.9,
            details={"method": "format_validation"},
        ))

        # 评估唯一性
        uniqueness = self._assess_uniqueness(df)
        metrics.append(QualityMetric(
            metric_type=QualityMetricType.UNIQUENSS,
            score=uniqueness,
            threshold=self.thresholds[QualityMetricType.UNIQUENSS],
            weight=0.8,
            details={"method": "duplicate_ratio"},
        ))

        # 评估相关性
        relevance = self._assess_relevance(df)
        metrics.append(QualityMetric(
            metric_type=QualityMetricType.RELEVANCE,
            score=relevance,
            threshold=self.thresholds[QualityMetricType.RELEVANCE],
            weight=0.6,
            details={"method": "information_density"},
        ))

        # 计算综合评分
        assessment = QualityAssessment(
            metrics=metrics,
            overall_score=self._calculate_overall_score(metrics),
            data_source=data_source,
            record_count=len(df),
        )

        logger.info(f"数据质量评估完成，综合评分: {assessment.overall_score:.2f}")
        return assessment

    def assess_field(
        self,
        field_name: str,
        values: pd.Series,
        validation_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[QualityMetricType, float]:
        """
        对单个字段进行质量评估

        Args:
            field_name: 字段名称
            values: 字段值序列
            validation_rules: 验证规则

        Returns:
            各质量指标的评分
        """
        results = {}

        total_count = len(values)

        if total_count == 0:
            return {mt: 0.0 for mt in QualityMetricType}

        # 完整性：非空比例
        non_null_count = values.notna().sum()
        results[QualityMetricType.COMPLETENESS] = non_null_count / total_count

        # 准确性：根据验证规则检查
        if validation_rules and field_name in validation_rules:
            accuracy = self._validate_field_values(values, validation_rules[field_name])
            results[QualityMetricType.ACCURACY] = accuracy
        else:
            results[QualityMetricType.ACCURACY] = 1.0  # 无规则默认满分

        # 一致性：格式一致性检查
        results[QualityMetricType.CONSISTENCY] = self._check_field_consistency(values)

        # 有效性：类型有效性检查
        results[QualityMetricType.VALIDITY] = self._check_field_validity(values)

        # 唯一性：非重复比例
        unique_count = values.nunique()
        duplicate_ratio = 1 - (total_count - unique_count) / total_count if total_count > 0 else 1.0
        results[QualityMetricType.UNIQUENSS] = duplicate_ratio

        return results

    def assess_record(
        self,
        record: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        对单条记录进行质量评估

        Args:
            record: 数据记录
            schema: 数据模式定义

        Returns:
            记录质量评分
        """
        if not record:
            return 0.0

        scores = []

        for field_name, value in record.items():
            field_score = 1.0

            # 检查是否存在性
            if value is None or (isinstance(value, str) and value.strip() == ""):
                field_score = 0.5

            # 根据schema检查有效性
            if schema and field_name in schema:
                field_schema = schema[field_name]

                # 类型检查
                expected_type = field_schema.get("type")
                if expected_type and not self._check_type(value, expected_type):
                    field_score *= 0.7

                # 范围检查
                min_val = field_schema.get("min")
                max_val = field_schema.get("max")
                if min_val is not None and max_val is not None:
                    if isinstance(value, (int, float)):
                        if not (min_val <= value <= max_val):
                            field_score *= 0.6

                # 格式检查
                pattern = field_schema.get("pattern")
                if pattern and isinstance(value, str):
                    import re
                    if not re.match(pattern, value):
                        field_score *= 0.5

            scores.append(field_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _assess_completeness(self, df: pd.DataFrame) -> float:
        """评估完整性"""
        if len(df) == 0:
            return 0.0

        # 计算每个字段非空比例
        field_completeness = []
        for col in df.columns:
            non_null_ratio = df[col].notna().sum() / len(df)
            field_completeness.append(non_null_ratio)

        # 综合完整性评分（加权平均）
        return sum(field_completeness) / len(field_completeness) if field_completeness else 0.0

    def _assess_accuracy(
        self,
        df: pd.DataFrame,
        validation_rules: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> float:
        """评估准确性"""
        if len(df) == 0:
            return 0.0

        validation_rules = validation_rules or {}
        scores = []

        for col in df.columns:
            if col in validation_rules:
                accuracy = self._validate_field_values(df[col], validation_rules[col])
                scores.append(accuracy)
            else:
                scores.append(1.0)

        return sum(scores) / len(scores) if scores else 0.0

    def _assess_consistency(self, df: pd.DataFrame) -> float:
        """评估一致性"""
        if len(df) == 0:
            return 0.0

        scores = []

        for col in df.columns:
            consistency = self._check_field_consistency(df[col])
            scores.append(consistency)

        return sum(scores) / len(scores) if scores else 0.0

    def _assess_timeliness(
        self,
        df: pd.DataFrame,
        time_field: Optional[str] = None,
    ) -> float:
        """评估时效性"""
        if len(df) == 0 or not time_field or time_field not in df.columns:
            return 1.0  # 无时间字段默认满分

        try:
            time_values = pd.to_datetime(df[time_field], errors='coerce')
            valid_times = time_values.dropna()

            if len(valid_times) == 0:
                return 0.0

            # 计算时效性衰减
            now = datetime.now()
            max_age_days = 365  # 最大可接受年龄（天数）

            # 计算每条记录的时效性分数
            timeliness_scores = []
            for t in valid_times:
                age_days = (now - t).days
                if age_days <= 0:
                    score = 1.0
                elif age_days <= 7:
                    score = 0.95
                elif age_days <= 30:
                    score = 0.85
                elif age_days <= 90:
                    score = 0.7
                elif age_days <= 180:
                    score = 0.5
                elif age_days <= max_age_days:
                    score = 0.3
                else:
                    score = 0.1
                timeliness_scores.append(score)

            return sum(timeliness_scores) / len(timeliness_scores)

        except Exception as e:
            logger.warning(f"时效性评估失败: {e}")
            return 0.5

    def _assess_validity(
        self,
        df: pd.DataFrame,
        validation_rules: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> float:
        """评估有效性"""
        if len(df) == 0:
            return 0.0

        validation_rules = validation_rules or {}
        scores = []

        for col in df.columns:
            validity = self._check_field_validity(df[col], validation_rules.get(col))
            scores.append(validity)

        return sum(scores) / len(scores) if scores else 0.0

    def _assess_uniqueness(self, df: pd.DataFrame) -> float:
        """评估唯一性"""
        if len(df) == 0:
            return 0.0

        # 计算完全重复行比例
        duplicate_rows = df.duplicated().sum()
        uniqueness = 1 - duplicate_rows / len(df)

        return uniqueness

    def _assess_relevance(self, df: pd.DataFrame) -> float:
        """评估相关性（信息密度）"""
        if len(df) == 0:
            return 0.0

        # 基于信息密度评估相关性
        scores = []

        for col in df.columns:
            non_null_values = df[col].dropna()
            if len(non_null_values) == 0:
                scores.append(0.0)
                continue

            # 计算信息熵（信息密度指标）
            if df[col].dtype == 'object':
                # 文本类型：基于不同值数量
                unique_ratio = non_null_values.nunique() / len(non_null_values)
                scores.append(unique_ratio)
            else:
                # 数值类型：基于标准差/均值比例
                try:
                    std = non_null_values.std()
                    mean = non_null_values.mean()
                    if abs(mean) > 0:
                        variation = abs(std / mean)
                        score = min(variation, 1.0)
                    else:
                        score = 0.5
                    scores.append(score)
                except Exception:
                    scores.append(0.5)

        return sum(scores) / len(scores) if scores else 0.0

    def _validate_field_values(
        self,
        values: pd.Series,
        rules: Dict[str, Any],
    ) -> float:
        """验证字段值"""
        if len(values) == 0:
            return 0.0

        valid_count = 0

        for value in values:
            if pd.isna(value):
                continue

            is_valid = True

            # 类型验证
            expected_type = rules.get("type")
            if expected_type and not self._check_type(value, expected_type):
                is_valid = False

            # 范围验证
            min_val = rules.get("min")
            max_val = rules.get("max")
            if min_val is not None and max_val is not None:
                if isinstance(value, (int, float)):
                    if not (min_val <= value <= max_val):
                        is_valid = False

            # 正则模式验证
            pattern = rules.get("pattern")
            if pattern and isinstance(value, str):
                import re
                if not re.match(pattern, str(value)):
                    is_valid = False

            # 自定义验证
            custom_validator = rules.get("custom_validator")
            if custom_validator and callable(custom_validator):
                if not custom_validator(value):
                    is_valid = False

            if is_valid:
                valid_count += 1

        non_null_count = values.notna().sum()
        return valid_count / non_null_count if non_null_count > 0 else 0.0

    def _check_field_consistency(self, values: pd.Series) -> float:
        """检查字段一致性"""
        if len(values) == 0:
            return 0.0

        non_null_values = values.dropna()
        if len(non_null_values) == 0:
            return 0.0

        # 检查数据类型一致性
        types = set()
        for val in non_null_values:
            types.add(type(val).__name__)

        type_consistency = 1.0 if len(types) <= 2 else 0.7

        # 检查格式一致性（对于字符串）
        if values.dtype == 'object':
            # 检查长度分布
            lengths = non_null_values.astype(str).str.len()
            length_std = lengths.std()
            length_mean = lengths.mean()
            if length_mean > 0:
                length_consistency = 1 - min(length_std / length_mean, 1.0)
            else:
                length_consistency = 1.0

            return (type_consistency + length_consistency) / 2

        return type_consistency

    def _check_field_validity(
        self,
        values: pd.Series,
        rules: Optional[Dict[str, Any]] = None,
    ) -> float:
        """检查字段有效性"""
        if len(values) == 0:
            return 0.0

        non_null_count = values.notna().sum()
        if non_null_count == 0:
            return 0.0

        # 基本有效性检查
        valid_count = 0

        for value in values.dropna():
            is_valid = True

            # 检查异常值
            if isinstance(value, (int, float)):
                # 检查NaN和Inf
                if pd.isna(value) or np.isinf(value):
                    is_valid = False

            # 检查空字符串
            if isinstance(value, str) and value.strip() == "":
                is_valid = False

            if is_valid:
                valid_count += 1

        return valid_count / non_null_count

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查值类型"""
        type_mapping = {
            "string": str,
            "integer": int,
            "float": float,
            "number": (int, float),
            "boolean": bool,
            "datetime": datetime,
            "list": list,
            "dict": dict,
        }

        expected = type_mapping.get(expected_type.lower())
        if expected is None:
            return True

        return isinstance(value, expected)

    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """计算综合质量评分"""
        if not metrics:
            return 0.0

        # 加权平均
        total_weight = sum(m.weight for m in metrics)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(m.score * m.weight for m in metrics)
        base_score = weighted_sum / total_weight

        # 质量调整因子：低于阈值的指标会产生额外惩罚
        penalty = 0.0
        for metric in metrics:
            if metric.score < metric.threshold:
                deficit = metric.threshold - metric.score
                penalty += deficit * 0.2

        final_score = max(0.0, base_score - penalty)
        return min(1.0, final_score)

    def generate_quality_report(
        self,
        assessment: QualityAssessment,
    ) -> Dict[str, Any]:
        """
        生成质量评估报告

        Args:
            assessment: 质量评估结果

        Returns:
            详细的质量评估报告
        """
        report = {
            "overall_score": assessment.overall_score,
            "record_count": assessment.record_count,
            "assessment_time": assessment.assessment_time.isoformat(),
            "data_source": assessment.data_source,
            "metrics": {},
            "issues": [],
            "recommendations": [],
        }

        # 各指标详情
        for metric in assessment.metrics:
            metric_name = metric.metric_type
            report["metrics"][metric_name] = {
                "score": metric.score,
                "threshold": metric.threshold,
                "is_acceptable": metric.is_acceptable,
                "weight": metric.weight,
            }

            # 记录问题
            if not metric.is_acceptable:
                issue = {
                    "metric": metric_name,
                    "score": metric.score,
                    "threshold": metric.threshold,
                    "severity": "high" if metric.score < metric.threshold * 0.7 else "medium",
                }
                report["issues"].append(issue)

        # 生成建议
        report["recommendations"] = self._generate_recommendations(assessment)

        return report

    def _generate_recommendations(self, assessment: QualityAssessment) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for metric in assessment.metrics:
            if not metric.is_acceptable:
                metric_name = metric.metric_type

                if metric_name == QualityMetricType.COMPLETENESS:
                    recommendations.append("建议检查缺失值并采用填充或删除策略")
                elif metric_name == QualityMetricType.ACCURACY:
                    recommendations.append("建议完善验证规则并修正不符合的数据")
                elif metric_name == QualityMetricType.CONSISTENCY:
                    recommendations.append("建议标准化数据格式，确保一致性")
                elif metric_name == QualityMetricType.TIMELINESS:
                    recommendations.append("建议更新过期数据或设置数据刷新机制")
                elif metric_name == QualityMetricType.VALIDITY:
                    recommendations.append("建议清洗无效数据，修正异常值")
                elif metric_name == QualityMetricType.UNIQUENSS:
                    recommendations.append("建议去重处理，删除或标记重复数据")
                elif metric_name == QualityMetricType.RELEVANCE:
                    recommendations.append("建议增加信息密度，补充关键字段")

        return recommendations


class DataMassEnergyCalculator:
    """
    数据质能计算器

    计算数据的"质量"与"能量"概念：
    - 数据质量：数据量的大小、记录数、字段数等
    - 数据能量：信息的价值、活跃度、传播力等
    """

    def __init__(
        self,
        quality_factor_threshold: float = 0.7,
        energy_decay_days: int = 365,
    ):
        """
        初始化质能计算器

        Args:
            quality_factor_threshold: 质量因子阈值
            energy_decay_days: 能量衰减周期
        """
        self.quality_factor_threshold = quality_factor_threshold
        self.energy_decay_days = energy_decay_days

    def calculate(
        self,
        df: pd.DataFrame,
        assessment: Optional[QualityAssessment] = None,
        time_field: Optional[str] = None,
    ) -> DataMassEnergy:
        """
        计算数据质能

        Args:
            df: 数据DataFrame
            assessment: 质量评估结果（可选）
            time_field: 时间字段名（可选）

        Returns:
            数据质能模型
        """
        # 数据质量：基于记录数和字段数
        data_mass = len(df) * len(df.columns) / 1000.0  # 以千为单位

        # 质量因子：基于质量评估结果
        if assessment:
            quality_factor = assessment.overall_score
        else:
            quality_factor = 1.0

        # 数据能量：基于活跃度和信息价值
        data_energy = self._calculate_energy(df, time_field)

        # 数据密度：信息密度
        density = self._calculate_density(df)

        # 数据熵：不确定性度量
        entropy = self._calculate_entropy(df)

        return DataMassEnergy(
            data_mass=data_mass,
            data_energy=data_energy,
            quality_factor=quality_factor,
            density=density,
            entropy=entropy,
        )

    def _calculate_energy(
        self,
        df: pd.DataFrame,
        time_field: Optional[str] = None,
    ) -> float:
        """计算数据能量"""
        if len(df) == 0:
            return 0.0

        # 基础能量：信息量
        info_energy = len(df) * len(df.columns) * 0.01

        # 活跃度能量：基于时间新鲜度
        activity_energy = 0.0
        if time_field and time_field in df.columns:
            try:
                time_values = pd.to_datetime(df[time_field], errors='coerce').dropna()
                if len(time_values) > 0:
                    now = datetime.now()
                    recent_count = sum(1 for t in time_values if (now - t).days <= 30)
                    activity_energy = recent_count * 0.5
            except Exception:
                pass

        # 价值能量：基于信息熵（高质量信息有更高能量）
        value_energy = self._calculate_information_value(df)

        return info_energy + activity_energy + value_energy

    def _calculate_density(self, df: pd.DataFrame) -> float:
        """计算数据密度"""
        if len(df) == 0:
            return 0.0

        # 非空值密度
        non_null_ratio = df.notna().sum().sum() / (len(df) * len(df.columns))

        # 信息密度：基于唯一值比例
        unique_ratios = []
        for col in df.columns:
            unique_ratio = df[col].nunique() / len(df)
            unique_ratios.append(unique_ratio)

        avg_unique_ratio = sum(unique_ratios) / len(unique_ratios) if unique_ratios else 0.0

        # 综合密度
        density = (non_null_ratio * 0.5 + avg_unique_ratio * 0.5) * 100

        return density

    def _calculate_entropy(self, df: pd.DataFrame) -> float:
        """计算数据熵"""
        if len(df) == 0:
            return 0.0

        entropies = []

        for col in df.columns:
            non_null_values = df[col].dropna()
            if len(non_null_values) == 0:
                continue

            # 计算字段熵
            if df[col].dtype == 'object':
                # 分类变量熵
                value_counts = non_null_values.value_counts(normalize=True)
                entropy = -sum(p * np.log2(p + 1e-10) for p in value_counts)
            else:
                # 数值变量熵（基于分桶）
                try:
                    bins = min(20, len(non_null_values.unique()))
                    hist, _ = np.histogram(non_null_values, bins=bins)
                    hist_norm = hist / hist.sum()
                    entropy = -sum(p * np.log2(p + 1e-10) for p in hist_norm if p > 0)
                except Exception:
                    entropy = 0.0

            entropies.append(entropy)

        return sum(entropies) / len(entropies) if entropies else 0.0

    def _calculate_information_value(self, df: pd.DataFrame) -> float:
        """计算信息价值"""
        if len(df) == 0:
            return 0.0

        # 基于信息密度和质量
        density = self._calculate_density(df)
        entropy = self._calculate_entropy(df)

        # 信息价值 = 密度 * 熵值贡献
        value = density * 0.01 * (entropy / 10.0 if entropy > 0 else 0.5)

        return value


class QualityDimensionAnalyzer:
    """质量维度分析器"""

    @staticmethod
    def analyze_quality_trend(
        assessments: List[QualityAssessment],
    ) -> Dict[str, Any]:
        """
        分析质量趋势

        Args:
            assessments: 时间序列质量评估结果列表

        Returns:
            质量趋势分析结果
        """
        if len(assessments) < 2:
            return {"trend": "insufficient_data"}

        scores = [a.overall_score for a in assessments]
        times = [a.assessment_time for a in assessments]

        # 计算趋势方向
        if scores[-1] > scores[0]:
            trend = "improving"
        elif scores[-1] < scores[0]:
            trend = "declining"
        else:
            trend = "stable"

        # 计算变化率
        change_rate = (scores[-1] - scores[0]) / len(scores) if len(scores) > 0 else 0.0

        # 识别异常波动
        avg_score = sum(scores) / len(scores)
        std_score = np.std(scores)
        anomalies = [i for i, s in enumerate(scores) if abs(s - avg_score) > 2 * std_score]

        return {
            "trend": trend,
            "change_rate": change_rate,
            "average_score": avg_score,
            "std_score": std_score,
            "anomaly_indices": anomalies,
            "score_series": scores,
        }

    @staticmethod
    def compare_quality_by_dimension(
        df: pd.DataFrame,
        classifier: Any,  # DimensionClassifier
    ) -> Dict[str, Dict[str, float]]:
        """
        按维度比较数据质量

        Args:
            df: 数据DataFrame
            classifier: 维度分类器

        Returns:
            各维度的质量评估结果
        """
        # 对DataFrame进行维度分类
        classification_results = classifier.classify_dataframe(df)

        # 按维度分组字段
        dimension_fields: Dict[DimensionType, List[str]] = {}
        for field_name, result in classification_results.items():
            dim = result.dimension_type
            if dim not in dimension_fields:
                dimension_fields[dim] = []
            dimension_fields[dim].append(field_name)

        # 对每个维度进行质量评估
        assessor = QualityAssessor()
        dimension_quality: Dict[str, Dict[str, float]] = {}

        for dim_type, fields in dimension_fields.items():
            if not fields:
                continue

            dim_df = df[fields]
            assessment = assessor.assess_dataframe(dim_df)

            dimension_quality[dim_type.value] = {
                "overall_score": assessment.overall_score,
                "field_count": len(fields),
                "completeness": assessment.get_metric(QualityMetricType.COMPLETENESS).score
                    if assessment.get_metric(QualityMetricType.COMPLETENESS) else 0.0,
                "validity": assessment.get_metric(QualityMetricType.VALIDITY).score
                    if assessment.get_metric(QualityMetricType.VALIDITY) else 0.0,
            }

        return dimension_quality