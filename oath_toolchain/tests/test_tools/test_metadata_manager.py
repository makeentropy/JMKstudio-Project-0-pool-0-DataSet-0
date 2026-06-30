"""MetadataManager元数据管理单元测试。"""
import pytest
import os
import tempfile
import shutil

from oath_toolchain.tools.dataset_pool.pool_manager import DatasetPoolManager
from oath_toolchain.tools.dataset_pool.metadata_manager import MetadataManager


class TestMetadataManager:
    """测试MetadataManager类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.test_dir = tempfile.mkdtemp()
        self.pool_manager = DatasetPoolManager(pool_path=self.test_dir)
        self.metadata_manager = MetadataManager(self.pool_manager)

    def teardown_method(self):
        """每个测试后的清理。"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """测试初始化。"""
        assert self.metadata_manager.pool_manager == self.pool_manager

    def test_set_metadata(self):
        """测试设置元数据。"""
        dataset = self.pool_manager.create_dataset(name="测试")

        result = self.metadata_manager.set_metadata(
            dataset.dataset_id,
            "author",
            "test_author",
        )

        assert result is True
        meta = self.metadata_manager.get_metadata(dataset.dataset_id, "author")
        assert meta == "test_author"

    def test_set_metadata_not_found(self):
        """测试设置不存在数据集的元数据。"""
        result = self.metadata_manager.set_metadata("nonexistent", "key", "value")
        assert result is False

    def test_get_metadata_all(self):
        """测试获取所有元数据。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        self.metadata_manager.set_metadata(dataset.dataset_id, "key1", "value1")
        self.metadata_manager.set_metadata(dataset.dataset_id, "key2", "value2")

        all_meta = self.metadata_manager.get_metadata(dataset.dataset_id)
        assert all_meta["key1"] == "value1"
        assert all_meta["key2"] == "value2"

    def test_get_metadata_by_key(self):
        """测试按key获取元数据。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        self.metadata_manager.set_metadata(dataset.dataset_id, "author", "test")

        value = self.metadata_manager.get_metadata(dataset.dataset_id, "author")
        assert value == "test"

    def test_get_metadata_key_not_found(self):
        """测试获取不存在的key。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        value = self.metadata_manager.get_metadata(dataset.dataset_id, "nonexistent")
        assert value is None

    def test_get_metadata_dataset_not_found(self):
        """测试获取不存在数据集的元数据。"""
        result = self.metadata_manager.get_metadata("nonexistent")
        assert result is None

    def test_update_metadata(self):
        """测试批量更新元数据。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        self.metadata_manager.set_metadata(dataset.dataset_id, "existing", "old_value")

        result = self.metadata_manager.update_metadata(
            dataset.dataset_id,
            {
                "new_key": "new_value",
                "existing": "updated_value",
                "another": "another_value",
            },
        )

        assert result is True
        all_meta = self.metadata_manager.get_metadata(dataset.dataset_id)
        assert all_meta["existing"] == "updated_value"
        assert all_meta["new_key"] == "new_value"
        assert all_meta["another"] == "another_value"

    def test_update_metadata_not_found(self):
        """测试更新不存在数据集的元数据。"""
        result = self.metadata_manager.update_metadata("nonexistent", {"key": "value"})
        assert result is False

    def test_remove_metadata(self):
        """测试删除元数据。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        self.metadata_manager.set_metadata(dataset.dataset_id, "to_remove", "value")
        self.metadata_manager.set_metadata(dataset.dataset_id, "to_keep", "value")

        result = self.metadata_manager.remove_metadata(dataset.dataset_id, "to_remove")
        assert result is True

        all_meta = self.metadata_manager.get_metadata(dataset.dataset_id)
        assert "to_remove" not in all_meta
        assert "to_keep" in all_meta

    def test_remove_metadata_not_found_key(self):
        """测试删除不存在的key。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        result = self.metadata_manager.remove_metadata(dataset.dataset_id, "nonexistent")
        assert result is False

    def test_remove_metadata_not_found_dataset(self):
        """测试删除不存在数据集的元数据。"""
        result = self.metadata_manager.remove_metadata("nonexistent", "key")
        assert result is False

    def test_search_by_metadata_single(self):
        """测试按单个元数据搜索。"""
        ds1 = self.pool_manager.create_dataset(name="数据集1")
        self.metadata_manager.set_metadata(ds1.dataset_id, "category", "image")
        self.metadata_manager.set_metadata(ds1.dataset_id, "source", "web")

        ds2 = self.pool_manager.create_dataset(name="数据集2")
        self.metadata_manager.set_metadata(ds2.dataset_id, "category", "text")
        self.metadata_manager.set_metadata(ds2.dataset_id, "source", "web")

        ds3 = self.pool_manager.create_dataset(name="数据集3")
        self.metadata_manager.set_metadata(ds3.dataset_id, "category", "image")
        self.metadata_manager.set_metadata(ds3.dataset_id, "source", "local")

        results = self.metadata_manager.search_by_metadata({"category": "image"})
        assert len(results) == 2
        assert ds1.dataset_id in results
        assert ds3.dataset_id in results

    def test_search_by_metadata_multiple(self):
        """测试按多个元数据搜索。"""
        ds1 = self.pool_manager.create_dataset(name="数据集1")
        self.metadata_manager.set_metadata(ds1.dataset_id, "category", "image")
        self.metadata_manager.set_metadata(ds1.dataset_id, "source", "web")

        ds2 = self.pool_manager.create_dataset(name="数据集2")
        self.metadata_manager.set_metadata(ds2.dataset_id, "category", "text")
        self.metadata_manager.set_metadata(ds2.dataset_id, "source", "web")

        results = self.metadata_manager.search_by_metadata({
            "category": "image",
            "source": "web",
        })
        assert len(results) == 1
        assert ds1.dataset_id in results

    def test_search_by_metadata_no_match(self):
        """测试无匹配的元数据搜索。"""
        ds1 = self.pool_manager.create_dataset(name="数据集1")
        self.metadata_manager.set_metadata(ds1.dataset_id, "category", "image")

        results = self.metadata_manager.search_by_metadata({"category": "audio"})
        assert len(results) == 0

    def test_search_by_metadata_list_value(self):
        """测试列表值的元数据搜索。"""
        ds1 = self.pool_manager.create_dataset(name="数据集1")
        self.metadata_manager.set_metadata(ds1.dataset_id, "category", "image")

        ds2 = self.pool_manager.create_dataset(name="数据集2")
        self.metadata_manager.set_metadata(ds2.dataset_id, "category", "text")

        ds3 = self.pool_manager.create_dataset(name="数据集3")
        self.metadata_manager.set_metadata(ds3.dataset_id, "category", "audio")

        results = self.metadata_manager.search_by_metadata({
            "category": ["image", "text"],
        })
        assert len(results) == 2
        assert ds1.dataset_id in results
        assert ds2.dataset_id in results

    def test_get_metadata_schema(self):
        """测试获取元数据schema。"""
        schema = self.metadata_manager.get_metadata_schema()
        assert schema["title"] == "Dataset Metadata Schema"
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "source" in schema["properties"]
        assert "author" in schema["properties"]
        assert "license" in schema["properties"]
        assert "category" in schema["properties"]

    def test_set_metadata_updates_timestamp(self):
        """测试设置元数据更新时间戳。"""
        import time
        dataset = self.pool_manager.create_dataset(name="测试")
        old_updated = dataset.updated_at
        time.sleep(0.01)
        self.metadata_manager.set_metadata(dataset.dataset_id, "key", "value")
        updated = self.pool_manager.get_dataset(dataset.dataset_id)
        assert updated.updated_at > old_updated

    def test_metadata_persistence(self):
        """测试元数据持久化。"""
        dataset = self.pool_manager.create_dataset(name="持久化测试")
        self.metadata_manager.set_metadata(dataset.dataset_id, "author", "test_author")
        self.metadata_manager.set_metadata(dataset.dataset_id, "source", "test_source")

        new_pool = DatasetPoolManager(pool_path=self.test_dir)
        new_mm = MetadataManager(new_pool)

        meta = new_mm.get_metadata(dataset.dataset_id)
        assert meta["author"] == "test_author"
        assert meta["source"] == "test_source"
