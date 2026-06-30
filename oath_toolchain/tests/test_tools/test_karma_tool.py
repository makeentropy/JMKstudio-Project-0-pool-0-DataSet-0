"""Karma标签系统主工具单元测试。"""
import pytest

from oath_toolchain.tools.karma_tags.tool import KarmaTagTool
from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.core.exceptions import ValidationError
from oath_toolchain.core.crypto.primitives import RSACipher


class TestKarmaTagTool:
    """测试KarmaTagTool类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.tool = KarmaTagTool()
        self.private_key, self.public_key = RSACipher.generate_keypair(key_size=2048)
        self.private_key_pem = RSACipher.serialize_private_key(self.private_key)
        self.public_key_pem = RSACipher.serialize_public_key(self.public_key)

    def test_initialization(self):
        """测试初始化。"""
        assert self.tool.name == "karma_tags"
        assert self.tool.description == "Karma数据标签系统"
        assert self.tool.version == "0.1.0"
        assert self.tool.category == "data"
        assert "data" in self.tool.tags
        assert "tags" in self.tool.tags
        assert "karma" in self.tool.tags

    def test_registry_integration(self):
        """测试工具注册集成。"""
        ToolRegistry.reset_instance()
        import importlib
        import oath_toolchain.tools.karma_tags.tool as tool_module
        importlib.reload(tool_module)

        registry = ToolRegistry()
        assert "karma_tags" in registry
        tool_class = registry.get_tool("karma_tags")
        assert tool_class.__name__ == "KarmaTagTool"

    def test_create_tool_from_registry(self):
        """测试从注册表创建工具。"""
        ToolRegistry.reset_instance()
        import importlib
        import oath_toolchain.tools.karma_tags.tool as tool_module
        importlib.reload(tool_module)

        registry = ToolRegistry()
        tool = registry.create_tool("karma_tags")
        assert tool.name == "karma_tags"
        assert tool.description == "Karma数据标签系统"

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
            "datafor": "测试数据",
            "datefor": "20240101",
            "datatag": ["tag1", "tag2"],
            "tag": ["general"],
        })
        assert result["success"] is True
        assert result["action"] == "create"
        assert "tag_id" in result
        assert "tag" in result
        assert result["tag"]["datafor"] == "测试数据"
        assert result["tag"]["datefor"] == "20240101"

    def test_action_validate_valid(self):
        """测试validate操作（有效标签）。"""
        result = self.tool.execute({
            "action": "validate",
            "datafor": "测试数据",
            "datefor": "20240101",
        })
        assert result["success"] is True
        assert result["action"] == "validate"
        assert result["valid"] is True
        assert result["errors"] == []

    def test_action_validate_invalid(self):
        """测试validate操作（无效标签）。"""
        result = self.tool.execute({
            "action": "validate",
            "datafor": "",
            "datefor": "invalid-date",
        })
        assert result["success"] is True
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_action_sign_with_private_key(self):
        """测试sign操作（使用私钥）。"""
        result = self.tool.execute({
            "action": "sign",
            "datafor": "签名测试",
            "datefor": "20240101",
            "private_key_pem": self.private_key_pem,
            "signer": "gpgca",
        })
        assert result["success"] is True
        assert result["action"] == "sign"
        assert result["signer"] == "gpgca"
        assert result["tag"]["gpgca"] != ""

    def test_action_verify_with_public_key(self):
        """测试verify操作（使用公钥）。"""
        create_result = self.tool.execute({
            "action": "sign",
            "datafor": "验证测试",
            "datefor": "20240101",
            "private_key_pem": self.private_key_pem,
            "signer": "gpgca",
        })
        tag = create_result["tag"]

        result = self.tool.execute({
            "action": "verify",
            "tag": tag,
            "public_key_pem": self.public_key_pem,
            "signer": "gpgca",
        })
        assert result["success"] is True
        assert result["action"] == "verify"
        assert result["valid"] is True

    def test_action_verify_invalid(self):
        """测试verify操作（无效签名）。"""
        other_private, other_public = RSACipher.generate_keypair(key_size=2048)
        other_private_pem = RSACipher.serialize_private_key(other_private)
        other_public_pem = RSACipher.serialize_public_key(other_public)

        create_result = self.tool.execute({
            "action": "sign",
            "datafor": "验证测试",
            "datefor": "20240101",
            "private_key_pem": self.private_key_pem,
            "signer": "gpgca",
        })
        tag = create_result["tag"]

        result = self.tool.execute({
            "action": "verify",
            "tag": tag,
            "public_key_pem": other_public_pem,
            "signer": "gpgca",
        })
        assert result["success"] is True
        assert result["valid"] is False

    def test_action_encode_base64(self):
        """测试encode_base64操作。"""
        result = self.tool.execute({
            "action": "encode_base64",
            "datafor": "base64测试",
            "datefor": "20240101",
            "datatag": ["t1"],
        })
        assert result["success"] is True
        assert result["action"] == "encode_base64"
        assert "base64" in result
        assert isinstance(result["base64"], str)

    def test_action_decode_base64(self):
        """测试decode_base64操作。"""
        encode_result = self.tool.execute({
            "action": "encode_base64",
            "datafor": "base64测试",
            "datefor": "20240101",
        })
        b64_str = encode_result["base64"]

        result = self.tool.execute({
            "action": "decode_base64",
            "base64": b64_str,
        })
        assert result["success"] is True
        assert result["action"] == "decode_base64"
        assert result["tag"]["datafor"] == "base64测试"
        assert result["tag"]["datefor"] == "20240101"

    def test_action_decode_base64_missing_param(self):
        """测试decode_base64缺少参数。"""
        with pytest.raises(ValidationError):
            self.tool.execute({"action": "decode_base64"})

    def test_action_to_json(self):
        """测试to_json操作。"""
        result = self.tool.execute({
            "action": "to_json",
            "datafor": "JSON测试",
            "datefor": "20240101",
        })
        assert result["success"] is True
        assert result["action"] == "to_json"
        assert "json" in result
        assert isinstance(result["json"], str)
        assert "JSON测试" in result["json"]

    def test_action_from_json(self):
        """测试from_json操作。"""
        import json
        tag_data = {
            "datafor": "JSON测试",
            "datefor": "20240101",
            "datatag": ["t1"],
        }
        json_str = json.dumps(tag_data)

        result = self.tool.execute({
            "action": "from_json",
            "json": json_str,
        })
        assert result["success"] is True
        assert result["action"] == "from_json"
        assert result["tag"]["datafor"] == "JSON测试"

    def test_action_from_json_missing_param(self):
        """测试from_json缺少参数。"""
        with pytest.raises(ValidationError):
            self.tool.execute({"action": "from_json"})

    def test_action_index_add(self):
        """测试index_add操作。"""
        result = self.tool.execute({
            "action": "index_add",
            "datafor": "索引测试",
            "datefor": "20240101",
            "dataset_id": "ds1",
        })
        assert result["success"] is True
        assert result["action"] == "index_add"
        assert result["index_size"] == 1

    def test_action_index_search(self):
        """测试index_search操作。"""
        self.tool.execute({
            "action": "index_add",
            "tag_id": "search-1",
            "datafor": "搜索测试",
            "datefor": "20240101",
            "datatag": ["重要"],
        })
        self.tool.execute({
            "action": "index_add",
            "tag_id": "search-2",
            "datafor": "其他用途",
            "datefor": "20240201",
            "datatag": ["普通"],
        })

        result = self.tool.execute({
            "action": "index_search",
            "filters": {"datafor": "搜索测试"},
        })
        assert result["success"] is True
        assert result["action"] == "index_search"
        assert result["count"] == 1
        assert len(result["results"]) == 1

    def test_action_index_stats(self):
        """测试index_stats操作。"""
        self.tool.execute({
            "action": "index_add",
            "tag_id": "stats-1",
            "datafor": "统计测试",
            "datefor": "20240101",
        })
        self.tool.execute({
            "action": "index_add",
            "tag_id": "stats-2",
            "datafor": "统计测试",
            "datefor": "20240201",
        })

        result = self.tool.execute({
            "action": "index_stats",
        })
        assert result["success"] is True
        assert result["action"] == "index_stats"
        assert "statistics" in result
        assert result["statistics"]["total_tags"] == 2

    def test_action_sign_missing_key(self):
        """测试sign操作缺少密钥。"""
        with pytest.raises(ValidationError, match="签名需要private_key_pem参数"):
            self.tool.execute({
                "action": "sign",
                "datafor": "test",
                "datefor": "20240101",
            })

    def test_action_verify_missing_key(self):
        """测试verify操作缺少密钥。"""
        with pytest.raises(ValidationError, match="验证需要public_key_pem参数"):
            self.tool.execute({
                "action": "verify",
                "datafor": "test",
                "datefor": "20240101",
            })

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
        assert metadata["name"] == "karma_tags"
        assert metadata["description"] == "Karma数据标签系统"
        assert metadata["version"] == "0.1.0"
        assert metadata["category"] == "data"
        assert isinstance(metadata["tags"], list)

    def test_tool_repr(self):
        """测试工具的字符串表示。"""
        repr_str = repr(self.tool)
        assert "KarmaTagTool" in repr_str
        assert "karma_tags" in repr_str

    def test_tool_str(self):
        """测试工具的可读字符串。"""
        str_repr = str(self.tool)
        assert "karma_tags" in str_repr
        assert "Karma数据标签系统" in str_repr

    def test_sign_with_tag_dict(self):
        """测试使用tag字典参数签名。"""
        tag_data = {
            "datafor": "tag字典测试",
            "datefor": "20240101",
        }
        result = self.tool.execute({
            "action": "sign",
            "tag": tag_data,
            "private_key_pem": self.private_key_pem,
            "signer": "gpgca",
        })
        assert result["success"] is True
        assert result["tag"]["gpgca"] != ""

    def test_full_workflow(self):
        """测试完整工作流程。"""
        create_result = self.tool.execute({
            "action": "create",
            "datafor": "完整流程",
            "datefor": "20240630",
            "datatag": ["重要", "测试"],
            "tag": ["verified"],
            "custom_info": "自定义信息",
        })
        tag_id = create_result["tag_id"]
        assert create_result["success"] is True

        sign_result = self.tool.execute({
            "action": "sign",
            "tag": create_result["tag"],
            "private_key_pem": self.private_key_pem,
            "signer": "gpgca",
        })
        assert sign_result["success"] is True
        assert sign_result["tag"]["gpgca"] != ""

        verify_result = self.tool.execute({
            "action": "verify",
            "tag": sign_result["tag"],
            "public_key_pem": self.public_key_pem,
            "signer": "gpgca",
        })
        assert verify_result["success"] is True
        assert verify_result["valid"] is True

        encode_result = self.tool.execute({
            "action": "encode_base64",
            "tag": sign_result["tag"],
        })
        assert encode_result["success"] is True

        decode_result = self.tool.execute({
            "action": "decode_base64",
            "base64": encode_result["base64"],
        })
        assert decode_result["success"] is True
        assert decode_result["tag"]["datafor"] == "完整流程"
        assert decode_result["tag"]["gpgca"] == sign_result["tag"]["gpgca"]

        add_result = self.tool.execute({
            "action": "index_add",
            "tag": sign_result["tag"],
            "dataset_id": "workflow-ds",
        })
        assert add_result["success"] is True

        search_result = self.tool.execute({
            "action": "index_search",
            "filters": {"datatag": "重要"},
        })
        assert search_result["success"] is True
        assert search_result["count"] >= 1

        stats_result = self.tool.execute({
            "action": "index_stats",
        })
        assert stats_result["success"] is True
        assert stats_result["statistics"]["total_tags"] >= 1
