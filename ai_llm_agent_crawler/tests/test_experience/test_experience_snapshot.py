"""
经验池快照管理单元测试

测试经验池快照的创建、查询、对比、回滚和删除功能。
"""

import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

from ai_llm_agent_crawler.experience import (
    ExperienceDataPool,
    ExperiencePoolSnapshot,
    ExperienceRecord,
    ExperienceSnapshotManager,
    TaskStatus,
    TaskType,
)


class TestExperiencePoolSnapshot:
    """经验池快照元数据模型测试"""

    def test_create_snapshot_defaults(self):
        """测试创建快照元数据（默认值）"""
        snapshot = ExperiencePoolSnapshot(
            snapshot_id="snap_test_001",
            version="1.0.0",
        )

        assert snapshot.snapshot_id == "snap_test_001"
        assert snapshot.version == "1.0.0"
        assert snapshot.name == ""
        assert snapshot.description == ""
        assert isinstance(snapshot.created_at, datetime)
        assert snapshot.record_count == 0
        assert snapshot.total_size_bytes == 0
        assert snapshot.checksum == ""
        assert snapshot.snapshot_type == "full"
        assert snapshot.status == "completed"
        assert snapshot.metadata == {}

    def test_create_snapshot_with_all_fields(self):
        """测试创建快照元数据（所有字段）"""
        now = datetime.now()
        snapshot = ExperiencePoolSnapshot(
            snapshot_id="snap_test_002",
            version="2.1.3",
            name="测试快照",
            description="这是一个测试快照",
            created_at=now,
            record_count=100,
            total_size_bytes=2048,
            checksum="abc123def456",
            snapshot_type="incremental",
            status="creating",
            metadata={"key": "value", "env": "test"},
        )

        assert snapshot.snapshot_id == "snap_test_002"
        assert snapshot.version == "2.1.3"
        assert snapshot.name == "测试快照"
        assert snapshot.description == "这是一个测试快照"
        assert snapshot.created_at == now
        assert snapshot.record_count == 100
        assert snapshot.total_size_bytes == 2048
        assert snapshot.checksum == "abc123def456"
        assert snapshot.snapshot_type == "incremental"
        assert snapshot.status == "creating"
        assert snapshot.metadata["key"] == "value"


