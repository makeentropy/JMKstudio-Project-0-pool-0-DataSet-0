"""
经验分析工具集

提供经验数据的趋势分析、模式挖掘和对比分析功能。
"""

import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.experience.models import ExperienceRecord
from ai_llm_agent_crawler.experience.pool import ExperienceDataPool
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class TrendPoint(BaseModel):
    """趋势点模型"""

    timestamp: datetime = Field(..., description="时间点")
    overall_score: float = Field(..., description="综合评分")
    dimension_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="各维度评分",
    )
    experience_count: int = Field(default=0, description="经验数量")
    is_inflection: bool = Field(default=False, description="是否拐点")
    inflection_type: Optional[str] = Field(default=None, description="拐点类型")
    description: str = Field(default="", description="描述")


class TrendAnalysisResult(BaseModel):
    """趋势分析结果模型"""

    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    total_points: int = Field(default=0, description="数据点数")
    overall_trend: str = Field(default="stable", description="整体趋势")
    trend_slope: float = Field(default=0.0, description="趋势斜率")
    trend_points: List[TrendPoint] = Field(default_factory=list, description="趋势点列表")
    dimension_trends: Dict[str, str] = Field(
        default_factory=dict,
        description="各维度趋势",
    )
    inflection_points: List[TrendPoint] = Field(
        default_factory=list,
        description="拐点列表",
    )
    key_findings: List[str] = Field(default_factory=list, description="关键发现")
    prediction: Dict[str, Any] = Field(default_factory=dict, description="预测预估")


class ComparisonResult(BaseModel):
    """对比分析结果模型"""

    comparison_type: str = Field(..., description="对比类型")
    group_a_name: str = Field(..., description="A组名称")
    group_b_name: str = Field(..., description="B组名称")
    metrics_a: Dict[str, float] = Field(default_factory=dict, description="A组指标")
    metrics_b: Dict[str, float] = Field(default_factory=dict, description="B组指标")
    differences: Dict[str, float] = Field(default_factory=dict, description="差异值")
    winner: Optional[str] = Field(default=None, description="优胜方")
    summary: str = Field(default="", description="总结描述")


