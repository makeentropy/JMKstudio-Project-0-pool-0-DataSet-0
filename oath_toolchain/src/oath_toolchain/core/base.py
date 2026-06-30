"""神誓工具链工具基类模块。

定义所有工具的抽象基类，提供统一的接口和元数据管理。
"""
from abc import ABC, abstractmethod
from typing import Any, Optional

from .logging_util import get_logger


class OathTool(ABC):
    """神誓工具抽象基类。

    所有工具都必须继承此类并实现抽象方法。
    提供统一的工具接口和元数据管理。

    Attributes:
        _version: 工具版本号
        _author: 工具作者
        _tags: 工具标签列表
        _category: 工具分类
        _logger: 工具日志记录器
    """

    _version: str = "0.1.0"
    _author: str = "Oath Toolchain Team"
    _tags: list[str] = []
    _category: str = "general"

    def __init__(self) -> None:
        """初始化工具。"""
        self._logger = get_logger(f"tools.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称。

        必须是唯一的标识符，使用小写字母和下划线。
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述。

        简要说明工具的功能和用途。
        """
        ...

    @property
    def version(self) -> str:
        """工具版本号。

        Returns:
            版本号字符串
        """
        return self._version

    @property
    def author(self) -> str:
        """工具作者。

        Returns:
            作者名称
        """
        return self._author

    @property
    def tags(self) -> list[str]:
        """工具标签列表。

        Returns:
            标签列表的副本
        """
        return list(self._tags)

    @property
    def category(self) -> str:
        """工具分类。

        Returns:
            分类名称
        """
        return self._category

    @property
    def metadata(self) -> dict[str, Any]:
        """获取工具的完整元数据。

        Returns:
            包含所有元数据的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "category": self.category,
        }

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具。

        Args:
            params: 输入参数字典

        Returns:
            执行结果字典

        Raises:
            ValidationError: 当参数验证失败时
            OathToolchainError: 当执行过程中出现错误时
        """
        ...

    def validate_params(self, params: dict[str, Any]) -> bool:
        """验证输入参数。

        默认实现返回True，子类可以重写此方法进行参数验证。

        Args:
            params: 输入参数字典

        Returns:
            验证通过返回True

        Raises:
            ValidationError: 当参数验证失败时
        """
        return True

    def __repr__(self) -> str:
        """返回工具的字符串表示。"""
        return f"<{self.__class__.__name__} name='{self.name}' version='{self.version}'>"

    def __str__(self) -> str:
        """返回工具的可读字符串。"""
        return f"{self.name} v{self.version} - {self.description}"
