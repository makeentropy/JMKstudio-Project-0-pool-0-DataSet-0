"""
错误归因与经验总结模块

提供错误分类归因、经验模式提取、周期总结等功能，
帮助智能体从历史经验中学习和改进。
"""

import hashlib
from collections import Counter, defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.experience.models import ExperienceRecord
from ai_llm_agent_crawler.experience.pool import ExperienceDataPool
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ErrorCategory(str, Enum):
    """错误分类枚举"""

    DATA_ISSUE = "data_issue"
    STRATEGY_ISSUE = "strategy_issue"
    PARAMETER_ISSUE = "parameter_issue"
    ENVIRONMENT_ISSUE = "environment_issue"
    UNKNOWN = "unknown"


class AttributionResult(BaseModel):
    """归因结果模型"""

    error_category: ErrorCategory = Field(..., description="错误分类")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 0-1")
    key_evidence: List[str] = Field(default_factory=list, description="关键证据列表")
    root_cause: str = Field(default="", description="根本原因描述")
    related_experience_ids: List[str] = Field(
        default_factory=list, description="相关经验ID列表"
    )
    suggested_fix: str = Field(default="", description="建议修复方案")
    attribution_time: datetime = Field(
        default_factory=datetime.now, description="归因时间"
    )


class Heuristic(BaseModel):
    """经验模式模型"""

    heuristic_id: str = Field(..., description="模式ID")
    name: str = Field(..., description="模式名称")
    description: str = Field(..., description="模式描述")
    pattern_type: str = Field(..., description="模式类型")
    frequency: int = Field(default=0, ge=0, description="出现频率/次数")
    typical_features: List[str] = Field(
        default_factory=list, description="典型特征列表"
    )
    applicable_scenarios: List[str] = Field(
        default_factory=list, description="适用场景列表"
    )
    related_tasks: List[str] = Field(
        default_factory=list, description="相关任务类型列表"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度 0-1")
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="扩展元数据"
    )


def _generate_heuristic_id(name: str, pattern_type: str) -> str:
    """生成模式ID

    Args:
        name: 模式名称
        pattern_type: 模式类型

    Returns:
        模式ID，格式为 heur_ + 8位hash
    """
    key = f"{pattern_type}|{name}"
    hash_str = hashlib.md5(key.encode("utf-8")).hexdigest()[:8]
    return f"heur_{hash_str}"


_DATA_ERROR_KEYWORDS = [
    "数据质量差", "数据缺失", "格式错误", "数据格式", "无效数据", "数据错误",
    "数据不完整", "数据损坏", "解析错误", "编码错误", "数据为空", "空数据",
    "数据不一致", "数据异常", "脏数据", "data quality", "missing data",
    "format error", "invalid data", "parse error", "empty data",
    "数据质量", "数据格式错误", "字段缺失", "数据不足",
]

_STRATEGY_ERROR_KEYWORDS = [
    "策略问题", "算法错误", "逻辑错误", "规则设计", "策略失效", "策略错误",
    "决策错误", "判断错误", "方法不当", "选择错误", "路径错误",
    "algorithm error", "logic error", "strategy error", "wrong approach",
    "策略失效", "规则错误", "判断失误",
]

_PARAMETER_ERROR_KEYWORDS = [
    "参数错误", "配置错误", "阈值不当", "参数配置", "参数缺失", "无效参数",
    "参数异常", "配置不当", "阈值设置", "parameter error", "config error",
    "invalid parameter", "wrong parameter", "参数不正确", "配置失效",
]

_ENVIRONMENT_ERROR_KEYWORDS = [
    "网络错误", "连接超时", "资源限制", "依赖缺失", "环境问题", "超时",
    "网络连接", "连接失败", "内存不足", "磁盘空间", "权限不足", "端口占用",
    "network error", "timeout", "connection", "resource limit",
    "dependency missing", "environment", "connection refused",
    "网络异常", "服务不可用",
]

_CATEGORY_KEYWORDS = {
    ErrorCategory.DATA_ISSUE: _DATA_ERROR_KEYWORDS,
    ErrorCategory.STRATEGY_ISSUE: _STRATEGY_ERROR_KEYWORDS,
    ErrorCategory.PARAMETER_ISSUE: _PARAMETER_ERROR_KEYWORDS,
    ErrorCategory.ENVIRONMENT_ISSUE: _ENVIRONMENT_ERROR_KEYWORDS,
}


