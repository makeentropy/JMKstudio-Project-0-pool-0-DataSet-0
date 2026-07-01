"""
Agent 统一编排模块

提供 Agent 生命周期管理、资源调度、任务编排能力，
整合 dataset（数据集）、skill（技能）、pool（存储池）三大核心资源。

模块组成:
- base: Agent 基类和核心抽象
- orchestrator: Agent 编排器，统一调度管理
- resource: 资源管理器（dataset/skill/pool）
- task: 任务定义和执行引擎
"""

from ai_llm_agent_crawler.agent.base import (
    AgentStatus,
    AgentType,
    AgentConfig,
    BaseAgent,
    AgentContext,
    AgentResult,
)
from ai_llm_agent_crawler.agent.orchestrator import (
    AgentOrchestrator,
    OrchestratorConfig,
    ExecutionPlan,
    ExecutionStatus,
)
from ai_llm_agent_crawler.agent.resource import (
    ResourceType,
    ResourceStatus,
    ResourceInfo,
    ResourceManager,
    DatasetPoolManager,
    SkillPoolManager,
    StoragePoolManager,
)
from ai_llm_agent_crawler.agent.task import (
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskConfig,
    BaseTask,
    TaskResult,
    TaskScheduler,
    TaskQueue,
)

__all__ = [
    # Base
    "AgentStatus",
    "AgentType",
    "AgentConfig",
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    # Orchestrator
    "AgentOrchestrator",
    "OrchestratorConfig",
    "ExecutionPlan",
    "ExecutionStatus",
    # Resource
    "ResourceType",
    "ResourceStatus",
    "ResourceInfo",
    "ResourceManager",
    "DatasetPoolManager",
    "SkillPoolManager",
    "StoragePoolManager",
    # Task
    "TaskStatus",
    "TaskPriority",
    "TaskType",
    "TaskConfig",
    "BaseTask",
    "TaskResult",
    "TaskScheduler",
    "TaskQueue",
]
