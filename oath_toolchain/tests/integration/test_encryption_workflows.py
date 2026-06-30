"""加密工作流集成测试。"""
from __future__ import annotations

import pytest

from oath_toolchain.core.crypto.primitives import AESCipher, RSACipher
from oath_toolchain.core.crypto.hash import Hash
from oath_toolchain.core.math.vector import Vector
from oath_toolchain.tools.geometric_proof.geometric_hash import GeometricHash
from oath_toolchain.tools.karmaca.encryption import KarmacaEncryption
from oath_toolchain.tools.karmaca.space_dict import KarmaSpaceDict
from oath_toolchain.tools.steganography.text_stego import TextSteganography


pytestmark = [pytest.mark.integration, pytest.mark.crypto]


class TestHybridEncryption:
    """AES+RSA混合加密测试。"""

    def test_hybrid_encrypt_decrypt(self, sample_data, rsa_keys):
        """测试AES+RSA混合加密解密流程。"""
        private_key, public_key = rsa_keys
        aes_key = AESCipher.generate_key(256)

        ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)
        encrypted_key = RSACipher.encrypt(aes_key, public_key)

        decrypted_key = RSACipher.decrypt(encrypted_key, private_key)
        assert decrypted_key == aes_key

        decrypted_data = AESCipher.decrypt(ciphertext, decrypted_key, nonce, tag)
        assert decrypted_data == sample_data

    def test_hybrid_with_associated_data(self, sample_data, rsa_keys):
        """测试带关联数据的混合加密。"""
        private_key, public_key = rsa_keys
        aes_key = AESCipher.generate_key(256)
        ad = b"associated data for authentication"

        ciphertext, nonce, tag = AESCipher.encrypt(
            sample_data, aes_key, associated_data=ad
        )
        encrypted_key = RSACipher.encrypt(aes_key, public_key)

        decrypted_key = RSACipher.decrypt(encrypted_key, private_key)
        decrypted_data = AESCipher.decrypt(
            ciphertext, decrypted_key, nonce, tag, associated_data=ad
        )
        assert decrypted_data == sample_data

    def test_hybrid_key_size_2048(self, sample_data):
        """测试2048位RSA密钥的混合加密。"""
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        aes_key = AESCipher.generate_key(128)

        ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)
        encrypted_key = RSACipher.encrypt(aes_key, public_key)

        decrypted_key = RSACipher.decrypt(encrypted_key, private_key)
        decrypted_data = AESCipher.decrypt(ciphertext, decrypted_key, nonce, tag)
        assert decrypted_data == sample_data


class TestKarmacaGeometricProof:
    """KARMACA+几何证明组合测试。"""

    def _create_3d_space_dict(self) -> KarmaSpaceDict:
        """创建3维空间字典。"""
        space_dict = KarmaSpaceDict(dimensions=3, key_size=32)
        points = [
            Vector([0.0, 0.0, 0.0]),
            Vector([1.0, 0.0, 0.0]),
            Vector([0.0, 1.0, 0.0]),
            Vector([0.0, 0.0, 1.0]),
            Vector([1.0, 1.0, 0.0]),
            Vector([1.0, 0.0, 1.0]),
            Vector([0.0, 1.0, 1.0]),
            Vector([1.0, 1.0, 1.0]),
        ]
        keys = [bytes([i] * 32) for i in range(len(points))]
        space_dict.build(points, keys)
        return space_dict

    def test_karmaca_encrypt_with_geometric_hash(self, sample_data):
        """测试KARMACA加密与几何哈希组合。"""
        space_dict = self._create_3d_space_dict()
        karmaca = KarmacaEncryption()
        geo_hash = GeometricHash(dimensions=4, hash_alg="sha256")

        data_hash = geo_hash.hash_data(sample_data)
        coordinate = Vector([0.5, 0.5, 0.5])

        encrypted = karmaca.encrypt(sample_data, coordinate, space_dict)
        decrypted = karmaca.decrypt(encrypted, coordinate, space_dict)

        assert decrypted == sample_data
        assert len(data_hash) == 32

    def test_karmaca_geometric_verification(self, sample_data):
        """测试KARMACA加密后几何哈希验证。"""
        space_dict = self._create_3d_space_dict()
        karmaca = KarmacaEncryption()
        geo_hash = GeometricHash(dimensions=3, hash_alg="sha256")

        original_hash = geo_hash.hash_data(sample_data)
        coordinate = Vector([0.3, 0.7, 0.2])

        encrypted = karmaca.encrypt(sample_data, coordinate, space_dict)
        decrypted = karmaca.decrypt(encrypted, coordinate, space_dict)
        decrypted_hash = geo_hash.hash_data(decrypted)

        assert decrypted_hash == original_hash
        assert decrypted == sample_data

    def test_multiple_coordinates(self, sample_data):
        """测试不同坐标的加密解密。"""
        space_dict = self._create_3d_space_dict()
        karmaca = KarmacaEncryption()

        coordinates = [
            Vector([0.1, 0.2, 0.3]),
            Vector([0.9, 0.1, 0.8]),
            Vector([0.5, 0.5, 0.5]),
            Vector([0.0, 0.0, 0.0]),
        ]

        for coord in coordinates:
            encrypted = karmaca.encrypt(sample_data, coord, space_dict)
            decrypted = karmaca.decrypt(encrypted, coord, space_dict)
            assert decrypted == sample_data


