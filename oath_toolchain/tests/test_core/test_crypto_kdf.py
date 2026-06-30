"""密钥派生函数单元测试。"""
import pytest

from oath_toolchain.core.crypto.kdf import KDF


class TestKDF:
    """测试KDF类。"""

    def test_hkdf(self):
        """测试HKDF。"""
        ikm = b"input key material"
        salt = b"salt"
        info = b"info"
        result = KDF.hkdf(ikm, salt=salt, info=info, length=32)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hkdf_deterministic(self):
        """测试HKDF的确定性。"""
        ikm = b"input key material"
        salt = b"salt"
        r1 = KDF.hkdf(ikm, salt=salt, length=32)
        r2 = KDF.hkdf(ikm, salt=salt, length=32)
        assert r1 == r2

    def test_hkdf_no_salt(self):
        """测试无盐的HKDF。"""
        ikm = b"input key material"
        result = KDF.hkdf(ikm, length=32)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hkdf_no_info(self):
        """测试无info的HKDF。"""
        ikm = b"input key material"
        salt = b"salt"
        result = KDF.hkdf(ikm, salt=salt, length=32)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hkdf_custom_length(self):
        """测试自定义长度的HKDF。"""
        ikm = b"input key material"
        result = KDF.hkdf(ikm, length=64)
        assert len(result) == 64

    def test_hkdf_invalid_length(self):
        """测试无效长度的HKDF。"""
        with pytest.raises(ValueError):
            KDF.hkdf(b"ikm", length=0)

    def test_hkdf_sha512(self):
        """测试使用SHA-512的HKDF。"""
        ikm = b"input key material"
        result = KDF.hkdf(ikm, length=32, hash_alg="sha512")
        assert len(result) == 32

    def test_pbkdf2_hmac(self):
        """测试PBKDF2-HMAC。"""
        password = b"password"
        salt = b"salt"
        result = KDF.pbkdf2_hmac(password, salt, iterations=1000, dkLen=32)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_pbkdf2_hmac_deterministic(self):
        """测试PBKDF2-HMAC的确定性。"""
        password = b"password"
        salt = b"salt"
        r1 = KDF.pbkdf2_hmac(password, salt, iterations=1000, dkLen=32)
        r2 = KDF.pbkdf2_hmac(password, salt, iterations=1000, dkLen=32)
        assert r1 == r2

    def test_pbkdf2_hmac_invalid_iterations(self):
        """测试无效迭代次数。"""
        with pytest.raises(ValueError):
            KDF.pbkdf2_hmac(b"pass", b"salt", iterations=0)

    def test_pbkdf2_hmac_invalid_dklen(self):
        """测试无效派生密钥长度。"""
        with pytest.raises(ValueError):
            KDF.pbkdf2_hmac(b"pass", b"salt", dkLen=0)

    def test_scrypt(self):
        """测试scrypt。"""
        password = b"password"
        salt = b"salt"
        result = KDF.scrypt(password, salt, n=2**10, r=8, p=1, dkLen=32)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_scrypt_deterministic(self):
        """测试scrypt的确定性。"""
        password = b"password"
        salt = b"salt"
        r1 = KDF.scrypt(password, salt, n=2**10, r=8, p=1, dkLen=32)
        r2 = KDF.scrypt(password, salt, n=2**10, r=8, p=1, dkLen=32)
        assert r1 == r2

    def test_scrypt_invalid_n(self):
        """测试无效的n参数。"""
        with pytest.raises(ValueError):
            KDF.scrypt(b"pass", b"salt", n=3)

    def test_scrypt_invalid_r(self):
        """测试无效的r参数。"""
        with pytest.raises(ValueError):
            KDF.scrypt(b"pass", b"salt", r=0)

    def test_scrypt_invalid_p(self):
        """测试无效的p参数。"""
        with pytest.raises(ValueError):
            KDF.scrypt(b"pass", b"salt", p=0)

    def test_scrypt_invalid_dklen(self):
        """测试无效的派生密钥长度。"""
        with pytest.raises(ValueError):
            KDF.scrypt(b"pass", b"salt", dkLen=0)

    def test_derive_key_from_password_scrypt(self):
        """测试从密码派生密钥（scrypt）。"""
        password = "my_password"
        key, salt = KDF.derive_key_from_password(password, kdf_type="scrypt")
        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)
        assert len(key) == 32
        assert len(salt) == 16

    def test_derive_key_from_password_pbkdf2(self):
        """测试从密码派生密钥（pbkdf2）。"""
        password = "my_password"
        key, salt = KDF.derive_key_from_password(password, kdf_type="pbkdf2")
        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)
        assert len(key) == 32

    def test_derive_key_from_password_hkdf(self):
        """测试从密码派生密钥（hkdf）。"""
        password = "my_password"
        key, salt = KDF.derive_key_from_password(password, kdf_type="hkdf")
        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)
        assert len(key) == 32

    def test_derive_key_from_password_with_salt(self):
        """测试带盐值的密码派生密钥。"""
        password = "my_password"
        salt = b"my_salt_value_16b"
        key, returned_salt = KDF.derive_key_from_password(
            password, salt=salt, kdf_type="scrypt"
        )
        assert returned_salt == salt

    def test_derive_key_from_password_custom_length(self):
        """测试自定义长度的密码派生密钥。"""
        password = "my_password"
        key, salt = KDF.derive_key_from_password(password, dkLen=64)
        assert len(key) == 64

    def test_derive_key_from_password_invalid_type(self):
        """测试无效的KDF类型。"""
        with pytest.raises(ValueError):
            KDF.derive_key_from_password("pass", kdf_type="invalid")

    def test_verify_password_scrypt(self):
        """测试密码验证（scrypt）。"""
        password = "my_password"
        key, salt = KDF.derive_key_from_password(password, kdf_type="scrypt")
        assert KDF.verify_password(password, salt, key, kdf_type="scrypt") is True

    def test_verify_password_wrong_password(self):
        """测试错误密码验证。"""
        password = "my_password"
        key, salt = KDF.derive_key_from_password(password, kdf_type="scrypt")
        assert KDF.verify_password("wrong_password", salt, key, kdf_type="scrypt") is False

    def test_verify_password_pbkdf2(self):
        """测试密码验证（pbkdf2）。"""
        password = "my_password"
        key, salt = KDF.derive_key_from_password(password, kdf_type="pbkdf2")
        assert KDF.verify_password(password, salt, key, kdf_type="pbkdf2") is True

    def test_verify_password_hkdf(self):
        """测试密码验证（hkdf）。"""
        password = "my_password"
        key, salt = KDF.derive_key_from_password(password, kdf_type="hkdf")
        assert KDF.verify_password(password, salt, key, kdf_type="hkdf") is True

    def test_verify_password_invalid_type(self):
        """测试无效类型的密码验证。"""
        assert KDF.verify_password("pass", b"salt", b"key", kdf_type="invalid") is False
