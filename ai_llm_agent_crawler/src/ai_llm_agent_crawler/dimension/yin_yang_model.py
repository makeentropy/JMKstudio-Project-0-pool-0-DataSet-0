"""
两仪模型模块

基于维度空间质能质量子奇点的熵发生生成两仪（阴阳二元）模型。
核心概念：
- 阴（Yin）：代表数据的静态、稳定、低熵、低能量状态
- 阳（Yang）：代表数据的动态、变化、高熵、高能量状态
- 两仪生成：从奇点状态生成阴阳二元对立统一的模型
- 熵发生：熵的变化驱动阴阳状态的转换和演化
"""

import math
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
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class YinYangState:
    """阴阳状态"""
    yin_score: float = 0.0
    yang_score: float = 0.0
    balance: float = 0.0
    entropy: float = 0.0
    mass_energy_ratio: float = 0.0
    singularity_risk: float = 0.0
    transition_probability: float = 0.0
    state_label: str = "balanced"
    state_at: datetime = field(default_factory=datetime.now)

    @property
    def total_score(self) -> float:
        """阴阳总分"""
        return self.yin_score + self.yang_score

    @property
    def dominance(self) -> str:
        """主导状态"""
        if self.yang_score > self.yin_score + 0.1:
            return "yang"
        elif self.yin_score > self.yang_score + 0.1:
            return "yin"
        else:
            return "balanced"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "yin_score": self.yin_score,
            "yang_score": self.yang_score,
            "balance": self.balance,
            "entropy": self.entropy,
            "mass_energy_ratio": self.mass_energy_ratio,
            "singularity_risk": self.singularity_risk,
            "transition_probability": self.transition_probability,
            "state_label": self.state_label,
            "dominance": self.dominance,
            "state_at": self.state_at.isoformat(),
        }


@dataclass
class YinYangTransition:
    """阴阳转换记录"""
    from_state: str
    to_state: str
    transition_probability: float
    entropy_change: float
    mass_energy_change: float
    trigger_type: str = "normal"
    transition_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "transition_probability": self.transition_probability,
            "entropy_change": self.entropy_change,
            "mass_energy_change": self.mass_energy_change,
            "trigger_type": self.trigger_type,
            "transition_at": self.transition_at.isoformat(),
        }


@dataclass
class YinYangConfig:
    """两仪模型配置"""
    balance_threshold: float = 0.1
    entropy_threshold_low: float = 2.0
    entropy_threshold_high: float = 6.0
    mass_energy_ratio_low: float = 0.5
    mass_energy_ratio_high: float = 2.0
    singularity_threshold: float = 0.7
    transition_sensitivity: float = 0.3
    history_window: int = 10


