"""DatasetPoolManager数据集池管理器单元测试。"""
import pytest
import os
import json
import tempfile
import shutil

from oath_toolchain.tools.dataset_pool.pool_manager import DatasetPoolManager
from oath_toolchain.tools.dataset_pool.dataset import Dataset
from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag


class TestDatasetPoolManager:
    """测试DatasetPoolManager类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = DatasetPoolManager(pool_path=self.test_dir)

    def teardown_method(self):
        """每个测试后的清理。"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """测试初始化。"""
        assert self.manager.pool_path == os.path.abspath(self.test_dir)
        assert os.path.exists(self.manager.pool_path)
        assert os.path.exists(self.manager.data_dir)
        assert os.path.exists(self.manager.index_path)

    def test_initialization_default_path(self):
        """测试默认路径初始化。"""
        manager = DatasetPoolManager()
        assert manager.pool_path is not None
        assert os.path.exists(manager.pool_path)

    def test_create_dataset(self):
        """测试创建数据集。"""
        data = {"records": [{"id": 1, "name": "test"}]}
        dataset = self.manager.create_dataset(
            name="测试数据集",
            data=data,
            format="json",
            description="测试描述",
        )

        assert dataset.name == "测试数据集"
        assert dataset.description == "测试描述"
        assert dataset.format == "json"
        assert dataset.data == data
        assert dataset.dataset_id in self.manager._index
        assert os.path.exists(self.manager._get_dataset_path(dataset.dataset_id))

    def test_create_dataset_minimal(self):
        """测试最小参数创建数据集。"""
        dataset = self.manager.create_dataset(name="最小数据集")
        assert dataset.name == "最小数据集"
        assert dataset.data is None

    def test_delete_dataset(self):
        """测试删除数据集。"""
        dataset = self.manager.create_dataset(name="待删除")
        dataset_id = dataset.dataset_id

        result = self.manager.delete_dataset(dataset_id)
        assert result is True
        assert dataset_id not in self.manager._index
        assert not os.path.exists(self.manager._get_dataset_path(dataset_id))

    def test_delete_dataset_not_found(self):
        """测试删除不存在的数据集。"""
        result = self.manager.delete_dataset("nonexistent")
        assert result is False

    def test_get_dataset(self):
        """测试获取数据集。"""
        original = self.manager.create_dataset(
            name="测试",
            data={"key": "value"},
        )

        retrieved = self.manager.get_dataset(original.dataset_id)
        assert retrieved is not None
        assert retrieved.dataset_id == original.dataset_id
        assert retrieved.name == "测试"
        assert retrieved.data == {"key": "value"}

    def test_get_dataset_not_found(self):
        """测试获取不存在的数据集。"""
        result = self.manager.get_dataset("nonexistent")
        assert result is None

    def test_update_dataset_data(self):
        """测试更新数据集数据。"""
        dataset = self.manager.create_dataset(
            name="测试",
            data={"old": "data"},
        )

        new_data = {"new": "data", "records": [1, 2, 3]}
        updated = self.manager.update_dataset(
            dataset_id=dataset.dataset_id,
            data=new_data,
        )

        assert updated is not None
        assert updated.data == new_data
        assert updated.record_count == 3

    def test_update_dataset_metadata(self):
        """测试更新数据集元数据。"""
        dataset = self.manager.create_dataset(name="测试")

        updated = self.manager.update_dataset(
            dataset_id=dataset.dataset_id,
            metadata={"author": "test", "version": "1.0"},
        )

        assert updated is not None
        assert updated.metadata["author"] == "test"
        assert updated.metadata["version"] == "1.0"

    def test_update_dataset_not_found(self):
        """测试更新不存在的数据集。"""
        result = self.manager.update_dataset(
            dataset_id="nonexistent",
            data={"key": "value"},
        )
        assert result is None

    def test_list_datasets(self):
        """测试列出数据集。"""
        self.manager.create_dataset(name="数据集1")
        self.manager.create_dataset(name="数据集2")
        self.manager.create_dataset(name="数据集3")

        datasets = self.manager.list_datasets()
        assert len(datasets) == 3

    def test_list_datasets_with_limit(self):
        """测试带限制的列出数据集。"""
        for i in range(10):
            self.manager.create_dataset(name=f"数据集{i}")

        datasets = self.manager.list_datasets(limit=5)
        assert len(datasets) == 5

    def test_list_datasets_with_offset(self):
        """测试带偏移的列出数据集。"""
        for i in range(10):
            self.manager.create_dataset(name=f"数据集{i}")

        datasets = self.manager.list_datasets(limit=5, offset=5)
        assert len(datasets) == 5

    def test_list_datasets_with_filters(self):
        """测试带过滤条件的列出数据集。"""
        self.manager.create_dataset(name="数据集1", format="json")
        self.manager.create_dataset(name="数据集2", format="csv")
        self.manager.create_dataset(name="数据集3", format="json")

        datasets = self.manager.list_datasets(filters={"format": "json"})
        assert len(datasets) == 2
        for ds in datasets:
            assert ds.format == "json"

    def test_search_by_tags(self):
        """测试按标签搜索数据集。"""
        tag1 = KarmaTag(datafor="训练数据", datefor="20240101")
        tag2 = KarmaTag(datafor="测试数据", datefor="20240102")

        ds1 = self.manager.create_dataset(name="数据集1")
        ds1.add_tag(tag1)
        self.manager.save_dataset(ds1)

        ds2 = self.manager.create_dataset(name="数据集2")
        ds2.add_tag(tag2)
        self.manager.save_dataset(ds2)

        ds3 = self.manager.create_dataset(name="数据集3")

        results = self.manager.search_by_tags({"datafor": "训练数据"})
        assert len(results) >= 1
        assert any(ds.dataset_id == ds1.dataset_id for ds in results)

    def test_search_by_tags_no_match(self):
        """测试按标签搜索无匹配。"""
        self.manager.create_dataset(name="数据集1")

        results = self.manager.search_by_tags({"datafor": "不存在的"})
        assert len(results) == 0

    def test_import_dataset_json(self):
        """测试导入JSON数据集。"""
        import_file = os.path.join(self.test_dir, "import_test.json")
        data = {"records": [{"id": 1}, {"id": 2}]}
        with open(import_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        dataset = self.manager.import_dataset(import_file)
        assert dataset.name == "import_test.json"
        assert dataset.format == "json"
        assert dataset.data == data
        assert dataset.record_count == 2

    def test_import_dataset_csv(self):
        """测试导入CSV数据集。"""
        import csv
        import_file = os.path.join(self.test_dir, "import_test.csv")
        with open(import_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name"])
            writer.writeheader()
            writer.writerow({"id": "1", "name": "test1"})
            writer.writerow({"id": "2", "name": "test2"})

        dataset = self.manager.import_dataset(import_file)
        assert dataset.format == "csv"
        assert dataset.record_count == 2

    def test_import_dataset_file_not_found(self):
        """测试导入不存在的文件。"""
        with pytest.raises(FileNotFoundError):
            self.manager.import_dataset("/nonexistent/path.json")

    def test_export_dataset_json(self):
        """测试导出JSON数据集。"""
        data = {"records": [{"id": 1, "name": "test"}]}
        dataset = self.manager.create_dataset(name="导出测试", data=data)

        export_path = os.path.join(self.test_dir, "export_test.json")
        result = self.manager.export_dataset(dataset.dataset_id, export_path)

        assert os.path.exists(result)
        with open(result, "r", encoding="utf-8") as f:
            exported_data = json.load(f)
        assert exported_data == data

    def test_export_dataset_csv(self):
        """测试导出CSV数据集。"""
        data = {"records": [{"id": "1", "name": "test1"}, {"id": "2", "name": "test2"}]}
        dataset = self.manager.create_dataset(name="导出测试", data=data, format="csv")

        export_path = os.path.join(self.test_dir, "export_test.csv")
        result = self.manager.export_dataset(dataset.dataset_id, export_path, format="csv")

        assert os.path.exists(result)

    def test_export_dataset_not_found(self):
        """测试导出不存在的数据集。"""
        with pytest.raises(ValueError, match="数据集不存在"):
            self.manager.export_dataset("nonexistent", "/tmp/out.json")

    def test_get_pool_stats(self):
        """测试获取池统计信息。"""
        self.manager.create_dataset(name="数据集1", data={"key": "value1"})
        self.manager.create_dataset(name="数据集2", data={"key": "value2"})

        stats = self.manager.get_pool_stats()
        assert stats["total_datasets"] == 2
        assert stats["total_size"] > 0
        assert "json" in stats["format_distribution"]
        assert stats["pool_path"] == os.path.abspath(self.test_dir)

    def test_get_storage_usage(self):
        """测试获取存储使用情况。"""
        self.manager.create_dataset(name="测试", data={"key": "value"})

        usage = self.manager.get_storage_usage()
        assert "pool_used_bytes" in usage
        assert "pool_used_mb" in usage
        assert "disk_total_bytes" in usage
        assert "disk_free_bytes" in usage
        assert usage["pool_used_bytes"] > 0

    def test_persistence(self):
        """测试数据持久化。"""
        dataset = self.manager.create_dataset(name="持久化测试", data={"test": True})
        dataset_id = dataset.dataset_id

        new_manager = DatasetPoolManager(pool_path=self.test_dir)
        retrieved = new_manager.get_dataset(dataset_id)
        assert retrieved is not None
        assert retrieved.name == "持久化测试"