class TestFullEncryptionPipeline:
    """完整加密管道测试。"""

    def test_hash_encrypt_sign_verify(self, sample_data, rsa_keys):
        """测试哈希→加密→签名→验证完整流程。"""
        private_key, public_key = rsa_keys
        aes_key = AESCipher.generate_key(256)

        data_hash = Hash.sha256(sample_data)
        ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)
        signature = RSACipher.sign(data_hash, private_key)

        assert RSACipher.verify(data_hash, signature, public_key)

        decrypted = AESCipher.decrypt(ciphertext, aes_key, nonce, tag)
        decrypted_hash = Hash.sha256(decrypted)
        assert decrypted_hash == data_hash
        assert decrypted == sample_data

    def test_encrypt_with_multiple_hashes(self, sample_data):
        """测试多种哈希算法的加密流程。"""
        aes_key = AESCipher.generate_key(256)

        hash_funcs = [
            Hash.sha256,
            Hash.sha512,
            Hash.blake2b,
        ]

        for hash_func in hash_funcs:
            original_hash = hash_func(sample_data)
            ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)
            decrypted = AESCipher.decrypt(ciphertext, aes_key, nonce, tag)
            decrypted_hash = hash_func(decrypted)
            assert decrypted_hash == original_hash

    def test_large_data_pipeline(self, medium_sample_data, rsa_keys):
        """测试大数据量的加密管道。"""
        private_key, public_key = rsa_keys
        aes_key = AESCipher.generate_key(256)

        data_hash = Hash.sha256(medium_sample_data)
        ciphertext, nonce, tag = AESCipher.encrypt(medium_sample_data, aes_key)
        signature = RSACipher.sign(data_hash, private_key)

        assert RSACipher.verify(data_hash, signature, public_key)
        decrypted = AESCipher.decrypt(ciphertext, aes_key, nonce, tag)
        assert decrypted == medium_sample_data


class TestStegoEncryptionPipeline:
    """加密→隐写→提取→解密全流程测试。"""

    def _generate_carrier(self, num_lines: int = 200) -> str:
        """生成载体文本。"""
        lines = []
        for i in range(num_lines):
            lines.append(f"Line {i + 1}: This is a sample carrier text line.")
        return "\n".join(lines)

    def test_aes_encrypt_then_text_stego(self, sample_data):
        """测试AES加密后文本隐写全流程。"""
        aes_key = AESCipher.generate_key(256)
        text_stego = TextSteganography()
        carrier = self._generate_carrier(1000)

        ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)
        encrypted_data = nonce + tag + ciphertext

        stego_text = text_stego.embed_whitespace(carrier, encrypted_data)
        extracted_data = text_stego.extract_whitespace(stego_text)

        assert extracted_data == encrypted_data

        extracted_nonce = extracted_data[:12]
        extracted_tag = extracted_data[12:28]
        extracted_ciphertext = extracted_data[28:]
        decrypted = AESCipher.decrypt(
            extracted_ciphertext, aes_key, extracted_nonce, extracted_tag
        )
        assert decrypted == sample_data

    def test_hybrid_encrypt_stego_pipeline(self, sample_data, rsa_keys):
        """测试混合加密+隐写完整管道。"""
        private_key, public_key = rsa_keys
        aes_key = AESCipher.generate_key(256)
        text_stego = TextSteganography()
        carrier = self._generate_carrier(3000)

        ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)
        encrypted_key = RSACipher.encrypt(aes_key, public_key)

        payload = len(encrypted_key).to_bytes(2, "big") + encrypted_key + nonce + tag + ciphertext

        stego_text = text_stego.embed_whitespace(carrier, payload)
        extracted_payload = text_stego.extract_whitespace(stego_text)

        assert extracted_payload == payload

        key_len = int.from_bytes(extracted_payload[:2], "big")
        extracted_encrypted_key = extracted_payload[2 : 2 + key_len]
        offset = 2 + key_len
        extracted_nonce = extracted_payload[offset : offset + 12]
        extracted_tag = extracted_payload[offset + 12 : offset + 28]
        extracted_ciphertext = extracted_payload[offset + 28 :]

        decrypted_key = RSACipher.decrypt(extracted_encrypted_key, private_key)
        decrypted_data = AESCipher.decrypt(
            extracted_ciphertext, decrypted_key, extracted_nonce, extracted_tag
        )
        assert decrypted_data == sample_data

    def test_unicode_stego_pipeline(self, sample_data):
        """测试Unicode零宽字符隐写全流程。"""
        aes_key = AESCipher.generate_key(128)
        text_stego = TextSteganography()
        carrier = "This is a normal text that will carry hidden data. " * 100

        ciphertext, nonce, tag = AESCipher.encrypt(sample_data, aes_key)
        encrypted_data = nonce + tag + ciphertext

        stego_text = text_stego.embed_unicode(carrier, encrypted_data)
        extracted_data = text_stego.extract_unicode(stego_text)

        assert extracted_data == encrypted_data

        extracted_nonce = extracted_data[:12]
        extracted_tag = extracted_data[12:28]
        extracted_ciphertext = extracted_data[28:]
        decrypted = AESCipher.decrypt(
            extracted_ciphertext, aes_key, extracted_nonce, extracted_tag
        )
        assert decrypted == sample_data