class YinYangModel:
    """
    两仪模型

    基于维度空间质能质量子奇点的熵发生生成阴阳二元模型：
    - 阴维度：完整性、一致性、稳定性、低熵特征
    - 阳维度：多样性、变化性、活跃度、高熵特征
    - 奇点发生：熵的突变触发阴阳转换
    - 两仪平衡：阴阳对立统一的动态平衡
    """

    YIN_DIMENSIONS = {
        DimensionType.QUALITY,
        DimensionType.STRUCTURAL,
        DimensionType.RELATIONAL,
    }

    YANG_DIMENSIONS = {
        DimensionType.STATISTICAL,
        DimensionType.CONTENT,
        DimensionType.SEMANTIC,
        DimensionType.TEMPORAL,
    }

    STATE_LABELS = {
        "yin_dominant": "阴盛",
        "yang_dominant": "阳盛",
        "balanced": "平衡",
        "singularity": "奇点",
        "transition": "转换中",
    }

    def __init__(
        self,
        config: Optional[YinYangConfig] = None,
        quantizer: Optional[DimensionQuantizer] = None,
    ):
        """
        初始化两仪模型

        Args:
            config: 两仪模型配置
            quantizer: 维度量化器
        """
        self.config = config or YinYangConfig()
        self.quantizer = quantizer or DimensionQuantizer()

        self.state_history: List[YinYangState] = []
        self.transition_history: List[YinYangTransition] = []

        logger.info(f"两仪模型初始化完成")

    def generate_yin_yang(
        self,
        df: pd.DataFrame,
        mass_energy: Optional[DataMassEnergy] = None,
        assessment: Optional[QualityAssessment] = None,
        singularity_result: Optional[SingularityDetectionResult] = None,
    ) -> YinYangState:
        """
        生成两仪状态

        Args:
            df: 数据DataFrame
            mass_energy: 数据质能模型
            assessment: 质量评估结果
            singularity_result: 奇点检测结果

        Returns:
            阴阳状态
        """
        yin_score = self._calculate_yin_score(df, assessment)
        yang_score = self._calculate_yang_score(df, mass_energy)
        balance = self._calculate_balance(yin_score, yang_score)

        entropy = mass_energy.entropy if mass_energy else 0.0
        mass_energy_ratio = mass_energy.mass_energy_ratio if mass_energy else 1.0
        singularity_risk = (
            mass_energy.calculate_singularity_risk() if mass_energy else 0.0
        )

        transition_probability = self._calculate_transition_probability(
            yin_score, yang_score, entropy, singularity_risk
        )

        state_label = self._determine_state_label(
            balance, entropy, singularity_risk
        )

        state = YinYangState(
            yin_score=yin_score,
            yang_score=yang_score,
            balance=balance,
            entropy=entropy,
            mass_energy_ratio=mass_energy_ratio,
            singularity_risk=singularity_risk,
            transition_probability=transition_probability,
            state_label=state_label,
        )

        self._record_state(state)
        self._check_transition(state)

        logger.info(
            f"两仪状态生成: {state.state_label}, "
            f"yin={yin_score:.4f}, yang={yang_score:.4f}, "
            f"balance={balance:.4f}, entropy={entropy:.4f}"
        )

        return state

    def generate_from_quantization(
        self,
        quantization_results: Dict[str, Any],
    ) -> YinYangState:
        """
        从量化结果生成两仪状态

        Args:
            quantization_results: 维度量化结果

        Returns:
            阴阳状态
        """
        yin_score = 0.0
        yang_score = 0.0
        yin_count = 0
        yang_count = 0

        for field_name, result in quantization_results.items():
            dim_type = result.get("dimension_type", "")
            score = result.get("effective_score", 0.0)

            if dim_type in [d.value for d in self.YIN_DIMENSIONS]:
                yin_score += score
                yin_count += 1
            elif dim_type in [d.value for d in self.YANG_DIMENSIONS]:
                yang_score += score
                yang_count += 1

        yin_score = yin_score / yin_count if yin_count > 0 else 0.5
        yang_score = yang_score / yang_count if yang_count > 0 else 0.5

        entropy = sum(
            r.get("entropy", 0.0) for r in quantization_results.values()
        ) / len(quantization_results) if quantization_results else 0.0

        balance = self._calculate_balance(yin_score, yang_score)
        singularity_risk = min(entropy / 10.0, 1.0)
        transition_probability = self._calculate_transition_probability(
            yin_score, yang_score, entropy, singularity_risk
        )
        state_label = self._determine_state_label(balance, entropy, singularity_risk)

        state = YinYangState(
            yin_score=yin_score,
            yang_score=yang_score,
            balance=balance,
            entropy=entropy,
            singularity_risk=singularity_risk,
            transition_probability=transition_probability,
            state_label=state_label,
        )

        self._record_state(state)
        self._check_transition(state)

        return state

    def predict_transition(
        self,
        current_state: YinYangState,
        entropy_change: float = 0.0,
        mass_energy_change: float = 0.0,
    ) -> YinYangTransition:
        """
        预测阴阳转换

        Args:
            current_state: 当前状态
            entropy_change: 熵变化量
            mass_energy_change: 质能变化量

        Returns:
            预测的转换结果
        """
        new_entropy = current_state.entropy + entropy_change
        new_mass_energy_ratio = current_state.mass_energy_ratio + mass_energy_change

        new_yin, new_yang = self._calculate_transition_scores(
            current_state, new_entropy, new_mass_energy_ratio
        )

        new_balance = self._calculate_balance(new_yin, new_yang)
        new_singularity_risk = min(new_entropy / 10.0, 1.0)
        new_state_label = self._determine_state_label(
            new_balance, new_entropy, new_singularity_risk
        )

        transition = YinYangTransition(
            from_state=current_state.state_label,
            to_state=new_state_label,
            transition_probability=current_state.transition_probability,
            entropy_change=entropy_change,
            mass_energy_change=mass_energy_change,
            trigger_type="predicted",
        )

        return transition

    def generate_yin_yang_report(
        self,
        state: YinYangState,
        df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        生成两仪分析报告

        Args:
            state: 阴阳状态
            df: 数据DataFrame（可选）

        Returns:
            详细的分析报告
        """
        report = {
            "state": state.to_dict(),
            "interpretation": self._interpret_state(state),
            "dimensions": {
                "yin_dimensions": [d.value for d in self.YIN_DIMENSIONS],
                "yang_dimensions": [d.value for d in self.YANG_DIMENSIONS],
            },
            "entropy_analysis": self._analyze_entropy(state),
            "mass_energy_analysis": self._analyze_mass_energy(state),
            "singularity_analysis": self._analyze_singularity(state),
            "recommendations": self._generate_recommendations(state),
            "history_summary": self._get_history_summary(),
        }

        if df is not None:
            report["data_summary"] = {
                "record_count": len(df),
                "field_count": len(df.columns),
                "numeric_fields": len(df.select_dtypes(include=[np.number]).columns),
                "text_fields": len(df.select_dtypes(include=['object']).columns),
            }

        return report

    def _calculate_yin_score(
        self,
        df: pd.DataFrame,
        assessment: Optional[QualityAssessment] = None,
    ) -> float:
        """计算阴分数（稳定性、一致性、完整性）"""
        scores = []

        if assessment:
            for metric in assessment.metrics:
                metric_type = str(metric.metric_type)
                if metric_type in ["completeness", "consistency", "validity", "uniqueness"]:
                    scores.append(metric.score)

        non_null_ratio = df.notna().sum().sum() / (len(df) * len(df.columns))
        scores.append(non_null_ratio)

        duplicate_ratio = 1 - df.duplicated().sum() / len(df)
        scores.append(duplicate_ratio)

        for col in df.columns:
            if df[col].dtype == 'object':
                type_consistency = len(set(type(v).__name__ for v in df[col].dropna()))
                scores.append(1.0 if type_consistency <= 1 else 0.8)

        return sum(scores) / len(scores) if scores else 0.5

    def _calculate_yang_score(
        self,
        df: pd.DataFrame,
        mass_energy: Optional[DataMassEnergy] = None,
    ) -> float:
        """计算阳分数（多样性、变化性、活跃度）"""
        scores = []

        if mass_energy:
            scores.append(min(mass_energy.entropy / 10.0, 1.0))
            scores.append(min(mass_energy.density / 100.0, 1.0))

        for col in df.columns:
            unique_ratio = df[col].nunique() / len(df)
            scores.append(unique_ratio)

            if df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
                non_null_values = df[col].dropna()
                if len(non_null_values) > 1:
                    std = non_null_values.std()
                    mean = non_null_values.mean()
                    if abs(mean) > 0:
                        cv = std / abs(mean)
                        scores.append(min(cv, 1.0))

        text_cols = df.select_dtypes(include=['object']).columns
        if len(text_cols) > 0:
            avg_lengths = []
            for col in text_cols:
                avg_lengths.append(df[col].astype(str).str.len().mean())
            avg_length = np.mean(avg_lengths) if avg_lengths else 0
            scores.append(min(avg_length / 1000.0, 1.0))

        return sum(scores) / len(scores) if scores else 0.5

    def _calculate_balance(self, yin_score: float, yang_score: float) -> float:
        """计算阴阳平衡度"""
        if yin_score + yang_score == 0:
            return 0.0

        balance = (yang_score - yin_score) / (yin_score + yang_score)
        return max(-1.0, min(1.0, balance))

    def _calculate_transition_probability(
        self,
        yin_score: float,
        yang_score: float,
        entropy: float,
        singularity_risk: float,
    ) -> float:
        """计算状态转换概率"""
        balance_diff = abs(yin_score - yang_score)
        entropy_factor = min(entropy / 10.0, 1.0)

        probability = (
            balance_diff * 0.3
            + entropy_factor * 0.4
            + singularity_risk * 0.3
        )

        return min(1.0, probability)

    def _determine_state_label(
        self,
        balance: float,
        entropy: float,
        singularity_risk: float,
    ) -> str:
        """确定状态标签"""
        if singularity_risk >= self.config.singularity_threshold:
            return self.STATE_LABELS["singularity"]

        if balance > self.config.balance_threshold:
            return self.STATE_LABELS["yang_dominant"]
        elif balance < -self.config.balance_threshold:
            return self.STATE_LABELS["yin_dominant"]
        else:
            return self.STATE_LABELS["balanced"]

    def _calculate_transition_scores(
        self,
        current_state: YinYangState,
        new_entropy: float,
        new_mass_energy_ratio: float,
    ) -> Tuple[float, float]:
        """计算转换后的阴阳分数"""
        entropy_factor = new_entropy / 10.0
        ratio_factor = abs(new_mass_energy_ratio - 1.0)

        yang_change = entropy_factor * self.config.transition_sensitivity
        yin_change = (1 - entropy_factor) * self.config.transition_sensitivity

        new_yin = max(0.0, min(1.0, current_state.yin_score + yin_change - yang_change * 0.5))
        new_yang = max(0.0, min(1.0, current_state.yang_score + yang_change - yin_change * 0.5))

        return new_yin, new_yang

    def _record_state(self, state: YinYangState) -> None:
        """记录状态到历史"""
        self.state_history.append(state)

        if len(self.state_history) > self.config.history_window:
            self.state_history = self.state_history[-self.config.history_window:]

    def _check_transition(self, state: YinYangState) -> None:
        """检查是否发生状态转换"""
        if len(self.state_history) < 2:
            return

        previous_state = self.state_history[-2]

        if previous_state.state_label != state.state_label:
            transition = YinYangTransition(
                from_state=previous_state.state_label,
                to_state=state.state_label,
                transition_probability=state.transition_probability,
                entropy_change=state.entropy - previous_state.entropy,
                mass_energy_change=state.mass_energy_ratio - previous_state.mass_energy_ratio,
                trigger_type="observed",
            )

            self.transition_history.append(transition)

            logger.info(
                f"状态转换: {previous_state.state_label} -> {state.state_label}, "
                f"probability={state.transition_probability:.4f}"
            )

    def _interpret_state(self, state: YinYangState) -> str:
        """解释阴阳状态"""
        if state.state_label == self.STATE_LABELS["singularity"]:
            return f"奇点状态：数据存在严重质量问题，熵值({state.entropy:.2f})极高，质能失衡，需要立即处理"
        elif state.state_label == self.STATE_LABELS["yin_dominant"]:
            return f"阴盛状态：数据稳定性高但多样性不足，熵值({state.entropy:.2f})较低，可能缺乏信息丰富度"
        elif state.state_label == self.STATE_LABELS["yang_dominant"]:
            return f"阳盛状态：数据多样性高但稳定性不足，熵值({state.entropy:.2f})较高，可能存在异常波动"
        else:
            return f"平衡状态：阴阳协调，数据质量良好，状态稳定"

    def _analyze_entropy(self, state: YinYangState) -> Dict[str, Any]:
        """分析熵特征"""
        entropy_level = "low"
        if state.entropy > self.config.entropy_threshold_high:
            entropy_level = "high"
        elif state.entropy > self.config.entropy_threshold_low:
            entropy_level = "medium"

        return {
            "entropy_value": state.entropy,
            "entropy_level": entropy_level,
            "interpretation": self._interpret_entropy(state.entropy),
        }

    def _interpret_entropy(self, entropy: float) -> str:
        """解释熵值"""
        if entropy < 1.0:
            return "极低熵：数据高度集中，信息多样性不足"
        elif entropy < 3.0:
            return "低熵：数据较稳定，变化不大"
        elif entropy < 5.0:
            return "中等熵：数据适度变化，信息丰富"
        elif entropy < 8.0:
            return "高熵：数据变化剧烈，可能存在异常"
        else:
            return "极高熵：数据极度混乱，存在严重问题"

    def _analyze_mass_energy(self, state: YinYangState) -> Dict[str, Any]:
        """分析质能特征"""
        ratio_status = "balanced"
        if state.mass_energy_ratio < self.config.mass_energy_ratio_low:
            ratio_status = "energy_deficient"
        elif state.mass_energy_ratio > self.config.mass_energy_ratio_high:
            ratio_status = "mass_deficient"

        return {
            "mass_energy_ratio": state.mass_energy_ratio,
            "ratio_status": ratio_status,
            "interpretation": self._interpret_mass_energy_ratio(state.mass_energy_ratio),
        }

    def _interpret_mass_energy_ratio(self, ratio: float) -> str:
        """解释质能比"""
        if ratio < 0.3:
            return "质能比极低：数据量大但信息价值低，存在大量冗余"
        elif ratio < 0.7:
            return "质能比偏低：数据量相对较大，信息价值有待提升"
        elif ratio < 1.5:
            return "质能比适中：数据量与信息价值匹配良好"
        elif ratio < 3.0:
            return "质能比偏高：数据量相对较小，信息价值较高"
        else:
            return "质能比极高：数据量小但信息价值极高，可能存在数据稀疏问题"

    def _analyze_singularity(self, state: YinYangState) -> Dict[str, Any]:
        """分析奇点风险"""
        risk_level = "low"
        if state.singularity_risk >= 0.8:
            risk_level = "critical"
        elif state.singularity_risk >= 0.6:
            risk_level = "high"
        elif state.singularity_risk >= 0.4:
            risk_level = "medium"

        return {
            "singularity_risk": state.singularity_risk,
            "risk_level": risk_level,
            "interpretation": self._interpret_singularity_risk(state.singularity_risk),
        }

    def _interpret_singularity_risk(self, risk: float) -> str:
        """解释奇点风险"""
        if risk < 0.3:
            return "奇点风险低：数据状态稳定，无明显异常"
        elif risk < 0.5:
            return "奇点风险中等：数据存在轻微异常，建议关注"
        elif risk < 0.7:
            return "奇点风险较高：数据可能即将发生质的变化，需要监控"
        elif risk < 0.9:
            return "奇点风险高：数据处于临界状态，需要立即处理"
        else:
            return "奇点风险极高：数据已发生质的变化，存在严重问题"

    def _generate_recommendations(self, state: YinYangState) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if state.state_label == self.STATE_LABELS["singularity"]:
            recommendations.append("立即处理：数据存在严重质量问题，建议进行全面数据清洗")
            recommendations.append("检查质能平衡：评估数据量与信息价值的匹配度")
            recommendations.append("降低熵值：通过标准化、去噪等方式减少数据混乱度")

        elif state.state_label == self.STATE_LABELS["yin_dominant"]:
            recommendations.append("增加多样性：引入更多变化的数据特征")
            recommendations.append("提升信息密度：增加数据的信息含量")
            recommendations.append("活跃数据：考虑增加时间维度或动态特征")

        elif state.state_label == self.STATE_LABELS["yang_dominant"]:
            recommendations.append("增强稳定性：标准化数据格式和结构")
            recommendations.append("提高一致性：确保数据格式统一")
            recommendations.append("降低异常：处理离群值和异常数据")

        else:
            recommendations.append("保持平衡：当前数据状态良好，建议持续监控")
            recommendations.append("定期评估：建立定期质量评估机制")

        if state.transition_probability > 0.5:
            recommendations.append(
                f"注意状态转换：当前转换概率({state.transition_probability:.2f})较高，建议密切监控"
            )

        return recommendations

    def _get_history_summary(self) -> Dict[str, Any]:
        """获取历史摘要"""
        if not self.state_history:
            return {"message": "No history"}

        recent_states = self.state_history[-5:]
        avg_yin = sum(s.yin_score for s in recent_states) / len(recent_states)
        avg_yang = sum(s.yang_score for s in recent_states) / len(recent_states)
        avg_balance = sum(s.balance for s in recent_states) / len(recent_states)

        transitions = len(self.transition_history)

        return {
            "history_length": len(self.state_history),
            "transition_count": transitions,
            "recent_avg_yin": avg_yin,
            "recent_avg_yang": avg_yang,
            "recent_avg_balance": avg_balance,
        }


class YinYangEvolution:
    """
    两仪演化分析器

    分析阴阳状态的演化轨迹，预测未来趋势。
    """

    def __init__(self, model: Optional[YinYangModel] = None):
        """
        初始化两仪演化分析器

        Args:
            model: 两仪模型实例
        """
        self.model = model or YinYangModel()

    def analyze_evolution(
        self,
        df_sequence: List[pd.DataFrame],
        mass_energy_sequence: Optional[List[DataMassEnergy]] = None,
    ) -> Dict[str, Any]:
        """
        分析阴阳演化轨迹

        Args:
            df_sequence: 数据序列（时间序列数据）
            mass_energy_sequence: 质能模型序列

        Returns:
            演化分析结果
        """
        states = []
        for i, df in enumerate(df_sequence):
            mass_energy = mass_energy_sequence[i] if mass_energy_sequence else None
            state = self.model.generate_yin_yang(df, mass_energy=mass_energy)
            states.append(state)

        if len(states) < 2:
            return {"error": "需要至少两个时间点的数据"}

        evolution = {
            "states": [s.to_dict() for s in states],
            "transitions": [t.to_dict() for t in self.model.transition_history],
            "trend": self._analyze_trend(states),
            "predictions": self._predict_future(states),
            "anomalies": self._detect_anomalies(states),
        }

        return evolution

    def _analyze_trend(self, states: List[YinYangState]) -> Dict[str, Any]:
        """分析演化趋势"""
        yin_scores = [s.yin_score for s in states]
        yang_scores = [s.yang_score for s in states]
        balances = [s.balance for s in states]
        entropies = [s.entropy for s in states]

        yin_trend = "increasing" if yin_scores[-1] > yin_scores[0] else "decreasing"
        yang_trend = "increasing" if yang_scores[-1] > yang_scores[0] else "decreasing"

        balance_change = balances[-1] - balances[0]
        entropy_change = entropies[-1] - entropies[0]

        return {
            "yin_trend": yin_trend,
            "yang_trend": yang_trend,
            "balance_change": balance_change,
            "entropy_change": entropy_change,
            "yin_change": yin_scores[-1] - yin_scores[0],
            "yang_change": yang_scores[-1] - yang_scores[0],
        }

    def _predict_future(
        self,
        states: List[YinYangState],
        steps: int = 3,
    ) -> List[Dict[str, Any]]:
        """预测未来状态"""
        if len(states) < 3:
            return []

        predictions = []
        current_state = states[-1]

        for _ in range(steps):
            entropy_trend = (
                sum(s.entropy for s in states[-3:]) / 3 - current_state.entropy
            )
            transition = self.model.predict_transition(
                current_state,
                entropy_change=entropy_trend * 0.5,
            )
            predictions.append(transition.to_dict())

        return predictions

    def _detect_anomalies(self, states: List[YinYangState]) -> List[Dict[str, Any]]:
        """检测演化异常"""
        anomalies = []
        entropies = [s.entropy for s in states]

        if len(entropies) < 3:
            return anomalies

        mean_entropy = np.mean(entropies)
        std_entropy = np.std(entropies)

        for i, state in enumerate(states):
            if abs(state.entropy - mean_entropy) > 2 * std_entropy:
                anomalies.append({
                    "index": i,
                    "state": state.to_dict(),
                    "anomaly_type": "entropy_spike" if state.entropy > mean_entropy else "entropy_drop",
                    "deviation": abs(state.entropy - mean_entropy) / std_entropy,
                })

        return anomalies