"""
Agent 编排器

提供统一的 Agent 编排、任务调度和资源管理能力。
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.agent.base import (
    AgentConfig,
    AgentContext,
    AgentResult,
    AgentStatus,
    AgentType,
    BaseAgent,
)
from ai_llm_agent_crawler.agent.resource import (
    ResourceManager,
    ResourceType,
)
from ai_llm_agent_crawler.agent.task import (
    BaseTask,
    TaskConfig,
    TaskPriority,
    TaskResult,
    TaskScheduler,
    TaskStatus,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ExecutionStatus(str, Enum):
    """执行计划状态枚举"""

    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionPlan(BaseModel):
    """执行计划"""

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    status: str = ExecutionStatus.DRAFT

    agent_configs: List[Dict[str, Any]] = Field(default_factory=list)
    task_configs: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class OrchestratorConfig(BaseModel):
    """编排器配置"""

    orchestrator_id: str = Field(default_factory=lambda: f"orch_{uuid.uuid4().hex[:8]}")
    name: str = "default_orchestrator"
    max_agents: int = 10
    max_concurrent_tasks: int = 5
    enable_resource_management: bool = True
    enable_task_scheduling: bool = True
    auto_recovery: bool = True

    dataset_base_dir: Optional[str] = None
    skills_dir: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class AgentOrchestrator:
    """
    Agent 编排器

    统一管理 Agent 生命周期、任务调度和资源分配。
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        初始化编排器

        Args:
            config: 编排器配置
        """
        self.config = config or OrchestratorConfig()
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_factories: Dict[str, Callable[..., BaseAgent]] = {}
        self._plans: Dict[str, ExecutionPlan] = {}
        self._is_running: bool = False
        self._event_handlers: Dict[str, List[Callable]] = {}

        self.resource_manager: Optional[ResourceManager] = None
        self.task_scheduler: Optional[TaskScheduler] = None

        self.logger = get_logger(f"{__name__}.{self.config.name}")

    async def initialize(self) -> bool:
        """
        初始化编排器

        Returns:
            是否初始化成功
        """
        self.logger.info(f"正在初始化编排器: {self.config.orchestrator_id}")

        try:
            if self.config.enable_resource_management:
                dataset_dir = Path(self.config.dataset_base_dir) if self.config.dataset_base_dir else None
                skills_dir = Path(self.config.skills_dir) if self.config.skills_dir else None

                self.resource_manager = ResourceManager(
                    dataset_base_dir=dataset_dir,
                    skills_dir=skills_dir,
                )
                self.logger.info("资源管理器已初始化")

            if self.config.enable_task_scheduling:
                self.task_scheduler = TaskScheduler(
                    max_concurrent=self.config.max_concurrent_tasks,
                )
                self.logger.info("任务调度器已初始化")

            self._is_running = True
            self.logger.info(f"编排器初始化完成: {self.config.orchestrator_id}")
            await self._emit_event("initialized", {"orchestrator_id": self.config.orchestrator_id})
            return True

        except Exception as e:
            self.logger.error(f"编排器初始化失败: {e}", exc_info=True)
            return False

    async def shutdown(self) -> None:
        """关闭编排器"""
        self.logger.info("正在关闭编排器...")

        self._is_running = False

        if self.task_scheduler:
            await self.task_scheduler.stop()

        for agent_id, agent in list(self._agents.items()):
            try:
                await agent.shutdown()
            except Exception as e:
                self.logger.error(f"关闭 Agent 失败: {agent_id} - {e}")

        self._agents.clear()
        await self._emit_event("shutdown", {"orchestrator_id": self.config.orchestrator_id})
        self.logger.info("编排器已关闭")

    def register_agent_factory(self, agent_type: str, factory: Callable[..., BaseAgent]) -> None:
        """
        注册 Agent 工厂

        Args:
            agent_type: Agent 类型
            factory: 工厂函数
        """
        self._agent_factories[agent_type] = factory
        self.logger.info(f"已注册 Agent 工厂: {agent_type}")

    async def create_agent(
        self,
        agent_type: str,
        name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        创建 Agent

        Args:
            agent_type: Agent 类型
            name: Agent 名称
            config: 配置参数

        Returns:
            Agent ID
        """
        if len(self._agents) >= self.config.max_agents:
            self.logger.error(f"Agent 数量已达上限: {self.config.max_agents}")
            return None

        if agent_type not in self._agent_factories:
            self.logger.error(f"未找到 Agent 工厂: {agent_type}")
            return None

        try:
            agent_config = AgentConfig(
                name=name,
                agent_type=agent_type,
                **(config or {}),
            )

            factory = self._agent_factories[agent_type]
            agent = factory(agent_config)

            if await agent.initialize():
                self._agents[agent.config.agent_id] = agent
                self.logger.info(f"Agent 创建成功: {agent.config.agent_id} ({name})")
                await self._emit_event("agent_created", {"agent_id": agent.config.agent_id, "name": name})
                return agent.config.agent_id
            else:
                self.logger.error(f"Agent 初始化失败: {name}")
                return None

        except Exception as e:
            self.logger.error(f"创建 Agent 异常: {e}", exc_info=True)
            return None

    async def remove_agent(self, agent_id: str) -> bool:
        """
        移除 Agent

        Args:
            agent_id: Agent ID

        Returns:
            是否移除成功
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        try:
            await agent.shutdown()
            del self._agents[agent_id]

            if self.resource_manager:
                self.resource_manager.release_agent_resources(agent_id)

            self.logger.info(f"Agent 已移除: {agent_id}")
            await self._emit_event("agent_removed", {"agent_id": agent_id})
            return True
        except Exception as e:
            self.logger.error(f"移除 Agent 异常: {agent_id} - {e}")
            return False

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取 Agent"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有 Agent"""
        return [
            {
                "agent_id": agent.config.agent_id,
                "name": agent.config.name,
                "type": agent.config.agent_type,
                "status": agent.status.value,
            }
            for agent in self._agents.values()
        ]

    async def execute_agent(
        self,
        agent_id: str,
        **kwargs,
    ) -> Optional[AgentResult]:
        """
        执行 Agent

        Args:
            agent_id: Agent ID
            **kwargs: 执行参数

        Returns:
            执行结果
        """
        agent = self._agents.get(agent_id)
        if not agent:
            self.logger.error(f"Agent 不存在: {agent_id}")
            return None

        self.logger.info(f"执行 Agent: {agent_id}")
        result = await agent.start(**kwargs)
        return result

    def create_execution_plan(
        self,
        name: str,
        description: str = "",
        agent_configs: Optional[List[Dict[str, Any]]] = None,
        task_configs: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[Dict[str, List[str]]] = None,
    ) -> ExecutionPlan:
        """
        创建执行计划

        Args:
            name: 计划名称
            description: 描述
            agent_configs: Agent 配置列表
            task_configs: 任务配置列表
            dependencies: 依赖关系

        Returns:
            执行计划
        """
        plan = ExecutionPlan(
            name=name,
            description=description,
            agent_configs=agent_configs or [],
            task_configs=task_configs or [],
            dependencies=dependencies or {},
            status=ExecutionStatus.READY,
        )

        self._plans[plan.plan_id] = plan
        self.logger.info(f"执行计划已创建: {plan.plan_id} ({name})")
        return plan

    async def execute_plan(self, plan_id: str) -> bool:
        """
        执行计划

        Args:
            plan_id: 计划ID

        Returns:
            是否启动成功
        """
        plan = self._plans.get(plan_id)
        if not plan:
            self.logger.error(f"执行计划不存在: {plan_id}")
            return False

        if plan.status not in [ExecutionStatus.READY, ExecutionStatus.PAUSED]:
            self.logger.warning(f"执行计划状态不允许执行: {plan.status}")
            return False

        plan.status = ExecutionStatus.RUNNING
        plan.started_at = datetime.now()

        self.logger.info(f"开始执行计划: {plan_id}")
        await self._emit_event("plan_started", {"plan_id": plan_id})

        try:
            for agent_cfg in plan.agent_configs:
                agent_type = agent_cfg.get("type", AgentType.WORKER)
                agent_name = agent_cfg.get("name", f"agent_{uuid.uuid4().hex[:6]}")
                await self.create_agent(agent_type, agent_name, agent_cfg.get("config"))

            await self._emit_event("plan_completed", {"plan_id": plan_id})
            plan.status = ExecutionStatus.COMPLETED
            plan.completed_at = datetime.now()
            return True

        except Exception as e:
            self.logger.error(f"执行计划失败: {e}", exc_info=True)
            plan.status = ExecutionStatus.FAILED
            plan.completed_at = datetime.now()
            return False

    def submit_task(self, task: BaseTask) -> Optional[str]:
        """
        提交任务到调度器

        Args:
            task: 任务对象

        Returns:
            任务ID
        """
        if not self.task_scheduler:
            self.logger.error("任务调度器未启用")
            return None

        task_id = self.task_scheduler.submit(task)
        return task_id

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        if not self.task_scheduler:
            return None
        return self.task_scheduler.get_task_status(task_id)

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        if not self.task_scheduler:
            return None
        return self.task_scheduler.get_task_result(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取编排器统计信息"""
        stats = {
            "orchestrator_id": self.config.orchestrator_id,
            "is_running": self._is_running,
            "total_agents": len(self._agents),
            "max_agents": self.config.max_agents,
            "execution_plans": len(self._plans),
        }

        if self.resource_manager:
            stats["resources"] = self.resource_manager.get_overall_stats()

        if self.task_scheduler:
            stats["tasks"] = self.task_scheduler.get_stats()

        return stats

    def on(self, event: str, handler: Callable) -> None:
        """注册事件处理器"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    async def _emit_event(self, event: str, data: Any) -> None:
        """触发事件"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"事件处理器异常: {event} - {e}")
