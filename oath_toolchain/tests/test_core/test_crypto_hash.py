"""哈希函数单元测试。"""
import os
import tempfile
import pytest

from oath_toolchain.core.crypto.hash import Hash


class TestHash:
    """测试Hash类。"""

    def test_sha256(self):
        """测试SHA-256哈希。"""
        data = b"hello world"
        result = Hash.sha256(data)
        assert isinstance(result, bytes)
        assert len(result) == 32
        assert result == Hash.sha256(data)

    def test_sha256_empty(self):
        """测试空数据的SHA-256。"""
        result = Hash.sha256(b"")
        assert len(result) == 32

    def test_sha512(self):
        """测试SHA-512哈希。"""
        data = b"hello world"
        result = Hash.sha512(data)
        assert isinstance(result, bytes)
        assert len(result) == 64

    def test_sha3_256(self):
        """测试SHA3-256哈希。"""
        data = b"hello world"
        result = Hash.sha3_256(data)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_sha3_512(self):
        """测试SHA3-512哈希。"""
        data = b"hello world"
        result = Hash.sha3_512(data)
        assert isinstance(result, bytes)
        assert len(result) == 64

    def test_blake2b_default(self):
        """测试默认大小的BLAKE2b。"""
        data = b"hello world"
        result = Hash.blake2b(data)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_blake2b_custom_size(self):
        """测试自定义大小的BLAKE2b。"""
        data = b"hello world"
        result = Hash.blake2b(data, digest_size=64)
        assert len(result) == 64

    def test_blake2s(self):
        """测试BLAKE2s哈希。"""
        data = b"hello world"
        result = Hash.blake2s(data)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_md5(self):
        """测试MD5哈希。"""
        data = b"hello world"
        result = Hash.md5(data)
        assert isinstance(result, bytes)
        assert len(result) == 16

    def test_hmac_sha256(self):
        """测试HMAC-SHA256。"""
        key = b"secret key"
        data = b"hello world"
        result = Hash.hmac(key, data, "sha256")
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hmac_deterministic(self):
        """测试HMAC的确定性。"""
        key = b"secret key"
        data = b"hello world"
        r1 = Hash.hmac(key, data, "sha256")
        r2 = Hash.hmac(key, data, "sha256")
        assert r1 == r2

    def test_hmac_invalid_algorithm(self):
        """测试无效的HMAC算法。"""
        with pytest.raises(ValueError):
            Hash.hmac(b"key", b"data", "invalid_alg")

    def test_pbkdf2(self):
        """测试PBKDF2。"""
        password = b"password"
        salt = b"salt"
        result = Hash.pbkdf2(password, salt, iterations=1000, dkLen=32)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_pbkdf2_deterministic(self):
        """测试PBKDF2的确定性。"""
        password = b"password"
        salt = b"salt"
        r1 = Hash.pbkdf2(password, salt, iterations=1000, dkLen=32)
        r2 = Hash.pbkdf2(password, salt, iterations=1000, dkLen=32)
        assert r1 == r2

    def test_pbkdf2_different_passwords(self):
        """测试不同密码产生不同结果。"""
        salt = b"salt"
        r1 = Hash.pbkdf2(b"pass1", salt, iterations=1000, dkLen=32)
        r2 = Hash.pbkdf2(b"pass2", salt, iterations=1000, dkLen=32)
        assert r1 != r2

    def test_pbkdf2_invalid_iterations(self):
        """测试无效的迭代次数。"""
        with pytest.raises(ValueError):
            Hash.pbkdf2(b"pass", b"salt", iterations=0)

    def test_pbkdf2_invalid_dklen(self):
        """测试无效的派生密钥长度。"""
        with pytest.raises(ValueError):
            Hash.pbkdf2(b"pass", b"salt", dkLen=0)

    def test_hash_file(self):
        """测试文件哈希。"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            temp_path = f.name

        try:
            result = Hash.hash_file(temp_path, "sha256")
            assert len(result) == 32
            assert result == Hash.sha256(b"hello world")
        finally:
            os.unlink(temp_path)

    def test_hash_file_invalid_algorithm(self):
        """测试无效的文件哈希算法。"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                Hash.hash_file(temp_path, "invalid_alg")
        finally:
            os.unlink(temp_path)

    def test_to_hex(self):
        """测试转换为十六进制。"""
        data = b"\x01\x02\x03"
        hex_str = Hash.to_hex(data)
        assert isinstance(hex_str, str)
        assert hex_str == "010203"

    def test_from_hex(self):
        """测试从十六进制转换。"""
        hex_str = "010203"
        data = Hash.from_hex(hex_str)
        assert data == b"\x01\x02\x03"

    def test_from_hex_invalid(self):
        """测试无效的十六进制字符串。"""
        with pytest.raises(ValueError):
            Hash.from_hex("not_hex")

    def test_hex_roundtrip(self):
        """测试十六进制往返转换。"""
        original = b"hello world test data"
        hex_str = Hash.to_hex(Hash.sha256(original))
        result = Hash.from_hex(hex_str)
        assert result == Hash.sha256(original)
