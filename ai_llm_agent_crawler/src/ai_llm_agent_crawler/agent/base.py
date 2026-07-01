"""
Agent 基类和核心抽象

定义 Agent 的基本结构、状态管理和核心接口。
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class AgentStatus(str, Enum):
    """Agent 状态枚举"""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SHUTDOWN = "shutdown"


class AgentType(str, Enum):
    """Agent 类型枚举"""

    CRAWLER = "crawler"
    DATASET = "dataset"
    SKILL = "skill"
    ANALYSIS = "analysis"
    ORCHESTRATOR = "orchestrator"
    WORKER = "worker"
    SUPERVISOR = "supervisor"
    LIANGYI = "liangyi"
    DATASCITALK = "datasci_talk"


class AgentConfig(BaseModel):
    """Agent 配置"""

    agent_id: str = Field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:8]}")
    name: str = Field(default="agent")
    agent_type: str = Field(default=AgentType.WORKER)
    description: str = Field(default="")
    version: str = Field(default="1.0.0")

    max_retries: int = Field(default=3)
    timeout_seconds: int = Field(default=300)
    max_concurrent_tasks: int = Field(default=5)

    enable_monitoring: bool = Field(default=True)
    enable_logging: bool = Field(default=True)
    auto_recover: bool = Field(default=True)

    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class AgentContext(BaseModel):
    """Agent 执行上下文"""

    agent_id: str
    session_id: str = Field(default_factory=lambda: f"session_{uuid.uuid4().hex[:8]}")
    start_time: datetime = Field(default_factory=datetime.now)
    current_task_id: Optional[str] = None
    shared_data: Dict[str, Any] = Field(default_factory=dict)
    resource_bindings: Dict[str, str] = Field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class AgentResult(BaseModel):
    """Agent 执行结果"""

    success: bool
    agent_id: str
    task_id: Optional[str] = None
    result_data: Any = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    output_paths: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    """
    Agent 基类

    所有 Agent 都应继承此类，实现核心生命周期方法。
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        初始化 Agent

        Args:
            config: Agent 配置
        """
        self.config = config or AgentConfig()
        self.status: AgentStatus = AgentStatus.CREATED
        self.context: Optional[AgentContext] = None
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self.logger = get_logger(f"{__name__}.{self.config.name}")

    async def initialize(self) -> bool:
        """
        初始化 Agent

        Returns:
            初始化是否成功
        """
        self.status = AgentStatus.INITIALIZING
        self.logger.info(f"正在初始化 Agent: {self.config.agent_id}")

        try:
            self.context = AgentContext(agent_id=self.config.agent_id)
            success = await self._on_initialize()

            if success:
                self.status = AgentStatus.READY
                self.logger.info(f"Agent 初始化成功: {self.config.agent_id}")
                await self._emit_event("initialized", {"agent_id": self.config.agent_id})
            else:
                self.status = AgentStatus.FAILED
                self.logger.error(f"Agent 初始化失败: {self.config.agent_id}")

            return success
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.logger.error(f"Agent 初始化异常: {e}", exc_info=True)
            return False

    async def start(self, **kwargs) -> AgentResult:
        """
        启动 Agent 执行

        Args:
            **kwargs: 执行参数

        Returns:
            执行结果
        """
        if self.status not in [AgentStatus.READY, AgentStatus.PAUSED]:
            self.logger.warning(f"Agent 状态不允许启动: {self.status}")
            return AgentResult(
                success=False,
                agent_id=self.config.agent_id,
                error_message=f"Invalid status: {self.status}",
            )

        self.status = AgentStatus.RUNNING
        start_time = datetime.now()
        self.logger.info(f"Agent 开始执行: {self.config.agent_id}")

        try:
            await self._emit_event("start", {"agent_id": self.config.agent_id})
            result = await self._execute(**kwargs)
            result.start_time = start_time
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - start_time).total_seconds()

            if result.success:
                self.status = AgentStatus.COMPLETED
                await self._emit_event("completed", result.model_dump())
            else:
                self.status = AgentStatus.FAILED
                await self._emit_event("failed", result.model_dump())

            return result
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.logger.error(f"Agent 执行异常: {e}", exc_info=True)
            return AgentResult(
                success=False,
                agent_id=self.config.agent_id,
                error_message=str(e),
                start_time=start_time,
                end_time=datetime.now(),
            )

    async def pause(self) -> bool:
        """
        暂停 Agent

        Returns:
            是否暂停成功
        """
        if self.status != AgentStatus.RUNNING:
            return False

        self.status = AgentStatus.PAUSED
        await self._on_pause()
        await self._emit_event("paused", {"agent_id": self.config.agent_id})
        self.logger.info(f"Agent 已暂停: {self.config.agent_id}")
        return True

    async def resume(self) -> bool:
        """
        恢复 Agent

        Returns:
            是否恢复成功
        """
        if self.status != AgentStatus.PAUSED:
            return False

        self.status = AgentStatus.RUNNING
        await self._on_resume()
        await self._emit_event("resumed", {"agent_id": self.config.agent_id})
        self.logger.info(f"Agent 已恢复: {self.config.agent_id}")
        return True

    async def cancel(self) -> bool:
        """
        取消 Agent 执行

        Returns:
            是否取消成功
        """
        if self.status not in [AgentStatus.RUNNING, AgentStatus.PAUSED, AgentStatus.WAITING]:
            return False

        self.status = AgentStatus.CANCELLED
        await self._on_cancel()
        await self._emit_event("cancelled", {"agent_id": self.config.agent_id})
        self.logger.info(f"Agent 已取消: {self.config.agent_id}")
        return True

    async def shutdown(self) -> None:
        """关闭 Agent"""
        if self.status == AgentStatus.SHUTDOWN:
            return

        await self._on_shutdown()
        self.status = AgentStatus.SHUTDOWN
        await self._emit_event("shutdown", {"agent_id": self.config.agent_id})
        self.logger.info(f"Agent 已关闭: {self.config.agent_id}")

    @abstractmethod
    async def _execute(self, **kwargs) -> AgentResult:
        """
        执行核心逻辑（子类必须实现）

        Returns:
            执行结果
        """
        pass

    async def _on_initialize(self) -> bool:
        """初始化回调，子类可重写"""
        return True

    async def _on_pause(self) -> None:
        """暂停回调，子类可重写"""
        pass

    async def _on_resume(self) -> None:
        """恢复回调，子类可重写"""
        pass

    async def _on_cancel(self) -> None:
        """取消回调，子类可重写"""
        pass

    async def _on_shutdown(self) -> None:
        """关闭回调，子类可重写"""
        pass

    def on(self, event: str, handler: Callable) -> None:
        """
        注册事件处理器

        Args:
            event: 事件名称
            handler: 处理函数
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    async def _emit_event(self, event: str, data: Any) -> None:
        """
        触发事件

        Args:
            event: 事件名称
            data: 事件数据
        """
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"事件处理器异常: {event} - {e}")

    def get_status(self) -> AgentStatus:
        """获取当前状态"""
        return self.status

    def get_config(self) -> AgentConfig:
        """获取配置"""
        return self.config

    def get_context(self) -> Optional[AgentContext]:
        """获取上下文"""
        return self.context

    def set_variable(self, key: str, value: Any) -> None:
        """设置上下文变量"""
        if self.context:
            self.context.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取上下文变量"""
        if self.context:
            return self.context.variables.get(key, default)
        return default
