"""
自我认知画像模块

提供智能体自我认知画像的生成和更新功能，基于经验数据池分析智能体的
技能领域、知识边界、优势劣势、典型错误和改进方向。
"""

import hashlib
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.experience.models import ExperienceRecord
from ai_llm_agent_crawler.experience.pool import ExperienceDataPool
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


def _generate_profile_id() -> str:
    """生成画像唯一ID

    Returns:
        画像ID，格式为 prof_ + 8位hash
    """
    random_hash = hashlib.md5(uuid.uuid4().hex.encode()).hexdigest()[:8]
    return f"prof_{random_hash}"


class SkillDomain(BaseModel):
    """技能领域模型"""

    domain_name: str = Field(..., description="领域名称")
    task_count: int = Field(default=0, description="任务数量")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="成功率 0-1")
    avg_accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="平均准确率 0-1")
    avg_efficiency: float = Field(default=0.0, ge=0.0, le=1.0, description="平均效率 0-1")
    proficiency: float = Field(default=0.0, ge=0.0, le=1.0, description="熟练度 0-1")
    last_active: datetime = Field(default_factory=datetime.now, description="最近活跃时间")
    strengths: List[str] = Field(default_factory=list, description="优势点")
    weaknesses: List[str] = Field(default_factory=list, description="薄弱点")


class KnowledgeBoundary(BaseModel):
    """知识边界模型"""

    known_domains: List[str] = Field(default_factory=list, description="已知领域")
    unknown_domains: List[str] = Field(default_factory=list, description="未知/未涉足领域")
    frontier_domains: List[str] = Field(default_factory=list, description="前沿/正在学习的领域")
    confidence_distribution: Dict[str, float] = Field(
        default_factory=dict, description="各领域置信度分布"
    )
    overall_certainty: float = Field(
        default=0.0, ge=0.0, le=1.0, description="整体确定性 0-1"
    )


class AgentProfile(BaseModel):
    """智能体画像模型"""

    profile_id: str = Field(
        default_factory=_generate_profile_id,
        description="画像ID: prof_ + 8位hash",
    )
    agent_name: str = Field(default="agent", description="智能体名称")
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="生成时间",
    )
    experience_count: int = Field(default=0, description="基于的经验数量")

    overall_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="综合能力评分 0-1"
    )

    strengths: List[str] = Field(default_factory=list, description="擅长领域/优势列表")
    weaknesses: List[str] = Field(default_factory=list, description="薄弱环节列表")
    typical_errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="典型错误类型：类型、频率、描述"
    )
    improvement_directions: List[str] = Field(
        default_factory=list, description="改进方向列表"
    )

    skill_domains: List[SkillDomain] = Field(
        default_factory=list, description="各技能领域详情"
    )
    knowledge_boundary: KnowledgeBoundary = Field(
        default_factory=KnowledgeBoundary,
        description="知识边界",
    )

    recent_trend: str = Field(default="stable", description="近期趋势：improving/stable/declining")
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="最后更新时间",
    )


