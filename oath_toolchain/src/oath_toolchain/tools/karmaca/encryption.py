"""KARMACA空间字典加密模块。

提供基于空间字典的加密解密功能，使用空间坐标映射得到密钥，
采用AES-256-GCM加密算法，并将坐标作为关联数据进行验证。
"""
from __future__ import annotations

import base64
from typing import Any, Dict

from ...core.base import OathTool
from ...core.crypto.hash import Hash
from ...core.crypto.primitives import AESCipher
from ...core.crypto.kdf import KDF
from ...core.exceptions import ValidationError
from ...core.math.vector import Vector
from ...core.registry import register_tool
from .space_dict import KarmaSpaceDict


@register_tool
class KarmacaEncryption(OathTool):
    """KARMACA空间字典加密工具。

    使用空间坐标从空间字典中获取或派生加密密钥，
    采用AES-256-GCM模式进行加密解密。

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
    """

    name: str = "karmaca_encryption"
    description: str = "KARMACA空间字典加密工具"
    _version: str = "0.1.0"
    _tags: list[str] = ["encryption", "karmaca", "space-dict"]
    _category: str = "crypto"

    def __init__(self) -> None:
        """初始化加密工具。"""
        super().__init__()

    def encrypt(
        self,
        data: bytes,
        coordinate: Vector,
        space_dict: KarmaSpaceDict,
        use_interpolation: bool = True,
    ) -> bytes:
        """加密数据。

        使用空间坐标从空间字典获取密钥，然后用AES-256-GCM加密数据。
        坐标信息作为关联数据(AAD)进行认证。

        Args:
            data: 待加密的明文数据
            coordinate: 空间坐标
            space_dict: 空间字典
            use_interpolation: 是否使用插值密钥，默认True

        Returns:
            加密后的数据，格式: nonce(12) + tag(16) + ciphertext

        Raises:
            ValueError: 当参数无效时
            EncryptionError: 当加密失败时
        """
        if not isinstance(data, bytes):
            raise ValueError("数据必须是bytes类型")
        if coordinate.dim != space_dict.dimensions:
            raise ValueError(
                f"坐标维度不匹配: 期望{space_dict.dimensions}维，实际{coordinate.dim}维"
            )
        if space_dict.size == 0:
            raise ValueError("空间字典为空")

        if use_interpolation:
            base_key = space_dict.interpolate_key(coordinate)
        else:
            base_key = space_dict.get_key(coordinate)

        derived_key = KDF.hkdf(
            base_key,
            salt=self._coord_to_salt(coordinate),
            info=b"karmaca_encryption",
            length=32,
        )

        associated_data = self._coord_to_bytes(coordinate)

        ciphertext, nonce, tag = AESCipher.encrypt(
            data,
            derived_key,
            associated_data=associated_data,
        )

        return nonce + tag + ciphertext

    def decrypt(
        self,
        ciphertext: bytes,
        coordinate: Vector,
        space_dict: KarmaSpaceDict,
        use_interpolation: bool = True,
    ) -> bytes:
        """解密数据。

        Args:
            ciphertext: 加密数据，格式: nonce(12) + tag(16) + ciphertext
            coordinate: 空间坐标
            space_dict: 空间字典
            use_interpolation: 是否使用插值密钥，默认True

        Returns:
            解密后的明文数据

        Raises:
            ValueError: 当参数无效时
            EncryptionError: 当解密或认证失败时
        """
        if not isinstance(ciphertext, bytes):
            raise ValueError("密文必须是bytes类型")
        if len(ciphertext) < 28:
            raise ValueError("密文格式无效，长度不足")
        if coordinate.dim != space_dict.dimensions:
            raise ValueError(
                f"坐标维度不匹配: 期望{space_dict.dimensions}维，实际{coordinate.dim}维"
            )
        if space_dict.size == 0:
            raise ValueError("空间字典为空")

        nonce = ciphertext[:12]
        tag = ciphertext[12:28]
        encrypted_data = ciphertext[28:]

        if use_interpolation:
            base_key = space_dict.interpolate_key(coordinate)
        else:
            base_key = space_dict.get_key(coordinate)

        derived_key = KDF.hkdf(
            base_key,
            salt=self._coord_to_salt(coordinate),
            info=b"karmaca_encryption",
            length=32,
        )

        associated_data = self._coord_to_bytes(coordinate)

        return AESCipher.decrypt(
            encrypted_data,
            derived_key,
            nonce,
            tag,
            associated_data=associated_data,
        )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具。

        Args:
            params: 参数字典
                - action: "encrypt" 或 "decrypt"
                - data: base64编码的数据字符串
                - coordinate: 坐标列表
                - space_dict: 空间字典的字典表示
                - use_interpolation: 是否使用插值，可选

        Returns:
            结果字典
                - result: base64编码的结果
                - success: 是否成功
                - message: 消息

        Raises:
            ValidationError: 当参数验证失败时
        """
        try:
            self.validate_params(params)

            action = params["action"]
            data_b64 = params["data"]
            coordinate_list = params["coordinate"]
            space_dict_data = params["space_dict"]
            use_interpolation = params.get("use_interpolation", True)

            data = base64.b64decode(data_b64)
            coordinate = Vector(coordinate_list)

            space_dict = KarmaSpaceDict()
            space_dict.from_dict(space_dict_data)

            if action == "encrypt":
                result = self.encrypt(data, coordinate, space_dict, use_interpolation)
                return {
                    "success": True,
                    "result": base64.b64encode(result).decode("utf-8"),
                    "message": "加密成功",
                }
            elif action == "decrypt":
                result = self.decrypt(data, coordinate, space_dict, use_interpolation)
                return {
                    "success": True,
                    "result": base64.b64encode(result).decode("utf-8"),
                    "message": "解密成功",
                }
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
                "result": None,
                "message": f"执行失败: {str(e)}",
            }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证输入参数。

        Args:
            params: 输入参数字典

        Returns:
            验证通过返回True

        Raises:
            ValidationError: 当参数验证失败时
        """
        required_fields = ["action", "data", "coordinate", "space_dict"]
        for field in required_fields:
            if field not in params:
                raise ValidationError(
                    field=field,
                    message=f"缺少必要参数: {field}",
                )

        if params["action"] not in ("encrypt", "decrypt"):
            raise ValidationError(
                field="action",
                message=f"不支持的操作: {params['action']}",
            )

        if not isinstance(params["data"], str):
            raise ValidationError(
                field="data",
                message="data必须是base64编码的字符串",
            )

        if not isinstance(params["coordinate"], list):
            raise ValidationError(
                field="coordinate",
                message="coordinate必须是列表",
            )

        if not isinstance(params["space_dict"], dict):
            raise ValidationError(
                field="space_dict",
                message="space_dict必须是字典",
            )

        return True

    @staticmethod
    def _coord_to_bytes(coordinate: Vector) -> bytes:
        """将坐标转换为字节。

        Args:
            coordinate: 空间坐标

        Returns:
            坐标的字节表示
        """
        import struct

        components = coordinate.to_list()
        return struct.pack(f"{len(components)}d", *components)

    @staticmethod
    def _coord_to_salt(coordinate: Vector) -> bytes:
        """将坐标转换为盐值。

        Args:
            coordinate: 空间坐标

        Returns:
            盐值字节
        """
        coord_bytes = KarmacaEncryption._coord_to_bytes(coordinate)
        return Hash.sha256(coord_bytes)[:16]
