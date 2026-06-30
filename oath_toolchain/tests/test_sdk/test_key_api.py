"""密钥API单元测试。"""
import pytest
import base64

from oath_toolchain.sdk import OathSDK
from oath_toolchain.core.registry import ToolRegistry


class TestKeyAPI:
    """测试KeyAPI类。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.sdk = OathSDK()

    def test_generate_aes_key_256(self):
        """测试生成256位AES密钥。"""
        key = self.sdk.keys.generate_aes_key(256)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_aes_key_128(self):
        """测试生成128位AES密钥。"""
        key = self.sdk.keys.generate_aes_key(128)
        assert isinstance(key, bytes)
        assert len(key) == 16

    def test_generate_aes_key_192(self):
        """测试生成192位AES密钥。"""
        key = self.sdk.keys.generate_aes_key(192)
        assert isinstance(key, bytes)
        assert len(key) == 24

    def test_generate_aes_key_invalid_size(self):
        """测试生成无效大小的AES密钥。"""
        with pytest.raises(ValueError):
            self.sdk.keys.generate_aes_key(100)

    def test_generate_rsa_key(self):
        """测试生成RSA密钥对。"""
        private_key, public_key = self.sdk.keys.generate_rsa_key(2048)
        assert isinstance(private_key, bytes)
        assert isinstance(public_key, bytes)
        assert b"PRIVATE KEY" in private_key
        assert b"PUBLIC KEY" in public_key

    def test_generate_rsa_key_4096(self):
        """测试生成4096位RSA密钥对。"""
        private_key, public_key = self.sdk.keys.generate_rsa_key(4096)
        assert isinstance(private_key, bytes)
        assert isinstance(public_key, bytes)
        assert len(private_key) > len(public_key)

    def test_generate_nlp_key(self):
        """测试生成NLP密钥。"""
        text = "这是一段用于生成密钥的测试文本，包含足够的语义信息。"
        key = self.sdk.keys.generate_nlp_key(text, mode='hybrid', key_length=32)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_nlp_key_semantic_mode(self):
        """测试semantic模式生成NLP密钥。"""
        text = "Natural language processing for key generation."
        key = self.sdk.keys.generate_nlp_key(text, mode='semantic', key_length=16)
        assert isinstance(key, bytes)
        assert len(key) == 16

    def test_generate_nlp_key_entropy_mode(self):
        """测试entropy模式生成NLP密钥。"""
        text = "Entropy based key generation test text."
        key = self.sdk.keys.generate_nlp_key(text, mode='entropy', key_length=24)
        assert isinstance(key, bytes)
        assert len(key) == 24

    def test_generate_nlp_key_deterministic(self):
        """测试NLP密钥生成的确定性。"""
        text = "相同的文本应该生成相同的密钥。"
        key1 = self.sdk.keys.generate_nlp_key(text, mode='hybrid', key_length=32)
        key2 = self.sdk.keys.generate_nlp_key(text, mode='hybrid', key_length=32)
        assert key1 == key2

    def test_generate_karmaca_key(self):
        """测试生成KARMACA密钥。"""
        seed = b"test_seed_for_karmaca_key"
        key = self.sdk.keys.generate_karmaca_key(seed, dimensions=3)
        assert isinstance(key, bytes)
        assert key == seed

    def test_generate_karmaca_key_no_seed(self):
        """测试不提供种子生成KARMACA密钥。"""
        key = self.sdk.keys.generate_karmaca_key(dimensions=3)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_combined_key(self):
        """测试生成组合密钥。"""
        sources = [
            {"type": "bytes", "value": b"source1", "weight": 1},
            {"type": "text", "value": "source2", "weight": 2},
            {"type": "password", "value": "password123", "weight": 1},
        ]
        key = self.sdk.keys.generate_combined_key(sources, key_length=32)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_combined_key_deterministic(self):
        """测试组合密钥生成的确定性。"""
        sources = [
            {"type": "bytes", "value": b"test_source", "weight": 1},
        ]
        key1 = self.sdk.keys.generate_combined_key(sources, key_length=32)
        key2 = self.sdk.keys.generate_combined_key(sources, key_length=32)
        assert key1 == key2

    def test_derive_key(self):
        """测试从密码派生密钥。"""
        password = "my_secret_password"
        salt = b"test_salt_value_123"
        key = self.sdk.keys.derive_key(password, salt, iterations=1000)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_derive_key_no_salt(self):
        """测试不提供盐值派生密钥。"""
        password = "my_secret_password"
        key = self.sdk.keys.derive_key(password, iterations=1000)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_derive_key_deterministic(self):
        """测试密钥派生的确定性。"""
        password = "test_password"
        salt = b"fixed_salt"
        key1 = self.sdk.keys.derive_key(password, salt, iterations=1000)
        key2 = self.sdk.keys.derive_key(password, salt, iterations=1000)
        assert key1 == key2

    def test_key_to_base64(self):
        """测试密钥转换为Base64。"""
        key = b"\x01\x02\x03\x04\x05"
        b64 = self.sdk.keys.key_to_base64(key)
        assert isinstance(b64, str)
        assert base64.b64decode(b64) == key

    def test_key_from_base64(self):
        """测试从Base64解析密钥。"""
        original = b"\x01\x02\x03\x04\x05"
        b64 = base64.b64encode(original).decode("utf-8")
        key = self.sdk.keys.key_from_base64(b64)
        assert key == original

    def test_key_base64_roundtrip(self):
        """测试密钥Base64往返转换。"""
        key = self.sdk.keys.generate_aes_key(256)
        b64 = self.sdk.keys.key_to_base64(key)
        restored = self.sdk.keys.key_from_base64(b64)
        assert restored == key

    def test_key_from_base64_invalid(self):
        """测试无效的Base64字符串。"""
        with pytest.raises(ValueError):
            self.sdk.keys.key_from_base64("!!!invalid!!!")

    def test_assess_key_strength_strong(self):
        """测试强密钥强度评估。"""
        import os
        strong_key = os.urandom(32)
        result = self.sdk.keys.assess_key_strength(strong_key)
        assert isinstance(result, dict)
        assert "score" in result
        assert "entropy" in result
        assert "length" in result
        assert "strength" in result
        assert result["length"] == 32

    def test_assess_key_strength_weak(self):
        """测试弱密钥强度评估。"""
        weak_key = b"aaaaa"
        result = self.sdk.keys.assess_key_strength(weak_key)
        assert isinstance(result, dict)
        assert "score" in result
        assert result["length"] == 5

    def test_assess_key_strength_empty(self):
        """测试空密钥强度评估。"""
        result = self.sdk.keys.assess_key_strength(b"")
        assert isinstance(result, dict)
        assert result["length"] == 0
