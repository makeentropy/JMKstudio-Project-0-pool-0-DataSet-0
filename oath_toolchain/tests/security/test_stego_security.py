"""隐写安全测试。"""
from __future__ import annotations

import math
import os
import re

import pytest

from oath_toolchain.tools.steganography.text_stego import TextSteganography


pytestmark = [pytest.mark.security, pytest.mark.steganography]


def calculate_entropy(data: bytes) -> float:
    """计算数据的香农熵。

    Args:
        data: 输入数据

    Returns:
        熵值（bits/byte）
    """
    if not data:
        return 0.0

    freq = [0] * 256
    for byte in data:
        freq[byte] += 1

    length = len(data)
    entropy = 0.0
    for count in freq:
        if count > 0:
            p = count / length
            entropy -= p * math.log2(p)

    return entropy


def char_frequency(text: str) -> dict:
    """计算字符频率。

    Args:
        text: 输入文本

    Returns:
        字符频率字典
    """
    freq = {}
    for char in text:
        freq[char] = freq.get(char, 0) + 1
    return freq


STEGO_TEST_DATA = b"Secret123"


class TestTextStegoStatisticalAnalysis:
    """隐写后统计特性分析。"""

    def _generate_carrier_lines(self, num_lines=500):
        """生成载体文本（按行）。"""
        lines = []
        for i in range(num_lines):
            lines.append(f"Line {i + 1}: This is a sample carrier text line for testing.")
        return "\n".join(lines)

    def _generate_carrier_spaces(self, num_spaces=500):
        """生成载体文本（按空格）。"""
        words = []
        for i in range(num_spaces):
            words.append(f"word{i}")
        return " ".join(words)

    def test_whitespace_stego_length_preservation(self):
        """测试空格隐写后文本行数不变。"""
        carrier = self._generate_carrier_lines(500)
        stego = TextSteganography()

        stego_text = stego.embed_whitespace(carrier, STEGO_TEST_DATA)

        original_lines = carrier.split("\n")
        stego_lines = stego_text.split("\n")

        assert len(original_lines) == len(stego_lines)

        original_length = len(carrier)
        stego_length = len(stego_text)
        length_diff = stego_length - original_length

        print(f"\n空格隐写长度变化:")
        print(f"  原始长度: {original_length}")
        print(f"  隐写后长度: {stego_length}")
        print(f"  长度差: {length_diff} chars")
        print(f"  变化比例: {length_diff/original_length*100:.3f}%")

        assert length_diff > 0

    def test_whitespace_stego_whitespace_ratio(self):
        """测试空格隐写后空白字符比例变化。"""
        carrier = self._generate_carrier_lines(500)
        stego = TextSteganography()

        stego_text = stego.embed_whitespace(carrier, STEGO_TEST_DATA)

        original_ws = sum(1 for c in carrier if c in " \t")
        stego_ws = sum(1 for c in stego_text if c in " \t")

        original_ratio = original_ws / len(carrier)
        stego_ratio = stego_ws / len(stego_text)

        print(f"\n空格隐写空白字符比例:")
        print(f"  原始空白比例: {original_ratio*100:.2f}%")
        print(f"  隐写后空白比例: {stego_ratio*100:.2f}%")
        print(f"  空白字符增加: {stego_ws - original_ws}")

        assert stego_ratio > original_ratio

    def test_unicode_stego_length_change(self):
        """测试Unicode零宽字符隐写后长度变化。"""
        carrier = self._generate_carrier_spaces(500)
        stego = TextSteganography()

        stego_text = stego.embed_unicode(carrier, STEGO_TEST_DATA)

        original_length = len(carrier)
        stego_length = len(stego_text)
        length_diff = stego_length - original_length

        print(f"\n零宽字符隐写长度变化:")
        print(f"  原始长度: {original_length} chars")
        print(f"  隐写后长度: {stego_length} chars")
        print(f"  长度差: {length_diff} chars (零宽字符数)")
        print(f"  数据大小: {len(STEGO_TEST_DATA)} bytes")

        assert stego_length > original_length
        assert length_diff > len(STEGO_TEST_DATA) * 4

    def test_unicode_invisibility(self):
        """测试零宽字符的不可见性（正则检测）。"""
        carrier = self._generate_carrier_spaces(200)
        stego = TextSteganography()

        stego_text = stego.embed_unicode(carrier, STEGO_TEST_DATA)

        visible_chars_pattern = re.compile(r"[^\u200b\u200c\u200d\u2060\ufeff]")
        visible_original = visible_chars_pattern.findall(carrier)
        visible_stego = visible_chars_pattern.findall(stego_text)

        assert len(visible_original) == len(visible_stego)
        assert "".join(visible_original) == "".join(visible_stego)

        zero_width_chars = sum(
            1 for c in stego_text if c in "\u200b\u200c\u200d\u2060\ufeff"
        )
        print(f"\n零宽字符数量: {zero_width_chars}")
        assert zero_width_chars > 0

    def test_whitespace_stego_correctness_roundtrip(self):
        """测试空格隐写的正确性（往返测试）。"""
        carrier = self._generate_carrier_lines(500)
        stego = TextSteganography()

        stego_text = stego.embed_whitespace(carrier, STEGO_TEST_DATA)
        extracted = stego.extract_whitespace(stego_text)

        assert extracted == STEGO_TEST_DATA

    def test_unicode_stego_correctness_roundtrip(self):
        """测试Unicode零宽字符隐写的正确性（往返测试）。"""
        carrier = self._generate_carrier_spaces(500)
        stego = TextSteganography()

        stego_text = stego.embed_unicode(carrier, STEGO_TEST_DATA)
        extracted = stego.extract_unicode(stego_text)

        assert extracted == STEGO_TEST_DATA

    def test_case_stego_correctness_roundtrip(self):
        """测试大小写隐写的正确性（往返测试）。"""
        carrier = ("abcdefghijklmnopqrstuvwxyz " * 100).strip()
        stego = TextSteganography()

        stego_text = stego.embed_case(carrier, STEGO_TEST_DATA)
        extracted = stego.extract_case(stego_text)

        assert extracted == STEGO_TEST_DATA


