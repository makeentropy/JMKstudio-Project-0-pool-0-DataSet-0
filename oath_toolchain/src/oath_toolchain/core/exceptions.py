"""神誓工具链异常体系模块。

定义了工具链中使用的所有异常类，提供统一的错误码和详细信息。
"""
from typing import Any, Optional


class OathToolchainError(Exception):
    """神誓工具链基础异常类。

    所有自定义异常都继承自此类，提供统一的错误码和详细信息格式。

    Attributes:
        code: 错误码，用于标识错误类型
        message: 错误详细信息
        details: 额外的错误详情信息
    """

    code: str = "E0000"
    message: str = "神誓工具链未知错误"

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """初始化异常。

        Args:
            message: 错误消息，如未提供则使用类默认值
            code: 错误码，如未提供则使用类默认值
            details: 额外的错误详情
        """
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """返回异常的字符串表示。"""
        base = f"[{self.code}] {self.message}"
        if self.details:
            base += f" - 详情: {self.details}"
        return base

    def __repr__(self) -> str:
        """返回异常的对象表示。"""
        return f"{self.__class__.__name__}(code='{self.code}', message='{self.message}')"


class ToolNotFoundError(OathToolchainError):
    """工具未找到异常。

    当请求的工具在注册表中不存在时抛出此异常。
    """

    code: str = "E1001"
    message: str = "工具未找到"

    def __init__(
        self,
        tool_name: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """初始化工具未找到异常。

        Args:
            tool_name: 未找到的工具名称
            message: 自定义错误消息
            details: 额外的错误详情
        """
        msg = message or f"{self.message}: {tool_name}"
        full_details = details or {}
        full_details.setdefault("tool_name", tool_name)
        super().__init__(message=msg, details=full_details)


class ConfigError(OathToolchainError):
    """配置错误异常。

    当配置加载、验证或访问出现问题时抛出此异常。
    """

    code: str = "E2001"
    message: str = "配置错误"

    def __init__(
        self,
        config_key: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """初始化配置错误异常。

        Args:
            config_key: 相关的配置键名
            message: 自定义错误消息
            details: 额外的错误详情
        """
        msg = message or self.message
        if config_key:
            msg = f"{msg}: {config_key}"
        full_details = details or {}
        if config_key:
            full_details.setdefault("config_key", config_key)
        super().__init__(message=msg, details=full_details)


class EncryptionError(OathToolchainError):
    """加密错误异常。

    当加密、解密或密钥管理操作失败时抛出此异常。
    """

    code: str = "E3001"
    message: str = "加密操作失败"

    def __init__(
        self,
        operation: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """初始化加密错误异常。

        Args:
            operation: 失败的操作类型（encrypt/decrypt/sign等）
            message: 自定义错误消息
            details: 额外的错误详情
        """
        msg = message or self.message
        if operation:
            msg = f"{msg} [{operation}]"
        full_details = details or {}
        if operation:
            full_details.setdefault("operation", operation)
        super().__init__(message=msg, details=full_details)


class ValidationError(OathToolchainError):
    """验证错误异常。

    当数据验证失败时抛出此异常。
    """

    code: str = "E4001"
    message: str = "数据验证失败"

    def __init__(
        self,
        field: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """初始化验证错误异常。

        Args:
            field: 验证失败的字段名
            message: 自定义错误消息
            details: 额外的错误详情
        """
        msg = message or self.message
        if field:
            msg = f"{msg}: {field}"
        full_details = details or {}
        if field:
            full_details.setdefault("field", field)
        super().__init__(message=msg, details=full_details)


class AuthenticationError(OathToolchainError):
    """认证错误异常。

    当身份认证或授权失败时抛出此异常。
    """

    code: str = "E5001"
    message: str = "身份认证失败"

    def __init__(
        self,
        auth_type: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """初始化认证错误异常。

        Args:
            auth_type: 认证类型（token/password/api_key等）
            message: 自定义错误消息
            details: 额外的错误详情
        """
        msg = message or self.message
        if auth_type:
            msg = f"{msg} [{auth_type}]"
        full_details = details or {}
        if auth_type:
            full_details.setdefault("auth_type", auth_type)
        super().__init__(message=msg, details=full_details)
