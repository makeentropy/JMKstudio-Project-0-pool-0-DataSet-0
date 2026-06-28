"""
Skill迭代优化机制模块

实现基于反馈循环的Skill自动改进机制：
- 收集Skill执行反馈
- 分析性能指标
- 自动调整参数
- 生成优化版本
- 版本对比和评估
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dataset.skill_engine import (
    GeneratedSkill,
    SkillEngine,
    SkillMetadata,
    SkillStatus,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class FeedbackType(str):
    """反馈类型"""

    PERFORMANCE = "performance"  # 性能反馈
    QUALITY = "quality"  # 质量反馈
    ERROR = "error"  # 错误反馈
    USER = "user"  # 用户反馈
    SYSTEM = "system"  # 系统反馈


class OptimizationStrategy(str):
    """优化策略"""

    RULE_TUNING = "rule_tuning"  # 规则调优
    PARAMETER_ADJUSTMENT = "parameter_adjustment"  # 参数调整
    CODE_REFINEMENT = "code_refinement"  # 代码优化
    MODEL_UPDATE = "model_update"  # 模型更新
    HYBRID = "hybrid"  # 混合优化


class SkillFeedback(BaseModel):
    """Skill反馈"""

    feedback_id: str = Field(..., description="反馈ID")
    skill_id: str = Field(..., description="Skill ID")
    skill_version: str = Field(default="1.0.0", description="Skill版本")
    feedback_type: str = Field(..., description="反馈类型")

    # 反馈内容
    message: str = Field(default="", description="反馈消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="反馈详情")

    # 性能指标
    metrics: Dict[str, float] = Field(default_factory=dict, description="性能指标")
    accuracy: float = Field(default=0.0, description="准确率")
    efficiency: float = Field(default=0.0, description="效率")
    success_rate: float = Field(default=0.0, description="成功率")

    # 问题信息
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")

    # 用户信息
    user_id: Optional[str] = Field(default=None, description="用户ID")
    user_rating: Optional[int] = Field(default=None, ge=1, le=5, description="用户评分")

    # 时间信息
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    processed: bool = Field(default=False, description="是否已处理")


class OptimizationRecord(BaseModel):
    """优化记录"""

    record_id: str = Field(..., description="记录ID")
    skill_id: str = Field(..., description="Skill ID")
    original_version: str = Field(..., description="原始版本")
    optimized_version: str = Field(..., description="优化版本")
    strategy: str = Field(..., description="优化策略")

    # 优化详情
    changes: List[str] = Field(default_factory=list, description="变更列表")
    improvements: Dict[str, float] = Field(default_factory=dict, description="改进指标")

    # 反馈信息
    feedback_ids: List[str] = Field(default_factory=list, description="相关反馈ID")

    # 评估结果
    evaluation_score: float = Field(default=0.0, description="评估得分")
    is_improved: bool = Field(default=False, description="是否有改进")

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    evaluated_at: Optional[datetime] = Field(default=None, description="评估时间")


class OptimizationConfig(BaseModel):
    """优化配置"""

    min_feedback_count: int = Field(default=5, description="最小反馈数量")
    improvement_threshold: float = Field(default=0.05, description="改进阈值")
    max_iterations: int = Field(default=10, description="最大迭代次数")
    optimization_strategy: str = Field(
        default=OptimizationStrategy.HYBRID, description="优化策略"
    )
    auto_apply: bool = Field(default=False, description="是否自动应用")
    require_approval: bool = Field(default=True, description="是否需要审批")
    rollback_enabled: bool = Field(default=True, description="是否启用回滚")


class PerformanceMetrics(BaseModel):
    """性能指标"""

    accuracy: float = Field(default=0.0, description="准确率")
    precision: float = Field(default=0.0, description="精确率")
    recall: float = Field(default=0.0, description="召回率")
    f1_score: float = Field(default=0.0, description="F1分数")
    efficiency: float = Field(default=0.0, description="效率")
    success_rate: float = Field(default=0.0, description="成功率")
    execution_time: float = Field(default=0.0, description="执行时间")
    resource_usage: float = Field(default=0.0, description="资源使用率")

    def compute_overall_score(self) -> float:
        """计算综合得分"""
        weights = {
            "accuracy": 0.3,
            "f1_score": 0.2,
            "efficiency": 0.15,
            "success_rate": 0.2,
            "execution_time": 0.1,
            "resource_usage": 0.05,
        }

        score = 0.0
        for metric, weight in weights.items():
            value = getattr(self, metric, 0.0)
            # 执行时间和资源使用率是反向指标
            if metric in ["execution_time", "resource_usage"]:
                value = 1.0 - value
            score += value * weight

        return score


class FeedbackCollector:
    """反馈收集器"""

    def __init__(self):
        """初始化反馈收集器"""
        self.feedback_store: Dict[str, List[SkillFeedback]] = {}
        self.feedback_handlers: Dict[str, Callable] = {}

    def collect_feedback(
        self,
        skill_id: str,
        feedback_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> SkillFeedback:
        """
        收集反馈

        Args:
            skill_id: Skill ID
            feedback_type: 反馈类型
            message: 反馈消息
            details: 反馈详情
            metrics: 性能指标

        Returns:
            Skill反馈
        """
        feedback_id = self._generate_feedback_id(skill_id)

        feedback = SkillFeedback(
            feedback_id=feedback_id,
            skill_id=skill_id,
            feedback_type=feedback_type,
            message=message,
            details=details or {},
            metrics=metrics or {},
        )

        # 存储反馈
        if skill_id not in self.feedback_store:
            self.feedback_store[skill_id] = []
        self.feedback_store[skill_id].append(feedback)

        # 触发反馈处理器
        handler = self.feedback_handlers.get(feedback_type)
        if handler:
            handler(feedback)

        logger.info(f"收集反馈: {feedback_id} for {skill_id}")
        return feedback

    def collect_performance_feedback(
        self,
        skill_id: str,
        metrics: PerformanceMetrics,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> SkillFeedback:
        """
        收集性能反馈

        Args:
            skill_id: Skill ID
            metrics: 性能指标
            execution_result: 执行结果

        Returns:
            Skill反馈
        """
        return self.collect_feedback(
            skill_id=skill_id,
            feedback_type=FeedbackType.PERFORMANCE,
            message="性能反馈",
            details=execution_result or {},
            metrics={
                "accuracy": metrics.accuracy,
                "efficiency": metrics.efficiency,
                "success_rate": metrics.success_rate,
                "execution_time": metrics.execution_time,
            },
        )

    def collect_error_feedback(
        self,
        skill_id: str,
        error: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SkillFeedback:
        """
        收集错误反馈

        Args:
            skill_id: Skill ID
            error: 错误信息
            context: 错误上下文

        Returns:
            Skill反馈
        """
        return self.collect_feedback(
            skill_id=skill_id,
            feedback_type=FeedbackType.ERROR,
            message=f"错误: {error}",
            details=context or {},
            errors=[error],
        )

    def collect_user_feedback(
        self,
        skill_id: str,
        user_id: str,
        rating: int,
        comment: str = "",
    ) -> SkillFeedback:
        """
        收集用户反馈

        Args:
            skill_id: Skill ID
            user_id: 用户ID
            rating: 评分(1-5)
            comment: 评论

        Returns:
            Skill反馈
        """
        return self.collect_feedback(
            skill_id=skill_id,
            feedback_type=FeedbackType.USER,
            message=comment,
            details={"user_id": user_id, "comment": comment},
            user_id=user_id,
            user_rating=rating,
        )

    def register_handler(self, feedback_type: str, handler: Callable) -> None:
        """
        注册反馈处理器

        Args:
            feedback_type: 反馈类型
            handler: 处理函数
        """
        self.feedback_handlers[feedback_type] = handler
        logger.info(f"注册反馈处理器: {feedback_type}")

    def get_feedback(self, skill_id: str) -> List[SkillFeedback]:
        """
        获取Skill的所有反馈

        Args:
            skill_id: Skill ID

        Returns:
            反馈列表
        """
        return self.feedback_store.get(skill_id, [])

    def get_unprocessed_feedback(self, skill_id: str) -> List[SkillFeedback]:
        """
        获取未处理的反馈

        Args:
            skill_id: Skill ID

        Returns:
            未处理反馈列表
        """
        feedbacks = self.get_feedback(skill_id)
        return [f for f in feedbacks if not f.processed]

    def mark_feedback_processed(self, feedback_id: str) -> None:
        """
        标记反馈已处理

        Args:
            feedback_id: 反馈ID
        """
        for skill_id, feedbacks in self.feedback_store.items():
            for feedback in feedbacks:
                if feedback.feedback_id == feedback_id:
                    feedback.processed = True
                    logger.info(f"反馈已处理: {feedback_id}")
                    return

    def get_feedback_statistics(self, skill_id: str) -> Dict[str, Any]:
        """
        获取反馈统计信息

        Args:
            skill_id: Skill ID

        Returns:
            统计信息
        """
        feedbacks = self.get_feedback(skill_id)

        if not feedbacks:
            return {"total_count": 0}

        stats = {
            "total_count": len(feedbacks),
            "processed_count": len([f for f in feedbacks if f.processed]),
            "unprocessed_count": len([f for f in feedbacks if not f.processed]),
            "by_type": {},
            "average_metrics": {},
            "average_rating": None,
        }

        # 按类型统计
        for feedback in feedbacks:
            type_name = feedback.feedback_type
            if type_name not in stats["by_type"]:
                stats["by_type"][type_name] = 0
            stats["by_type"][type_name] += 1

        # 平均性能指标
        metrics_list = [f.metrics for f in feedbacks if f.metrics]
        if metrics_list:
            avg_metrics = {}
            for key in metrics_list[0].keys():
                values = [m.get(key, 0.0) for m in metrics_list]
                avg_metrics[key] = sum(values) / len(values)
            stats["average_metrics"] = avg_metrics

        # 平均用户评分
        ratings = [f.user_rating for f in feedbacks if f.user_rating is not None]
        if ratings:
            stats["average_rating"] = sum(ratings) / len(ratings)

        return stats

    def _generate_feedback_id(self, skill_id: str) -> str:
        """生成反馈ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_input = f"{skill_id}_{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"feedback_{hash_value}"


