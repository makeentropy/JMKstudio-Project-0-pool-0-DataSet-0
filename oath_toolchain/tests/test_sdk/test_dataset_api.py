"""数据集API单元测试。"""
import pytest
import os
import tempfile

from oath_toolchain.sdk import OathSDK
from oath_toolchain.core.registry import ToolRegistry


class TestDatasetAPI:
    """测试DatasetAPI类。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.sdk = OathSDK()

    def test_create_dataset(self):
        """测试创建数据集。"""
        result = self.sdk.datasets.create("test_dataset", {"key": "value"})
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert "dataset_id" in result
        assert "dataset" in result

    def test_create_dataset_without_data(self):
        """测试创建空数据集。"""
        result = self.sdk.datasets.create("empty_dataset")
        assert result.get("success") is True
        assert "dataset_id" in result

    def test_get_dataset(self):
        """测试获取数据集。"""
        create_result = self.sdk.datasets.create("get_test", {"a": 1})
        dataset_id = create_result["dataset_id"]

        result = self.sdk.datasets.get(dataset_id)
        assert result.get("success") is True
        assert result["dataset_id"] == dataset_id

    def test_get_nonexistent_dataset(self):
        """测试获取不存在的数据集。"""
        with pytest.raises(Exception):
            self.sdk.datasets.get("nonexistent_id")

    def test_update_dataset(self):
        """测试更新数据集。"""
        create_result = self.sdk.datasets.create("update_test", {"old": "data"})
        dataset_id = create_result["dataset_id"]

        update_result = self.sdk.datasets.update(
            dataset_id,
            data={"new": "data", "updated": True},
        )
        assert update_result.get("success") is True

    def test_delete_dataset(self):
        """测试删除数据集。"""
        create_result = self.sdk.datasets.create("delete_test", {"to": "delete"})
        dataset_id = create_result["dataset_id"]

        result = self.sdk.datasets.delete(dataset_id)
        assert result is True

    def test_list_datasets(self):
        """测试列出数据集。"""
        self.sdk.datasets.create("list_test_1", {"n": 1})
        self.sdk.datasets.create("list_test_2", {"n": 2})

        datasets = self.sdk.datasets.list_datasets()
        assert isinstance(datasets, list)
        assert len(datasets) >= 2

    def test_commit_version(self):
        """测试提交版本。"""
        create_result = self.sdk.datasets.create("version_test", {"v": 1})
        dataset_id = create_result["dataset_id"]

        version = self.sdk.datasets.commit_version(dataset_id, "initial version")
        assert isinstance(version, str)
        assert len(version) > 0

    def test_list_versions(self):
        """测试列出版本。"""
        create_result = self.sdk.datasets.create("versions_test", {"v": 0})
        dataset_id = create_result["dataset_id"]

        self.sdk.datasets.commit_version(dataset_id, "v1")
        self.sdk.datasets.update(dataset_id, data={"v": 1})
        self.sdk.datasets.commit_version(dataset_id, "v2")

        versions = self.sdk.datasets.list_versions(dataset_id)
        assert isinstance(versions, list)
        assert len(versions) >= 2

    def test_revert_version(self):
        """测试版本回滚。"""
        create_result = self.sdk.datasets.create("revert_test", {"v": "original"})
        dataset_id = create_result["dataset_id"]

        self.sdk.datasets.commit_version(dataset_id, "original_version")

        self.sdk.datasets.update(dataset_id, data={"v": "modified"})

        versions = self.sdk.datasets.list_versions(dataset_id)
        if len(versions) > 0:
            first_version = versions[0].get("version", "")
            if first_version:
                result = self.sdk.datasets.revert_version(dataset_id, first_version)
                assert isinstance(result, dict)
                assert result.get("success") is True

    def test_search_by_tags(self):
        """测试按标签搜索。"""
        create_result = self.sdk.datasets.create("tag_test", {"data": "tagged"})
        dataset_id = create_result["dataset_id"]

        self.sdk.datasets.add_tag(dataset_id, {"name": "test", "value": "true"})

        results = self.sdk.datasets.search_by_tags({"test": "true"})
        assert isinstance(results, list)

    def test_add_tag(self):
        """测试添加标签。"""
        create_result = self.sdk.datasets.create("add_tag_test", {"data": "x"})
        dataset_id = create_result["dataset_id"]

        result = self.sdk.datasets.add_tag(dataset_id, {"key": "type", "value": "test"})
        assert result is True

    def test_remove_tag(self):
        """测试移除标签。"""
        create_result = self.sdk.datasets.create("remove_tag_test", {"data": "y"})
        dataset_id = create_result["dataset_id"]

        self.sdk.datasets.add_tag(dataset_id, {"tag_id": "tag1", "name": "temp"})
        result = self.sdk.datasets.remove_tag(dataset_id, "tag1")
        assert result is True

    def test_export_dataset(self):
        """测试导出数据集。"""
        create_result = self.sdk.datasets.create("export_test", {"export": "me"})
        dataset_id = create_result["dataset_id"]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            export_path = self.sdk.datasets.export_dataset(dataset_id, filepath)
            assert isinstance(export_path, str)
            assert os.path.exists(export_path)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
