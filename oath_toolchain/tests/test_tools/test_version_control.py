"""DatasetVersionControl版本控制单元测试。"""
import pytest
import os
import tempfile
import shutil

from oath_toolchain.tools.dataset_pool.pool_manager import DatasetPoolManager
from oath_toolchain.tools.dataset_pool.version_control import DatasetVersionControl
from oath_toolchain.tools.dataset_pool.dataset import Dataset


class TestDatasetVersionControl:
    """测试DatasetVersionControl类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.test_dir = tempfile.mkdtemp()
        self.pool_manager = DatasetPoolManager(pool_path=self.test_dir)
        self.version_control = DatasetVersionControl(self.pool_manager)

    def teardown_method(self):
        """每个测试后的清理。"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """测试初始化。"""
        assert self.version_control.pool_manager == self.pool_manager
        assert os.path.exists(self.version_control.versions_dir)

    def test_commit_version(self):
        """测试提交版本。"""
        dataset = self.pool_manager.create_dataset(
            name="测试数据集",
            data={"version": 1, "records": [1, 2, 3]},
        )

        version = self.version_control.commit_version(
            dataset.dataset_id,
            message="初始版本",
        )

        assert version == "v1.0.0"
        versions = self.version_control.list_versions(dataset.dataset_id)
        assert len(versions) == 1
        assert versions[0]["version"] == "v1.0.0"
        assert versions[0]["message"] == "初始版本"

    def test_commit_multiple_versions(self):
        """测试提交多个版本。"""
        dataset = self.pool_manager.create_dataset(
            name="测试数据集",
            data={"version": 1},
        )

        v1 = self.version_control.commit_version(dataset.dataset_id, "版本1")
        assert v1 == "v1.0.0"

        self.pool_manager.update_dataset(dataset.dataset_id, data={"version": 2})
        v2 = self.version_control.commit_version(dataset.dataset_id, "版本2")
        assert v2 == "v2.0.0"

        self.pool_manager.update_dataset(dataset.dataset_id, data={"version": 3})
        v3 = self.version_control.commit_version(dataset.dataset_id, "版本3")
        assert v3 == "v3.0.0"

        versions = self.version_control.list_versions(dataset.dataset_id)
        assert len(versions) == 3
        assert versions[0]["version"] == "v3.0.0"
        assert versions[2]["version"] == "v1.0.0"

    def test_commit_version_dataset_not_found(self):
        """测试提交不存在的数据集版本。"""
        with pytest.raises(ValueError, match="数据集不存在"):
            self.version_control.commit_version("nonexistent")

    def test_list_versions_empty(self):
        """测试空版本列表。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        versions = self.version_control.list_versions(dataset.dataset_id)
        assert versions == []

    def test_get_version(self):
        """测试获取指定版本。"""
        dataset = self.pool_manager.create_dataset(
            name="测试",
            data={"version": 1, "data": "original"},
        )

        self.version_control.commit_version(dataset.dataset_id, "v1")
        self.pool_manager.update_dataset(dataset.dataset_id, data={"version": 2, "data": "updated"})
        self.version_control.commit_version(dataset.dataset_id, "v2")

        v1 = self.version_control.get_version(dataset.dataset_id, "v1.0.0")
        assert v1 is not None
        assert v1.data == {"version": 1, "data": "original"}

        v2 = self.version_control.get_version(dataset.dataset_id, "v2.0.0")
        assert v2 is not None
        assert v2.data == {"version": 2, "data": "updated"}

    def test_get_version_not_found(self):
        """测试获取不存在的版本。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        result = self.version_control.get_version(dataset.dataset_id, "v999.0.0")
        assert result is None

    def test_revert_to_version(self):
        """测试回滚到指定版本。"""
        dataset = self.pool_manager.create_dataset(
            name="测试",
            data={"version": 1, "data": "original"},
        )

        self.version_control.commit_version(dataset.dataset_id, "初始版本")
        self.pool_manager.update_dataset(dataset.dataset_id, data={"version": 2, "data": "modified"})

        reverted = self.version_control.revert_to_version(dataset.dataset_id, "v1.0.0")
        assert reverted is not None
        assert reverted.data == {"version": 1, "data": "original"}

        current = self.pool_manager.get_dataset(dataset.dataset_id)
        assert current.data == {"version": 1, "data": "original"}

    def test_revert_to_version_not_found(self):
        """测试回滚到不存在的版本。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        result = self.version_control.revert_to_version(dataset.dataset_id, "v999.0.0")
        assert result is None

    def test_diff_versions(self):
        """测试版本差异比较。"""
        dataset = self.pool_manager.create_dataset(
            name="测试",
            data={"key1": "value1", "key2": "old"},
        )
        dataset.description = "旧描述"
        self.pool_manager.update_dataset(dataset.dataset_id, data=dataset.data)
        self.version_control.commit_version(dataset.dataset_id, "版本1")

        self.pool_manager.update_dataset(
            dataset.dataset_id,
            data={"key1": "value1", "key2": "new", "key3": "added"},
            metadata={"author": "test"},
        )
        self.version_control.commit_version(dataset.dataset_id, "版本2")

        diff = self.version_control.diff_versions(
            dataset.dataset_id,
            "v1.0.0",
            "v2.0.0",
        )

        assert diff["version1"] == "v1.0.0"
        assert diff["version2"] == "v2.0.0"
        assert "key2" in diff["data_changes"]
        assert "key3" in diff["data_changes"]

    def test_diff_versions_with_tags(self):
        """测试带标签的版本差异比较。"""
        from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag

        dataset = self.pool_manager.create_dataset(name="测试", data={"v": 1})
        tag1 = KarmaTag(datafor="测试1", datefor="20240101", tag_id="tag-1")
        dataset.add_tag(tag1)
        self.pool_manager.save_dataset(dataset)
        self.version_control.commit_version(dataset.dataset_id, "版本1")

        dataset = self.pool_manager.get_dataset(dataset.dataset_id)
        tag2 = KarmaTag(datafor="测试2", datefor="20240102", tag_id="tag-2")
        dataset.add_tag(tag2)
        dataset.remove_tag("tag-1")
        self.pool_manager.save_dataset(dataset)
        self.version_control.commit_version(dataset.dataset_id, "版本2")

        diff = self.version_control.diff_versions(
            dataset.dataset_id,
            "v1.0.0",
            "v2.0.0",
        )

        assert len(diff["tag_changes"]["added"]) == 1
        assert len(diff["tag_changes"]["removed"]) == 1

    def test_diff_versions_v1_not_found(self):
        """测试版本1不存在时的差异比较。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        self.version_control.commit_version(dataset.dataset_id)

        with pytest.raises(ValueError, match="版本不存在"):
            self.version_control.diff_versions(dataset.dataset_id, "v999.0.0", "v1.0.0")

    def test_diff_versions_v2_not_found(self):
        """测试版本2不存在时的差异比较。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        self.version_control.commit_version(dataset.dataset_id)

        with pytest.raises(ValueError, match="版本不存在"):
            self.version_control.diff_versions(dataset.dataset_id, "v1.0.0", "v999.0.0")

    def test_tag_version(self):
        """测试为版本打标签。"""
        dataset = self.pool_manager.create_dataset(name="测试", data={"v": 1})
        self.version_control.commit_version(dataset.dataset_id, "初始版本")

        result = self.version_control.tag_version(dataset.dataset_id, "v1.0.0", "release")
        assert result is True

        versions = self.version_control.list_versions(dataset.dataset_id)
        assert "release" in versions[0]["tags"]

    def test_tag_version_not_found(self):
        """测试为不存在的版本打标签。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        result = self.version_control.tag_version(dataset.dataset_id, "v999.0.0", "release")
        assert result is False

    def test_get_version_by_tag(self):
        """测试按标签获取版本。"""
        dataset = self.pool_manager.create_dataset(name="测试", data={"v": 1})
        self.version_control.commit_version(dataset.dataset_id, "v1")
        self.version_control.tag_version(dataset.dataset_id, "v1.0.0", "release")

        self.pool_manager.update_dataset(dataset.dataset_id, data={"v": 2})
        self.version_control.commit_version(dataset.dataset_id, "v2")

        result = self.version_control.get_version_by_tag(dataset.dataset_id, "release")
        assert result is not None
        assert result.version == "v1.0.0"
        assert result.data == {"v": 1}

    def test_get_version_by_tag_not_found(self):
        """测试按不存在的标签获取版本。"""
        dataset = self.pool_manager.create_dataset(name="测试")
        self.version_control.commit_version(dataset.dataset_id)

        result = self.version_control.get_version_by_tag(dataset.dataset_id, "nonexistent")
        assert result is None

    def test_version_persistence(self):
        """测试版本持久化。"""
        dataset = self.pool_manager.create_dataset(name="持久化测试", data={"v": 1})
        self.version_control.commit_version(dataset.dataset_id, "测试版本")

        new_pool = DatasetPoolManager(pool_path=self.test_dir)
        new_vc = DatasetVersionControl(new_pool)

        versions = new_vc.list_versions(dataset.dataset_id)
        assert len(versions) == 1
        assert versions[0]["message"] == "测试版本"