class AgentProfileGenerator:
    """画像生成器类

    基于经验数据池生成和更新智能体自我认知画像。
    """

    def __init__(self, pool: ExperienceDataPool):
        """
        初始化画像生成器

        Args:
            pool: 经验数据池
        """
        self._pool = pool
        self._logger = get_logger(f"{__name__}.AgentProfileGenerator")

    def generate_profile(self, agent_name: str = "agent") -> AgentProfile:
        """
        生成完整的智能体画像

        基于经验池中的所有历史数据生成完整画像。

        Args:
            agent_name: 智能体名称

        Returns:
            AgentProfile 完整画像
        """
        experiences = self._pool.query({}, limit=10000)
        experience_count = len(experiences)

        if experience_count == 0:
            return self._generate_default_profile(agent_name)

        skill_domains = self._analyze_skill_domains(experiences)
        strengths = self._identify_strengths(skill_domains)
        weaknesses = self._identify_weaknesses(skill_domains)
        typical_errors = self._identify_typical_errors(experiences)
        improvement_directions = self._determine_improvement_directions(
            skill_domains, typical_errors
        )
        knowledge_boundary = self._compute_knowledge_boundary(experiences)
        recent_trend = self._analyze_trend(experiences)
        overall_score = self._compute_overall_score(skill_domains)

        last_active = max((e.timestamp for e in experiences), default=datetime.now())

        profile = AgentProfile(
            agent_name=agent_name,
            experience_count=experience_count,
            overall_score=overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
            typical_errors=typical_errors,
            improvement_directions=improvement_directions,
            skill_domains=skill_domains,
            knowledge_boundary=knowledge_boundary,
            recent_trend=recent_trend,
            last_updated=last_active,
        )

        self._logger.info(
            f"生成智能体画像: {agent_name}, 经验数: {experience_count}, "
            f"综合评分: {overall_score:.3f}"
        )

        return profile

    def update_profile(self, profile: AgentProfile) -> AgentProfile:
        """
        更新已有画像（重新计算）

        Args:
            profile: 已有画像对象

        Returns:
            更新后的画像
        """
        new_profile = self.generate_profile(profile.agent_name)
        new_profile.profile_id = profile.profile_id
        new_profile.generated_at = profile.generated_at
        new_profile.last_updated = datetime.now()

        self._logger.info(
            f"更新智能体画像: {profile.agent_name}, 经验数: {new_profile.experience_count}"
        )

        return new_profile

    def _analyze_skill_domains(
        self, experiences: List[ExperienceRecord]
    ) -> List[SkillDomain]:
        """
        分析各技能领域的表现

        按 task_type 分组，计算各领域的成功率、准确率、效率等。

        Args:
            experiences: 经验记录列表

        Returns:
            SkillDomain 列表
        """
        if not experiences:
            return []

        domain_groups: Dict[str, List[ExperienceRecord]] = defaultdict(list)
        for exp in experiences:
            domain_groups[exp.task_type].append(exp)

        skill_domains = []
        for domain_name, domain_exps in domain_groups.items():
            task_count = len(domain_exps)

            success_count = sum(
                1 for e in domain_exps if e.status == "success"
            )
            success_rate = success_count / task_count if task_count > 0 else 0.0

            accuracy_values = [
                e.performance_metrics.get("accuracy", 0.0)
                for e in domain_exps
                if "accuracy" in e.performance_metrics
            ]
            avg_accuracy = (
                sum(accuracy_values) / len(accuracy_values)
                if accuracy_values
                else 0.0
            )

            efficiency_values = [
                e.performance_metrics.get("efficiency", 0.0)
                for e in domain_exps
                if "efficiency" in e.performance_metrics
            ]
            avg_efficiency = (
                sum(efficiency_values) / len(efficiency_values)
                if efficiency_values
                else 0.0
            )

            proficiency = self._compute_proficiency(task_count, success_rate, avg_accuracy)

            last_active = max(e.timestamp for e in domain_exps)

            domain_strengths = []
            domain_weaknesses = []

            if success_rate > 0.8:
                domain_strengths.append(f"成功率高达 {success_rate:.1%}")
            elif success_rate < 0.5:
                domain_weaknesses.append(f"成功率仅 {success_rate:.1%}")

            if avg_accuracy > 0.8:
                domain_strengths.append(f"平均准确率达 {avg_accuracy:.1%}")
            elif avg_accuracy < 0.5 and accuracy_values:
                domain_weaknesses.append(f"平均准确率仅 {avg_accuracy:.1%}")

            if avg_efficiency > 0.8 and efficiency_values:
                domain_strengths.append(f"平均效率达 {avg_efficiency:.1%}")
            elif avg_efficiency < 0.5 and efficiency_values:
                domain_weaknesses.append(f"平均效率仅 {avg_efficiency:.1%}")

            skill_domain = SkillDomain(
                domain_name=domain_name,
                task_count=task_count,
                success_rate=success_rate,
                avg_accuracy=avg_accuracy,
                avg_efficiency=avg_efficiency,
                proficiency=proficiency,
                last_active=last_active,
                strengths=domain_strengths,
                weaknesses=domain_weaknesses,
            )
            skill_domains.append(skill_domain)

        skill_domains.sort(key=lambda d: d.task_count, reverse=True)

        return skill_domains

    def _compute_proficiency(
        self, task_count: int, success_rate: float, avg_accuracy: float
    ) -> float:
        """
        计算熟练度

        基于任务数量和成功率综合计算。

        Args:
            task_count: 任务数量
            success_rate: 成功率
            avg_accuracy: 平均准确率

        Returns:
            熟练度 0-1
        """
        count_factor = min(task_count / 20.0, 1.0)
        quality_factor = success_rate * 0.6 + avg_accuracy * 0.4
        proficiency = count_factor * 0.4 + quality_factor * 0.6
        return max(0.0, min(1.0, proficiency))

    def _identify_strengths(self, domains: List[SkillDomain]) -> List[str]:
        """
        识别擅长领域

        标准：成功率 > 0.8 且任务数 > 5 的领域。

        Args:
            domains: 技能领域列表

        Returns:
            优势描述列表
        """
        strengths = []

        for domain in domains:
            if domain.success_rate > 0.8 and domain.task_count > 5:
                strengths.append(
                    f"{domain.domain_name}领域表现优秀，"
                    f"成功率 {domain.success_rate:.1%}，"
                    f"共完成 {domain.task_count} 个任务"
                )

        if not strengths and domains:
            top_domain = max(domains, key=lambda d: d.success_rate)
            strengths.append(
                f"{top_domain.domain_name}领域相对较强，"
                f"成功率 {top_domain.success_rate:.1%}"
            )

        return strengths

    def _identify_weaknesses(self, domains: List[SkillDomain]) -> List[str]:
        """
        识别薄弱环节

        标准：成功率 < 0.5 或效率 < 0.5 的领域。

        Args:
            domains: 技能领域列表

        Returns:
            薄弱点描述列表
        """
        weaknesses = []

        for domain in domains:
            if domain.success_rate < 0.5:
                weaknesses.append(
                    f"{domain.domain_name}领域成功率偏低，"
                    f"仅 {domain.success_rate:.1%}，"
                    f"共 {domain.task_count} 个任务"
                )
            elif domain.avg_efficiency < 0.5 and domain.task_count > 2:
                weaknesses.append(
                    f"{domain.domain_name}领域效率偏低，"
                    f"平均效率 {domain.avg_efficiency:.1%}"
                )

        if not weaknesses and domains:
            bottom_domain = min(domains, key=lambda d: d.success_rate)
            weaknesses.append(
                f"{bottom_domain.domain_name}领域仍有提升空间，"
                f"成功率 {bottom_domain.success_rate:.1%}"
            )

        return weaknesses

    def _identify_typical_errors(
        self, experiences: List[ExperienceRecord]
    ) -> List[Dict[str, Any]]:
        """
        识别典型错误类型

        统计高频错误模式，按出现频率排序。

        Args:
            experiences: 经验记录列表

        Returns:
            错误类型、频率、占比、示例列表
        """
        if not experiences:
            return []

        error_counter = Counter()
        error_examples: Dict[str, List[str]] = defaultdict(list)

        for exp in experiences:
            for error in exp.errors:
                error_type = self._categorize_error(error)
                error_counter[error_type] += 1
                if len(error_examples[error_type]) < 3:
                    error_examples[error_type].append(error)

        total_errors = sum(error_counter.values())
        if total_errors == 0:
            return []

        typical_errors = []
        for error_type, count in error_counter.most_common(10):
            typical_errors.append(
                {
                    "error_type": error_type,
                    "frequency": count,
                    "percentage": count / total_errors,
                    "examples": error_examples[error_type],
                }
            )

        return typical_errors

    def _categorize_error(self, error: str) -> str:
        """
        对错误进行分类

        Args:
            error: 错误信息

        Returns:
            错误类型
        """
        error_lower = error.lower()

        category_keywords = {
            "网络错误": ["timeout", "connection", "network", "request", "http", "超时", "连接", "网络"],
            "解析错误": ["parse", "decode", "format", "解析", "格式", "编码"],
            "权限错误": ["permission", "access", "denied", "auth", "权限", "访问", "认证"],
            "数据错误": ["data", "missing", "invalid", "null", "数据", "缺失", "无效"],
            "资源错误": ["resource", "memory", "disk", "space", "资源", "内存", "磁盘"],
            "配置错误": ["config", "setting", "配置", "设置"],
            "验证错误": ["validation", "verify", "check", "验证", "校验", "检查"],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in error_lower:
                    return category

        return "其他错误"

    def _determine_improvement_directions(
        self, domains: List[SkillDomain], errors: List[Dict[str, Any]]
    ) -> List[str]:
        """
        确定改进方向

        基于薄弱环节和高频错误。

        Args:
            domains: 技能领域列表
            errors: 典型错误列表

        Returns:
            具体的改进建议列表
        """
        directions = []

        for domain in domains:
            if domain.success_rate < 0.5:
                directions.append(
                    f"重点提升 {domain.domain_name} 领域的任务成功率，"
                    f"当前成功率 {domain.success_rate:.1%}"
                )
            elif domain.avg_efficiency < 0.5 and domain.task_count > 2:
                directions.append(
                    f"优化 {domain.domain_name} 领域的执行效率，"
                    f"当前平均效率 {domain.avg_efficiency:.1%}"
                )

        if errors:
            top_error = errors[0]
            error_type = top_error["error_type"]
            directions.append(
                f"减少 {error_type} 的发生，当前占比 {top_error['percentage']:.1%}"
            )

        if not directions:
            directions.append("继续保持当前表现，追求更高的稳定性和效率")

        return directions

    def _compute_knowledge_boundary(
        self, experiences: List[ExperienceRecord]
    ) -> KnowledgeBoundary:
        """
        计算知识边界

        已知：有足够经验的领域
        前沿：经验较少但正在增长的领域
        未知：无经验的领域（基于已知任务类型推断）

        Args:
            experiences: 经验记录列表

        Returns:
            KnowledgeBoundary 知识边界
        """
        all_task_types = [
            "crawler",
            "processor",
            "analyzer",
            "annotator",
            "validator",
            "other",
        ]

        domain_counts: Dict[str, int] = defaultdict(int)
        domain_timestamps: Dict[str, List[datetime]] = defaultdict(list)

        for exp in experiences:
            domain_counts[exp.task_type] += 1
            domain_timestamps[exp.task_type].append(exp.timestamp)

        known_domains = []
        frontier_domains = []
        confidence_distribution: Dict[str, float] = {}

        for domain, count in domain_counts.items():
            confidence = min(count / 10.0, 1.0)
            confidence_distribution[domain] = confidence

            if count >= 5:
                known_domains.append(domain)
            else:
                frontier_domains.append(domain)

        unknown_domains = [
            t for t in all_task_types if t not in domain_counts
        ]

        known_count = len(known_domains)
        total_types = len(all_task_types)
        overall_certainty = known_count / total_types if total_types > 0 else 0.0

        if confidence_distribution:
            avg_confidence = sum(confidence_distribution.values()) / len(
                confidence_distribution
            )
            overall_certainty = overall_certainty * 0.5 + avg_confidence * 0.5

        return KnowledgeBoundary(
            known_domains=sorted(known_domains),
            unknown_domains=sorted(unknown_domains),
            frontier_domains=sorted(frontier_domains),
            confidence_distribution=confidence_distribution,
            overall_certainty=overall_certainty,
        )

    def _analyze_trend(self, experiences: List[ExperienceRecord]) -> str:
        """
        分析近期趋势

        比较最近10条与更早的经验的成功率变化。

        Args:
            experiences: 经验记录列表

        Returns:
            improving/stable/declining
        """
        if len(experiences) < 20:
            return "stable"

        sorted_exps = sorted(experiences, key=lambda e: e.timestamp, reverse=True)

        recent = sorted_exps[:10]
        earlier = sorted_exps[10:20]

        recent_success = sum(1 for e in recent if e.status == "success") / len(recent)
        earlier_success = sum(1 for e in earlier if e.status == "success") / len(earlier)

        diff = recent_success - earlier_success

        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"

    def _compute_overall_score(self, domains: List[SkillDomain]) -> float:
        """
        计算综合能力评分

        各技能领域的加权平均（按任务数加权）。

        Args:
            domains: 技能领域列表

        Returns:
            综合评分 0-1
        """
        if not domains:
            return 0.0

        total_tasks = sum(d.task_count for d in domains)
        if total_tasks == 0:
            return 0.0

        weighted_sum = 0.0
        for domain in domains:
            domain_score = (
                domain.success_rate * 0.4
                + domain.avg_accuracy * 0.3
                + domain.avg_efficiency * 0.3
            )
            weighted_sum += domain_score * domain.task_count

        return max(0.0, min(1.0, weighted_sum / total_tasks))

    def _generate_default_profile(self, agent_name: str) -> AgentProfile:
        """
        生成默认画像（空经验池）

        Args:
            agent_name: 智能体名称

        Returns:
            默认画像
        """
        return AgentProfile(
            agent_name=agent_name,
            experience_count=0,
            overall_score=0.0,
            strengths=[],
            weaknesses=["经验数据不足，尚未建立技能画像"],
            typical_errors=[],
            improvement_directions=["积累更多经验数据以建立准确的自我认知"],
            skill_domains=[],
            knowledge_boundary=KnowledgeBoundary(
                known_domains=[],
                unknown_domains=[
                    "crawler",
                    "processor",
                    "analyzer",
                    "annotator",
                    "validator",
                    "other",
                ],
                frontier_domains=[],
                confidence_distribution={},
                overall_certainty=0.0,
            ),
            recent_trend="stable",
        )

    def to_json(self, profile: AgentProfile) -> str:
        """
        将画像导出为 JSON 字符串

        Args:
            profile: 智能体画像

        Returns:
            JSON 字符串
        """
        return profile.model_dump_json(indent=2)

    def get_profile_summary(self, profile: AgentProfile) -> Dict[str, Any]:
        """
        获取画像摘要（简化版）

        包含：综合评分、优势Top3、劣势Top3、改进方向Top3。

        Args:
            profile: 智能体画像

        Returns:
            摘要字典
        """
        return {
            "agent_name": profile.agent_name,
            "overall_score": profile.overall_score,
            "experience_count": profile.experience_count,
            "recent_trend": profile.recent_trend,
            "top_strengths": profile.strengths[:3],
            "top_weaknesses": profile.weaknesses[:3],
            "top_improvement_directions": profile.improvement_directions[:3],
            "knowledge_certainty": profile.knowledge_boundary.overall_certainty,
            "known_domains_count": len(profile.knowledge_boundary.known_domains),
        }
