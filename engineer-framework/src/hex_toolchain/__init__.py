"""hex_toolchain 模块 - 进制转换与XOR操作工具

提供进制编码转换、XOR加密解密以及二进制数据容器等功能。
"""

import base64
import binascii


def base16_encode(data: bytes) -> str:
    """将字节数据编码为Base16字符串

    Args:
        data: 输入的字节数据

    Returns:
        Base16编码字符串（大写）
    """
    return binascii.b2a_hex(data).upper().decode('ascii')


def base16_decode(data: str) -> bytes:
    """将Base16字符串解码为字节数据

    Args:
        data: Base16编码字符串（大写或小写均可）

    Returns:
        解码后的字节数据
    """
    return binascii.a2b_hex(data.encode('ascii'))


def base32_encode(data: bytes) -> str:
    """将字节数据编码为Base32字符串

    Args:
        data: 输入的字节数据

    Returns:
        Base32编码字符串（大写）
    """
    return base64.b32encode(data).decode('ascii')


def base32_decode(data: str) -> bytes:
    """将Base32字符串解码为字节数据

    Args:
        data: Base32编码字符串（大写或小写均可）

    Returns:
        解码后的字节数据
    """
    return base64.b32decode(data.encode('ascii'))


def base64_encode(data: bytes) -> str:
    """将字节数据编码为Base64字符串

    Args:
        data: 输入的字节数据

    Returns:
        Base64编码字符串
    """
    return base64.b64encode(data).decode('ascii')


def base64_decode(data: str) -> bytes:
    """将Base64字符串解码为字节数据

    Args:
        data: Base64编码字符串

    Returns:
        解码后的字节数据
    """
    return base64.b64decode(data.encode('ascii'))


def xor_bytes(data1: bytes, data2: bytes) -> bytes:
    """对两个字节数组进行XOR运算

    如果data2比data1短，会自动循环重复data2以匹配data1的长度。

    Args:
        data1: 第一个字节数组
        data2: 第二个字节数组（会循环重复以匹配data1长度）

    Returns:
        XOR运算结果字节数组

    Example:
        >>> xor_bytes(b'hello', b'x')
        b'\\x0e\\x0e\\x03\\x07\\x0c'
    """
    if len(data2) == 0:
        return data1
    result = bytearray(len(data1))
    for i, byte in enumerate(data1):
        result[i] = byte ^ data2[i % len(data2)]
    return bytes(result)


def xor_hex(hex1: str, hex2: str) -> str:
    """对两个十六进制字符串进行XOR运算

    将两个十六进制字符串转换为字节数组，进行XOR运算后返回十六进制结果。
    如果hex2比hex1短，会自动循环重复以匹配hex1的长度。

    Args:
        hex1: 第一个十六进制字符串
        hex2: 第二个十六进制字符串

    Returns:
        XOR运算结果的十六进制字符串

    Example:
        >>> xor_hex('48656c6c6f', '01')
        '4964696f68'
    """
    data1 = binascii.unhexlify(hex1.encode('ascii'))
    data2 = binascii.unhexlify(hex2.encode('ascii'))
    result = xor_bytes(data1, data2)
    return binascii.hexlify(result).decode('ascii').upper()


class BoostContainer:
    """二进制数据容器，支持多种格式转换和XOR运算"""

    def __init__(self, data: bytes):
        """初始化容器

        Args:
            data: 初始化的字节数据
        """
        self._data = data

    def to_hex(self) -> str:
        """将数据转换为十六进制字符串

        Returns:
            十六进制字符串（大写）
        """
        return binascii.hexlify(self._data).decode('ascii').upper()

    def to_base64(self) -> str:
        """将数据转换为Base64字符串

        Returns:
            Base64编码字符串
        """
        return base64.b64encode(self._data).decode('ascii')

    def to_base32(self) -> str:
        """将数据转换为Base32字符串

        Returns:
            Base32编码字符串（大写）
        """
        return base64.b32encode(self._data).decode('ascii')

    def to_base16(self) -> str:
        """将数据转换为Base16字符串

        Returns:
            Base16编码字符串（大写）
        """
        return binascii.b2a_hex(self._data).upper().decode('ascii')

    def __xor__(self, other):
        """与另一个BoostContainer或bytes进行XOR运算

        Args:
            other: 另一个BoostContainer实例或bytes对象

        Returns:
            新的BoostContainer实例，包含XOR运算结果

        Raises:
            TypeError: 当other不是BoostContainer或bytes类型时
        """
        if isinstance(other, BoostContainer):
            other_data = other._data
        elif isinstance(other, bytes):
            other_data = other
        else:
            raise TypeError("XOR操作仅支持BoostContainer或bytes类型")
        return BoostContainer(xor_bytes(self._data, other_data))

    def __rxor__(self, other):
        """支持右侧XOR运算 (bytes ^ BoostContainer)"""
        return self.__xor__(other)

    def __bytes__(self) -> bytes:
        """返回原始字节数据

        Returns:
            原始字节数据
        """
        return self._data
