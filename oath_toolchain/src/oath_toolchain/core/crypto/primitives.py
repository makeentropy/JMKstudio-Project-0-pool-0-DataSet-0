"""密码学原语封装模块。

提供AES、RSA、椭圆曲线等密码学原语的高级封装。
"""
from __future__ import annotations

from typing import Optional, Tuple, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidSignature

from ..exceptions import EncryptionError


class AESCipher:
    """AES-GCM加密类。

    提供AES-GCM模式的对称加密和解密功能。
    """

    NONCE_SIZE = 12
    TAG_SIZE = 16

    @staticmethod
    def encrypt(
        plaintext: bytes,
        key: bytes,
        associated_data: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes, bytes]:
        """使用AES-GCM加密数据。

        Args:
            plaintext: 明文数据
            key: 加密密钥（16、24或32字节，对应AES-128/192/256）
            associated_data: 关联数据（认证但不加密），可选
            nonce: 随机数（12字节），不提供则自动生成

        Returns:
            (密文, nonce, 认证标签) 元组

        Raises:
            EncryptionError: 当加密失败时
            ValueError: 当密钥长度无效时
        """
        if len(key) not in (16, 24, 32):
            raise ValueError(
                "密钥长度必须是16、24或32字节（对应AES-128/192/256）"
            )

        try:
            if nonce is None:
                from .random import get_random_bytes

                nonce = get_random_bytes(AESCipher.NONCE_SIZE)

            if len(nonce) != AESCipher.NONCE_SIZE:
                raise ValueError(
                    f"nonce长度必须是{AESCipher.NONCE_SIZE}字节"
                )

            aesgcm = AESGCM(key)
            ciphertext_with_tag = aesgcm.encrypt(
                nonce, plaintext, associated_data
            )

            ciphertext = ciphertext_with_tag[: -AESCipher.TAG_SIZE]
            tag = ciphertext_with_tag[-AESCipher.TAG_SIZE :]

            return ciphertext, nonce, tag
        except Exception as e:
            raise EncryptionError(operation="encrypt", message=str(e)) from e

    @staticmethod
    def decrypt(
        ciphertext: bytes,
        key: bytes,
        nonce: bytes,
        tag: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """使用AES-GCM解密数据。

        Args:
            ciphertext: 密文数据
            key: 解密密钥
            nonce: 随机数
            tag: 认证标签
            associated_data: 关联数据（认证但不加密），可选

        Returns:
            明文数据

        Raises:
            EncryptionError: 当解密或认证失败时
        """
        try:
            aesgcm = AESGCM(key)
            ciphertext_with_tag = ciphertext + tag
            plaintext = aesgcm.decrypt(
                nonce, ciphertext_with_tag, associated_data
            )
            return plaintext
        except Exception as e:
            raise EncryptionError(operation="decrypt", message=str(e)) from e

    @staticmethod
    def generate_key(key_size: int = 256) -> bytes:
        """生成AES密钥。

        Args:
            key_size: 密钥位数（128、192或256），默认为256

        Returns:
            密钥字节

        Raises:
            ValueError: 当密钥大小无效时
        """
        if key_size not in (128, 192, 256):
            raise ValueError("密钥大小必须是128、192或256位")
        from .random import get_random_bytes

        return get_random_bytes(key_size // 8)


class RSACipher:
    """RSA加密类。

    提供RSA非对称加密、解密、签名和验证功能。
    """

    @staticmethod
    def generate_keypair(
        key_size: int = 4096,
        public_exponent: int = 65537,
    ) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """生成RSA密钥对。

        Args:
            key_size: 密钥大小（位），默认为4096
            public_exponent: 公钥指数，默认为65537

        Returns:
            (私钥, 公钥) 元组

        Raises:
            ValueError: 当密钥大小无效时
        """
        if key_size < 2048:
            raise ValueError("RSA密钥大小至少为2048位")
        if public_exponent not in (3, 65537):
            raise ValueError("公钥指数必须是3或65537")

        private_key = rsa.generate_private_key(
            public_exponent=public_exponent,
            key_size=key_size,
        )
        public_key = private_key.public_key()
        return private_key, public_key

    @staticmethod
    def encrypt(
        plaintext: bytes,
        public_key: rsa.RSAPublicKey,
    ) -> bytes:
        """使用RSA-OAEP加密数据。

        Args:
            plaintext: 明文数据
            public_key: RSA公钥

        Returns:
            密文数据

        Raises:
            EncryptionError: 当加密失败时
        """
        try:
            ciphertext = public_key.encrypt(
                plaintext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            return ciphertext
        except Exception as e:
            raise EncryptionError(operation="encrypt", message=str(e)) from e

    @staticmethod
    def decrypt(
        ciphertext: bytes,
        private_key: rsa.RSAPrivateKey,
    ) -> bytes:
        """使用RSA-OAEP解密数据。

        Args:
            ciphertext: 密文数据
            private_key: RSA私钥

        Returns:
            明文数据

        Raises:
            EncryptionError: 当解密失败时
        """
        try:
            plaintext = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            return plaintext
        except Exception as e:
            raise EncryptionError(operation="decrypt", message=str(e)) from e

    @staticmethod
    def sign(
        data: bytes,
        private_key: rsa.RSAPrivateKey,
    ) -> bytes:
        """使用RSA-PSS签名数据。

        Args:
            data: 待签名的数据
            private_key: RSA私钥

        Returns:
            签名数据

        Raises:
            EncryptionError: 当签名失败时
        """
        try:
            signature = private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return signature
        except Exception as e:
            raise EncryptionError(operation="sign", message=str(e)) from e

    @staticmethod
    def verify(
        data: bytes,
        signature: bytes,
        public_key: rsa.RSAPublicKey,
    ) -> bool:
        """验证RSA-PSS签名。

        Args:
            data: 原始数据
            signature: 签名数据
            public_key: RSA公钥

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    @staticmethod
    def serialize_public_key(public_key: rsa.RSAPublicKey) -> bytes:
        """序列化公钥为PEM格式。

        Args:
            public_key: RSA公钥

        Returns:
            PEM格式的公钥字节
        """
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    @staticmethod
    def deserialize_public_key(pem_data: bytes) -> rsa.RSAPublicKey:
        """从PEM格式反序列化公钥。

        Args:
            pem_data: PEM格式的公钥字节

        Returns:
            RSA公钥对象

        Raises:
            ValueError: 当公钥格式无效时
        """
        try:
            public_key = serialization.load_pem_public_key(pem_data)
            if not isinstance(public_key, rsa.RSAPublicKey):
                raise ValueError("不是有效的RSA公钥")
            return public_key
        except Exception as e:
            raise ValueError(f"公钥反序列化失败: {e}") from e

    @staticmethod
    def serialize_private_key(
        private_key: rsa.RSAPrivateKey,
        password: Optional[bytes] = None,
    ) -> bytes:
        """序列化私钥为PEM格式。

        Args:
            private_key: RSA私钥
            password: 加密密码，可选

        Returns:
            PEM格式的私钥字节
        """
        encryption_algorithm = (
            serialization.BestAvailableEncryption(password)
            if password
            else serialization.NoEncryption()
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption_algorithm,
        )

    @staticmethod
    def deserialize_private_key(
        pem_data: bytes,
        password: Optional[bytes] = None,
    ) -> rsa.RSAPrivateKey:
        """从PEM格式反序列化私钥。

        Args:
            pem_data: PEM格式的私钥字节
            password: 解密密码，可选

        Returns:
            RSA私钥对象

        Raises:
            ValueError: 当私钥格式无效时
        """
        try:
            private_key = serialization.load_pem_private_key(
                pem_data, password=password
            )
            if not isinstance(private_key, rsa.RSAPrivateKey):
                raise ValueError("不是有效的RSA私钥")
            return private_key
        except Exception as e:
            raise ValueError(f"私钥反序列化失败: {e}") from e


class ECCipher:
    """椭圆曲线加密类。

    提供ECDH密钥交换和ECDSA签名功能。
    """

    @staticmethod
    def generate_keypair(
        curve: ec.EllipticCurve = None,
    ) -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """生成椭圆曲线密钥对。

        Args:
            curve: 椭圆曲线，默认为SECP256R1

        Returns:
            (私钥, 公钥) 元组
        """
        if curve is None:
            curve = ec.SECP256R1()

        private_key = ec.generate_private_key(curve)
        public_key = private_key.public_key()
        return private_key, public_key

    @staticmethod
    def derive_shared_key(
        private_key: ec.EllipticCurvePrivateKey,
        peer_public_key: ec.EllipticCurvePublicKey,
        length: int = 32,
    ) -> bytes:
        """使用ECDH派生共享密钥。

        Args:
            private_key: 己方私钥
            peer_public_key: 对方公钥
            length: 派生密钥长度（字节），默认为32

        Returns:
            共享密钥

        Raises:
            EncryptionError: 当密钥派生失败时
        """
        try:
            shared_secret = private_key.exchange(
                ec.ECDH(), peer_public_key
            )
            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=length,
                salt=None,
                info=b"ecdh derived key",
            ).derive(shared_secret)
            return derived_key
        except Exception as e:
            raise EncryptionError(
                operation="derive_shared_key", message=str(e)
            ) from e

    @staticmethod
    def sign(
        data: bytes,
        private_key: ec.EllipticCurvePrivateKey,
    ) -> bytes:
        """使用ECDSA签名数据。

        Args:
            data: 待签名的数据
            private_key: 椭圆曲线私钥

        Returns:
            签名数据

        Raises:
            EncryptionError: 当签名失败时
        """
        try:
            signature = private_key.sign(
                data,
                ec.ECDSA(hashes.SHA256()),
            )
            return signature
        except Exception as e:
            raise EncryptionError(operation="sign", message=str(e)) from e

    @staticmethod
    def verify(
        data: bytes,
        signature: bytes,
        public_key: ec.EllipticCurvePublicKey,
    ) -> bool:
        """验证ECDSA签名。

        Args:
            data: 原始数据
            signature: 签名数据
            public_key: 椭圆曲线公钥

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            public_key.verify(
                signature,
                data,
                ec.ECDSA(hashes.SHA256()),
            )
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    @staticmethod
    def serialize_public_key(
        public_key: ec.EllipticCurvePublicKey,
    ) -> bytes:
        """序列化公钥为PEM格式。

        Args:
            public_key: 椭圆曲线公钥

        Returns:
            PEM格式的公钥字节
        """
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    @staticmethod
    def deserialize_public_key(
        pem_data: bytes,
    ) -> ec.EllipticCurvePublicKey:
        """从PEM格式反序列化公钥。

        Args:
            pem_data: PEM格式的公钥字节

        Returns:
            椭圆曲线公钥对象

        Raises:
            ValueError: 当公钥格式无效时
        """
        try:
            public_key = serialization.load_pem_public_key(pem_data)
            if not isinstance(public_key, ec.EllipticCurvePublicKey):
                raise ValueError("不是有效的椭圆曲线公钥")
            return public_key
        except Exception as e:
            raise ValueError(f"公钥反序列化失败: {e}") from e

    @staticmethod
    def serialize_private_key(
        private_key: ec.EllipticCurvePrivateKey,
        password: Optional[bytes] = None,
    ) -> bytes:
        """序列化私钥为PEM格式。

        Args:
            private_key: 椭圆曲线私钥
            password: 加密密码，可选

        Returns:
            PEM格式的私钥字节
        """
        encryption_algorithm = (
            serialization.BestAvailableEncryption(password)
            if password
            else serialization.NoEncryption()
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption_algorithm,
        )

    @staticmethod
    def deserialize_private_key(
        pem_data: bytes,
        password: Optional[bytes] = None,
    ) -> ec.EllipticCurvePrivateKey:
        """从PEM格式反序列化私钥。

        Args:
            pem_data: PEM格式的私钥字节
            password: 解密密码，可选

        Returns:
            椭圆曲线私钥对象

        Raises:
            ValueError: 当私钥格式无效时
        """
        try:
            private_key = serialization.load_pem_private_key(
                pem_data, password=password
            )
            if not isinstance(private_key, ec.EllipticCurvePrivateKey):
                raise ValueError("不是有效的椭圆曲线私钥")
            return private_key
        except Exception as e:
            raise ValueError(f"私钥反序列化失败: {e}") from e
