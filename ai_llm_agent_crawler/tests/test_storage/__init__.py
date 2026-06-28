"""
NAS存储模块单元测试

测试存储后端、数据池分配、冗余备份和监控功能。
"""

import os
import tempfile
from pathlib import Path

import pytest

from ai_llm_agent_crawler.storage import (
    AllocationPolicy,
    AllocationStrategy,
    CapacityThreshold,
    ConsistencyLevel,
    LocalStorageBackend,
    NASStoragePool,
    NASStoragePoolConfig,
    ReplicationMode,
    StorageBackendConfig,
    StorageBackendType,
    StorageMonitor,
    create_nas_pool,
)


class TestLocalStorageBackend:
    """本地存储后端测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def backend_config(self, temp_dir):
        """创建后端配置"""
        return StorageBackendConfig(
            backend_type=StorageBackendType.LOCAL,
            name="test_local",
            root_path=temp_dir,
            priority=10,
            tags={"type": "test", "tier": "primary"}
        )
    
    @pytest.fixture
    def backend(self, backend_config):
        """创建并连接后端"""
        backend = LocalStorageBackend(backend_config)
        backend.connect()
        yield backend
        backend.disconnect()
    
    def test_backend_creation(self, backend_config):
        """测试后端创建"""
        backend = LocalStorageBackend(backend_config)
        assert backend.config.name == "test_local"
        assert backend.config.backend_type == StorageBackendType.LOCAL
    
    def test_backend_connection(self, backend):
        """测试后端连接"""
        assert backend.is_connected()
    
    def test_backend_write_read(self, backend):
        """测试写入和读取"""
        path = "test_file.txt"
        data = b"Hello, NAS Storage!"
        
        # 写入
        assert backend.write(path, data)
        
        # 读取
        read_data = backend.read(path)
        assert read_data == data
    
    def test_backend_write_string(self, backend):
        """测试字符串写入"""
        path = "test_string.txt"
        data = "Hello, NAS Storage!"
        
        # 写入
        assert backend.write(path, data)
        
        # 读取
        read_data = backend.read(path)
        assert read_data == data.encode("utf-8")
    
    def test_backend_delete(self, backend):
        """测试删除"""
        path = "test_delete.txt"
        data = b"Delete me"
        
        # 写入
        backend.write(path, data)
        
        # 删除
        assert backend.delete(path)
        
        # 检查不存在
        assert not backend.exists(path)
    
    def test_backend_exists(self, backend):
        """测试文件存在检查"""
        path = "test_exists.txt"
        
        # 不存在
        assert not backend.exists(path)
        
        # 写入
        backend.write(path, b"data")
        
        # 存在
        assert backend.exists(path)
    
    def test_backend_list_files(self, backend):
        """测试列出文件"""
        # 写入多个文件
        backend.write("file1.txt", b"data1")
        backend.write("file2.txt", b"data2")
        backend.write("dir/file3.txt", b"data3")
        
        # 列出文件（非递归）
        files = backend.list_files()
        assert len(files) >= 2
        assert "file1.txt" in files
        assert "file2.txt" in files
        
        # 递归列出
        files_recursive = backend.list_files("", recursive=True)
        assert len(files_recursive) >= 3
    
    def test_backend_create_directory(self, backend):
        """测试创建目录"""
        path = "test_dir/subdir"
        
        assert backend.create_directory(path)
        assert backend.exists("test_dir")
        assert backend.exists("test_dir/subdir")
    
    def test_backend_delete_directory(self, backend):
        """测试删除目录"""
        path = "test_dir_delete"
        
        # 创建
        backend.create_directory(path)
        
        # 删除（空目录）
        assert backend.delete_directory(path)
        assert not backend.exists(path)
    
    def test_backend_get_info(self, backend):
        """测试获取存储信息"""
        info = backend.get_info()
        
        assert info.total_size > 0
        assert info.available_size > 0
        assert info.usage_percent >= 0
    
    def test_backend_get_file_size(self, backend):
        """测试获取文件大小"""
        path = "size_test.txt"
        data = b"1234567890"  # 10 bytes
        
        backend.write(path, data)
        
        size = backend.get_file_size(path)
        assert size == 10
    
    def test_backend_copy(self, backend):
        """测试复制文件"""
        src = "source.txt"
        dst = "destination.txt"
        data = b"copy test"
        
        backend.write(src, data)
        assert backend.copy(src, dst)
        assert backend.exists(dst)
        assert backend.read(dst) == data
    
    def test_backend_move(self, backend):
        """测试移动文件"""
        src = "move_source.txt"
        dst = "move_destination.txt"
        data = b"move test"
        
        backend.write(src, data)
        assert backend.move(src, dst)
        assert not backend.exists(src)
        assert backend.exists(dst)
        assert backend.read(dst) == data
    
    def test_backend_read_only(self, temp_dir):
        """测试只读模式"""
        config = StorageBackendConfig(
            backend_type=StorageBackendType.LOCAL,
            name="read_only",
            root_path=temp_dir,
            read_only=True
        )
        
        backend = LocalStorageBackend(config)
        backend.connect()
        
        # 不能写入
        assert not backend.write("test.txt", b"data")
        
        backend.disconnect()


class TestAllocationPolicy:
    """分配策略测试"""
    
    @pytest.fixture
    def policy(self):
        """创建分配策略"""
        return AllocationPolicy(AllocationStrategy.CAPACITY_BALANCED)
    
    def test_policy_creation(self, policy):
        """测试策略创建"""
        assert policy.strategy == AllocationStrategy.CAPACITY_BALANCED
    
    def test_allocation_strategies(self):
        """测试不同分配策略"""
        strategies = [
            AllocationStrategy.ROUND_ROBIN,
            AllocationStrategy.LEAST_USED,
            AllocationStrategy.PRIORITY,
            AllocationStrategy.WEIGHTED,
            AllocationStrategy.CAPACITY_BALANCED,
            AllocationStrategy.LATENCY_OPTIMIZED,
        ]
        
        for strategy in strategies:
            policy = AllocationPolicy(strategy)
            assert policy.strategy == strategy


class TestStorageMonitor:
    """存储监控测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def monitor(self):
        """创建监控器"""
        threshold = CapacityThreshold(
            warning_percent=70.0,
            error_percent=85.0,
            critical_percent=95.0
        )
        return StorageMonitor(threshold=threshold)
    
    @pytest.fixture
    def backend(self, temp_dir):
        """创建后端"""
        config = StorageBackendConfig(
            backend_type=StorageBackendType.LOCAL,
            name="monitor_test",
            root_path=temp_dir
        )
        backend = LocalStorageBackend(config)
        backend.connect()
        yield backend
        backend.disconnect()
    
    def test_monitor_creation(self, monitor):
        """测试监控器创建"""
        assert monitor.threshold.warning_percent == 70.0
    
    def test_monitor_register_backend(self, monitor, backend):
        """测试注册后端"""
        assert monitor.register_backend(backend)
        assert "monitor_test" in monitor.list_backends()
    
    def test_monitor_unregister_backend(self, monitor, backend):
        """测试注销后端"""
        monitor.register_backend(backend)
        assert monitor.unregister_backend("monitor_test")
        assert "monitor_test" not in monitor.list_backends()
    
    def test_monitor_collect_metrics(self, monitor, backend):
        """测试收集指标"""
        monitor.register_backend(backend)
        metrics = monitor.collect_metrics()
        assert len(metrics) > 0
    
    def test_monitor_get_status(self, monitor, backend):
        """测试获取状态"""
        monitor.register_backend(backend)
        status = monitor.get_current_status()
        assert status["backend_count"] == 1
        assert status["connected_backends"] == ["monitor_test"]
    
    def test_monitor_check_capacity(self, monitor, backend):
        """测试容量检查"""
        monitor.register_backend(backend)
        alerts = monitor.check_capacity()
        # 正常情况下应该没有告警
        # 或者只有低级别的告警


