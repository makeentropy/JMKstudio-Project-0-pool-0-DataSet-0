"""
GPG加密模块

提供基于GPG风格的字典数据加密和解密功能。
支持对称加密、非对称加密和混合加密模式。
"""

import base64
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class EncryptionMode(Enum):
    """加密模式枚举"""
    SYMMETRIC = "symmetric"  # 对称加密
    ASYMMETRIC = "asymmetric"  # 非对称加密
    HYBRID = "hybrid"  # 混合加密


@dataclass
class GPGKey:
    """GPG密钥数据类"""
    key_id: str
    key_type: str  # 'public' or 'private'
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    algorithm: str = "RSA-4096"
    key_data: bytes = b""
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key_id": self.key_id,
            "key_type": self.key_type,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "algorithm": self.algorithm,
            "key_data": base64.b64encode(self.key_data).decode("utf-8"),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GPGKey":
        """从字典创建"""
        return cls(
            key_id=data["key_id"],
            key_type=data["key_type"],
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            algorithm=data.get("algorithm", "RSA-4096"),
            key_data=base64.b64decode(data["key_data"]),
            fingerprint=data.get("fingerprint", ""),
        )


@dataclass
class EncryptedData:
    """加密数据结构"""
    version: int = 1
    mode: str = "hybrid"
    key_id: str = ""
    encrypted_key: Optional[bytes] = None  # 加密的对称密钥（混合模式）
    iv: bytes = b""
    tag: bytes = b""
    ciphertext: bytes = b""
    signature: Optional[bytes] = None
    timestamp: float = field(default_factory=time.time)
    compression: bool = False
    compression_algo: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "mode": self.mode,
            "key_id": self.key_id,
            "encrypted_key": base64.b64encode(self.encrypted_key).decode("utf-8") if self.encrypted_key else None,
            "iv": base64.b64encode(self.iv).decode("utf-8"),
            "tag": base64.b64encode(self.tag).decode("utf-8"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("utf-8"),
            "signature": base64.b64encode(self.signature).decode("utf-8") if self.signature else None,
            "timestamp": self.timestamp,
            "compression": self.compression,
            "compression_algo": self.compression_algo,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedData":
        """从字典创建"""
        return cls(
            version=data.get("version", 1),
            mode=data.get("mode", "hybrid"),
            key_id=data.get("key_id", ""),
            encrypted_key=base64.b64decode(data["encrypted_key"]) if data.get("encrypted_key") else None,
            iv=base64.b64decode(data["iv"]),
            tag=base64.b64decode(data["tag"]),
            ciphertext=base64.b64decode(data["ciphertext"]),
            signature=base64.b64decode(data["signature"]) if data.get("signature") else None,
            timestamp=data.get("timestamp", time.time()),
            compression=data.get("compression", False),
            compression_algo=data.get("compression_algo", "none"),
        )

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "EncryptedData":
        """从JSON字符串创建"""
        return cls.from_dict(json.loads(json_str))


class GPGKeyManager:
    """
    GPG密钥管理器

    负责密钥的生成、存储和管理。
    """

    def __init__(self, key_size: int = 4096):
        """
        初始化密钥管理器

        Args:
            key_size: RSA密钥大小（位）
        """
        self.key_size = key_size
        self._keys: Dict[str, GPGKey] = {}

    def generate_key_pair(self, key_id: Optional[str] = None) -> tuple[GPGKey, GPGKey]:
        """
        生成RSA密钥对

        Args:
            key_id: 密钥ID，如不提供则自动生成

        Returns:
            (私钥, 公钥) 元组
        """
        if key_id is None:
            key_id = self._generate_key_id()

        # 生成RSA密钥对
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        # 序列化密钥
        private_key_data = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_key_data = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # 计算指纹
        fingerprint = self._calculate_fingerprint(public_key_data)

        # 创建密钥对象
        private_gpg_key = GPGKey(
            key_id=key_id,
            key_type="private",
            key_data=private_key_data,
            fingerprint=fingerprint,
        )

        public_gpg_key = GPGKey(
            key_id=key_id,
            key_type="public",
            key_data=public_key_data,
            fingerprint=fingerprint,
        )

        # 存储密钥
        self._keys[f"{key_id}_private"] = private_gpg_key
        self._keys[f"{key_id}_public"] = public_gpg_key

        logger.info(f"生成密钥对: {key_id}, 指纹: {fingerprint[:16]}...")
        return private_gpg_key, public_gpg_key

    def _generate_key_id(self) -> str:
        """生成唯一的密钥ID"""
        return secrets.token_hex(8).upper()

    def _calculate_fingerprint(self, key_data: bytes) -> str:
        """计算密钥指纹"""
        import hashlib
        return hashlib.sha256(key_data).hexdigest()

    def get_key(self, key_id: str, key_type: str) -> Optional[GPGKey]:
        """
        获取密钥

        Args:
            key_id: 密钥ID
            key_type: 密钥类型 ('public' 或 'private')

        Returns:
            GPGKey对象或None
        """
        return self._keys.get(f"{key_id}_{key_type}")

    def import_key(self, key_data: bytes, key_type: str, key_id: Optional[str] = None) -> GPGKey:
        """
        导入密钥

        Args:
            key_data: 密钥数据（PEM格式）
            key_type: 密钥类型 ('public' 或 'private')
            key_id: 密钥ID，如不提供则自动生成

        Returns:
            GPGKey对象
        """
        if key_id is None:
            key_id = self._generate_key_id()

        fingerprint = self._calculate_fingerprint(key_data)

        gpg_key = GPGKey(
            key_id=key_id,
            key_type=key_type,
            key_data=key_data,
            fingerprint=fingerprint,
        )

        self._keys[f"{key_id}_{key_type}"] = gpg_key
        logger.info(f"导入{key_type}密钥: {key_id}")
        return gpg_key

    def export_key(self, key_id: str, key_type: str) -> Optional[bytes]:
        """
        导出密钥

        Args:
            key_id: 密钥ID
            key_type: 密钥类型

        Returns:
            密钥数据（PEM格式）或None
        """
        key = self.get_key(key_id, key_type)
        if key:
            return key.key_data
        return None

    def delete_key(self, key_id: str, key_type: str) -> bool:
        """
        删除密钥

        Args:
            key_id: 密钥ID
            key_type: 密钥类型

        Returns:
            是否删除成功
        """
        key_key = f"{key_id}_{key_type}"
        if key_key in self._keys:
            del self._keys[key_key]
            logger.info(f"删除{key_type}密钥: {key_id}")
            return True
        return False

    def list_keys(self) -> List[Dict[str, Any]]:
        """列出所有密钥"""
        return [key.to_dict() for key in self._keys.values()]


class GPGDictionaryEncryptor:
    """
    GPG字典加密器

    专门用于加密和解密字典数据，支持多种加密模式。
    """

    def __init__(self, key_manager: Optional[GPGKeyManager] = None):
        """
        初始化加密器

        Args:
            key_manager: 密钥管理器，如不提供则创建新的
        """
        self.key_manager = key_manager or GPGKeyManager()

    def encrypt_dict(
        self,
        data: Dict[str, Any],
        public_key_id: str,
        mode: EncryptionMode = EncryptionMode.HYBRID,
        sign_with_key_id: Optional[str] = None,
    ) -> EncryptedData:
        """
        加密字典数据

        Args:
            data: 要加密的字典数据
            public_key_id: 用于加密的公钥ID
            mode: 加密模式
            sign_with_key_id: 用于签名的私钥ID（可选）

        Returns:
            EncryptedData对象
        """
        # 序列化数据
        json_data = json.dumps(data, ensure_ascii=False, sort_keys=True)
        plaintext = json_data.encode("utf-8")

        if mode == EncryptionMode.SYMMETRIC:
            return self._encrypt_symmetric(plaintext, public_key_id, sign_with_key_id)
        elif mode == EncryptionMode.ASYMMETRIC:
            return self._encrypt_asymmetric(plaintext, public_key_id, sign_with_key_id)
        else:  # HYBRID
            return self._encrypt_hybrid(plaintext, public_key_id, sign_with_key_id)

    def _encrypt_symmetric(
        self,
        plaintext: bytes,
        key_id: str,
        sign_with_key_id: Optional[str] = None,
    ) -> EncryptedData:
        """对称加密"""
        # 获取对称密钥
        key = self.key_manager.get_key(key_id, "private")
        if not key:
            raise ValueError(f"密钥不存在: {key_id}")

        # 从密钥数据派生对称密钥
        symmetric_key = self._derive_symmetric_key(key.key_data)

        # 加密
        iv = os.urandom(12)
        cipher = Cipher(algorithms.AES(symmetric_key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        # 签名（如果需要）
        signature = None
        if sign_with_key_id:
            signature = self._sign_data(plaintext, sign_with_key_id)

        return EncryptedData(
            mode="symmetric",
            key_id=key_id,
            iv=iv,
            tag=encryptor.tag,
            ciphertext=ciphertext,
            signature=signature,
        )

    def _encrypt_asymmetric(
        self,
        plaintext: bytes,
        public_key_id: str,
        sign_with_key_id: Optional[str] = None,
    ) -> EncryptedData:
        """非对称加密"""
        # 获取公钥
        public_key_gpg = self.key_manager.get_key(public_key_id, "public")
        if not public_key_gpg:
            raise ValueError(f"公钥不存在: {public_key_id}")

        public_key = serialization.load_pem_public_key(
            public_key_gpg.key_data, backend=default_backend()
        )

        # RSA加密
        ciphertext = public_key.encrypt(
            plaintext,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 签名
        signature = None
        if sign_with_key_id:
            signature = self._sign_data(plaintext, sign_with_key_id)

        return EncryptedData(
            mode="asymmetric",
            key_id=public_key_id,
            iv=b"",
            tag=b"",
            ciphertext=ciphertext,
            signature=signature,
        )

    def _encrypt_hybrid(
        self,
        plaintext: bytes,
        public_key_id: str,
        sign_with_key_id: Optional[str] = None,
    ) -> EncryptedData:
        """混合加密（RSA + AES）"""
        # 生成随机的对称密钥
        symmetric_key = os.urandom(32)

        # 获取公钥
        public_key_gpg = self.key_manager.get_key(public_key_id, "public")
        if not public_key_gpg:
            raise ValueError(f"公钥不存在: {public_key_id}")

        public_key = serialization.load_pem_public_key(
            public_key_gpg.key_data, backend=default_backend()
        )

        # 使用RSA加密对称密钥
        encrypted_key = public_key.encrypt(
            symmetric_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 使用AES-GCM加密数据
        iv = os.urandom(12)
        cipher = Cipher(algorithms.AES(symmetric_key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        # 签名
        signature = None
        if sign_with_key_id:
            signature = self._sign_data(plaintext, sign_with_key_id)

        return EncryptedData(
            mode="hybrid",
            key_id=public_key_id,
            encrypted_key=encrypted_key,
            iv=iv,
            tag=encryptor.tag,
            ciphertext=ciphertext,
            signature=signature,
        )

    def decrypt_dict(
        self,
        encrypted_data: EncryptedData,
        private_key_id: str,
        verify_with_key_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        解密字典数据

        Args:
            encrypted_data: 加密数据
            private_key_id: 用于解密的私钥ID
            verify_with_key_id: 用于验证签名的公钥ID（可选）

        Returns:
            解密后的字典数据
        """
        if encrypted_data.mode == "symmetric":
            plaintext = self._decrypt_symmetric(encrypted_data, private_key_id)
        elif encrypted_data.mode == "asymmetric":
            plaintext = self._decrypt_asymmetric(encrypted_data, private_key_id)
        else:  # hybrid
            plaintext = self._decrypt_hybrid(encrypted_data, private_key_id)

        # 验证签名
        if encrypted_data.signature and verify_with_key_id:
            if not self._verify_signature(plaintext, encrypted_data.signature, verify_with_key_id):
                raise ValueError("签名验证失败")

        # 反序列化
        json_data = plaintext.decode("utf-8")
        return json.loads(json_data)

    def _decrypt_symmetric(self, encrypted_data: EncryptedData, key_id: str) -> bytes:
        """对称解密"""
        key = self.key_manager.get_key(key_id, "private")
        if not key:
            raise ValueError(f"密钥不存在: {key_id}")

        symmetric_key = self._derive_symmetric_key(key.key_data)

        cipher = Cipher(
            algorithms.AES(symmetric_key),
            modes.GCM(encrypted_data.iv, encrypted_data.tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()

    def _decrypt_asymmetric(self, encrypted_data: EncryptedData, private_key_id: str) -> bytes:
        """非对称解密"""
        private_key_gpg = self.key_manager.get_key(private_key_id, "private")
        if not private_key_gpg:
            raise ValueError(f"私钥不存在: {private_key_id}")

        private_key = serialization.load_pem_private_key(
            private_key_gpg.key_data, password=None, backend=default_backend()
        )

        return private_key.decrypt(
            encrypted_data.ciphertext,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def _decrypt_hybrid(self, encrypted_data: EncryptedData, private_key_id: str) -> bytes:
        """混合解密"""
        if not encrypted_data.encrypted_key:
            raise ValueError("缺少加密的密钥")

        private_key_gpg = self.key_manager.get_key(private_key_id, "private")
        if not private_key_gpg:
            raise ValueError(f"私钥不存在: {private_key_id}")

        private_key = serialization.load_pem_private_key(
            private_key_gpg.key_data, password=None, backend=default_backend()
        )

        # 解密对称密钥
        symmetric_key = private_key.decrypt(
            encrypted_data.encrypted_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 使用AES-GCM解密数据
        cipher = Cipher(
            algorithms.AES(symmetric_key),
            modes.GCM(encrypted_data.iv, encrypted_data.tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()

    def _derive_symmetric_key(self, key_data: bytes) -> bytes:
        """从密钥数据派生对称密钥"""
        import hashlib
        return hashlib.sha256(key_data).digest()

    def _sign_data(self, data: bytes, private_key_id: str) -> bytes:
        """使用私钥签名数据"""
        private_key_gpg = self.key_manager.get_key(private_key_id, "private")
        if not private_key_gpg:
            raise ValueError(f"私钥不存在: {private_key_id}")

        private_key = serialization.load_pem_private_key(
            private_key_gpg.key_data, password=None, backend=default_backend()
        )

        signature = private_key.sign(
            data,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return signature

    def _verify_signature(self, data: bytes, signature: bytes, public_key_id: str) -> bool:
        """使用公钥验证签名"""
        public_key_gpg = self.key_manager.get_key(public_key_id, "public")
        if not public_key_gpg:
            raise ValueError(f"公钥不存在: {public_key_id}")

        public_key = serialization.load_pem_public_key(
            public_key_gpg.key_data, backend=default_backend()
        )

        try:
            public_key.verify(
                signature,
                data,
                asym_padding.PSS(
                    mgf=asym_padding.MGF1(hashes.SHA256()),
                    salt_length=asym_padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def encrypt_dict_to_json(
        self,
        data: Dict[str, Any],
        public_key_id: str,
        mode: EncryptionMode = EncryptionMode.HYBRID,
        sign_with_key_id: Optional[str] = None,
    ) -> str:
        """
        加密字典数据并返回JSON字符串

        Args:
            data: 要加密的字典数据
            public_key_id: 用于加密的公钥ID
            mode: 加密模式
            sign_with_key_id: 用于签名的私钥ID（可选）

        Returns:
            JSON格式的加密数据
        """
        encrypted_data = self.encrypt_dict(data, public_key_id, mode, sign_with_key_id)
        return encrypted_data.to_json()

    def decrypt_dict_from_json(
        self,
        json_str: str,
        private_key_id: str,
        verify_with_key_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        从JSON字符串解密字典数据

        Args:
            json_str: JSON格式的加密数据
            private_key_id: 用于解密的私钥ID
            verify_with_key_id: 用于验证签名的公钥ID（可选）

        Returns:
            解密后的字典数据
        """
        encrypted_data = EncryptedData.from_json(json_str)
        return self.decrypt_dict(encrypted_data, private_key_id, verify_with_key_id)


class SecureDictionaryStorage:
    """
    安全字典存储

    提供字典数据的加密存储和检索功能。
    """

    def __init__(self, encryptor: Optional[GPGDictionaryEncryptor] = None):
        """
        初始化安全存储

        Args:
            encryptor: GPG字典加密器
        """
        self.encryptor = encryptor or GPGDictionaryEncryptor()
        self._storage: Dict[str, str] = {}  # 存储加密后的数据

    def store(
        self,
        key: str,
        data: Dict[str, Any],
        public_key_id: str,
        mode: EncryptionMode = EncryptionMode.HYBRID,
        sign_with_key_id: Optional[str] = None,
    ) -> None:
        """
        安全存储字典数据

        Args:
            key: 存储键名
            data: 要存储的字典数据
            public_key_id: 用于加密的公钥ID
            mode: 加密模式
            sign_with_key_id: 用于签名的私钥ID（可选）
        """
        encrypted_json = self.encryptor.encrypt_dict_to_json(
            data, public_key_id, mode, sign_with_key_id
        )
        self._storage[key] = encrypted_json
        logger.info(f"安全存储数据: {key}")

    def retrieve(
        self,
        key: str,
        private_key_id: str,
        verify_with_key_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        检索并解密字典数据

        Args:
            key: 存储键名
            private_key_id: 用于解密的私钥ID
            verify_with_key_id: 用于验证签名的公钥ID（可选）

        Returns:
            解密后的字典数据或None
        """
        encrypted_json = self._storage.get(key)
        if not encrypted_json:
            return None

        try:
            data = self.encryptor.decrypt_dict_from_json(
                encrypted_json, private_key_id, verify_with_key_id
            )
            logger.info(f"检索并解密数据: {key}")
            return data
        except Exception as e:
            logger.error(f"解密数据失败: {key}, 错误: {e}")
            return None

    def delete(self, key: str) -> bool:
        """
        删除存储的数据

        Args:
            key: 存储键名

        Returns:
            是否删除成功
        """
        if key in self._storage:
            del self._storage[key]
            logger.info(f"删除存储数据: {key}")
            return True
        return False

    def list_keys(self) -> List[str]:
        """列出所有存储的键"""
        return list(self._storage.keys())

    def export_storage(self) -> Dict[str, str]:
        """导出所有加密数据"""
        return self._storage.copy()

    def import_storage(self, data: Dict[str, str]) -> None:
        """导入加密数据"""
        self._storage.update(data)
        logger.info(f"导入{len(data)}条加密数据")