class ErrorAttributor:
    """错误归因器类

    基于规则、关键词匹配和历史统计的混合方法对错误进行归因分析。
    """

    def __init__(self, pool: ExperienceDataPool):
        """
        初始化错误归因器

        Args:
            pool: 经验数据池
        """
        self._pool = pool
        self._logger = get_logger(f"{__name__}.ErrorAttributor")

    def attribute_error(self, experience: ExperienceRecord) -> AttributionResult:
        """
        对单条失败经验进行错误归因

        Args:
            experience: 经验记录

        Returns:
            归因结果（分类+置信度+证据+建议）
        """
        if not experience.errors:
            return AttributionResult(
                error_category=ErrorCategory.UNKNOWN,
                confidence=0.1,
                key_evidence=["无错误信息可供归因"],
                root_cause="未发现明确错误信息",
                related_experience_ids=[experience.experience_id],
                suggested_fix="检查任务执行日志，确认是否存在未记录的错误",
            )

        results: List[Tuple[ErrorCategory, float, List[str]]] = []

        error_msg_result = self._classify_by_error_messages(experience.errors)
        results.append(error_msg_result)

        context_result = self._classify_by_context(experience)
        results.append(context_result)

        historical_result = self._classify_by_historical_similarity(experience)
        results.append(historical_result)

        combined = self._combine_attributions(results)
        combined.related_experience_ids = [experience.experience_id]

        similar_ids = historical_result[2]
        if similar_ids:
            combined.related_experience_ids.extend(similar_ids[:5])

        combined.suggested_fix = self._generate_suggested_fix(
            combined.error_category, combined.key_evidence
        )

        self._logger.debug(
            f"错误归因完成: {experience.experience_id} -> "
            f"{combined.error_category.value}, 置信度: {combined.confidence:.2f}"
        )

        return combined

    def attribute_batch(
        self, experiences: List[ExperienceRecord]
    ) -> List[AttributionResult]:
        """
        批量归因

        Args:
            experiences: 经验记录列表

        Returns:
            归因结果列表
        """
        results = []
        for exp in experiences:
            result = self.attribute_error(exp)
            results.append(result)

        self._logger.info(f"批量归因完成，共处理 {len(experiences)} 条经验记录")
        return results

    def _classify_by_error_messages(
        self, errors: List[str]
    ) -> Tuple[ErrorCategory, float, List[str]]:
        """
        基于错误消息文本的关键词匹配进行分类

        Args:
            errors: 错误消息列表

        Returns:
            (分类, 置信度, 匹配到的关键词)
        """
        if not errors:
            return ErrorCategory.UNKNOWN, 0.0, []

        category_scores: Dict[ErrorCategory, int] = defaultdict(int)
        matched_keywords: List[str] = []

        for error in errors:
            error_lower = error.lower()
            for category, keywords in _CATEGORY_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in error_lower:
                        category_scores[category] += 1
                        matched_keywords.append(f"{error} 匹配关键词: {kw}")

        if not category_scores:
            return ErrorCategory.UNKNOWN, 0.2, ["未匹配到已知错误关键词"]

        best_category = max(category_scores.items(), key=lambda x: x[1])
        total_matches = sum(category_scores.values())
        confidence = min(best_category[1] / max(total_matches, 1) * 0.8 + 0.2, 0.95)

        evidence = [
            f"错误消息关键词匹配: {best_category[1]} 个匹配",
        ] + matched_keywords[:5]

        return best_category[0], confidence, evidence

    def _classify_by_context(
        self, experience: ExperienceRecord
    ) -> Tuple[ErrorCategory, float, List[str]]:
        """
        基于上下文（任务类型、元数据、性能指标）分类

        Args:
            experience: 经验记录

        Returns:
            (分类, 置信度, 证据)
        """
        evidence: List[str] = []
        category_scores: Dict[ErrorCategory, float] = defaultdict(float)

        task_type = experience.task_type
        metadata = experience.metadata
        metrics = experience.performance_metrics

        if task_type in ("crawler", "processor"):
            if metrics.get("data_quality", 1.0) < 0.5:
                category_scores[ErrorCategory.DATA_ISSUE] += 0.3
                evidence.append(f"数据质量指标低: {metrics.get('data_quality'):.2f}")

            if metrics.get("completeness", 1.0) < 0.5:
                category_scores[ErrorCategory.DATA_ISSUE] += 0.2
                evidence.append(f"数据完整度指标低: {metrics.get('completeness'):.2f}")

        if task_type == "analyzer":
            if metrics.get("accuracy", 1.0) < 0.5:
                category_scores[ErrorCategory.STRATEGY_ISSUE] += 0.3
                evidence.append(f"分析准确率低: {metrics.get('accuracy'):.2f}")

        if "wrong_params" in metadata or "invalid_config" in metadata:
            category_scores[ErrorCategory.PARAMETER_ISSUE] += 0.4
            evidence.append("元数据中标记了参数/配置问题")

        if metadata.get("timeout") or metadata.get("network_error"):
            category_scores[ErrorCategory.ENVIRONMENT_ISSUE] += 0.4
            evidence.append("元数据中标记了超时/网络问题")

        if experience.duration_ms > 30000:
            category_scores[ErrorCategory.ENVIRONMENT_ISSUE] += 0.2
            evidence.append(f"执行耗时过长: {experience.duration_ms:.0f}ms")

        if not category_scores:
            return ErrorCategory.UNKNOWN, 0.1, ["上下文信息不足以分类"]

        best_category = max(category_scores.items(), key=lambda x: x[1])
        confidence = min(best_category[1], 0.7)

        return best_category[0], confidence, evidence

    def _classify_by_historical_similarity(
        self, experience: ExperienceRecord
    ) -> Tuple[ErrorCategory, float, List[str]]:
        """
        基于历史相似案例的分类

        简化版：匹配相同任务类型的历史错误分布。

        Args:
            experience: 经验记录

        Returns:
            (分类, 置信度, 相似案例ID列表)
        """
        similar_experiences = self._pool.query(
            {"task_type": experience.task_type, "status": "failed"},
            limit=100,
        )

        if not similar_experiences:
            return ErrorCategory.UNKNOWN, 0.0, []

        category_counts: Dict[ErrorCategory, int] = defaultdict(int)
        similar_ids: List[str] = []

        for exp in similar_experiences:
            if exp.experience_id == experience.experience_id:
                continue

            similar_ids.append(exp.experience_id)

            if exp.errors:
                for error in exp.errors:
                    error_lower = error.lower()
                    for category, keywords in _CATEGORY_KEYWORDS.items():
                        if any(kw.lower() in error_lower for kw in keywords):
                            category_counts[category] += 1
                            break

        if not category_counts:
            return (
                ErrorCategory.UNKNOWN,
                0.15,
                similar_ids[:5],
            )

        best_category = max(category_counts.items(), key=lambda x: x[1])
        total = sum(category_counts.values())
        confidence = min(best_category[1] / max(total, 1) * 0.6 + 0.1, 0.7)

        evidence = [
            f"基于 {len(similar_ids)} 条相似历史失败案例统计",
            f"该任务类型最常见错误类别: {best_category[0].value}",
        ] + similar_ids[:3]

        return best_category[0], confidence, evidence

    def _combine_attributions(
        self, results: List[Tuple[ErrorCategory, float, List[str]]]
    ) -> AttributionResult:
        """
        综合多个归因方法的结果，取置信度最高的分类

        Args:
            results: 多个归因方法的结果列表，每个元素为 (分类, 置信度, 证据列表)

        Returns:
            综合归因结果
        """
        category_confidences: Dict[ErrorCategory, List[float]] = defaultdict(list)
        all_evidence: List[str] = []
        all_related_ids: List[str] = []

        for category, confidence, evidence in results:
            if confidence > 0:
                category_confidences[category].append(confidence)
            all_evidence.extend(evidence)

        if not category_confidences:
            return AttributionResult(
                error_category=ErrorCategory.UNKNOWN,
                confidence=0.1,
                key_evidence=all_evidence[:10],
                root_cause="无法确定错误原因",
            )

        weighted_scores: Dict[ErrorCategory, float] = {}
        for category, confidences in category_confidences.items():
            avg_conf = sum(confidences) / len(confidences)
            max_conf = max(confidences)
            weighted_scores[category] = avg_conf * 0.6 + max_conf * 0.4

        best_category = max(weighted_scores.items(), key=lambda x: x[1])
        final_confidence = min(best_category[1], 0.98)

        root_cause = self._generate_root_cause(best_category[0], all_evidence)

        return AttributionResult(
            error_category=best_category[0],
            confidence=final_confidence,
            key_evidence=all_evidence[:10],
            root_cause=root_cause,
            related_experience_ids=all_related_ids,
        )

    def _generate_root_cause(
        self, category: ErrorCategory, evidence: List[str]
    ) -> str:
        """
        生成根本原因描述

        Args:
            category: 错误分类
            evidence: 证据列表

        Returns:
            根本原因描述文本
        """
        descriptions = {
            ErrorCategory.DATA_ISSUE: "数据质量或格式存在问题，导致任务无法正常执行",
            ErrorCategory.STRATEGY_ISSUE: "策略或算法设计存在缺陷，导致决策或执行错误",
            ErrorCategory.PARAMETER_ISSUE: "参数配置不正确或阈值设置不当，影响任务执行效果",
            ErrorCategory.ENVIRONMENT_ISSUE: "环境因素（网络、资源、依赖等）导致任务失败",
            ErrorCategory.UNKNOWN: "错误原因不明确，需要进一步分析",
        }

        base_desc = descriptions.get(category, "未知错误原因")

        if evidence:
            return f"{base_desc}。关键证据: {evidence[0]}"
        return base_desc

    def _generate_suggested_fix(
        self, category: ErrorCategory, evidence: List[str]
    ) -> str:
        """
        根据错误分类和证据生成建议修复方案

        Args:
            category: 错误分类
            evidence: 证据列表

        Returns:
            建议修复方案文本
        """
        suggestions = {
            ErrorCategory.DATA_ISSUE: (
                "建议：1) 检查输入数据源的质量和完整性；"
                "2) 增加数据校验和清洗环节；"
                "3) 优化数据格式转换逻辑；"
                "4) 考虑添加数据质量监控告警"
            ),
            ErrorCategory.STRATEGY_ISSUE: (
                "建议：1) 审查相关策略和算法逻辑；"
                "2) 增加边界条件测试；"
                "3) 考虑引入多种策略并择优；"
                "4) 增加策略效果评估机制"
            ),
            ErrorCategory.PARAMETER_ISSUE: (
                "建议：1) 检查相关参数配置是否正确；"
                "2) 根据历史数据调优阈值；"
                "3) 增加参数有效性校验；"
                "4) 考虑使用自适应参数调整"
            ),
            ErrorCategory.ENVIRONMENT_ISSUE: (
                "建议：1) 检查网络连接和依赖服务状态；"
                "2) 评估系统资源使用情况；"
                "3) 增加重试和降级机制；"
                "4) 优化超时设置和资源配置"
            ),
            ErrorCategory.UNKNOWN: (
                "建议：1) 详细记录错误日志便于后续分析；"
                "2) 增加监控覆盖范围；"
                "3) 逐步排查可能的原因；"
                "4) 积累更多案例后重新分析"
            ),
        }

        return suggestions.get(category, suggestions[ErrorCategory.UNKNOWN])

    def get_error_statistics(
        self, filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        获取错误统计信息

        Args:
            filters: 可选过滤条件

        Returns:
            统计信息字典，包含按分类分布、Top错误消息、按任务类型分布等
        """
        query_filters = filters or {}
        query_filters["status"] = "failed"

        failed_experiences = self._pool.query(query_filters, limit=10000)

        stats: Dict[str, Any] = {
            "total_failed": len(failed_experiences),
            "by_category": {},
            "top_errors": [],
            "by_task_type": {},
            "attribution_summary": {},
        }

        if not failed_experiences:
            return stats

        category_counts: Dict[str, int] = defaultdict(int)
        error_counter: Counter = Counter()
        task_type_counts: Dict[str, int] = defaultdict(int)

        for exp in failed_experiences:
            task_type_counts[exp.task_type] += 1

            result = self._classify_by_error_messages(exp.errors)
            category_counts[result[0].value] += 1

            for error in exp.errors:
                error_counter[error] += 1

        stats["by_category"] = dict(category_counts)
        stats["by_task_type"] = dict(task_type_counts)
        stats["top_errors"] = [
            {"message": msg, "count": count}
            for msg, count in error_counter.most_common(10)
        ]

        total = len(failed_experiences)
        if total > 0:
            stats["attribution_summary"] = {
                cat: {"count": cnt, "ratio": cnt / total}
                for cat, cnt in category_counts.items()
            }

        self._logger.debug(f"错误统计完成，共 {total} 条失败记录")
        return stats


class ExperienceSummarizer:
    """经验总结器类

    从经验数据中提取可复用的模式、洞察和总结。
    """

    def __init__(self, pool: ExperienceDataPool):
        """
        初始化经验总结器

        Args:
            pool: 经验数据池
        """
        self._pool = pool
        self._logger = get_logger(f"{__name__}.ExperienceSummarizer")

    def extract_heuristics(self, min_frequency: int = 3) -> List[Heuristic]:
        """
        从经验池中提取可复用的经验模式

        Args:
            min_frequency: 最小频率阈值

        Returns:
            启发式模式列表
        """
        all_experiences = self._pool.query({}, limit=10000)

        if not all_experiences:
            return []

        heuristics: List[Heuristic] = []

        success_patterns = self._extract_success_patterns(all_experiences)
        heuristics.extend(
            [h for h in success_patterns if h.frequency >= min_frequency]
        )

        failure_patterns = self._extract_failure_patterns(all_experiences)
        heuristics.extend(
            [h for h in failure_patterns if h.frequency >= min_frequency]
        )

        best_practices = self._extract_best_practices(all_experiences)
        heuristics.extend(
            [h for h in best_practices if h.frequency >= min_frequency]
        )

        pitfalls = self._extract_pitfalls(all_experiences)
        heuristics.extend([h for h in pitfalls if h.frequency >= min_frequency])

        heuristics.sort(key=lambda h: h.frequency * h.confidence, reverse=True)

        self._logger.info(
            f"经验模式提取完成，共提取 {len(heuristics)} 条模式"
        )
        return heuristics

    def _extract_success_patterns(
        self, experiences: List[ExperienceRecord]
    ) -> List[Heuristic]:
        """
        从成功经验中提取成功模式

        Args:
            experiences: 经验记录列表

        Returns:
            成功模式列表
        """
        heuristics: List[Heuristic] = []

        success_exps = [e for e in experiences if e.status == "success"]
        if not success_exps:
            return heuristics

        task_type_success: Dict[str, int] = defaultdict(int)
        task_type_total: Dict[str, int] = defaultdict(int)

        for exp in experiences:
            task_type_total[exp.task_type] += 1
            if exp.status == "success":
                task_type_success[exp.task_type] += 1

        for task_type, total in task_type_total.items():
            success_count = task_type_success.get(task_type, 0)
            if total >= 3 and success_count / total >= 0.8:
                name = f"高成功率任务类型: {task_type}"
                heuristic = Heuristic(
                    heuristic_id=_generate_heuristic_id(name, "success_pattern"),
                    name=name,
                    description=f"任务类型 {task_type} 的成功率达到 {success_count / total:.1%}",
                    pattern_type="success_pattern",
                    frequency=success_count,
                    typical_features=[
                        f"任务类型: {task_type}",
                        f"成功率: {success_count / total:.1%}",
                        f"总样本数: {total}",
                    ],
                    applicable_scenarios=[f"{task_type} 类任务执行"],
                    related_tasks=[task_type],
                    confidence=min(success_count / total, 0.95),
                    metadata={
                        "success_count": success_count,
                        "total_count": total,
                        "success_rate": success_count / total,
                    },
                )
                heuristics.append(heuristic)

        high_quality_exps = [
            e for e in success_exps
            if e.quality_score is not None and e.quality_score >= 0.8
        ]
        if len(high_quality_exps) >= 3:
            name = "高质量成功模式"
            heuristic = Heuristic(
                heuristic_id=_generate_heuristic_id(name, "success_pattern"),
                name=name,
                description="高质量成功任务的共同特征",
                pattern_type="success_pattern",
                frequency=len(high_quality_exps),
                typical_features=[
                    "质量评分 >= 0.8",
                    f"涉及 {len(set(e.task_type for e in high_quality_exps))} 种任务类型",
                ],
                applicable_scenarios=["追求高质量结果的任务"],
                related_tasks=list(set(e.task_type for e in high_quality_exps)),
                confidence=min(len(high_quality_exps) / len(success_exps), 0.9),
                metadata={
                    "high_quality_count": len(high_quality_exps),
                    "avg_quality": sum(
                        e.quality_score for e in high_quality_exps
                    ) / len(high_quality_exps),
                },
            )
            heuristics.append(heuristic)

        return heuristics

    def _extract_failure_patterns(
        self, experiences: List[ExperienceRecord]
    ) -> List[Heuristic]:
        """
        从失败经验中提取失败模式

        Args:
            experiences: 经验记录列表

        Returns:
            失败模式列表
        """
        heuristics: List[Heuristic] = []

        failed_exps = [e for e in experiences if e.status == "failed"]
        if not failed_exps:
            return heuristics

        task_type_failure: Dict[str, int] = defaultdict(int)
        task_type_total: Dict[str, int] = defaultdict(int)

        for exp in experiences:
            task_type_total[exp.task_type] += 1
            if exp.status == "failed":
                task_type_failure[exp.task_type] += 1

        for task_type, total in task_type_total.items():
            fail_count = task_type_failure.get(task_type, 0)
            if total >= 3 and fail_count / total >= 0.4:
                name = f"高失败率任务类型: {task_type}"
                heuristic = Heuristic(
                    heuristic_id=_generate_heuristic_id(name, "failure_pattern"),
                    name=name,
                    description=f"任务类型 {task_type} 的失败率达到 {fail_count / total:.1%}",
                    pattern_type="failure_pattern",
                    frequency=fail_count,
                    typical_features=[
                        f"任务类型: {task_type}",
                        f"失败率: {fail_count / total:.1%}",
                        f"总样本数: {total}",
                    ],
                    applicable_scenarios=[f"{task_type} 类任务风险评估"],
                    related_tasks=[task_type],
                    confidence=min(fail_count / total, 0.95),
                    metadata={
                        "fail_count": fail_count,
                        "total_count": total,
                        "failure_rate": fail_count / total,
                    },
                )
                heuristics.append(heuristic)

        error_counter: Counter = Counter()
        for exp in failed_exps:
            for error in exp.errors:
                error_counter[error] += 1

        for error_msg, count in error_counter.most_common(5):
            if count >= 3:
                name = f"高频错误: {error_msg[:30]}"
                heuristic = Heuristic(
                    heuristic_id=_generate_heuristic_id(
                        error_msg, "failure_pattern"
                    ),
                    name=name,
                    description=f"频繁出现的错误: {error_msg}",
                    pattern_type="failure_pattern",
                    frequency=count,
                    typical_features=[
                        f"错误消息: {error_msg}",
                        f"出现次数: {count}",
                    ],
                    applicable_scenarios=["错误预防和排查"],
                    related_tasks=list(
                        set(
                            e.task_type
                            for e in failed_exps
                            if error_msg in e.errors
                        )
                    ),
                    confidence=min(count / len(failed_exps), 0.9),
                    metadata={"error_message": error_msg},
                )
                heuristics.append(heuristic)

        return heuristics

    def _extract_best_practices(
        self, experiences: List[ExperienceRecord]
    ) -> List[Heuristic]:
        """
        提取最佳实践模式

        基于高成功率+高效率的组合特征。

        Args:
            experiences: 经验记录列表

        Returns:
            最佳实践模式列表
        """
        heuristics: List[Heuristic] = []

        success_exps = [e for e in experiences if e.status == "success"]
        if not success_exps:
            return heuristics

        durations = [e.duration_ms for e in success_exps if e.duration_ms > 0]
        if not durations:
            return heuristics

        avg_duration = sum(durations) / len(durations)

        fast_success = [
            e for e in success_exps
            if e.duration_ms > 0 and e.duration_ms <= avg_duration * 0.7
        ]

        if len(fast_success) >= 3:
            name = "高效成功模式"
            heuristic = Heuristic(
                heuristic_id=_generate_heuristic_id(name, "best_practice"),
                name=name,
                description="既成功又高效的任务执行模式",
                pattern_type="best_practice",
                frequency=len(fast_success),
                typical_features=[
                    f"耗时低于平均水平的 70%",
                    f"平均耗时: {sum(e.duration_ms for e in fast_success) / len(fast_success):.0f}ms",
                    f"涉及任务类型: {len(set(e.task_type for e in fast_success))} 种",
                ],
                applicable_scenarios=["追求效率的任务执行优化"],
                related_tasks=list(set(e.task_type for e in fast_success)),
                confidence=min(len(fast_success) / len(success_exps), 0.85),
                metadata={
                    "avg_duration": sum(e.duration_ms for e in fast_success) / len(fast_success),
                    "overall_avg_duration": avg_duration,
                },
            )
            heuristics.append(heuristic)

        high_quality_fast = [
            e for e in fast_success
            if e.quality_score is not None and e.quality_score >= 0.7
        ]
        if len(high_quality_fast) >= 3:
            name = "优质高效最佳实践"
            heuristic = Heuristic(
                heuristic_id=_generate_heuristic_id(name, "best_practice"),
                name=name,
                description="同时满足高质量和高效率的最佳实践",
                pattern_type="best_practice",
                frequency=len(high_quality_fast),
                typical_features=[
                    "质量评分 >= 0.7",
                    f"耗时低于平均值的 70%",
                    f"样本数: {len(high_quality_fast)}",
                ],
                applicable_scenarios=["对质量和效率都有高要求的场景"],
                related_tasks=list(
                    set(e.task_type for e in high_quality_fast)
                ),
                confidence=min(len(high_quality_fast) / len(success_exps), 0.9),
                metadata={
                    "avg_quality": sum(
                        e.quality_score for e in high_quality_fast
                    ) / len(high_quality_fast),
                },
            )
            heuristics.append(heuristic)

        return heuristics

    def _extract_pitfalls(
        self, experiences: List[ExperienceRecord]
    ) -> List[Heuristic]:
        """
        提取陷阱/坑点模式

        基于常见错误模式、易踩坑场景。

        Args:
            experiences: 经验记录列表

        Returns:
            陷阱模式列表
        """
        heuristics: List[Heuristic] = []

        failed_exps = [e for e in experiences if e.status == "failed"]
        if not failed_exps:
            return heuristics

        multi_error_exps = [e for e in failed_exps if len(e.errors) >= 2]
        if len(multi_error_exps) >= 3:
            name = "多重错误陷阱"
            heuristic = Heuristic(
                heuristic_id=_generate_heuristic_id(name, "pitfall"),
                name=name,
                description="任务失败时伴随多个错误，可能存在连锁反应",
                pattern_type="pitfall",
                frequency=len(multi_error_exps),
                typical_features=[
                    "失败时伴随 2 个及以上错误",
                    f"平均错误数: {sum(len(e.errors) for e in multi_error_exps) / len(multi_error_exps):.1f}",
                ],
                applicable_scenarios=["复杂任务的错误预防"],
                related_tasks=list(set(e.task_type for e in multi_error_exps)),
                confidence=min(len(multi_error_exps) / len(failed_exps), 0.8),
                metadata={
                    "avg_errors": sum(len(e.errors) for e in multi_error_exps) / len(multi_error_exps),
                },
            )
            heuristics.append(heuristic)

        warning_failed = [
            e for e in failed_exps if len(e.warnings) > 0
        ]
        if len(warning_failed) >= 3:
            name = "警告忽视陷阱"
            heuristic = Heuristic(
                heuristic_id=_generate_heuristic_id(name, "pitfall"),
                name=name,
                description="出现警告后未及时处理，最终导致失败",
                pattern_type="pitfall",
                frequency=len(warning_failed),
                typical_features=[
                    "失败前存在警告信息",
                    f"平均警告数: {sum(len(e.warnings) for e in warning_failed) / len(warning_failed):.1f}",
                ],
                applicable_scenarios=["任务执行中的风险预警"],
                related_tasks=list(set(e.task_type for e in warning_failed)),
                confidence=min(len(warning_failed) / len(failed_exps), 0.75),
                metadata={
                    "avg_warnings": sum(len(e.warnings) for e in warning_failed) / len(warning_failed),
                },
            )
            heuristics.append(heuristic)

        return heuristics

    def summarize_period(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        总结某段时间的经验

        Args:
            start_date: 开始时间
            end_date: 结束时间

        Returns:
            总结信息，包含总体概况、成功模式、失败模式、关键教训、改进建议
        """
        period_exps = self._pool.query(
            {"time_range": {"start": start_date, "end": end_date}},
            limit=10000,
        )

        summary: Dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "total_records": len(period_exps),
            "overview": {},
            "success_patterns": [],
            "failure_patterns": [],
            "key_lessons": [],
            "improvement_suggestions": [],
        }

        if not period_exps:
            summary["overview"] = {
                "message": "该时间段内无经验记录",
            }
            return summary

        success_count = sum(1 for e in period_exps if e.status == "success")
        failed_count = sum(1 for e in period_exps if e.status == "failed")
        partial_count = sum(1 for e in period_exps if e.status == "partial")
        skipped_count = sum(1 for e in period_exps if e.status == "skipped")

        total_errors = sum(len(e.errors) for e in period_exps)
        total_warnings = sum(len(e.warnings) for e in period_exps)

        avg_duration = (
            sum(e.duration_ms for e in period_exps) / len(period_exps)
            if period_exps
            else 0.0
        )

        quality_scores = [
            e.quality_score for e in period_exps if e.quality_score is not None
        ]
        avg_quality = (
            sum(quality_scores) / len(quality_scores) if quality_scores else None
        )

        summary["overview"] = {
            "success_count": success_count,
            "failed_count": failed_count,
            "partial_count": partial_count,
            "skipped_count": skipped_count,
            "success_rate": success_count / len(period_exps),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "avg_duration_ms": avg_duration,
            "avg_quality_score": avg_quality,
            "task_types": list(set(e.task_type for e in period_exps)),
        }

        temp_pool = ExperienceDataPool()
        for exp in period_exps:
            temp_pool.add_record(exp)

        temp_summarizer = ExperienceSummarizer(temp_pool)
        heuristics = temp_summarizer.extract_heuristics(min_frequency=2)

        summary["success_patterns"] = [
            h.model_dump() for h in heuristics if h.pattern_type == "success_pattern"
        ]
        summary["failure_patterns"] = [
            h.model_dump() for h in heuristics if h.pattern_type == "failure_pattern"
        ]

        if failed_count > 0:
            attributor = ErrorAttributor(temp_pool)
            error_stats = attributor.get_error_statistics()
            summary["error_statistics"] = error_stats

            top_category = max(
                error_stats["by_category"].items(), key=lambda x: x[1]
            ) if error_stats["by_category"] else None
            if top_category:
                summary["key_lessons"].append(
                    f"最主要的错误类型是 {top_category[0]}，共发生 {top_category[1]} 次"
                )

        if total_errors > 0:
            summary["key_lessons"].append(
                f"期间共发生 {total_errors} 个错误，{total_warnings} 个警告"
            )

        if success_count / len(period_exps) < 0.6:
            summary["improvement_suggestions"].append(
                "成功率低于 60%，建议重点提升任务执行质量"
            )

        if avg_quality is not None and avg_quality < 0.6:
            summary["improvement_suggestions"].append(
                "平均质量评分偏低，建议优化核心流程"
            )

        if not summary["improvement_suggestions"]:
            summary["improvement_suggestions"].append(
                "整体表现良好，继续保持并追求更高的稳定性"
            )

        self._logger.info(
            f"周期总结完成，时间段: {start_date} ~ {end_date}, "
            f"记录数: {len(period_exps)}"
        )
        return summary

    def get_top_insights(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        获取 Top N 条最有价值的洞察

        Args:
            top_n: 返回的洞察数量

        Returns:
            洞察列表，按重要性/频率排序
        """
        heuristics = self.extract_heuristics(min_frequency=2)

        if not heuristics:
            return []

        scored_insights = []

        for h in heuristics:
            importance = h.frequency * h.confidence

            type_weights = {
                "failure_pattern": 1.2,
                "pitfall": 1.15,
                "best_practice": 1.1,
                "success_pattern": 1.0,
            }
            importance *= type_weights.get(h.pattern_type, 1.0)

            insight = {
                "heuristic_id": h.heuristic_id,
                "name": h.name,
                "description": h.description,
                "pattern_type": h.pattern_type,
                "frequency": h.frequency,
                "confidence": h.confidence,
                "importance_score": importance,
                "typical_features": h.typical_features,
                "applicable_scenarios": h.applicable_scenarios,
                "related_tasks": h.related_tasks,
            }
            scored_insights.append(insight)

        scored_insights.sort(key=lambda x: x["importance_score"], reverse=True)

        self._logger.debug(f"获取 Top {top_n} 洞察，共 {len(scored_insights)} 条候选")
        return scored_insights[:top_n]
