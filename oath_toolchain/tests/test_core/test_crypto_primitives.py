"""密码学原语封装单元测试。"""
import pytest

from oath_toolchain.core.crypto.primitives import AESCipher, RSACipher, ECCipher
from oath_toolchain.core.exceptions import EncryptionError


class TestAESCipher:
    """测试AESCipher类。"""

    def test_generate_key(self):
        """测试生成AES密钥。"""
        key = AESCipher.generate_key(256)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_key_128(self):
        """测试生成128位密钥。"""
        key = AESCipher.generate_key(128)
        assert len(key) == 16

    def test_generate_key_192(self):
        """测试生成192位密钥。"""
        key = AESCipher.generate_key(192)
        assert len(key) == 24

    def test_generate_key_invalid_size(self):
        """测试无效密钥大小。"""
        with pytest.raises(ValueError):
            AESCipher.generate_key(512)

    def test_encrypt_decrypt(self):
        """测试AES加密和解密。"""
        key = AESCipher.generate_key(256)
        plaintext = b"Hello, World! This is a test message."
        ciphertext, nonce, tag = AESCipher.encrypt(plaintext, key)
        assert isinstance(ciphertext, bytes)
        assert isinstance(nonce, bytes)
        assert isinstance(tag, bytes)
        assert len(nonce) == 12
        assert len(tag) == 16

        decrypted = AESCipher.decrypt(ciphertext, key, nonce, tag)
        assert decrypted == plaintext

    def test_encrypt_decrypt_with_associated_data(self):
        """测试带关联数据的加密解密。"""
        key = AESCipher.generate_key(256)
        plaintext = b"Secret data"
        aad = b"Additional authenticated data"
        ciphertext, nonce, tag = AESCipher.encrypt(
            plaintext, key, associated_data=aad
        )
        decrypted = AESCipher.decrypt(
            ciphertext, key, nonce, tag, associated_data=aad
        )
        assert decrypted == plaintext

    def test_encrypt_decrypt_wrong_associated_data(self):
        """测试错误关联数据的解密失败。"""
        key = AESCipher.generate_key(256)
        plaintext = b"Secret data"
        ciphertext, nonce, tag = AESCipher.encrypt(
            plaintext, key, associated_data=b"correct aad"
        )
        with pytest.raises(EncryptionError):
            AESCipher.decrypt(
                ciphertext, key, nonce, tag, associated_data=b"wrong aad"
            )

    def test_encrypt_invalid_key_length(self):
        """测试无效密钥长度。"""
        with pytest.raises(ValueError):
            AESCipher.encrypt(b"data", b"short")

    def test_encrypt_with_custom_nonce(self):
        """测试使用自定义nonce。"""
        key = AESCipher.generate_key(256)
        nonce = b"123456789012"
        plaintext = b"test data"
        ciphertext, returned_nonce, tag = AESCipher.encrypt(
            plaintext, key, nonce=nonce
        )
        assert returned_nonce == nonce
        decrypted = AESCipher.decrypt(ciphertext, key, nonce, tag)
        assert decrypted == plaintext

    def test_decrypt_wrong_key(self):
        """测试错误密钥解密失败。"""
        key1 = AESCipher.generate_key(256)
        key2 = AESCipher.generate_key(256)
        plaintext = b"test data"
        ciphertext, nonce, tag = AESCipher.encrypt(plaintext, key1)
        with pytest.raises(EncryptionError):
            AESCipher.decrypt(ciphertext, key2, nonce, tag)

    def test_empty_plaintext(self):
        """测试空明文加密。"""
        key = AESCipher.generate_key(256)
        plaintext = b""
        ciphertext, nonce, tag = AESCipher.encrypt(plaintext, key)
        decrypted = AESCipher.decrypt(ciphertext, key, nonce, tag)
        assert decrypted == plaintext


