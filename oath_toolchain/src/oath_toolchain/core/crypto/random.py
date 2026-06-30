"""安全随机数生成器。

提供加密安全的随机数生成功能。
"""
from __future__ import annotations

import os
import secrets
import string
from typing import Optional


class SecureRandom:
    """安全随机数生成器类。

    基于操作系统提供的加密安全随机源生成随机数。
    """

    _instance: Optional[SecureRandom] = None

    def __new__(cls) -> SecureRandom:
        """单例模式获取实例。

        Returns:
            SecureRandom单例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_random_bytes(self, n: int) -> bytes:
        """生成指定长度的随机字节。

        Args:
            n: 字节数

        Returns:
            随机字节串

        Raises:
            ValueError: 当n小于0时
        """
        if n < 0:
            raise ValueError("字节数不能为负数")
        return secrets.token_bytes(n)

    def get_random_int(self, min_val: int, max_val: int) -> int:
        """生成指定范围内的随机整数。

        Args:
            min_val: 最小值（含）
            max_val: 最大值（含）

        Returns:
            随机整数

        Raises:
            ValueError: 当min_val大于max_val时
        """
        if min_val > max_val:
            raise ValueError("最小值不能大于最大值")
        return secrets.randbelow(max_val - min_val + 1) + min_val

    def get_random_string(
        self,
        length: int,
        charset: Optional[str] = None,
    ) -> str:
        """生成指定长度的随机字符串。

        Args:
            length: 字符串长度
            charset: 字符集，默认为大小写字母+数字

        Returns:
            随机字符串

        Raises:
            ValueError: 当length小于0时
        """
        if length < 0:
            raise ValueError("长度不能为负数")
        if charset is None:
            charset = string.ascii_letters + string.digits
        if len(charset) == 0:
            raise ValueError("字符集不能为空")
        return "".join(secrets.choice(charset) for _ in range(length))

    def generate_salt(self, length: int = 16) -> bytes:
        """生成密码学安全的盐值。

        Args:
            length: 盐值长度（字节），默认为16

        Returns:
            盐值字节串

        Raises:
            ValueError: 当length小于1时
        """
        if length < 1:
            raise ValueError("盐值长度至少为1字节")
        return secrets.token_bytes(length)

    def choice(self, seq: list) -> object:
        """从序列中随机选择一个元素。

        Args:
            seq: 选择序列

        Returns:
            随机选择的元素

        Raises:
            IndexError: 当序列为空时
        """
        if len(seq) == 0:
            raise IndexError("不能从空序列中选择")
        return secrets.choice(seq)

    def randbits(self, k: int) -> int:
        """生成k位随机整数。

        Args:
            k: 位数

        Returns:
            k位随机整数

        Raises:
            ValueError: 当k小于0时
        """
        if k < 0:
            raise ValueError("位数不能为负数")
        return secrets.randbits(k)


def get_random_bytes(n: int) -> bytes:
    """生成指定长度的随机字节（便捷函数）。

    Args:
        n: 字节数

    Returns:
        随机字节串
    """
    return SecureRandom().get_random_bytes(n)


def get_random_int(min_val: int, max_val: int) -> int:
    """生成指定范围内的随机整数（便捷函数）。

    Args:
        min_val: 最小值（含）
        max_val: 最大值（含）

    Returns:
        随机整数
    """
    return SecureRandom().get_random_int(min_val, max_val)


def get_random_string(length: int, charset: Optional[str] = None) -> str:
    """生成指定长度的随机字符串（便捷函数）。

    Args:
        length: 字符串长度
        charset: 字符集，默认为大小写字母+数字

    Returns:
        随机字符串
    """
    return SecureRandom().get_random_string(length, charset)


def generate_salt(length: int = 16) -> bytes:
    """生成密码学安全的盐值（便捷函数）。

    Args:
        length: 盐值长度（字节），默认为16

    Returns:
        盐值字节串
    """
    return SecureRandom().generate_salt(length)