class TestExperienceSnapshotManager:
    """经验池快照管理器测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def snapshot_manager(self, pool, tmp_path):
        """创建快照管理器"""
        storage_dir = str(tmp_path / "snapshots")
        return ExperienceSnapshotManager(pool=pool, storage_dir=storage_dir)

    @pytest.fixture
    def sample_records(self):
        """创建示例记录列表"""
        records = []
        for i in range(5):
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_name_{i}",
                status=TaskStatus.SUCCESS,
                duration_ms=100.0 * i,
                performance_metrics={
                    "accuracy": 0.5 + i * 0.1,
                    "efficiency": 0.4 + i * 0.1,
                },
                input_summary=f"input_{i}",
                output_summary=f"output_{i}",
            )
            records.append(record)
        return records

    def test_create_snapshot_success(self, pool, snapshot_manager, sample_records):
        """测试创建快照成功，元数据正确"""
        for record in sample_records:
            pool.add_record(record)

        snapshot = snapshot_manager.create_snapshot(
            name="测试快照",
            description="测试创建快照",
        )

        assert snapshot.snapshot_id.startswith("snap_")
        assert snapshot.version == "0.1.0"
        assert snapshot.name == "测试快照"
        assert snapshot.description == "测试创建快照"
        assert snapshot.record_count == 5
        assert snapshot.total_size_bytes > 0
        assert snapshot.checksum != ""
        assert snapshot.snapshot_type == "full"
        assert snapshot.status == "completed"
        assert isinstance(snapshot.created_at, datetime)

    def test_create_snapshot_empty_pool(self, pool, snapshot_manager):
        """测试空池创建快照"""
        snapshot = snapshot_manager.create_snapshot(name="空池快照")

        assert snapshot.snapshot_id.startswith("snap_")
        assert snapshot.version == "0.1.0"
        assert snapshot.record_count == 0
        assert snapshot.status == "completed"

    def test_create_multiple_snapshots_version_increment(self, pool, snapshot_manager, sample_records):
        """测试连续创建多个快照，版本号正确递增"""
        for record in sample_records:
            pool.add_record(record)

        snapshot1 = snapshot_manager.create_snapshot(name="快照1")
        assert snapshot1.version == "0.1.0"

        time.sleep(0.01)
        snapshot2 = snapshot_manager.create_snapshot(name="快照2")
        assert snapshot2.version == "0.1.1"

        time.sleep(0.01)
        snapshot3 = snapshot_manager.create_snapshot(name="快照3")
        assert snapshot3.version == "0.1.2"

    def test_create_snapshot_with_custom_version(self, pool, snapshot_manager, sample_records):
        """测试使用自定义版本号创建快照"""
        for record in sample_records:
            pool.add_record(record)

        snapshot = snapshot_manager.create_snapshot(
            name="自定义版本",
            version="2.0.0",
        )

        assert snapshot.version == "2.0.0"

    def test_get_snapshot(self, pool, snapshot_manager, sample_records):
        """测试按ID查询快照"""
        for record in sample_records:
            pool.add_record(record)

        snapshot = snapshot_manager.create_snapshot(name="测试快照")
        retrieved = snapshot_manager.get_snapshot(snapshot.snapshot_id)

        assert retrieved is not None
        assert retrieved.snapshot_id == snapshot.snapshot_id
        assert retrieved.version == snapshot.version
        assert retrieved.name == snapshot.name

    def test_get_nonexistent_snapshot(self, snapshot_manager):
        """测试查询不存在的快照"""
        result = snapshot_manager.get_snapshot("nonexistent_id")
        assert result is None

    def test_list_snapshots_order(self, pool, snapshot_manager, sample_records):
        """测试列出快照按时间倒序"""
        for record in sample_records:
            pool.add_record(record)

        snapshot_ids = []
        for i in range(5):
            time.sleep(0.01)
            snapshot = snapshot_manager.create_snapshot(name=f"快照{i}")
            snapshot_ids.append(snapshot.snapshot_id)

        listed = snapshot_manager.list_snapshots()

        assert len(listed) == 5
        assert listed[0].snapshot_id == snapshot_ids[-1]
        assert listed[-1].snapshot_id == snapshot_ids[0]

    def test_list_snapshots_empty(self, snapshot_manager):
        """测试列出空快照列表"""
        listed = snapshot_manager.list_snapshots()
        assert listed == []

    def test_compare_snapshots_added(self, pool, snapshot_manager):
        """测试快照对比能识别新增记录"""
        record1 = ExperienceRecord(
            task_id="task_1",
            task_type=TaskType.CRAWLER,
            task_name="task_1",
            status=TaskStatus.SUCCESS,
        )
        pool.add_record(record1)

        snapshot1 = snapshot_manager.create_snapshot(name="快照1")

        record2 = ExperienceRecord(
            task_id="task_2",
            task_type=TaskType.PROCESSOR,
            task_name="task_2",
            status=TaskStatus.SUCCESS,
        )
        pool.add_record(record2)

        snapshot2 = snapshot_manager.create_snapshot(name="快照2")

        diff = snapshot_manager.compare_snapshots(snapshot1.snapshot_id, snapshot2.snapshot_id)

        assert diff["summary"]["total_1"] == 1
        assert diff["summary"]["total_2"] == 2
        assert diff["summary"]["added_count"] == 1
        assert diff["summary"]["removed_count"] == 0
        assert diff["summary"]["modified_count"] == 0
        assert len(diff["added"]) == 1
        assert diff["added"][0]["task_id"] == "task_2"

    def test_compare_snapshots_removed(self, pool, snapshot_manager):
        """测试快照对比能识别删除记录"""
        record1 = ExperienceRecord(
            task_id="task_1",
            task_type=TaskType.CRAWLER,
            task_name="task_1",
            status=TaskStatus.SUCCESS,
        )
        pool.add_record(record1)

        record2 = ExperienceRecord(
            task_id="task_2",
            task_type=TaskType.PROCESSOR,
            task_name="task_2",
            status=TaskStatus.SUCCESS,
        )
        pool.add_record(record2)

        snapshot1 = snapshot_manager.create_snapshot(name="快照1")

        pool.delete_record(record1.experience_id)

        snapshot2 = snapshot_manager.create_snapshot(name="快照2")

        diff = snapshot_manager.compare_snapshots(snapshot1.snapshot_id, snapshot2.snapshot_id)

        assert diff["summary"]["total_1"] == 2
        assert diff["summary"]["total_2"] == 1
        assert diff["summary"]["added_count"] == 0
        assert diff["summary"]["removed_count"] == 1
        assert diff["summary"]["modified_count"] == 0
        assert len(diff["removed"]) == 1
        assert diff["removed"][0]["task_id"] == "task_1"

    def test_compare_snapshots_modified(self, pool, snapshot_manager):
        """测试快照对比能识别修改记录"""
        record = ExperienceRecord(
            task_id="task_1",
            task_type=TaskType.CRAWLER,
            task_name="task_1",
            status=TaskStatus.SUCCESS,
            duration_ms=100.0,
        )
        pool.add_record(record)

        snapshot1 = snapshot_manager.create_snapshot(name="快照1")

        record.duration_ms = 200.0
        record.status = TaskStatus.FAILED

        snapshot2 = snapshot_manager.create_snapshot(name="快照2")

        diff = snapshot_manager.compare_snapshots(snapshot1.snapshot_id, snapshot2.snapshot_id)

        assert diff["summary"]["total_1"] == 1
        assert diff["summary"]["total_2"] == 1
        assert diff["summary"]["added_count"] == 0
        assert diff["summary"]["removed_count"] == 0
        assert diff["summary"]["modified_count"] == 1
        assert len(diff["modified"]) == 1

    def test_compare_same_snapshot(self, pool, snapshot_manager, sample_records):
        """测试对比同一个快照"""
        for record in sample_records:
            pool.add_record(record)

        snapshot = snapshot_manager.create_snapshot(name="快照")

        diff = snapshot_manager.compare_snapshots(snapshot.snapshot_id, snapshot.snapshot_id)

        assert diff["summary"]["total_1"] == 5
        assert diff["summary"]["total_2"] == 5
        assert diff["summary"]["added_count"] == 0
        assert diff["summary"]["removed_count"] == 0
        assert diff["summary"]["modified_count"] == 0
        assert diff["added"] == []
        assert diff["removed"] == []
        assert diff["modified"] == []

    def test_compare_nonexistent_snapshot(self, pool, snapshot_manager, sample_records):
        """测试对比不存在的快照"""
        for record in sample_records:
            pool.add_record(record)

        snapshot = snapshot_manager.create_snapshot(name="快照")

        diff = snapshot_manager.compare_snapshots(snapshot.snapshot_id, "nonexistent")

        assert diff["summary"]["added_count"] == 0
        assert diff["summary"]["removed_count"] == 0
        assert diff["summary"]["modified_count"] == 0

    def test_restore_snapshot(self, pool, snapshot_manager, sample_records):
        """测试回滚快照后数据与快照时一致"""
        for record in sample_records:
            pool.add_record(record)

        snapshot = snapshot_manager.create_snapshot(name="基线快照")

        original_ids = set(pool._records.keys())

        for i in range(3):
            new_record = ExperienceRecord(
                task_id=f"new_task_{i}",
                task_type=TaskType.ANALYZER,
                task_name=f"new_task_{i}",
                status=TaskStatus.SUCCESS,
            )
            pool.add_record(new_record)

        assert pool.count() == 8

        result = snapshot_manager.restore_snapshot(snapshot.snapshot_id)

        assert result is True
        assert pool.count() == 5

        restored_ids = set(pool._records.keys())
        assert restored_ids == original_ids

    def test_restore_nonexistent_snapshot(self, pool, snapshot_manager):
        """测试回滚不存在的快照"""
        result = snapshot_manager.restore_snapshot("nonexistent_id")
        assert result is False

    def test_delete_snapshot(self, pool, snapshot_manager, sample_records):
        """测试删除快照后无法再查询到"""
        for record in sample_records:
            pool.add_record(record)

        snapshot = snapshot_manager.create_snapshot(name="待删除快照")
        snapshot_id = snapshot.snapshot_id

        assert snapshot_manager.get_snapshot(snapshot_id) is not None

        result = snapshot_manager.delete_snapshot(snapshot_id)

        assert result is True
        assert snapshot_manager.get_snapshot(snapshot_id) is None

    def test_delete_nonexistent_snapshot(self, snapshot_manager):
        """测试删除不存在的快照"""
        result = snapshot_manager.delete_snapshot("nonexistent_id")
        assert result is False

    def test_get_latest_snapshot(self, pool, snapshot_manager, sample_records):
        """测试获取最新快照"""
        for record in sample_records:
            pool.add_record(record)

        snapshot1 = snapshot_manager.create_snapshot(name="快照1")
        time.sleep(0.01)
        snapshot2 = snapshot_manager.create_snapshot(name="快照2")
        time.sleep(0.01)
        snapshot3 = snapshot_manager.create_snapshot(name="快照3")

        latest = snapshot_manager.get_latest_snapshot()

        assert latest is not None
        assert latest.snapshot_id == snapshot3.snapshot_id
        assert latest.name == "快照3"

    def test_get_latest_snapshot_empty(self, snapshot_manager):
        """测试无快照时获取最新快照"""
        latest = snapshot_manager.get_latest_snapshot()
        assert latest is None

    def test_increment_version(self):
        """测试版本号递增"""
        assert ExperienceSnapshotManager._increment_version("0.1.0") == "0.1.1"
        assert ExperienceSnapshotManager._increment_version("1.0.0") == "1.0.1"
        assert ExperienceSnapshotManager._increment_version("2.3.4") == "2.3.5"

    def test_increment_version_invalid_format(self):
        """测试无效版本号格式"""
        assert ExperienceSnapshotManager._increment_version("invalid") == "0.1.0"
        assert ExperienceSnapshotManager._increment_version("1.0") == "0.1.0"

    def test_snapshot_storage_structure(self, pool, snapshot_manager, sample_records, tmp_path):
        """测试快照存储结构"""
        for record in sample_records:
            pool.add_record(record)

        snapshot = snapshot_manager.create_snapshot(name="结构测试")

        storage_dir = tmp_path / "snapshots"
        snapshot_dir = storage_dir / snapshot.snapshot_id

        assert (storage_dir / "snapshots.json").exists()
        assert snapshot_dir.exists()
        assert (snapshot_dir / "data.json").exists()
        assert (snapshot_dir / "metadata.json").exists()

    def test_snapshot_persistence(self, pool, sample_records, tmp_path):
        """测试快照持久化（重新加载管理器）"""
        storage_dir = str(tmp_path / "snapshots")

        manager1 = ExperienceSnapshotManager(pool=pool, storage_dir=storage_dir)

        for record in sample_records:
            pool.add_record(record)

        snapshot = manager1.create_snapshot(name="持久化测试")

        new_pool = ExperienceDataPool()
        manager2 = ExperienceSnapshotManager(pool=new_pool, storage_dir=storage_dir)

        loaded = manager2.get_snapshot(snapshot.snapshot_id)
        assert loaded is not None
        assert loaded.snapshot_id == snapshot.snapshot_id
        assert loaded.name == "持久化测试"
        assert loaded.record_count == 5

        result = manager2.restore_snapshot(snapshot.snapshot_id)
        assert result is True
        assert new_pool.count() == 5
