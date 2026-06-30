"""XOR隐写单元测试。"""
import pytest

from oath_toolchain.tools.steganography.xor_stego import XORSteganography


class TestXORSteganography:
    """测试XORSteganography类。"""

    def setup_method(self):
        """每个测试前初始化。"""
        self.stego = XORSteganography()

    def test_init(self):
        """测试初始化。"""
        assert self.stego.LENGTH_PREFIX_SIZE == 4

    def test_embed_basic(self):
        """测试基础嵌入。"""
        secret = b"Hello"
        carrier = b"\x00" * 10
        result = self.stego.embed(secret, carrier)
        assert len(result) == len(carrier)
        assert result[:5] == secret

    def test_embed_and_extract_basic(self):
        """测试基础嵌入和提取。"""
        secret = b"Hello, XOR!"
        carrier = b"A" * 50
        stego_data = self.stego.embed(secret, carrier)
        extracted = self.stego.extract(stego_data, len(secret))
        assert extracted == secret

    def test_embed_with_key(self):
        """测试带密钥的嵌入和提取。"""
        secret = b"Secret Data"
        carrier = b"B" * 50
        key = b"mykey123"
        stego_data = self.stego.embed(secret, carrier, key)
        extracted = self.stego.extract(stego_data, len(secret), key)
        assert extracted == secret

    def test_embed_with_key_different_from_basic(self):
        """测试密钥模式与基础模式结果不同。"""
        secret = b"Test"
        carrier = b"\x00" * 20
        key = b"key"
        basic_result = self.stego.embed(secret, carrier)
        key_result = self.stego.embed(secret, carrier, key)
        assert basic_result != key_result

    def test_embed_with_length(self):
        """测试带长度前缀的嵌入。"""
        secret = b"Length Prefix Test"
        carrier = b"X" * 100
        stego_data = self.stego.embed_with_length(secret, carrier)
        assert len(stego_data) == len(carrier)

    def test_extract_with_length(self):
        """测试带长度前缀的提取。"""
        secret = b"Auto Length Test Data"
        carrier = b"Y" * 200
        stego_data = self.stego.embed_with_length(secret, carrier)
        extracted = self.stego.extract_with_length(stego_data)
        assert extracted == secret

    def test_embed_with_length_and_key(self):
        """测试带长度前缀和密钥的嵌入提取。"""
        secret = b"Encrypted Length Prefix"
        carrier = b"Z" * 200
        key = b"secretkey"
        stego_data = self.stego.embed_with_length(secret, carrier, key)
        extracted = self.stego.extract_with_length(stego_data, key)
        assert extracted == secret

    def test_capacity(self):
        """测试容量计算。"""
        assert self.stego.capacity(100) == 96
        assert self.stego.capacity(4) == 0
        assert self.stego.capacity(5) == 1
        assert self.stego.capacity(0) == 0

    def test_embed_secret_too_long(self):
        """测试秘密数据过长。"""
        secret = b"A" * 100
        carrier = b"B" * 50
        with pytest.raises(ValueError):
            self.stego.embed(secret, carrier)

    def test_embed_with_length_too_long(self):
        """测试带长度前缀时数据过长。"""
        secret = b"A" * 100
        carrier = b"B" * 50
        with pytest.raises(ValueError):
            self.stego.embed_with_length(secret, carrier)

    def test_extract_invalid_length(self):
        """测试提取时无效长度。"""
        stego_data = b"test"
        with pytest.raises(ValueError):
            self.stego.extract(stego_data, -1)

    def test_extract_length_too_large(self):
        """测试提取长度超过数据长度。"""
        stego_data = b"test"
        with pytest.raises(ValueError):
            self.stego.extract(stego_data, 10)

    def test_extract_with_length_insufficient_data(self):
        """测试带长度提取时数据不足。"""
        stego_data = b"\x00\x00"
        with pytest.raises(ValueError):
            self.stego.extract_with_length(stego_data)

    def test_extract_with_length_declared_too_large(self):
        """测试声明的长度过大。"""
        stego_data = b"\x00\x00\x01\x00" + b"test"
        with pytest.raises(ValueError):
            self.stego.extract_with_length(stego_data)

    def test_embed_invalid_secret_type(self):
        """测试无效的秘密数据类型。"""
        with pytest.raises(TypeError):
            self.stego.embed("not bytes", b"carrier")

    def test_embed_invalid_carrier_type(self):
        """测试无效的载体数据类型。"""
        with pytest.raises(TypeError):
            self.stego.embed(b"secret", "not bytes")

    def test_capacity_invalid_length(self):
        """测试无效的容量长度参数。"""
        with pytest.raises(ValueError):
            self.stego.capacity(-1)

    def test_embed_empty_secret(self):
        """测试嵌入空秘密数据。"""
        secret = b""
        carrier = b"test"
        result = self.stego.embed(secret, carrier)
        assert result == carrier

    def test_key_stream_generation(self):
        """测试密钥流生成。"""
        key = b"testkey"
        stream1 = self.stego._generate_key_stream(key, 10)
        stream2 = self.stego._generate_key_stream(key, 10)
        assert stream1 == stream2
        assert len(stream1) == 10

    def test_key_stream_empty_key(self):
        """测试空密钥生成密钥流。"""
        with pytest.raises(ValueError):
            self.stego._generate_key_stream(b"", 10)
