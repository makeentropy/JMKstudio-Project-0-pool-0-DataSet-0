"""加密API模块。

提供对称加密、非对称加密、KARMACA空间加密、几何证明加密、
签名验证、哈希和HMAC等密码学功能的高层API。
"""
from __future__ import annotations

import base64
from typing import Any, Dict, Optional, Tuple

from ..core.crypto.primitives import AESCipher, RSACipher
from ..core.crypto.hash import Hash
from ..core.math.vector import Vector
from ..tools.karmaca.encryption import KarmacaEncryption
from ..tools.karmaca.space_dict import KarmaSpaceDict
from ..tools.geometric_proof.geometric_hash import GeometricHash
from ..tools.geometric_proof.proof_generator import GeometricProof


class CryptoAPI:
    """加密API类。

    提供多种加密算法的统一高层接口，包括对称加密、非对称加密、
    KARMACA空间加密、几何证明加密、签名验证、哈希和HMAC等功能。

    Attributes:
        engine: 乾坤引擎实例
    """

    def __init__(self, engine: Any) -> None:
        """初始化加密API。

        Args:
            engine: 乾坤引擎实例
        """
        self._engine = engine
        self._karmaca = KarmacaEncryption()
        self._geometric_proof = GeometricProof(dimensions=4, hash_alg='sha256')

    def encrypt_aes(self, data: bytes, key: bytes) -> bytes:
        """使用AES-GCM加密数据。

        Args:
            data: 待加密的明文数据
            key: 加密密钥（16、24或32字节）

        Returns:
            加密后的数据，格式: nonce(12) + tag(16) + ciphertext

        Raises:
            ValueError: 当密钥长度无效时
            EncryptionError: 当加密失败时
        """
        ciphertext, nonce, tag = AESCipher.encrypt(data, key)
        return nonce + tag + ciphertext

    def decrypt_aes(self, data: bytes, key: bytes) -> bytes:
        """使用AES-GCM解密数据。

        Args:
            data: 加密数据，格式: nonce(12) + tag(16) + ciphertext
            key: 解密密钥

        Returns:
            解密后的明文数据

        Raises:
            EncryptionError: 当解密或认证失败时
        """
        nonce = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]
        return AESCipher.decrypt(ciphertext, key, nonce, tag)

    def encrypt_rsa(self, data: bytes, public_key: bytes) -> bytes:
        """使用RSA-OAEP加密数据。

        Args:
            data: 待加密的明文数据
            public_key: PEM格式的公钥字节

        Returns:
            加密后的密文数据

        Raises:
            EncryptionError: 当加密失败时
        """
        pub_key = RSACipher.deserialize_public_key(public_key)
        return RSACipher.encrypt(data, pub_key)

    def decrypt_rsa(self, data: bytes, private_key: bytes) -> bytes:
        """使用RSA-OAEP解密数据。

        Args:
            data: 密文数据
            private_key: PEM格式的私钥字节

        Returns:
            解密后的明文数据

        Raises:
            EncryptionError: 当解密失败时
        """
        priv_key = RSACipher.deserialize_private_key(private_key)
        return RSACipher.decrypt(data, priv_key)

    def encrypt_karmaca(
        self,
        data: bytes,
        space_key: bytes,
        dimensions: int = 3,
    ) -> bytes:
        """使用KARMACA空间字典加密数据。

        Args:
            data: 待加密的明文数据
            space_key: 空间密钥（用于生成空间坐标）
            dimensions: 空间维度数，默认为3

        Returns:
            加密后的数据，格式: nonce(12) + tag(16) + ciphertext

        Raises:
            ValueError: 当参数无效时
            EncryptionError: 当加密失败时
        """
        coordinate_list = self._derive_coordinate(space_key, dimensions)
        coordinate = Vector(coordinate_list)
        space_dict = self._build_space_dict(space_key, dimensions)
        return self._karmaca.encrypt(data, coordinate, space_dict)

    def decrypt_karmaca(
        self,
        data: bytes,
        space_key: bytes,
        dimensions: int = 3,
    ) -> bytes:
        """使用KARMACA空间字典解密数据。

        Args:
            data: 加密数据
            space_key: 空间密钥（用于生成空间坐标）
            dimensions: 空间维度数，默认为3

        Returns:
            解密后的明文数据

        Raises:
            ValueError: 当参数无效时
            EncryptionError: 当解密失败时
        """
        coordinate_list = self._derive_coordinate(space_key, dimensions)
        coordinate = Vector(coordinate_list)
        space_dict = self._build_space_dict(space_key, dimensions)
        return self._karmaca.decrypt(data, coordinate, space_dict)

    def _build_space_dict(
        self,
        seed: bytes,
        dimensions: int,
        size: int = 50,
    ) -> KarmaSpaceDict:
        """从种子构建空间字典。

        Args:
            seed: 种子字节
            dimensions: 维度数
            size: 空间字典大小

        Returns:
            KarmaSpaceDict实例
        """
        space_dict = KarmaSpaceDict(dimensions=dimensions)
        points = []
        keys = []

        for i in range(size):
            point_coords = []
            for d in range(dimensions):
                h = Hash.sha256(seed + bytes([i]) + bytes([d]))
                val = int.from_bytes(h[:8], 'big') / (2 ** 64)
                point_coords.append(val)
            point = Vector(point_coords)
            key = Hash.sha256(seed + b"key_" + bytes([i]))[:32]
            points.append(point)
            keys.append(key)

        space_dict.build(points, keys)
        return space_dict

    def encrypt_geometric(self, data: bytes, key: bytes) -> Dict[str, Any]:
        """使用几何证明加密数据。

        先用AES加密数据，再生成几何证明。

        Args:
            data: 待加密的明文数据
            key: 加密密钥

        Returns:
            包含加密数据和证明的字典: {"data": bytes, "proof": dict}
        """
        encrypted = self.encrypt_aes(data, key)
        proof = self._geometric_proof.generate_proof(encrypted, key)
        return {
            "data": encrypted,
            "proof": proof,
        }

    def decrypt_geometric(
        self,
        data: bytes,
        proof: Dict[str, Any],
        key: bytes,
    ) -> bytes:
        """使用几何证明解密数据。

        先验证几何证明，再用AES解密数据。

        Args:
            data: 加密数据
            proof: 几何证明字典
            key: 解密密钥

        Returns:
            解密后的明文数据

        Raises:
            ValidationError: 当证明验证失败时
        """
        valid = self._geometric_proof.verify_proof(data, proof)
        if not valid:
            from ..core.exceptions import ValidationError
            raise ValidationError(
                field="proof",
                message="几何证明验证失败",
            )
        return self.decrypt_aes(data, key)

    def encrypt_full(self, data: bytes, config: Dict[str, Any]) -> Dict[str, Any]:
        """完整多层加密。

        按照配置进行多层加密，包括AES、RSA、KARMACA等。

        Args:
            data: 待加密的明文数据
            config: 加密配置字典，可包含：
                - aes_key: AES密钥
                - rsa_public_key: RSA公钥
                - space_key: KARMACA空间密钥
                - karmaca_dimensions: KARMACA维度数
                - use_geometric_proof: 是否使用几何证明

        Returns:
            包含各层加密结果的字典
        """
        result: Dict[str, Any] = {
            "layers": [],
            "final_data": data,
        }

        current_data = data

        if "aes_key" in config:
            aes_key = config["aes_key"]
            current_data = self.encrypt_aes(current_data, aes_key)
            result["layers"].append({"type": "aes", "key_used": True})

        if "space_key" in config:
            space_key = config["space_key"]
            dimensions = config.get("karmaca_dimensions", 3)
            current_data = self.encrypt_karmaca(current_data, space_key, dimensions)
            result["layers"].append({"type": "karmaca", "dimensions": dimensions})

        if config.get("use_geometric_proof", False) and "aes_key" in config:
            geo_result = self.encrypt_geometric(current_data, config["aes_key"])
            current_data = geo_result["data"]
            result["geometric_proof"] = geo_result["proof"]
            result["layers"].append({"type": "geometric_proof"})

        if "rsa_public_key" in config:
            rsa_pub = config["rsa_public_key"]
            if isinstance(rsa_pub, str):
                rsa_pub = rsa_pub.encode("utf-8")
            current_data = self.encrypt_rsa(current_data, rsa_pub)
            result["layers"].append({"type": "rsa"})

        result["final_data"] = current_data
        return result

    def decrypt_full(
        self,
        encrypted: Dict[str, Any],
        config: Dict[str, Any],
    ) -> bytes:
        """完整多层解密。

        按照加密的逆序进行多层解密。

        Args:
            encrypted: 加密结果字典
            config: 解密配置字典

        Returns:
            解密后的明文数据
        """
        current_data = encrypted.get("final_data", b"")
        layers = encrypted.get("layers", [])

        for layer in reversed(layers):
            layer_type = layer.get("type", "")

            if layer_type == "rsa":
                rsa_priv = config.get("rsa_private_key")
                if isinstance(rsa_priv, str):
                    rsa_priv = rsa_priv.encode("utf-8")
                current_data = self.decrypt_rsa(current_data, rsa_priv)

            elif layer_type == "geometric_proof":
                proof = encrypted.get("geometric_proof", {})
                aes_key = config.get("aes_key")
                current_data = self.decrypt_geometric(
                    current_data, proof, aes_key
                )

            elif layer_type == "karmaca":
                space_key = config.get("space_key")
                dimensions = layer.get("dimensions", 3)
                current_data = self.decrypt_karmaca(
                    current_data, space_key, dimensions
                )

            elif layer_type == "aes":
                aes_key = config.get("aes_key")
                current_data = self.decrypt_aes(current_data, aes_key)

        return current_data

    def sign(
        self,
        data: bytes,
        key: bytes,
        method: str = 'rsa',
    ) -> bytes:
        """对数据进行签名。

        Args:
            data: 待签名的数据
            key: 签名私钥（PEM格式）
            method: 签名方法，支持'rsa'、'ec'，默认为'rsa'

        Returns:
            签名数据

        Raises:
            EncryptionError: 当签名失败时
            ValueError: 当签名方法不支持时
        """
        if method == 'rsa':
            priv_key = RSACipher.deserialize_private_key(key)
            return RSACipher.sign(data, priv_key)
        else:
            raise ValueError(f"不支持的签名方法: {method}")

    def verify(
        self,
        data: bytes,
        signature: bytes,
        key: bytes,
        method: str = 'rsa',
    ) -> bool:
        """验证签名。

        Args:
            data: 原始数据
            signature: 签名数据
            key: 验证公钥（PEM格式）
            method: 签名方法，支持'rsa'、'ec'，默认为'rsa'

        Returns:
            验证通过返回True，否则返回False
        """
        if method == 'rsa':
            pub_key = RSACipher.deserialize_public_key(key)
            return RSACipher.verify(data, signature, pub_key)
        else:
            raise ValueError(f"不支持的签名方法: {method}")

    def hash(self, data: bytes, algorithm: str = 'sha256') -> bytes:
        """计算哈希值。

        Args:
            data: 输入数据
            algorithm: 哈希算法，支持sha256、sha512、sha3_256、sha3_512、
                blake2b、blake2s、md5，默认为sha256

        Returns:
            哈希值字节

        Raises:
            ValueError: 当哈希算法不支持时
        """
        hash_methods = {
            'sha256': Hash.sha256,
            'sha512': Hash.sha512,
            'sha3_256': Hash.sha3_256,
            'sha3_512': Hash.sha3_512,
            'blake2b': Hash.blake2b,
            'blake2s': Hash.blake2s,
            'md5': Hash.md5,
        }

        if algorithm not in hash_methods:
            raise ValueError(f"不支持的哈希算法: {algorithm}")

        return hash_methods[algorithm](data)

    def hmac(
        self,
        data: bytes,
        key: bytes,
        algorithm: str = 'sha256',
    ) -> bytes:
        """计算HMAC消息认证码。

        Args:
            data: 输入数据
            key: 密钥
            algorithm: 哈希算法，默认为sha256

        Returns:
            HMAC值字节
        """
        return Hash.hmac(key, data, algorithm)

    @staticmethod
    def _derive_coordinate(seed: bytes, dimensions: int) -> list:
        """从种子派生空间坐标。

        Args:
            seed: 种子字节
            dimensions: 维度数

        Returns:
            坐标列表
        """
        coordinate = []
        for i in range(dimensions):
            h = Hash.sha256(seed + bytes([i]))
            val = int.from_bytes(h[:8], 'big') / (2 ** 64)
            coordinate.append(val)
        return coordinate
