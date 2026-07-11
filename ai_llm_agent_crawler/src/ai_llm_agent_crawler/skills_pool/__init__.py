"""
Skills Pool 模块

提供 skills/dataset 集赞积攒与性能效率 POOL 能力：
- :class:`Skill` / :class:`DatasetEntry` —— 数据空间中的可沉淀条目；
- :class:`SkillsPool` —— 开放性能效率 POOL，支持登记、检索、点赞（集赞）、清算；
- :class:`EfficiencyTracker` —— 跟踪迭代省效率版本，输出加速比与累计节省。
"""

from ai_llm_agent_crawler.skills_pool.models import (
    Skill,
    DatasetEntry,
    PoolEntry,
    PerformanceMetric,
)
from ai_llm_agent_crawler.skills_pool.pool import SkillsPool
from ai_llm_agent_crawler.skills_pool.efficiency import EfficiencyTracker

__all__ = [
    "Skill",
    "DatasetEntry",
    "PoolEntry",
    "PerformanceMetric",
    "SkillsPool",
    "EfficiencyTracker",
]
