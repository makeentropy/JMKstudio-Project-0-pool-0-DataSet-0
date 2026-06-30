"""隐写工具集主模块。

提供多载体隐写工具的统一入口，集成XOR隐写、证书隐写、
文本隐写等多种隐写技术，以及容量分析功能。
"""
from __future__ import annotations

import base64
from typing import Any, Optional

from ...core.base import OathTool
from ...core.exceptions import ValidationError
from ...core.registry import register_tool
from .xor_stego import XORSteganography
from .cert_stego import CertificateSteganography
from .text_stego import TextSteganography
from .capacity_analyzer import StegoCapacityAnalyzer


@register_tool
class SteganographyTool(OathTool):
    """多载体隐写工具集。

    集成多种隐写技术，提供统一的操作接口，支持：
    - XOR隐写
    - 证书隐写（扩展字段、序列号）
    - 文本隐写（空格、Unicode、大小写）
    - 隐写容量与安全性分析

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
        _xor_stego: XOR隐写实例
        _cert_stego: 证书隐写实例
        _text_stego: 文本隐写实例
        _analyzer: 容量分析器实例
    """

    name: str = "steganography"
    description: str = "多载体隐写工具集"
    _version: str = "0.1.0"
    _tags: list[str] = ["steganography", "crypto", "security", "multi-carrier"]
    _category: str = "crypto"

    def __init__(self) -> None:
        """初始化隐写工具集。"""
        super().__init__()
        self._xor_stego = XORSteganography()
        self._cert_stego = CertificateSteganography()
        self._text_stego = TextSteganography()
        self._analyzer = StegoCapacityAnalyzer()

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具。

        根据action参数执行不同的隐写操作。

        Args:
            params: 输入参数字典，必须包含action字段
                支持的action:
                - xor_embed: XOR隐写嵌入
                - xor_extract: XOR隐写提取
                - cert_embed: 证书扩展字段隐写嵌入
                - cert_extract: 证书扩展字段隐写提取
                - cert_serial_embed: 证书序列号隐写嵌入
                - cert_serial_extract: 证书序列号隐写提取
                - text_whitespace_embed: 文本空格隐写嵌入
                - text_whitespace_extract: 文本空格隐写提取
                - text_unicode_embed: 文本Unicode隐写嵌入
                - text_unicode_extract: 文本Unicode隐写提取
                - text_case_embed: 文本大小写隐写嵌入
                - text_case_extract: 文本大小写隐写提取
                - analyze: 隐写容量与安全性分析
                - report: 生成隐写分析报告

        Returns:
            执行结果字典

        Raises:
            ValidationError: 当参数验证失败时
        """
        self.validate_params(params)

        action = params.get("action")

        try:
            if action == "xor_embed":
                return self._action_xor_embed(params)
            elif action == "xor_extract":
                return self._action_xor_extract(params)
            elif action == "cert_embed":
                return self._action_cert_embed(params)
            elif action == "cert_extract":
                return self._action_cert_extract(params)
            elif action == "cert_serial_embed":
                return self._action_cert_serial_embed(params)
            elif action == "cert_serial_extract":
                return self._action_cert_serial_extract(params)
            elif action == "text_whitespace_embed":
                return self._action_text_whitespace_embed(params)
            elif action == "text_whitespace_extract":
                return self._action_text_whitespace_extract(params)
            elif action == "text_unicode_embed":
                return self._action_text_unicode_embed(params)
            elif action == "text_unicode_extract":
                return self._action_text_unicode_extract(params)
            elif action == "text_case_embed":
                return self._action_text_case_embed(params)
            elif action == "text_case_extract":
                return self._action_text_case_extract(params)
            elif action == "analyze":
                return self._action_analyze(params)
            elif action == "report":
                return self._action_report(params)
            else:
                raise ValidationError(
                    field="action",
                    message=f"不支持的操作: {action}",
                )
        except ValidationError:
            raise
        except Exception as e:
            return {
                "success": False,
                "action": action,
                "result": None,
                "message": f"执行失败: {str(e)}",
            }

    def validate_params(self, params: dict[str, Any]) -> bool:
        """验证输入参数。

        Args:
            params: 输入参数字典

        Returns:
            验证通过返回True

        Raises:
            ValidationError: 当参数验证失败时
        """
        if "action" not in params:
            raise ValidationError(
                field="action",
                message="缺少必需的action参数",
            )

        action = params["action"]
        valid_actions = [
            "xor_embed", "xor_extract",
            "cert_embed", "cert_extract",
            "cert_serial_embed", "cert_serial_extract",
            "text_whitespace_embed", "text_whitespace_extract",
            "text_unicode_embed", "text_unicode_extract",
            "text_case_embed", "text_case_extract",
            "analyze", "report",
        ]

        if action not in valid_actions:
            raise ValidationError(
                field="action",
                message=f"不支持的操作: {action}",
            )

        return True

    def _action_xor_embed(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行XOR隐写嵌入操作。"""
        secret_data = self._get_bytes_param(params, "secret_data")
        carrier_data = self._get_bytes_param(params, "carrier_data")
        key = self._get_optional_bytes_param(params, "key")
        with_length = params.get("with_length", True)

        if with_length:
            stego_data = self._xor_stego.embed_with_length(secret_data, carrier_data, key)
        else:
            stego_data = self._xor_stego.embed(secret_data, carrier_data, key)

        return {
            "success": True,
            "action": "xor_embed",
            "result": base64.b64encode(stego_data).decode("utf-8"),
            "secret_size": len(secret_data),
            "carrier_size": len(carrier_data),
        }

    def _action_xor_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行XOR隐写提取操作。"""
        stego_data = self._get_bytes_param(params, "stego_data")
        key = self._get_optional_bytes_param(params, "key")
        secret_length = params.get("secret_length", 0)
        with_length = params.get("with_length", True)

        if with_length:
            secret_data = self._xor_stego.extract_with_length(stego_data, key)
        else:
            if secret_length <= 0:
                raise ValidationError(
                    field="secret_length",
                    message="with_length为False时必须提供secret_length",
                )
            secret_data = self._xor_stego.extract(stego_data, secret_length, key)

        return {
            "success": True,
            "action": "xor_extract",
            "result": base64.b64encode(secret_data).decode("utf-8"),
            "secret_size": len(secret_data),
        }

    def _action_cert_embed(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行证书扩展字段隐写嵌入操作。"""
        cert_pem = self._get_bytes_param(params, "cert_pem")
        secret_data = self._get_bytes_param(params, "secret_data")
        oid = params.get("oid")

        stego_cert = self._cert_stego.embed_in_extension(cert_pem, secret_data, oid)

        return {
            "success": True,
            "action": "cert_embed",
            "result": stego_cert.decode("utf-8"),
            "secret_size": len(secret_data),
        }

    def _action_cert_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行证书扩展字段隐写提取操作。"""
        cert_pem = self._get_bytes_param(params, "cert_pem")
        oid = params.get("oid")

        secret_data = self._cert_stego.extract_from_extension(cert_pem, oid)

        return {
            "success": True,
            "action": "cert_extract",
            "result": base64.b64encode(secret_data).decode("utf-8"),
            "secret_size": len(secret_data),
        }

    def _action_cert_serial_embed(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行证书序列号隐写嵌入操作。"""
        cert_pem = self._get_bytes_param(params, "cert_pem")
        secret_byte = params.get("secret_byte")

        if not isinstance(secret_byte, int) or not (0 <= secret_byte <= 255):
            raise ValidationError(
                field="secret_byte",
                message="secret_byte必须是0-255之间的整数",
            )

        stego_cert = self._cert_stego.embed_in_serial(cert_pem, secret_byte)

        return {
            "success": True,
            "action": "cert_serial_embed",
            "result": stego_cert.decode("utf-8"),
            "secret_byte": secret_byte,
        }

    def _action_cert_serial_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行证书序列号隐写提取操作。"""
        cert_pem = self._get_bytes_param(params, "cert_pem")

        secret_byte = self._cert_stego.extract_from_serial(cert_pem)

        return {
            "success": True,
            "action": "cert_serial_extract",
            "result": secret_byte,
            "secret_byte": secret_byte,
        }

    def _action_text_whitespace_embed(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行文本空格隐写嵌入操作。"""
        text = self._get_str_param(params, "text")
        secret_data = self._get_bytes_param(params, "secret_data")

        stego_text = self._text_stego.embed_whitespace(text, secret_data)

        return {
            "success": True,
            "action": "text_whitespace_embed",
            "result": stego_text,
            "secret_size": len(secret_data),
        }

    def _action_text_whitespace_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行文本空格隐写提取操作。"""
        stego_text = self._get_str_param(params, "stego_text")

        secret_data = self._text_stego.extract_whitespace(stego_text)

        return {
            "success": True,
            "action": "text_whitespace_extract",
            "result": base64.b64encode(secret_data).decode("utf-8"),
            "secret_size": len(secret_data),
        }

    def _action_text_unicode_embed(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行文本Unicode隐写嵌入操作。"""
        text = self._get_str_param(params, "text")
        secret_data = self._get_bytes_param(params, "secret_data")

        stego_text = self._text_stego.embed_unicode(text, secret_data)

        return {
            "success": True,
            "action": "text_unicode_embed",
            "result": stego_text,
            "secret_size": len(secret_data),
        }

    def _action_text_unicode_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行文本Unicode隐写提取操作。"""
        stego_text = self._get_str_param(params, "stego_text")

        secret_data = self._text_stego.extract_unicode(stego_text)

        return {
            "success": True,
            "action": "text_unicode_extract",
            "result": base64.b64encode(secret_data).decode("utf-8"),
            "secret_size": len(secret_data),
        }

    def _action_text_case_embed(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行文本大小写隐写嵌入操作。"""
        text = self._get_str_param(params, "text")
        secret_data = self._get_bytes_param(params, "secret_data")

        stego_text = self._text_stego.embed_case(text, secret_data)

        return {
            "success": True,
            "action": "text_case_embed",
            "result": stego_text,
            "secret_size": len(secret_data),
        }

    def _action_text_case_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行文本大小写隐写提取操作。"""
        stego_text = self._get_str_param(params, "stego_text")

        secret_data = self._text_stego.extract_case(stego_text)

        return {
            "success": True,
            "action": "text_case_extract",
            "result": base64.b64encode(secret_data).decode("utf-8"),
            "secret_size": len(secret_data),
        }

    def _action_analyze(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行隐写容量分析操作。"""
        carrier_data = self._get_bytes_param(params, "carrier_data")
        carrier_type = params.get("carrier_type", "binary")

        analysis = self._analyzer.analyze_carrier(carrier_data, carrier_type)

        return {
            "success": True,
            "action": "analyze",
            "result": analysis,
        }

    def _action_report(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行隐写分析报告生成操作。"""
        carrier_data = self._get_bytes_param(params, "carrier_data")
        secret_data = self._get_bytes_param(params, "secret_data")
        method = params.get("method", "xor")

        report = self._analyzer.generate_report(carrier_data, secret_data, method)

        return {
            "success": True,
            "action": "report",
            "result": report,
        }

    def _get_bytes_param(self, params: dict[str, Any], key: str) -> bytes:
        """获取字节类型参数。

        Args:
            params: 参数字典
            key: 参数名

        Returns:
            字节值

        Raises:
            ValidationError: 当参数不存在或类型错误时
        """
        if key not in params:
            raise ValidationError(
                field=key,
                message=f"缺少必需的参数: {key}",
            )

        value = params[key]
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            try:
                return base64.b64decode(value)
            except Exception:
                return value.encode("utf-8")
        else:
            raise ValidationError(
                field=key,
                message=f"参数{key}必须是bytes或str类型",
            )

    def _get_str_param(self, params: dict[str, Any], key: str) -> str:
        """获取字符串类型参数。

        Args:
            params: 参数字典
            key: 参数名

        Returns:
            字符串值

        Raises:
            ValidationError: 当参数不存在或类型错误时
        """
        if key not in params:
            raise ValidationError(
                field=key,
                message=f"缺少必需的参数: {key}",
            )

        value = params[key]
        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return value.decode("utf-8")
        else:
            raise ValidationError(
                field=key,
                message=f"参数{key}必须是str类型",
            )

    def _get_optional_bytes_param(
        self,
        params: dict[str, Any],
        key: str,
    ) -> Optional[bytes]:
        """获取可选的字节类型参数。

        Args:
            params: 参数字典
            key: 参数名

        Returns:
            字节值或None
        """
        if key not in params or params[key] is None:
            return None

        value = params[key]
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            try:
                return base64.b64decode(value)
            except Exception:
                return value.encode("utf-8")
        else:
            raise ValidationError(
                field=key,
                message=f"参数{key}必须是bytes或str类型",
            )
