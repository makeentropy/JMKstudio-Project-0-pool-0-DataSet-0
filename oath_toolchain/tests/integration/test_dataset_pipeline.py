"""数据集管道集成测试。"""
from __future__ import annotations

import json
import os

import pytest

from oath_toolchain.tools.dataset_pool.pool_manager import DatasetPoolManager
from oath_toolchain.tools.dataset_pool.dataset import Dataset


pytestmark = [pytest.mark.integration, pytest.mark.dataset]


class TestDatasetPipeline:
    """数据集创建→更新→保存→加载全流程测试。"""

    def test_full_dataset_lifecycle(self, temp_dir):
        """测试数据集完整生命周期。"""
        pool = DatasetPoolManager(pool_path=temp_dir)
        dataset_name = "test_dataset"

        dataset = pool.create_dataset(
            name=dataset_name,
            description="测试数据集",
            data={"records": [1, 2, 3, 4, 5]},
        )

        assert dataset is not None
        assert dataset.name == dataset_name
        assert dataset.dataset_id is not None
        assert dataset.record_count == 5

        loaded = pool.get_dataset(dataset.dataset_id)
        assert loaded is not None
        assert loaded.name == dataset_name
        assert loaded.record_count == 5
        assert loaded.data == {"records": [1, 2, 3, 4, 5]}

        updated = pool.update_dataset(
            dataset.dataset_id,
            data={"records": [1, 2, 3, 4, 5, 6, 7]},
            metadata={"author": "test"},
        )

        assert updated is not None
        assert updated.record_count == 7
        assert updated.metadata["author"] == "test"

        result = pool.delete_dataset(dataset.dataset_id)
        assert result

        deleted = pool.get_dataset(dataset.dataset_id)
        assert deleted is None

    def test_dataset_multiple_tags(self, temp_dir):
        """测试数据集标签管理。"""
        from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag

        pool = DatasetPoolManager(pool_path=temp_dir)

        dataset = pool.create_dataset(
            name="tagged_dataset",
            data={"key": "value"},
        )

        tag1 = KarmaTag(datafor="test1", tag=["category:test"])
        tag2 = KarmaTag(datafor="test2", tag=["category:production"])
        tag3 = KarmaTag(datafor="test3", tag=["priority:high"])
        dataset.tags = [tag1, tag2, tag3]
        pool.save_dataset(dataset)

        loaded = pool.get_dataset(dataset.dataset_id)
        assert loaded is not None
        assert len(loaded.tags) == 3
        tag_datafors = [t.datafor for t in loaded.tags]
        assert "test1" in tag_datafors
        assert "test2" in tag_datafors
        assert "test3" in tag_datafors

        tag4 = KarmaTag(datafor="test4", tag=["status:active"])
        loaded.tags.append(tag4)
        pool.save_dataset(loaded)

        reloaded = pool.get_dataset(dataset.dataset_id)
        reloaded_datafors = [t.datafor for t in reloaded.tags]
        assert "test4" in reloaded_datafors
        assert len(reloaded.tags) == 4

    def test_dataset_version_tracking(self, temp_dir):
        """测试数据集版本跟踪。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        dataset = pool.create_dataset(
            name="versioned_dataset",
            data={"version": 1},
        )

        assert dataset.version == "1.0.0"

        dataset.version = "1.1.0"
        dataset.data = {"version": 2}
        pool.save_dataset(dataset)

        loaded = pool.get_dataset(dataset.dataset_id)
        assert loaded.version == "1.1.0"
        assert loaded.data["version"] == 2

    def test_dataset_metadata_update(self, temp_dir):
        """测试数据集元数据更新。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        dataset = pool.create_dataset(
            name="metadata_test",
            data={"test": True},
        )

        dataset.metadata = {
            "author": "tester",
            "source": "test_data",
            "license": "MIT",
        }
        dataset.quality_score = 95.5
        pool.save_dataset(dataset)

        loaded = pool.get_dataset(dataset.dataset_id)
        assert loaded.metadata["author"] == "tester"
        assert loaded.metadata["source"] == "test_data"
        assert loaded.quality_score == 95.5


class TestDatasetImportExport:
    """数据集导入导出往返测试。"""

    def test_dataset_save_load_roundtrip(self, temp_dir):
        """测试数据集保存加载往返。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        original_data = {
            "records": [
                {"id": 1, "name": "test1"},
                {"id": 2, "name": "test2"},
                {"id": 3, "name": "test3"},
            ],
            "metadata": {"source": "test"},
        }

        dataset = pool.create_dataset(
            name="roundtrip_test",
            data=original_data,
        )
        dataset_id = dataset.dataset_id

        loaded = pool.get_dataset(dataset_id)
        assert loaded is not None
        assert loaded.data == original_data
        assert loaded.name == "roundtrip_test"

    def test_dataset_export_import_json(self, temp_dir):
        """测试数据集JSON格式的导入导出。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        dataset = pool.create_dataset(
            name="json_test",
            description="JSON测试数据集",
            data={"records": [10, 20, 30]},
        )

        dict_data = dataset.to_dict()
        json_str = json.dumps(dict_data, ensure_ascii=False)

        loaded_dict = json.loads(json_str)
        restored = Dataset.from_dict(loaded_dict)

        assert restored.name == dataset.name
        assert restored.description == dataset.description
        assert restored.data == dataset.data
        assert restored.dataset_id == dataset.dataset_id

    def test_dataset_bytes_data(self, temp_dir):
        """测试bytes类型数据。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        binary_data = b"\x00\x01\x02\x03\x04\x05"
        dataset = pool.create_dataset(
            name="bytes_test",
            data=binary_data,
        )

        loaded = pool.get_dataset(dataset.dataset_id)
        assert loaded is not None
        assert loaded.data == binary_data
        assert loaded.size == len(binary_data)

    def test_multiple_datasets_in_pool(self, temp_dir):
        """测试池中多个数据集。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        for i in range(5):
            pool.create_dataset(
                name=f"dataset_{i}",
                data={"index": i},
            )

        datasets = pool.list_datasets()
        assert len(datasets) == 5

        names = [d.name for d in datasets]
        for i in range(5):
            assert f"dataset_{i}" in names

    def test_dataset_list_filters(self, temp_dir):
        """测试数据集列表过滤。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        pool.create_dataset(name="alpha", data={"type": "a"})
        pool.create_dataset(name="beta", data={"type": "b"})
        pool.create_dataset(name="gamma", data={"type": "a"})

        all_datasets = pool.list_datasets()
        assert len(all_datasets) == 3


class TestDatasetMetadata:
    """数据集元数据测试。"""

    def test_metadata_update(self, temp_dir):
        """测试元数据更新。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        dataset = pool.create_dataset(name="meta_test", data={})
        dataset.metadata = {"key1": "value1"}
        pool.save_dataset(dataset)

        loaded = pool.get_dataset(dataset.dataset_id)
        assert loaded.metadata["key1"] == "value1"

        loaded.metadata["key2"] = "value2"
        pool.save_dataset(loaded)

        reloaded = pool.get_dataset(dataset.dataset_id)
        assert reloaded.metadata["key1"] == "value1"
        assert reloaded.metadata["key2"] == "value2"

    def test_quality_score_tracking(self, temp_dir):
        """测试质量分数跟踪。"""
        pool = DatasetPoolManager(pool_path=temp_dir)

        dataset = pool.create_dataset(name="quality_test", data={})
        assert dataset.quality_score == 0.0

        dataset.quality_score = 87.5
        pool.save_dataset(dataset)

        loaded = pool.get_dataset(dataset.dataset_id)
        assert loaded.quality_score == 87.5
