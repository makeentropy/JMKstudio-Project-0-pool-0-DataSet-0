"""NLPTCmodel密钥生成器模块。

基于自然语言文本的语义特征和统计特征生成加密密钥，
支持多种密钥派生模式和强度评估。
"""
from __future__ import annotations

import base64
import struct
from typing import Any, Dict, Optional, Tuple

from ...core.base import OathTool
from ...core.crypto.hash import Hash
from ...core.crypto.kdf import KDF
from ...core.exceptions import ValidationError
from ...core.registry import register_tool
from .text_features import TextFeatureExtractor
from .strength_evaluator import KeyStrengthEvaluator


@register_tool
class NLPTCKeyGenerator(OathTool):
    """NLPTCmodel自然语言密钥生成器。

    基于自然语言文本的语义特征和统计特征生成加密密钥，
    支持semantic、entropy、hybrid三种密钥派生模式。

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
    """

    name: str = "nlptc_keygen"
    description: str = "NLPTCmodel自然语言密钥生成器"
    _version: str = "0.1.0"
    _tags: list[str] = ["crypto", "key-generation", "nlp", "nlptc"]
    _category: str = "crypto"

    def __init__(self) -> None:
        """初始化NLPTC密钥生成器。"""
        super().__init__()
        self._feature_extractor = TextFeatureExtractor()
        self._strength_evaluator = KeyStrengthEvaluator()

    def generate_key(
        self,
        text: str,
        key_size: int = 32,
        mode: str = 'hybrid',
        salt: Optional[bytes] = None,
        iterations: int = 100000,
    ) -> bytes:
        """从文本生成密钥。

        Args:
            text: 输入文本
            key_size: 密钥长度（字节），默认为32（256位）
            mode: 密钥生成模式，支持'semantic'、'entropy'、'hybrid'
            salt: 盐值，不提供则使用默认盐
            iterations: PBKDF2迭代次数，默认为100000

        Returns:
            生成的密钥字节

        Raises:
            ValueError: 当参数无效时
        """
        if not isinstance(text, str):
            raise TypeError("text必须是字符串类型")
        if not text:
            raise ValueError("text不能为空")
        if key_size < 1:
            raise ValueError("key_size必须大于0")
        if mode not in ('semantic', 'entropy', 'hybrid'):
            raise ValueError(f"不支持的模式: {mode}")
        if iterations < 1:
            raise ValueError("iterations必须大于0")

        if salt is None:
            salt = b"nlptc_keygen_default_salt"

        if mode == 'semantic':
            return self._generate_semantic_key(text, key_size, salt, iterations)
        elif mode == 'entropy':
            return self._generate_entropy_key(text, key_size, salt, iterations)
        else:
            return self._generate_hybrid_key(text, key_size, salt, iterations)

    def generate_from_passphrase(
        self,
        passphrase: str,
        salt: Optional[bytes] = None,
        key_size: int = 32,
    ) -> Tuple[bytes, bytes]:
        """从口令派生密钥。

        使用PBKDF2-HMAC-SHA256从口令派生密钥，返回密钥和盐值。

        Args:
            passphrase: 口令字符串
            salt: 盐值，不提供则自动生成
            key_size: 密钥长度（字节），默认为32

        Returns:
            (密钥, 盐值) 元组
        """
        if not isinstance(passphrase, str):
            raise TypeError("passphrase必须是字符串类型")
        if not passphrase:
            raise ValueError("passphrase不能为空")
        if key_size < 1:
            raise ValueError("key_size必须大于0")

        if salt is None:
            from ...core.crypto.random import generate_salt
            salt = generate_salt(16)

        key = KDF.pbkdf2_hmac(
            password=passphrase.encode('utf-8'),
            salt=salt,
            iterations=200000,
            dkLen=key_size,
            hash_alg='sha256',
        )

        return key, salt

    def verify_key(
        self,
        text: str,
        expected_key: bytes,
        mode: str = 'hybrid',
        salt: Optional[bytes] = None,
    ) -> bool:
        """验证文本生成的密钥是否匹配。

        Args:
            text: 输入文本
            expected_key: 期望的密钥
            mode: 密钥生成模式
            salt: 盐值

        Returns:
            匹配返回True，否则返回False
        """
        try:
            key_size = len(expected_key)
            actual_key = self.generate_key(
                text, key_size=key_size, mode=mode, salt=salt
            )
            return actual_key == expected_key
        except Exception:
            return False

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具。

        Args:
            params: 参数字典
                - text: 输入文本
                - key_size: 密钥长度（字节），可选，默认32
                - mode: 生成模式，可选，默认'hybrid'
                - salt: base64编码的盐值，可选
                - iterations: 迭代次数，可选，默认100000

        Returns:
            结果字典
                - key: base64编码的密钥
                - key_hex: 十六进制密钥
                - features: 文本特征
                - strength: 密钥强度评估
                - success: 是否成功
                - message: 消息

        Raises:
            ValidationError: 当参数验证失败时
        """
        try:
            self.validate_params(params)

            text = params["text"]
            key_size = params.get("key_size", 32)
            mode = params.get("mode", "hybrid")
            iterations = params.get("iterations", 100000)

            salt = None
            if "salt" in params and params["salt"]:
                salt = base64.b64decode(params["salt"])

            key = self.generate_key(
                text=text,
                key_size=key_size,
                mode=mode,
                salt=salt,
                iterations=iterations,
            )

            features = self._feature_extractor.extract_features(text)
            strength = self._strength_evaluator.evaluate(key)

            return {
                "success": True,
                "key": base64.b64encode(key).decode("utf-8"),
                "key_hex": key.hex(),
                "features": {
                    "length": features["length"],
                    "entropy": features["entropy"],
                    "lang": features["lang"],
                    "char_distribution": features["char_distribution"],
                },
                "strength": strength,
                "message": "密钥生成成功",
            }

        except ValidationError:
            raise
        except Exception as e:
            return {
                "success": False,
                "key": None,
                "key_hex": None,
                "features": None,
                "strength": None,
                "message": f"执行失败: {str(e)}",
            }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证输入参数。

        Args:
            params: 输入参数字典

        Returns:
            验证通过返回True

        Raises:
            ValidationError: 当参数验证失败时
        """
        if "text" not in params:
            raise ValidationError(
                field="text",
                message="缺少必要参数: text",
            )

        if not isinstance(params["text"], str):
            raise ValidationError(
                field="text",
                message="text必须是字符串类型",
            )

        if not params["text"]:
            raise ValidationError(
                field="text",
                message="text不能为空",
            )

        if "key_size" in params:
            if not isinstance(params["key_size"], int):
                raise ValidationError(
                    field="key_size",
                    message="key_size必须是整数",
                )
            if params["key_size"] < 1:
                raise ValidationError(
                    field="key_size",
                    message="key_size必须大于0",
                )

        if "mode" in params:
            if params["mode"] not in ('semantic', 'entropy', 'hybrid'):
                raise ValidationError(
                    field="mode",
                    message=f"不支持的模式: {params['mode']}",
                )

        if "iterations" in params:
            if not isinstance(params["iterations"], int):
                raise ValidationError(
                    field="iterations",
                    message="iterations必须是整数",
                )
            if params["iterations"] < 1:
                raise ValidationError(
                    field="iterations",
                    message="iterations必须大于0",
                )

        if "salt" in params and params["salt"] is not None:
            if not isinstance(params["salt"], str):
                raise ValidationError(
                    field="salt",
                    message="salt必须是base64编码的字符串",
                )
            try:
                base64.b64decode(params["salt"])
            except Exception:
                raise ValidationError(
                    field="salt",
                    message="salt不是有效的base64编码",
                )

        return True

    def _generate_semantic_key(
        self,
        text: str,
        key_size: int,
        salt: bytes,
        iterations: int,
    ) -> bytes:
        """基于语义特征生成密钥。

        使用语义种子作为输入密钥材料，通过HKDF派生最终密钥。

        Args:
            text: 输入文本
            key_size: 密钥长度
            salt: 盐值
            iterations: 迭代次数（此模式下未使用）

        Returns:
            生成的密钥
        """
        semantic_seed = self._feature_extractor.semantic_seed(text)

        derived_key = KDF.hkdf(
            ikm=semantic_seed,
            salt=salt,
            info=b"nlptc_semantic_key",
            length=key_size,
            hash_alg='sha256',
        )

        return derived_key

    def _generate_entropy_key(
        self,
        text: str,
        key_size: int,
        salt: bytes,
        iterations: int,
    ) -> bytes:
        """基于文本熵值生成密钥。

        使用文本原始字节通过PBKDF2派生密钥。

        Args:
            text: 输入文本
            key_size: 密钥长度
            salt: 盐值
            iterations: 迭代次数

        Returns:
            生成的密钥
        """
        text_bytes = text.encode('utf-8')

        derived_key = KDF.pbkdf2_hmac(
            password=text_bytes,
            salt=salt,
            iterations=iterations,
            dkLen=key_size,
            hash_alg='sha256',
        )

        return derived_key

    def _generate_hybrid_key(
        self,
        text: str,
        key_size: int,
        salt: bytes,
        iterations: int,
    ) -> bytes:
        """混合模式生成密钥。

        结合语义特征和文本熵值，通过多次哈希和KDF派生最终密钥。

        Args:
            text: 输入文本
            key_size: 密钥长度
            salt: 盐值
            iterations: 迭代次数

        Returns:
            生成的密钥
        """
        semantic_seed = self._feature_extractor.semantic_seed(text)
        text_bytes = text.encode('utf-8')
        text_hash = Hash.sha256(text_bytes)

        combined_ikm = bytearray()
        combined_ikm.extend(semantic_seed)
        combined_ikm.extend(text_hash)
        combined_ikm.extend(len(text).to_bytes(8, 'big'))

        features = self._feature_extractor.extract_features(text)
        combined_ikm.extend(struct.pack('>d', features['entropy']))

        intermediate = Hash.sha256(bytes(combined_ikm))

        derived_key = KDF.pbkdf2_hmac(
            password=intermediate,
            salt=salt,
            iterations=iterations,
            dkLen=key_size,
            hash_alg='sha256',
        )

        return derived_key
