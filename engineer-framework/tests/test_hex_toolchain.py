"""hex_toolchain 模块单元测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from src.hex_toolchain import (
    base16_encode, base16_decode,
    base32_encode, base32_decode,
    base64_encode, base64_decode,
    xor_bytes, xor_hex,
    BoostContainer
)


class TestBase16(unittest.TestCase):
    """Base16 编码解码测试"""

    def test_encode_roundtrip(self):
        """测试 base16 编码后解码能够还原原始数据"""
        original = b'hello world'
        encoded = base16_encode(original)
        decoded = base16_decode(encoded)
        self.assertEqual(decoded, original)

    def test_encode_uppercase(self):
        """测试 base16 编码结果为大写"""
        result = base16_encode(b'test')
        self.assertEqual(result, '74657374')

    def test_decode_uppercase(self):
        """测试 base16 解码支持大写输入"""
        result = base16_decode('54455354')
        self.assertEqual(result, b'TEST')

    def test_empty_bytes(self):
        """测试空字节的编码解码"""
        original = b''
        encoded = base16_encode(original)
        self.assertEqual(encoded, '')
        decoded = base16_decode(encoded)
        self.assertEqual(decoded, original)

    def test_special_characters(self):
        """测试特殊字符的编码解码"""
        original = b'\x00\xff\x7f\x80'
        encoded = base16_encode(original)
        self.assertEqual(encoded, '00FF7F80')
        decoded = base16_decode(encoded)
        self.assertEqual(decoded, original)


class TestBase32(unittest.TestCase):
    """Base32 编码解码测试"""

    def test_encode_roundtrip(self):
        """测试 base32 编码后解码能够还原原始数据"""
        original = b'hello world'
        encoded = base32_encode(original)
        decoded = base32_decode(encoded)
        self.assertEqual(decoded, original)

    def test_encode_uppercase(self):
        """测试 base32 编码结果为大写"""
        result = base32_encode(b'test')
        self.assertEqual(result, 'ORSXG5A=')

    def test_empty_bytes(self):
        """测试空字节的编码解码"""
        original = b''
        encoded = base32_encode(original)
        decoded = base32_decode(encoded)
        self.assertEqual(decoded, original)

    def test_longer_data(self):
        """测试较长数据的编码解码"""
        original = b'this is a longer string for testing base32 encoding'
        encoded = base32_encode(original)
        decoded = base32_decode(encoded)
        self.assertEqual(decoded, original)


class TestBase64(unittest.TestCase):
    """Base64 编码解码测试"""

    def test_encode_roundtrip(self):
        """测试 base64 编码后解码能够还原原始数据"""
        original = b'hello world'
        encoded = base64_encode(original)
        decoded = base64_decode(encoded)
        self.assertEqual(decoded, original)

    def test_known_encoding(self):
        """测试已知的 base64 编码结果"""
        result = base64_encode(b'test')
        self.assertEqual(result, 'dGVzdA==')

    def test_empty_bytes(self):
        """测试空字节的编码解码"""
        original = b''
        encoded = base64_encode(original)
        decoded = base64_decode(encoded)
        self.assertEqual(decoded, original)

    def test_longer_data(self):
        """测试较长数据的编码解码"""
        original = b'this is a longer string for testing base64 encoding and decoding'
        encoded = base64_encode(original)
        decoded = base64_decode(encoded)
        self.assertEqual(decoded, original)

    def test_binary_data(self):
        """测试二进制数据的编码解码"""
        original = b'\x00\xff\x7f\x80\xfe\x01'
        encoded = base64_encode(original)
        decoded = base64_decode(encoded)
        self.assertEqual(decoded, original)


class TestXorBytes(unittest.TestCase):
    """xor_bytes 函数测试"""

    def test_equal_length(self):
        """测试等长字节数组的 XOR 运算"""
        data1 = b'\x01\x02\x03\x04'
        data2 = b'\x0f\x0e\x0d\x0c'
        result = xor_bytes(data1, data2)
        expected = b'\x0e\x0c\x0e\x08'
        self.assertEqual(result, expected)

    def test_unequal_length_data2_repeats(self):
        """测试不等长时 data2 会循环重复"""
        data1 = b'hello'
        data2 = b'x'
        result = xor_bytes(data1, data2)
        expected = b'\x10\x1d\x14\x14\x17'
        self.assertEqual(result, expected)

    def test_empty_data2(self):
        """测试空 data2 时返回原始 data1"""
        data1 = b'\x01\x02\x03'
        data2 = b''
        result = xor_bytes(data1, data2)
        self.assertEqual(result, data1)

    def test_data2_shorter_than_data1(self):
        """测试 data2 比 data1 短的情况"""
        data1 = b'hello world'
        data2 = b'xy'
        result = xor_bytes(data1, data2)
        # h^x, e^y, l^x, l^y, o^x, ' '^y, w^x, o^y, r^x, l^y, d^x
        self.assertEqual(len(result), len(data1))

    def test_same_data(self):
        """测试相同数据的 XOR 结果为全零"""
        data = b'\x01\x02\x03\x04'
        result = xor_bytes(data, data)
        self.assertEqual(result, b'\x00\x00\x00\x00')


class TestXorHex(unittest.TestCase):
    """xor_hex 函数测试"""

    def test_equal_length(self):
        """测试等长十六进制字符串的 XOR 运算"""
        hex1 = '48656c6c6f'  # 'Hello'
        hex2 = '0102030405'
        result = xor_hex(hex1, hex2)
        expected = '49676F686A'
        self.assertEqual(result, expected)

    def test_unequal_length(self):
        """测试不等长十六进制字符串的 XOR 运算"""
        hex1 = '48656c6c6f'  # 'Hello'
        hex2 = '01'
        result = xor_hex(hex1, hex2)
        # 48^01=49, 65^01=64, 6c^01=6d, 6c^01=6d, 6f^01=6e
        self.assertEqual(result, '49646D6D6E')

    def test_empty_hex2(self):
        """测试空 hex2 时返回原始 hex1 的 XOR 结果（全零）"""
        hex1 = '48656c6c6f'
        hex2 = ''
        result = xor_hex(hex1, hex2)
        self.assertEqual(result, hex1.upper())

    def test_lowercase_input(self):
        """测试支持小写输入"""
        hex1 = '48656c6c6f'
        hex2 = '0f0e0d0c0b'
        result = xor_hex(hex1, hex2)
        self.assertEqual(result, '476B616064')


class TestBoostContainer(unittest.TestCase):
    """BoostContainer 类测试"""

    def test_initialization(self):
        """测试 BoostContainer 初始化"""
        data = b'test data'
        container = BoostContainer(data)
        self.assertEqual(bytes(container), data)

    def test_to_hex(self):
        """测试转换为十六进制字符串"""
        data = b'\x48\x65\x6c\x6c\x6f'
        container = BoostContainer(data)
        self.assertEqual(container.to_hex(), '48656C6C6F')

    def test_to_base64(self):
        """测试转换为 Base64 字符串"""
        data = b'hello'
        container = BoostContainer(data)
        self.assertEqual(container.to_base64(), 'aGVsbG8=')

    def test_to_base32(self):
        """测试转换为 Base32 字符串"""
        data = b'hello'
        container = BoostContainer(data)
        self.assertEqual(container.to_base32(), 'NBSWY3DP')

    def test_to_base16(self):
        """测试转换为 Base16 字符串"""
        data = b'hello'
        container = BoostContainer(data)
        self.assertEqual(container.to_base16(), '68656C6C6F')

    def test_xor_with_bytes(self):
        """测试 BoostContainer 与 bytes 的 XOR 运算"""
        container1 = BoostContainer(b'\x01\x02\x03\x04')
        container2 = b'\x0f\x0e\x0d\x0c'
        result = container1 ^ container2
        self.assertEqual(bytes(result), b'\x0e\x0c\x0e\x08')

    def test_xor_with_boost_container(self):
        """测试两个 BoostContainer 的 XOR 运算"""
        container1 = BoostContainer(b'\x01\x02\x03\x04')
        container2 = BoostContainer(b'\x0f\x0e\x0d\x0c')
        result = container1 ^ container2
        self.assertEqual(bytes(result), b'\x0e\x0c\x0e\x08')

    def test_xor_invalid_type(self):
        """测试 XOR 运算对无效类型抛出异常"""
        container = BoostContainer(b'\x01\x02\x03\x04')
        with self.assertRaises(TypeError):
            container ^ "invalid"

    def test_rxor(self):
        """测试右侧 XOR 运算 (bytes ^ BoostContainer)"""
        container = BoostContainer(b'\x0f\x0e\x0d\x0c')
        result = b'\x01\x02\x03\x04' ^ container
        self.assertEqual(bytes(result), b'\x0e\x0c\x0e\x08')

    def test_bytes_conversion(self):
        """测试 bytes 转换"""
        data = b'test data'
        container = BoostContainer(data)
        self.assertEqual(bytes(container), data)


if __name__ == '__main__':
    unittest.main()
