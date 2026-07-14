"""
快照调度器单元测试

测试快照自动化策略的核心功能：
- 策略管理
- 任务调度
- 保留策略执行
- 自动清理
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import pytest

from ai_llm_agent_crawler.snapshot_scheduler import (
    ScheduleType,
    TaskStatus,
    SnapshotPolicy,
    SnapshotTask,
    SnapshotScheduler,
)


class TestSnapshotPolicy:
    """快照策略类测试"""

    def test_policy_creation(self):
        """测试策略创建"""
        policy = SnapshotPolicy(
            name="每日快照",
            description="每天凌晨3点执行快照",
            schedule_type=ScheduleType.CRON,
            schedule_expression="0 3 * * *",
            retention_count=7,
            retention_days=30,
            targets=["vm-001", "vm-002"],
            enabled=True,
        )

        assert policy.name == "每日快照"
        assert policy.description == "每天凌晨3点执行快照"
        assert policy.schedule_type == ScheduleType.CRON
        assert policy.schedule_expression == "0 3 * * *"
        assert policy.retention_count == 7
        assert policy.retention_days == 30
        assert policy.targets == ["vm-001", "vm-002"]
        assert policy.enabled is True
        assert len(policy.policy_id) > 0

    def test_policy_disabled_by_default(self):
        """测试策略默认启用状态"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
        )
        assert policy.enabled is True

    def test_policy_enum_values(self):
        """测试枚举值序列化"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.CRON,
        )
        data = policy.model_dump()
        assert data["schedule_type"] == "cron"


class TestSnapshotTask:
    """快照任务类测试"""

    def test_task_creation(self):
        """测试任务创建"""
        task = SnapshotTask(
            policy_id="policy-123",
        )

        assert task.policy_id == "policy-123"
        assert task.status == TaskStatus.PENDING
        assert len(task.task_id) > 0
        assert len(task.scheduled_time) > 0

    def test_task_status_transition(self):
        """测试任务状态转换"""
        task = SnapshotTask(policy_id="policy-123")

        assert task.status == TaskStatus.PENDING

        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED


class TestSnapshotScheduler:
    """快照调度器测试"""

    @pytest.fixture
    def mock_snapshot_manager(self):
        """创建mock快照管理器"""
        manager = Mock()
        manager.create_full_snapshot.return_value = Mock(snapshot_id="snap-test123")
        manager.cleanup_old_snapshots.return_value = 0
        manager.list_snapshots.return_value = []
        manager.delete_snapshot.return_value = True
        return manager

    @pytest.fixture
    def scheduler(self, mock_snapshot_manager):
        """创建调度器实例"""
        return SnapshotScheduler(snapshot_manager=mock_snapshot_manager)

    def test_add_policy(self, scheduler):
        """测试添加策略"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
        )

        result = scheduler.add_policy(policy)

        assert result is policy
        assert scheduler.get_policy(policy.policy_id) is policy
        assert len(scheduler.list_policies()) == 1

    def test_remove_policy(self, scheduler):
        """测试删除策略"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
        )
        scheduler.add_policy(policy)

        result = scheduler.remove_policy(policy.policy_id)

        assert result is True
        assert scheduler.get_policy(policy.policy_id) is None
        assert len(scheduler.list_policies()) == 0

    def test_remove_nonexistent_policy(self, scheduler):
        """测试删除不存在的策略"""
        result = scheduler.remove_policy("nonexistent")
        assert result is False

    def test_get_policy(self, scheduler):
        """测试获取策略"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
        )
        scheduler.add_policy(policy)

        result = scheduler.get_policy(policy.policy_id)

        assert result is policy

    def test_list_policies(self, scheduler):
        """测试列出策略"""
        policy1 = SnapshotPolicy(name="策略1", schedule_type=ScheduleType.MANUAL)
        policy2 = SnapshotPolicy(name="策略2", schedule_type=ScheduleType.MANUAL)

        scheduler.add_policy(policy1)
        scheduler.add_policy(policy2)

        policies = scheduler.list_policies()

        assert len(policies) == 2
        assert policy1 in policies
        assert policy2 in policies

    def test_enable_policy(self, scheduler):
        """测试启用策略"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            enabled=False,
        )
        scheduler.add_policy(policy)

        result = scheduler.enable_policy(policy.policy_id)

        assert result is True
        assert policy.enabled is True

    def test_disable_policy(self, scheduler):
        """测试禁用策略"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            enabled=True,
        )
        scheduler.add_policy(policy)

        result = scheduler.disable_policy(policy.policy_id)

        assert result is True
        assert policy.enabled is False

    def test_enable_already_enabled_policy(self, scheduler):
        """测试启用已启用的策略"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            enabled=True,
        )
        scheduler.add_policy(policy)

        result = scheduler.enable_policy(policy.policy_id)

        assert result is False

    def test_disable_already_disabled_policy(self, scheduler):
        """测试禁用已禁用的策略"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            enabled=False,
        )
        scheduler.add_policy(policy)

        result = scheduler.disable_policy(policy.policy_id)

        assert result is False

    def test_trigger_task(self, scheduler, mock_snapshot_manager):
        """测试触发任务"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            targets=["vm-001"],
        )
        scheduler.add_policy(policy)

        task = scheduler.trigger_task(policy.policy_id)

        assert task.policy_id == policy.policy_id
        assert task.status == TaskStatus.COMPLETED
        assert task.started_at is not None
        assert task.completed_at is not None
        assert task.result["success"] is True
        assert scheduler.get_task(task.task_id) is task

        mock_snapshot_manager.create_full_snapshot.assert_called_once()

    def test_trigger_task_with_nonexistent_policy(self, scheduler):
        """测试触发不存在策略的任务"""
        with pytest.raises(ValueError, match="策略不存在"):
            scheduler.trigger_task("nonexistent")

    def test_trigger_task_failure(self, scheduler, mock_snapshot_manager):
        """测试任务执行失败"""
        mock_snapshot_manager.create_full_snapshot.side_effect = Exception("快照创建失败")

        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            targets=["vm-001"],
        )
        scheduler.add_policy(policy)

        task = scheduler.trigger_task(policy.policy_id)

        assert task.status == TaskStatus.FAILED
        assert task.result["success"] is False
        assert "快照创建失败" in task.result["error"]

    def test_list_tasks(self, scheduler):
        """测试列出任务"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            targets=["vm-001"],
        )
        scheduler.add_policy(policy)

        task1 = scheduler.trigger_task(policy.policy_id)
        task2 = scheduler.trigger_task(policy.policy_id)

        tasks = scheduler.list_tasks()

        assert len(tasks) == 2
        assert task1 in tasks
        assert task2 in tasks

    def test_list_tasks_by_policy(self, scheduler):
        """测试按策略ID筛选任务"""
        policy1 = SnapshotPolicy(name="策略1", schedule_type=ScheduleType.MANUAL, targets=["vm-001"])
        policy2 = SnapshotPolicy(name="策略2", schedule_type=ScheduleType.MANUAL, targets=["vm-002"])

        scheduler.add_policy(policy1)
        scheduler.add_policy(policy2)

        task1 = scheduler.trigger_task(policy1.policy_id)
        scheduler.trigger_task(policy2.policy_id)

        tasks = scheduler.list_tasks(policy_id=policy1.policy_id)

        assert len(tasks) == 1
        assert task1 in tasks

    def test_list_tasks_by_status(self, scheduler):
        """测试按状态筛选任务"""
        policy = SnapshotPolicy(name="测试策略", schedule_type=ScheduleType.MANUAL, targets=["vm-001"])
        scheduler.add_policy(policy)

        scheduler.trigger_task(policy.policy_id)

        tasks = scheduler.list_tasks(status=TaskStatus.COMPLETED)

        assert len(tasks) == 1
        assert tasks[0].status == TaskStatus.COMPLETED


