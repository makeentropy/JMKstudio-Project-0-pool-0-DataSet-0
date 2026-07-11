"""
算法库模块

提供:
- performance_budget: 系统性能预算 (CPU/内存/IO/网络 预算与监控)
- algorithm_pool: 算法 POOL (算法注册表, 按条件选择与执行追踪)
- data_settlement: 数据清算分析 (数据集对账/差异/结算报告)
"""

from ai_llm_agent_crawler.algorithm.algorithm_pool import (
    AlgorithmEntry,
    AlgorithmPool,
    AlgorithmStatus,
    get_default_pool,
    register_algorithm,
)
from ai_llm_agent_crawler.algorithm.data_settlement import (
    SettlementReport,
    SettlementStatus,
    DataSettlement,
)
from ai_llm_agent_crawler.algorithm.performance_budget import (
    BudgetStatus,
    PerformanceBudget,
    ResourceBudget,
    ResourceKind,
    UsageRecord,
)

__all__ = [
    # algorithm_pool
    "AlgorithmEntry",
    "AlgorithmPool",
    "AlgorithmStatus",
    "get_default_pool",
    "register_algorithm",
    # data_settlement
    "SettlementReport",
    "SettlementStatus",
    "DataSettlement",
    # performance_budget
    "BudgetStatus",
    "PerformanceBudget",
    "ResourceBudget",
    "ResourceKind",
    "UsageRecord",
]