class TestStegoDetectability:
    """隐写可检测性评估。"""

    def _generate_carrier_lines(self, num_lines=500):
        """生成载体文本（按行）。"""
        lines = []
        for i in range(num_lines):
            lines.append(f"Line {i + 1}: This is a sample carrier text line for testing.")
        return "\n".join(lines)

    def _generate_carrier_spaces(self, num_spaces=500):
        """生成载体文本（按空格）。"""
        words = []
        for i in range(num_spaces):
            words.append(f"word{i}")
        return " ".join(words)

    def test_whitespace_stego_statistical_distortion(self):
        """评估空格隐写的统计失真度。"""
        carrier = self._generate_carrier_lines(500)
        stego = TextSteganography()

        stego_text = stego.embed_whitespace(carrier, STEGO_TEST_DATA)

        original_freq = char_frequency(carrier)
        stego_freq = char_frequency(stego_text)

        all_chars = set(original_freq.keys()) | set(stego_freq.keys())

        total_diff = 0
        total_original = sum(original_freq.values())
        total_stego = sum(stego_freq.values())

        for char in all_chars:
            orig_ratio = original_freq.get(char, 0) / total_original
            stego_ratio = stego_freq.get(char, 0) / total_stego
            total_diff += abs(orig_ratio - stego_ratio)

        avg_diff = total_diff / len(all_chars)

        print(f"\n空格隐写统计失真度:")
        print(f"  平均字符频率差: {avg_diff:.6f}")
        print(f"  总频率差: {total_diff:.6f}")

        assert avg_diff < 0.05

    def test_whitespace_line_endings_analysis(self):
        """分析行尾空白字符分布。"""
        carrier = self._generate_carrier_lines(500)
        stego = TextSteganography()

        stego_text = stego.embed_whitespace(carrier, STEGO_TEST_DATA)

        original_lines = carrier.rstrip().split("\n")
        stego_lines = stego_text.rstrip().split("\n")

        orig_trailing_ws = sum(
            1 for line in original_lines if line.endswith((" ", "\t"))
        )
        stego_trailing_ws = sum(
            1 for line in stego_lines if line.endswith((" ", "\t"))
        )

        print(f"\n行尾空白字符分析:")
        print(f"  原始行尾空白行数: {orig_trailing_ws}/{len(original_lines)}")
        print(f"  隐写后行尾空白行数: {stego_trailing_ws}/{len(stego_lines)}")

        assert stego_trailing_ws > orig_trailing_ws

    def test_unicode_stego_detection_difficulty(self):
        """评估零宽字符隐写的检测难度。"""
        carrier = self._generate_carrier_spaces(500)
        stego = TextSteganography()

        stego_text = stego.embed_unicode(carrier, STEGO_TEST_DATA)

        zero_width_chars = "\u200b\u200c\u200d\u2060\ufeff"
        zw_count = sum(1 for c in stego_text if c in zero_width_chars)
        total_chars = len(stego_text)
        zw_ratio = zw_count / total_chars

        print(f"\n零宽字符隐写检测难度评估:")
        print(f"  零宽字符数: {zw_count}")
        print(f"  总字符数: {total_chars}")
        print(f"  零宽字符比例: {zw_ratio*100:.3f}%")

        assert zw_ratio < 0.1

    def test_stego_capacity_whitespace(self):
        """测试空格隐写的容量。"""
        stego = TextSteganography()

        for num_lines in [100, 200, 500]:
            carrier = "\n".join([f"Line {i}" for i in range(num_lines)])
            capacity = stego.capacity(carrier, method="whitespace")

            print(f"\n空格隐写容量 ({num_lines} lines): {capacity} bytes")
            assert capacity >= 0

    def test_stego_capacity_unicode(self):
        """测试Unicode隐写的容量。"""
        stego = TextSteganography()
        carrier = self._generate_carrier_spaces(200)

        capacity = stego.capacity(carrier, method="unicode")

        print(f"\nUnicode隐写容量 (200 spaces): {capacity} bytes")
        assert capacity >= 0

    def test_stego_capacity_case(self):
        """测试大小写隐写的容量。"""
        stego = TextSteganography()
        carrier = "abcdefghijklmnopqrstuvwxyz" * 50

        capacity = stego.capacity(carrier, method="case")

        print(f"\n大小写隐写容量 (1300 letters): {capacity} bytes")
        assert capacity >= 0


