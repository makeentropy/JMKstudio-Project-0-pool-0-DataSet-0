"""
技能自迭代闭环模块

提供技能的自动迭代优化功能，包括触发检测、经验分析、优化方案生成、
版本创建、测试验证、效果评估、应用与回滚等完整闭环管理。
"""

import hashlib
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.experience.pool import ExperienceDataPool
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


def _generate_iteration_id() -> str:
    """生成迭代记录唯一ID

    Returns:
        迭代记录ID，格式为 iter_ + 时间戳 + 8位hash
    """
    timestamp = str(int(time.time() * 1000))
    random_hash = hashlib.md5(uuid.uuid4().hex.encode()).hexdigest()[:8]
    return f"iter_{timestamp}_{random_hash}"


class IterationTriggerType(str, Enum):
    """迭代触发类型枚举"""

    PERFORMANCE_DEGRADATION = "performance_degradation"
    EXPERIENCE_ACCUMULATION = "experience_accumulation"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class OptimizationStrategyType(str, Enum):
    """优化策略类型枚举"""

    RULE_TUNING = "rule_tuning"
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    CODE_REFINEMENT = "code_refinement"
    HYBRID = "hybrid"


class IterationRecord(BaseModel):
    """迭代记录模型"""

    iteration_id: str = Field(
        default_factory=_generate_iteration_id,
        description="迭代记录唯一ID",
    )
    skill_id: str = Field(..., description="技能ID")
    skill_name: str = Field(..., description="技能名称")
    trigger_type: IterationTriggerType = Field(..., description="触发类型")
    strategy: OptimizationStrategyType = Field(..., description="优化策略")
    original_version: str = Field(..., description="原始版本")
    optimized_version: str = Field(..., description="优化后版本")

    reason: str = Field(default="", description="迭代原因")
    changes: List[str] = Field(default_factory=list, description="变更列表")
    improvements: Dict[str, float] = Field(
        default_factory=dict,
        description="改进指标：accuracy, efficiency, success_rate等的变化值",
    )

    before_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="优化前指标",
    )
    after_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="优化后指标",
    )
    overall_improvement: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="综合改进率 0-1",
    )
    is_approved: bool = Field(default=False, description="是否已批准")
    is_applied: bool = Field(default=False, description="是否已应用")
    rollback_available: bool = Field(default=True, description="是否可回滚")

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    applied_at: Optional[datetime] = Field(default=None, description="应用时间")
    test_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="测试结果",
    )

    class Config:
        use_enum_values = True


class IterationConfig(BaseModel):
    """迭代配置"""

    min_experience_count: int = Field(
        default=10,
        description="最小经验数量触发",
    )
    performance_degradation_threshold: float = Field(
        default=0.1,
        description="性能下降阈值",
    )
    auto_apply: bool = Field(default=False, description="是否自动应用")
    require_approval: bool = Field(default=True, description="是否需要审批")
    rollback_enabled: bool = Field(default=True, description="是否启用回滚")
    default_strategy: OptimizationStrategyType = Field(
        default=OptimizationStrategyType.HYBRID,
        description="默认优化策略",
    )
    max_iterations_without_improvement: int = Field(
        default=3,
        description="无改进最大迭代次数",
    )
    test_sample_size: int = Field(default=20, description="测试样本大小")