class TestRSACipher:
    """测试RSACipher类。"""

    def test_generate_keypair(self):
        """测试生成RSA密钥对。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        assert private_key is not None
        assert public_key is not None

    def test_generate_keypair_small_key(self):
        """测试过小的密钥大小。"""
        with pytest.raises(ValueError):
            RSACipher.generate_keypair(key_size=1024)

    def test_generate_keypair_invalid_exponent(self):
        """测试无效的公钥指数。"""
        with pytest.raises(ValueError):
            RSACipher.generate_keypair(public_exponent=5)

    def test_encrypt_decrypt(self):
        """测试RSA加密解密。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        plaintext = b"Hello RSA!"
        ciphertext = RSACipher.encrypt(plaintext, public_key)
        assert isinstance(ciphertext, bytes)
        assert len(ciphertext) > 0

        decrypted = RSACipher.decrypt(ciphertext, private_key)
        assert decrypted == plaintext

    def test_sign_verify(self):
        """测试RSA签名和验证。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        data = b"Data to be signed"
        signature = RSACipher.sign(data, private_key)
        assert isinstance(signature, bytes)
        assert len(signature) > 0

        assert RSACipher.verify(data, signature, public_key) is True

    def test_verify_wrong_data(self):
        """测试错误数据的签名验证。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        data = b"Data to be signed"
        signature = RSACipher.sign(data, private_key)
        assert RSACipher.verify(b"Wrong data", signature, public_key) is False

    def test_verify_wrong_signature(self):
        """测试错误签名的验证。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        data = b"Data to be signed"
        RSACipher.sign(data, private_key)
        wrong_sig = b"x" * 256
        assert RSACipher.verify(data, wrong_sig, public_key) is False

    def test_serialize_deserialize_public_key(self):
        """测试公钥序列化和反序列化。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        pem = RSACipher.serialize_public_key(public_key)
        assert isinstance(pem, bytes)
        assert b"BEGIN PUBLIC KEY" in pem

        deserialized = RSACipher.deserialize_public_key(pem)
        assert deserialized is not None

        plaintext = b"test"
        ciphertext = RSACipher.encrypt(plaintext, public_key)
        decrypted = RSACipher.decrypt(ciphertext, private_key)
        assert decrypted == plaintext

    def test_deserialize_invalid_public_key(self):
        """测试无效公钥反序列化。"""
        with pytest.raises(ValueError):
            RSACipher.deserialize_public_key(b"not a valid key")

    def test_serialize_deserialize_private_key(self):
        """测试私钥序列化和反序列化。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        pem = RSACipher.serialize_private_key(private_key)
        assert isinstance(pem, bytes)
        assert b"BEGIN PRIVATE KEY" in pem

        deserialized = RSACipher.deserialize_private_key(pem)
        assert deserialized is not None

        data = b"test data"
        signature = RSACipher.sign(data, private_key)
        assert RSACipher.verify(data, signature, public_key) is True

    def test_serialize_private_key_with_password(self):
        """测试带密码的私钥序列化。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        password = b"my_password"
        pem = RSACipher.serialize_private_key(private_key, password=password)
        assert b"BEGIN ENCRYPTED PRIVATE KEY" in pem

        deserialized = RSACipher.deserialize_private_key(pem, password=password)
        assert deserialized is not None

    def test_deserialize_private_key_wrong_password(self):
        """测试错误密码的私钥反序列化。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        password = b"correct_password"
        pem = RSACipher.serialize_private_key(private_key, password=password)
        with pytest.raises(ValueError):
            RSACipher.deserialize_private_key(pem, password=b"wrong_password")

    def test_deserialize_invalid_private_key(self):
        """测试无效私钥反序列化。"""
        with pytest.raises(ValueError):
            RSACipher.deserialize_private_key(b"not a valid key")


class TestECCipher:
    """测试ECCipher类。"""

    def test_generate_keypair(self):
        """测试生成EC密钥对。"""
        private_key, public_key = ECCipher.generate_keypair()
        assert private_key is not None
        assert public_key is not None

    def test_derive_shared_key(self):
        """测试ECDH密钥交换。"""
        priv1, pub1 = ECCipher.generate_keypair()
        priv2, pub2 = ECCipher.generate_keypair()

        shared1 = ECCipher.derive_shared_key(priv1, pub2)
        shared2 = ECCipher.derive_shared_key(priv2, pub1)

        assert isinstance(shared1, bytes)
        assert isinstance(shared2, bytes)
        assert len(shared1) == 32
        assert shared1 == shared2

    def test_sign_verify(self):
        """测试ECDSA签名和验证。"""
        private_key, public_key = ECCipher.generate_keypair()
        data = b"Data to be signed with ECDSA"
        signature = ECCipher.sign(data, private_key)
        assert isinstance(signature, bytes)
        assert len(signature) > 0

        assert ECCipher.verify(data, signature, public_key) is True

    def test_verify_wrong_data(self):
        """测试错误数据的ECDSA验证。"""
        private_key, public_key = ECCipher.generate_keypair()
        data = b"Original data"
        signature = ECCipher.sign(data, private_key)
        assert ECCipher.verify(b"Wrong data", signature, public_key) is False

    def test_verify_wrong_signature(self):
        """测试错误签名的ECDSA验证。"""
        private_key, public_key = ECCipher.generate_keypair()
        data = b"test data"
        assert ECCipher.verify(data, b"wrong_signature", public_key) is False

    def test_serialize_deserialize_public_key(self):
        """测试EC公钥序列化和反序列化。"""
        private_key, public_key = ECCipher.generate_keypair()
        pem = ECCipher.serialize_public_key(public_key)
        assert isinstance(pem, bytes)
        assert b"BEGIN PUBLIC KEY" in pem

        deserialized = ECCipher.deserialize_public_key(pem)
        assert deserialized is not None

        data = b"test"
        signature = ECCipher.sign(data, private_key)
        assert ECCipher.verify(data, signature, deserialized) is True

    def test_deserialize_invalid_public_key(self):
        """测试无效EC公钥反序列化。"""
        with pytest.raises(ValueError):
            ECCipher.deserialize_public_key(b"not a valid key")

    def test_serialize_deserialize_private_key(self):
        """测试EC私钥序列化和反序列化。"""
        private_key, public_key = ECCipher.generate_keypair()
        pem = ECCipher.serialize_private_key(private_key)
        assert isinstance(pem, bytes)

        deserialized = ECCipher.deserialize_private_key(pem)
        assert deserialized is not None

        data = b"test data"
        signature = ECCipher.sign(data, deserialized)
        assert ECCipher.verify(data, signature, public_key) is True

    def test_serialize_private_key_with_password(self):
        """测试带密码的EC私钥序列化。"""
        private_key, public_key = ECCipher.generate_keypair()
        password = b"ec_password"
        pem = ECCipher.serialize_private_key(private_key, password=password)
        assert b"BEGIN ENCRYPTED PRIVATE KEY" in pem

        deserialized = ECCipher.deserialize_private_key(pem, password=password)
        assert deserialized is not None

    def test_deserialize_invalid_private_key(self):
        """测试无效EC私钥反序列化。"""
        with pytest.raises(ValueError):
            ECCipher.deserialize_private_key(b"not a valid key")
