"""密码学安全测试。"""
from __future__ import annotations

import math
import os

import pytest

from oath_toolchain.core.crypto.primitives import AESCipher, RSACipher
from oath_toolchain.core.crypto.hash import Hash
from oath_toolchain.core.crypto.random import get_random_bytes
from oath_toolchain.core.crypto.kdf import KDF


pytestmark = [pytest.mark.security, pytest.mark.crypto]


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


class TestKeyStrength:
    """密钥强度检测。"""

    def test_aes_key_length(self):
        """测试AES密钥长度。"""
        key_128 = AESCipher.generate_key(128)
        key_256 = AESCipher.generate_key(256)

        assert len(key_128) == 16
        assert len(key_256) == 32

    def test_aes_key_uniqueness(self):
        """测试AES密钥的唯一性。"""
        keys = [AESCipher.generate_key(256) for _ in range(100)]
        unique_keys = set(keys)

        assert len(unique_keys) == len(keys)

    def test_rsa_key_strength_2048(self):
        """测试RSA-2048密钥强度。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)

        private_pem = RSACipher.serialize_private_key(private_key)
        public_pem = RSACipher.serialize_public_key(public_key)

        assert len(private_pem) > 1000
        assert len(public_pem) > 100

    def test_random_bytes_entropy(self):
        """测试随机字节生成器的熵值。"""
        random_data = get_random_bytes(10000)
        entropy = calculate_entropy(random_data)

        print(f"\n随机字节熵 (10000 bytes): {entropy:.4f} bits/byte")

        assert entropy > 7.5

    def test_kdf_output_length(self):
        """测试KDF输出长度。"""
        key = os.urandom(32)
        salt = os.urandom(16)

        derived = KDF.hkdf(key, salt=salt, info=b"test", length=64)

        assert len(derived) == 64

    def test_pbkdf2_output_length(self):
        """测试PBKDF2输出长度。"""
        password = b"test_password"
        salt = os.urandom(16)

        derived = Hash.pbkdf2(password, salt, iterations=10000, dkLen=32)

        assert len(derived) == 32


class TestEncryptionEntropy:
    """加密后熵值测试。"""

    def test_aes_large_data_entropy(self, medium_sample_data):
        """测试大数据量AES加密后的熵值。"""
        key = AESCipher.generate_key(256)
        ciphertext, nonce, tag = AESCipher.encrypt(medium_sample_data, key)

        full_data = nonce + tag + ciphertext
        entropy = calculate_entropy(full_data)

        print(f"\nAES大文件加密熵 ({len(medium_sample_data)} bytes): {entropy:.4f} bits/byte")

        assert entropy > 7.0

    def test_rsa_encrypted_entropy(self):
        """测试RSA加密后数据的熵值。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        data = os.urandom(32)

        encrypted = RSACipher.encrypt(data, public_key)
        entropy = calculate_entropy(encrypted)

        print(f"\nRSA加密熵: {entropy:.4f} bits/byte")
        print(f"  密文长度: {len(encrypted)} bytes")

        assert entropy > 4.0

    def test_hash_output_deterministic(self, sample_data):
        """测试哈希输出的确定性。"""
        h1 = Hash.sha256(sample_data)
        h2 = Hash.sha256(sample_data)

        assert h1 == h2

    def test_hash_output_length(self, sample_data):
        """测试各种哈希算法的输出长度。"""
        assert len(Hash.sha256(sample_data)) == 32
        assert len(Hash.sha512(sample_data)) == 64
        assert len(Hash.blake2b(sample_data)) == 32

    def test_hmac_output_length(self):
        """测试HMAC输出长度。"""
        key = os.urandom(32)
        data = b"test data for hmac"

        hmac = Hash.hmac(key, data, "sha256")

        assert len(hmac) == 32


