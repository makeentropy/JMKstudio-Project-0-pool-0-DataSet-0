"""
自反思智能体统一入口模块

提供 IntrospectiveAgent 类，作为整个自反思系统的统一入口和门面（Facade），
整合经验数据池、自我评估、错误归因、经验总结、画像生成、技能迭代、
趋势分析、模式挖掘、对比分析和维度空间探测等所有子模块。
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ai_llm_agent_crawler.experience.analytics import (
    ExperienceComparator,
    PatternMiner,
    TrendAnalyzer,
)
from ai_llm_agent_crawler.experience.attribution import (
    ErrorAttributor,
    ExperienceSummarizer,
)
from ai_llm_agent_crawler.experience.iteration import (
    IterationTriggerType,
    SkillIterationEngine,
)
from ai_llm_agent_crawler.experience.models import ExperienceRecord
from ai_llm_agent_crawler.experience.pool import ExperienceDataPool
from ai_llm_agent_crawler.experience.profile import (
    AgentProfile,
    AgentProfileGenerator,
)
from ai_llm_agent_crawler.experience.self_assessment import SelfAssessment
from ai_llm_agent_crawler.experience.snapshot import ExperienceSnapshotManager
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class IntrospectiveAgent:
    """自反思智能体统一入口类

    使用 Facade 模式，整合所有子模块，提供简化的高层 API，
    隐藏内部复杂性，便于外部调用。
    """

    def __init__(
        self,
        agent_name: str = "introspective_agent",
        storage_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化自反思智能体

        Args:
            agent_name: 智能体名称
            storage_path: 存储路径
            config: 配置字典
        """
        self._agent_name = agent_name
        self._storage_path = storage_path
        self._config = config or {}
        self._logger = get_logger(f"{__name__}.IntrospectiveAgent")

        self.pool: ExperienceDataPool = ExperienceDataPool(storage_path)
        self.snapshot_manager: ExperienceSnapshotManager = self._init_snapshot_manager()
        self.self_assessment: SelfAssessment = SelfAssessment(self.pool)
        self.error_attributor: ErrorAttributor = ErrorAttributor(self.pool)
        self.experience_summarizer: ExperienceSummarizer = ExperienceSummarizer(self.pool)
        self.profile_generator: AgentProfileGenerator = AgentProfileGenerator(self.pool)
        self.iteration_engine: SkillIterationEngine = SkillIterationEngine(self.pool)
        self.trend_analyzer: TrendAnalyzer = TrendAnalyzer(self.pool)
        self.pattern_miner: PatternMiner = PatternMiner(self.pool)
        self.comparator: ExperienceComparator = ExperienceComparator(self.pool)
        self.dimension_probe: Optional[Any] = self._init_dimension_probe()

        self._logger.info(
            f"自反思智能体初始化完成: {agent_name}, "
            f"存储路径: {storage_path or '内存模式'}"
        )

    def _init_snapshot_manager(self) -> ExperienceSnapshotManager:
        """初始化快照管理器"""
        if self._storage_path:
            snapshot_dir = str(Path(self._storage_path) / "snapshots")
        else:
            snapshot_dir = tempfile.mkdtemp(prefix="experience_snapshots_")
        return ExperienceSnapshotManager(self.pool, storage_dir=snapshot_dir)

    def _init_dimension_probe(self) -> Optional[Any]:
        """初始化维度空间探针（可选）"""
        if not self._config.get("enable_dimension_probe", False):
            return None
        try:
            from ai_llm_agent_crawler.dimension.probe import DimensionSpaceProbe

            probe_config = self._config.get("dimension_probe_config", {})
            return DimensionSpaceProbe(config=probe_config)
        except ImportError:
            self._logger.warning("维度空间探针模块不可用，跳过初始化")
            return None

    def record_experience(
        self,
        task_id: str,
        task_type: str,
        status: str,
        duration_ms: float,
        **kwargs,
    ) -> ExperienceRecord:
        """
        记录一条经验（简化接口）

        自动创建 ExperienceRecord 并添加到数据池，自动触发评估和总结。

        Args:
            task_id: 任务ID
            task_type: 任务类型
            status: 任务状态
            duration_ms: 执行耗时（毫秒）
            **kwargs: 其他参数，传递给 ExperienceRecord

        Returns:
            经验记录
        """
        record = ExperienceRecord(
            task_id=task_id,
            task_type=task_type,
            task_name=kwargs.pop("task_name", task_id),
            status=status,
            duration_ms=duration_ms,
            **kwargs,
        )

        self.pool.add_record(record)
        self.pool.compute_quality_scores()

        self._logger.debug(
            f"记录经验: {record.experience_id}, 任务: {task_id}, 状态: {status}"
        )

        return record

    def self_reflect(self, experience_id: Optional[str] = None) -> Dict[str, Any]:
        """
        执行一次完整的自我反思

        流程：自我评估 → 错误归因 → 经验总结 → 更新画像

        Args:
            experience_id: 指定单条经验ID，None 表示对全部经验反思

        Returns:
            反思结果摘要
        """
        filters = {}
        if experience_id:
            record = self.pool.get_record(experience_id)
            if not record:
                return {
                    "success": False,
                    "error": f"经验记录不存在: {experience_id}",
                    "reflection_time": datetime.now().isoformat(),
                }
            filters = {"task_type": record.task_type}

        assessment_result = self.self_assessment.assess(filters=filters if experience_id else None)

        error_stats = self.error_attributor.get_error_statistics(
            filters=filters if experience_id else None
        )

        heuristics = self.experience_summarizer.extract_heuristics(min_frequency=2)

        profile = self.profile_generator.generate_profile(self._agent_name)

        result = {
            "success": True,
            "reflection_time": datetime.now().isoformat(),
            "agent_name": self._agent_name,
            "experience_count": assessment_result.experience_count,
            "self_assessment": {
                "overall_score": assessment_result.overall_score,
                "summary": assessment_result.summary,
                "strengths": assessment_result.strengths,
                "weaknesses": assessment_result.weaknesses,
                "recommendations": assessment_result.recommendations,
                "dimensions": {
                    k: {"score": v.score, "confidence": v.confidence}
                    for k, v in assessment_result.dimensions.items()
                },
            },
            "error_statistics": error_stats,
            "heuristics_count": len(heuristics),
            "top_heuristics": [
                {
                    "heuristic_id": h.heuristic_id,
                    "name": h.name,
                    "pattern_type": h.pattern_type,
                    "frequency": h.frequency,
                    "confidence": h.confidence,
                }
                for h in heuristics[:5]
            ],
            "profile_summary": self.profile_generator.get_profile_summary(profile),
        }

        self._logger.info(
            f"自我反思完成，经验数: {assessment_result.experience_count}, "
            f"综合评分: {assessment_result.overall_score:.3f}"
        )

        return result

    def get_self_profile(self) -> AgentProfile:
        """
        获取当前自我认知画像

        自动重新生成。

        Returns:
            AgentProfile 完整画像
        """
        profile = self.profile_generator.generate_profile(self._agent_name)
        self._logger.debug(f"获取自我画像，经验数: {profile.experience_count}")
        return profile

    def analyze_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        获取趋势分析报告（简化接口）

        Args:
            days: 分析的天数范围

        Returns:
            趋势摘要
        """
        result = self.trend_analyzer.analyze_trend(days=days)

        summary = {
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "total_points": result.total_points,
            "overall_trend": result.overall_trend,
            "trend_slope": result.trend_slope,
            "dimension_trends": result.dimension_trends,
            "inflection_point_count": len(result.inflection_points),
            "key_findings": result.key_findings,
            "prediction": result.prediction,
        }

        self._logger.debug(f"趋势分析完成，趋势: {result.overall_trend}")
        return summary

    def mine_patterns(self, min_frequency: int = 3) -> List[Dict[str, Any]]:
        """
        挖掘经验模式（简化接口）

        Args:
            min_frequency: 最小频率阈值

        Returns:
            模式列表
        """
        patterns = self.pattern_miner.mine_patterns(min_frequency=min_frequency)
        self._logger.debug(f"模式挖掘完成，共 {len(patterns)} 个模式")
        return patterns

    def optimize_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        对指定技能执行一次迭代优化

        Args:
            skill_id: 技能ID

        Returns:
            优化结果摘要
        """
        iteration_record = self.iteration_engine.run_iteration(
            skill_id=skill_id,
            trigger_type=IterationTriggerType.MANUAL,
        )

        if iteration_record is None:
            return {
                "success": False,
                "skill_id": skill_id,
                "message": "无法执行迭代优化，可能经验数据不足或已达最大无改进迭代次数",
            }

        result = {
            "success": True,
            "skill_id": skill_id,
            "iteration_id": iteration_record.iteration_id,
            "skill_name": iteration_record.skill_name,
            "trigger_type": iteration_record.trigger_type,
            "strategy": iteration_record.strategy,
            "original_version": iteration_record.original_version,
            "optimized_version": iteration_record.optimized_version,
            "overall_improvement": iteration_record.overall_improvement,
            "improvements": iteration_record.improvements,
            "before_metrics": iteration_record.before_metrics,
            "after_metrics": iteration_record.after_metrics,
            "changes": iteration_record.changes,
            "is_approved": iteration_record.is_approved,
            "is_applied": iteration_record.is_applied,
            "reason": iteration_record.reason,
        }

        self._logger.info(
            f"技能优化完成: {skill_id}, 改进率: {iteration_record.overall_improvement:.1%}"
        )

        return result

    def create_snapshot(self, name: str = "") -> str:
        """
        创建经验池快照（简化接口）

        Args:
            name: 快照名称

        Returns:
            快照ID
        """
        snapshot = self.snapshot_manager.create_snapshot(name=name)
        self._logger.info(f"创建快照: {snapshot.snapshot_id}, 记录数: {snapshot.record_count}")
        return snapshot.snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        恢复快照

        Args:
            snapshot_id: 快照ID

        Returns:
            是否成功
        """
        success = self.snapshot_manager.restore_snapshot(snapshot_id)
        if success:
            self._logger.info(f"恢复快照成功: {snapshot_id}")
        else:
            self._logger.warning(f"恢复快照失败: {snapshot_id}")
        return success

    def export_experience(self, format: str = "json") -> str:
        """
        导出经验数据

        支持 json/csv 格式。

        Args:
            format: 导出格式，支持 "json" 或 "csv"

        Returns:
            导出的文件路径或数据字符串
        """
        format_lower = format.lower()

        if format_lower == "json":
            records = self.pool.query({}, limit=100000)
            records_list = [record.to_dict() for record in records]
            result = json.dumps(records_list, ensure_ascii=False, indent=2)
            self._logger.debug(f"导出经验数据 (JSON), 共 {len(records)} 条")
            return result

        elif format_lower == "csv":
            df = self.pool.export_to_dataframe()
            if df.empty:
                return ""
            result = df.to_csv(index=False)
            self._logger.debug(f"导出经验数据 (CSV), 共 {len(df)} 条")
            return result

        else:
            raise ValueError(f"不支持的导出格式: {format}，仅支持 json/csv")

    def get_status(self) -> Dict[str, Any]:
        """
        获取智能体运行状态

        包含：经验数量、快照数量、画像评分、最近趋势等。

        Returns:
            状态信息字典
        """
        stats = self.pool.get_statistics()
        snapshots = self.snapshot_manager.list_snapshots()
        profile = self.profile_generator.generate_profile(self._agent_name)
        trend = self.trend_analyzer.analyze_trend(days=30)

        status = {
            "agent_name": self._agent_name,
            "status_time": datetime.now().isoformat(),
            "experience": {
                "total_records": stats["total_records"],
                "by_task_type": stats["by_task_type"],
                "by_status": stats["by_status"],
                "average_quality_score": stats["average_quality_score"],
                "avg_duration_ms": stats["avg_duration_ms"],
                "total_errors": stats["total_errors"],
                "total_warnings": stats["total_warnings"],
            },
            "snapshots": {
                "count": len(snapshots),
                "latest": snapshots[0].snapshot_id if snapshots else None,
                "latest_version": snapshots[0].version if snapshots else None,
            },
            "profile": {
                "overall_score": profile.overall_score,
                "experience_count": profile.experience_count,
                "recent_trend": profile.recent_trend,
                "strengths_count": len(profile.strengths),
                "weaknesses_count": len(profile.weaknesses),
                "skill_domains_count": len(profile.skill_domains),
                "knowledge_certainty": profile.knowledge_boundary.overall_certainty,
            },
            "trend": {
                "overall_trend": trend.overall_trend,
                "trend_slope": trend.trend_slope,
                "total_points": trend.total_points,
                "inflection_point_count": len(trend.inflection_points),
            },
            "dimension_probe_enabled": self.dimension_probe is not None,
        }

        self._logger.debug(f"获取状态，总经验数: {stats['total_records']}")
        return status

    def introspect_deep(self) -> Dict[str, Any]:
        """
        深度自省：执行完整的分析流程

        包括：画像 + 趋势 + 模式 + 迭代建议。

        Returns:
            完整的自省报告
        """
        profile = self.profile_generator.generate_profile(self._agent_name)
        trend = self.trend_analyzer.analyze_trend(days=30)
        patterns = self.pattern_miner.mine_patterns(min_frequency=2)
        top_insights = self.experience_summarizer.get_top_insights(top_n=5)
        error_stats = self.error_attributor.get_error_statistics()

        iteration_suggestions = []
        for domain in profile.skill_domains:
            if domain.success_rate < 0.7 and domain.task_count >= 3:
                iteration_suggestions.append(
                    {
                        "skill_id": domain.domain_name,
                        "reason": f"成功率偏低 ({domain.success_rate:.1%})，建议优化",
                        "priority": "high" if domain.success_rate < 0.5 else "medium",
                    }
                )

        report = {
            "introspection_time": datetime.now().isoformat(),
            "agent_name": self._agent_name,
            "profile": self.profile_generator.get_profile_summary(profile),
            "trend": {
                "overall_trend": trend.overall_trend,
                "trend_slope": trend.trend_slope,
                "key_findings": trend.key_findings,
                "prediction": trend.prediction,
            },
            "patterns": {
                "total_count": len(patterns),
                "top_patterns": patterns[:10],
            },
            "top_insights": top_insights,
            "error_statistics": error_stats,
            "iteration_suggestions": iteration_suggestions,
            "overall_summary": self._generate_deep_summary(profile, trend, patterns),
        }

        self._logger.info(
            f"深度自省完成，经验数: {profile.experience_count}, "
            f"综合评分: {profile.overall_score:.3f}"
        )

        return report

    def _generate_deep_summary(
        self,
        profile: AgentProfile,
        trend: Any,
        patterns: List[Dict[str, Any]],
    ) -> str:
        """生成深度自省摘要"""
        parts = []

        parts.append(
            f"智能体 '{self._agent_name}' 基于 {profile.experience_count} 条经验的深度自省报告。"
        )
        parts.append(
            f"综合能力评分为 {profile.overall_score:.1%}，整体表现"
            f"{'优秀' if profile.overall_score >= 0.8 else '良好' if profile.overall_score >= 0.6 else '一般'}。"
        )

        if trend.overall_trend == "improving":
            parts.append("近期能力呈上升趋势，持续优化效果明显。")
        elif trend.overall_trend == "declining":
            parts.append("近期能力呈下降趋势，需要关注并采取改进措施。")
        else:
            parts.append("近期能力相对稳定，建议寻找新的突破点。")

        if patterns:
            parts.append(f"挖掘到 {len(patterns)} 个经验模式，可为后续优化提供参考。")

        if profile.weaknesses:
            parts.append(f"主要薄弱点: {profile.weaknesses[0]}")

        return " ".join(parts)

    def dimension_probe_dataset(
        self,
        df: pd.DataFrame,
        dataset_name: str = "dataset",
    ) -> Optional[Dict[str, Any]]:
        """
        对数据集进行维度空间探测

        如果配置了 dimension_probe 则执行，否则返回 None。

        Args:
            df: 要探测的 DataFrame
            dataset_name: 数据集名称

        Returns:
            探测结果摘要，未配置探针时返回 None
        """
        if self.dimension_probe is None:
            self._logger.debug("维度空间探针未配置，跳过探测")
            return None

        report = self.dimension_probe.probe(df, dataset_name=dataset_name)
        summary = self.dimension_probe.get_probe_summary(report)

        self._logger.info(
            f"维度空间探测完成: {dataset_name}, "
            f"健康度: {report.overall_health_score:.2f}"
        )

        return summary
