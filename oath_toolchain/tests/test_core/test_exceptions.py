"""异常体系单元测试。"""
import pytest

from oath_toolchain.core.exceptions import (
    OathToolchainError,
    ToolNotFoundError,
    ConfigError,
    EncryptionError,
    ValidationError,
    AuthenticationError,
)


class TestOathToolchainError:
    """测试基础异常类。"""

    def test_default_values(self):
        """测试默认值。"""
        err = OathToolchainError()
        assert err.code == "E0000"
        assert err.message == "神誓工具链未知错误"
        assert err.details == {}

    def test_custom_message(self):
        """测试自定义消息。"""
        err = OathToolchainError(message="自定义错误")
        assert err.message == "自定义错误"

    def test_custom_code(self):
        """测试自定义错误码。"""
        err = OathToolchainError(code="E9999")
        assert err.code == "E9999"

    def test_custom_details(self):
        """测试自定义详情。"""
        details = {"key": "value", "num": 123}
        err = OathToolchainError(details=details)
        assert err.details == details

    def test_str_representation(self):
        """测试字符串表示。"""
        err = OathToolchainError(message="测试错误", code="E1234")
        s = str(err)
        assert "[E1234]" in s
        assert "测试错误" in s

    def test_str_with_details(self):
        """测试带详情的字符串表示。"""
        err = OathToolchainError(details={"info": "test"})
        s = str(err)
        assert "详情" in s
        assert "info" in s

    def test_repr_representation(self):
        """测试repr表示。"""
        err = OathToolchainError(message="测试", code="E1111")
        r = repr(err)
        assert "OathToolchainError" in r
        assert "E1111" in r


class TestToolNotFoundError:
    """测试工具未找到异常。"""

    def test_tool_name_in_details(self):
        """测试工具名称是否在详情中。"""
        err = ToolNotFoundError(tool_name="test_tool")
        assert err.details["tool_name"] == "test_tool"
        assert "test_tool" in str(err)
        assert err.code == "E1001"

    def test_custom_message(self):
        """测试自定义消息。"""
        err = ToolNotFoundError(tool_name="my_tool", message="找不到啊")
        assert "找不到啊" in err.message


class TestConfigError:
    """测试配置错误异常。"""

    def test_config_key(self):
        """测试配置键。"""
        err = ConfigError(config_key="database.host")
        assert err.details["config_key"] == "database.host"
        assert "database.host" in str(err)
        assert err.code == "E2001"

    def test_no_config_key(self):
        """测试无配置键。"""
        err = ConfigError()
        assert err.message == "配置错误"


class TestEncryptionError:
    """测试加密错误异常。"""

    def test_operation(self):
        """测试操作类型。"""
        err = EncryptionError(operation="encrypt")
        assert err.details["operation"] == "encrypt"
        assert "encrypt" in str(err)
        assert err.code == "E3001"

    def test_no_operation(self):
        """测试无操作类型。"""
        err = EncryptionError()
        assert err.message == "加密操作失败"


class TestValidationError:
    """测试验证错误异常。"""

    def test_field(self):
        """测试字段。"""
        err = ValidationError(field="username")
        assert err.details["field"] == "username"
        assert "username" in str(err)
        assert err.code == "E4001"

    def test_no_field(self):
        """测试无字段。"""
        err = ValidationError()
        assert err.message == "数据验证失败"


class TestAuthenticationError:
    """测试认证错误异常。"""

    def test_auth_type(self):
        """测试认证类型。"""
        err = AuthenticationError(auth_type="token")
        assert err.details["auth_type"] == "token"
        assert "token" in str(err)
        assert err.code == "E5001"

    def test_no_auth_type(self):
        """测试无认证类型。"""
        err = AuthenticationError()
        assert err.message == "身份认证失败"


def test_exception_hierarchy():
    """测试异常继承关系。"""
    assert issubclass(ToolNotFoundError, OathToolchainError)
    assert issubclass(ConfigError, OathToolchainError)
    assert issubclass(EncryptionError, OathToolchainError)
    assert issubclass(ValidationError, OathToolchainError)
    assert issubclass(AuthenticationError, OathToolchainError)

    err = ToolNotFoundError(tool_name="test")
    assert isinstance(err, OathToolchainError)
    assert isinstance(err, Exception)
