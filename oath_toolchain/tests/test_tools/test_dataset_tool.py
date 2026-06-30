"""DatasetPoolTool数据集池主工具单元测试。"""
import pytest
import os
import tempfile
import shutil
import json

from oath_toolchain.tools.dataset_pool.tool import DatasetPoolTool
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.core.exceptions import ValidationError


class TestDatasetPoolTool:
    """测试DatasetPoolTool类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.test_dir = tempfile.mkdtemp()
        self.tool = DatasetPoolTool(pool_path=self.test_dir)

    def teardown_method(self):
        """每个测试后的清理。"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """测试初始化。"""
        assert self.tool.name == "dataset_pool"
        assert self.tool.description == "Dataset Pool数据集池管理工具"
        assert self.tool.version == "0.1.0"
        assert self.tool.category == "data"
        assert "data" in self.tool.tags
        assert "dataset" in self.tool.tags

    def test_pool_manager_property(self):
        """测试pool_manager属性。"""
        assert self.tool.pool_manager is not None

    def test_version_control_property(self):
        """测试version_control属性。"""
        assert self.tool.version_control is not None

    def test_metadata_manager_property(self):
        """测试metadata_manager属性。"""
        assert self.tool.metadata_manager is not None

    def test_registry_integration(self):
        """测试工具注册集成。"""
        ToolRegistry.reset_instance()
        import importlib
        import oath_toolchain.tools.dataset_pool.tool as tool_module
        importlib.reload(tool_module)

        registry = ToolRegistry()
        assert "dataset_pool" in registry
        tool_class = registry.get_tool("dataset_pool")
        assert tool_class.__name__ == "DatasetPoolTool"

    def test_create_tool_from_registry(self):
        """测试从注册表创建工具。"""
        ToolRegistry.reset_instance()
        import importlib
        import oath_toolchain.tools.dataset_pool.tool as tool_module
        importlib.reload(tool_module)

        registry = ToolRegistry()
        tool = registry.create_tool("dataset_pool")
        assert tool.name == "dataset_pool"
        assert tool.description == "Dataset Pool数据集池管理工具"

    def test_execute_missing_action(self):
        """测试缺少action参数。"""
        with pytest.raises(ValidationError):
            self.tool.execute({})

    def test_execute_invalid_action(self):
        """测试无效的action参数。"""
        with pytest.raises(ValidationError):
            self.tool.execute({"action": "invalid_action"})

    def test_action_create(self):
        """测试create操作。"""
        result = self.tool.execute({
            "action": "create",
            "name": "测试数据集",
            "data": {"records": [1, 2, 3]},
            "format": "json",
            "description": "测试描述",
        })
        assert result["success"] is True
        assert result["action"] == "create"
        assert "dataset_id" in result
        assert result["dataset"]["name"] == "测试数据集"
        assert result["dataset"]["description"] == "测试描述"

    def test_action_delete(self):
        """测试delete操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "待删除",
        })
        dataset_id = create_result["dataset_id"]

        result = self.tool.execute({
            "action": "delete",
            "dataset_id": dataset_id,
        })
        assert result["success"] is True
        assert result["action"] == "delete"
        assert result["dataset_id"] == dataset_id

    def test_action_delete_missing_id(self):
        """测试delete缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "delete"})

    def test_action_get(self):
        """测试get操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "测试数据集",
            "data": {"key": "value"},
        })
        dataset_id = create_result["dataset_id"]

        result = self.tool.execute({
            "action": "get",
            "dataset_id": dataset_id,
        })
        assert result["success"] is True
        assert result["action"] == "get"
        assert result["dataset"]["name"] == "测试数据集"

    def test_action_get_missing_id(self):
        """测试get缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "get"})

    def test_action_get_not_found(self):
        """测试get不存在的数据集。"""
        with pytest.raises(ValidationError, match="数据集不存在"):
            self.tool.execute({"action": "get", "dataset_id": "nonexistent"})

    def test_action_update(self):
        """测试update操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "测试数据集",
            "data": {"old": "data"},
        })
        dataset_id = create_result["dataset_id"]

        result = self.tool.execute({
            "action": "update",
            "dataset_id": dataset_id,
            "data": {"new": "data"},
            "metadata": {"author": "test"},
        })
        assert result["success"] is True
        assert result["action"] == "update"

    def test_action_update_missing_id(self):
        """测试update缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "update"})

    def test_action_list(self):
        """测试list操作。"""
        self.tool.execute({"action": "create", "name": "数据集1"})
        self.tool.execute({"action": "create", "name": "数据集2"})

        result = self.tool.execute({"action": "list"})
        assert result["success"] is True
        assert result["action"] == "list"
        assert result["count"] == 2
        assert len(result["datasets"]) == 2

    def test_action_list_with_limit(self):
        """测试带limit的list操作。"""
        for i in range(10):
            self.tool.execute({"action": "create", "name": f"数据集{i}"})

        result = self.tool.execute({"action": "list", "limit": 5})
        assert result["count"] == 5

    def test_action_search_tags(self):
        """测试search_tags操作。"""
        from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag

        create_result = self.tool.execute({
            "action": "create",
            "name": "测试数据集",
        })
        dataset_id = create_result["dataset_id"]

        dataset = self.tool.pool_manager.get_dataset(dataset_id)
        tag = KarmaTag(datafor="训练数据", datefor="20240101")
        dataset.add_tag(tag)
        self.tool.pool_manager.save_dataset(dataset)

        result = self.tool.execute({
            "action": "search_tags",
            "tag_filters": {"datafor": "训练数据"},
        })
        assert result["success"] is True
        assert result["action"] == "search_tags"
        assert result["count"] >= 1

    def test_action_import(self):
        """测试import操作。"""
        import_file = os.path.join(self.test_dir, "import.json")
        with open(import_file, "w", encoding="utf-8") as f:
            json.dump({"key": "value"}, f)

        result = self.tool.execute({
            "action": "import",
            "filepath": import_file,
        })
        assert result["success"] is True
        assert result["action"] == "import"
        assert "dataset_id" in result

    def test_action_import_missing_filepath(self):
        """测试import缺少filepath参数。"""
        with pytest.raises(ValidationError, match="缺少必需的filepath参数"):
            self.tool.execute({"action": "import"})

    def test_action_export(self):
        """测试export操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "导出测试",
            "data": {"key": "value"},
        })
        dataset_id = create_result["dataset_id"]

        export_path = os.path.join(self.test_dir, "export.json")
        result = self.tool.execute({
            "action": "export",
            "dataset_id": dataset_id,
            "filepath": export_path,
        })
        assert result["success"] is True
        assert result["action"] == "export"
        assert os.path.exists(result["export_path"])

    def test_action_export_missing_dataset_id(self):
        """测试export缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "export", "filepath": "/tmp/out.json"})

    def test_action_export_missing_filepath(self):
        """测试export缺少filepath参数。"""
        with pytest.raises(ValidationError, match="缺少必需的filepath参数"):
            self.tool.execute({"action": "export", "dataset_id": "test"})

    def test_action_stats(self):
        """测试stats操作。"""
        self.tool.execute({"action": "create", "name": "测试1", "data": {"k": "v"}})
        self.tool.execute({"action": "create", "name": "测试2", "data": {"k": "v"}})

        result = self.tool.execute({"action": "stats"})
        assert result["success"] is True
        assert result["action"] == "stats"
        assert "pool_stats" in result
        assert "storage_usage" in result
        assert result["pool_stats"]["total_datasets"] == 2

    def test_action_commit(self):
        """测试commit操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "测试",
            "data": {"v": 1},
        })
        dataset_id = create_result["dataset_id"]

        result = self.tool.execute({
            "action": "commit",
            "dataset_id": dataset_id,
            "message": "初始版本",
        })
        assert result["success"] is True
        assert result["action"] == "commit"
        assert result["version"] == "v1.0.0"

    def test_action_commit_missing_id(self):
        """测试commit缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "commit"})

    def test_action_versions(self):
        """测试versions操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "测试",
            "data": {"v": 1},
        })
        dataset_id = create_result["dataset_id"]
        self.tool.execute({"action": "commit", "dataset_id": dataset_id})

        result = self.tool.execute({
            "action": "versions",
            "dataset_id": dataset_id,
        })
        assert result["success"] is True
        assert result["action"] == "versions"
        assert result["count"] == 1
        assert len(result["versions"]) == 1

    def test_action_versions_missing_id(self):
        """测试versions缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "versions"})

    def test_action_revert(self):
        """测试revert操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "测试",
            "data": {"v": 1},
        })
        dataset_id = create_result["dataset_id"]
        self.tool.execute({"action": "commit", "dataset_id": dataset_id})

        self.tool.execute({
            "action": "update",
            "dataset_id": dataset_id,
            "data": {"v": 2},
        })

        result = self.tool.execute({
            "action": "revert",
            "dataset_id": dataset_id,
            "version": "v1.0.0",
        })
        assert result["success"] is True
        assert result["action"] == "revert"

    def test_action_revert_missing_dataset_id(self):
        """测试revert缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "revert", "version": "v1.0.0"})

    def test_action_revert_missing_version(self):
        """测试revert缺少version参数。"""
        with pytest.raises(ValidationError, match="缺少必需的version参数"):
            self.tool.execute({"action": "revert", "dataset_id": "test"})

    def test_action_set_meta(self):
        """测试set_meta操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "测试",
        })
        dataset_id = create_result["dataset_id"]

        result = self.tool.execute({
            "action": "set_meta",
            "dataset_id": dataset_id,
            "key": "author",
            "value": "test_author",
        })
        assert result["success"] is True
        assert result["action"] == "set_meta"
        assert result["key"] == "author"
        assert result["value"] == "test_author"

    def test_action_set_meta_missing_dataset_id(self):
        """测试set_meta缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "set_meta", "key": "k", "value": "v"})

    def test_action_set_meta_missing_key(self):
        """测试set_meta缺少key参数。"""
        with pytest.raises(ValidationError, match="缺少必需的key参数"):
            self.tool.execute({"action": "set_meta", "dataset_id": "test"})

    def test_action_get_meta(self):
        """测试get_meta操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "测试",
        })
        dataset_id = create_result["dataset_id"]
        self.tool.execute({
            "action": "set_meta",
            "dataset_id": dataset_id,
            "key": "author",
            "value": "test_author",
        })

        result = self.tool.execute({
            "action": "get_meta",
            "dataset_id": dataset_id,
        })
        assert result["success"] is True
        assert result["action"] == "get_meta"
        assert result["metadata"]["author"] == "test_author"

    def test_action_get_meta_with_key(self):
        """测试带key的get_meta操作。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "测试",
        })
        dataset_id = create_result["dataset_id"]
        self.tool.execute({
            "action": "set_meta",
            "dataset_id": dataset_id,
            "key": "author",
            "value": "test_author",
        })

        result = self.tool.execute({
            "action": "get_meta",
            "dataset_id": dataset_id,
            "key": "author",
        })
        assert result["success"] is True
        assert result["metadata"] == "test_author"

    def test_action_get_meta_missing_dataset_id(self):
        """测试get_meta缺少dataset_id参数。"""
        with pytest.raises(ValidationError, match="缺少必需的dataset_id参数"):
            self.tool.execute({"action": "get_meta"})

    def test_validate_params_missing_action(self):
        """测试参数验证：缺少action。"""
        with pytest.raises(ValidationError):
            self.tool.validate_params({})

    def test_validate_params_invalid_action(self):
        """测试参数验证：无效action。"""
        with pytest.raises(ValidationError):
            self.tool.validate_params({"action": "invalid"})

    def test_validate_params_valid_action(self):
        """测试参数验证：有效action。"""
        assert self.tool.validate_params({"action": "create"}) is True

    def test_metadata(self):
        """测试工具元数据。"""
        metadata = self.tool.metadata
        assert metadata["name"] == "dataset_pool"
        assert metadata["description"] == "Dataset Pool数据集池管理工具"
        assert metadata["version"] == "0.1.0"
        assert metadata["category"] == "data"
        assert isinstance(metadata["tags"], list)

    def test_tool_repr(self):
        """测试工具的字符串表示。"""
        repr_str = repr(self.tool)
        assert "DatasetPoolTool" in repr_str
        assert "dataset_pool" in repr_str

    def test_tool_str(self):
        """测试工具的可读字符串。"""
        str_repr = str(self.tool)
        assert "dataset_pool" in str_repr
        assert "Dataset Pool数据集池管理工具" in str_repr

    def test_full_workflow(self):
        """测试完整工作流程。"""
        create_result = self.tool.execute({
            "action": "create",
            "name": "完整流程测试",
            "data": {"records": [{"id": 1}, {"id": 2}]},
            "description": "用于测试完整流程",
        })
        assert create_result["success"] is True
        dataset_id = create_result["dataset_id"]

        commit_result = self.tool.execute({
            "action": "commit",
            "dataset_id": dataset_id,
            "message": "初始版本",
        })
        assert commit_result["success"] is True

        self.tool.execute({
            "action": "update",
            "dataset_id": dataset_id,
            "data": {"records": [{"id": 1}, {"id": 2}, {"id": 3}]},
            "metadata": {"author": "tester"},
        })

        set_meta_result = self.tool.execute({
            "action": "set_meta",
            "dataset_id": dataset_id,
            "key": "category",
            "value": "test",
        })
        assert set_meta_result["success"] is True

        get_meta_result = self.tool.execute({
            "action": "get_meta",
            "dataset_id": dataset_id,
        })
        assert get_meta_result["success"] is True
        assert get_meta_result["metadata"]["author"] == "tester"

        versions_result = self.tool.execute({
            "action": "versions",
            "dataset_id": dataset_id,
        })
        assert versions_result["success"] is True
        assert versions_result["count"] == 1

        export_path = os.path.join(self.test_dir, "workflow_export.json")
        export_result = self.tool.execute({
            "action": "export",
            "dataset_id": dataset_id,
            "filepath": export_path,
        })
        assert export_result["success"] is True
        assert os.path.exists(export_path)

        list_result = self.tool.execute({"action": "list"})
        assert list_result["success"] is True
        assert list_result["count"] >= 1

        stats_result = self.tool.execute({"action": "stats"})
        assert stats_result["success"] is True
        assert stats_result["pool_stats"]["total_datasets"] >= 1

        delete_result = self.tool.execute({
            "action": "delete",
            "dataset_id": dataset_id,
        })
        assert delete_result["success"] is True
