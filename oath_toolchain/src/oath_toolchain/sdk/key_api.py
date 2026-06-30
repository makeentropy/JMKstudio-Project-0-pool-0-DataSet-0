"""密钥API模块。

提供各种密钥生成、派生、转换和强度评估功能的高层API。
"""
from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional, Tuple

from ..core.crypto.primitives import AESCipher, RSACipher
from ..core.crypto.hash import Hash
from ..core.crypto.kdf import KDF
from ..core.crypto.random import get_random_bytes
from ..core.math.vector import Vector
from ..tools.nlptcmodel.key_generator import NLPTCKeyGenerator
from ..tools.nlptcmodel.strength_evaluator import KeyStrengthEvaluator
from ..tools.karmaca.space_dict import KarmaSpaceDict


class KeyAPI:
    """密钥API类。

    提供多种密钥生成、派生、转换和强度评估功能的统一接口。

    Attributes:
        engine: 乾坤引擎实例
    """

    def __init__(self, engine: Any) -> None:
        """初始化密钥API。

        Args:
            engine: 乾坤引擎实例
        """
        self._engine = engine
        self._nlptc_keygen = NLPTCKeyGenerator()
        self._strength_evaluator = KeyStrengthEvaluator()

    def generate_aes_key(self, bits: int = 256) -> bytes:
        """生成AES密钥。

        Args:
            bits: 密钥位数，支持128、192、256，默认为256

        Returns:
            AES密钥字节

        Raises:
            ValueError: 当密钥大小无效时
        """
        return AESCipher.generate_key(bits)

    def generate_rsa_key(self, bits: int = 2048) -> Tuple[bytes, bytes]:
        """生成RSA密钥对。

        Args:
            bits: 密钥位数，默认为2048

        Returns:
            (私钥PEM字节, 公钥PEM字节) 元组

        Raises:
            ValueError: 当密钥大小无效时
        """
        private_key, public_key = RSACipher.generate_keypair(key_size=bits)
        private_pem = RSACipher.serialize_private_key(private_key)
        public_pem = RSACipher.serialize_public_key(public_key)
        return private_pem, public_pem

    def generate_nlp_key(
        self,
        text: str,
        mode: str = 'hybrid',
        key_length: int = 32,
    ) -> bytes:
        """从自然语言文本生成密钥。

        Args:
            text: 输入文本
            mode: 密钥生成模式，支持'semantic'、'entropy'、'hybrid'，
                默认为'hybrid'
            key_length: 密钥长度（字节），默认为32

        Returns:
            生成的密钥字节

        Raises:
            ValueError: 当参数无效时
        """
        return self._nlptc_keygen.generate_key(
            text=text,
            key_size=key_length,
            mode=mode,
        )

    def generate_karmaca_key(
        self,
        seed: bytes = None,
        dimensions: int = 3,
    ) -> bytes:
        """生成KARMACA空间密钥。

        Args:
            seed: 种子字节，不提供则随机生成
            dimensions: 空间维度数，默认为3

        Returns:
            KARMACA空间密钥字节
        """
        if seed is None:
            seed = get_random_bytes(32)

        space_dict = KarmaSpaceDict(dimensions=dimensions)
        points = []
        keys = []
        for i in range(10):
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

        return seed

    def generate_combined_key(
        self,
        sources: List[Dict[str, Any]],
        key_length: int = 32,
    ) -> bytes:
        """生成组合密钥。

        从多个密钥源组合生成一个密钥。

        Args:
            sources: 密钥源列表，每个源是一个字典，包含：
                - type: 源类型 ('bytes', 'text', 'password')
                - value: 源值
                - weight: 权重（可选，默认为1）
            key_length: 输出密钥长度（字节），默认为32

        Returns:
            组合后的密钥字节
        """
        combined = b""
        for source in sources:
            source_type = source.get("type", "bytes")
            value = source.get("value", b"")
            weight = source.get("weight", 1)

            if source_type == "text":
                value_bytes = value.encode("utf-8") if isinstance(value, str) else value
            elif source_type == "password":
                value_bytes = KDF.pbkdf2_hmac(
                    password=value.encode("utf-8") if isinstance(value, str) else value,
                    salt=b"combined_key_salt",
                    iterations=10000,
                    dkLen=32,
                )
            else:
                value_bytes = value if isinstance(value, bytes) else str(value).encode("utf-8")

            for _ in range(weight):
                combined += value_bytes

        return KDF.hkdf(
            ikm=combined,
            salt=b"combined_key_salt",
            info=b"oath_sdk_combined_key",
            length=key_length,
        )

    def derive_key(
        self,
        password: str,
        salt: bytes = None,
        iterations: int = 100000,
    ) -> bytes:
        """从密码派生密钥。

        使用PBKDF2-HMAC-SHA256从密码派生密钥。

        Args:
            password: 密码字符串
            salt: 盐值，不提供则随机生成
            iterations: 迭代次数，默认为100000

        Returns:
            派生的密钥字节（32字节）
        """
        if salt is None:
            salt = get_random_bytes(16)

        return KDF.pbkdf2_hmac(
            password=password.encode("utf-8"),
            salt=salt,
            iterations=iterations,
            dkLen=32,
        )

    def key_to_base64(self, key: bytes) -> str:
        """将密钥转换为Base64编码字符串。

        Args:
            key: 密钥字节

        Returns:
            Base64编码的密钥字符串
        """
        return base64.b64encode(key).decode("utf-8")

    def key_from_base64(self, b64: str) -> bytes:
        """从Base64编码字符串解析密钥。

        Args:
            b64: Base64编码的密钥字符串

        Returns:
            密钥字节

        Raises:
            ValueError: 当Base64格式无效时
        """
        try:
            return base64.b64decode(b64)
        except Exception as e:
            raise ValueError(f"无效的Base64编码: {e}") from e

    def assess_key_strength(self, key: bytes) -> Dict[str, Any]:
        """评估密钥强度。

        Args:
            key: 待评估的密钥字节

        Returns:
            强度评估结果字典，包含：
                - score: 强度分数（0-100）
                - entropy: 熵值（位/字节）
                - length: 密钥长度（字节）
                - strength: 强度等级 ('weak', 'medium', 'strong', 'very_strong')
                - details: 详细评估信息
        """
        try:
            eval_result = self._strength_evaluator.evaluate(key)
            score = int(eval_result.get('strength_score', 0) * 100)
            level = eval_result.get('strength_level', 'weak')
            entropy = eval_result.get('entropy', 0)

            strength_map = {
                'very_weak': 'weak',
                'weak': 'weak',
                'medium': 'medium',
                'strong': 'strong',
                'very_strong': 'very_strong',
            }

            return {
                "score": score,
                "entropy": entropy * len(key),
                "length": len(key),
                "strength": strength_map.get(level, level),
                "details": eval_result,
            }
        except Exception:
            entropy = self._calculate_entropy(key)
            length = len(key)
            score = min(100, int((entropy / 256) * 100))

            if score < 40:
                strength = "weak"
            elif score < 65:
                strength = "medium"
            elif score < 85:
                strength = "strong"
            else:
                strength = "very_strong"

            return {
                "score": score,
                "entropy": entropy,
                "length": length,
                "strength": strength,
                "details": {
                    "byte_count": length,
                    "bit_count": length * 8,
                    "estimated_entropy": entropy,
                },
            }

    @staticmethod
    def _calculate_entropy(data: bytes) -> float:
        """计算数据的香农熵。

        Args:
            data: 输入数据

        Returns:
            熵值（位）
        """
        if not data:
            return 0.0

        freq = {}
        for byte in data:
            freq[byte] = freq.get(byte, 0) + 1

        length = len(data)
        entropy = 0.0
        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * (p.bit_length() - 1 if p > 0 else 0)

        return entropy * length
