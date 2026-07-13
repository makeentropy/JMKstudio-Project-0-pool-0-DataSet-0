"""
熵数据审查模块

基于信息熵的数据审查建模和生成。核心功能：
- 熵数据审查：基于信息熵的全面数据质量审查
- 熵异常检测：识别熵值异常的字段和记录
- 熵演变分析：追踪数据熵的时间演变轨迹
- 熵报告生成：生成详细的熵审查报告
- 熵驱动的数据质量评估：将熵作为核心评估指标
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ai_llm_agent_crawler.dimension.models import (
    DataMassEnergy,
    DimensionType,
    QualityAssessment,
    SingularityDetectionResult,
)
from ai_llm_agent_crawler.dimension.dimension_quantizer import DimensionQuantizer
from ai_llm_agent_crawler.dimension.yin_yang_model import YinYangModel
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EntropyAuditResult:
    """熵审查结果"""
    overall_entropy: float = 0.0
    entropy_level: str = "normal"
    entropy_score: float = 0.0
    anomaly_fields: List[str] = field(default_factory=list)
    high_entropy_fields: List[str] = field(default_factory=list)
    low_entropy_fields: List[str] = field(default_factory=list)
    field_entropies: Dict[str, float] = field(default_factory=dict)
    record_entropies: Dict[int, float] = field(default_factory=dict)
    entropy_distribution: Dict[str, int] = field(default_factory=dict)
    quality_score: float = 0.0
    risk_level: str = "low"
    recommendations: List[str] = field(default_factory=list)
    audited_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_entropy": self.overall_entropy,
            "entropy_level": self.entropy_level,
            "entropy_score": self.entropy_score,
            "anomaly_fields": self.anomaly_fields,
            "high_entropy_fields": self.high_entropy_fields,
            "low_entropy_fields": self.low_entropy_fields,
            "field_entropies": self.field_entropies,
            "record_entropies": {str(k): v for k, v in self.record_entropies.items()},
            "entropy_distribution": self.entropy_distribution,
            "quality_score": self.quality_score,
            "risk_level": self.risk_level,
            "recommendations": self.recommendations,
            "audited_at": self.audited_at.isoformat(),
        }


@dataclass
class EntropyAnomaly:
    """熵异常记录"""
    field_name: str
    anomaly_type: str  # high_entropy, low_entropy, entropy_spike, entropy_drop
    entropy_value: float
    threshold: float
    deviation: float
    severity: str = "medium"
    affected_records: int = 0
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "field_name": self.field_name,
            "anomaly_type": self.anomaly_type,
            "entropy_value": self.entropy_value,
            "threshold": self.threshold,
            "deviation": self.deviation,
            "severity": self.severity,
            "affected_records": self.affected_records,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class EntropyEvolutionPoint:
    """熵演变点"""
    timestamp: datetime
    entropy_value: float
    entropy_score: float
    quality_score: float
    anomaly_count: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "entropy_value": self.entropy_value,
            "entropy_score": self.entropy_score,
            "quality_score": self.quality_score,
            "anomaly_count": self.anomaly_count,
        }


@dataclass
class EntropyAuditConfig:
    """熵审查配置"""
    entropy_threshold_low: float = 1.0
    entropy_threshold_high: float = 7.0
    anomaly_deviation_threshold: float = 2.0
    high_entropy_threshold: float = 6.0
    low_entropy_threshold: float = 2.0
    record_sample_size: int = 100
    enable_record_analysis: bool = True
    enable_field_analysis: bool = True
    enable_evolution_tracking: bool = True


class EntropyAuditor:
    """
    熵数据审查器

    基于信息熵的数据质量审查：
    - 字段级熵分析：评估每个字段的信息熵
    - 记录级熵分析：评估每条记录的熵值
    - 异常检测：识别熵值异常的字段和记录
    - 质量评分：基于熵的综合质量评估
    - 报告生成：生成详细的审查报告
    """

    def __init__(
        self,
        config: Optional[EntropyAuditConfig] = None,
        quantizer: Optional[DimensionQuantizer] = None,
    ):
        """
        初始化熵数据审查器

        Args:
            config: 审查配置
            quantizer: 维度量化器
        """
        self.config = config or EntropyAuditConfig()
        self.quantizer = quantizer or DimensionQuantizer()

        self.evolution_history: List[EntropyEvolutionPoint] = []
        self.anomaly_history: List[EntropyAnomaly] = []

        logger.info(f"熵数据审查器初始化完成")

    def audit(
        self,
        df: pd.DataFrame,
        mass_energy: Optional[DataMassEnergy] = None,
        assessment: Optional[QualityAssessment] = None,
    ) -> EntropyAuditResult:
        """
        执行熵数据审查

        Args:
            df: 数据DataFrame
            mass_energy: 数据质能模型
            assessment: 质量评估结果

        Returns:
            审查结果
        """
        if len(df) == 0:
            return EntropyAuditResult(
                recommendations=["空数据集，无法进行熵审查"],
            )

        field_entropies = self._calculate_field_entropies(df)
        overall_entropy = self._calculate_overall_entropy(field_entropies)
        entropy_level = self._determine_entropy_level(overall_entropy)
        entropy_score = self._calculate_entropy_score(overall_entropy)

        high_entropy_fields = self._identify_high_entropy_fields(field_entropies)
        low_entropy_fields = self._identify_low_entropy_fields(field_entropies)
        anomalies = self._detect_entropy_anomalies(df, field_entropies)

        record_entropies = {}
        if self.config.enable_record_analysis:
            record_entropies = self._calculate_record_entropies(df)

        entropy_distribution = self._calculate_entropy_distribution(field_entropies)
        quality_score = self._calculate_quality_score(
            entropy_score, field_entropies, assessment
        )
        risk_level = self._determine_risk_level(quality_score, len(anomalies))

        recommendations = self._generate_recommendations(
            overall_entropy,
            entropy_level,
            high_entropy_fields,
            low_entropy_fields,
            anomalies,
            risk_level,
        )

        result = EntropyAuditResult(
            overall_entropy=overall_entropy,
            entropy_level=entropy_level,
            entropy_score=entropy_score,
            anomaly_fields=[a.field_name for a in anomalies],
            high_entropy_fields=high_entropy_fields,
            low_entropy_fields=low_entropy_fields,
            field_entropies=field_entropies,
            record_entropies=record_entropies,
            entropy_distribution=entropy_distribution,
            quality_score=quality_score,
            risk_level=risk_level,
            recommendations=recommendations,
        )

        self._record_evolution(result, mass_energy)
        self._record_anomalies(anomalies)

        logger.info(
            f"熵审查完成: entropy={overall_entropy:.4f}, level={entropy_level}, "
            f"quality={quality_score:.4f}, risk={risk_level}"
        )

        return result

    def generate_audit_report(
        self,
        result: EntropyAuditResult,
        df: Optional[pd.DataFrame] = None,
        mass_energy: Optional[DataMassEnergy] = None,
    ) -> Dict[str, Any]:
        """
        生成审查报告

        Args:
            result: 审查结果
            df: 数据DataFrame（可选）
            mass_energy: 数据质能模型（可选）

        Returns:
            详细的审查报告
        """
        report = {
            "audit_result": result.to_dict(),
            "entropy_analysis": self._analyze_entropy_profile(result),
            "field_analysis": self._analyze_fields(result),
            "risk_analysis": self._analyze_risk(result),
            "evolution_summary": self._get_evolution_summary(),
        }

        if df is not None:
            report["data_summary"] = {
                "record_count": len(df),
                "field_count": len(df.columns),
                "numeric_fields": len(df.select_dtypes(include=[np.number]).columns),
                "text_fields": len(df.select_dtypes(include=['object']).columns),
                "null_ratio": df.isna().sum().sum() / (len(df) * len(df.columns)),
            }

        if mass_energy:
            report["mass_energy"] = {
                "data_mass": mass_energy.data_mass,
                "data_energy": mass_energy.data_energy,
                "mass_energy_ratio": mass_energy.mass_energy_ratio,
                "density": mass_energy.density,
                "entropy": mass_energy.entropy,
                "singularity_risk": mass_energy.calculate_singularity_risk(),
            }

        return report

    def analyze_entropy_evolution(
        self,
        df_sequence: List[pd.DataFrame],
        timestamps: Optional[List[datetime]] = None,
    ) -> Dict[str, Any]:
        """
        分析熵演变轨迹

        Args:
            df_sequence: 数据序列
            timestamps: 时间戳序列

        Returns:
            演变分析结果
        """
        if len(df_sequence) < 2:
            return {"error": "需要至少两个时间点的数据"}

        evolution_points = []
        for i, df in enumerate(df_sequence):
            result = self.audit(df)
            timestamp = timestamps[i] if timestamps else datetime.now()
            evolution_points.append(EntropyEvolutionPoint(
                timestamp=timestamp,
                entropy_value=result.overall_entropy,
                entropy_score=result.entropy_score,
                quality_score=result.quality_score,
                anomaly_count=len(result.anomaly_fields),
            ))

        trend = self._analyze_entropy_trend(evolution_points)
        anomalies = self._detect_evolution_anomalies(evolution_points)

        return {
            "evolution_points": [p.to_dict() for p in evolution_points],
            "trend": trend,
            "anomalies": anomalies,
            "summary": {
                "min_entropy": min(p.entropy_value for p in evolution_points),
                "max_entropy": max(p.entropy_value for p in evolution_points),
                "avg_entropy": sum(p.entropy_value for p in evolution_points) / len(evolution_points),
                "total_anomalies": sum(p.anomaly_count for p in evolution_points),
            },
        }

    def _calculate_field_entropies(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算各字段的熵值"""
        entropies = {}

        for col in df.columns:
            non_null_values = df[col].dropna()
            if len(non_null_values) == 0:
                entropies[col] = 0.0
                continue

            try:
                if df[col].dtype == 'object':
                    value_counts = non_null_values.value_counts(normalize=True)
                    entropy = -sum(p * np.log2(p + 1e-10) for p in value_counts)
                else:
                    bins = min(20, len(non_null_values.unique()))
                    hist, _ = np.histogram(non_null_values, bins=bins)
                    hist_norm = hist / hist.sum()
                    entropy = -sum(p * np.log2(p + 1e-10) for p in hist_norm if p > 0)

                entropies[col] = entropy
            except Exception as e:
                logger.warning(f"计算字段 '{col}' 熵值失败: {e}")
                entropies[col] = 0.0

        return entropies

    def _calculate_overall_entropy(self, field_entropies: Dict[str, float]) -> float:
        """计算整体熵值"""
        if not field_entropies:
            return 0.0

        return sum(field_entropies.values()) / len(field_entropies)

    def _determine_entropy_level(self, entropy: float) -> str:
        """确定熵级别"""
        if entropy < self.config.low_entropy_threshold:
            return "low"
        elif entropy < self.config.high_entropy_threshold:
            return "normal"
        else:
            return "high"

    def _calculate_entropy_score(self, entropy: float) -> float:
        """计算熵分数（归一化）"""
        if entropy < self.config.low_entropy_threshold:
            return min(entropy / self.config.low_entropy_threshold, 1.0)
        elif entropy > self.config.high_entropy_threshold:
            return max(1.0 - (entropy - self.config.high_entropy_threshold) / 5.0, 0.0)
        else:
            return 1.0

    def _identify_high_entropy_fields(
        self,
        field_entropies: Dict[str, float],
    ) -> List[str]:
        """识别高熵字段"""
        return [
            field for field, entropy in field_entropies.items()
            if entropy > self.config.high_entropy_threshold
        ]

    def _identify_low_entropy_fields(
        self,
        field_entropies: Dict[str, float],
    ) -> List[str]:
        """识别低熵字段"""
        return [
            field for field, entropy in field_entropies.items()
            if entropy < self.config.low_entropy_threshold
        ]

    def _detect_entropy_anomalies(
        self,
        df: pd.DataFrame,
        field_entropies: Dict[str, float],
    ) -> List[EntropyAnomaly]:
        """检测熵异常"""
        anomalies = []
        entropies = list(field_entropies.values())

        if len(entropies) < 3:
            return anomalies

        mean_entropy = np.mean(entropies)
        std_entropy = np.std(entropies)

        for field_name, entropy in field_entropies.items():
            deviation = abs(entropy - mean_entropy) / std_entropy if std_entropy > 0 else 0

            if deviation > self.config.anomaly_deviation_threshold:
                anomaly_type = "high_entropy" if entropy > mean_entropy else "low_entropy"
                severity = "high" if deviation > self.config.anomaly_deviation_threshold * 1.5 else "medium"

                anomalies.append(EntropyAnomaly(
                    field_name=field_name,
                    anomaly_type=anomaly_type,
                    entropy_value=entropy,
                    threshold=mean_entropy + self.config.anomaly_deviation_threshold * std_entropy,
                    deviation=deviation,
                    severity=severity,
                    affected_records=len(df),
                ))

        return anomalies

    def _calculate_record_entropies(self, df: pd.DataFrame) -> Dict[int, float]:
        """计算记录级熵值"""
        record_entropies = {}
        sample_size = min(self.config.record_sample_size, len(df))
        sample_indices = np.random.choice(len(df), sample_size, replace=False)

        for idx in sample_indices:
            record = df.iloc[idx]
            entropy = self._calculate_single_record_entropy(record)
            record_entropies[int(idx)] = entropy

        return record_entropies

    def _calculate_single_record_entropy(self, record: pd.Series) -> float:
        """计算单条记录的熵值"""
        non_null_values = record.dropna()
        if len(non_null_values) == 0:
            return 0.0

        type_counts = {}
        for val in non_null_values:
            val_type = type(val).__name__
            type_counts[val_type] = type_counts.get(val_type, 0) + 1

        total = len(non_null_values)
        entropy = 0.0
        for count in type_counts.values():
            p = count / total
            entropy -= p * np.log2(p + 1e-10)

        return entropy

    def _calculate_entropy_distribution(
        self,
        field_entropies: Dict[str, float],
    ) -> Dict[str, int]:
        """计算熵值分布"""
        distribution = {
            "very_low": 0,
            "low": 0,
            "normal": 0,
            "high": 0,
            "very_high": 0,
        }

        for entropy in field_entropies.values():
            if entropy < 1.0:
                distribution["very_low"] += 1
            elif entropy < 3.0:
                distribution["low"] += 1
            elif entropy < 5.0:
                distribution["normal"] += 1
            elif entropy < 7.0:
                distribution["high"] += 1
            else:
                distribution["very_high"] += 1

        return distribution

    def _calculate_quality_score(
        self,
        entropy_score: float,
        field_entropies: Dict[str, float],
        assessment: Optional[QualityAssessment],
    ) -> float:
        """计算综合质量评分"""
        scores = [entropy_score]

        if assessment:
            for metric in assessment.metrics:
                scores.append(metric.score)

        high_entropy_ratio = sum(
            1 for e in field_entropies.values()
            if e > self.config.high_entropy_threshold
        ) / len(field_entropies) if field_entropies else 0
        scores.append(max(0.0, 1.0 - high_entropy_ratio))

        low_entropy_ratio = sum(
            1 for e in field_entropies.values()
            if e < self.config.low_entropy_threshold
        ) / len(field_entropies) if field_entropies else 0
        scores.append(max(0.0, 1.0 - low_entropy_ratio))

        return sum(scores) / len(scores)

    def _determine_risk_level(self, quality_score: float, anomaly_count: int) -> str:
        """确定风险级别"""
        if quality_score < 0.5 or anomaly_count >= 5:
            return "high"
        elif quality_score < 0.7 or anomaly_count >= 3:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        overall_entropy: float,
        entropy_level: str,
        high_entropy_fields: List[str],
        low_entropy_fields: List[str],
        anomalies: List[EntropyAnomaly],
        risk_level: str,
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if risk_level == "high":
            recommendations.append("高风险警告：数据存在严重质量问题，需要立即处理")

        if entropy_level == "high":
            recommendations.append(
                f"高熵状态：整体熵值({overall_entropy:.2f})偏高，数据变化剧烈"
            )
            recommendations.append("建议检查异常数据，进行数据清洗和标准化")

        elif entropy_level == "low":
            recommendations.append(
                f"低熵状态：整体熵值({overall_entropy:.2f})偏低，数据多样性不足"
            )
            recommendations.append("建议增加数据多样性，丰富信息内容")

        if high_entropy_fields:
            recommendations.append(
                f"发现 {len(high_entropy_fields)} 个高熵字段：{', '.join(high_entropy_fields)}"
            )
            recommendations.append("建议分析这些字段的异常值和数据分布")

        if low_entropy_fields:
            recommendations.append(
                f"发现 {len(low_entropy_fields)} 个低熵字段：{', '.join(low_entropy_fields)}"
            )
            recommendations.append("建议增加这些字段的数据多样性")

        if anomalies:
            high_severity = [a for a in anomalies if a.severity == "high"]
            if high_severity:
                recommendations.append(
                    f"发现 {len(high_severity)} 个严重级别熵异常，需要优先处理"
                )

        return recommendations

    def _record_evolution(
        self,
        result: EntropyAuditResult,
        mass_energy: Optional[DataMassEnergy],
    ) -> None:
        """记录熵演变"""
        if not self.config.enable_evolution_tracking:
            return

        point = EntropyEvolutionPoint(
            timestamp=datetime.now(),
            entropy_value=result.overall_entropy,
            entropy_score=result.entropy_score,
            quality_score=result.quality_score,
            anomaly_count=len(result.anomaly_fields),
        )

        self.evolution_history.append(point)

        max_history = 100
        if len(self.evolution_history) > max_history:
            self.evolution_history = self.evolution_history[-max_history:]

    def _record_anomalies(self, anomalies: List[EntropyAnomaly]) -> None:
        """记录异常"""
        self.anomaly_history.extend(anomalies)

        max_history = 200
        if len(self.anomaly_history) > max_history:
            self.anomaly_history = self.anomaly_history[-max_history:]

    def _analyze_entropy_profile(self, result: EntropyAuditResult) -> Dict[str, Any]:
        """分析熵特征"""
        return {
            "overall_entropy": result.overall_entropy,
            "entropy_level": result.entropy_level,
            "entropy_score": result.entropy_score,
            "interpretation": self._interpret_entropy_level(result.entropy_level),
            "distribution": result.entropy_distribution,
        }

    def _interpret_entropy_level(self, level: str) -> str:
        """解释熵级别"""
        interpretations = {
            "low": "低熵：数据变化小，可能存在冗余或信息不足",
            "normal": "正常熵：数据变化适中，信息丰富度良好",
            "high": "高熵：数据变化剧烈，可能存在异常或噪声",
        }
        return interpretations.get(level, "未知")

    def _analyze_fields(self, result: EntropyAuditResult) -> Dict[str, Any]:
        """分析字段熵"""
        field_details = {}
        for field_name, entropy in result.field_entropies.items():
            field_details[field_name] = {
                "entropy": entropy,
                "is_high_entropy": field_name in result.high_entropy_fields,
                "is_low_entropy": field_name in result.low_entropy_fields,
                "is_anomaly": field_name in result.anomaly_fields,
            }

        return {
            "field_count": len(result.field_entropies),
            "high_entropy_count": len(result.high_entropy_fields),
            "low_entropy_count": len(result.low_entropy_fields),
            "anomaly_count": len(result.anomaly_fields),
            "fields": field_details,
        }

    def _analyze_risk(self, result: EntropyAuditResult) -> Dict[str, Any]:
        """分析风险"""
        risk_details = {
            "low": {
                "description": "低风险：数据质量良好，无明显异常",
                "action": "持续监控",
            },
            "medium": {
                "description": "中风险：数据存在一些问题，需要关注",
                "action": "定期检查，及时处理异常",
            },
            "high": {
                "description": "高风险：数据存在严重问题，需要立即处理",
                "action": "立即进行数据清洗和质量修复",
            },
        }

        return {
            "risk_level": result.risk_level,
            "quality_score": result.quality_score,
            **risk_details.get(result.risk_level, {}),
        }

    def _get_evolution_summary(self) -> Dict[str, Any]:
        """获取演变摘要"""
        if not self.evolution_history:
            return {"message": "No evolution history"}

        recent_points = self.evolution_history[-10:]
        avg_entropy = sum(p.entropy_value for p in recent_points) / len(recent_points)
        avg_quality = sum(p.quality_score for p in recent_points) / len(recent_points)

        return {
            "history_length": len(self.evolution_history),
            "recent_avg_entropy": avg_entropy,
            "recent_avg_quality": avg_quality,
            "total_anomalies": len(self.anomaly_history),
        }

    def _analyze_entropy_trend(
        self,
        points: List[EntropyEvolutionPoint],
    ) -> Dict[str, Any]:
        """分析熵演变趋势"""
        entropies = [p.entropy_value for p in points]
        qualities = [p.quality_score for p in points]

        entropy_trend = "stable"
        if entropies[-1] > entropies[0] + 1.0:
            entropy_trend = "increasing"
        elif entropies[-1] < entropies[0] - 1.0:
            entropy_trend = "decreasing"

        quality_trend = "stable"
        if qualities[-1] > qualities[0] + 0.1:
            quality_trend = "improving"
        elif qualities[-1] < qualities[0] - 0.1:
            quality_trend = "declining"

        return {
            "entropy_trend": entropy_trend,
            "quality_trend": quality_trend,
            "entropy_change": entropies[-1] - entropies[0],
            "quality_change": qualities[-1] - qualities[0],
        }

    def _detect_evolution_anomalies(
        self,
        points: List[EntropyEvolutionPoint],
    ) -> List[Dict[str, Any]]:
        """检测演变异常"""
        anomalies = []
        entropies = [p.entropy_value for p in points]

        if len(entropies) < 3:
            return anomalies

        mean_entropy = np.mean(entropies)
        std_entropy = np.std(entropies)

        for i, point in enumerate(points):
            if abs(point.entropy_value - mean_entropy) > 2 * std_entropy:
                anomalies.append({
                    "index": i,
                    "timestamp": point.timestamp.isoformat(),
                    "entropy_value": point.entropy_value,
                    "anomaly_type": "entropy_spike" if point.entropy_value > mean_entropy else "entropy_drop",
                    "deviation": abs(point.entropy_value - mean_entropy) / std_entropy,
                })

        return anomalies


