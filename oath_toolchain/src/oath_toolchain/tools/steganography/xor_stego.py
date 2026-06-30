"""XOR隐加密算法模块。

提供基于异或运算的隐写技术，支持基础XOR模式和密钥流模式，
可将秘密数据嵌入载体数据中实现信息隐藏。
"""
from __future__ import annotations

import struct
from typing import Optional


class XORSteganography:
    """XOR隐写类。

    利用异或运算将秘密数据嵌入载体数据，支持两种模式：
    - 基础模式：秘密数据直接与载体数据异或
    - 密钥模式：秘密数据与密钥生成的密钥流异或

    同时支持自动长度前缀嵌入与提取。

    Attributes:
        LENGTH_PREFIX_SIZE: 长度前缀占用字节数（4字节，大端无符号整数）
    """

    LENGTH_PREFIX_SIZE: int = 4

    def __init__(self) -> None:
        """初始化XOR隐写工具。"""
        pass

    def embed(
        self,
        secret_data: bytes,
        carrier_data: bytes,
        key: Optional[bytes] = None,
    ) -> bytes:
        """将秘密数据嵌入载体。

        基础模式：直接将秘密数据存储在载体前部。
        密钥模式：使用密钥流加密秘密数据后存储在载体前部。

        Args:
            secret_data: 要嵌入的秘密数据
            carrier_data: 载体数据
            key: 加密密钥，提供时使用密钥流模式，否则使用基础模式

        Returns:
            嵌入秘密数据后的隐写数据

        Raises:
            ValueError: 当秘密数据长度超过载体数据长度时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(secret_data, bytes):
            raise TypeError("秘密数据必须是bytes类型")
        if not isinstance(carrier_data, bytes):
            raise TypeError("载体数据必须是bytes类型")
        if key is not None and not isinstance(key, bytes):
            raise TypeError("密钥必须是bytes类型")

        if len(secret_data) > len(carrier_data):
            raise ValueError(
                f"秘密数据长度({len(secret_data)})超过载体数据长度({len(carrier_data)})"
            )

        if key is not None:
            key_stream = self._generate_key_stream(key, len(secret_data))
            embed_data = bytes(s ^ k for s, k in zip(secret_data, key_stream))
        else:
            embed_data = secret_data

        result = bytearray(carrier_data)
        for i, b in enumerate(embed_data):
            result[i] = b

        return bytes(result)

    def extract(
        self,
        stego_data: bytes,
        secret_length: int,
        key: Optional[bytes] = None,
    ) -> bytes:
        """提取秘密数据。

        Args:
            stego_data: 包含隐藏数据的隐写数据
            secret_length: 秘密数据长度（字节）
            key: 加密密钥，提供时使用密钥流模式，否则使用基础XOR模式

        Returns:
            提取出的秘密数据

        Raises:
            ValueError: 当秘密长度无效时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(stego_data, bytes):
            raise TypeError("隐写数据必须是bytes类型")
        if not isinstance(secret_length, int) or secret_length <= 0:
            raise ValueError("秘密数据长度必须是正整数")
        if key is not None and not isinstance(key, bytes):
            raise TypeError("密钥必须是bytes类型")

        if secret_length > len(stego_data):
            raise ValueError(
                f"秘密数据长度({secret_length})超过隐写数据长度({len(stego_data)})"
            )

        xor_part = stego_data[:secret_length]

        if key is not None:
            key_stream = self._generate_key_stream(key, secret_length)
            secret_data = bytes(s ^ k for s, k in zip(xor_part, key_stream))
        else:
            secret_data = xor_part

        return bytes(secret_data)

    def embed_with_length(
        self,
        secret_data: bytes,
        carrier_data: bytes,
        key: Optional[bytes] = None,
    ) -> bytes:
        """自动嵌入长度前缀的隐写。

        在数据前嵌入4字节的长度前缀，便于自动提取。

        Args:
            secret_data: 要嵌入的秘密数据
            carrier_data: 载体数据
            key: 加密密钥，提供时使用密钥流模式

        Returns:
            嵌入长度前缀和秘密数据后的隐写数据

        Raises:
            ValueError: 当数据过长时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(secret_data, bytes):
            raise TypeError("秘密数据必须是bytes类型")

        total_length = self.LENGTH_PREFIX_SIZE + len(secret_data)
        if total_length > len(carrier_data):
            raise ValueError(
                f"总数据长度({total_length})超过载体容量({len(carrier_data)})"
            )

        length_bytes = struct.pack(">I", len(secret_data))
        combined = length_bytes + secret_data

        return self.embed(combined, carrier_data, key)

    def extract_with_length(
        self,
        stego_data: bytes,
        key: Optional[bytes] = None,
    ) -> bytes:
        """自动检测长度提取秘密数据。

        从隐写数据前部读取4字节长度前缀，然后提取对应长度的秘密数据。

        Args:
            stego_data: 包含隐藏数据的隐写数据
            key: 加密密钥，提供时使用密钥流模式

        Returns:
            提取出的秘密数据

        Raises:
            ValueError: 当数据不足或长度无效时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(stego_data, bytes):
            raise TypeError("隐写数据必须是bytes类型")

        if len(stego_data) < self.LENGTH_PREFIX_SIZE:
            raise ValueError(
                f"隐写数据长度不足，至少需要{self.LENGTH_PREFIX_SIZE}字节"
            )

        length_bytes = stego_data[: self.LENGTH_PREFIX_SIZE]
        if key is not None:
            key_stream = self._generate_key_stream(key, self.LENGTH_PREFIX_SIZE)
            length_bytes = bytes(b ^ k for b, k in zip(length_bytes, key_stream))

        secret_length = struct.unpack(">I", length_bytes)[0]

        total_needed = self.LENGTH_PREFIX_SIZE + secret_length
        if total_needed > len(stego_data):
            raise ValueError(
                f"声明的秘密数据长度({secret_length}字节)超出隐写数据容量"
            )

        combined = self.extract(stego_data, total_needed, key)
        return combined[self.LENGTH_PREFIX_SIZE :]

    def capacity(self, carrier_length: int) -> int:
        """计算载体的隐写容量（含长度前缀）。

        Args:
            carrier_length: 载体数据长度（字节）

        Returns:
            可嵌入的最大秘密数据字节数（扣除长度前缀后）

        Raises:
            ValueError: 当载体长度无效时
        """
        if not isinstance(carrier_length, int) or carrier_length < 0:
            raise ValueError("载体长度必须是非负整数")

        if carrier_length <= self.LENGTH_PREFIX_SIZE:
            return 0
        return carrier_length - self.LENGTH_PREFIX_SIZE

    @staticmethod
    def _generate_key_stream(key: bytes, length: int) -> bytes:
        """生成指定长度的密钥流。

        使用简单的循环密钥扩展方式生成密钥流。

        Args:
            key: 原始密钥
            length: 需要的密钥流长度

        Returns:
            密钥流字节
        """
        if not key:
            raise ValueError("密钥不能为空")

        key_stream = bytearray()
        key_len = len(key)
        for i in range(length):
            key_stream.append(key[i % key_len] ^ (i & 0xFF))
        return bytes(key_stream)
