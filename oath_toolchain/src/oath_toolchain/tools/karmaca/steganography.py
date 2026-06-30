"""KARMACA维度空间隐写模块。

提供基于空间字典坐标微调的隐写功能，通过LSB（最低有效位）方式
微调坐标值来嵌入秘密数据，实现信息的隐藏传输。
"""
from __future__ import annotations

import base64
import struct
from typing import Any, Dict, List

import numpy as np

from ...core.base import OathTool
from ...core.exceptions import ValidationError
from ...core.math.vector import Vector
from ...core.registry import register_tool
from .space_dict import KarmaSpaceDict


@register_tool
class DimensionSteganography(OathTool):
    """维度空间隐写工具。

    利用空间字典的坐标点微调嵌入比特信息，通过LSB（最低有效位）
    方式微调坐标值，实现秘密数据的隐藏。

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
        _precision: 嵌入精度（小数点后第几位用于嵌入）
    """

    name: str = "dimension_steganography"
    description: str = "维度空间隐写工具"
    _version: str = "0.1.0"
    _tags: list[str] = ["steganography", "karmaca", "space-dict"]
    _category: str = "crypto"

    def __init__(self, precision: int = 6) -> None:
        """初始化隐写工具。

        Args:
            precision: 嵌入精度，即小数点后第几位用于嵌入数据，默认为6
        """
        super().__init__()
        self._precision = precision

    @property
    def precision(self) -> int:
        """获取嵌入精度。

        Returns:
            嵌入精度
        """
        return self._precision

    def embed(self, secret_data: bytes, space_dict: KarmaSpaceDict) -> KarmaSpaceDict:
        """将秘密数据嵌入空间字典。

        通过微调空间字典中坐标点的坐标值来嵌入秘密数据。
        每个坐标分量可以嵌入指定精度位的数据。

        Args:
            secret_data: 要嵌入的秘密数据
            space_dict: 原始空间字典

        Returns:
            嵌入数据后的新空间字典

        Raises:
            ValueError: 当数据过长或参数无效时
        """
        if not isinstance(secret_data, bytes):
            raise ValueError("秘密数据必须是bytes类型")
        if space_dict.size == 0:
            raise ValueError("空间字典为空")

        capacity = self._calculate_capacity(space_dict)
        data_length = len(secret_data)

        if data_length + 4 > capacity:
            raise ValueError(
                f"数据过长: 需要嵌入{data_length + 4}字节，容量仅{capacity}字节"
            )

        bits = self._bytes_to_bits(secret_data)
        length_bits = self._int_to_bits(data_length, 32)
        all_bits = length_bits + bits

        new_points: List[Vector] = []
        bit_idx = 0
        total_bits = len(all_bits)

        for point in space_dict._points:
            components = point.to_list()
            new_components = []

            for comp in components:
                if bit_idx < total_bits:
                    new_comp = self._embed_bit(comp, all_bits[bit_idx])
                    bit_idx += 1
                else:
                    new_comp = comp
                new_components.append(new_comp)

            new_points.append(Vector(new_components))

        new_space_dict = KarmaSpaceDict(
            dimensions=space_dict.dimensions,
            key_size=space_dict.key_size,
        )
        new_space_dict.build(new_points, list(space_dict._keys))

        return new_space_dict

    def extract(self, space_dict: KarmaSpaceDict, data_length: int = 0) -> bytes:
        """从空间字典提取秘密数据。

        Args:
            space_dict: 包含隐藏数据的空间字典
            data_length: 数据长度（字节），为0时自动从头部读取

        Returns:
            提取出的秘密数据

        Raises:
            ValueError: 当参数无效时
        """
        if space_dict.size == 0:
            raise ValueError("空间字典为空")

        all_bits: List[int] = []

        for point in space_dict._points:
            components = point.to_list()
            for comp in components:
                bit = self._extract_bit(comp)
                all_bits.append(bit)

        if data_length == 0:
            if len(all_bits) < 32:
                raise ValueError("空间字典容量不足，无法读取数据长度")
            length_bits = all_bits[:32]
            data_length = self._bits_to_int(length_bits)

            max_data_bits = len(all_bits) - 32
            if data_length * 8 > max_data_bits:
                raise ValueError(
                    f"声明的数据长度({data_length}字节)超出可用容量"
                )

            data_bits = all_bits[32 : 32 + data_length * 8]
        else:
            if data_length * 8 > len(all_bits):
                raise ValueError(
                    f"数据长度({data_length}字节)超出可用容量"
                )
            data_bits = all_bits[32 : 32 + data_length * 8]

        return self._bits_to_bytes(data_bits)

    def get_capacity(self, space_dict: KarmaSpaceDict) -> int:
        """获取空间字典的隐写容量。

        Args:
            space_dict: 空间字典

        Returns:
            可嵌入的最大字节数（含4字节长度头）
        """
        return self._calculate_capacity(space_dict)

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具。

        Args:
            params: 参数字典
                - action: "embed" 或 "extract"
                - secret_data: base64编码的秘密数据（embed时需要）
                - space_dict: 空间字典的字典表示
                - data_length: 数据长度（extract时可选）

        Returns:
            结果字典
                - success: 是否成功
                - result: base64编码的结果或空间字典
                - message: 消息

        Raises:
            ValidationError: 当参数验证失败时
        """
        try:
            self.validate_params(params)

            action = params["action"]
            space_dict_data = params["space_dict"]

            space_dict = KarmaSpaceDict()
            space_dict.from_dict(space_dict_data)

            if action == "embed":
                secret_data_b64 = params["secret_data"]
                secret_data = base64.b64decode(secret_data_b64)

                result_dict = self.embed(secret_data, space_dict)
                return {
                    "success": True,
                    "result": result_dict.to_dict(),
                    "message": "嵌入成功",
                }
            elif action == "extract":
                data_length = params.get("data_length", 0)
                result = self.extract(space_dict, data_length)
                return {
                    "success": True,
                    "result": base64.b64encode(result).decode("utf-8"),
                    "message": "提取成功",
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
        required_fields = ["action", "space_dict"]
        for field in required_fields:
            if field not in params:
                raise ValidationError(
                    field=field,
                    message=f"缺少必要参数: {field}",
                )

        if params["action"] not in ("embed", "extract"):
            raise ValidationError(
                field="action",
                message=f"不支持的操作: {params['action']}",
            )

        if params["action"] == "embed" and "secret_data" not in params:
            raise ValidationError(
                field="secret_data",
                message="embed操作需要secret_data参数",
            )

        if not isinstance(params["space_dict"], dict):
            raise ValidationError(
                field="space_dict",
                message="space_dict必须是字典",
            )

        return True

    def _calculate_capacity(self, space_dict: KarmaSpaceDict) -> int:
        """计算空间字典的隐写容量（字节数）。

        Args:
            space_dict: 空间字典

        Returns:
            可嵌入的最大字节数
        """
        total_components = space_dict.size * space_dict.dimensions
        total_bits = total_components
        return total_bits // 8

    def _embed_bit(self, value: float, bit: int) -> float:
        """在浮点数中嵌入一个比特。

        通过修改指定小数位来嵌入比特信息。

        Args:
            value: 原始浮点数值
            bit: 要嵌入的比特（0或1）

        Returns:
            嵌入比特后的浮点数值
        """
        scale = 10 ** self._precision
        scaled = round(value * scale)
        if bit == 1:
            scaled = scaled | 1
        else:
            scaled = scaled & ~1
        return scaled / scale

    def _extract_bit(self, value: float) -> int:
        """从浮点数中提取一个比特。

        Args:
            value: 包含隐藏比特的浮点数值

        Returns:
            提取出的比特（0或1）
        """
        scale = 10 ** self._precision
        scaled = round(value * scale)
        return int(scaled & 1)

    @staticmethod
    def _bytes_to_bits(data: bytes) -> List[int]:
        """将字节转换为比特列表。

        Args:
            data: 字节数据

        Returns:
            比特列表（每个元素为0或1）
        """
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return bits

    @staticmethod
    def _bits_to_bytes(bits: List[int]) -> bytes:
        """将比特列表转换为字节。

        Args:
            bits: 比特列表

        Returns:
            字节数据
        """
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte_bits = bits[i : i + 8]
            if len(byte_bits) < 8:
                byte_bits = byte_bits + [0] * (8 - len(byte_bits))
            byte = 0
            for bit in byte_bits:
                byte = (byte << 1) | bit
            result.append(byte)
        return bytes(result)

    @staticmethod
    def _int_to_bits(value: int, num_bits: int) -> List[int]:
        """将整数转换为比特列表。

        Args:
            value: 整数值
            num_bits: 比特数

        Returns:
            比特列表
        """
        bits = []
        for i in range(num_bits - 1, -1, -1):
            bits.append((value >> i) & 1)
        return bits

    @staticmethod
    def _bits_to_int(bits: List[int]) -> int:
        """将比特列表转换为整数。

        Args:
            bits: 比特列表

        Returns:
            整数值
        """
        value = 0
        for bit in bits:
            value = (value << 1) | bit
        return value