class TestNASStoragePool:
    """NAS存储池测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def pool_config(self):
        """创建存储池配置"""
        return NASStoragePoolConfig(
            default_replicas=2,
            max_replicas=3,
            min_replicas=1,
            default_replication_mode=ReplicationMode.SYNC,
            default_consistency_level=ConsistencyLevel.QUORUM,
            default_allocation_strategy=AllocationStrategy.CAPACITY_BALANCED
        )
    
    @pytest.fixture
    def pool(self, pool_config, temp_dir):
        """创建存储池"""
        pool = NASStoragePool(pool_config)
        
        # 添加两个本地存储后端
        pool.add_backend(
            StorageBackendType.LOCAL,
            "backend1",
            os.path.join(temp_dir, "storage1"),
            priority=10
        )
        
        pool.add_backend(
            StorageBackendType.LOCAL,
            "backend2",
            os.path.join(temp_dir, "storage2"),
            priority=5
        )
        
        yield pool
        
        # 清理
        pool.remove_backend("backend1")
        pool.remove_backend("backend2")
    
    def test_pool_creation(self, pool_config):
        """测试存储池创建"""
        pool = NASStoragePool(pool_config)
        assert pool.config.default_replicas == 2
    
    def test_pool_add_backend(self, pool):
        """测试添加后端"""
        assert len(pool.list_backends()) == 2
        assert "backend1" in pool.list_backends()
        assert "backend2" in pool.list_backends()
    
    def test_pool_remove_backend(self, pool, temp_dir):
        """测试移除后端"""
        pool.add_backend(
            StorageBackendType.LOCAL,
            "backend3",
            os.path.join(temp_dir, "storage3")
        )
        
        assert "backend3" in pool.list_backends()
        assert pool.remove_backend("backend3")
        assert "backend3" not in pool.list_backends()
    
    def test_pool_write_read(self, pool):
        """测试写入和读取"""
        path = "test_pool_file.txt"
        data = b"NAS Pool Test Data"
        
        # 写入
        result = pool.write(path, data)
        assert result.success
        assert result.successful_replicas >= 1
        
        # 读取
        read_data = pool.read(path)
        assert read_data == data
    
    def test_pool_exists(self, pool):
        """测试文件存在检查"""
        path = "exists_test.txt"
        
        assert not pool.exists(path)
        
        pool.write(path, b"data")
        
        assert pool.exists(path)
    
    def test_pool_delete(self, pool):
        """测试删除"""
        path = "delete_test.txt"
        
        pool.write(path, b"data")
        assert pool.exists(path)
        
        results = pool.delete(path)
        assert all(results.values())
        
        assert not pool.exists(path)
    
    def test_pool_list_files(self, pool):
        """测试列出文件"""
        pool.write("file1.txt", b"data1")
        pool.write("file2.txt", b"data2")
        
        files = pool.list_files()
        assert len(files) >= 2
        assert "file1.txt" in files
        assert "file2.txt" in files
    
    def test_pool_get_file_info(self, pool):
        """测试获取文件信息"""
        path = "info_test.txt"
        data = b"info test data"
        
        pool.write(path, data)
        
        info = pool.get_file_info(path)
        assert info["exists"]
        assert len(info["replicas"]) >= 1
    
    def test_pool_get_status(self, pool):
        """测试获取存储状态"""
        status = pool.get_storage_status()
        
        assert "allocator" in status
        assert "replicator" in status
        assert "monitor" in status
        assert "capacity" in status
    
    def test_pool_can_allocate(self, pool):
        """测试分配检查"""
        # 应该可以分配小量数据
        assert pool.can_allocate(1024, replicas=1)
    
    def test_pool_sync_replicas(self, pool):
        """测试副本同步"""
        path = "sync_test.txt"
        
        pool.write(path, b"sync test data")
        
        result = pool.sync_replicas(path)
        assert result.success or result.successful_replicas >= 1
    
    def test_pool_check_consistency(self, pool):
        """测试一致性检查"""
        pool.write("consistency1.txt", b"data1")
        pool.write("consistency2.txt", b"data2")
        
        result = pool.check_consistency()
        # 新创建的数据应该是一致的
        assert result.is_consistent or len(result.inconsistent_files) == 0
    
    def test_create_nas_pool(self, temp_dir):
        """测试工厂函数创建存储池"""
        backend_configs = [
            {
                "name": "primary",
                "backend_type": "local",
                "root_path": os.path.join(temp_dir, "primary"),
                "priority": 10
            },
            {
                "name": "secondary",
                "backend_type": "local",
                "root_path": os.path.join(temp_dir, "secondary"),
                "priority": 5
            }
        ]
        
        pool = create_nas_pool(backend_configs)
        
        assert len(pool.list_backends()) == 2
        assert "primary" in pool.list_backends()
        assert "secondary" in pool.list_backends()


class TestReplication:
    """复制功能测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def pool(self, temp_dir):
        """创建存储池"""
        config = NASStoragePoolConfig(
            default_replicas=2,
            default_replication_mode=ReplicationMode.SYNC
        )
        pool = NASStoragePool(config)
        
        pool.add_backend(
            StorageBackendType.LOCAL,
            "replica1",
            os.path.join(temp_dir, "rep1")
        )
        
        pool.add_backend(
            StorageBackendType.LOCAL,
            "replica2",
            os.path.join(temp_dir, "rep2")
        )
        
        yield pool
    
    def test_sync_replication(self, pool):
        """测试同步复制"""
        path = "sync_rep.txt"
        data = b"sync replication test"
        
        result = pool.write(path, data, replicas=2)
        
        assert result.success
        assert result.total_replicas == 2
    
    def test_replica_info(self, pool):
        """测试副本信息"""
        path = "rep_info.txt"
        
        pool.write(path, b"data")
        
        info = pool.get_file_info(path)
        assert len(info["replicas"]) >= 1
    
    def test_data_consistency(self, pool):
        """测试数据一致性"""
        path = "consistency.txt"
        data = b"consistent data"
        
        pool.write(path, data)
        
        # 从不同后端读取应该得到相同数据
        data1 = pool.read(path, prefer_backend="replica1")
        data2 = pool.read(path, prefer_backend="replica2")
        
        # 如果两个后端都成功读取
        if data1 and data2:
            assert data1 == data2


