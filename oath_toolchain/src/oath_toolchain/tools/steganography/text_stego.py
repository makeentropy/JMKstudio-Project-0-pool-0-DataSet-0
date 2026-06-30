"""文本载体隐写模块。

提供多种文本隐写技术，包括空格/制表符隐写、Unicode零宽字符隐写、
大小写隐写等，可在不明显影响文本可读性的前提下隐藏秘密数据。
"""
from __future__ import annotations

from typing import Optional


class TextSteganography:
    """文本隐写类。

    提供多种基于文本载体的隐写方法：
    - 空格/制表符隐写：利用行尾的空格和制表符编码数据
    - Unicode零宽字符隐写：使用零宽字符编码比特数据
    - 大小写隐写：利用英文字母的大小写变化编码数据

    Attributes:
        ZERO_WIDTH_CHARS: 用于Unicode隐写的零宽字符对
    """

    ZERO_WIDTH_CHARS: tuple[str, str] = ("\u200b", "\u200c")

    def __init__(self) -> None:
        """初始化文本隐写工具。"""
        pass

    def embed_whitespace(
        self,
        text: str,
        secret_data: bytes,
    ) -> str:
        """空格/制表符隐写（行尾空格隐写）。

        利用每行末尾的空格和制表符来编码比特数据：
        - 空格(' ')表示比特0
        - 制表符('\t')表示比特1

        Args:
            text: 载体文本
            secret_data: 要嵌入的秘密数据

        Returns:
            嵌入秘密数据后的文本

        Raises:
            ValueError: 当文本行数不足时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(text, str):
            raise TypeError("文本必须是str类型")
        if not isinstance(secret_data, bytes):
            raise TypeError("秘密数据必须是bytes类型")

        lines = text.split("\n")
        num_lines = len(lines)
        data_bits = self._bytes_to_bits(secret_data)
        num_bits = len(data_bits)

        max_bits = num_lines - 1
        if num_bits + 32 > max_bits:
            raise ValueError(
                f"文本行数不足，需要至少{(num_bits + 32)}行，当前有{num_lines}行"
            )

        length_bits = self._int_to_bits(len(secret_data), 32)
        all_bits = length_bits + data_bits

        result_lines = []
        for i, line in enumerate(lines):
            if i < len(all_bits):
                line = line.rstrip()
                if all_bits[i] == 0:
                    line += " "
                else:
                    line += "\t"
            result_lines.append(line)

        return "\n".join(result_lines)

    def extract_whitespace(
        self,
        stego_text: str,
    ) -> bytes:
        """提取空格隐写数据。

        从行尾的空格和制表符中提取秘密数据。

        Args:
            stego_text: 包含隐藏数据的文本

        Returns:
            提取出的秘密数据

        Raises:
            ValueError: 当数据格式无效时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(stego_text, str):
            raise TypeError("文本必须是str类型")

        lines = stego_text.split("\n")
        bits = []

        for line in lines:
            if len(line) > 0:
                last_char = line[-1]
                if last_char == " ":
                    bits.append(0)
                elif last_char == "\t":
                    bits.append(1)
                else:
                    break

        if len(bits) < 32:
            raise ValueError("数据不足，无法读取长度前缀")

        length_bits = bits[:32]
        data_length = self._bits_to_int(length_bits)

        data_bits = bits[32 : 32 + data_length * 8]
        if len(data_bits) < data_length * 8:
            raise ValueError("数据长度不足")

        return self._bits_to_bytes(data_bits)

    def embed_unicode(
        self,
        text: str,
        secret_data: bytes,
    ) -> str:
        """Unicode零宽字符隐写。

        使用零宽字符编码秘密数据，插入到文本的空格位置：
        - ZERO WIDTH SPACE (U+200B) 表示比特0
        - ZERO WIDTH NON-JOINER (U+200C) 表示比特1

        数据前添加32位长度前缀。

        Args:
            text: 载体文本
            secret_data: 要嵌入的秘密数据

        Returns:
            嵌入秘密数据后的文本

        Raises:
            ValueError: 当文本中没有足够的空格位置时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(text, str):
            raise TypeError("文本必须是str类型")
        if not isinstance(secret_data, bytes):
            raise TypeError("秘密数据必须是bytes类型")

        data_bits = self._bytes_to_bits(secret_data)
        length_bits = self._int_to_bits(len(secret_data), 32)
        all_bits = length_bits + data_bits

        space_count = text.count(" ")
        if len(all_bits) > space_count:
            raise ValueError(
                f"文本中空格数量不足，需要至少{len(all_bits)}个空格，当前有{space_count}个"
            )

        result = []
        bit_idx = 0

        for char in text:
            if char == " " and bit_idx < len(all_bits):
                if all_bits[bit_idx] == 0:
                    result.append(" " + self.ZERO_WIDTH_CHARS[0])
                else:
                    result.append(" " + self.ZERO_WIDTH_CHARS[1])
                bit_idx += 1
            else:
                result.append(char)

        return "".join(result)

    def extract_unicode(
        self,
        stego_text: str,
    ) -> bytes:
        """提取Unicode隐写数据。

        从零宽字符中提取秘密数据。

        Args:
            stego_text: 包含隐藏数据的文本

        Returns:
            提取出的秘密数据

        Raises:
            ValueError: 当数据格式无效时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(stego_text, str):
            raise TypeError("文本必须是str类型")

        bits = []
        i = 0
        while i < len(stego_text):
            char = stego_text[i]
            if char == self.ZERO_WIDTH_CHARS[0]:
                bits.append(0)
            elif char == self.ZERO_WIDTH_CHARS[1]:
                bits.append(1)
            i += 1

        if len(bits) < 32:
            raise ValueError("数据不足，无法读取长度前缀")

        length_bits = bits[:32]
        data_length = self._bits_to_int(length_bits)

        data_bits = bits[32 : 32 + data_length * 8]
        if len(data_bits) < data_length * 8:
            raise ValueError("数据长度不足")

        return self._bits_to_bytes(data_bits)

    def embed_case(
        self,
        text: str,
        secret_data: bytes,
    ) -> str:
        """大小写隐写（英文文本）。

        利用英文字母的大小写变化来编码比特数据：
        - 小写表示比特0
        - 大写表示比特1

        仅修改字母字符的大小写，不影响非字母字符。

        Args:
            text: 载体文本（建议为英文）
            secret_data: 要嵌入的秘密数据

        Returns:
            嵌入秘密数据后的文本

        Raises:
            ValueError: 当文本中英文字母数量不足时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(text, str):
            raise TypeError("文本必须是str类型")
        if not isinstance(secret_data, bytes):
            raise TypeError("秘密数据必须是bytes类型")

        alpha_count = sum(1 for c in text if c.isalpha())
        data_bits = self._bytes_to_bits(secret_data)
        total_bits_needed = len(data_bits) + 32

        if total_bits_needed > alpha_count:
            raise ValueError(
                f"文本中英文字母数量不足，需要至少{total_bits_needed}个字母，当前有{alpha_count}个"
            )

        length_bits = self._int_to_bits(len(secret_data), 32)
        all_bits = length_bits + data_bits

        result = []
        bit_idx = 0

        for char in text:
            if char.isalpha() and bit_idx < len(all_bits):
                if all_bits[bit_idx] == 0:
                    result.append(char.lower())
                else:
                    result.append(char.upper())
                bit_idx += 1
            else:
                result.append(char)

        return "".join(result)

    def extract_case(
        self,
        stego_text: str,
    ) -> bytes:
        """提取大小写隐写数据。

        从英文字母的大小写变化中提取秘密数据。

        Args:
            stego_text: 包含隐藏数据的文本

        Returns:
            提取出的秘密数据

        Raises:
            ValueError: 当数据格式无效时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(stego_text, str):
            raise TypeError("文本必须是str类型")

        bits = []
        for char in stego_text:
            if char.isalpha():
                if char.isupper():
                    bits.append(1)
                else:
                    bits.append(0)

        if len(bits) < 32:
            raise ValueError("数据不足，无法读取长度前缀")

        length_bits = bits[:32]
        data_length = self._bits_to_int(length_bits)

        data_bits = bits[32 : 32 + data_length * 8]
        if len(data_bits) < data_length * 8:
            raise ValueError("数据长度不足")

        return self._bits_to_bytes(data_bits)

    def capacity(
        self,
        text: str,
        method: str = "unicode",
    ) -> int:
        """计算文本的隐写容量。

        Args:
            text: 载体文本
            method: 隐写方法，可选 'whitespace'、'unicode'、'case'

        Returns:
            可嵌入的最大秘密数据字节数（扣除长度前缀后）

        Raises:
            ValueError: 当方法不支持时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(text, str):
            raise TypeError("文本必须是str类型")

        if method == "whitespace":
            num_lines = len(text.split("\n"))
            total_bits = max(0, num_lines - 1)
        elif method == "unicode":
            space_count = text.count(" ")
            total_bits = space_count
        elif method == "case":
            alpha_count = sum(1 for c in text if c.isalpha())
            total_bits = alpha_count
        else:
            raise ValueError(f"不支持的隐写方法: {method}")

        if total_bits <= 32:
            return 0
        return (total_bits - 32) // 8

    @staticmethod
    def _bytes_to_bits(data: bytes) -> list[int]:
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
    def _bits_to_bytes(bits: list[int]) -> bytes:
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
    def _int_to_bits(value: int, num_bits: int) -> list[int]:
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
    def _bits_to_int(bits: list[int]) -> int:
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
