"""工具基类单元测试。"""
import pytest

from oath_toolchain.core.base import OathTool


class ConcreteTool(OathTool):
    """具体的测试工具类。"""

    _version = "1.2.3"
    _author = "Test Author"
    _tags = ["test", "example"]
    _category = "testing"

    @property
    def name(self) -> str:
        return "concrete_test_tool"

    @property
    def description(self) -> str:
        return "一个用于测试的具体工具"

    def execute(self, params: dict) -> dict:
        return {"result": "success", "input": params}


class MinimalTool(OathTool):
    """最小化的工具类。"""

    @property
    def name(self) -> str:
        return "minimal_tool"

    @property
    def description(self) -> str:
        return "最小化工具"

    def execute(self, params: dict) -> dict:
        return {}


class TestOathTool:
    """测试工具基类。"""

    def test_cannot_instantiate_abstract_class(self):
        """测试不能直接实例化抽象类。"""
        with pytest.raises(TypeError):
            OathTool()

    def test_concrete_tool_instantiation(self):
        """测试具体工具的实例化。"""
        tool = ConcreteTool()
        assert tool is not None

    def test_name_property(self):
        """测试name属性。"""
        tool = ConcreteTool()
        assert tool.name == "concrete_test_tool"

    def test_description_property(self):
        """测试description属性。"""
        tool = ConcreteTool()
        assert tool.description == "一个用于测试的具体工具"

    def test_version_property(self):
        """测试version属性。"""
        tool = ConcreteTool()
        assert tool.version == "1.2.3"

    def test_default_version(self):
        """测试默认版本号。"""
        tool = MinimalTool()
        assert tool.version == "0.1.0"

    def test_author_property(self):
        """测试author属性。"""
        tool = ConcreteTool()
        assert tool.author == "Test Author"

    def test_default_author(self):
        """测试默认作者。"""
        tool = MinimalTool()
        assert tool.author == "Oath Toolchain Team"

    def test_tags_property(self):
        """测试tags属性。"""
        tool = ConcreteTool()
        assert tool.tags == ["test", "example"]

    def test_tags_returns_copy(self):
        """测试tags返回的是副本。"""
        tool = ConcreteTool()
        tags = tool.tags
        tags.append("new_tag")
        assert "new_tag" not in tool.tags

    def test_default_tags_empty(self):
        """测试默认标签为空列表。"""
        tool = MinimalTool()
        assert tool.tags == []

    def test_category_property(self):
        """测试category属性。"""
        tool = ConcreteTool()
        assert tool.category == "testing"

    def test_default_category(self):
        """测试默认分类。"""
        tool = MinimalTool()
        assert tool.category == "general"

    def test_metadata_property(self):
        """测试metadata属性。"""
        tool = ConcreteTool()
        meta = tool.metadata
        assert meta["name"] == "concrete_test_tool"
        assert meta["description"] == "一个用于测试的具体工具"
        assert meta["version"] == "1.2.3"
        assert meta["author"] == "Test Author"
        assert meta["tags"] == ["test", "example"]
        assert meta["category"] == "testing"

    def test_execute_method(self):
        """测试execute方法。"""
        tool = ConcreteTool()
        result = tool.execute({"key": "value"})
        assert result["result"] == "success"
        assert result["input"] == {"key": "value"}

    def test_validate_params_default_true(self):
        """测试默认的validate_params返回True。"""
        tool = ConcreteTool()
        assert tool.validate_params({}) is True

    def test_repr(self):
        """测试repr表示。"""
        tool = ConcreteTool()
        r = repr(tool)
        assert "ConcreteTool" in r
        assert "concrete_test_tool" in r
        assert "1.2.3" in r

    def test_str(self):
        """测试str表示。"""
        tool = ConcreteTool()
        s = str(tool)
        assert "concrete_test_tool" in s
        assert "1.2.3" in s
        assert "一个用于测试的具体工具" in s