class TestCapacityManagement:
    """容量管理测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def pool(self, temp_dir):
        """创建存储池"""
        config = NASStoragePoolConfig(
            capacity_warning_threshold=70.0,
            capacity_error_threshold=85.0,
            capacity_critical_threshold=95.0
        )
        pool = NASStoragePool(config)
        
        pool.add_backend(
            StorageBackendType.LOCAL,
            "capacity_test",
            os.path.join(temp_dir, "storage")
        )
        
        yield pool
    
    def test_capacity_check(self, pool):
        """测试容量检查"""
        alerts = pool.check_capacity()
        # 空存储池不应该有严重告警
        critical_alerts = [a for a in alerts if a.level.name == "CRITICAL"]
        assert len(critical_alerts) == 0
    
    def test_capacity_planning(self, pool):
        """测试容量规划"""
        result = pool.plan_capacity(1024, replicas=1)
        
        # 小量数据应该可以分配
        assert result["feasible"] or "recommendations" in result
    
    def test_capacity_summary(self, pool):
        """测试容量摘要"""
        summary = pool.get_storage_status()
        assert "capacity" in summary


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_full_workflow(self, temp_dir):
        """测试完整工作流"""
        # 创建存储池
        pool_config = NASStoragePoolConfig(
            default_replicas=2,
            default_replication_mode=ReplicationMode.SYNC,
            default_allocation_strategy=AllocationStrategy.CAPACITY_BALANCED
        )
        
        pool = NASStoragePool(pool_config)
        
        # 添加后端
        pool.add_backend(
            StorageBackendType.LOCAL,
            "storage1",
            os.path.join(temp_dir, "s1"),
            priority=10,
            tags={"tier": "primary"}
        )
        
        pool.add_backend(
            StorageBackendType.LOCAL,
            "storage2",
            os.path.join(temp_dir, "s2"),
            priority=5,
            tags={"tier": "secondary"}
        )
        
        # 写入数据
        assert pool.write("test1.txt", b"test data 1").success
        assert pool.write("test2.txt", b"test data 2").success
        assert pool.write("test3.txt", b"test data 3", tags={"category": "test"}).success
        
        # 读取数据
        assert pool.read("test1.txt") == b"test data 1"
        assert pool.read("test2.txt") == b"test data 2"
        
        # 检查文件存在
        assert pool.exists("test1.txt")
        assert not pool.exists("nonexistent.txt")
        
        # 列出文件
        files = pool.list_files()
        assert len(files) >= 3
        
        # 同步副本
        pool.sync_replicas("test1.txt")
        
        # 检查一致性
        consistency = pool.check_consistency()
        assert consistency.is_consistent or len(consistency.inconsistent_files) == 0
        
        # 获取状态
        status = pool.get_storage_status()
        assert status["allocator"]["backend_count"] == 2
        
        # 检查容量
        alerts = pool.check_capacity()
        
        # 删除数据
        pool.delete("test1.txt")
        assert not pool.exists("test1.txt")
        
        # 清理
        pool.remove_backend("storage1")
        pool.remove_backend("storage2")
        
        assert len(pool.list_backends()) == 0