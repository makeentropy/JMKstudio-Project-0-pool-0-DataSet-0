"""
自我评估模块

提供自反思智能体的自我评估功能，基于经验数据池对智能体表现进行多维度评估。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.experience.models import ExperienceRecord
from ai_llm_agent_crawler.experience.pool import ExperienceDataPool
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class AssessmentDimension(str, Enum):
    """评估维度枚举"""

    ACCURACY = "accuracy"
    EFFICIENCY = "efficiency"
    COMPLETENESS = "completeness"
    RESOURCE_USAGE = "resource_usage"
    INNOVATIVENESS = "innovativeness"


class DimensionScore(BaseModel):
    """维度评分模型"""

    dimension: AssessmentDimension = Field(..., description="评估维度")
    score: float = Field(..., ge=0.0, le=1.0, description="评分 0-1")
    weight: float = Field(..., ge=0.0, le=1.0, description="权重")
    evidence: List[str] = Field(default_factory=list, description="评分依据说明")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度 0-1")


class SelfAssessmentResult(BaseModel):
    """自我评估结果模型"""

    overall_score: float = Field(..., ge=0.0, le=1.0, description="综合评分 0-1")
    dimensions: Dict[str, DimensionScore] = Field(default_factory=dict, description="各维度评分")
    assessment_time: datetime = Field(default_factory=datetime.now, description="评估时间")
    experience_count: int = Field(default=0, description="基于的经验数量")
    summary: str = Field(default="", description="总体评价文本")
    strengths: List[str] = Field(default_factory=list, description="优势列表")
    weaknesses: List[str] = Field(default_factory=list, description="不足列表")
    recommendations: List[str] = Field(default_factory=list, description="改进建议列表")


class SelfAssessmentConfig(BaseModel):
    """评估配置"""

    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "accuracy": 0.3,
            "efficiency": 0.25,
            "completeness": 0.2,
            "resource_usage": 0.15,
            "innovativeness": 0.1,
        },
        description="各维度权重",
    )
    min_experience_count: int = Field(default=1, description="最少经验数量")
    lookback_days: Optional[int] = Field(default=None, description="回顾天数，None表示全部")
    success_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="成功阈值")
    custom_dimensions: Optional[List[Dict[str, Any]]] = Field(default=None, description="自定义维度")


class SelfAssessment:
    """自我评估器类

    基于经验数据池对智能体表现进行多维度自我评估。
    """

    def __init__(
        self,
        pool: ExperienceDataPool,
        config: Optional[SelfAssessmentConfig] = None,
    ):
        """
        初始化自我评估器

        Args:
            pool: 经验数据池
            config: 评估配置
        """
        self._pool = pool
        self._config = config or SelfAssessmentConfig()
        self._logger = get_logger(f"{__name__}.SelfAssessment")
        self._assessment_history: List[Dict[str, Any]] = []

    def assess(self, filters: Optional[Dict[str, Any]] = None) -> SelfAssessmentResult:
        """
        对经验池中指定范围的经验进行自我评估

        Args:
            filters: 过滤条件，与 pool.query 一致（task_type, status, time_range等）

        Returns:
            完整的评估结果
        """
        query_filters = filters or {}

        if self._config.lookback_days is not None:
            start_time = datetime.now() - timedelta(days=self._config.lookback_days)
            if "time_range" not in query_filters:
                query_filters["time_range"] = {}
            query_filters["time_range"]["start"] = start_time

        experiences = self._pool.query(query_filters, limit=10000)
        experience_count = len(experiences)

        if experience_count < self._config.min_experience_count:
            return self._generate_empty_result(experience_count)

        dimensions = {}
        for dim in AssessmentDimension:
            dim_score = self.assess_dimension(dim, experiences)
            dimensions[dim.value] = dim_score

        overall_score = self._calculate_overall_score(dimensions)

        result = SelfAssessmentResult(
            overall_score=overall_score,
            dimensions=dimensions,
            experience_count=experience_count,
        )

        self._generate_summary(result)

        history_entry = {
            "date": result.assessment_time.strftime("%Y-%m-%d"),
            "overall_score": result.overall_score,
            "experience_count": result.experience_count,
            "dimensions": {k: v.score for k, v in result.dimensions.items()},
        }
        self._assessment_history.append(history_entry)

        self._logger.info(
            f"自我评估完成，综合评分: {overall_score:.3f}, 经验数量: {experience_count}"
        )

        return result

    def assess_dimension(
        self,
        dimension: AssessmentDimension,
        experiences: List[ExperienceRecord],
    ) -> DimensionScore:
        """
        对指定维度进行评分

        Args:
            dimension: 评估维度
            experiences: 经验记录列表

        Returns:
            该维度的评分详情和依据
        """
        if not experiences:
            return DimensionScore(
                dimension=dimension,
                score=0.0,
                weight=self._config.weights.get(dimension.value, 0.0),
                evidence=["无经验数据可供评估"],
                confidence=0.0,
            )

        assess_methods = {
            AssessmentDimension.ACCURACY: self._assess_accuracy,
            AssessmentDimension.EFFICIENCY: self._assess_efficiency,
            AssessmentDimension.COMPLETENESS: self._assess_completeness,
            AssessmentDimension.RESOURCE_USAGE: self._assess_resource_usage,
            AssessmentDimension.INNOVATIVENESS: self._assess_innovativeness,
        }

        method = assess_methods.get(dimension)
        if method:
            result = method(experiences)
            result.weight = self._config.weights.get(dimension.value, 0.0)
            return result

        return DimensionScore(
            dimension=dimension,
            score=0.5,
            weight=self._config.weights.get(dimension.value, 0.0),
            evidence=["未知维度，使用默认评分"],
            confidence=0.0,
        )

    def _assess_accuracy(self, experiences: List[ExperienceRecord]) -> DimensionScore:
        """
        准确性维度评分逻辑

        基于 success/failed 比例、performance_metrics 中的 accuracy、错误数量惩罚。

        Args:
            experiences: 经验记录列表

        Returns:
            准确性维度评分
        """
        total = len(experiences)
        success_count = sum(1 for e in experiences if e.status == "success")
        failed_count = sum(1 for e in experiences if e.status == "failed")
        partial_count = sum(1 for e in experiences if e.status == "partial")

        success_rate = success_count / total if total > 0 else 0.0

        accuracy_metrics = [
            e.performance_metrics.get("accuracy", None)
            for e in experiences
            if "accuracy" in e.performance_metrics
        ]
        avg_accuracy = (
            sum(accuracy_metrics) / len(accuracy_metrics)
            if accuracy_metrics
            else None
        )

        total_errors = sum(len(e.errors) for e in experiences)
        avg_errors = total_errors / total if total > 0 else 0.0
        error_penalty = min(avg_errors * 0.1, 0.3)

        if avg_accuracy is not None:
            score = success_rate * 0.5 + avg_accuracy * 0.5 - error_penalty
        else:
            score = success_rate * 0.7 + (partial_count / total) * 0.3 - error_penalty

        score = max(0.0, min(1.0, score))

        confidence = min(total / 10.0, 1.0)

        evidence = [
            f"基于 {total} 条经验记录评估",
            f"成功 {success_count} 条，失败 {failed_count} 条，部分完成 {partial_count} 条",
            f"任务成功率: {success_rate:.1%}",
        ]
        if avg_accuracy is not None:
            evidence.append(f"平均准确率指标: {avg_accuracy:.1%}")
        evidence.append(f"平均错误数: {avg_errors:.2f} 个/任务")

        return DimensionScore(
            dimension=AssessmentDimension.ACCURACY,
            score=score,
            weight=self._config.weights.get("accuracy", 0.3),
            evidence=evidence,
            confidence=confidence,
        )

    def _assess_efficiency(self, experiences: List[ExperienceRecord]) -> DimensionScore:
        """
        效率维度评分逻辑

        基于 duration_ms 的分布（与基准比较）、performance_metrics 中的 efficiency、超时任务比例。

        Args:
            experiences: 经验记录列表

        Returns:
            效率维度评分
        """
        total = len(experiences)
        durations = [e.duration_ms for e in experiences if e.duration_ms > 0]

        if not durations:
            return DimensionScore(
                dimension=AssessmentDimension.EFFICIENCY,
                score=0.5,
                weight=self._config.weights.get("efficiency", 0.25),
                evidence=["无耗时数据可供评估"],
                confidence=0.1,
            )

        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        baseline_duration = 5000.0
        if avg_duration <= baseline_duration:
            duration_score = 1.0 - 0.3 * (avg_duration / baseline_duration)
        else:
            duration_score = max(0.0, 0.7 - 0.5 * ((avg_duration - baseline_duration) / baseline_duration))

        efficiency_metrics = [
            e.performance_metrics.get("efficiency", None)
            for e in experiences
            if "efficiency" in e.performance_metrics
        ]
        avg_efficiency = (
            sum(efficiency_metrics) / len(efficiency_metrics)
            if efficiency_metrics
            else None
        )

        timeout_count = sum(
            1 for e in experiences if e.duration_ms > baseline_duration * 2
        )
        timeout_rate = timeout_count / total if total > 0 else 0.0
        timeout_penalty = timeout_rate * 0.3

        if avg_efficiency is not None:
            score = duration_score * 0.4 + avg_efficiency * 0.6 - timeout_penalty
        else:
            score = duration_score * 0.7 + (1.0 - timeout_rate) * 0.3 - timeout_penalty

        score = max(0.0, min(1.0, score))

        confidence = min(total / 10.0, 1.0)

        evidence = [
            f"基于 {len(durations)} 条有耗时数据的记录评估",
            f"平均耗时: {avg_duration:.0f}ms (范围: {min_duration:.0f}ms - {max_duration:.0f}ms)",
            f"基准耗时: {baseline_duration:.0f}ms",
            f"耗时评分: {duration_score:.1%}",
        ]
        if avg_efficiency is not None:
            evidence.append(f"平均效率指标: {avg_efficiency:.1%}")
        evidence.append(f"超时任务数: {timeout_count} 个 (超时率: {timeout_rate:.1%})")

        return DimensionScore(
            dimension=AssessmentDimension.EFFICIENCY,
            score=score,
            weight=self._config.weights.get("efficiency", 0.25),
            evidence=evidence,
            confidence=confidence,
        )

    def _assess_completeness(self, experiences: List[ExperienceRecord]) -> DimensionScore:
        """
        完整性维度评分逻辑

        任务完成率（success + partial 占比）、output_summary 的完整度、跳过任务比例。

        Args:
            experiences: 经验记录列表

        Returns:
            完整性维度评分
        """
        total = len(experiences)
        success_count = sum(1 for e in experiences if e.status == "success")
        partial_count = sum(1 for e in experiences if e.status == "partial")
        skipped_count = sum(1 for e in experiences if e.status == "skipped")

        completion_rate = (success_count + partial_count) / total if total > 0 else 0.0
        skip_rate = skipped_count / total if total > 0 else 0.0

        outputs_with_content = sum(
            1 for e in experiences if e.output_summary and len(e.output_summary.strip()) > 0
        )
        output_completeness = outputs_with_content / total if total > 0 else 0.0

        score = completion_rate * 0.6 + output_completeness * 0.3 + (1.0 - skip_rate) * 0.1
        score = max(0.0, min(1.0, score))

        confidence = min(total / 10.0, 1.0)

        evidence = [
            f"基于 {total} 条经验记录评估",
            f"成功 {success_count} 条，部分完成 {partial_count} 条，跳过 {skipped_count} 条",
            f"任务完成率 (成功+部分完成): {completion_rate:.1%}",
            f"跳过率: {skip_rate:.1%}",
            f"输出完整度: {output_completeness:.1%}",
        ]

        return DimensionScore(
            dimension=AssessmentDimension.COMPLETENESS,
            score=score,
            weight=self._config.weights.get("completeness", 0.2),
            evidence=evidence,
            confidence=confidence,
        )

    def _assess_resource_usage(self, experiences: List[ExperienceRecord]) -> DimensionScore:
        """
        资源使用率评分逻辑

        基于 duration_ms（耗时越短资源使用越优）、错误和重试导致的额外资源消耗、警告数量。

        Args:
            experiences: 经验记录列表

        Returns:
            资源使用率评分
        """
        total = len(experiences)
        durations = [e.duration_ms for e in experiences if e.duration_ms > 0]

        if not durations:
            return DimensionScore(
                dimension=AssessmentDimension.RESOURCE_USAGE,
                score=0.5,
                weight=self._config.weights.get("resource_usage", 0.15),
                evidence=["无耗时数据可供评估"],
                confidence=0.1,
            )

        avg_duration = sum(durations) / len(durations)

        baseline_duration = 5000.0
        if avg_duration <= baseline_duration:
            resource_score = 1.0 - 0.2 * (avg_duration / baseline_duration)
        else:
            resource_score = max(
                0.0, 0.8 - 0.6 * ((avg_duration - baseline_duration) / baseline_duration)
            )

        error_count = sum(len(e.errors) for e in experiences)
        avg_errors = error_count / total if total > 0 else 0.0
        error_resource_penalty = min(avg_errors * 0.08, 0.2)

        warning_count = sum(len(e.warnings) for e in experiences)
        avg_warnings = warning_count / total if total > 0 else 0.0
        warning_resource_penalty = min(avg_warnings * 0.04, 0.1)

        score = resource_score - error_resource_penalty - warning_resource_penalty
        score = max(0.0, min(1.0, score))

        confidence = min(total / 10.0, 1.0)

        evidence = [
            f"基于 {len(durations)} 条有耗时数据的记录评估",
            f"平均耗时: {avg_duration:.0f}ms",
            f"资源使用评分 (基于耗时): {resource_score:.1%}",
            f"平均错误数: {avg_errors:.2f} 个/任务",
            f"平均警告数: {avg_warnings:.2f} 个/任务",
        ]

        return DimensionScore(
            dimension=AssessmentDimension.RESOURCE_USAGE,
            score=score,
            weight=self._config.weights.get("resource_usage", 0.15),
            evidence=evidence,
            confidence=confidence,
        )

    def _assess_innovativeness(self, experiences: List[ExperienceRecord]) -> DimensionScore:
        """
        创新性维度评分逻辑

        任务类型多样性、metadata 中的新方法/新策略标记、解决罕见问题的比例。

        Args:
            experiences: 经验记录列表

        Returns:
            创新性维度评分
        """
        total = len(experiences)

        task_types = set(e.task_type for e in experiences)
        type_diversity = min(len(task_types) / 6.0, 1.0)

        innovation_keywords = [
            "new_method",
            "new_strategy",
            "innovation",
            "novel",
            "creative",
            "优化策略",
            "新方法",
            "创新",
        ]
        innovative_count = 0
        for e in experiences:
            metadata_str = str(e.metadata).lower()
            output_str = e.output_summary.lower()
            for keyword in innovation_keywords:
                if keyword.lower() in metadata_str or keyword.lower() in output_str:
                    innovative_count += 1
                    break

        innovation_rate = innovative_count / total if total > 0 else 0.0

        rare_task_count = sum(
            1 for e in experiences
            if e.task_type == "other" or e.metadata.get("rare", False)
        )
        rare_rate = rare_task_count / total if total > 0 else 0.0

        score = type_diversity * 0.4 + innovation_rate * 0.4 + rare_rate * 0.2
        score = max(0.0, min(1.0, score))

        confidence = min(total / 20.0, 1.0)

        evidence = [
            f"基于 {total} 条经验记录评估",
            f"涉及任务类型数: {len(task_types)} 种 ({', '.join(sorted(task_types))})",
            f"任务类型多样性评分: {type_diversity:.1%}",
            f"含创新标记的任务数: {innovative_count} 个 (比例: {innovation_rate:.1%})",
            f"罕见/特殊任务数: {rare_task_count} 个 (比例: {rare_rate:.1%})",
        ]

        return DimensionScore(
            dimension=AssessmentDimension.INNOVATIVENESS,
            score=score,
            weight=self._config.weights.get("innovativeness", 0.1),
            evidence=evidence,
            confidence=confidence,
        )

    def _generate_summary(self, result: SelfAssessmentResult) -> None:
        """
        生成总体评价、优势、不足、建议

        Args:
            result: 评估结果对象（就地修改）
        """
        overall = result.overall_score
        dimensions = result.dimensions

        if overall >= 0.9:
            level_desc = "优秀"
        elif overall >= 0.8:
            level_desc = "良好"
        elif overall >= 0.7:
            level_desc = "中等"
        elif overall >= 0.5:
            level_desc = "一般"
        else:
            level_desc = "较差"

        result.summary = (
            f"本次评估基于 {result.experience_count} 条经验记录，"
            f"综合评分为 {overall:.1%}，整体表现{level_desc}。"
        )

        sorted_dims = sorted(
            dimensions.items(),
            key=lambda x: x[1].score,
            reverse=True,
        )

        strengths = []
        weaknesses = []
        recommendations = []

        for dim_name, dim_score in sorted_dims:
            if dim_score.score >= 0.8:
                dim_label = self._get_dimension_label(dim_name)
                strengths.append(f"{dim_label}表现优秀，评分 {dim_score.score:.1%}")
            elif dim_score.score < 0.5:
                dim_label = self._get_dimension_label(dim_name)
                weaknesses.append(f"{dim_label}表现不足，评分 {dim_score.score:.1%}")

        if not strengths:
            top_dim = sorted_dims[0] if sorted_dims else None
            if top_dim:
                dim_label = self._get_dimension_label(top_dim[0])
                strengths.append(f"{dim_label}相对较好，评分 {top_dim[1].score:.1%}")

        if not weaknesses:
            bottom_dim = sorted_dims[-1] if sorted_dims else None
            if bottom_dim:
                dim_label = self._get_dimension_label(bottom_dim[0])
                weaknesses.append(f"{dim_label}仍有提升空间，评分 {bottom_dim[1].score:.1%}")

        for dim_name, dim_score in sorted_dims:
            if dim_score.score < self._config.success_threshold:
                rec = self._get_dimension_recommendation(dim_name)
                if rec:
                    recommendations.append(rec)

        if not recommendations:
            recommendations.append("继续保持当前表现，追求更高的稳定性和效率")

        result.strengths = strengths
        result.weaknesses = weaknesses
        result.recommendations = recommendations

    def _get_dimension_label(self, dim_name: str) -> str:
        """
        获取维度的中文名称

        Args:
            dim_name: 维度英文名

        Returns:
            维度中文名称
        """
        labels = {
            "accuracy": "准确性",
            "efficiency": "效率",
            "completeness": "完整性",
            "resource_usage": "资源使用率",
            "innovativeness": "创新性",
        }
        return labels.get(dim_name, dim_name)

    def _get_dimension_recommendation(self, dim_name: str) -> str:
        """
        获取维度改进建议

        Args:
            dim_name: 维度英文名

        Returns:
            改进建议文本
        """
        recommendations = {
            "accuracy": "建议提升任务准确性，增加验证环节和错误检查机制",
            "efficiency": "建议优化执行效率，分析耗时瓶颈并进行针对性优化",
            "completeness": "建议提升任务完成度，减少跳过和部分完成的任务比例",
            "resource_usage": "建议优化资源使用，减少不必要的错误重试和警告",
            "innovativeness": "建议鼓励创新尝试，探索更多任务类型和解决策略",
        }
        return recommendations.get(dim_name, "")

    def _calculate_overall_score(
        self, dimensions: Dict[str, DimensionScore]
    ) -> float:
        """
        计算综合评分（加权平均）

        Args:
            dimensions: 各维度评分字典

        Returns:
            综合评分
        """
        if not dimensions:
            return 0.0

        total_weight = sum(d.weight for d in dimensions.values())
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(d.score * d.weight for d in dimensions.values())
        return weighted_sum / total_weight

    def _generate_empty_result(self, experience_count: int) -> SelfAssessmentResult:
        """
        生成空数据的默认评估结果

        Args:
            experience_count: 经验数量

        Returns:
            默认评估结果
        """
        dimensions = {}
        for dim in AssessmentDimension:
            dimensions[dim.value] = DimensionScore(
                dimension=dim,
                score=0.0,
                weight=self._config.weights.get(dim.value, 0.0),
                evidence=["经验数据不足，无法进行有效评估"],
                confidence=0.0,
            )

        result = SelfAssessmentResult(
            overall_score=0.0,
            dimensions=dimensions,
            experience_count=experience_count,
            summary=f"经验数据不足（仅 {experience_count} 条），无法进行有效评估。",
            strengths=[],
            weaknesses=["经验数据不足"],
            recommendations=["积累更多经验数据后再进行评估"],
        )

        return result

    def get_historical_assessment(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取历史评估趋势（按天聚合）

        Args:
            days: 回顾天数，默认 30 天

        Returns:
            每天的综合评分列表
        """
        history_by_date: Dict[str, Dict[str, Any]] = {}

        for entry in self._assessment_history:
            date_str = entry["date"]
            if date_str not in history_by_date:
                history_by_date[date_str] = {
                    "date": date_str,
                    "scores": [],
                    "experience_counts": [],
                }
            history_by_date[date_str]["scores"].append(entry["overall_score"])
            history_by_date[date_str]["experience_counts"].append(entry["experience_count"])

        result = []
        for date_str in sorted(history_by_date.keys())[-days:]:
            data = history_by_date[date_str]
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
            total_exp = sum(data["experience_counts"])
            result.append(
                {
                    "date": date_str,
                    "overall_score": avg_score,
                    "experience_count": total_exp,
                    "assessment_count": len(data["scores"]),
                }
            )

        return result
