"""
经验数据池模块

提供经验记录的管理、存储、查询和质量评估功能。
"""

from ai_llm_agent_crawler.experience.attribution import (
    AttributionResult,
    ErrorAttributor,
    ErrorCategory,
    ExperienceSummarizer,
    Heuristic,
)
from ai_llm_agent_crawler.experience.models import (
    ExperienceRecord,
    ExperienceType,
    TaskStatus,
    TaskType,
)
from ai_llm_agent_crawler.experience.pool import ExperienceDataPool
from ai_llm_agent_crawler.experience.profile import (
    AgentProfile,
    AgentProfileGenerator,
    KnowledgeBoundary,
    SkillDomain,
)
from ai_llm_agent_crawler.experience.self_assessment import (
    AssessmentDimension,
    DimensionScore,
    SelfAssessment,
    SelfAssessmentConfig,
    SelfAssessmentResult,
)
from ai_llm_agent_crawler.experience.iteration import (
    IterationConfig,
    IterationRecord,
    IterationTriggerType,
    OptimizationStrategyType,
    SkillIterationEngine,
)
from ai_llm_agent_crawler.experience.snapshot import (
    ExperiencePoolSnapshot,
    ExperienceSnapshotManager,
)
from ai_llm_agent_crawler.experience.analytics import (
    ComparisonResult,
    ExperienceComparator,
    PatternMiner,
    TrendAnalysisResult,
    TrendAnalyzer,
    TrendPoint,
)
from ai_llm_agent_crawler.experience.agent import IntrospectiveAgent

__all__ = [
    "ExperienceRecord",
    "ExperienceType",
    "TaskStatus",
    "TaskType",
    "ExperienceDataPool",
    "ExperiencePoolSnapshot",
    "ExperienceSnapshotManager",
    "AssessmentDimension",
    "DimensionScore",
    "SelfAssessment",
    "SelfAssessmentConfig",
    "SelfAssessmentResult",
    "ErrorCategory",
    "AttributionResult",
    "Heuristic",
    "ErrorAttributor",
    "ExperienceSummarizer",
    "SkillDomain",
    "KnowledgeBoundary",
    "AgentProfile",
    "AgentProfileGenerator",
    "IterationTriggerType",
    "OptimizationStrategyType",
    "IterationRecord",
    "IterationConfig",
    "SkillIterationEngine",
    "TrendPoint",
    "TrendAnalysisResult",
    "ComparisonResult",
    "TrendAnalyzer",
    "PatternMiner",
    "ExperienceComparator",
    "IntrospectiveAgent",
]
