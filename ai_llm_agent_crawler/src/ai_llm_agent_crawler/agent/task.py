"""
任务定义和执行引擎

提供任务的定义、队列管理、调度执行能力。
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class TaskPriority(str, Enum):
    """任务优先级枚举"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    IMMEDIATE = "immediate"


class TaskType(str, Enum):
    """任务类型枚举"""

    CRAWL = "crawl"
    DATASET_GENERATE = "dataset_generate"
    SKILL_GENERATE = "skill_generate"
    DATA_PROCESS = "data_process"
    ANALYSIS = "analysis"
    TRAIN = "train"
    VALIDATE = "validate"
    EXPORT = "export"
    LIANGYI_GEN = "liangyi_gen"
    DATASCITALK = "datasci_talk"


class TaskConfig(BaseModel):
    """任务配置"""

    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    name: str
    task_type: str = Field(default=TaskType.DATA_PROCESS)
    priority: str = Field(default=TaskPriority.NORMAL)
    description: str = ""

    max_retries: int = 3
    timeout_seconds: int = 300
    retry_delay_seconds: int = 5

    dependencies: List[str] = Field(default_factory=list)
    required_resources: Dict[str, List[str]] = Field(default_factory=dict)

    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class TaskResult(BaseModel):
    """任务结果"""

    task_id: str
    success: bool
    status: str = TaskStatus.COMPLETED
    result_data: Any = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    retry_count: int = 0
    output_paths: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class BaseTask(ABC):
    """
    任务基类

    所有具体任务都应继承此类。
    """

    def __init__(self, config: TaskConfig):
        """
        初始化任务

        Args:
            config: 任务配置
        """
        self.config = config
        self.status: TaskStatus = TaskStatus.PENDING
        self.result: Optional[TaskResult] = None
        self.retry_count: int = 0
        self.created_at: datetime = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self._cancel_requested: bool = False
        self.logger = get_logger(f"{__name__}.{config.name}")

    @abstractmethod
    async def execute(self, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        执行任务（子类必须实现）

        Args:
            context: 执行上下文

        Returns:
            任务结果
        """
        pass

    async def run(self, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        运行任务（包含重试逻辑）

        Args:
            context: 执行上下文

        Returns:
            任务结果
        """
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()

        while self.retry_count <= self.config.max_retries:
            try:
                if self._cancel_requested:
                    self.status = TaskStatus.CANCELLED
                    return TaskResult(
                        task_id=self.config.task_id,
                        success=False,
                        status=TaskStatus.CANCELLED,
                        error_message="Task cancelled",
                        start_time=self.started_at,
                        end_time=datetime.now(),
                        retry_count=self.retry_count,
                    )

                result = await self.execute(context)
                self.result = result
                self.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                self.completed_at = datetime.now()
                result.duration_seconds = (self.completed_at - self.started_at).total_seconds()
                result.retry_count = self.retry_count

                return result

            except asyncio.TimeoutError:
                self.retry_count += 1
                if self.retry_count <= self.config.max_retries:
                    self.status = TaskStatus.RETRYING
                    self.logger.warning(f"任务超时，正在重试 ({self.retry_count}/{self.config.max_retries})")
                    await asyncio.sleep(self.config.retry_delay_seconds)
                else:
                    self.status = TaskStatus.TIMEOUT
                    return TaskResult(
                        task_id=self.config.task_id,
                        success=False,
                        status=TaskStatus.TIMEOUT,
                        error_message="Task timeout after max retries",
                        start_time=self.started_at,
                        end_time=datetime.now(),
                        retry_count=self.retry_count,
                    )

            except Exception as e:
                self.retry_count += 1
                if self.retry_count <= self.config.max_retries:
                    self.status = TaskStatus.RETRYING
                    self.logger.warning(f"任务失败，正在重试 ({self.retry_count}/{self.config.max_retries}): {e}")
                    await asyncio.sleep(self.config.retry_delay_seconds)
                else:
                    self.status = TaskStatus.FAILED
                    self.logger.error(f"任务最终失败: {e}", exc_info=True)
                    return TaskResult(
                        task_id=self.config.task_id,
                        success=False,
                        status=TaskStatus.FAILED,
                        error_message=str(e),
                        start_time=self.started_at,
                        end_time=datetime.now(),
                        retry_count=self.retry_count,
                    )

        return TaskResult(
            task_id=self.config.task_id,
            success=False,
            status=TaskStatus.FAILED,
            error_message="Max retries exceeded",
            start_time=self.started_at,
            end_time=datetime.now(),
            retry_count=self.retry_count,
        )

    def cancel(self) -> None:
        """取消任务"""
        self._cancel_requested = True
        self.status = TaskStatus.CANCELLED
        self.logger.info(f"任务已请求取消: {self.config.task_id}")

    def get_status(self) -> TaskStatus:
        """获取任务状态"""
        return self.status

    def get_config(self) -> TaskConfig:
        """获取任务配置"""
        return self.config


class TaskQueue:
    """
    任务队列

    支持优先级的任务队列管理。
    """

    def __init__(self, max_size: int = 1000):
        """
        初始化任务队列

        Args:
            max_size: 最大队列大小
        """
        self._tasks: Dict[str, BaseTask] = {}
        self._priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self._priority_map = {
            TaskPriority.IMMEDIATE: 0,
            TaskPriority.CRITICAL: 1,
            TaskPriority.HIGH: 2,
            TaskPriority.NORMAL: 3,
            TaskPriority.LOW: 4,
        }
        self.logger = get_logger(f"{__name__}.TaskQueue")

    def enqueue(self, task: BaseTask) -> bool:
        """
        任务入队

        Args:
            task: 任务对象

        Returns:
            是否入队成功
        """
        try:
            priority = self._priority_map.get(task.config.priority, 3)
            task_id = task.config.task_id

            if task_id in self._tasks:
                self.logger.warning(f"任务已存在: {task_id}")
                return False

            self._tasks[task_id] = task
            self._priority_queue.put_nowait((priority, task_id, task))
            task.status = TaskStatus.QUEUED

            self.logger.info(f"任务入队: {task_id} (优先级: {task.config.priority})")
            return True
        except asyncio.QueueFull:
            self.logger.error("任务队列已满")
            return False

    async def dequeue(self) -> Optional[BaseTask]:
        """
        任务出队

        Returns:
            任务对象
        """
        try:
            priority, task_id, task = await self._priority_queue.get()
            if task_id in self._tasks:
                del self._tasks[task_id]
            return task
        except Exception as e:
            self.logger.error(f"任务出队异常: {e}")
            return None

    def peek(self) -> Optional[BaseTask]:
        """查看队首任务（不移除）"""
        if self._priority_queue.empty():
            return None
        return None

    def size(self) -> int:
        """获取队列大小"""
        return self._priority_queue.qsize()

    def is_empty(self) -> bool:
        """队列是否为空"""
        return self._priority_queue.empty()

    def get_task(self, task_id: str) -> Optional[BaseTask]:
        """根据ID获取任务"""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[BaseTask]:
        """列出所有队列中的任务"""
        return list(self._tasks.values())

    def clear(self) -> None:
        """清空队列"""
        while not self._priority_queue.empty():
            try:
                self._priority_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._tasks.clear()
        self.logger.info("任务队列已清空")


class TaskScheduler:
    """
    任务调度器

    负责任务的调度、执行和生命周期管理。
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        queue_max_size: int = 1000,
    ):
        """
        初始化任务调度器

        Args:
            max_concurrent: 最大并发任务数
            queue_max_size: 队列最大大小
        """
        self.max_concurrent = max_concurrent
        self.queue = TaskQueue(max_size=queue_max_size)
        self._running_tasks: Dict[str, BaseTask] = {}
        self._completed_tasks: Dict[str, TaskResult] = {}
        self._is_running: bool = False
        self._workers: List[asyncio.Task] = []
        self._event_handlers: Dict[str, List[Callable]] = {}
        self.logger = get_logger(f"{__name__}.TaskScheduler")

    async def start(self) -> None:
        """启动调度器"""
        if self._is_running:
            return

        self._is_running = True
        self.logger.info("任务调度器已启动")

        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            self._workers.append(worker)

    async def stop(self) -> None:
        """停止调度器"""
        self._is_running = False
        self.logger.info("正在停止任务调度器...")

        for task in self._running_tasks.values():
            task.cancel()

        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self.logger.info("任务调度器已停止")

    async def _worker_loop(self, worker_id: str) -> None:
        """工作协程循环"""
        self.logger.debug(f"工作协程启动: {worker_id}")

        while self._is_running:
            try:
                task = await self.queue.dequeue()
                if task is None:
                    await asyncio.sleep(0.1)
                    continue

                task_id = task.config.task_id
                self._running_tasks[task_id] = task

                self.logger.info(f"[{worker_id}] 开始执行任务: {task_id}")
                await self._emit_event("task_start", task_id)

                result = await task.run()

                self._completed_tasks[task_id] = result
                del self._running_tasks[task_id]

                if result.success:
                    self.logger.info(f"[{worker_id}] 任务完成: {task_id}")
                    await self._emit_event("task_complete", result)
                else:
                    self.logger.error(f"[{worker_id}] 任务失败: {task_id} - {result.error_message}")
                    await self._emit_event("task_failed", result)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"工作协程异常: {worker_id} - {e}", exc_info=True)
                await asyncio.sleep(1)

        self.logger.debug(f"工作协程退出: {worker_id}")

    def submit(self, task: BaseTask) -> str:
        """
        提交任务

        Args:
            task: 任务对象

        Returns:
            任务ID
        """
        task_id = task.config.task_id

        if not self.queue.enqueue(task):
            raise RuntimeError(f"Failed to enqueue task: {task_id}")

        return task_id

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        if task_id in self._completed_tasks:
            return TaskStatus(self._completed_tasks[task_id].status)
        if task_id in self._running_tasks:
            return self._running_tasks[task_id].status
        queued_task = self.queue.get_task(task_id)
        if queued_task:
            return queued_task.status
        return None

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        return self._completed_tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            return True

        queued_task = self.queue.get_task(task_id)
        if queued_task:
            queued_task.cancel()
            return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计"""
        return {
            "queue_size": self.queue.size(),
            "running_tasks": len(self._running_tasks),
            "completed_tasks": len(self._completed_tasks),
            "max_concurrent": self.max_concurrent,
            "is_running": self._is_running,
        }

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
