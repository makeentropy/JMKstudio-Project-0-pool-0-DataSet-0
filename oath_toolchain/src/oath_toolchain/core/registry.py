"""神誓工具链工具注册与发现模块。

提供工具的注册、发现和管理功能，使用单例模式确保全局唯一。
"""
from typing import Optional, Type

from .base import OathTool
from .exceptions import ToolNotFoundError
from .logging_util import get_logger

_logger = get_logger("registry")


class ToolRegistry:
    """工具注册表。

    管理所有可用工具的注册和发现，支持按标签、分类筛选。
    使用单例模式确保全局唯一实例。

    Attributes:
        _tools: 已注册的工具类字典，键为工具名称，值为工具类
    """

    _instance: Optional["ToolRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "ToolRegistry":
        """单例模式实现。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """初始化注册表。"""
        if self._initialized:
            return
        self._tools: dict[str, Type[OathTool]] = {}
        self._initialized = True

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（主要用于测试）。"""
        cls._instance = None
        cls._initialized = False

    def register(self, tool_class: Type[OathTool]) -> Type[OathTool]:
        """注册一个工具类。

        Args:
            tool_class: 要注册的工具类，必须是OathTool的子类

        Returns:
            注册的工具类，方便作为装饰器使用

        Raises:
            TypeError: 当tool_class不是OathTool的子类时
            ValueError: 当工具名称已存在时
        """
        if not isinstance(tool_class, type) or not issubclass(tool_class, OathTool):
            raise TypeError(f"工具类必须是OathTool的子类，收到: {type(tool_class)}")

        temp_instance = tool_class.__new__(tool_class)
        OathTool.__init__(temp_instance)
        tool_name = temp_instance.name

        if tool_name in self._tools:
            raise ValueError(f"工具名称 '{tool_name}' 已存在")

        self._tools[tool_name] = tool_class
        _logger.info(f"工具已注册: {tool_name}")
        return tool_class

    def unregister(self, name: str) -> None:
        """注销一个工具。

        Args:
            name: 工具名称

        Raises:
            ToolNotFoundError: 当工具不存在时
        """
        if name not in self._tools:
            raise ToolNotFoundError(tool_name=name)
        del self._tools[name]
        _logger.info(f"工具已注销: {name}")

    def get_tool(self, name: str) -> Type[OathTool]:
        """获取指定名称的工具类。

        Args:
            name: 工具名称

        Returns:
            工具类

        Raises:
            ToolNotFoundError: 当工具不存在时
        """
        if name not in self._tools:
            raise ToolNotFoundError(tool_name=name)
        return self._tools[name]

    def create_tool(self, name: str) -> OathTool:
        """创建指定名称的工具实例。

        Args:
            name: 工具名称

        Returns:
            工具实例

        Raises:
            ToolNotFoundError: 当工具不存在时
        """
        tool_class = self.get_tool(name)
        return tool_class()

    def list_tools(self) -> list[str]:
        """列出所有已注册的工具名称。

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def list_tool_metadata(self) -> list[dict]:
        """列出所有已注册工具的元数据。

        Returns:
            工具元数据列表
        """
        metadata_list = []
        for tool_name, tool_class in self._tools.items():
            try:
                instance = tool_class()
                metadata_list.append(instance.metadata)
            except Exception:
                metadata_list.append({"name": tool_name, "error": "无法获取元数据"})
        return metadata_list

    def filter_by_tag(self, tag: str) -> list[str]:
        """按标签筛选工具。

        Args:
            tag: 标签名称

        Returns:
            匹配的工具名称列表
        """
        result = []
        for tool_name, tool_class in self._tools.items():
            try:
                instance = tool_class()
                if tag in instance.tags:
                    result.append(tool_name)
            except Exception:
                continue
        return result

    def filter_by_category(self, category: str) -> list[str]:
        """按分类筛选工具。

        Args:
            category: 分类名称

        Returns:
            匹配的工具名称列表
        """
        result = []
        for tool_name, tool_class in self._tools.items():
            try:
                instance = tool_class()
                if instance.category == category:
                    result.append(tool_name)
            except Exception:
                continue
        return result

    def has_tool(self, name: str) -> bool:
        """检查工具是否已注册。

        Args:
            name: 工具名称

        Returns:
            如果已注册返回True，否则返回False
        """
        return name in self._tools

    def __len__(self) -> int:
        """返回已注册工具的数量。"""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """检查工具是否存在（支持in运算符）。"""
        return name in self._tools


def register_tool(tool_class: Type[OathTool]) -> Type[OathTool]:
    """工具注册装饰器。

    使用方式:
        @register_tool
        class MyTool(OathTool):
            ...

    Args:
        tool_class: 要注册的工具类

    Returns:
        注册的工具类
    """
    registry = ToolRegistry()
    registry.register(tool_class)
    return tool_class
