"""
爬虫任务调度和队列管理模块

提供：
- 任务队列管理（支持优先级）
- 并发任务调度
- 任务状态跟踪
- 任务结果收集
- 任务依赖管理
- 任务重试机制
- 任务超时处理
- 任务统计分析
"""

import asyncio
import heapq
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    
    PENDING = "pending"          # 待执行
    QUEUED = "queued"            # 已入队
    RUNNING = "running"          # 正在执行
    PAUSED = "paused"            # 已暂停
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 已失败
    CANCELLED = "cancelled"      # 已取消
    TIMEOUT = "timeout"          # 超时
    RETRYING = "retrying"        # 正在重试


class TaskPriority(int, Enum):
    """任务优先级枚举"""
    
    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 15
    CRITICAL = 20


class TaskResult(BaseModel):
    """任务结果"""
    
    task_id: str = Field(description="任务ID")
    status: TaskStatus = Field(description="任务状态")
    result: Any = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    end_time: Optional[str] = Field(default=None, description="结束时间")
    elapsed_time: float = Field(default=0.0, description="耗时（秒）")
    retry_count: int = Field(default=0, description="重试次数")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class CrawlerTask(BaseModel):
    """爬虫任务"""
    
    # 任务标识
    task_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="任务ID",
    )
    name: str = Field(default="", description="任务名称")
    
    # 任务类型和参数
    task_type: str = Field(default="crawl", description="任务类型")
    target: str = Field(description="目标（URL、关键词等）")
    params: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    
    # 优先级和状态
    priority: int = Field(default=TaskPriority.NORMAL, description="优先级")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="状态")
    
    # 依赖关系
    dependencies: List[str] = Field(default_factory=list, description="依赖任务ID列表")
    
    # 重试配置
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_count: int = Field(default=0, description="当前重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟")
    
    # 超时配置
    timeout: float = Field(default=60.0, description="超时时间（秒）")
    
    # 时间信息
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间",
    )
    started_at: Optional[str] = Field(default=None, description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    
    # 执行者信息
    crawler_type: Optional[str] = Field(default=None, description="爬虫类型")
    
    # 结果
    result: Optional[TaskResult] = Field(default=None, description="执行结果")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    tags: List[str] = Field(default_factory=list, description="标签")
    
    # 队列信息（用于优先级队列）
    queue_position: int = Field(default=0, description="队列位置")
    
    class Config:
        use_enum_values = True
    
    def __lt__(self, other: "CrawlerTask") -> bool:
        """比较运算符（用于优先级队列）"""
        # 优先级越高（数值越大），越先执行
        return self.priority > other.priority
    
    def is_ready(self, completed_tasks: List[str]) -> bool:
        """
        检查任务是否准备好执行
        
        Args:
            completed_tasks: 已完成的任务ID列表
            
        Returns:
            是否准备好
        """
        if self.status != TaskStatus.PENDING:
            return False
        
        # 检查依赖是否都已完成
        for dep_id in self.dependencies:
            if dep_id not in completed_tasks:
                return False
        
        return True
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries
    
    def record_retry(self) -> None:
        """记录重试"""
        self.retry_count += 1
        self.status = TaskStatus.RETRYING
    
    def record_start(self) -> None:
        """记录开始"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now().isoformat()
    
    def record_success(self, result: Any) -> None:
        """记录成功"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()
        
        start_time = datetime.fromisoformat(self.started_at) if self.started_at else datetime.now()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        self.result = TaskResult(
            task_id=self.task_id,
            status=TaskStatus.COMPLETED,
            result=result,
            start_time=self.started_at,
            end_time=self.completed_at,
            elapsed_time=elapsed,
            retry_count=self.retry_count,
        )
    
    def record_failure(self, error: str) -> None:
        """记录失败"""
        if self.can_retry():
            self.status = TaskStatus.RETRYING
            self.retry_count += 1
        else:
            self.status = TaskStatus.FAILED
            self.completed_at = datetime.now().isoformat()
        
        start_time = datetime.fromisoformat(self.started_at) if self.started_at else datetime.now()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        self.result = TaskResult(
            task_id=self.task_id,
            status=self.status,
            error=error,
            start_time=self.started_at,
            end_time=self.completed_at,
            elapsed_time=elapsed,
            retry_count=self.retry_count,
        )
    
    def record_timeout(self) -> None:
        """记录超时"""
        self.status = TaskStatus.TIMEOUT
        self.completed_at = datetime.now().isoformat()
        
        start_time = datetime.fromisoformat(self.started_at) if self.started_at else datetime.now()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        self.result = TaskResult(
            task_id=self.task_id,
            status=TaskStatus.TIMEOUT,
            error="Task timeout",
            start_time=self.started_at,
            end_time=self.completed_at,
            elapsed_time=elapsed,
            retry_count=self.retry_count,
        )
    
    def cancel(self) -> None:
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now().isoformat()
    
    def pause(self) -> None:
        """暂停任务"""
        self.status = TaskStatus.PAUSED
    
    def resume(self) -> None:
        """恢复任务"""
        self.status = TaskStatus.PENDING


class SchedulerConfig(BaseModel):
    """调度器配置"""
    
    # 并发配置
    max_concurrent_tasks: int = Field(default=10, description="最大并发任务数")
    max_concurrent_per_crawler: int = Field(default=5, description="每类爬虫最大并发数")
    
    # 队列配置
    max_queue_size: int = Field(default=1000, description="最大队列大小")
    queue_timeout: float = Field(default=300.0, description="队列等待超时")
    
    # 任务配置
    default_timeout: float = Field(default=60.0, description="默认任务超时")
    default_max_retries: int = Field(default=3, description="默认最大重试次数")
    default_retry_delay: float = Field(default=1.0, description="默认重试延迟")
    
    # 调度策略
    scheduling_strategy: str = Field(
        default="priority",
        description="调度策略（priority/fifo/round_robin）",
    )
    
    # 统计配置
    enable_statistics: bool = Field(default=True, description="启用统计")
    statistics_interval: int = Field(default=60, description="统计间隔（秒）")
    
    # 回调配置
    on_task_complete: Optional[str] = Field(default=None, description="任务完成回调")
    on_task_fail: Optional[str] = Field(default=None, description="任务失败回调")


class TaskQueue:
    """
    任务队列
    
    支持优先级队列和多种调度策略。
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queue: List[CrawlerTask] = []  # 优先级队列
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
    
    async def put(
        self,
        task: CrawlerTask,
        block: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        将任务放入队列
        
        Args:
            task: 任务对象
            block: 是否阻塞等待
            timeout: 等待超时
            
        Returns:
            是否成功放入
        """
        async with self._not_full:
            # 检查队列是否已满
            if len(self._queue) >= self.max_size:
                if not block:
                    return False
                try:
                    await asyncio.wait_for(
                        self._not_full.wait(),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    return False
            
            # 加入队列（使用堆维护优先级）
            heapq.heappush(self._queue, task)
            task.status = TaskStatus.QUEUED
            task.queue_position = len(self._queue)
            
            # 通知消费者
            self._not_empty.notify()
            
            logger.debug(f"任务入队: {task.task_id}, 优先级: {task.priority}")
            return True
    
    async def get(
        self,
        block: bool = True,
        timeout: Optional[float] = None,
    ) -> Optional[CrawlerTask]:
        """
        从队列获取任务
        
        Args:
            block: 是否阻塞等待
            timeout: 等待超时
            
        Returns:
            任务对象，队列为空时返回None
        """
        async with self._not_empty:
            # 检查队列是否为空
            if not self._queue:
                if not block:
                    return None
                try:
                    await asyncio.wait_for(
                        self._not_empty.wait(),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    return None
            
            # 从队列取出（优先级最高的）
            if self._queue:
                task = heapq.heappop(self._queue)
                # 更新队列位置
                for i, t in enumerate(self._queue):
                    t.queue_position = i + 1
                
                # 通知生产者
                self._not_full.notify()
                
                logger.debug(f"任务出队: {task.task_id}, 优先级: {task.priority}")
                return task
            
            return None
    
    async def peek(self) -> Optional[CrawlerTask]:
        """
        查看队列顶部任务（不移除）
        
        Returns:
            任务对象
        """
        async with self._lock:
            if self._queue:
                return self._queue[0]
            return None
    
    async def remove(self, task_id: str) -> Optional[CrawlerTask]:
        """
        移除指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            移除的任务
        """
        async with self._lock:
            for i, task in enumerate(self._queue):
                if task.task_id == task_id:
                    self._queue.remove(task)
                    heapq.heapify(self._queue)  # 重新堆化
                    return task
            return None
    
    async def clear(self) -> List[CrawlerTask]:
        """清空队列"""
        async with self._lock:
            tasks = self._queue.copy()
            self._queue.clear()
            return tasks
    
    def size(self) -> int:
        """获取队列大小"""
        return len(self._queue)
    
    def is_empty(self) -> bool:
        """检查队列是否为空"""
        return len(self._queue) == 0
    
    def is_full(self) -> bool:
        """检查队列是否已满"""
        return len(self._queue) >= self.max_size
    
    async def get_all_tasks(self) -> List[CrawlerTask]:
        """获取所有任务（不移除）"""
        async with self._lock:
            return sorted(self._queue, reverse=True)  # 按优先级排序
    
    async def get_tasks_by_status(
        self,
        status: TaskStatus,
    ) -> List[CrawlerTask]:
        """获取指定状态的任务"""
        async with self._lock:
            return [
                task for task in self._queue
                if task.status == status
            ]
    
    async def get_tasks_by_priority(
        self,
        min_priority: int = TaskPriority.LOW,
        max_priority: int = TaskPriority.CRITICAL,
    ) -> List[CrawlerTask]:
        """获取指定优先级范围的任务"""
        async with self._lock:
            return [
                task for task in self._queue
                if min_priority <= task.priority <= max_priority
            ]


class TaskScheduler:
    """
    任务调度器
    
    功能：
    - 任务队列管理
    - 并发任务调度
    - 任务状态跟踪
    - 任务执行和结果收集
    - 任务重试机制
    - 任务超时处理
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        
        # 任务队列
        self.task_queue = TaskQueue(self.config.max_queue_size)
        
        # 执行器注册表
        self._executors: Dict[str, Callable] = {}
        
        # 运行中的任务
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._running_count: int = 0
        
        # 任务状态跟踪
        self._all_tasks: Dict[str, CrawlerTask] = {}
        self._completed_tasks: List[str] = []
        self._failed_tasks: List[str] = []
        
        # 并发控制
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)
        self._crawler_semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # 调度器状态
        self._is_running: bool = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "timeout_tasks": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
        }
        
        # 回调函数
        self._callbacks: Dict[str, Callable] = {}
    
    def register_executor(
        self,
        task_type: str,
        executor: Callable,
    ) -> None:
        """
        注册任务执行器
        
        Args:
            task_type: 任务类型
            executor: 执行函数（异步函数）
        """
        self._executors[task_type] = executor
        self._crawler_semaphores[task_type] = asyncio.Semaphore(
            self.config.max_concurrent_per_crawler
        )
        logger.info(f"注册执行器: {task_type}")
    
    def register_callback(
        self,
        event: str,
        callback: Callable,
    ) -> None:
        """
        注册回调函数
        
        Args:
            event: 事件名称（task_complete, task_fail等）
            callback: 回调函数
        """
        self._callbacks[event] = callback
        logger.info(f"注册回调: {event}")
    
    async def submit_task(
        self,
        task: CrawlerTask,
    ) -> str:
        """
        提交任务
        
        Args:
            task: 任务对象
            
        Returns:
            任务ID
        """
        # 设置默认值
        task.timeout = task.timeout or self.config.default_timeout
        task.max_retries = task.max_retries or self.config.default_max_retries
        task.retry_delay = task.retry_delay or self.config.default_retry_delay
        
        # 添加到任务跟踪
        self._all_tasks[task.task_id] = task
        self._stats["total_tasks"] += 1
        
        # 放入队列
        await self.task_queue.put(task)
        
        logger.info(f"提交任务: {task.task_id}, 类型: {task.task_type}, 优先级: {task.priority}")
        return task.task_id
    
    async def submit_batch(
        self,
        targets: List[str],
        task_type: str = "crawl",
        priority: int = TaskPriority.NORMAL,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        批量提交任务
        
        Args:
            targets: 目标列表
            task_type: 任务类型
            priority: 优先级
            params: 公共参数
            
        Returns:
            任务ID列表
        """
        task_ids = []
        params = params or {}
        
        for target in targets:
            task = CrawlerTask(
                task_type=task_type,
                target=target,
                priority=priority,
                params=params.copy(),
            )
            task_id = await self.submit_task(task)
            task_ids.append(task_id)
        
        logger.info(f"批量提交任务: {len(task_ids)}个")
        return task_ids
    
    async def start(self) -> None:
        """启动调度器"""
        if self._is_running:
            logger.warning("调度器已启动")
            return
        
        self._is_running = True
        self._scheduler_task = asyncio.create_task(self._schedule_loop())
        
        logger.info("任务调度器已启动")
    
    async def stop(self) -> None:
        """停止调度器"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # 取消调度任务
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # 等待运行中的任务完成
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        logger.info("任务调度器已停止")
    
    async def _schedule_loop(self) -> None:
        """调度循环"""
        while self._is_running:
            try:
                # 获取下一个任务
                task = await self.task_queue.get(block=True, timeout=1.0)
                
                if task is None:
                    continue
                
                # 检查依赖
                if task.dependencies and not task.is_ready(self._completed_tasks):
                    # 依赖未完成，重新放回队列
                    await self.task_queue.put(task)
                    await asyncio.sleep(0.1)
                    continue
                
                # 检查状态
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                # 等待并发许可
                await self._semaphore.acquire()
                
                # 创建执行任务
                asyncio_task = asyncio.create_task(self._execute_task(task))
                self._running_tasks[task.task_id] = asyncio_task
                self._running_count += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"调度循环错误: {e}")
                await asyncio.sleep(1.0)
    
    async def _execute_task(self, task: CrawlerTask) -> None:
        """
        执行单个任务
        
        Args:
            task: 任务对象
        """
        task.record_start()
        logger.info(f"开始执行任务: {task.task_id}")
        
        try:
            # 获取执行器
            executor = self._executors.get(task.task_type)
            if executor is None:
                raise ValueError(f"未注册执行器: {task.task_type}")
            
            # 获取爬虫特定并发许可
            crawler_semaphore = self._crawler_semaphores.get(task.task_type)
            if crawler_semaphore:
                await crawler_semaphore.acquire()
            
            try:
                # 执行任务（带超时）
                result = await asyncio.wait_for(
                    executor(task.target, **task.params),
                    timeout=task.timeout,
                )
                
                # 记录成功
                task.record_success(result)
                self._completed_tasks.append(task.task_id)
                self._stats["completed_tasks"] += 1
                
                logger.info(
                    f"任务完成: {task.task_id}, "
                    f"耗时: {task.result.elapsed_time:.2f}s"
                )
                
                # 执行回调
                if "task_complete" in self._callbacks:
                    await self._callbacks["task_complete"](task)
                
            except asyncio.TimeoutError:
                # 超时处理
                task.record_timeout()
                self._stats["timeout_tasks"] += 1
                
                logger.warning(f"任务超时: {task.task_id}, 超时: {task.timeout}s")
                
                # 检查是否重试
                if task.can_retry():
                    await self._retry_task(task)
                else:
                    self._failed_tasks.append(task.task_id)
                    self._stats["failed_tasks"] += 1
                    
                    if "task_fail" in self._callbacks:
                        await self._callbacks["task_fail"](task)
            
            except Exception as e:
                # 错误处理
                task.record_failure(str(e))
                
                logger.error(f"任务失败: {task.task_id}, 错误: {e}")
                
                # 检查是否重试
                if task.can_retry():
                    await self._retry_task(task)
                else:
                    self._failed_tasks.append(task.task_id)
                    self._stats["failed_tasks"] += 1
                    
                    if "task_fail" in self._callbacks:
                        await self._callbacks["task_fail"](task)
            
            finally:
                # 释放爬虫并发许可
                if crawler_semaphore:
                    crawler_semaphore.release()
        
        finally:
            # 释放全局并发许可
            self._semaphore.release()
            
            # 移除运行记录
            self._running_tasks.pop(task.task_id, None)
            self._running_count -= 1
    
    async def _retry_task(self, task: CrawlerTask) -> None:
        """
        重试任务
        
        Args:
            task: 任务对象
        """
        task.record_retry()
        
        # 等待重试延迟
        retry_delay = task.retry_delay * (2 ** task.retry_count)  # 指数退避
        await asyncio.sleep(retry_delay)
        
        # 重置任务状态并重新提交
        task.status = TaskStatus.PENDING
        await self.task_queue.put(task)
        
        logger.info(
            f"重试任务: {task.task_id}, "
            f"第{task.retry_count}次重试, "
            f"延迟{retry_delay}s"
        )
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        # 检查运行中的任务
        if task_id in self._running_tasks:
            asyncio_task = self._running_tasks[task_id]
            asyncio_task.cancel()
            
            task = self._all_tasks.get(task_id)
            if task:
                task.cancel()
                self._stats["cancelled_tasks"] += 1
            
            logger.info(f"取消运行中任务: {task_id}")
            return True
        
        # 检查队列中的任务
        task = await self.task_queue.remove(task_id)
        if task:
            task.cancel()
            self._stats["cancelled_tasks"] += 1
            logger.info(f"取消队列任务: {task_id}")
            return True
        
        return False
    
    async def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功暂停
        """
        task = await self.task_queue.remove(task_id)
        if task:
            task.pause()
            # 暂停的任务不重新放回队列
            logger.info(f"暂停任务: {task_id}")
            return True
        
        return False
    
    async def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功恢复
        """
        task = self._all_tasks.get(task_id)
        if task and task.status == TaskStatus.PAUSED:
            task.resume()
            await self.task_queue.put(task)
            logger.info(f"恢复任务: {task_id}")
            return True
        
        return False
    
    def get_task(self, task_id: str) -> Optional[CrawlerTask]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务对象
        """
        return self._all_tasks.get(task_id)
    
    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果
        """
        task = self._all_tasks.get(task_id)
        if task:
            return task.result
        return None
    
    def get_running_tasks(self) -> List[CrawlerTask]:
        """获取运行中的任务"""
        return [
            self._all_tasks[task_id]
            for task_id in self._running_tasks.keys()
            if task_id in self._all_tasks
        ]
    
    def get_pending_tasks(self) -> List[CrawlerTask]:
        """获取待执行的任务"""
        return [
            task for task in self._all_tasks.values()
            if task.status == TaskStatus.PENDING or task.status == TaskStatus.QUEUED
        ]
    
    def get_completed_tasks(self) -> List[CrawlerTask]:
        """获取已完成的任务"""
        return [
            self._all_tasks[task_id]
            for task_id in self._completed_tasks
            if task_id in self._all_tasks
        ]
    
    def get_failed_tasks(self) -> List[CrawlerTask]:
        """获取失败的任务"""
        return [
            self._all_tasks[task_id]
            for task_id in self._failed_tasks
            if task_id in self._all_tasks
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = dict(self._stats)
        
        # 计算平均时间
        completed = self.get_completed_tasks()
        if completed:
            total_time = sum(
                t.result.elapsed_time for t in completed
                if t.result and t.result.elapsed_time
            )
            stats["avg_time"] = total_time / len(completed)
        
        # 运行状态
        stats["is_running"] = self._is_running
        stats["running_count"] = self._running_count
        stats["queue_size"] = self.task_queue.size()
        
        # 各状态任务数
        stats["pending_count"] = len(self.get_pending_tasks())
        stats["running_count"] = len(self.get_running_tasks())
        
        return stats
    
    async def wait_for_completion(
        self,
        task_ids: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, TaskResult]:
        """
        等待任务完成
        
        Args:
            task_ids: 等待的任务ID列表，None表示等待所有
            timeout: 等待超时
            
        Returns:
            任务结果字典
        """
        if task_ids is None:
            # 等待所有任务
            task_ids = list(self._all_tasks.keys())
        
        start_time = time.time()
        results = {}
        
        while True:
            # 检查所有任务是否完成
            all_done = True
            for task_id in task_ids:
                task = self._all_tasks.get(task_id)
                if task:
                    if task.status in [
                        TaskStatus.COMPLETED,
                        TaskStatus.FAILED,
                        TaskStatus.CANCELLED,
                        TaskStatus.TIMEOUT,
                    ]:
                        if task.result:
                            results[task_id] = task.result
                    else:
                        all_done = False
            
            if all_done:
                break
            
            # 检查超时
            if timeout:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    break
            
            await asyncio.sleep(0.5)
        
        return results
    
    async def shutdown(self, wait: bool = True) -> None:
        """
        关闭调度器
        
        Args:
            wait: 是否等待运行任务完成
        """
        await self.stop()
        
        if wait:
            # 等待运行中的任务
            await self.wait_for_completion(timeout=60.0)
        
        # 清空队列
        await self.task_queue.clear()
        
        logger.info("调度器已关闭")


class AsyncTaskManager:
    """
    异步任务管理器
    
    提供简单的任务管理和监控接口。
    """
    
    def __init__(self, scheduler: TaskScheduler):
        self.scheduler = scheduler
    
    async def crawl_urls(
        self,
        urls: List[str],
        crawler_type: str = "http",
        priority: int = TaskPriority.NORMAL,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """
        爬取URL列表
        
        Args:
            urls: URL列表
            crawler_type: 爬虫类型
            priority: 优先级
            timeout: 超时
            
        Returns:
            爬取结果字典
        """
        task_ids = await self.scheduler.submit_batch(
            targets=urls,
            task_type=crawler_type,
            priority=priority,
            params={"timeout": timeout},
        )
        
        results = await self.scheduler.wait_for_completion(task_ids)
        
        return {
            task_id: result.result
            for task_id, result in results.items()
            if result.result is not None
        }
    
    async def search_query(
        self,
        query: str,
        engine: str = "duckduckgo",
        priority: int = TaskPriority.NORMAL,
    ) -> Any:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            engine: 搜索引擎
            priority: 优先级
            
        Returns:
            搜索结果
        """
        task = CrawlerTask(
            task_type="search",
            target=query,
            priority=priority,
            params={"engine": engine},
        )
        
        task_id = await self.scheduler.submit_task(task)
        results = await self.scheduler.wait_for_completion([task_id])
        
        if task_id in results and results[task_id].result:
            return results[task_id].result
        
        return None
    
    def get_progress(self) -> Dict[str, Any]:
        """获取进度信息"""
        stats = self.scheduler.get_stats()
        
        total = stats["total_tasks"]
        completed = stats["completed_tasks"]
        
        progress = {
            "total": total,
            "completed": completed,
            "failed": stats["failed_tasks"],
            "running": stats["running_count"],
            "pending": stats["pending_count"],
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "avg_time": stats["avg_time"],
        }
        
        return progress
    
    async def monitor(
        self,
        interval: float = 5.0,
        callback: Optional[Callable] = None,
    ) -> None:
        """
        监控任务进度
        
        Args:
            interval: 监控间隔
            callback: 进度回调函数
        """
        while self.scheduler._is_running:
            progress = self.get_progress()
            
            if callback:
                await callback(progress)
            else:
                logger.info(
                    f"进度: {progress['completed']}/{progress['total']} "
                    f"({progress['progress_percent']:.1f}%), "
                    f"运行: {progress['running']}, "
                    f"待执行: {progress['pending']}"
                )
            
            # 检查是否完成
            if progress["running"] == 0 and progress["pending"] == 0:
                break
            
            await asyncio.sleep(interval)