class TestKnownPlaintextResistance:
    """已知明文攻击抗性测试。"""

    def test_aes_same_data_different_keys(self, sample_data):
        """测试相同数据不同密钥加密结果不同。"""
        key1 = AESCipher.generate_key(256)
        key2 = AESCipher.generate_key(256)

        ct1, n1, t1 = AESCipher.encrypt(sample_data, key1)
        ct2, n2, t2 = AESCipher.encrypt(sample_data, key2)

        assert ct1 != ct2

    def test_aes_different_data_same_key(self):
        """测试不同数据相同密钥加密结果不同。"""
        key = AESCipher.generate_key(256)

        data1 = b"Data 1: Hello World"
        data2 = b"Data 2: Hello World"

        ct1, _, _ = AESCipher.encrypt(data1, key)
        ct2, _, _ = AESCipher.encrypt(data2, key)

        assert ct1 != ct2

    def test_aes_nonce_randomness(self, sample_data):
        """测试AES nonce的随机性。"""
        key = AESCipher.generate_key(256)

        nonces = []
        for _ in range(100):
            _, nonce, _ = AESCipher.encrypt(sample_data, key)
            nonces.append(nonce)

        unique_nonces = set(nonces)
        assert len(unique_nonces) == len(nonces)

    def test_rsa_same_data_different_encryption(self):
        """测试RSA相同数据相同公钥加密结果不同（OAEP填充随机性）。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        data = b"test data"

        enc1 = RSACipher.encrypt(data, public_key)
        enc2 = RSACipher.encrypt(data, public_key)

        assert enc1 != enc2

        dec1 = RSACipher.decrypt(enc1, private_key)
        dec2 = RSACipher.decrypt(enc2, private_key)

        assert dec1 == data
        assert dec2 == data

    def test_hash_avalanche_effect(self):
        """测试哈希的雪崩效应。"""
        data1 = b"The quick brown fox jumps over the lazy dog"
        data2 = b"The quick brown fox jumps over the lazy doh"

        h1 = Hash.sha256(data1)
        h2 = Hash.sha256(data2)

        differing_bits = sum(
            bin(a ^ b).count("1") for a, b in zip(h1, h2)
        )

        total_bits = len(h1) * 8
        diff_ratio = differing_bits / total_bits

        print(f"\n哈希雪崩效应:")
        print(f"  不同位数: {differing_bits}/{total_bits}")
        print(f"  差异比例: {diff_ratio*100:.2f}%")

        assert diff_ratio > 0.25


class TestTamperResistance:
    """篡改抗性测试。"""

    def test_aes_tamper_detection(self, sample_data, aes_key):
        """测试AES-GCM篡改检测。"""
        ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)

        tampered = bytearray(ciphertext)
        tampered[0] ^= 0xFF

        from oath_toolchain.core.exceptions import EncryptionError

        with pytest.raises(EncryptionError):
            AESCipher.decrypt(bytes(tampered), aes_key, nonce, tag)

    def test_aes_tag_tamper_detection(self, sample_data, aes_key):
        """测试AES-GCM标签篡改检测。"""
        ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)

        tampered_tag = bytearray(tag)
        tampered_tag[0] ^= 0xFF

        from oath_toolchain.core.exceptions import EncryptionError

        with pytest.raises(EncryptionError):
            AESCipher.decrypt(ciphertext, aes_key, nonce, bytes(tampered_tag))

    def test_rsa_signature_tamper_detection(self, sample_data, rsa_keys):
        """测试RSA签名篡改检测。"""
        private_key, public_key = rsa_keys
        signature = RSACipher.sign(sample_data, private_key)

        tampered_signature = bytearray(signature)
        tampered_signature[10] ^= 0xFF

        valid = RSACipher.verify(sample_data, bytes(tampered_signature), public_key)
        assert not valid

    def test_rsa_data_tamper_detection(self, sample_data, rsa_keys):
        """测试RSA数据篡改的签名验证失败。"""
        private_key, public_key = rsa_keys
        signature = RSACipher.sign(sample_data, private_key)

        tampered_data = bytearray(sample_data)
        tampered_data[0] ^= 0xFF

        valid = RSACipher.verify(bytes(tampered_data), signature, public_key)
        assert not valid
