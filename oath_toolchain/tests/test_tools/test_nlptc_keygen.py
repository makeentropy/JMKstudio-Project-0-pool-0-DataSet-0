"""NLPTC密钥生成器单元测试。"""
import base64

import pytest

from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.tools.nlptcmodel.key_generator import NLPTCKeyGenerator
from oath_toolchain.core.crypto.primitives import AESCipher


class TestNLPTCKeyGenerator:
    """测试NLPTCKeyGenerator类。"""

    def setup_method(self):
        """每个测试前重置注册表并初始化生成器。"""
        ToolRegistry.reset_instance()
        from oath_toolchain.tools.nlptcmodel.key_generator import NLPTCKeyGenerator as NK
        ToolRegistry.reset_instance()
        ToolRegistry().register(NK)
        self.keygen = NLPTCKeyGenerator()

    def test_tool_name(self):
        """测试工具名称。"""
        assert self.keygen.name == "nlptc_keygen"

    def test_tool_description(self):
        """测试工具描述。"""
        assert self.keygen.description == "NLPTCmodel自然语言密钥生成器"

    def test_tool_registration(self):
        """测试工具注册。"""
        registry = ToolRegistry()
        assert registry.has_tool("nlptc_keygen")

    def test_tool_tags(self):
        """测试工具标签。"""
        tags = self.keygen.tags
        assert "crypto" in tags
        assert "key-generation" in tags
        assert "nlptc" in tags

    def test_tool_category(self):
        """测试工具分类。"""
        assert self.keygen.category == "crypto"

    def test_generate_key_hybrid_mode(self):
        """测试hybrid模式密钥生成。"""
        text = "This is a test text for key generation"
        key = self.keygen.generate_key(text, key_size=32, mode='hybrid')
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_key_semantic_mode(self):
        """测试semantic模式密钥生成。"""
        text = "This is a test text for key generation"
        key = self.keygen.generate_key(text, key_size=32, mode='semantic')
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_key_entropy_mode(self):
        """测试entropy模式密钥生成。"""
        text = "This is a test text for key generation"
        key = self.keygen.generate_key(text, key_size=32, mode='entropy')
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_key_deterministic(self):
        """测试密钥生成的确定性。"""
        text = "Deterministic key generation test"
        key1 = self.keygen.generate_key(text, key_size=32, mode='hybrid')
        key2 = self.keygen.generate_key(text, key_size=32, mode='hybrid')
        assert key1 == key2

    def test_generate_key_different_text(self):
        """测试不同文本生成不同密钥。"""
        text1 = "Text number one"
        text2 = "Text number two"
        key1 = self.keygen.generate_key(text1, key_size=32)
        key2 = self.keygen.generate_key(text2, key_size=32)
        assert key1 != key2

    def test_generate_key_avalanche_effect(self):
        """测试密钥生成的雪崩效应。"""
        text1 = "Hello world, this is a test"
        text2 = "Hello world, this is a tesu"
        key1 = self.keygen.generate_key(text1, key_size=32)
        key2 = self.keygen.generate_key(text2, key_size=32)
        assert key1 != key2

        diff_bits = sum(bin(b1 ^ b2).count('1') for b1, b2 in zip(key1, key2))
        total_bits = len(key1) * 8
        assert diff_bits > total_bits * 0.2

    def test_generate_key_different_sizes(self):
        """测试不同密钥长度生成。"""
        text = "Test text"
        for size in [16, 24, 32, 48, 64]:
            key = self.keygen.generate_key(text, key_size=size)
            assert len(key) == size

    def test_generate_key_with_salt(self):
        """测试带盐值的密钥生成。"""
        text = "Test text"
        salt = b"custom_salt_value_16"
        key1 = self.keygen.generate_key(text, key_size=32, salt=salt)
        key2 = self.keygen.generate_key(text, key_size=32, salt=b"different_salt")
        assert key1 != key2

    def test_generate_key_chinese_text(self):
        """测试中文文本密钥生成。"""
        text = "这是一段用于生成密钥的中文文本"
        key = self.keygen.generate_key(text, key_size=32)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_key_japanese_text(self):
        """测试日文文本密钥生成。"""
        text = "これは日本語のテキストです"
        key = self.keygen.generate_key(text, key_size=32)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_key_invalid_text_type(self):
        """测试无效文本类型。"""
        with pytest.raises(TypeError):
            self.keygen.generate_key(12345)

    def test_generate_key_empty_text(self):
        """测试空文本。"""
        with pytest.raises(ValueError):
            self.keygen.generate_key("")

    def test_generate_key_invalid_key_size(self):
        """测试无效密钥长度。"""
        with pytest.raises(ValueError):
            self.keygen.generate_key("test", key_size=0)

    def test_generate_key_invalid_mode(self):
        """测试无效模式。"""
        with pytest.raises(ValueError):
            self.keygen.generate_key("test", mode='invalid')

    def test_generate_key_invalid_iterations(self):
        """测试无效迭代次数。"""
        with pytest.raises(ValueError):
            self.keygen.generate_key("test", iterations=0)

    def test_generate_from_passphrase(self):
        """测试从口令生成密钥。"""
        passphrase = "my secret passphrase"
        key, salt = self.keygen.generate_from_passphrase(passphrase)
        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)
        assert len(key) == 32
        assert len(salt) == 16

    def test_generate_from_passphrase_with_salt(self):
        """测试带盐值的口令密钥生成。"""
        passphrase = "my secret passphrase"
        salt = b"testsalt16bytes!"
        key, returned_salt = self.keygen.generate_from_passphrase(passphrase, salt=salt)
        assert returned_salt == salt
        assert len(key) == 32

    def test_generate_from_passphrase_deterministic(self):
        """测试口令密钥生成的确定性。"""
        passphrase = "test passphrase"
        salt = b"testsalt16bytes!"
        key1, _ = self.keygen.generate_from_passphrase(passphrase, salt=salt)
        key2, _ = self.keygen.generate_from_passphrase(passphrase, salt=salt)
        assert key1 == key2

    def test_generate_from_passphrase_invalid_type(self):
        """测试无效口令类型。"""
        with pytest.raises(TypeError):
            self.keygen.generate_from_passphrase(123)

    def test_generate_from_passphrase_empty(self):
        """测试空口令。"""
        with pytest.raises(ValueError):
            self.keygen.generate_from_passphrase("")

    def test_verify_key_correct(self):
        """测试正确的密钥验证。"""
        text = "Verification test text"
        key = self.keygen.generate_key(text, key_size=32, mode='hybrid')
        assert self.keygen.verify_key(text, key, mode='hybrid') is True

    def test_verify_key_wrong_text(self):
        """测试错误文本的密钥验证。"""
        text1 = "Correct text"
        text2 = "Wrong text"
        key = self.keygen.generate_key(text1, key_size=32)
        assert self.keygen.verify_key(text2, key) is False

    def test_verify_key_wrong_mode(self):
        """测试错误模式的密钥验证。"""
        text = "Test text"
        key = self.keygen.generate_key(text, key_size=32, mode='semantic')
        assert self.keygen.verify_key(text, key, mode='entropy') is False

    def test_key_usable_for_aes256(self):
        """测试生成的密钥可用于AES-256加密。"""
        text = "AES-256 test key"
        key = self.keygen.generate_key(text, key_size=32)

        plaintext = b"Secret message for AES-256 encryption"
        ciphertext, nonce, tag = AESCipher.encrypt(plaintext, key)
        decrypted = AESCipher.decrypt(ciphertext, key, nonce, tag)

        assert decrypted == plaintext

    def test_execute_success(self):
        """测试execute方法成功执行。"""
        params = {
            "text": "Test text for execute",
            "key_size": 32,
            "mode": "hybrid",
        }

        result = self.keygen.execute(params)
        assert result["success"] is True
        assert "key" in result
        assert "key_hex" in result
        assert "features" in result
        assert "strength" in result
        assert isinstance(result["key"], str)
        assert isinstance(result["key_hex"], str)

        key_bytes = base64.b64decode(result["key"])
        assert len(key_bytes) == 32

    def test_execute_with_salt(self):
        """测试带盐值的execute方法。"""
        salt = b"test_salt_16byte"
        params = {
            "text": "Test text",
            "salt": base64.b64encode(salt).decode("utf-8"),
        }

        result = self.keygen.execute(params)
        assert result["success"] is True

    def test_execute_missing_text(self):
        """测试缺少text参数的execute。"""
        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.keygen.execute({})

    def test_execute_invalid_key_size_type(self):
        """测试无效key_size类型。"""
        from oath_toolchain.core.exceptions import ValidationError

        params = {
            "text": "test",
            "key_size": "not_an_int",
        }

        with pytest.raises(ValidationError):
            self.keygen.execute(params)

    def test_validate_params_success(self):
        """测试参数验证成功。"""
        params = {
            "text": "test text",
            "key_size": 32,
            "mode": "hybrid",
            "iterations": 100000,
        }

        assert self.keygen.validate_params(params) is True

    def test_validate_params_missing_text(self):
        """测试缺少text参数验证。"""
        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.keygen.validate_params({})

    def test_validate_params_invalid_text_type(self):
        """测试无效text类型验证。"""
        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.keygen.validate_params({"text": 123})

    def test_validate_params_empty_text(self):
        """测试空text验证。"""
        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.keygen.validate_params({"text": ""})

    def test_validate_params_invalid_mode(self):
        """测试无效mode验证。"""
        from oath_toolchain.core.exceptions import ValidationError

        params = {"text": "test", "mode": "invalid"}
        with pytest.raises(ValidationError):
            self.keygen.validate_params(params)

    def test_validate_params_invalid_salt(self):
        """测试无效salt验证。"""
        from oath_toolchain.core.exceptions import ValidationError

        params = {"text": "test", "salt": "not_valid_base64!!!"}
        with pytest.raises(ValidationError):
            self.keygen.validate_params(params)
