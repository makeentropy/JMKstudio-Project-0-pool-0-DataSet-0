"""密钥派生函数模块。

提供多种密钥派生函数(KDF)的实现。
"""
from __future__ import annotations

from typing import Optional, Tuple

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives import hashes

from .random import generate_salt


class KDF:
    """密钥派生函数类。

    提供多种密钥派生算法的统一接口。
    """

    @staticmethod
    def hkdf(
        ikm: bytes,
        salt: Optional[bytes] = None,
        info: Optional[bytes] = None,
        length: int = 32,
        hash_alg: str = "sha256",
    ) -> bytes:
        """使用HKDF派生密钥。

        HKDF是基于HMAC的密钥派生函数，遵循RFC 5869。

        Args:
            ikm: 输入密钥材料
            salt: 盐值，可选，默认为None（使用全零盐）
            info: 上下文和应用特定信息，可选
            length: 派生密钥长度（字节），默认为32
            hash_alg: 哈希算法，默认为sha256

        Returns:
            派生密钥

        Raises:
            ValueError: 当参数无效时
        """
        if length < 1:
            raise ValueError("派生密钥长度必须大于0")

        hash_obj = KDF._get_hash_algorithm(hash_alg)

        hkdf = HKDF(
            algorithm=hash_obj,
            length=length,
            salt=salt,
            info=info or b"",
        )
        return hkdf.derive(ikm)

    @staticmethod
    def pbkdf2_hmac(
        password: bytes,
        salt: bytes,
        iterations: int = 200000,
        dkLen: int = 32,
        hash_alg: str = "sha256",
    ) -> bytes:
        """使用PBKDF2-HMAC派生密钥。

        PBKDF2是基于密码的密钥派生函数2，遵循RFC 2898。

        Args:
            password: 密码
            salt: 盐值
            iterations: 迭代次数，默认为200000
            dkLen: 派生密钥长度（字节），默认为32
            hash_alg: 哈希算法，默认为sha256

        Returns:
            派生密钥

        Raises:
            ValueError: 当参数无效时
        """
        if iterations < 1:
            raise ValueError("迭代次数必须大于0")
        if dkLen < 1:
            raise ValueError("派生密钥长度必须大于0")

        hash_obj = KDF._get_hash_algorithm(hash_alg)

        kdf = PBKDF2HMAC(
            algorithm=hash_obj,
            length=dkLen,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password)

    @staticmethod
    def scrypt(
        password: bytes,
        salt: bytes,
        n: int = 2**14,
        r: int = 8,
        p: int = 1,
        dkLen: int = 32,
    ) -> bytes:
        """使用scrypt派生密钥。

        scrypt是一种内存难的密钥派生函数，适合密码哈希。

        Args:
            password: 密码
            salt: 盐值
            n: CPU/内存成本参数，必须是2的幂，默认为2^14=16384
            r: 块大小参数，默认为8
            p: 并行化参数，默认为1
            dkLen: 派生密钥长度（字节），默认为32

        Returns:
            派生密钥

        Raises:
            ValueError: 当参数无效时
        """
        if n < 2 or (n & (n - 1)) != 0:
            raise ValueError("n必须是2的幂且大于等于2")
        if r < 1:
            raise ValueError("r必须大于0")
        if p < 1:
            raise ValueError("p必须大于0")
        if dkLen < 1:
            raise ValueError("派生密钥长度必须大于0")

        kdf = Scrypt(
            salt=salt,
            length=dkLen,
            n=n,
            r=r,
            p=p,
        )
        return kdf.derive(password)

    @staticmethod
    def derive_key_from_password(
        password: str,
        salt: Optional[bytes] = None,
        kdf_type: str = "scrypt",
        dkLen: int = 32,
    ) -> Tuple[bytes, bytes]:
        """从密码派生密钥。

        便捷方法，自动生成盐值并使用推荐的KDF参数。

        Args:
            password: 密码字符串
            salt: 盐值，可选，不提供则自动生成
            kdf_type: KDF类型，支持scrypt, pbkdf2, hkdf，默认为scrypt
            dkLen: 派生密钥长度（字节），默认为32

        Returns:
            (派生密钥, 盐值) 元组

        Raises:
            ValueError: 当kdf_type不支持时
        """
        password_bytes = password.encode("utf-8")
        if salt is None:
            salt = generate_salt(16)

        if kdf_type == "scrypt":
            key = KDF.scrypt(password_bytes, salt, dkLen=dkLen)
        elif kdf_type == "pbkdf2":
            key = KDF.pbkdf2_hmac(password_bytes, salt, dkLen=dkLen)
        elif kdf_type == "hkdf":
            key = KDF.hkdf(password_bytes, salt=salt, length=dkLen)
        else:
            raise ValueError(f"不支持的KDF类型: {kdf_type}")

        return key, salt

    @staticmethod
    def verify_password(
        password: str,
        salt: bytes,
        expected_key: bytes,
        kdf_type: str = "scrypt",
    ) -> bool:
        """验证密码是否匹配。

        Args:
            password: 密码字符串
            salt: 盐值
            expected_key: 期望的密钥
            kdf_type: KDF类型，默认为scrypt

        Returns:
            匹配返回True，否则返回False
        """
        password_bytes = password.encode("utf-8")
        dkLen = len(expected_key)

        try:
            if kdf_type == "scrypt":
                actual_key = KDF.scrypt(password_bytes, salt, dkLen=dkLen)
            elif kdf_type == "pbkdf2":
                actual_key = KDF.pbkdf2_hmac(
                    password_bytes, salt, dkLen=dkLen
                )
            elif kdf_type == "hkdf":
                actual_key = KDF.hkdf(
                    password_bytes, salt=salt, length=dkLen
                )
            else:
                return False

            return actual_key == expected_key
        except Exception:
            return False

    @staticmethod
    def _get_hash_algorithm(hash_alg: str) -> hashes.HashAlgorithm:
        """获取哈希算法对象。

        Args:
            hash_alg: 哈希算法名称

        Returns:
            哈希算法对象

        Raises:
            ValueError: 当哈希算法不支持时
        """
        hash_map = {
            "sha256": hashes.SHA256(),
            "sha512": hashes.SHA512(),
            "sha3_256": hashes.SHA3_256(),
            "sha3_512": hashes.SHA3_512(),
            "sha224": hashes.SHA224(),
            "sha384": hashes.SHA384(),
            "sha1": hashes.SHA1(),
            "md5": hashes.MD5(),
        }
        if hash_alg not in hash_map:
            raise ValueError(f"不支持的哈希算法: {hash_alg}")
        return hash_map[hash_alg]