class TestStegoRobustness:
    """隐写鲁棒性测试。"""

    def _generate_carrier_lines(self, num_lines=500):
        """生成载体文本（按行）。"""
        lines = []
        for i in range(num_lines):
            lines.append(f"Line {i + 1}: This is a sample carrier text line for testing.")
        return "\n".join(lines)

    def _generate_carrier_spaces(self, num_spaces=500):
        """生成载体文本（按空格）。"""
        words = []
        for i in range(num_spaces):
            words.append(f"word{i}")
        return " ".join(words)

    def test_whitespace_stego_deterministic(self):
        """测试空格隐写的确定性（相同数据产生相同结果）。"""
        carrier = self._generate_carrier_lines(500)
        stego = TextSteganography()

        stego1 = stego.embed_whitespace(carrier, STEGO_TEST_DATA)
        stego2 = stego.embed_whitespace(carrier, STEGO_TEST_DATA)

        assert stego1 == stego2

    def test_unicode_stego_deterministic(self):
        """测试Unicode隐写的确定性。"""
        carrier = self._generate_carrier_spaces(500)
        stego = TextSteganography()

        stego1 = stego.embed_unicode(carrier, STEGO_TEST_DATA)
        stego2 = stego.embed_unicode(carrier, STEGO_TEST_DATA)

        assert stego1 == stego2

    def test_whitespace_multiple_messages(self):
        """测试不同消息的空格隐写。"""
        carrier = self._generate_carrier_lines(500)
        stego = TextSteganography()

        messages = [
            b"Msg1",
            b"Msg2",
            b"Msg3",
        ]

        for msg in messages:
            stego_text = stego.embed_whitespace(carrier, msg)
            extracted = stego.extract_whitespace(stego_text)
            assert extracted == msg

    def test_unicode_multiple_messages(self):
        """测试不同消息的Unicode隐写。"""
        carrier = self._generate_carrier_spaces(500)
        stego = TextSteganography()

        messages = [
            b"Msg1",
            b"Msg2",
            b"Msg3",
        ]

        for msg in messages:
            stego_text = stego.embed_unicode(carrier, msg)
            extracted = stego.extract_unicode(stego_text)
            assert extracted == msg

    def test_empty_data_stego_whitespace(self):
        """测试空数据的空格隐写。"""
        carrier = self._generate_carrier_lines(100)
        stego = TextSteganography()

        empty_data = b""
        stego_text = stego.embed_whitespace(carrier, empty_data)
        extracted = stego.extract_whitespace(stego_text)

        assert extracted == empty_data

    def test_empty_data_stego_unicode(self):
        """测试空数据的Unicode隐写。"""
        carrier = self._generate_carrier_spaces(100)
        stego = TextSteganography()

        empty_data = b""
        stego_text = stego.embed_unicode(carrier, empty_data)
        extracted = stego.extract_unicode(stego_text)

        assert extracted == empty_data