class SkillIterationEngine:
    """技能迭代引擎类

    管理技能的完整迭代优化闭环，包括触发检测、经验分析、策略生成、
    版本优化、测试验证、效果评估、应用与回滚等功能。
    """

    def __init__(
        self,
        experience_pool: ExperienceDataPool,
        config: Optional[IterationConfig] = None,
    ):
        """
        初始化技能迭代引擎

        Args:
            experience_pool: 经验数据池
            config: 迭代配置
        """
        self._pool = experience_pool
        self._config = config or IterationConfig()
        self._logger = get_logger(f"{__name__}.SkillIterationEngine")
        self._iterations: Dict[str, IterationRecord] = {}
        self._skill_versions: Dict[str, List[str]] = {}
        self._skill_current_version: Dict[str, str] = {}
        self._iterations_without_improvement: Dict[str, int] = {}

    def check_trigger(
        self, skill_id: str
    ) -> Tuple[bool, Optional[IterationTriggerType]]:
        """
        检查是否触发迭代优化

        检查条件：性能下降？经验积累足够？

        Args:
            skill_id: 技能ID

        Returns:
            元组 (是否触发, 触发类型)
        """
        experiences = self._get_skill_experiences(skill_id)
        exp_count = len(experiences)

        if exp_count == 0:
            return False, None

        if exp_count >= self._config.min_experience_count:
            iterations = self.get_iteration_history(skill_id)
            if not iterations:
                return True, IterationTriggerType.EXPERIENCE_ACCUMULATION
            latest_iteration = iterations[0]
            if latest_iteration.is_applied:
                return True, IterationTriggerType.EXPERIENCE_ACCUMULATION

        if exp_count >= 5:
            performance_degraded = self._check_performance_degradation(experiences)
            if performance_degraded:
                return True, IterationTriggerType.PERFORMANCE_DEGRADATION

        return False, None

    def run_iteration(
        self,
        skill_id: str,
        trigger_type: IterationTriggerType = IterationTriggerType.MANUAL,
    ) -> Optional[IterationRecord]:
        """
        执行一次完整的迭代优化

        流程：分析经验 → 生成优化方案 → 创建新版本 → 运行测试 → 评估效果 → （可选）应用

        Args:
            skill_id: 技能ID
            trigger_type: 触发类型

        Returns:
            迭代记录，无法执行时返回None
        """
        no_improve_count = self._iterations_without_improvement.get(skill_id, 0)
        if no_improve_count >= self._config.max_iterations_without_improvement:
            self._logger.warning(
                f"技能 {skill_id} 已连续 {no_improve_count} 次迭代无改进，停止迭代"
            )
            return None

        analysis = self._analyze_experiences(skill_id)
        if not analysis.get("experiences_available", False):
            self._logger.warning(f"技能 {skill_id} 没有足够的经验数据进行迭代")
            return None

        strategy, changes = self._generate_optimization_plan(analysis)
        version_info = self._create_optimized_version(skill_id, strategy, changes)

        skill_name = analysis.get("skill_name", skill_id)
        original_version = self._get_current_version(skill_id)
        optimized_version = version_info["version"]

        test_data = self._prepare_test_data(skill_id)
        before_metrics = self._run_tests(skill_id, original_version, test_data)
        after_metrics = self._run_tests(skill_id, optimized_version, test_data)

        overall_improvement = self._evaluate_improvement(before_metrics, after_metrics)

        improvements = {}
        for key in after_metrics:
            if key in before_metrics:
                improvements[key] = after_metrics[key] - before_metrics[key]

        reason = self._generate_iteration_reason(trigger_type, analysis)

        record = IterationRecord(
            skill_id=skill_id,
            skill_name=skill_name,
            trigger_type=trigger_type,
            strategy=strategy,
            original_version=original_version,
            optimized_version=optimized_version,
            reason=reason,
            changes=changes,
            improvements=improvements,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            overall_improvement=overall_improvement,
            rollback_available=self._config.rollback_enabled,
            test_results={"test_sample_size": len(test_data)},
        )

        if overall_improvement <= 0:
            self._iterations_without_improvement[skill_id] = no_improve_count + 1
        else:
            self._iterations_without_improvement[skill_id] = 0

        if self._config.auto_apply and not self._config.require_approval:
            record.is_approved = True
            self._apply_record(record)

        self._iterations[record.iteration_id] = record

        if skill_id not in self._skill_versions:
            self._skill_versions[skill_id] = []
        if optimized_version not in self._skill_versions[skill_id]:
            self._skill_versions[skill_id].append(optimized_version)

        self._logger.info(
            f"技能 {skill_id} 迭代完成，改进率: {overall_improvement:.1%}"
        )

        return record

    def _analyze_experiences(self, skill_id: str) -> Dict[str, Any]:
        """
        分析该技能相关的经验数据

        提取：性能趋势、常见错误、成功模式、薄弱点

        Args:
            skill_id: 技能ID

        Returns:
            分析结果字典
        """
        experiences = self._get_skill_experiences(skill_id)

        if not experiences:
            return {
                "experiences_available": False,
                "skill_name": skill_id,
                "total_count": 0,
            }

        total_count = len(experiences)
        success_count = sum(1 for e in experiences if e.status == "success")
        failed_count = sum(1 for e in experiences if e.status == "failed")
        partial_count = sum(1 for e in experiences if e.status == "partial")

        success_rate = success_count / total_count if total_count > 0 else 0.0

        all_errors = []
        for e in experiences:
            all_errors.extend(e.errors)

        error_frequency: Dict[str, int] = {}
        for err in all_errors:
            error_frequency[err] = error_frequency.get(err, 0) + 1

        common_errors = sorted(
            error_frequency.items(), key=lambda x: x[1], reverse=True
        )[:5]

        accuracy_values = [
            e.performance_metrics.get("accuracy", 0.0)
            for e in experiences
            if "accuracy" in e.performance_metrics
        ]
        avg_accuracy = (
            sum(accuracy_values) / len(accuracy_values) if accuracy_values else 0.0
        )

        efficiency_values = [
            e.performance_metrics.get("efficiency", 0.0)
            for e in experiences
            if "efficiency" in e.performance_metrics
        ]
        avg_efficiency = (
            sum(efficiency_values) / len(efficiency_values)
            if efficiency_values
            else 0.0
        )

        durations = [e.duration_ms for e in experiences if e.duration_ms > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        success_experiences = [e for e in experiences if e.status == "success"]
        success_patterns = self._extract_success_patterns(success_experiences)

        weak_points = self._identify_weak_points(
            experiences, avg_accuracy, avg_efficiency, common_errors
        )

        performance_trend = self._analyze_performance_trend(experiences)

        return {
            "experiences_available": True,
            "skill_name": skill_id,
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "partial_count": partial_count,
            "success_rate": success_rate,
            "avg_accuracy": avg_accuracy,
            "avg_efficiency": avg_efficiency,
            "avg_duration": avg_duration,
            "common_errors": common_errors,
            "success_patterns": success_patterns,
            "weak_points": weak_points,
            "performance_trend": performance_trend,
        }

    def _generate_optimization_plan(
        self, analysis: Dict[str, Any]
    ) -> Tuple[OptimizationStrategyType, List[str]]:
        """
        基于分析结果生成优化方案

        选择最优策略，列出具体变更点

        Args:
            analysis: 经验分析结果

        Returns:
            元组 (策略类型, 变更列表)
        """
        if not analysis.get("experiences_available", False):
            return self._config.default_strategy, []

        changes: List[str] = []
        strategy_scores: Dict[OptimizationStrategyType, float] = {
            OptimizationStrategyType.RULE_TUNING: 0.0,
            OptimizationStrategyType.PARAMETER_ADJUSTMENT: 0.0,
            OptimizationStrategyType.CODE_REFINEMENT: 0.0,
        }

        common_errors = analysis.get("common_errors", [])
        if common_errors:
            strategy_scores[OptimizationStrategyType.RULE_TUNING] += 0.3
            changes.append(f"针对常见错误增加异常处理规则")
            for err, count in common_errors[:3]:
                changes.append(f"优化错误处理: {err} (出现 {count} 次)")

        avg_accuracy = analysis.get("avg_accuracy", 0.0)
        if avg_accuracy < 0.7:
            strategy_scores[OptimizationStrategyType.PARAMETER_ADJUSTMENT] += 0.4
            changes.append("调整准确性相关参数以提升准确率")

        avg_efficiency = analysis.get("avg_efficiency", 0.0)
        if avg_efficiency < 0.6:
            strategy_scores[OptimizationStrategyType.PARAMETER_ADJUSTMENT] += 0.3
            changes.append("优化性能参数以提升执行效率")

        weak_points = analysis.get("weak_points", [])
        if weak_points:
            strategy_scores[OptimizationStrategyType.CODE_REFINEMENT] += 0.2
            for wp in weak_points[:2]:
                changes.append(f"代码优化: 改进{wp}")

        success_rate = analysis.get("success_rate", 0.0)
        if success_rate < 0.6:
            strategy_scores[OptimizationStrategyType.CODE_REFINEMENT] += 0.3
            changes.append("重构核心逻辑以提升成功率")

        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])

        if best_strategy[1] < 0.2:
            selected_strategy = self._config.default_strategy
            changes.append("综合优化: 多维度混合策略提升")
        else:
            selected_strategy = best_strategy[0]

        if not changes:
            changes.append("常规优化调整")

        return selected_strategy, changes

    def _create_optimized_version(
        self,
        skill_id: str,
        strategy: OptimizationStrategyType,
        changes: List[str],
    ) -> Dict[str, Any]:
        """
        创建优化后的技能版本（模拟版，不实际修改skill_engine中的skill）

        生成新版本号，模拟优化后的指标

        Args:
            skill_id: 技能ID
            strategy: 优化策略
            changes: 变更列表

        Returns:
            新版本信息和预期指标
        """
        current_version = self._get_current_version(skill_id)
        version_parts = current_version.split(".")

        try:
            major = int(version_parts[0]) if len(version_parts) > 0 else 1
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
            patch = int(version_parts[2]) if len(version_parts) > 2 else 0
        except (ValueError, IndexError):
            major, minor, patch = 1, 0, 0

        if strategy == OptimizationStrategyType.CODE_REFINEMENT:
            major += 1
            minor = 0
            patch = 0
        elif strategy == OptimizationStrategyType.RULE_TUNING:
            minor += 1
            patch = 0
        else:
            patch += 1

        new_version = f"{major}.{minor}.{patch}"

        base_improvement = 0.05 + len(changes) * 0.02
        strategy_boost = {
            OptimizationStrategyType.RULE_TUNING: 0.02,
            OptimizationStrategyType.PARAMETER_ADJUSTMENT: 0.03,
            OptimizationStrategyType.CODE_REFINEMENT: 0.05,
            OptimizationStrategyType.HYBRID: 0.04,
        }
        total_improvement = min(
            base_improvement + strategy_boost.get(strategy, 0.0), 0.3
        )

        expected_metrics = {
            "accuracy_improvement": total_improvement * 0.6,
            "efficiency_improvement": total_improvement * 0.4,
            "success_rate_improvement": total_improvement * 0.5,
        }

        return {
            "version": new_version,
            "strategy": strategy,
            "changes": changes,
            "expected_metrics": expected_metrics,
            "created_at": datetime.now().isoformat(),
        }

    def _run_tests(
        self,
        skill_id: str,
        version: str,
        test_data: List[Dict],
    ) -> Dict[str, float]:
        """
        运行测试验证优化效果

        使用测试样本数据进行模拟测试

        Args:
            skill_id: 技能ID
            version: 版本号
            test_data: 测试数据列表

        Returns:
            测试指标（accuracy, efficiency, success_rate）
        """
        if not test_data:
            return {
                "accuracy": 0.5,
                "efficiency": 0.5,
                "success_rate": 0.5,
            }

        version_factor = self._get_version_performance_factor(skill_id, version)

        total_accuracy = 0.0
        total_efficiency = 0.0
        success_count = 0

        for test_item in test_data:
            base_accuracy = test_item.get("expected_accuracy", 0.7)
            base_efficiency = test_item.get("expected_efficiency", 0.6)

            accuracy = min(1.0, max(0.0, base_accuracy * version_factor))
            efficiency = min(1.0, max(0.0, base_efficiency * version_factor))

            total_accuracy += accuracy
            total_efficiency += efficiency

            if accuracy > 0.6 and efficiency > 0.5:
                success_count += 1

        test_count = len(test_data)
        avg_accuracy = total_accuracy / test_count if test_count > 0 else 0.0
        avg_efficiency = total_efficiency / test_count if test_count > 0 else 0.0
        success_rate = success_count / test_count if test_count > 0 else 0.0

        return {
            "accuracy": round(avg_accuracy, 4),
            "efficiency": round(avg_efficiency, 4),
            "success_rate": round(success_rate, 4),
        }

    def _evaluate_improvement(
        self,
        before: Dict[str, float],
        after: Dict[str, float],
    ) -> float:
        """
        评估改进程度

        加权计算综合改进率

        Args:
            before: 优化前指标
            after: 优化后指标

        Returns:
            0-1 的改进率（0表示无改进，1表示完美）
        """
        weights = {
            "accuracy": 0.4,
            "efficiency": 0.3,
            "success_rate": 0.3,
        }

        total_weight = 0.0
        weighted_improvement = 0.0

        for key, weight in weights.items():
            if key in before and key in after:
                before_val = before[key]
                after_val = after[key]

                if before_val < 0.001:
                    relative_improvement = min(after_val, 1.0)
                else:
                    relative_improvement = (after_val - before_val) / before_val
                    relative_improvement = max(0.0, min(relative_improvement, 1.0))

                weighted_improvement += relative_improvement * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0

        overall = weighted_improvement / total_weight
        return max(0.0, min(1.0, overall))

    def apply_iteration(self, iteration_id: str) -> bool:
        """
        应用迭代（将优化版本设为活跃版本）

        Args:
            iteration_id: 迭代记录ID

        Returns:
            是否成功
        """
        record = self._iterations.get(iteration_id)
        if not record:
            self._logger.warning(f"迭代记录不存在: {iteration_id}")
            return False

        if record.is_applied:
            self._logger.info(f"迭代已应用: {iteration_id}")
            return True

        if self._config.require_approval and not record.is_approved:
            self._logger.warning(f"迭代未批准，无法应用: {iteration_id}")
            return False

        return self._apply_record(record)

    def _apply_record(self, record: IterationRecord) -> bool:
        """应用迭代记录"""
        skill_id = record.skill_id
        self._skill_current_version[skill_id] = record.optimized_version
        record.is_applied = True
        record.applied_at = datetime.now()

        if skill_id not in self._skill_versions:
            self._skill_versions[skill_id] = []
        if record.optimized_version not in self._skill_versions[skill_id]:
            self._skill_versions[skill_id].append(record.optimized_version)

        self._logger.info(
            f"技能 {skill_id} 已应用版本 {record.optimized_version} "
            f"(迭代: {record.iteration_id})"
        )
        return True

    def rollback(self, skill_id: str) -> bool:
        """
        回滚到上一个版本

        Args:
            skill_id: 技能ID

        Returns:
            是否成功
        """
        if not self._config.rollback_enabled:
            self._logger.warning(f"回滚功能未启用，技能: {skill_id}")
            return False

        versions = self._skill_versions.get(skill_id, [])
        current_version = self._skill_current_version.get(skill_id)

        if not current_version or len(versions) < 2:
            self._logger.warning(f"技能 {skill_id} 无可回滚版本")
            return False

        current_index = versions.index(current_version) if current_version in versions else -1
        if current_index <= 0:
            self._logger.warning(f"技能 {skill_id} 已是最早版本，无法回滚")
            return False

        previous_version = versions[current_index - 1]
        self._skill_current_version[skill_id] = previous_version

        self._logger.info(
            f"技能 {skill_id} 已回滚到版本 {previous_version}"
        )
        return True

    def get_iteration_history(self, skill_id: str) -> List[IterationRecord]:
        """
        获取技能的迭代历史

        按时间倒序排列

        Args:
            skill_id: 技能ID

        Returns:
            迭代记录列表
        """
        history = [
            record
            for record in self._iterations.values()
            if record.skill_id == skill_id
        ]
        history.sort(key=lambda r: r.created_at, reverse=True)
        return history

    def get_iteration(self, iteration_id: str) -> Optional[IterationRecord]:
        """
        获取单条迭代记录

        Args:
            iteration_id: 迭代记录ID

        Returns:
            迭代记录，不存在则返回None
        """
        return self._iterations.get(iteration_id)

    def get_evolution_trajectory(self, skill_id: str) -> Dict[str, Any]:
        """
        获取技能的进化轨迹

        返回：版本列表、性能曲线、关键迭代点

        Args:
            skill_id: 技能ID

        Returns:
            进化轨迹信息
        """
        iterations = self.get_iteration_history(skill_id)
        iterations.reverse()

        versions = []
        performance_curve = []
        key_iterations = []

        if iterations:
            first_original = iterations[0].original_version
            versions.append(first_original)
            performance_curve.append(
                {
                    "version": first_original,
                    "accuracy": iterations[0].before_metrics.get("accuracy", 0.5),
                    "efficiency": iterations[0].before_metrics.get("efficiency", 0.5),
                    "success_rate": iterations[0].before_metrics.get("success_rate", 0.5),
                }
            )
        else:
            current_version = self._get_current_version(skill_id)
            versions.append(current_version)
            performance_curve.append(
                {
                    "version": current_version,
                    "accuracy": 0.5,
                    "efficiency": 0.5,
                    "success_rate": 0.5,
                }
            )

        for record in iterations:
            if record.optimized_version not in versions:
                versions.append(record.optimized_version)

            perf_point = {
                "version": record.optimized_version,
                "accuracy": record.after_metrics.get("accuracy", 0.0),
                "efficiency": record.after_metrics.get("efficiency", 0.0),
                "success_rate": record.after_metrics.get("success_rate", 0.0),
                "overall_improvement": record.overall_improvement,
            }
            performance_curve.append(perf_point)

            if record.overall_improvement > 0.1:
                key_iterations.append(
                    {
                        "iteration_id": record.iteration_id,
                        "version": record.optimized_version,
                        "improvement": record.overall_improvement,
                        "strategy": record.strategy,
                        "reason": record.reason,
                    }
                )

        return {
            "skill_id": skill_id,
            "versions": versions,
            "version_count": len(versions),
            "performance_curve": performance_curve,
            "key_iterations": key_iterations,
            "current_version": self._get_current_version(skill_id),
            "total_iterations": len(iterations),
        }

    def _get_skill_experiences(self, skill_id: str) -> List:
        """获取技能相关的经验记录"""
        filters = {"task_type": "skill_usage"}
        all_experiences = self._pool.query(filters, limit=1000)

        skill_experiences = []
        for exp in all_experiences:
            if exp.metadata.get("skill_id") == skill_id:
                skill_experiences.append(exp)

        if not skill_experiences:
            skill_experiences = self._pool.query({}, limit=1000)

        return skill_experiences

    def _check_performance_degradation(self, experiences: List) -> bool:
        """检查性能是否下降"""
        if len(experiences) < 5:
            return False

        sorted_exps = sorted(experiences, key=lambda e: e.timestamp)
        mid_point = len(sorted_exps) // 2

        first_half = sorted_exps[:mid_point]
        second_half = sorted_exps[mid_point:]

        first_quality = self._avg_quality(first_half)
        second_quality = self._avg_quality(second_half)

        if first_quality <= 0:
            return False

        degradation = (first_quality - second_quality) / first_quality
        return degradation >= self._config.performance_degradation_threshold

    def _avg_quality(self, experiences: List) -> float:
        """计算平均质量分"""
        if not experiences:
            return 0.0
        scores = [
            e.quality_score for e in experiences if e.quality_score is not None
        ]
        if not scores:
            status_scores = {"success": 1.0, "partial": 0.6, "failed": 0.2, "skipped": 0.0}
            scores = [status_scores.get(e.status, 0.0) for e in experiences]
        return sum(scores) / len(scores) if scores else 0.0

    def _get_current_version(self, skill_id: str) -> str:
        """获取技能当前版本"""
        if skill_id in self._skill_current_version:
            return self._skill_current_version[skill_id]
        return "1.0.0"

    def _get_version_performance_factor(self, skill_id: str, version: str) -> float:
        """获取版本性能因子（模拟）"""
        iterations = self.get_iteration_history(skill_id)
        base_factor = 1.0

        for record in iterations:
            if record.optimized_version == version and record.is_applied:
                base_factor = 1.0 + record.overall_improvement * 0.5
                break

        return base_factor

    def _prepare_test_data(self, skill_id: str) -> List[Dict]:
        """准备测试数据"""
        experiences = self._get_skill_experiences(skill_id)
        sample_size = min(self._config.test_sample_size, len(experiences))

        test_data = []
        for i in range(sample_size):
            exp = experiences[i % len(experiences)]
            test_item = {
                "test_id": f"test_{i}",
                "input_summary": exp.input_summary,
                "expected_accuracy": exp.performance_metrics.get("accuracy", 0.7),
                "expected_efficiency": exp.performance_metrics.get("efficiency", 0.6),
                "metadata": {"source_experience": exp.experience_id},
            }
            test_data.append(test_item)

        if not test_data:
            for i in range(self._config.test_sample_size):
                test_data.append(
                    {
                        "test_id": f"test_{i}",
                        "input_summary": f"test_input_{i}",
                        "expected_accuracy": 0.7,
                        "expected_efficiency": 0.6,
                        "metadata": {},
                    }
                )

        return test_data

    def _generate_iteration_reason(
        self,
        trigger_type: IterationTriggerType,
        analysis: Dict[str, Any],
    ) -> str:
        """生成迭代原因描述"""
        reasons = {
            IterationTriggerType.PERFORMANCE_DEGRADATION: "性能下降触发迭代优化",
            IterationTriggerType.EXPERIENCE_ACCUMULATION: "经验积累达到阈值，触发迭代优化",
            IterationTriggerType.MANUAL: "手动触发迭代优化",
            IterationTriggerType.SCHEDULED: "定时触发迭代优化",
        }

        base_reason = reasons.get(trigger_type, "迭代优化")

        if analysis.get("experiences_available", False):
            details = (
                f"基于 {analysis.get('total_count', 0)} 条经验记录分析，"
                f"成功率 {analysis.get('success_rate', 0):.1%}"
            )
            return f"{base_reason}。{details}"

        return base_reason

    def _extract_success_patterns(self, success_experiences: List) -> List[str]:
        """提取成功模式"""
        if not success_experiences:
            return []

        patterns = []
        high_quality = [
            e for e in success_experiences
            if e.quality_score is not None and e.quality_score >= 0.8
        ]

        if high_quality:
            patterns.append("高质量完成任务")

        fast_tasks = [
            e for e in success_experiences
            if e.duration_ms > 0 and e.duration_ms < 2000
        ]
        if len(fast_tasks) > len(success_experiences) * 0.5:
            patterns.append("高效执行模式")

        no_error = [e for e in success_experiences if not e.errors]
        if len(no_error) > len(success_experiences) * 0.7:
            patterns.append("零错误执行模式")

        return patterns

    def _identify_weak_points(
        self,
        experiences: List,
        avg_accuracy: float,
        avg_efficiency: float,
        common_errors: List,
    ) -> List[str]:
        """识别薄弱点"""
        weak_points = []

        if avg_accuracy < 0.6:
            weak_points.append("准确性不足")

        if avg_efficiency < 0.5:
            weak_points.append("效率偏低")

        if common_errors and common_errors[0][1] > len(experiences) * 0.3:
            weak_points.append(f"高频错误: {common_errors[0][0]}")

        failed_count = sum(1 for e in experiences if e.status == "failed")
        if failed_count > len(experiences) * 0.3:
            weak_points.append("失败率较高")

        return weak_points

    def _analyze_performance_trend(self, experiences: List) -> str:
        """分析性能趋势"""
        if len(experiences) < 5:
            return "insufficient_data"

        sorted_exps = sorted(experiences, key=lambda e: e.timestamp)
        mid_point = len(sorted_exps) // 2

        first_half = sorted_exps[:mid_point]
        second_half = sorted_exps[mid_point:]

        first_quality = self._avg_quality(first_half)
        second_quality = self._avg_quality(second_half)

        if second_quality > first_quality * 1.05:
            return "improving"
        elif second_quality < first_quality * 0.95:
            return "declining"
        else:
            return "stable"