class TestSnapshotSchedulerRetention:
    """快照调度器保留策略测试"""

    def test_retention_count_policy(self):
        """测试快照保留数量策略"""
        mock_manager = Mock()
        mock_manager.create_full_snapshot.return_value = Mock(snapshot_id="snap-test123")
        mock_manager.cleanup_old_snapshots.return_value = 2
        mock_manager.list_snapshots.return_value = []

        scheduler = SnapshotScheduler(snapshot_manager=mock_manager)

        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            targets=["vm-001"],
            retention_count=5,
            retention_days=0,
        )
        scheduler.add_policy(policy)

        scheduler.trigger_task(policy.policy_id)

        mock_manager.cleanup_old_snapshots.assert_called_once_with(
            entity_id="vm-001",
            keep_count=5,
        )

    def test_retention_days_policy(self):
        """测试快照保留天数策略"""
        mock_manager = Mock()
        mock_manager.create_full_snapshot.return_value = Mock(snapshot_id="snap-test123")
        mock_manager.cleanup_old_snapshots.return_value = 0

        old_snapshot = Mock()
        old_snapshot.created_at = (datetime.now() - timedelta(days=40)).isoformat()
        old_snapshot.snapshot_id = "snap-old"

        new_snapshot = Mock()
        new_snapshot.created_at = (datetime.now() - timedelta(days=10)).isoformat()
        new_snapshot.snapshot_id = "snap-new"

        mock_manager.list_snapshots.return_value = [old_snapshot, new_snapshot]
        mock_manager.delete_snapshot.return_value = True

        scheduler = SnapshotScheduler(snapshot_manager=mock_manager)

        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            targets=["vm-001"],
            retention_count=0,
            retention_days=30,
        )
        scheduler.add_policy(policy)

        scheduler.trigger_task(policy.policy_id)

        mock_manager.delete_snapshot.assert_called_once_with(
            "vm-001", "snap-old", force=True
        )

    def test_combined_retention_policy(self):
        """测试组合保留策略"""
        mock_manager = Mock()
        mock_manager.create_full_snapshot.return_value = Mock(snapshot_id="snap-test123")
        mock_manager.cleanup_old_snapshots.return_value = 1

        old_snapshot = Mock()
        old_snapshot.created_at = (datetime.now() - timedelta(days=40)).isoformat()
        old_snapshot.snapshot_id = "snap-old"

        mock_manager.list_snapshots.return_value = [old_snapshot]
        mock_manager.delete_snapshot.return_value = True

        scheduler = SnapshotScheduler(snapshot_manager=mock_manager)

        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            targets=["vm-001"],
            retention_count=5,
            retention_days=30,
        )
        scheduler.add_policy(policy)

        scheduler.trigger_task(policy.policy_id)

        mock_manager.cleanup_old_snapshots.assert_called_once()
        mock_manager.delete_snapshot.assert_called_once()