class TrendAnalyzer:
    """
    趋势分析器

    分析经验数据池中的能力变化趋势，检测拐点，生成预测。
    """

    def __init__(self, pool: ExperienceDataPool):
        """
        初始化趋势分析器

        Args:
            pool: 经验数据池
        """
        self._pool = pool
        self._logger = get_logger(f"{__name__}.TrendAnalyzer")
        self._default_dimensions = ["accuracy", "efficiency", "completeness"]

    def analyze_trend(
        self,
        days: int = 30,
        granularity: str = "day",
    ) -> TrendAnalysisResult:
        """
        分析指定时间范围内的能力趋势

        Args:
            days: 分析的天数范围
            granularity: 时间粒度，支持 day/week/hour

        Returns:
            趋势分析结果
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        experiences = self._pool.query(
            {"time_range": {"start": start_date, "end": end_date}},
            limit=10000,
        )

        if not experiences:
            return self._generate_empty_result(start_date, end_date)

        aggregated = self._aggregate_by_period(experiences, granularity)

        trend_points = []
        for period_start, period_exps in aggregated:
            overall_score, dim_scores = self._compute_period_score(period_exps)
            point = TrendPoint(
                timestamp=period_start,
                overall_score=overall_score,
                dimension_scores=dim_scores,
                experience_count=len(period_exps),
                description=f"{period_start.strftime('%Y-%m-%d')} 共{len(period_exps)}条经验",
            )
            trend_points.append(point)

        trend_points.sort(key=lambda p: p.timestamp)

        inflection_points = self._detect_inflection_points(trend_points)
        for ip in inflection_points:
            for tp in trend_points:
                if tp.timestamp == ip.timestamp:
                    tp.is_inflection = True
                    tp.inflection_type = ip.inflection_type
                    tp.description = ip.description
                    break

        slope = self._compute_trend_slope(trend_points)
        overall_trend = self._generate_trend_description(slope)

        dimension_trends = {}
        all_dims = set()
        for tp in trend_points:
            all_dims.update(tp.dimension_scores.keys())

        for dim in all_dims:
            dim_points = []
            for tp in trend_points:
                if dim in tp.dimension_scores:
                    dp = TrendPoint(
                        timestamp=tp.timestamp,
                        overall_score=tp.dimension_scores[dim],
                        dimension_scores={},
                        experience_count=tp.experience_count,
                    )
                    dim_points.append(dp)
            if len(dim_points) >= 2:
                dim_slope = self._compute_trend_slope(dim_points)
                dimension_trends[dim] = self._generate_trend_description(dim_slope)

        key_findings = self._generate_key_findings(trend_points, inflection_points)

        result = TrendAnalysisResult(
            start_date=start_date,
            end_date=end_date,
            total_points=len(trend_points),
            overall_trend=overall_trend,
            trend_slope=slope,
            trend_points=trend_points,
            dimension_trends=dimension_trends,
            inflection_points=inflection_points,
            key_findings=key_findings,
        )

        result.prediction = self.predict_next_period(result)

        self._logger.info(
            f"趋势分析完成，时间范围: {start_date.date()} ~ {end_date.date()}, "
            f"数据点: {len(trend_points)}, 趋势: {overall_trend}"
        )

        return result

    def _aggregate_by_period(
        self,
        experiences: List[ExperienceRecord],
        granularity: str,
    ) -> List[Tuple[datetime, List[ExperienceRecord]]]:
        """
        按时间粒度聚合经验数据

        Args:
            experiences: 经验记录列表
            granularity: 时间粒度

        Returns:
            时间段和对应经验列表的元组列表
        """
        if not experiences:
            return []

        groups: Dict[str, List[ExperienceRecord]] = defaultdict(list)

        for exp in experiences:
            ts = exp.timestamp
            if granularity == "hour":
                key = ts.replace(minute=0, second=0, microsecond=0)
            elif granularity == "week":
                weekday = ts.weekday()
                week_start = ts - timedelta(days=weekday)
                key = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                key = ts.replace(hour=0, minute=0, second=0, microsecond=0)
            groups[key.isoformat()].append(exp)

        result = []
        for key_str in sorted(groups.keys()):
            period_start = datetime.fromisoformat(key_str)
            result.append((period_start, groups[key_str]))

        return result

    def _compute_period_score(
        self,
        experiences: List[ExperienceRecord],
    ) -> Tuple[float, Dict[str, float]]:
        """
        计算某一时间段的综合评分和各维度评分

        Args:
            experiences: 该时间段的经验记录列表

        Returns:
            (综合分, 各维度分数字典)
        """
        if not experiences:
            return 0.0, {}

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
            else success_rate * 0.8
        )

        efficiency_metrics = [
            e.performance_metrics.get("efficiency", None)
            for e in experiences
            if "efficiency" in e.performance_metrics
        ]
        avg_efficiency = (
            sum(efficiency_metrics) / len(efficiency_metrics)
            if efficiency_metrics
            else 0.5
        )

        total_errors = sum(len(e.errors) for e in experiences)
        avg_errors = total_errors / total if total > 0 else 0.0
        error_penalty = min(avg_errors * 0.05, 0.2)

        outputs_with_content = sum(
            1 for e in experiences if e.output_summary and len(e.output_summary.strip()) > 0
        )
        completeness = outputs_with_content / total if total > 0 else 0.0
        partial_factor = partial_count / total if total > 0 else 0.0
        completeness = completeness * 0.7 + (1.0 - failed_count / total if total > 0 else 0.0) * 0.3

        avg_accuracy = max(0.0, min(1.0, avg_accuracy))
        avg_efficiency = max(0.0, min(1.0, avg_efficiency))
        completeness = max(0.0, min(1.0, completeness))

        dimension_scores = {
            "accuracy": avg_accuracy,
            "efficiency": avg_efficiency,
            "completeness": completeness,
        }

        overall_score = (
            avg_accuracy * 0.4 + avg_efficiency * 0.3 + completeness * 0.3 - error_penalty
        )
        overall_score = max(0.0, min(1.0, overall_score))

        return overall_score, dimension_scores

    def _detect_inflection_points(self, points: List[TrendPoint]) -> List[TrendPoint]:
        """
        检测趋势中的拐点（峰值、谷值、突变点）

        Args:
            points: 趋势点列表

        Returns:
            拐点列表
        """
        if len(points) < 3:
            return []

        inflections = []
        window = 2
        scores = [p.overall_score for p in points]

        for i in range(window, len(points) - window):
            left_avg = sum(scores[i - window : i]) / window
            right_avg = sum(scores[i + 1 : i + window + 1]) / window
            current = scores[i]

            change_rate_left = current - left_avg
            change_rate_right = right_avg - current

            if abs(change_rate_left) < 0.02 and abs(change_rate_right) < 0.02:
                continue

            is_peak = current > left_avg and current > right_avg and abs(change_rate_left) > 0.03
            is_trough = current < left_avg and current < right_avg and abs(change_rate_left) > 0.03

            prev_change = scores[i] - scores[i - 1]
            next_change = scores[i + 1] - scores[i]
            is_breaking = (
                (prev_change > 0 and next_change < 0 and abs(prev_change) > 0.05)
                or (prev_change < 0 and next_change > 0 and abs(prev_change) > 0.05)
            )

            if is_peak:
                inflection_type = "peak"
                desc = f"峰值点，评分达到 {current:.3f}"
            elif is_trough:
                inflection_type = "trough"
                desc = f"谷值点，评分降至 {current:.3f}"
            elif is_breaking:
                inflection_type = "breaking"
                if prev_change > 0:
                    desc = f"上升转下降突变点，变化率 {prev_change:.3f} → {next_change:.3f}"
                else:
                    desc = f"下降转上升突变点，变化率 {prev_change:.3f} → {next_change:.3f}"
            else:
                continue

            inflection_point = TrendPoint(
                timestamp=points[i].timestamp,
                overall_score=current,
                dimension_scores=points[i].dimension_scores,
                experience_count=points[i].experience_count,
                is_inflection=True,
                inflection_type=inflection_type,
                description=desc,
            )
            inflections.append(inflection_point)

        return inflections

    def _compute_trend_slope(self, points: List[TrendPoint]) -> float:
        """
        计算趋势斜率（线性回归近似）

        Args:
            points: 趋势点列表

        Returns:
            趋势斜率，正值表示上升，负值表示下降
        """
        n = len(points)
        if n < 2:
            return 0.0

        x_mean = (n - 1) / 2.0
        y_mean = sum(p.overall_score for p in points) / n

        numerator = 0.0
        denominator = 0.0

        for i, p in enumerate(points):
            x_diff = i - x_mean
            y_diff = p.overall_score - y_mean
            numerator += x_diff * y_diff
            denominator += x_diff * x_diff

        if denominator == 0:
            return 0.0

        slope = numerator / denominator
        return slope

    def _generate_trend_description(self, slope: float) -> str:
        """
        根据斜率生成趋势描述

        Args:
            slope: 趋势斜率

        Returns:
            improving/declining/stable
        """
        threshold = 0.005
        if slope > threshold:
            return "improving"
        elif slope < -threshold:
            return "declining"
        else:
            return "stable"

    def _generate_key_findings(
        self,
        points: List[TrendPoint],
        inflections: List[TrendPoint],
    ) -> List[str]:
        """
        生成关键发现列表

        Args:
            points: 趋势点列表
            inflections: 拐点列表

        Returns:
            关键发现列表
        """
        findings = []

        if not points:
            return findings

        first_score = points[0].overall_score
        last_score = points[-1].overall_score
        change = last_score - first_score
        change_pct = (change / first_score * 100) if first_score > 0 else 0.0

        if change > 0.05:
            findings.append(
                f"整体表现呈上升趋势，评分从 {first_score:.3f} 提升至 {last_score:.3f} "
                f"（提升 {change_pct:.1f}%）"
            )
        elif change < -0.05:
            findings.append(
                f"整体表现呈下降趋势，评分从 {first_score:.3f} 降至 {last_score:.3f} "
                f"（下降 {abs(change_pct):.1f}%）"
            )
        else:
            findings.append(
                f"整体表现相对稳定，评分在 {first_score:.3f} ~ {last_score:.3f} 之间波动"
            )

        if inflections:
            peak_count = sum(1 for ip in inflections if ip.inflection_type == "peak")
            trough_count = sum(1 for ip in inflections if ip.inflection_type == "trough")
            breaking_count = sum(1 for ip in inflections if ip.inflection_type == "breaking")
            findings.append(
                f"检测到 {len(inflections)} 个拐点："
                f"峰值 {peak_count} 个，谷值 {trough_count} 个，突变 {breaking_count} 个"
            )

            max_score = max(p.overall_score for p in points)
            min_score = min(p.overall_score for p in points)
            findings.append(
                f"最高评分 {max_score:.3f}，最低评分 {min_score:.3f}，"
                f"波动幅度 {max_score - min_score:.3f}"
            )

        total_exp = sum(p.experience_count for p in points)
        avg_exp = total_exp / len(points) if points else 0
        findings.append(f"分析期间共 {total_exp} 条经验，平均每周期 {avg_exp:.1f} 条")

        best_dim = None
        best_score = -1
        worst_dim = None
        worst_score = 2
        latest = points[-1]
        for dim, score in latest.dimension_scores.items():
            if score > best_score:
                best_score = score
                best_dim = dim
            if score < worst_score:
                worst_score = score
                worst_dim = dim

        if best_dim:
            findings.append(f"表现最佳维度：{best_dim}（{best_score:.3f}）")
        if worst_dim:
            findings.append(f"待提升维度：{worst_dim}（{worst_score:.3f}）")

        return findings

    def predict_next_period(
        self,
        current_trend: TrendAnalysisResult,
        periods: int = 3,
    ) -> Dict[str, Any]:
        """
        预测未来几个周期的表现

        Args:
            current_trend: 当前趋势分析结果
            periods: 预测的周期数

        Returns:
            预测值和置信度
        """
        points = current_trend.trend_points
        if len(points) < 2:
            return {
                "periods": periods,
                "predictions": [],
                "confidence": 0.0,
                "method": "insufficient_data",
            }

        slope = current_trend.trend_slope
        last_score = points[-1].overall_score
        last_time = points[-1].timestamp

        predictions = []
        for i in range(1, periods + 1):
            predicted_score = last_score + slope * i
            predicted_score = max(0.0, min(1.0, predicted_score))
            predictions.append(
                {
                    "period_index": i,
                    "predicted_score": predicted_score,
                    "predicted_time": last_time + timedelta(days=i),
                }
            )

        n = len(points)
        if n < 5:
            confidence = 0.3
        elif n < 10:
            confidence = 0.5
        else:
            confidence = 0.7

        recent_volatility = 0.0
        if n >= 3:
            recent = points[-min(5, n) :]
            scores = [p.overall_score for p in recent]
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            recent_volatility = math.sqrt(variance)

        if recent_volatility > 0.15:
            confidence = max(0.2, confidence - 0.2)
        elif recent_volatility < 0.05:
            confidence = min(0.9, confidence + 0.1)

        return {
            "periods": periods,
            "predictions": predictions,
            "confidence": round(confidence, 2),
            "method": "linear_extrapolation",
            "trend_slope": round(slope, 6),
            "volatility": round(recent_volatility, 4),
        }

    def _generate_empty_result(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> TrendAnalysisResult:
        """
        生成空数据的趋势分析结果

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            空趋势分析结果
        """
        return TrendAnalysisResult(
            start_date=start_date,
            end_date=end_date,
            total_points=0,
            overall_trend="stable",
            trend_slope=0.0,
            trend_points=[],
            dimension_trends={},
            inflection_points=[],
            key_findings=["无足够经验数据进行趋势分析"],
            prediction={
                "periods": 3,
                "predictions": [],
                "confidence": 0.0,
                "method": "no_data",
            },
        )


class PatternMiner:
    """
    模式挖掘器

    从经验数据中挖掘高频模式、成功/失败模式、相关性和绩效组合。
    """

    def __init__(self, pool: ExperienceDataPool):
        """
        初始化模式挖掘器

        Args:
            pool: 经验数据池
        """
        self._pool = pool
        self._logger = get_logger(f"{__name__}.PatternMiner")

    def mine_patterns(self, min_frequency: int = 3) -> List[Dict[str, Any]]:
        """
        挖掘经验中的高频模式

        Args:
            min_frequency: 最小频率阈值

        Returns:
            模式列表
        """
        experiences = self._pool.query({}, limit=10000)

        if not experiences:
            return []

        success_patterns = self._mine_success_patterns(experiences, min_frequency)
        failure_patterns = self._mine_failure_patterns(experiences, min_frequency)

        all_patterns = success_patterns + failure_patterns
        all_patterns.sort(key=lambda p: p.get("frequency", 0), reverse=True)

        self._logger.info(
            f"模式挖掘完成，共发现 {len(all_patterns)} 个模式 "
            f"（成功: {len(success_patterns)}, 失败: {len(failure_patterns)}）"
        )

        return all_patterns

    def _mine_success_patterns(
        self,
        experiences: List[ExperienceRecord],
        min_freq: int,
    ) -> List[Dict[str, Any]]:
        """
        挖掘成功模式

        Args:
            experiences: 经验记录列表
            min_freq: 最小频率

        Returns:
            成功模式列表
        """
        success_exps = [e for e in experiences if e.status == "success"]
        if not success_exps:
            return []

        patterns = []

        task_type_counts: Dict[str, int] = defaultdict(int)
        task_type_quality: Dict[str, List[float]] = defaultdict(list)
        for exp in success_exps:
            task_type_counts[exp.task_type] += 1
            if exp.quality_score is not None:
                task_type_quality[exp.task_type].append(exp.quality_score)

        for task_type, count in task_type_counts.items():
            if count >= min_freq:
                avg_quality = (
                    sum(task_type_quality[task_type]) / len(task_type_quality[task_type])
                    if task_type_quality[task_type]
                    else 0.8
                )
                patterns.append(
                    {
                        "pattern_type": "success_pattern",
                        "name": f"{task_type}任务高成功率模式",
                        "frequency": count,
                        "confidence": min(0.5 + count / 20.0, 0.95),
                        "typical_features": [
                            f"任务类型: {task_type}",
                            f"成功次数: {count}",
                            f"平均质量分: {avg_quality:.3f}",
                        ],
                        "applicable_scenarios": [f"{task_type}类型任务执行"],
                        "related_tasks": [task_type],
                        "pattern_details": {
                            "task_type": task_type,
                            "success_count": count,
                            "avg_quality": round(avg_quality, 4),
                        },
                    }
                )

        high_quality = [e for e in success_exps if (e.quality_score or 0) >= 0.8]
        if len(high_quality) >= min_freq:
            perf_keys = set()
            for exp in high_quality:
                perf_keys.update(exp.performance_metrics.keys())

            high_perf_features = []
            for key in sorted(perf_keys):
                values = [
                    exp.performance_metrics[key]
                    for exp in high_quality
                    if key in exp.performance_metrics
                ]
                if values:
                    avg_val = sum(values) / len(values)
                    high_perf_features.append(f"{key} ≥ {avg_val:.2f}")

            patterns.append(
                {
                    "pattern_type": "success_pattern",
                    "name": "高质量完成模式",
                    "frequency": len(high_quality),
                    "confidence": min(0.6 + len(high_quality) / 30.0, 0.9),
                    "typical_features": [
                        f"高质量经验数: {len(high_quality)}",
                        "质量分 ≥ 0.8",
                    ] + high_perf_features[:3],
                    "applicable_scenarios": ["追求高质量输出的任务"],
                    "related_tasks": list(set(e.task_type for e in high_quality)),
                    "pattern_details": {
                        "quality_threshold": 0.8,
                        "count": len(high_quality),
                    },
                }
            )

        low_error = [e for e in success_exps if len(e.errors) == 0 and len(e.warnings) == 0]
        if len(low_error) >= min_freq:
            patterns.append(
                {
                    "pattern_type": "success_pattern",
                    "name": "零错误执行模式",
                    "frequency": len(low_error),
                    "confidence": min(0.5 + len(low_error) / 25.0, 0.9),
                    "typical_features": [
                        f"零错误经验数: {len(low_error)}",
                        "无错误无警告",
                        f"涉及任务类型: {len(set(e.task_type for e in low_error))} 种",
                    ],
                    "applicable_scenarios": ["稳定可靠的任务执行", "关键路径任务"],
                    "related_tasks": list(set(e.task_type for e in low_error)),
                    "pattern_details": {
                        "zero_error_count": len(low_error),
                        "task_types": list(set(e.task_type for e in low_error)),
                    },
                }
            )

        return patterns

    def _mine_failure_patterns(
        self,
        experiences: List[ExperienceRecord],
        min_freq: int,
    ) -> List[Dict[str, Any]]:
        """
        挖掘失败模式

        Args:
            experiences: 经验记录列表
            min_freq: 最小频率

        Returns:
            失败模式列表
        """
        failed_exps = [e for e in experiences if e.status == "failed"]
        if not failed_exps:
            return []

        patterns = []

        all_errors: Dict[str, int] = defaultdict(int)
        for exp in failed_exps:
            for error in exp.errors:
                all_errors[error] += 1

        common_errors = [
            (err, cnt) for err, cnt in all_errors.items() if cnt >= min_freq
        ]
        common_errors.sort(key=lambda x: x[1], reverse=True)

        for error, count in common_errors[:5]:
            related_exps = [e for e in failed_exps if error in e.errors]
            task_types = list(set(e.task_type for e in related_exps))
            patterns.append(
                {
                    "pattern_type": "failure_pattern",
                    "name": f"错误模式: {error[:30]}",
                    "frequency": count,
                    "confidence": min(0.5 + count / 15.0, 0.95),
                    "typical_features": [
                        f"错误信息: {error}",
                        f"出现次数: {count}",
                        f"影响任务类型: {len(task_types)} 种",
                    ],
                    "applicable_scenarios": [f"涉及{', '.join(task_types[:3])}等任务"],
                    "related_tasks": task_types,
                    "pattern_details": {
                        "error_message": error,
                        "occurrence_count": count,
                        "affected_task_types": task_types,
                    },
                }
            )

        task_type_fail_counts: Dict[str, int] = defaultdict(int)
        task_type_total_counts: Dict[str, int] = defaultdict(int)
        for exp in experiences:
            task_type_total_counts[exp.task_type] += 1
            if exp.status == "failed":
                task_type_fail_counts[exp.task_type] += 1

        for task_type, fail_count in task_type_fail_counts.items():
            if fail_count >= min_freq:
                total = task_type_total_counts[task_type]
                fail_rate = fail_count / total if total > 0 else 0.0
                if fail_rate > 0.2:
                    patterns.append(
                        {
                            "pattern_type": "failure_pattern",
                            "name": f"{task_type}任务高失败率模式",
                            "frequency": fail_count,
                            "confidence": min(0.4 + fail_count / 20.0, 0.85),
                            "typical_features": [
                                f"任务类型: {task_type}",
                                f"失败次数: {fail_count}",
                                f"失败率: {fail_rate:.1%}",
                            ],
                            "applicable_scenarios": [f"{task_type}类型任务"],
                            "related_tasks": [task_type],
                            "pattern_details": {
                                "task_type": task_type,
                                "fail_count": fail_count,
                                "total_count": total,
                                "fail_rate": round(fail_rate, 4),
                            },
                        }
                    )

        multi_error = [e for e in failed_exps if len(e.errors) >= 2]
        if len(multi_error) >= min_freq:
            patterns.append(
                {
                    "pattern_type": "failure_pattern",
                    "name": "多错误并发模式",
                    "frequency": len(multi_error),
                    "confidence": min(0.4 + len(multi_error) / 20.0, 0.8),
                    "typical_features": [
                        f"多错误经验数: {len(multi_error)}",
                        "单次失败出现 ≥ 2 个错误",
                        f"平均错误数: {sum(len(e.errors) for e in multi_error) / len(multi_error):.1f}",
                    ],
                    "applicable_scenarios": ["复杂任务执行", "系统性问题排查"],
                    "related_tasks": list(set(e.task_type for e in multi_error)),
                    "pattern_details": {
                        "multi_error_count": len(multi_error),
                        "avg_errors_per_task": round(
                            sum(len(e.errors) for e in multi_error) / len(multi_error), 2
                        ),
                    },
                }
            )

        return patterns

    def find_correlations(self, metric1: str, metric2: str) -> Dict[str, Any]:
        """
        发现两个指标间的相关性

        Args:
            metric1: 指标1名称
            metric2: 指标2名称

        Returns:
            相关系数、显著性、散点数据摘要
        """
        experiences = self._pool.query({}, limit=10000)

        if not experiences:
            return {
                "metric1": metric1,
                "metric2": metric2,
                "correlation": 0.0,
                "p_value": None,
                "sample_size": 0,
                "method": "pearson",
                "scatter_summary": [],
                "message": "无数据可用",
            }

        metric_map = {
            "accuracy": lambda e: e.performance_metrics.get("accuracy"),
            "efficiency": lambda e: e.performance_metrics.get("efficiency"),
            "quality_score": lambda e: e.quality_score,
            "duration_ms": lambda e: e.duration_ms,
            "error_count": lambda e: len(e.errors),
            "warning_count": lambda e: len(e.warnings),
        }

        getter1 = metric_map.get(metric1)
        getter2 = metric_map.get(metric2)

        pairs = []
        for exp in experiences:
            v1 = getter1(exp) if getter1 else exp.performance_metrics.get(metric1)
            v2 = getter2(exp) if getter2 else exp.performance_metrics.get(metric2)
            if v1 is not None and v2 is not None and isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                pairs.append((float(v1), float(v2)))

        n = len(pairs)
        if n < 3:
            return {
                "metric1": metric1,
                "metric2": metric2,
                "correlation": 0.0,
                "p_value": None,
                "sample_size": n,
                "method": "pearson",
                "scatter_summary": [],
                "message": "样本量不足，无法计算相关性",
            }

        x_mean = sum(p[0] for p in pairs) / n
        y_mean = sum(p[1] for p in pairs) / n

        numerator = sum((p[0] - x_mean) * (p[1] - y_mean) for p in pairs)
        denom_x = math.sqrt(sum((p[0] - x_mean) ** 2 for p in pairs))
        denom_y = math.sqrt(sum((p[1] - y_mean) ** 2 for p in pairs))

        if denom_x == 0 or denom_y == 0:
            correlation = 0.0
        else:
            correlation = numerator / (denom_x * denom_y)

        correlation = max(-1.0, min(1.0, correlation))

        if abs(correlation) < 0.3:
            strength = "极弱" if abs(correlation) < 0.1 else "弱"
        elif abs(correlation) < 0.5:
            strength = "中等"
        elif abs(correlation) < 0.7:
            strength = "强"
        else:
            strength = "极强"

        direction = "正相关" if correlation > 0 else "负相关" if correlation < 0 else "无相关"

        sorted_pairs = sorted(pairs, key=lambda p: p[0])
        quantiles = []
        if n >= 10:
            for q in [0, 0.25, 0.5, 0.75, 1.0]:
                idx = min(int(q * (n - 1)), n - 1)
                quantiles.append(
                    {
                        "quantile": q,
                        f"{metric1}_value": round(sorted_pairs[idx][0], 4),
                        f"{metric2}_value": round(sorted_pairs[idx][1], 4),
                    }
                )

        return {
            "metric1": metric1,
            "metric2": metric2,
            "correlation": round(correlation, 4),
            "correlation_strength": strength,
            "correlation_direction": direction,
            "sample_size": n,
            "method": "pearson",
            "scatter_summary": quantiles,
            "mean_values": {
                metric1: round(x_mean, 4),
                metric2: round(y_mean, 4),
            },
        }

    def identify_high_performing_combinations(
        self,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        识别高绩效组合

        Args:
            top_n: 返回前N个组合

        Returns:
            高绩效组合列表，按成功率排序
        """
        experiences = self._pool.query({}, limit=10000)

        if not experiences:
            return []

        combos: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "success": 0, "quality_scores": [], "task_type": ""}
        )

        for exp in experiences:
            key = exp.task_type
            combos[key]["total"] += 1
            combos[key]["task_type"] = exp.task_type
            if exp.status == "success":
                combos[key]["success"] += 1
            if exp.quality_score is not None:
                combos[key]["quality_scores"].append(exp.quality_score)

        results = []
        for key, data in combos.items():
            total = data["total"]
            if total < 2:
                continue
            success_rate = data["success"] / total if total > 0 else 0.0
            avg_quality = (
                sum(data["quality_scores"]) / len(data["quality_scores"])
                if data["quality_scores"]
                else None
            )
            combined_score = success_rate * 0.6 + (avg_quality or 0.5) * 0.4

            results.append(
                {
                    "combination": {"task_type": key},
                    "task_type": key,
                    "total_count": total,
                    "success_count": data["success"],
                    "success_rate": round(success_rate, 4),
                    "avg_quality_score": round(avg_quality, 4) if avg_quality else None,
                    "combined_score": round(combined_score, 4),
                }
            )

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results[:top_n]

    def identify_low_performing_combinations(
        self,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        识别低绩效组合

        Args:
            top_n: 返回前N个组合

        Returns:
            低绩效组合列表，按失败率排序
        """
        experiences = self._pool.query({}, limit=10000)

        if not experiences:
            return []

        combos: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "failed": 0, "quality_scores": [], "task_type": ""}
        )

        for exp in experiences:
            key = exp.task_type
            combos[key]["total"] += 1
            combos[key]["task_type"] = exp.task_type
            if exp.status == "failed":
                combos[key]["failed"] += 1
            if exp.quality_score is not None:
                combos[key]["quality_scores"].append(exp.quality_score)

        results = []
        for key, data in combos.items():
            total = data["total"]
            if total < 2:
                continue
            fail_rate = data["failed"] / total if total > 0 else 0.0
            avg_quality = (
                sum(data["quality_scores"]) / len(data["quality_scores"])
                if data["quality_scores"]
                else None
            )
            combined_score = fail_rate * 0.6 + (1.0 - (avg_quality or 0.5)) * 0.4

            results.append(
                {
                    "combination": {"task_type": key},
                    "task_type": key,
                    "total_count": total,
                    "failed_count": data["failed"],
                    "fail_rate": round(fail_rate, 4),
                    "avg_quality_score": round(avg_quality, 4) if avg_quality else None,
                    "combined_score": round(combined_score, 4),
                }
            )

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results[:top_n]


class ExperienceComparator:
    """
    经验对比分析器

    对比不同组别的经验表现差异。
    """

    def __init__(self, pool: ExperienceDataPool):
        """
        初始化对比分析器

        Args:
            pool: 经验数据池
        """
        self._pool = pool
        self._logger = get_logger(f"{__name__}.ExperienceComparator")

    def compare_by_task_type(self, type_a: str, type_b: str) -> ComparisonResult:
        """
        对比两种任务类型的表现

        Args:
            type_a: 任务类型A
            type_b: 任务类型B

        Returns:
            对比分析结果
        """
        exps_a = self._pool.query({"task_type": type_a}, limit=5000)
        exps_b = self._pool.query({"task_type": type_b}, limit=5000)

        metrics_a = self._compute_group_metrics(exps_a)
        metrics_b = self._compute_group_metrics(exps_b)

        differences = {}
        for key in metrics_a:
            if key in metrics_b:
                differences[key] = round(metrics_a[key] - metrics_b[key], 6)

        winner = self._determine_winner(metrics_a, metrics_b)

        summary = self._generate_comparison_summary(
            "task_type",
            type_a,
            type_b,
            metrics_a,
            metrics_b,
            differences,
            winner,
        )

        self._logger.info(
            f"任务类型对比完成: {type_a} vs {type_b}, 优胜方: {winner}"
        )

        return ComparisonResult(
            comparison_type="task_type",
            group_a_name=type_a,
            group_b_name=type_b,
            metrics_a=metrics_a,
            metrics_b=metrics_b,
            differences=differences,
            winner=winner,
            summary=summary,
        )

    def compare_by_time_range(
        self,
        start_a: datetime,
        end_a: datetime,
        start_b: datetime,
        end_b: datetime,
    ) -> ComparisonResult:
        """
        对比两个时间段的表现

        Args:
            start_a: A组开始时间
            end_a: A组结束时间
            start_b: B组开始时间
            end_b: B组结束时间

        Returns:
            对比分析结果
        """
        exps_a = self._pool.query(
            {"time_range": {"start": start_a, "end": end_a}},
            limit=5000,
        )
        exps_b = self._pool.query(
            {"time_range": {"start": start_b, "end": end_b}},
            limit=5000,
        )

        metrics_a = self._compute_group_metrics(exps_a)
        metrics_b = self._compute_group_metrics(exps_b)

        differences = {}
        for key in metrics_a:
            if key in metrics_b:
                differences[key] = round(metrics_a[key] - metrics_b[key], 6)

        winner = self._determine_winner(metrics_a, metrics_b)

        label_a = f"{start_a.strftime('%Y-%m-%d')} ~ {end_a.strftime('%Y-%m-%d')}"
        label_b = f"{start_b.strftime('%Y-%m-%d')} ~ {end_b.strftime('%Y-%m-%d')}"

        summary = self._generate_comparison_summary(
            "time_range",
            label_a,
            label_b,
            metrics_a,
            metrics_b,
            differences,
            winner,
        )

        self._logger.info(
            f"时间段对比完成: {label_a} vs {label_b}, 优胜方: {winner}"
        )

        return ComparisonResult(
            comparison_type="time_range",
            group_a_name=label_a,
            group_b_name=label_b,
            metrics_a=metrics_a,
            metrics_b=metrics_b,
            differences=differences,
            winner=winner,
            summary=summary,
        )

    def compare_by_status(self, status_a: str, status_b: str) -> ComparisonResult:
        """
        对比两种状态的特征

        Args:
            status_a: 状态A
            status_b: 状态B

        Returns:
            对比分析结果
        """
        exps_a = self._pool.query({"status": status_a}, limit=5000)
        exps_b = self._pool.query({"status": status_b}, limit=5000)

        metrics_a = self._compute_group_metrics(exps_a)
        metrics_b = self._compute_group_metrics(exps_b)

        differences = {}
        for key in metrics_a:
            if key in metrics_b:
                differences[key] = round(metrics_a[key] - metrics_b[key], 6)

        if status_a == "success":
            winner = status_a
        elif status_b == "success":
            winner = status_b
        else:
            winner = self._determine_winner(metrics_a, metrics_b)

        summary = self._generate_comparison_summary(
            "status",
            status_a,
            status_b,
            metrics_a,
            metrics_b,
            differences,
            winner,
        )

        self._logger.info(
            f"状态对比完成: {status_a} vs {status_b}, 优胜方: {winner}"
        )

        return ComparisonResult(
            comparison_type="status",
            group_a_name=status_a,
            group_b_name=status_b,
            metrics_a=metrics_a,
            metrics_b=metrics_b,
            differences=differences,
            winner=winner,
            summary=summary,
        )

    def _compute_group_metrics(
        self,
        experiences: List[ExperienceRecord],
    ) -> Dict[str, float]:
        """
        计算一组经验的统计指标

        Args:
            experiences: 经验记录列表

        Returns:
            统计指标字典
        """
        if not experiences:
            return {
                "total_count": 0.0,
                "success_rate": 0.0,
                "fail_rate": 0.0,
                "avg_accuracy": 0.0,
                "avg_efficiency": 0.0,
                "avg_duration_ms": 0.0,
                "avg_quality_score": 0.0,
                "error_rate": 0.0,
                "avg_errors_per_task": 0.0,
                "avg_warnings_per_task": 0.0,
            }

        total = len(experiences)
        success_count = sum(1 for e in experiences if e.status == "success")
        failed_count = sum(1 for e in experiences if e.status == "failed")
        partial_count = sum(1 for e in experiences if e.status == "partial")

        success_rate = success_count / total if total > 0 else 0.0
        fail_rate = failed_count / total if total > 0 else 0.0

        accuracy_vals = [
            e.performance_metrics["accuracy"]
            for e in experiences
            if "accuracy" in e.performance_metrics
        ]
        avg_accuracy = sum(accuracy_vals) / len(accuracy_vals) if accuracy_vals else 0.0

        efficiency_vals = [
            e.performance_metrics["efficiency"]
            for e in experiences
            if "efficiency" in e.performance_metrics
        ]
        avg_efficiency = sum(efficiency_vals) / len(efficiency_vals) if efficiency_vals else 0.0

        durations = [e.duration_ms for e in experiences if e.duration_ms > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        quality_scores = [
            e.quality_score for e in experiences if e.quality_score is not None
        ]
        avg_quality = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )

        total_errors = sum(len(e.errors) for e in experiences)
        tasks_with_errors = sum(1 for e in experiences if len(e.errors) > 0)
        error_rate = tasks_with_errors / total if total > 0 else 0.0
        avg_errors = total_errors / total if total > 0 else 0.0

        total_warnings = sum(len(e.warnings) for e in experiences)
        avg_warnings = total_warnings / total if total > 0 else 0.0

        return {
            "total_count": float(total),
            "success_rate": round(success_rate, 6),
            "fail_rate": round(fail_rate, 6),
            "partial_rate": round(partial_count / total if total > 0 else 0.0, 6),
            "avg_accuracy": round(avg_accuracy, 6),
            "avg_efficiency": round(avg_efficiency, 6),
            "avg_duration_ms": round(avg_duration, 4),
            "avg_quality_score": round(avg_quality, 6),
            "error_rate": round(error_rate, 6),
            "avg_errors_per_task": round(avg_errors, 4),
            "avg_warnings_per_task": round(avg_warnings, 4),
        }

    def _determine_winner(
        self,
        metrics_a: Dict[str, float],
        metrics_b: Dict[str, float],
    ) -> Optional[str]:
        """
        确定优胜方

        Args:
            metrics_a: A组指标
            metrics_b: B组指标

        Returns:
            优胜方名称（A或B）或 None
        """
        if metrics_a["total_count"] == 0 and metrics_b["total_count"] == 0:
            return None
        if metrics_a["total_count"] == 0:
            return "B"
        if metrics_b["total_count"] == 0:
            return "A"

        score_a = (
            metrics_a["success_rate"] * 0.4
            + metrics_a["avg_quality_score"] * 0.3
            + metrics_a["avg_accuracy"] * 0.2
            + metrics_a["avg_efficiency"] * 0.1
        )
        score_b = (
            metrics_b["success_rate"] * 0.4
            + metrics_b["avg_quality_score"] * 0.3
            + metrics_b["avg_accuracy"] * 0.2
            + metrics_b["avg_efficiency"] * 0.1
        )

        if abs(score_a - score_b) < 0.02:
            return None
        return "A" if score_a > score_b else "B"

    def _generate_comparison_summary(
        self,
        comparison_type: str,
        name_a: str,
        name_b: str,
        metrics_a: Dict[str, float],
        metrics_b: Dict[str, float],
        differences: Dict[str, float],
        winner: Optional[str],
    ) -> str:
        """
        生成对比总结描述

        Args:
            comparison_type: 对比类型
            name_a: A组名称
            name_b: B组名称
            metrics_a: A组指标
            metrics_b: B组指标
            differences: 差异值
            winner: 优胜方

        Returns:
            总结描述
        """
        parts = []

        parts.append(
            f"对比 {name_a} 与 {name_b} 的表现："
        )

        if metrics_a["total_count"] == 0 and metrics_b["total_count"] == 0:
            parts.append("两组均无数据。")
            return " ".join(parts)

        parts.append(
            f"A组 {int(metrics_a['total_count'])} 条经验，"
            f"B组 {int(metrics_b['total_count'])} 条经验。"
        )

        success_diff = differences.get("success_rate", 0)
        if success_diff > 0.01:
            parts.append(
                f"A组成功率（{metrics_a['success_rate']:.1%}）"
                f"高于B组（{metrics_b['success_rate']:.1%}），"
                f"差距 {success_diff:.1%}。"
            )
        elif success_diff < -0.01:
            parts.append(
                f"B组成功率（{metrics_b['success_rate']:.1%}）"
                f"高于A组（{metrics_a['success_rate']:.1%}），"
                f"差距 {abs(success_diff):.1%}。"
            )
        else:
            parts.append("两组成功率相近。")

        quality_diff = differences.get("avg_quality_score", 0)
        if abs(quality_diff) > 0.02:
            better = "A组" if quality_diff > 0 else "B组"
            better_quality = metrics_a["avg_quality_score"] if quality_diff > 0 else metrics_b["avg_quality_score"]
            worse_quality = metrics_b["avg_quality_score"] if quality_diff > 0 else metrics_a["avg_quality_score"]
            parts.append(
                f"{better}平均质量分更高（{better_quality:.3f} vs {worse_quality:.3f}）。"
            )

        if winner == "A":
            parts.append(f"综合评估，{name_a}表现更优。")
        elif winner == "B":
            parts.append(f"综合评估，{name_b}表现更优。")
        else:
            parts.append("两组表现相当，无明显优胜方。")

        return " ".join(parts)
