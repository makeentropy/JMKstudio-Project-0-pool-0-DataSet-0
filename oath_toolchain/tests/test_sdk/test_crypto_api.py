"""加密API单元测试。"""
import pytest

from oath_toolchain.sdk import OathSDK
from oath_toolchain.core.crypto.primitives import AESCipher, RSACipher
from oath_toolchain.core.registry import ToolRegistry


class TestCryptoAPI:
    """测试CryptoAPI类。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.sdk = OathSDK()
        self.test_data = b"Hello, Oath Toolchain!"

    def test_encrypt_decrypt_aes(self):
        """测试AES加密解密往返。"""
        key = AESCipher.generate_key(256)
        encrypted = self.sdk.crypto.encrypt_aes(self.test_data, key)
        assert isinstance(encrypted, bytes)
        assert encrypted != self.test_data
        assert len(encrypted) == len(self.test_data) + 28

        decrypted = self.sdk.crypto.decrypt_aes(encrypted, key)
        assert decrypted == self.test_data

    def test_encrypt_aes_128_key(self):
        """测试使用128位AES密钥。"""
        key = AESCipher.generate_key(128)
        encrypted = self.sdk.crypto.encrypt_aes(self.test_data, key)
        decrypted = self.sdk.crypto.decrypt_aes(encrypted, key)
        assert decrypted == self.test_data

    def test_encrypt_aes_invalid_key_length(self):
        """测试无效的AES密钥长度。"""
        with pytest.raises(ValueError):
            self.sdk.crypto.encrypt_aes(self.test_data, b"short")

    def test_encrypt_decrypt_rsa(self):
        """测试RSA加密解密往返。"""
        private_key, public_key = self.sdk.keys.generate_rsa_key(2048)
        test_data = b"Short RSA test"

        encrypted = self.sdk.crypto.encrypt_rsa(test_data, public_key)
        assert isinstance(encrypted, bytes)
        assert encrypted != test_data

        decrypted = self.sdk.crypto.decrypt_rsa(encrypted, private_key)
        assert decrypted == test_data

    def test_encrypt_karmaca(self):
        """测试KARMACA加密。"""
        space_key = b"test_karmaca_space_key_12345"
        encrypted = self.sdk.crypto.encrypt_karmaca(self.test_data, space_key)
        assert isinstance(encrypted, bytes)
        assert encrypted != self.test_data

    def test_decrypt_karmaca(self):
        """测试KARMACA解密。"""
        space_key = b"test_karmaca_space_key_12345"
        encrypted = self.sdk.crypto.encrypt_karmaca(self.test_data, space_key)
        decrypted = self.sdk.crypto.decrypt_karmaca(encrypted, space_key)
        assert decrypted == self.test_data

    def test_karmaca_different_dimensions(self):
        """测试不同维度的KARMACA加密解密。"""
        space_key = b"test_dimensions_key"
        for dims in [2, 3, 4]:
            encrypted = self.sdk.crypto.encrypt_karmaca(
                self.test_data, space_key, dimensions=dims
            )
            decrypted = self.sdk.crypto.decrypt_karmaca(
                encrypted, space_key, dimensions=dims
            )
            assert decrypted == self.test_data, f"维度{dims}解密失败"

    def test_encrypt_geometric(self):
        """测试几何证明加密。"""
        key = AESCipher.generate_key(256)
        result = self.sdk.crypto.encrypt_geometric(self.test_data, key)
        assert isinstance(result, dict)
        assert "data" in result
        assert "proof" in result
        assert isinstance(result["data"], bytes)
        assert isinstance(result["proof"], dict)

    def test_decrypt_geometric(self):
        """测试几何证明解密。"""
        key = AESCipher.generate_key(256)
        result = self.sdk.crypto.encrypt_geometric(self.test_data, key)
        decrypted = self.sdk.crypto.decrypt_geometric(
            result["data"], result["proof"], key
        )
        assert decrypted == self.test_data

    def test_encrypt_full_aes_only(self):
        """测试仅AES的完整加密。"""
        aes_key = AESCipher.generate_key(256)
        config = {"aes_key": aes_key}

        encrypted = self.sdk.crypto.encrypt_full(self.test_data, config)
        assert isinstance(encrypted, dict)
        assert "layers" in encrypted
        assert "final_data" in encrypted
        assert len(encrypted["layers"]) == 1
        assert encrypted["layers"][0]["type"] == "aes"

        decrypted = self.sdk.crypto.decrypt_full(encrypted, config)
        assert decrypted == self.test_data

    def test_encrypt_full_multiple_layers(self):
        """测试多层加密。"""
        aes_key = AESCipher.generate_key(256)
        space_key = b"multi_layer_test_key"
        config = {
            "aes_key": aes_key,
            "space_key": space_key,
            "karmaca_dimensions": 3,
        }

        encrypted = self.sdk.crypto.encrypt_full(self.test_data, config)
        assert len(encrypted["layers"]) == 2

        decrypted = self.sdk.crypto.decrypt_full(encrypted, config)
        assert decrypted == self.test_data

    def test_sign_verify_rsa(self):
        """测试RSA签名和验证。"""
        private_key, public_key = self.sdk.keys.generate_rsa_key(2048)

        signature = self.sdk.crypto.sign(self.test_data, private_key, method='rsa')
        assert isinstance(signature, bytes)

        valid = self.sdk.crypto.verify(
            self.test_data, signature, public_key, method='rsa'
        )
        assert valid is True

    def test_verify_invalid_signature(self):
        """测试验证无效签名。"""
        private_key, public_key = self.sdk.keys.generate_rsa_key(2048)

        signature = self.sdk.crypto.sign(self.test_data, private_key, method='rsa')
        modified_data = b"Modified data"
        valid = self.sdk.crypto.verify(
            modified_data, signature, public_key, method='rsa'
        )
        assert valid is False

    def test_hash_sha256(self):
        """测试SHA-256哈希。"""
        result = self.sdk.crypto.hash(self.test_data, algorithm='sha256')
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hash_sha512(self):
        """测试SHA-512哈希。"""
        result = self.sdk.crypto.hash(self.test_data, algorithm='sha512')
        assert isinstance(result, bytes)
        assert len(result) == 64

    def test_hash_consistency(self):
        """测试哈希一致性。"""
        h1 = self.sdk.crypto.hash(self.test_data, algorithm='sha256')
        h2 = self.sdk.crypto.hash(self.test_data, algorithm='sha256')
        assert h1 == h2

    def test_hash_different_data(self):
        """测试不同数据的哈希不同。"""
        h1 = self.sdk.crypto.hash(self.test_data, algorithm='sha256')
        h2 = self.sdk.crypto.hash(b"Different data", algorithm='sha256')
        assert h1 != h2

    def test_hash_invalid_algorithm(self):
        """测试无效的哈希算法。"""
        with pytest.raises(ValueError):
            self.sdk.crypto.hash(self.test_data, algorithm='invalid_alg')

    def test_hmac(self):
        """测试HMAC。"""
        key = b"test_hmac_key"
        result = self.sdk.crypto.hmac(self.test_data, key, algorithm='sha256')
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hmac_consistency(self):
        """测试HMAC一致性。"""
        key = b"test_hmac_key"
        h1 = self.sdk.crypto.hmac(self.test_data, key, algorithm='sha256')
        h2 = self.sdk.crypto.hmac(self.test_data, key, algorithm='sha256')
        assert h1 == h2

    def test_hmac_different_key(self):
        """测试不同密钥的HMAC不同。"""
        h1 = self.sdk.crypto.hmac(self.test_data, b"key1", algorithm='sha256')
        h2 = self.sdk.crypto.hmac(self.test_data, b"key2", algorithm='sha256')
        assert h1 != h2
