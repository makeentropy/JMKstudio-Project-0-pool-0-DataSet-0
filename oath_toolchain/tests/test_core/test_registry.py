"""工具注册表单元测试。"""
import pytest

from oath_toolchain.core.registry import ToolRegistry, register_tool
from oath_toolchain.core.base import OathTool
from oath_toolchain.core.exceptions import ToolNotFoundError


class SampleToolA(OathTool):
    """测试工具A。"""

    __test__ = False

    _tags = ["tag1", "common"]
    _category = "cat1"

    @property
    def name(self) -> str:
        return "test_tool_a"

    @property
    def description(self) -> str:
        return "测试工具A"

    def execute(self, params: dict) -> dict:
        return {"tool": "A"}


class SampleToolB(OathTool):
    """测试工具B。"""

    __test__ = False

    _tags = ["tag2", "common"]
    _category = "cat2"

    @property
    def name(self) -> str:
        return "test_tool_b"

    @property
    def description(self) -> str:
        return "测试工具B"

    def execute(self, params: dict) -> dict:
        return {"tool": "B"}


class TestToolRegistry:
    """测试工具注册表。"""

    def setup_method(self):
        """每个测试前重置注册表。"""
        ToolRegistry.reset_instance()
        self.registry = ToolRegistry()

    def test_singleton_pattern(self):
        """测试单例模式。"""
        reg1 = ToolRegistry()
        reg2 = ToolRegistry()
        assert reg1 is reg2

    def test_register_tool(self):
        """测试注册工具。"""
        self.registry.register(SampleToolA)
        assert self.registry.has_tool("test_tool_a")

    def test_register_returns_class(self):
        """测试register返回类本身。"""
        result = self.registry.register(SampleToolA)
        assert result is SampleToolA

    def test_register_invalid_class(self):
        """测试注册非工具类。"""

        class NotATool:
            pass

        with pytest.raises(TypeError):
            self.registry.register(NotATool)

    def test_register_duplicate_name(self):
        """测试重复注册相同名称的工具。"""
        self.registry.register(SampleToolA)
        with pytest.raises(ValueError, match="test_tool_a"):
            self.registry.register(SampleToolA)

    def test_unregister_tool(self):
        """测试注销工具。"""
        self.registry.register(SampleToolA)
        assert self.registry.has_tool("test_tool_a")
        self.registry.unregister("test_tool_a")
        assert not self.registry.has_tool("test_tool_a")

    def test_unregister_nonexistent_tool(self):
        """测试注销不存在的工具。"""
        with pytest.raises(ToolNotFoundError):
            self.registry.unregister("nonexistent")

    def test_get_tool(self):
        """测试获取工具类。"""
        self.registry.register(SampleToolA)
        tool_class = self.registry.get_tool("test_tool_a")
        assert tool_class is SampleToolA

    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具。"""
        with pytest.raises(ToolNotFoundError):
            self.registry.get_tool("nonexistent")

    def test_create_tool(self):
        """测试创建工具实例。"""
        self.registry.register(SampleToolA)
        tool = self.registry.create_tool("test_tool_a")
        assert isinstance(tool, SampleToolA)
        assert tool.name == "test_tool_a"

    def test_create_nonexistent_tool(self):
        """测试创建不存在的工具。"""
        with pytest.raises(ToolNotFoundError):
            self.registry.create_tool("nonexistent")

    def test_list_tools_empty(self):
        """测试空注册表的工具列表。"""
        assert self.registry.list_tools() == []

    def test_list_tools(self):
        """测试列出所有工具。"""
        self.registry.register(SampleToolA)
        self.registry.register(SampleToolB)
        tools = self.registry.list_tools()
        assert len(tools) == 2
        assert "test_tool_a" in tools
        assert "test_tool_b" in tools

    def test_list_tool_metadata(self):
        """测试列出工具元数据。"""
        self.registry.register(SampleToolA)
        metadata_list = self.registry.list_tool_metadata()
        assert len(metadata_list) == 1
        assert metadata_list[0]["name"] == "test_tool_a"
        assert metadata_list[0]["category"] == "cat1"

    def test_filter_by_tag(self):
        """测试按标签筛选。"""
        self.registry.register(SampleToolA)
        self.registry.register(SampleToolB)

        result1 = self.registry.filter_by_tag("tag1")
        assert result1 == ["test_tool_a"]

        result2 = self.registry.filter_by_tag("tag2")
        assert result2 == ["test_tool_b"]

        result_common = self.registry.filter_by_tag("common")
        assert len(result_common) == 2
        assert "test_tool_a" in result_common
        assert "test_tool_b" in result_common

        result_none = self.registry.filter_by_tag("nonexistent")
        assert result_none == []

    def test_filter_by_category(self):
        """测试按分类筛选。"""
        self.registry.register(SampleToolA)
        self.registry.register(SampleToolB)

        result1 = self.registry.filter_by_category("cat1")
        assert result1 == ["test_tool_a"]

        result2 = self.registry.filter_by_category("cat2")
        assert result2 == ["test_tool_b"]

        result_none = self.registry.filter_by_category("nonexistent")
        assert result_none == []

    def test_has_tool(self):
        """测试has_tool方法。"""
        assert not self.registry.has_tool("test_tool_a")
        self.registry.register(SampleToolA)
        assert self.registry.has_tool("test_tool_a")

    def test_len(self):
        """测试len方法。"""
        assert len(self.registry) == 0
        self.registry.register(SampleToolA)
        assert len(self.registry) == 1
        self.registry.register(SampleToolB)
        assert len(self.registry) == 2

    def test_contains(self):
        """测试in运算符。"""
        assert "test_tool_a" not in self.registry
        self.registry.register(SampleToolA)
        assert "test_tool_a" in self.registry

    def test_reset_instance(self):
        """测试重置单例。"""
        self.registry.register(SampleToolA)
        ToolRegistry.reset_instance()
        new_registry = ToolRegistry()
        assert len(new_registry) == 0


class TestRegisterToolDecorator:
    """测试register_tool装饰器。"""

    def setup_method(self):
        """每个测试前重置注册表。"""
        ToolRegistry.reset_instance()

    def test_decorator_registers_tool(self):
        """测试装饰器能正确注册工具。"""

        @register_tool
        class DecoratedTool(OathTool):
            @property
            def name(self) -> str:
                return "decorated_tool"

            @property
            def description(self) -> str:
                return "装饰器测试工具"

            def execute(self, params: dict) -> dict:
                return {}

        registry = ToolRegistry()
        assert registry.has_tool("decorated_tool")
