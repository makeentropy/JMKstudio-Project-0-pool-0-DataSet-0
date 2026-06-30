"""隐写API模块。

提供多种隐写技术的高层API，包括XOR隐写、文本隐写、
证书隐写以及隐写安全性分析功能。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ..tools.steganography.xor_stego import XORSteganography
from ..tools.steganography.text_stego import TextSteganography
from ..tools.steganography.cert_stego import CertificateSteganography
from ..tools.steganography.capacity_analyzer import StegoCapacityAnalyzer


class StegoAPI:
    """隐写API类。

    提供多种隐写技术的统一高层接口，包括XOR隐写、文本隐写、
    证书隐写以及隐写安全性分析功能。

    Attributes:
        engine: 乾坤引擎实例
    """

    def __init__(self, engine: Any) -> None:
        """初始化隐写API。

        Args:
            engine: 乾坤引擎实例
        """
        self._engine = engine
        self._xor_stego = XORSteganography()
        self._text_stego = TextSteganography()
        self._cert_stego = CertificateSteganography()
        self._analyzer = StegoCapacityAnalyzer()

    def embed_xor(
        self,
        secret: bytes,
        carrier: bytes,
        key: bytes = None,
    ) -> bytes:
        """使用XOR隐写嵌入秘密数据。

        Args:
            secret: 秘密数据
            carrier: 载体数据
            key: 加密密钥（可选）

        Returns:
            隐写后的数据
        """
        return self._xor_stego.embed_with_length(secret, carrier, key)

    def extract_xor(
        self,
        stego: bytes,
        length: int = 0,
        key: bytes = None,
    ) -> bytes:
        """从XOR隐写数据中提取秘密。

        Args:
            stego: 隐写数据
            length: 秘密长度（不提供则从数据中读取长度前缀）
            key: 加密密钥（可选）

        Returns:
            提取的秘密数据
        """
        if length > 0:
            return self._xor_stego.extract(stego, length, key)
        return self._xor_stego.extract_with_length(stego, key)

    def embed_text_unicode(self, secret: bytes, text: str) -> str:
        """使用Unicode隐写将秘密嵌入文本。

        Args:
            secret: 秘密数据
            text: 载体文本

        Returns:
            隐写后的文本
        """
        return self._text_stego.embed_unicode(text, secret)

    def extract_text_unicode(self, stego_text: str) -> bytes:
        """从Unicode隐写文本中提取秘密。

        Args:
            stego_text: 隐写文本

        Returns:
            提取的秘密数据
        """
        return self._text_stego.extract_unicode(stego_text)

    def embed_text_whitespace(self, secret: bytes, text: str) -> str:
        """使用空格隐写将秘密嵌入文本。

        Args:
            secret: 秘密数据
            text: 载体文本

        Returns:
            隐写后的文本
        """
        return self._text_stego.embed_whitespace(text, secret)

    def extract_text_whitespace(self, stego_text: str) -> bytes:
        """从空格隐写文本中提取秘密。

        Args:
            stego_text: 隐写文本

        Returns:
            提取的秘密数据
        """
        return self._text_stego.extract_whitespace(stego_text)

    def embed_in_cert(self, secret: bytes, cert_pem: bytes) -> bytes:
        """将秘密数据嵌入证书扩展字段。

        Args:
            secret: 秘密数据
            cert_pem: PEM格式的证书字节

        Returns:
            隐写后的证书PEM字节
        """
        return self._cert_stego.embed_in_extension(cert_pem, secret)

    def extract_from_cert(self, cert_pem: bytes) -> bytes:
        """从证书扩展字段中提取秘密数据。

        Args:
            cert_pem: PEM格式的证书字节

        Returns:
            提取的秘密数据
        """
        return self._cert_stego.extract_from_extension(cert_pem)

    def analyze_carrier(
        self,
        carrier: bytes,
        carrier_type: str = "binary",
    ) -> Dict[str, Any]:
        """分析载体的隐写容量。

        Args:
            carrier: 载体数据
            carrier_type: 载体类型，默认为"binary"

        Returns:
            分析结果字典
        """
        return self._analyzer.analyze_carrier(carrier, carrier_type)

    def estimate_security(
        self,
        original: bytes,
        stego: bytes,
    ) -> Dict[str, Any]:
        """评估隐写的安全性。

        Args:
            original: 原始载体数据
            stego: 隐写后的数据

        Returns:
            安全性评估结果字典
        """
        return self._analyzer.generate_report(original, stego, "xor")