class SkillOptimizer:
    """Skill优化器"""

    def __init__(
        self,
        skill_engine: Optional[SkillEngine] = None,
        config: Optional[OptimizationConfig] = None,
    ):
        """
        初始化Skill优化器

        Args:
            skill_engine: Skill生成引擎
            config: 优化配置
        """
        self.skill_engine = skill_engine or SkillEngine()
        self.config = config or OptimizationConfig()
        self.feedback_collector = FeedbackCollector()
        self.optimization_history: Dict[str, List[OptimizationRecord]] = {}
        self.optimization_strategies: Dict[str, Callable] = {}
        self._setup_default_strategies()

    def _setup_default_strategies(self) -> None:
        """设置默认优化策略"""
        self.optimization_strategies[OptimizationStrategy.RULE_TUNING] = self._rule_tuning_strategy
        self.optimization_strategies[OptimizationStrategy.PARAMETER_ADJUSTMENT] = self._parameter_adjustment_strategy
        self.optimization_strategies[OptimizationStrategy.CODE_REFINEMENT] = self._code_refinement_strategy

    def optimize(
        self,
        skill_id: str,
        strategy: Optional[str] = None,
    ) -> Optional[GeneratedSkill]:
        """
        优化Skill

        Args:
            skill_id: Skill ID
            strategy: 优化策略

        Returns:
            优化后的Skill
        """
        # 获取原始Skill
        original_skill = self.skill_engine.get_skill(skill_id)
        if original_skill is None:
            logger.error(f"Skill '{skill_id}' 不存在")
            return None

        # 检查是否有足够的反馈
        feedbacks = self.feedback_collector.get_unprocessed_feedback(skill_id)
        if len(feedbacks) < self.config.min_feedback_count:
            logger.info(f"反馈数量不足: {len(feedbacks)} < {self.config.min_feedback_count}")
            return None

        # 选择优化策略
        strategy = strategy or self.config.optimization_strategy
        strategy_func = self.optimization_strategies.get(strategy)

        if strategy_func is None:
            logger.error(f"优化策略 '{strategy}' 不存在")
            return None

        # 分析反馈
        analysis = self._analyze_feedback(feedbacks)

        # 执行优化
        optimized_skill = strategy_func(original_skill, analysis)

        if optimized_skill is None:
            logger.warning(f"Skill '{skill_id}' 优化失败")
            return None

        # 创建优化记录
        record = self._create_optimization_record(
            skill_id, original_skill, optimized_skill, strategy, feedbacks
        )

        # 评估优化效果
        if self._evaluate_optimization(original_skill, optimized_skill, analysis):
            record.is_improved = True
            record.evaluated_at = datetime.now()

            # 自动应用优化
            if self.config.auto_apply:
                self._apply_optimization(skill_id, optimized_skill)
        else:
            logger.info(f"优化效果未达阈值，不应用优化")

        # 存储优化历史
        if skill_id not in self.optimization_history:
            self.optimization_history[skill_id] = []
        self.optimization_history[skill_id].append(record)

        # 标记反馈已处理
        for feedback in feedbacks:
            self.feedback_collector.mark_feedback_processed(feedback.feedback_id)

        return optimized_skill

    def _analyze_feedback(self, feedbacks: List[SkillFeedback]) -> Dict[str, Any]:
        """分析反馈"""
        analysis = {
            "total_count": len(feedbacks),
            "error_count": 0,
            "performance_issues": [],
            "user_sentiment": None,
            "avg_metrics": {},
            "recommendations": [],
        }

        # 统计错误
        for feedback in feedbacks:
            if feedback.feedback_type == FeedbackType.ERROR:
                analysis["error_count"] += 1
                analysis["performance_issues"].extend(feedback.errors)

        # 计算平均指标
        metrics_list = [f.metrics for f in feedbacks if f.metrics]
        if metrics_list:
            for key in metrics_list[0].keys():
                values = [m.get(key, 0.0) for m in metrics_list]
                analysis["avg_metrics"][key] = sum(values) / len(values)

        # 分析用户情感
        ratings = [f.user_rating for f in feedbacks if f.user_rating is not None]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            analysis["user_sentiment"] = avg_rating

            if avg_rating < 3.0:
                analysis["recommendations"].append("用户评分偏低，需要重点改进")
            elif avg_rating >= 4.0:
                analysis["recommendations"].append("用户评分良好，可考虑细微优化")

        # 生成优化建议
        if analysis["avg_metrics"].get("accuracy", 1.0) < 0.9:
            analysis["recommendations"].append("准确率偏低，建议优化规则或模型")

        if analysis["avg_metrics"].get("efficiency", 1.0) < 0.7:
            analysis["recommendations"].append("效率偏低，建议优化代码性能")

        if analysis["error_count"] > len(feedbacks) * 0.1:
            analysis["recommendations"].append("错误率偏高，建议修复bug")

        return analysis

    def _rule_tuning_strategy(
        self,
        skill: GeneratedSkill,
        analysis: Dict[str, Any],
    ) -> Optional[GeneratedSkill]:
        """规则调优策略"""
        # 复制Skill元数据
        new_metadata = SkillMetadata(
            id=skill.metadata.id,
            name=skill.metadata.name,
            version=self._increment_version(skill.metadata.version),
            description=skill.metadata.description + " (优化版)",
            skill_type=skill.metadata.skill_type,
            status=SkillStatus.TESTING,
            dataset_id=skill.metadata.dataset_id,
            dataset_name=skill.metadata.dataset_name,
        )

        # 修改配置中的规则参数
        new_config = skill.config.copy()

        # 根据分析结果调整阈值
        if "avg_metrics" in analysis:
            accuracy = analysis["avg_metrics"].get("accuracy", 1.0)
            if accuracy < 0.9:
                # 降低置信度阈值以提高覆盖率
                if "confidence_threshold" in new_config:
                    new_config["confidence_threshold"] = max(
                        0.5, new_config["confidence_threshold"] - 0.1
                    )

        # 基于错误调整规则
        if analysis.get("performance_issues"):
            new_config["adjusted_for_errors"] = analysis["performance_issues"]

        return GeneratedSkill(
            metadata=new_metadata,
            code=skill.code,  # 保持代码不变
            config=new_config,
            test_cases=skill.test_cases,
            documentation=skill.documentation,
        )

    def _parameter_adjustment_strategy(
        self,
        skill: GeneratedSkill,
        analysis: Dict[str, Any],
    ) -> Optional[GeneratedSkill]:
        """参数调整策略"""
        new_metadata = SkillMetadata(
            id=skill.metadata.id,
            name=skill.metadata.name,
            version=self._increment_version(skill.metadata.version),
            description=skill.metadata.description + " (参数优化版)",
            skill_type=skill.metadata.skill_type,
            status=SkillStatus.TESTING,
        )

        new_config = skill.config.copy()

        # 根据性能指标调整参数
        if "avg_metrics" in analysis:
            efficiency = analysis["avg_metrics"].get("efficiency", 1.0)
            if efficiency < 0.7:
                # 降低批处理大小以提高效率
                if "batch_size" in new_config:
                    new_config["batch_size"] = max(100, new_config["batch_size"] // 2)

                # 增加并行度
                if "num_workers" in new_config:
                    new_config["num_workers"] = min(10, new_config["num_workers"] + 2)

        return GeneratedSkill(
            metadata=new_metadata,
            code=skill.code,
            config=new_config,
            test_cases=skill.test_cases,
            documentation=skill.documentation,
        )

    def _code_refinement_strategy(
        self,
        skill: GeneratedSkill,
        analysis: Dict[str, Any],
    ) -> Optional[GeneratedSkill]:
        """代码优化策略"""
        new_metadata = SkillMetadata(
            id=skill.metadata.id,
            name=skill.metadata.name,
            version=self._increment_version(skill.metadata.version),
            description=skill.metadata.description + " (代码优化版)",
            skill_type=skill.metadata.skill_type,
            status=SkillStatus.TESTING,
        )

        # 简化的代码优化（实际应用中可以使用更复杂的优化）
        optimized_code = skill.code

        # 基于错误添加异常处理
        if analysis.get("error_count", 0) > 0:
            optimized_code = self._add_error_handling(optimized_code)

        # 添加性能优化注释
        if analysis["avg_metrics"].get("efficiency", 1.0) < 0.7:
            optimized_code = self._add_performance_optimizations(optimized_code)

        return GeneratedSkill(
            metadata=new_metadata,
            code=optimized_code,
            config=skill.config,
            test_cases=skill.test_cases,
            documentation=skill.documentation,
        )

    def _add_error_handling(self, code: str) -> str:
        """添加错误处理"""
        # 在代码开头添加错误处理导入
        error_handling_import = """
from typing import Optional
import traceback

"""

        if "try:" not in code:
            # 在主要方法中添加try-except块
            lines = code.split("\n")
            modified_lines = []
            for line in lines:
                modified_lines.append(line)
                # 在主要方法定义后添加try块
                if "def process(" in line or "def validate(" in line:
                    modified_lines.append("        try:")

            code = "\n".join(modified_lines)

        return error_handling_import + code

    def _add_performance_optimizations(self, code: str) -> str:
        """添加性能优化"""
        # 添加缓存优化提示
        cache_hint = """
# 性能优化：考虑使用缓存
# from functools import lru_cache

"""
        return cache_hint + code

    def _increment_version(self, version: str) -> str:
        """增加版本号"""
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            return ".".join(parts)
        return version

    def _create_optimization_record(
        self,
        skill_id: str,
        original_skill: GeneratedSkill,
        optimized_skill: GeneratedSkill,
        strategy: str,
        feedbacks: List[SkillFeedback],
    ) -> OptimizationRecord:
        """创建优化记录"""
        record_id = hashlib.md5(
            f"{skill_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        return OptimizationRecord(
            record_id=record_id,
            skill_id=skill_id,
            original_version=original_skill.metadata.version,
            optimized_version=optimized_skill.metadata.version,
            strategy=strategy,
            feedback_ids=[f.feedback_id for f in feedbacks],
            changes=[f.message for f in feedbacks],
        )

    def _evaluate_optimization(
        self,
        original_skill: GeneratedSkill,
        optimized_skill: GeneratedSkill,
        analysis: Dict[str, Any],
    ) -> bool:
        """评估优化效果"""
        # 计算预期改进
        original_score = analysis["avg_metrics"].get("accuracy", 0.0) * 0.5 + \
                         analysis["avg_metrics"].get("efficiency", 0.0) * 0.3 + \
                         analysis["avg_metrics"].get("success_rate", 0.0) * 0.2

        # 简化评估：基于配置变化判断
        # 实际应用中可以运行测试来评估
        config_changes = len([
            k for k in optimized_skill.config.keys()
            if optimized_skill.config.get(k) != original_skill.config.get(k)
        ])

        # 如果有配置变化，预期改进
        expected_improvement = config_changes * 0.02

        return expected_improvement >= self.config.improvement_threshold

    def _apply_optimization(self, skill_id: str, optimized_skill: GeneratedSkill) -> None:
        """应用优化"""
        # 更新Skill引擎中的Skill
        self.skill_engine.generated_skills[skill_id] = optimized_skill
        self.skill_engine.skill_registry[skill_id] = optimized_skill.metadata

        logger.info(f"优化已应用到Skill: {skill_id}")

    def rollback(self, skill_id: str, version: str) -> Optional[GeneratedSkill]:
        """
        回滚到指定版本

        Args:
            skill_id: Skill ID
            version: 目标版本

        Returns:
            回滚后的Skill
        """
        history = self.optimization_history.get(skill_id, [])

        # 找到目标版本的记录
        for record in reversed(history):
            if record.original_version == version:
                # 恢复原始版本
                original_skill = self.skill_engine.get_skill(skill_id)
                if original_skill:
                    # 创建回滚版本的元数据
                    rollback_metadata = SkillMetadata(
                        id=skill_id,
                        name=original_skill.metadata.name,
                        version=self._increment_version(version),
                        description=f"回滚到版本 {version}",
                        status=SkillStatus.ACTIVE,
                    )

                    rollback_skill = GeneratedSkill(
                        metadata=rollback_metadata,
                        code=original_skill.code,
                        config=original_skill.config,
                        test_cases=original_skill.test_cases,
                        documentation=original_skill.documentation,
                    )

                    self._apply_optimization(skill_id, rollback_skill)
                    logger.info(f"Skill回滚成功: {skill_id} -> {version}")
                    return rollback_skill

        logger.warning(f"未找到版本 {version} 的记录")
        return None

    def get_optimization_history(self, skill_id: str) -> List[OptimizationRecord]:
        """
        获取优化历史

        Args:
            skill_id: Skill ID

        Returns:
            优化记录列表
        """
        return self.optimization_history.get(skill_id, [])

    def get_best_version(self, skill_id: str) -> Optional[str]:
        """
        获取最佳版本

        Args:
            skill_id: Skill ID

        Returns:
            最佳版本号
        """
        history = self.get_optimization_history(skill_id)

        if not history:
            return None

        # 找到评估得分最高的版本
        best_record = max(history, key=lambda r: r.evaluation_score)
        return best_record.optimized_version


class FeedbackLoopManager:
    """反馈循环管理器"""

    def __init__(
        self,
        optimizer: Optional[SkillOptimizer] = None,
        auto_optimize: bool = False,
    ):
        """
        初始化反馈循环管理器

        Args:
            optimizer: Skill优化器
            auto_optimize: 是否自动优化
        """
        self.optimizer = optimizer or SkillOptimizer()
        self.auto_optimize = auto_optimize
        self.active_loops: Dict[str, Dict[str, Any]] = {}

    def start_loop(self, skill_id: str) -> str:
        """
        启动反馈循环

        Args:
            skill_id: Skill ID

        Returns:
            循环ID
        """
        loop_id = hashlib.md5(f"{skill_id}_{datetime.now()}".encode()).hexdigest()[:8]

        self.active_loops[loop_id] = {
            "skill_id": skill_id,
            "started_at": datetime.now(),
            "iteration_count": 0,
            "status": "active",
        }

        logger.info(f"启动反馈循环: {loop_id} for {skill_id}")
        return loop_id

    def process_feedback(
        self,
        loop_id: str,
        feedback: SkillFeedback,
    ) -> Optional[GeneratedSkill]:
        """
        处理反馈并触发优化

        Args:
            loop_id: 循环ID
            feedback: Skill反馈

        Returns:
            优化后的Skill（如果触发优化）
        """
        loop_info = self.active_loops.get(loop_id)
        if loop_info is None:
            logger.error(f"循环 '{loop_id}' 不存在")
            return None

        # 存储反馈
        self.optimizer.feedback_collector.feedback_store.setdefault(
            feedback.skill_id, []
        ).append(feedback)

        loop_info["iteration_count"] += 1

        # 检查是否触发优化
        unprocessed_count = len(
            self.optimizer.feedback_collector.get_unprocessed_feedback(feedback.skill_id)
        )

        if self.auto_optimize and unprocessed_count >= self.optimizer.config.min_feedback_count:
            optimized_skill = self.optimizer.optimize(feedback.skill_id)
            if optimized_skill:
                loop_info["last_optimization"] = datetime.now()
                return optimized_skill

        return None

    def stop_loop(self, loop_id: str) -> Dict[str, Any]:
        """
        停止反馈循环

        Args:
            loop_id: 循环ID

        Returns:
            循环统计信息
        """
        loop_info = self.active_loops.get(loop_id)
        if loop_info is None:
            return {"error": "循环不存在"}

        loop_info["status"] = "stopped"
        loop_info["stopped_at"] = datetime.now()

        stats = {
            "loop_id": loop_id,
            "skill_id": loop_info["skill_id"],
            "iteration_count": loop_info["iteration_count"],
            "duration": (loop_info["stopped_at"] - loop_info["started_at"]).total_seconds(),
        }

        logger.info(f"停止反馈循环: {loop_id}")
        return stats

    def get_loop_status(self, loop_id: str) -> Optional[Dict[str, Any]]:
        """
        获取循环状态

        Args:
            loop_id: 循环ID

        Returns:
            循环状态
        """
        return self.active_loops.get(loop_id)

    def list_active_loops(self) -> List[Dict[str, Any]]:
        """列出所有活跃的循环"""
        return [
            loop for loop in self.active_loops.values()
            if loop["status"] == "active"
        ]


class SkillEvolutionSystem:
    """Skill进化系统"""

    def __init__(
        self,
        skill_engine: Optional[SkillEngine] = None,
        optimizer: Optional[SkillOptimizer] = None,
    ):
        """
        初始化Skill进化系统

        Args:
            skill_engine: Skill生成引擎
            optimizer: Skill优化器
        """
        self.skill_engine = skill_engine or SkillEngine()
        self.optimizer = optimizer or SkillOptimizer(skill_engine=self.skill_engine)
        self.feedback_manager = FeedbackLoopManager(optimizer=self.optimizer)
        self.evolution_history: List[Dict[str, Any]] = []

    def evolve(
        self,
        skill_id: str,
        max_iterations: int = 5,
    ) -> Optional[GeneratedSkill]:
        """
        执行Skill进化

        Args:
            skill_id: Skill ID
            max_iterations: 最大迭代次数

        Returns:
            最终进化的Skill
        """
        current_skill = self.skill_engine.get_skill(skill_id)
        if current_skill is None:
            logger.error(f"Skill '{skill_id}' 不存在")
            return None

        best_skill = current_skill
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # 执行优化
            optimized_skill = self.optimizer.optimize(skill_id)

            if optimized_skill is None:
                break

            # 评估优化效果
            if self._is_better(optimized_skill, best_skill):
                best_skill = optimized_skill

            # 记录进化历史
            self.evolution_history.append({
                "skill_id": skill_id,
                "iteration": iteration,
                "version": optimized_skill.metadata.version,
                "timestamp": datetime.now(),
            })

            logger.info(f"进化迭代 {iteration}: {skill_id} -> {optimized_skill.metadata.version}")

        return best_skill

    def _is_better(self, new_skill: GeneratedSkill, old_skill: GeneratedSkill) -> bool:
        """判断新版本是否更好"""
        # 简化比较：基于版本号和配置复杂度
        # 实际应用中应该基于性能测试
        new_score = len(new_skill.config) + int(new_skill.metadata.version.split(".")[-1])
        old_score = len(old_skill.config) + int(old_skill.metadata.version.split(".")[-1])

        return new_score > old_score

    def batch_evolve(
        self,
        skill_ids: List[str],
        max_iterations: int = 5,
    ) -> Dict[str, Optional[GeneratedSkill]]:
        """
        批量进化Skills

        Args:
            skill_ids: Skill ID列表
            max_iterations: 最大迭代次数

        Returns:
            进化结果字典
        """
        results = {}

        for skill_id in skill_ids:
            results[skill_id] = self.evolve(skill_id, max_iterations)

        return results

    def get_evolution_statistics(self) -> Dict[str, Any]:
        """获取进化统计信息"""
        return {
            "total_evolution_cycles": len(self.evolution_history),
            "by_skill": self._group_evolution_by_skill(),
        }

    def _group_evolution_by_skill(self) -> Dict[str, int]:
        """按Skill分组进化统计"""
        grouped = {}
        for record in self.evolution_history:
            skill_id = record["skill_id"]
            grouped[skill_id] = grouped.get(skill_id, 0) + 1
        return grouped