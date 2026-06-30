"""安全随机数生成器单元测试。"""
import string
import pytest

from oath_toolchain.core.crypto.random import (
    SecureRandom,
    get_random_bytes,
    get_random_int,
    get_random_string,
    generate_salt,
)


class TestSecureRandom:
    """测试SecureRandom类。"""

    def test_singleton(self):
        """测试单例模式。"""
        r1 = SecureRandom()
        r2 = SecureRandom()
        assert r1 is r2

    def test_get_random_bytes(self):
        """测试生成随机字节。"""
        sr = SecureRandom()
        result = sr.get_random_bytes(32)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_get_random_bytes_zero(self):
        """测试生成零字节。"""
        sr = SecureRandom()
        result = sr.get_random_bytes(0)
        assert result == b""

    def test_get_random_bytes_negative(self):
        """测试负数字节数。"""
        sr = SecureRandom()
        with pytest.raises(ValueError):
            sr.get_random_bytes(-1)

    def test_get_random_bytes_unique(self):
        """测试随机字节的唯一性。"""
        sr = SecureRandom()
        b1 = sr.get_random_bytes(32)
        b2 = sr.get_random_bytes(32)
        assert b1 != b2

    def test_get_random_int(self):
        """测试生成随机整数。"""
        sr = SecureRandom()
        result = sr.get_random_int(1, 10)
        assert isinstance(result, int)
        assert 1 <= result <= 10

    def test_get_random_int_min_equals_max(self):
        """测试最小值等于最大值。"""
        sr = SecureRandom()
        result = sr.get_random_int(5, 5)
        assert result == 5

    def test_get_random_int_min_greater_than_max(self):
        """测试最小值大于最大值。"""
        sr = SecureRandom()
        with pytest.raises(ValueError):
            sr.get_random_int(10, 1)

    def test_get_random_string(self):
        """测试生成随机字符串。"""
        sr = SecureRandom()
        result = sr.get_random_string(16)
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in string.ascii_letters + string.digits for c in result)

    def test_get_random_string_custom_charset(self):
        """测试自定义字符集。"""
        sr = SecureRandom()
        charset = "abc"
        result = sr.get_random_string(10, charset=charset)
        assert len(result) == 10
        assert all(c in charset for c in result)

    def test_get_random_string_zero_length(self):
        """测试零长度字符串。"""
        sr = SecureRandom()
        result = sr.get_random_string(0)
        assert result == ""

    def test_get_random_string_negative_length(self):
        """测试负长度字符串。"""
        sr = SecureRandom()
        with pytest.raises(ValueError):
            sr.get_random_string(-1)

    def test_get_random_string_empty_charset(self):
        """测试空字符集。"""
        sr = SecureRandom()
        with pytest.raises(ValueError):
            sr.get_random_string(10, charset="")

    def test_generate_salt(self):
        """测试生成盐值。"""
        sr = SecureRandom()
        salt = sr.generate_salt()
        assert isinstance(salt, bytes)
        assert len(salt) == 16

    def test_generate_salt_custom_length(self):
        """测试自定义长度的盐值。"""
        sr = SecureRandom()
        salt = sr.generate_salt(32)
        assert len(salt) == 32

    def test_generate_salt_zero_length(self):
        """测试零长度盐值。"""
        sr = SecureRandom()
        with pytest.raises(ValueError):
            sr.generate_salt(0)

    def test_choice(self):
        """测试随机选择。"""
        sr = SecureRandom()
        seq = [1, 2, 3, 4, 5]
        result = sr.choice(seq)
        assert result in seq

    def test_choice_empty_sequence(self):
        """测试从空序列选择。"""
        sr = SecureRandom()
        with pytest.raises(IndexError):
            sr.choice([])

    def test_randbits(self):
        """测试随机位数。"""
        sr = SecureRandom()
        result = sr.randbits(8)
        assert isinstance(result, int)
        assert 0 <= result < 256

    def test_randbits_zero(self):
        """测试零位。"""
        sr = SecureRandom()
        result = sr.randbits(0)
        assert result == 0

    def test_randbits_negative(self):
        """测试负位数。"""
        sr = SecureRandom()
        with pytest.raises(ValueError):
            sr.randbits(-1)


class TestUtilityFunctions:
    """测试便捷函数。"""

    def test_get_random_bytes_func(self):
        """测试get_random_bytes便捷函数。"""
        result = get_random_bytes(16)
        assert isinstance(result, bytes)
        assert len(result) == 16

    def test_get_random_int_func(self):
        """测试get_random_int便捷函数。"""
        result = get_random_int(1, 100)
        assert 1 <= result <= 100

    def test_get_random_string_func(self):
        """测试get_random_string便捷函数。"""
        result = get_random_string(10)
        assert len(result) == 10

    def test_generate_salt_func(self):
        """测试generate_salt便捷函数。"""
        result = generate_salt()
        assert isinstance(result, bytes)
        assert len(result) == 16
