"""标签签名与验证模块。

提供Karma标签的RSA签名和验证功能，支持GPG CA、JMK CA和自定义签名者。
"""
from __future__ import annotations

import base64
from typing import List, Optional

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import Certificate, load_pem_x509_certificate

from ...core.crypto.primitives import RSACipher
from .karma_tag import KarmaTag


class TagSigner:
    """标签签名器类。

    提供Karma标签的签名和验证功能。支持多种签名方式：
    - 使用RSA密钥对直接签名
    - 使用X.509证书签名
    - 支持多签名者（gpgca, jmkca等）

    Attributes:
        _private_key: RSA私钥（用于签名）
        _public_key: RSA公钥（用于验证）
    """

    SIGNATURE_FIELDS = {
        "gpgca": "gpgca",
        "jmkca": "jmkca",
        "custom": "custom_signature",
    }

    def __init__(
        self,
        private_key_pem: Optional[bytes] = None,
        public_key_pem: Optional[bytes] = None,
    ) -> None:
        """初始化标签签名器。

        Args:
            private_key_pem: PEM格式的私钥字节，用于签名。可选。
            public_key_pem: PEM格式的公钥字节，用于验证。可选。
        """
        self._private_key: Optional[rsa.RSAPrivateKey] = None
        self._public_key: Optional[rsa.RSAPublicKey] = None

        if private_key_pem:
            self._private_key = RSACipher.deserialize_private_key(private_key_pem)
            self._public_key = self._private_key.public_key()

        if public_key_pem and self._public_key is None:
            self._public_key = RSACipher.deserialize_public_key(public_key_pem)

    def sign_tag(
        self,
        tag: KarmaTag,
        signer: str = "gpgca",
    ) -> KarmaTag:
        """签名标签。

        对标签数据（排除签名字段）进行哈希，然后使用RSA私钥签名。
        签名结果存储在对应签名字段中（base64编码）。

        Args:
            tag: 要签名的Karma标签
            signer: 签名者标识，可选 "gpgca", "jmkca", "custom"

        Returns:
            签名后的Karma标签（同一对象，已更新签名字段）

        Raises:
            ValueError: 当私钥未设置或签名者无效时
        """
        if self._private_key is None:
            raise ValueError("签名需要私钥，请先设置private_key_pem")

        if signer not in self.SIGNATURE_FIELDS:
            raise ValueError(
                f"不支持的签名者: {signer}，支持的签名者: {list(self.SIGNATURE_FIELDS.keys())}"
            )

        data_to_sign = tag.get_data_for_signing()
        signature = RSACipher.sign(data_to_sign, self._private_key)
        signature_b64 = base64.b64encode(signature).decode("utf-8")

        field_name = self.SIGNATURE_FIELDS[signer]
        tag.set_custom_field(field_name, signature_b64)

        return tag

    def verify_tag(
        self,
        tag: KarmaTag,
        signer: str = "gpgca",
    ) -> bool:
        """验证标签签名。

        从对应签名字段获取签名，然后使用RSA公钥验证。

        Args:
            tag: 要验证的Karma标签
            signer: 签名者标识，可选 "gpgca", "jmkca", "custom"

        Returns:
            验证通过返回True，否则返回False

        Raises:
            ValueError: 当公钥未设置或签名者无效时
        """
        if self._public_key is None:
            raise ValueError("验证需要公钥，请先设置public_key_pem或private_key_pem")

        if signer not in self.SIGNATURE_FIELDS:
            raise ValueError(
                f"不支持的签名者: {signer}，支持的签名者: {list(self.SIGNATURE_FIELDS.keys())}"
            )

        field_name = self.SIGNATURE_FIELDS[signer]
        signature_b64 = tag.get_custom_field(field_name) if field_name not in ["gpgca", "jmkca"] else getattr(tag, field_name, "")

        if signer == "gpgca":
            signature_b64 = tag.gpgca
        elif signer == "jmkca":
            signature_b64 = tag.jmkca
        else:
            signature_b64 = tag.get_custom_field(field_name) or ""

        if not signature_b64:
            return False

        try:
            signature = base64.b64decode(signature_b64)
        except Exception:
            return False

        data_to_verify = tag.get_data_for_signing()
        return RSACipher.verify(data_to_verify, signature, self._public_key)

    def sign_with_cert(
        self,
        tag: KarmaTag,
        cert_pem: bytes,
        key_pem: bytes,
    ) -> KarmaTag:
        """使用证书签名标签。

        使用证书对应的私钥签名，并将签名存储在custom_signature字段中。

        Args:
            tag: 要签名的Karma标签
            cert_pem: PEM格式的证书字节
            key_pem: PEM格式的私钥字节

        Returns:
            签名后的Karma标签（同一对象，已更新签名字段）
        """
        private_key = RSACipher.deserialize_private_key(key_pem)
        cert = load_pem_x509_certificate(cert_pem)

        data_to_sign = tag.get_data_for_signing()
        signature = RSACipher.sign(data_to_sign, private_key)
        signature_b64 = base64.b64encode(signature).decode("utf-8")

        tag.set_custom_field("custom_signature", signature_b64)
        tag.set_custom_field("signer_cert", base64.b64encode(cert_pem).decode("utf-8"))

        return tag

    def verify_with_cert(
        self,
        tag: KarmaTag,
        cert_pem: bytes,
    ) -> bool:
        """使用证书验证标签签名。

        从证书中提取公钥，然后验证custom_signature字段中的签名。

        Args:
            tag: 要验证的Karma标签
            cert_pem: PEM格式的证书字节

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            cert = load_pem_x509_certificate(cert_pem)
            public_key = cert.public_key()

            if not isinstance(public_key, rsa.RSAPublicKey):
                return False

            signature_b64 = tag.get_custom_field("custom_signature") or ""
            if not signature_b64:
                return False

            signature = base64.b64decode(signature_b64)
            data_to_verify = tag.get_data_for_signing()

            return RSACipher.verify(data_to_verify, signature, public_key)
        except Exception:
            return False

    def get_signers(self, tag: KarmaTag) -> List[str]:
        """获取标签上的所有签名者。

        检查所有签名字段，返回存在签名的签名者列表。

        Args:
            tag: 要检查的Karma标签

        Returns:
            签名者名称列表
        """
        signers: List[str] = []

        if tag.gpgca:
            signers.append("gpgca")

        if tag.jmkca:
            signers.append("jmkca")

        if tag.get_custom_field("custom_signature"):
            signers.append("custom")

        return signers

    def set_private_key(self, private_key_pem: bytes) -> None:
        """设置私钥。

        Args:
            private_key_pem: PEM格式的私钥字节
        """
        self._private_key = RSACipher.deserialize_private_key(private_key_pem)
        self._public_key = self._private_key.public_key()

    def set_public_key(self, public_key_pem: bytes) -> None:
        """设置公钥。

        Args:
            public_key_pem: PEM格式的公钥字节
        """
        self._public_key = RSACipher.deserialize_public_key(public_key_pem)
