"""哈希函数模块。

提供统一的哈希函数接口，支持多种哈希算法。
"""
from __future__ import annotations

import hashlib
import hmac as hmac_lib
from typing import Optional


class Hash:
    """哈希工具类。

    提供统一的哈希接口，支持多种常用哈希算法。
    """

    @staticmethod
    def sha256(data: bytes) -> bytes:
        """计算SHA-256哈希。

        Args:
            data: 输入数据

        Returns:
            SHA-256哈希值（32字节）
        """
        return hashlib.sha256(data).digest()

    @staticmethod
    def sha512(data: bytes) -> bytes:
        """计算SHA-512哈希。

        Args:
            data: 输入数据

        Returns:
            SHA-512哈希值（64字节）
        """
        return hashlib.sha512(data).digest()

    @staticmethod
    def sha3_256(data: bytes) -> bytes:
        """计算SHA3-256哈希。

        Args:
            data: 输入数据

        Returns:
            SHA3-256哈希值（32字节）
        """
        return hashlib.sha3_256(data).digest()

    @staticmethod
    def sha3_512(data: bytes) -> bytes:
        """计算SHA3-512哈希。

        Args:
            data: 输入数据

        Returns:
            SHA3-512哈希值（64字节）
        """
        return hashlib.sha3_512(data).digest()

    @staticmethod
    def blake2b(data: bytes, digest_size: int = 32) -> bytes:
        """计算BLAKE2b哈希。

        Args:
            data: 输入数据
            digest_size: 摘要大小（字节），默认为32

        Returns:
            BLAKE2b哈希值
        """
        return hashlib.blake2b(data, digest_size=digest_size).digest()

    @staticmethod
    def blake2s(data: bytes, digest_size: int = 32) -> bytes:
        """计算BLAKE2s哈希。

        Args:
            data: 输入数据
            digest_size: 摘要大小（字节），默认为32

        Returns:
            BLAKE2s哈希值
        """
        return hashlib.blake2s(data, digest_size=digest_size).digest()

    @staticmethod
    def md5(data: bytes) -> bytes:
        """计算MD5哈希。

        注意：MD5已被证明不安全，仅用于兼容性目的。

        Args:
            data: 输入数据

        Returns:
            MD5哈希值（16字节）
        """
        return hashlib.md5(data).digest()

    @staticmethod
    def hmac(
        key: bytes,
        data: bytes,
        hash_alg: str = "sha256",
    ) -> bytes:
        """计算HMAC消息认证码。

        Args:
            key: 密钥
            data: 输入数据
            hash_alg: 哈希算法名称，支持sha256, sha512, sha3_256等

        Returns:
            HMAC值

        Raises:
            ValueError: 当哈希算法不支持时
        """
        try:
            return hmac_lib.new(key, data, hash_alg).digest()
        except ValueError as e:
            raise ValueError(f"不支持的哈希算法: {hash_alg}") from e

    @staticmethod
    def pbkdf2(
        password: bytes,
        salt: bytes,
        iterations: int = 100000,
        dkLen: int = 32,
        hash_alg: str = "sha256",
    ) -> bytes:
        """使用PBKDF2派生密钥。

        Args:
            password: 密码
            salt: 盐值
            iterations: 迭代次数，默认为100000
            dkLen: 派生密钥长度（字节），默认为32
            hash_alg: 哈希算法名称，默认为sha256

        Returns:
            派生密钥

        Raises:
            ValueError: 当参数无效时
        """
        if iterations < 1:
            raise ValueError("迭代次数必须大于0")
        if dkLen < 1:
            raise ValueError("派生密钥长度必须大于0")
        return hashlib.pbkdf2_hmac(hash_alg, password, salt, iterations, dkLen)

    @staticmethod
    def hash_file(
        file_path: str,
        hash_alg: str = "sha256",
        chunk_size: int = 8192,
    ) -> bytes:
        """计算文件的哈希值。

        Args:
            file_path: 文件路径
            hash_alg: 哈希算法名称，默认为sha256
            chunk_size: 分块读取大小，默认为8192字节

        Returns:
            文件哈希值

        Raises:
            FileNotFoundError: 当文件不存在时
            ValueError: 当哈希算法不支持时
        """
        try:
            hasher = hashlib.new(hash_alg)
        except ValueError as e:
            raise ValueError(f"不支持的哈希算法: {hash_alg}") from e

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.digest()

    @staticmethod
    def to_hex(hash_bytes: bytes) -> str:
        """将哈希字节转换为十六进制字符串。

        Args:
            hash_bytes: 哈希字节

        Returns:
            十六进制字符串
        """
        return hash_bytes.hex()

    @staticmethod
    def from_hex(hex_str: str) -> bytes:
        """将十六进制字符串转换为哈希字节。

        Args:
            hex_str: 十六进制字符串

        Returns:
            哈希字节

        Raises:
            ValueError: 当十六进制字符串无效时
        """
        return bytes.fromhex(hex_str)
