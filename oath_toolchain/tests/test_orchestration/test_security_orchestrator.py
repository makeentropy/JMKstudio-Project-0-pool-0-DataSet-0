"""安全编排器单元测试。"""
import base64
import pytest

from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.orchestration import QiankunEngine, SecurityOrchestrator
from oath_toolchain.core.exceptions import EncryptionError, ValidationError


class TestSecurityOrchestrator:
    """测试安全编排器。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.engine = QiankunEngine()
        self.orchestrator = SecurityOrchestrator(self.engine)

    def test_init(self):
        """测试初始化。"""
        assert self.orchestrator.engine is self.engine
        assert isinstance(self.orchestrator._profiles, dict)

    def test_encrypt_with_multiple_layers_aes(self):
        """测试AES单层加密。"""
        data = b"Hello, Qiankun!"
        key = b"0123456789abcdef0123456789abcdef"
        layers = [
            {
                "type": "aes",
                "params": {"key": base64.b64encode(key).decode("utf-8")},
            },
        ]
        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        assert encrypted is not None
        assert isinstance(encrypted, bytes)
        assert encrypted != data

    def test_encrypt_decrypt_aes_roundtrip(self):
        """测试AES加密解密往返。"""
        data = b"Test data for AES roundtrip"
        key = b"0123456789abcdef0123456789abcdef"
        key_b64 = base64.b64encode(key).decode("utf-8")
        layers = [
            {"type": "aes", "params": {"key": key_b64}},
        ]

        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        decrypted = self.orchestrator.decrypt_with_multiple_layers(encrypted, layers)

        assert decrypted == data

    def test_encrypt_with_multiple_layers_geometric(self):
        """测试几何加密层。"""
        data = b"Geometric encryption test"
        layers = [
            {"type": "geometric", "params": {"dimensions": 4}},
        ]
        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        assert encrypted is not None
        assert isinstance(encrypted, bytes)

    def test_encrypt_decrypt_geometric_roundtrip(self):
        """测试几何加密解密往返。"""
        data = b"Geometric roundtrip test data"
        layers = [
            {"type": "geometric", "params": {"dimensions": 4, "salt": "test_salt"}},
        ]

        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        decrypted = self.orchestrator.decrypt_with_multiple_layers(encrypted, layers)

        assert decrypted == data

    def test_encrypt_with_multiple_layers_karmaca(self):
        """测试KARMACA加密层。"""
        data = b"Karmaca encryption test"
        layers = [
            {"type": "karmaca", "params": {"key": "test_key"}},
        ]
        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        assert encrypted is not None

    def test_encrypt_decrypt_karmaca_roundtrip(self):
        """测试KARMACA加密解密往返。"""
        data = b"Karmaca roundtrip test"
        layers = [
            {"type": "karmaca", "params": {"key": "my_secret_key"}},
        ]

        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        decrypted = self.orchestrator.decrypt_with_multiple_layers(encrypted, layers)

        assert decrypted == data

    def test_encrypt_with_multiple_layers_xor_stego(self):
        """测试XOR隐写加密层。"""
        data = b"XOR steganography test"
        layers = [
            {"type": "xor_stego", "params": {"key": "stego_key"}},
        ]
        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        assert encrypted is not None

    def test_encrypt_decrypt_xor_stego_roundtrip(self):
        """测试XOR隐写加密解密往返。"""
        data = b"XOR stego roundtrip test data"
        layers = [
            {"type": "xor_stego", "params": {"key": "stego_key_123"}},
        ]

        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        decrypted = self.orchestrator.decrypt_with_multiple_layers(encrypted, layers)

        assert decrypted == data

    def test_encrypt_multiple_layers(self):
        """测试多层加密。"""
        data = b"Multi-layer encryption test"
        key = b"0123456789abcdef0123456789abcdef"
        layers = [
            {"type": "karmaca", "params": {"key": "layer1"}},
            {"type": "aes", "params": {"key": base64.b64encode(key).decode("utf-8")}},
            {"type": "geometric", "params": {"dimensions": 3}},
        ]

        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        decrypted = self.orchestrator.decrypt_with_multiple_layers(encrypted, layers)

        assert decrypted == data

    def test_encrypt_empty_layers(self):
        """测试空加密层列表。"""
        with pytest.raises(ValidationError, match="不能为空"):
            self.orchestrator.encrypt_with_multiple_layers(b"data", [])

    def test_encrypt_invalid_layer_type(self):
        """测试无效加密层类型。"""
        with pytest.raises(ValidationError, match="不支持的加密层类型"):
            self.orchestrator.encrypt_with_multiple_layers(
                b"data",
                [{"type": "invalid_type"}],
            )

    def test_encrypt_non_bytes_data(self):
        """测试非字节数据加密。"""
        with pytest.raises(ValidationError, match="必须是bytes类型"):
            self.orchestrator.encrypt_with_multiple_layers("not bytes", [{"type": "aes"}])

    def test_generate_secure_key(self):
        """测试生成安全密钥。"""
        config = {
            "base_text": "这是一个测试文本",
            "salt": b"test_salt",
            "length": 32,
            "use_nlp": True,
            "use_geometric": True,
        }
        key = self.orchestrator.generate_secure_key(config)
        assert key is not None
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_secure_key_deterministic(self):
        """测试密钥生成的确定性。"""
        config = {
            "base_text": "相同的文本",
            "salt": b"same_salt",
            "length": 16,
        }
        key1 = self.orchestrator.generate_secure_key(config)
        key2 = self.orchestrator.generate_secure_key(config)
        assert key1 == key2

    def test_generate_secure_key_different_salt(self):
        """测试不同盐值生成不同密钥。"""
        config1 = {"base_text": "text", "salt": b"salt1", "length": 16}
        config2 = {"base_text": "text", "salt": b"salt2", "length": 16}
        key1 = self.orchestrator.generate_secure_key(config1)
        key2 = self.orchestrator.generate_secure_key(config2)
        assert key1 != key2

    def test_sign_with_multiple_keys_hmac(self):
        """测试HMAC多密钥签名。"""
        data = b"Data to sign"
        signers = [
            {
                "id": "signer1",
                "type": "hmac",
                "private_key": "secret_key_1",
            },
            {
                "id": "signer2",
                "type": "hmac",
                "private_key": "secret_key_2",
            },
        ]
        result = self.orchestrator.sign_with_multiple_keys(data, signers)
        assert result["signer_count"] == 2
        assert "signer1" in result["signatures"]
        assert "signer2" in result["signatures"]
        assert "data_hash" in result

    def test_verify_multiple_signatures_hmac(self):
        """测试HMAC多签名验证。"""
        data = b"Verify this data"
        key1 = b"verify_key_1"
        key2 = b"verify_key_2"

        signers = [
            {"id": "s1", "type": "hmac", "private_key": key1},
            {"id": "s2", "type": "hmac", "private_key": key2},
        ]
        sig_result = self.orchestrator.sign_with_multiple_keys(data, signers)

        for signer_id in ["s1", "s2"]:
            sig_result["signatures"][signer_id]["secret_key"] = (
                key1 if signer_id == "s1" else key2
            )

        all_verified, verified_list = self.orchestrator.verify_multiple_signatures(
            data, sig_result
        )
        assert "s1" in verified_list
        assert "s2" in verified_list

    def test_sign_empty_signers(self):
        """测试空签名者列表。"""
        with pytest.raises(ValidationError, match="签名者列表不能为空"):
            self.orchestrator.sign_with_multiple_keys(b"data", [])

    def test_sign_non_bytes_data(self):
        """测试非字节数据签名。"""
        with pytest.raises(ValidationError, match="必须是bytes类型"):
            self.orchestrator.sign_with_multiple_keys(
                "not bytes",
                [{"id": "s1", "type": "hmac", "private_key": "k"}],
            )

    def test_create_security_profile(self):
        """测试创建安全配置文件。"""
        config = {
            "encryption_layers": [{"type": "aes"}],
            "key_config": {"base_text": "test"},
            "description": "测试配置文件",
        }
        result = self.orchestrator.create_security_profile("test_profile", config)
        assert result["success"] is True
        assert result["profile_name"] == "test_profile"
        assert "test_profile" in self.orchestrator._profiles

    def test_create_security_profile_empty_name(self):
        """测试创建空名称的配置文件。"""
        with pytest.raises(ValidationError, match="名称不能为空"):
            self.orchestrator.create_security_profile("", {})

    def test_apply_security_profile(self):
        """测试应用安全配置文件。"""
        profile_config = {
            "encryption_layers": [
                {"type": "karmaca", "params": {"key": "profile_key"}},
            ],
            "key_config": {"base_text": "profile_text", "length": 16},
        }
        self.orchestrator.create_security_profile("apply_test", profile_config)

        data = b"Profile application test"
        result = self.orchestrator.apply_security_profile("apply_test", data)

        assert result["success"] is True
        assert result["profile"] == "apply_test"
        assert "encrypted_data" in result
        assert "generated_key" in result

    def test_apply_security_profile_not_found(self):
        """测试应用不存在的配置文件。"""
        with pytest.raises(ValidationError, match="不存在"):
            self.orchestrator.apply_security_profile("nonexistent", b"data")

    def test_get_security_report(self):
        """测试获取安全报告。"""
        report = self.orchestrator.get_security_report()
        assert "profiles" in report
        assert "profile_count" in report
        assert "supported_layers" in report
        assert "supported_signatures" in report
        assert "aes" in report["supported_layers"]
        assert "rsa" in report["supported_layers"]

    def test_decrypt_invalid_format(self):
        """测试解密无效格式数据。"""
        layers = [{"type": "aes"}]
        with pytest.raises(EncryptionError, match="格式无效"):
            self.orchestrator.decrypt_with_multiple_layers(b"invalid_data", layers)

    def test_rsa_encrypt_decrypt(self):
        """测试RSA加密解密。"""
        data = b"Short RSA test"
        layers = [{"type": "rsa", "params": {}}]

        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        assert encrypted is not None
        assert isinstance(encrypted, bytes)

    def test_decrypt_empty_layers(self):
        """测试空层解密。"""
        with pytest.raises(ValidationError, match="不能为空"):
            self.orchestrator.decrypt_with_multiple_layers(b"data", [])

    def test_generate_secure_key_without_nlp(self):
        """测试不使用NLP的密钥生成。"""
        config = {
            "base_text": "test",
            "salt": b"salt",
            "length": 16,
            "use_nlp": False,
            "use_geometric": True,
        }
        key = self.orchestrator.generate_secure_key(config)
        assert len(key) == 16

    def test_generate_secure_key_without_geometric(self):
        """测试不使用几何哈希的密钥生成。"""
        config = {
            "base_text": "test",
            "salt": b"salt",
            "length": 24,
            "use_nlp": True,
            "use_geometric": False,
        }
        key = self.orchestrator.generate_secure_key(config)
        assert len(key) == 24

    def test_generate_secure_key_neither(self):
        """测试不使用NLP和几何的密钥生成。"""
        config = {
            "base_text": "test",
            "salt": b"salt",
            "length": 8,
            "use_nlp": False,
            "use_geometric": False,
        }
        key = self.orchestrator.generate_secure_key(config)
        assert len(key) == 8

    def test_generate_secure_key_string_salt(self):
        """测试字符串盐值的密钥生成。"""
        config = {
            "base_text": "test",
            "salt": "string_salt",
            "length": 32,
        }
        key = self.orchestrator.generate_secure_key(config)
        assert len(key) == 32

    def test_sign_with_rsa(self):
        """测试RSA签名。"""
        from oath_toolchain.core.crypto.primitives import RSACipher

        private_key, public_key = RSACipher.generate_keypair(2048)
        data = b"Test RSA signing data"

        signers = [
            {
                "id": "rsa_signer",
                "type": "rsa",
                "private_key": private_key,
            },
        ]
        result = self.orchestrator.sign_with_multiple_keys(data, signers)
        assert result["signer_count"] == 1
        assert "rsa_signer" in result["signatures"]
        assert result["signatures"]["rsa_signer"]["type"] == "rsa"

    def test_verify_rsa_signature(self):
        """测试RSA签名验证。"""
        from oath_toolchain.core.crypto.primitives import RSACipher

        private_key, public_key = RSACipher.generate_keypair(2048)
        data = b"Verify this RSA signature"

        signers = [{"id": "rsa1", "type": "rsa", "private_key": private_key}]
        sig_result = self.orchestrator.sign_with_multiple_keys(data, signers)

        sig_result["signatures"]["rsa1"]["public_key"] = RSACipher.serialize_public_key(
            public_key
        )

        all_verified, verified = self.orchestrator.verify_multiple_signatures(
            data, sig_result
        )
        assert "rsa1" in verified

    def test_sign_invalid_type(self):
        """测试无效签名类型。"""
        with pytest.raises(ValidationError, match="不支持的签名类型"):
            self.orchestrator.sign_with_multiple_keys(
                b"data",
                [{"id": "s1", "type": "invalid", "private_key": "k"}],
            )

    def test_sign_missing_id(self):
        """测试缺少签名者ID。"""
        with pytest.raises(ValidationError, match="ID不能为空"):
            self.orchestrator.sign_with_multiple_keys(
                b"data",
                [{"id": "", "type": "hmac", "private_key": "k"}],
            )

    def test_verify_with_invalid_signature(self):
        """测试验证无效签名。"""
        data = b"test data"
        signatures = {
            "data_hash": base64.b64encode(b"hash").decode(),
            "signatures": {
                "bad_sig": {
                    "type": "hmac",
                    "signature": base64.b64encode(b"invalid").decode(),
                    "secret_key": b"wrong_key",
                }
            },
        }
        all_verified, verified = self.orchestrator.verify_multiple_signatures(
            data, signatures
        )
        assert all_verified is False

    def test_apply_profile_with_signatures(self):
        """测试应用带签名的安全配置文件。"""
        from oath_toolchain.core.crypto.primitives import RSACipher

        private_key, public_key = RSACipher.generate_keypair(2048)

        profile_config = {
            "encryption_layers": [{"type": "karmaca", "params": {"key": "test"}}],
            "key_config": {"base_text": "test", "length": 16},
            "signature_config": {
                "signers": [
                    {"id": "s1", "type": "hmac", "private_key": "hmac_key"},
                ]
            },
        }
        self.orchestrator.create_security_profile("sig_profile", profile_config)

        data = b"Profile with signatures"
        result = self.orchestrator.apply_security_profile("sig_profile", data)
        assert result["success"] is True
        assert "signatures" in result
        assert "encrypted_data" in result
        assert "generated_key" in result

    def test_encrypt_with_rsa_layer(self):
        """测试RSA加密层。"""
        data = b"Short RSA test data"
        layers = [{"type": "rsa", "params": {}}]
        encrypted = self.orchestrator.encrypt_with_multiple_layers(data, layers)
        assert encrypted is not None
        assert isinstance(encrypted, bytes)

    def test_decrypt_non_bytes(self):
        """测试非字节数据解密。"""
        with pytest.raises(ValidationError, match="必须是bytes类型"):
            self.orchestrator.decrypt_with_multiple_layers(
                "not bytes",
                [{"type": "aes"}],
            )
