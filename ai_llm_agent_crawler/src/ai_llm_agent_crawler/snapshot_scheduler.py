"""
快照自动化调度模块

提供快照策略管理、任务调度和自动清理功能：
- SnapshotPolicy - 快照策略配置
- SnapshotTask - 快照任务跟踪
- SnapshotScheduler - 调度器核心
"""

import schedule
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger
from ai_llm_agent_crawler.versioning.snapshot_manager import SnapshotManager

logger = get_logger(__name__)


class ScheduleType(str, Enum):
    """调度类型"""

    CRON = "cron"
    FIXED_INTERVAL = "fixed_interval"
    MANUAL = "manual"


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SnapshotPolicy(BaseModel):
    """快照策略"""

    policy_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="策略ID",
    )
    name: str = Field(description="策略名称")
    description: str = Field(default="", description="策略描述")
    schedule_type: ScheduleType = Field(description="调度类型")
    schedule_expression: str = Field(default="", description="调度表达式")
    retention_count: int = Field(default=10, description="保留快照数量")
    retention_days: int = Field(default=30, description="保留天数")
    targets: List[str] = Field(default_factory=list, description="目标列表")
    enabled: bool = Field(default=True, description="是否启用")

    class Config:
        use_enum_values = True


class SnapshotTask(BaseModel):
    """快照任务"""

    task_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="任务ID",
    )
    policy_id: str = Field(description="关联策略ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    scheduled_time: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="计划执行时间",
    )
    started_at: Optional[str] = Field(default=None, description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    result: Dict[str, Any] = Field(default_factory=dict, description="执行结果")

    class Config:
        use_enum_values = True


class SnapshotScheduler:
    """快照调度器"""

    def __init__(self, snapshot_manager: Optional[SnapshotManager] = None):
        """
        初始化调度器

        Args:
            snapshot_manager: 快照管理器实例
        """
        self.snapshot_manager = snapshot_manager or SnapshotManager()
        self.policies: Dict[str, SnapshotPolicy] = {}
        self.tasks: Dict[str, SnapshotTask] = {}
        self._schedule_jobs: Dict[str, schedule.Job] = {}
        self._is_running: bool = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_policy(self, policy: SnapshotPolicy) -> SnapshotPolicy:
        """
        添加策略

        Args:
            policy: 策略对象

        Returns:
            添加后的策略
        """
        with self._lock:
            self.policies[policy.policy_id] = policy
            logger.info(f"添加策略: {policy.policy_id}, 名称: {policy.name}")

            if policy.enabled:
                self._schedule_policy(policy)

        return policy

    def remove_policy(self, policy_id: str) -> bool:
        """
        删除策略

        Args:
            policy_id: 策略ID

        Returns:
            是否成功删除
        """
        with self._lock:
            if policy_id not in self.policies:
                logger.warning(f"策略不存在: {policy_id}")
                return False

            self._unschedule_policy(policy_id)
            del self.policies[policy_id]
            logger.info(f"删除策略: {policy_id}")

        return True

    def get_policy(self, policy_id: str) -> Optional[SnapshotPolicy]:
        """
        获取策略

        Args:
            policy_id: 策略ID

        Returns:
            策略对象，不存在返回None
        """
        return self.policies.get(policy_id)

    def list_policies(self) -> List[SnapshotPolicy]:
        """
        列出所有策略

        Returns:
            策略列表
        """
        return list(self.policies.values())

    def enable_policy(self, policy_id: str) -> bool:
        """
        启用策略

        Args:
            policy_id: 策略ID

        Returns:
            是否成功启用
        """
        with self._lock:
            policy = self.policies.get(policy_id)
            if policy is None:
                logger.warning(f"策略不存在: {policy_id}")
                return False

            if policy.enabled:
                logger.warning(f"策略已启用: {policy_id}")
                return False

            policy.enabled = True
            self._schedule_policy(policy)
            logger.info(f"启用策略: {policy_id}")

        return True

    def disable_policy(self, policy_id: str) -> bool:
        """
        禁用策略

        Args:
            policy_id: 策略ID

        Returns:
            是否成功禁用
        """
        with self._lock:
            policy = self.policies.get(policy_id)
            if policy is None:
                logger.warning(f"策略不存在: {policy_id}")
                return False

            if not policy.enabled:
                logger.warning(f"策略已禁用: {policy_id}")
                return False

            policy.enabled = False
            self._unschedule_policy(policy_id)
            logger.info(f"禁用策略: {policy_id}")

        return True

    def trigger_task(self, policy_id: str) -> SnapshotTask:
        """
        触发任务

        Args:
            policy_id: 策略ID

        Returns:
            任务对象
        """
        policy = self.policies.get(policy_id)
        if policy is None:
            raise ValueError(f"策略不存在: {policy_id}")

        task = SnapshotTask(
            policy_id=policy_id,
            scheduled_time=datetime.now().isoformat(),
        )

        with self._lock:
            self.tasks[task.task_id] = task

        self._execute_task(task, policy)

        return task

    def run_scheduler(self) -> None:
        """运行调度器"""
        if self._is_running:
            logger.warning("调度器已运行")
            return

        self._is_running = True

        for policy in self.policies.values():
            if policy.enabled:
                self._schedule_policy(policy)

        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
        )
        self._scheduler_thread.start()

        logger.info("快照调度器已启动")

    def stop_scheduler(self) -> None:
        """停止调度器"""
        if not self._is_running:
            return

        self._is_running = False

        for policy_id in list(self._schedule_jobs.keys()):
            self._unschedule_policy(policy_id)

        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)

        logger.info("快照调度器已停止")

    def _schedule_policy(self, policy: SnapshotPolicy) -> None:
        """
        调度策略

        Args:
            policy: 策略对象
        """
        if policy.policy_id in self._schedule_jobs:
            self._unschedule_policy(policy.policy_id)

        expression = policy.schedule_expression

        try:
            if policy.schedule_type == ScheduleType.CRON:
                job = self._create_cron_job(expression)
            elif policy.schedule_type == ScheduleType.FIXED_INTERVAL:
                interval = int(expression)
                job = schedule.every(interval).seconds
            else:
                return

            if job:
                job.do(self._on_scheduled_task, policy.policy_id)
                self._schedule_jobs[policy.policy_id] = job
                logger.info(f"策略已调度: {policy.policy_id}, 表达式: {expression}")

        except Exception as e:
            logger.error(f"调度策略失败: {policy.policy_id}, 错误: {e}")

    def _create_cron_job(self, cron_expression: str) -> Optional[schedule.Job]:
        """
        根据cron表达式创建调度任务

        Args:
            cron_expression: cron表达式（5个字段）

        Returns:
            schedule.Job对象，解析失败返回None
        """
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            logger.error(f"无效的cron表达式: {cron_expression}")
            return None

        minute, hour, day, month, weekday = parts

        job = schedule.every()

        weekday_map = {
            "0": "sunday",
            "1": "monday",
            "2": "tuesday",
            "3": "wednesday",
            "4": "thursday",
            "5": "friday",
            "6": "saturday",
        }

        if weekday != "*":
            if weekday.isdigit() and weekday in weekday_map:
                job = getattr(job, weekday_map[weekday])
            elif weekday.lower() in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
                job = getattr(job, weekday.lower())
        elif month != "*" and day != "*":
            job = job.month
        elif day != "*":
            job = job.day
        else:
            job = job.day

        time_str = ""
        if hour != "*" or minute != "*":
            h = hour.zfill(2) if hour != "*" else "00"
            m = minute.zfill(2) if minute != "*" else "00"
            time_str = f"{h}:{m}"

        if time_str:
            job = job.at(time_str)

        return job

    def _unschedule_policy(self, policy_id: str) -> None:
        """
        取消策略调度

        Args:
            policy_id: 策略ID
        """
        job = self._schedule_jobs.pop(policy_id, None)
        if job:
            schedule.cancel_job(job)
            logger.info(f"取消策略调度: {policy_id}")

    def _scheduler_loop(self) -> None:
        """调度器循环"""
        while self._is_running:
            schedule.run_pending()
            time.sleep(1)

    def _on_scheduled_task(self, policy_id: str) -> None:
        """
        定时任务回调

        Args:
            policy_id: 策略ID
        """
        logger.info(f"定时任务触发: {policy_id}")
        self.trigger_task(policy_id)

    def _execute_task(self, task: SnapshotTask, policy: SnapshotPolicy) -> None:
        """
        执行任务

        Args:
            task: 任务对象
            policy: 策略对象
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()

        logger.info(f"开始执行任务: {task.task_id}, 策略: {policy.policy_id}")

        try:
            for target in policy.targets:
                self.snapshot_manager.create_full_snapshot(
                    entity_id=target,
                    source_path="",
                    name=f"snapshot_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                )

            self._cleanup_expired_snapshots(policy)

            task.status = TaskStatus.COMPLETED
            task.result = {
                "success": True,
                "targets": policy.targets,
                "message": "快照任务执行成功",
            }
            logger.info(f"任务完成: {task.task_id}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result = {
                "success": False,
                "error": str(e),
            }
            logger.error(f"任务失败: {task.task_id}, 错误: {e}")

        finally:
            task.completed_at = datetime.now().isoformat()

    def _cleanup_expired_snapshots(self, policy: SnapshotPolicy) -> int:
        """
        清理过期快照

        Args:
            policy: 策略对象

        Returns:
            清理的快照数量
        """
        deleted_count = 0

        for target in policy.targets:
            if policy.retention_count > 0:
                deleted = self.snapshot_manager.cleanup_old_snapshots(
                    entity_id=target,
                    keep_count=policy.retention_count,
                )
                deleted_count += deleted

            if policy.retention_days > 0:
                deleted_by_days = self._cleanup_by_days(target, policy.retention_days)
                deleted_count += deleted_by_days

        if deleted_count > 0:
            logger.info(f"清理过期快照: {deleted_count} 个")

        return deleted_count

    def _cleanup_by_days(self, entity_id: str, retention_days: int) -> int:
        """
        按天数清理快照

        Args:
            entity_id: 实体ID
            retention_days: 保留天数

        Returns:
            清理的快照数量
        """
        snapshots = self.snapshot_manager.list_snapshots(entity_id)
        if not snapshots:
            return 0

        cutoff_time = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0

        for snapshot in snapshots:
            created_at = snapshot.created_at
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            if created_at < cutoff_time:
                if self.snapshot_manager.delete_snapshot(
                    entity_id, snapshot.snapshot_id, force=True
                ):
                    deleted_count += 1

        return deleted_count

    def get_task(self, task_id: str) -> Optional[SnapshotTask]:
        """
        获取任务

        Args:
            task_id: 任务ID

        Returns:
            任务对象，不存在返回None
        """
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        policy_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
    ) -> List[SnapshotTask]:
        """
        列出任务

        Args:
            policy_id: 策略ID筛选
            status: 状态筛选

        Returns:
            任务列表
        """
        tasks = list(self.tasks.values())

        if policy_id:
            tasks = [t for t in tasks if t.policy_id == policy_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks


__all__ = [
    "ScheduleType",
    "TaskStatus",
    "SnapshotPolicy",
    "SnapshotTask",
    "SnapshotScheduler",
]