class EntropyDrivenQualityAssessor:
    """
    熵驱动的质量评估器

    将熵作为核心评估指标，结合传统质量指标进行综合评估。
    """

    def __init__(self, auditor: Optional[EntropyAuditor] = None):
        """
        初始化熵驱动的质量评估器

        Args:
            auditor: 熵审查器实例
        """
        self.auditor = auditor or EntropyAuditor()

    def assess(
        self,
        df: pd.DataFrame,
        mass_energy: Optional[DataMassEnergy] = None,
        assessment: Optional[QualityAssessment] = None,
    ) -> Dict[str, Any]:
        """
        执行熵驱动的质量评估

        Args:
            df: 数据DataFrame
            mass_energy: 数据质能模型
            assessment: 传统质量评估结果

        Returns:
            综合评估结果
        """
        audit_result = self.auditor.audit(df, mass_energy, assessment)

        entropy_weight = 0.4
        traditional_weight = 0.6

        entropy_score = audit_result.entropy_score

        traditional_score = 0.5
        if assessment:
            if assessment.metrics:
                traditional_score = assessment.calculate_weighted_score()
            else:
                traditional_score = assessment.overall_score

        combined_score = (
            entropy_score * entropy_weight
            + traditional_score * traditional_weight
        )

        return {
            "combined_score": combined_score,
            "entropy_score": entropy_score,
            "traditional_score": traditional_score,
            "entropy_weight": entropy_weight,
            "traditional_weight": traditional_weight,
            "audit_result": audit_result.to_dict(),
            "quality_level": self._determine_quality_level(combined_score),
            "interpretation": self._interpret_combined_score(combined_score),
        }

    def _determine_quality_level(self, score: float) -> str:
        """确定质量级别"""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "critical"

    def _interpret_combined_score(self, score: float) -> str:
        """解释综合评分"""
        if score >= 0.8:
            return "高质量：数据质量优秀，熵值适中，信息丰富度良好"
        elif score >= 0.6:
            return "中等质量：数据基本可用，但存在一些改进空间"
        elif score >= 0.4:
            return "低质量：数据存在较多问题，需要进行清洗和优化"
        else:
            return "严重质量问题：数据质量极差，需要立即处理"