class TestSnapshotSchedulerScheduling:
    """快照调度器定时任务测试"""

    @pytest.fixture
    def mock_snapshot_manager(self):
        """创建mock快照管理器"""
        manager = Mock()
        manager.create_full_snapshot.return_value = Mock(snapshot_id="snap-test123")
        manager.cleanup_old_snapshots.return_value = 0
        manager.list_snapshots.return_value = []
        manager.delete_snapshot.return_value = True
        return manager

    @pytest.fixture
    def scheduler(self, mock_snapshot_manager):
        """创建调度器实例"""
        return SnapshotScheduler(snapshot_manager=mock_snapshot_manager)

    def test_fixed_interval_scheduling(self, scheduler):
        """测试固定间隔调度"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.FIXED_INTERVAL,
            schedule_expression="5",
            targets=["vm-001"],
        )

        scheduler.add_policy(policy)

        assert policy.policy_id in scheduler._schedule_jobs

    def test_cron_scheduling(self, scheduler):
        """测试Cron调度"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.CRON,
            schedule_expression="0 3 * * *",
            targets=["vm-001"],
        )

        scheduler.add_policy(policy)

        assert policy.policy_id in scheduler._schedule_jobs

    def test_manual_scheduling_not_scheduled(self, scheduler):
        """测试手动类型不被调度"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.MANUAL,
            targets=["vm-001"],
        )

        scheduler.add_policy(policy)

        assert policy.policy_id not in scheduler._schedule_jobs

    def test_scheduler_run_stop(self, scheduler):
        """测试调度器启动和停止"""
        scheduler.run_scheduler()

        assert scheduler._is_running is True
        assert scheduler._scheduler_thread is not None
        assert scheduler._scheduler_thread.is_alive()

        scheduler.stop_scheduler()

        assert scheduler._is_running is False
        assert scheduler._scheduler_thread.is_alive() is False

    def test_scheduler_run_already_running(self, scheduler):
        """测试调度器重复启动"""
        scheduler.run_scheduler()

        scheduler.run_scheduler()

        assert scheduler._is_running is True

        scheduler.stop_scheduler()

    def test_scheduled_task_trigger(self, scheduler, mock_snapshot_manager):
        """测试定时任务触发"""
        policy = SnapshotPolicy(
            name="测试策略",
            schedule_type=ScheduleType.FIXED_INTERVAL,
            schedule_expression="1",
            targets=["vm-001"],
        )

        scheduler.add_policy(policy)
        scheduler.run_scheduler()

        time.sleep(2)

        tasks = scheduler.list_tasks(policy_id=policy.policy_id)
        assert len(tasks) >= 1

        scheduler.stop_scheduler()