"""JMKstudio CA管理器模块。

提供JMKstudio证书颁发机构的核心管理功能，包括根CA初始化、
中间CA创建、证书签发、验证和吊销等操作。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509.oid import NameOID, ExtensionOID

from ...core.crypto.primitives import RSACipher
from .certificate_types import (
    CertificateType,
    CertificateStatus,
    JMKStudioExtension,
    RevocationReason,
    ScienceCertExtension,
    WarshipCertExtension,
)

JMKSTUDIO_EXTENSION_OID = x509.ObjectIdentifier("1.3.6.1.4.1.99999.1")
WARSHIP_EXTENSION_OID = x509.ObjectIdentifier("1.3.6.1.4.1.99999.2")
SCIENCE_EXTENSION_OID = x509.ObjectIdentifier("1.3.6.1.4.1.99999.3")
CERT_TYPE_OID = x509.ObjectIdentifier("1.3.6.1.4.1.99999.4")


class JMKStudioCA:
    """JMKstudio证书颁发机构管理器。

    管理JMKstudio CA体系的完整层级结构，支持根CA、中间CA和终端实体证书的
    创建、签发、验证和吊销。

    Attributes:
        ca_name: CA名称
        _root_cert: 根CA证书
        _root_key: 根CA私钥
        _intermediate_cas: 中间CA字典
        _certificates: 已签发证书字典
        _revoked_certificates: 已吊销证书字典
    """

    def __init__(self, ca_name: str = "JMKstudio Root CA") -> None:
        """初始化JMKstudio CA管理器。

        Args:
            ca_name: CA名称，默认为"JMKstudio Root CA"
        """
        self.ca_name = ca_name
        self._root_cert: Optional[x509.Certificate] = None
        self._root_key: Optional[rsa.RSAPrivateKey] = None
        self._intermediate_cas: Dict[str, Tuple[x509.Certificate, rsa.RSAPrivateKey]] = {}
        self._certificates: Dict[str, Dict[str, Any]] = {}
        self._revoked_certificates: Dict[str, Dict[str, Any]] = {}

    def initialize_root(self, key_size: int = 4096, validity_days: int = 3650) -> Tuple[bytes, bytes]:
        """初始化JMKstudio根CA。

        生成自签名的根CA证书和私钥。

        Args:
            key_size: RSA密钥大小，默认为4096位
            validity_days: 证书有效期（天），默认为10年

        Returns:
            (证书PEM, 私钥PEM) 元组
        """
        private_key, public_key = RSACipher.generate_keypair(key_size=key_size)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JMKstudio"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Certificate Authority"),
            x509.NameAttribute(NameOID.COMMON_NAME, self.ca_name),
        ])

        now = datetime.now(timezone.utc)
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(public_key),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                self._build_cert_type_extension(CertificateType.JMKSTUDIO_ROOT),
                critical=False,
            )
        )

        cert = cert_builder.sign(private_key, hashes.SHA256())

        self._root_cert = cert
        self._root_key = private_key

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = RSACipher.serialize_private_key(private_key)

        self._register_certificate(cert, CertificateType.JMKSTUDIO_ROOT, "root")

        return cert_pem, key_pem

    def create_intermediate_ca(
        self,
        ca_name: str,
        ca_type: CertificateType,
        validity_days: int = 1825,
    ) -> Tuple[bytes, bytes]:
        """创建中间CA证书。

        Args:
            ca_name: 中间CA名称
            ca_type: 中间CA类型
            validity_days: 证书有效期（天），默认为5年

        Returns:
            (证书PEM, 私钥PEM) 元组

        Raises:
            ValueError: 当根CA未初始化时
            ValueError: 当ca_type不是CA类型时
        """
        if self._root_cert is None or self._root_key is None:
            raise ValueError("根CA未初始化，请先调用initialize_root()")

        if not CertificateType.is_ca_type(ca_type):
            raise ValueError(f"证书类型 {ca_type.value} 不是有效的CA类型")

        private_key, public_key = RSACipher.generate_keypair(key_size=4096)

        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JMKstudio"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, ca_name),
            x509.NameAttribute(NameOID.COMMON_NAME, ca_name),
        ])

        now = datetime.now(timezone.utc)
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self._root_cert.subject)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(self._root_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=0),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                self._build_cert_type_extension(ca_type),
                critical=False,
            )
        )

        cert = cert_builder.sign(self._root_key, hashes.SHA256())

        self._intermediate_cas[ca_name] = (cert, private_key)

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = RSACipher.serialize_private_key(private_key)

        self._register_certificate(cert, ca_type, ca_name)

        return cert_pem, key_pem

    def issue_certificate(
        self,
        subject: str,
        cert_type: CertificateType,
        issuer_ca: str = "root",
        extensions: Optional[Dict[str, Any]] = None,
        validity_days: int = 365,
        key_size: int = 2048,
    ) -> Tuple[bytes, bytes]:
        """签发证书。

        Args:
            subject: 证书主题（Common Name）
            cert_type: 证书类型
            issuer_ca: 签发CA名称，"root"表示根CA，默认为"root"
            extensions: 扩展字段字典
            validity_days: 证书有效期（天），默认为1年
            key_size: RSA密钥大小，默认为2048位

        Returns:
            (证书PEM, 私钥PEM) 元组

        Raises:
            ValueError: 当指定的签发CA不存在时
        """
        issuer_cert, issuer_key = self._get_issuer_ca(issuer_ca)

        private_key, public_key = RSACipher.generate_keypair(key_size=key_size)

        subject_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JMKstudio"),
            x509.NameAttribute(NameOID.COMMON_NAME, subject),
        ])

        now = datetime.now(timezone.utc)
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject_name)
            .issuer_name(issuer_cert.subject)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=True,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                ]),
                critical=False,
            )
            .add_extension(
                self._build_cert_type_extension(cert_type),
                critical=False,
            )
        )

        if extensions:
            cert_builder = self._add_custom_extensions(cert_builder, cert_type, extensions)

        cert = cert_builder.sign(issuer_key, hashes.SHA256())

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = RSACipher.serialize_private_key(private_key)

        self._register_certificate(cert, cert_type, subject, extensions)

        return cert_pem, key_pem

    def verify_certificate(self, cert_pem: bytes) -> Tuple[bool, str]:
        """验证证书。

        Args:
            cert_pem: PEM格式的证书

        Returns:
            (验证结果, 消息) 元组
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem)

            serial_number = str(cert.serial_number)
            if serial_number in self._revoked_certificates:
                return False, "证书已被吊销"

            now = datetime.now(timezone.utc)
            if now < cert.not_valid_before_utc:
                return False, "证书尚未生效"
            if now > cert.not_valid_after_utc:
                return False, "证书已过期"

            try:
                cert_type = self._get_cert_type_from_extension(cert)
            except Exception:
                cert_type = None

            issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
            if not issuer_cn:
                return False, "无法获取颁发者信息"

            issuer_name = issuer_cn[0].value

            issuer_cert = None
            issuer_key = None

            if self._root_cert is not None:
                root_cn = self._root_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                if root_cn and root_cn[0].value == issuer_name:
                    issuer_cert = self._root_cert
                    issuer_key = self._root_key

            if issuer_cert is None and issuer_name in self._intermediate_cas:
                issuer_cert, issuer_key = self._intermediate_cas[issuer_name]

            if issuer_cert is None:
                return False, f"未知的颁发者: {issuer_name}"

            try:
                issuer_public_key = issuer_cert.public_key()
                issuer_public_key.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    cert.signature_hash_algorithm,
                )
                return True, "证书验证通过"
            except Exception:
                return False, "证书签名验证失败"

        except Exception as e:
            return False, f"证书验证失败: {str(e)}"

    def get_ca_certificate(self, ca_name: str) -> bytes:
        """获取CA证书。

        Args:
            ca_name: CA名称，"root"表示根CA

        Returns:
            PEM格式的CA证书

        Raises:
            ValueError: 当指定的CA不存在时
        """
        if ca_name == "root":
            if self._root_cert is None:
                raise ValueError("根CA未初始化")
            return self._root_cert.public_bytes(serialization.Encoding.PEM)

        if ca_name not in self._intermediate_cas:
            raise ValueError(f"CA不存在: {ca_name}")

        cert, _ = self._intermediate_cas[ca_name]
        return cert.public_bytes(serialization.Encoding.PEM)

    def revoke_certificate(
        self,
        serial_number: str,
        reason: str = "unspecified",
    ) -> bool:
        """吊销证书。

        Args:
            serial_number: 证书序列号
            reason: 吊销原因

        Returns:
            吊销成功返回True，证书不存在返回False
        """
        if serial_number not in self._certificates:
            return False

        self._revoked_certificates[serial_number] = {
            "serial_number": serial_number,
            "reason": reason,
            "revocation_date": datetime.now(timezone.utc).isoformat(),
            "cert_info": self._certificates[serial_number],
        }

        self._certificates[serial_number]["status"] = CertificateStatus.REVOKED.value

        return True

    def list_certificates(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出证书。

        Args:
            status: 按状态筛选，None表示列出所有证书

        Returns:
            证书信息列表
        """
        result = []
        for serial_number, cert_info in self._certificates.items():
            if status is None or cert_info.get("status") == status:
                result.append(cert_info)
        return result

    def _get_issuer_ca(
        self,
        ca_name: str,
    ) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """获取签发CA的证书和私钥。

        Args:
            ca_name: CA名称

        Returns:
            (证书, 私钥) 元组

        Raises:
            ValueError: 当CA不存在时
        """
        if ca_name == "root":
            if self._root_cert is None or self._root_key is None:
                raise ValueError("根CA未初始化")
            return self._root_cert, self._root_key

        if ca_name not in self._intermediate_cas:
            raise ValueError(f"CA不存在: {ca_name}")

        return self._intermediate_cas[ca_name]

    def _build_cert_type_extension(self, cert_type: CertificateType) -> x509.ExtensionType:
        """构建证书类型扩展。

        Args:
            cert_type: 证书类型

        Returns:
            自定义扩展对象
        """
        return x509.UnrecognizedExtension(
            CERT_TYPE_OID,
            cert_type.value.encode("utf-8"),
        )

    def _get_cert_type_from_extension(self, cert: x509.Certificate) -> Optional[CertificateType]:
        """从证书扩展中获取证书类型。

        Args:
            cert: 证书对象

        Returns:
            证书类型，如果未找到返回None
        """
        try:
            ext = cert.extensions.get_extension_for_oid(CERT_TYPE_OID)
            type_str = ext.value.value.decode("utf-8")
            return CertificateType.from_string(type_str)
        except Exception:
            return None

    def _add_custom_extensions(
        self,
        builder: x509.CertificateBuilder,
        cert_type: CertificateType,
        extensions: Dict[str, Any],
    ) -> x509.CertificateBuilder:
        """添加自定义扩展。

        Args:
            builder: 证书构建器
            cert_type: 证书类型
            extensions: 扩展字段字典

        Returns:
            更新后的证书构建器
        """
        if cert_type == CertificateType.WARSHIP_CERT:
            ext = WarshipCertExtension.from_dict(extensions)
            builder = builder.add_extension(
                x509.UnrecognizedExtension(
                    WARSHIP_EXTENSION_OID,
                    json.dumps(ext.to_dict()).encode("utf-8"),
                ),
                critical=False,
            )
        elif cert_type in (CertificateType.SCIENCE_CERT, CertificateType.SPACE_PHYSICS_CERT):
            ext = ScienceCertExtension.from_dict(extensions)
            builder = builder.add_extension(
                x509.UnrecognizedExtension(
                    SCIENCE_EXTENSION_OID,
                    json.dumps(ext.to_dict()).encode("utf-8"),
                ),
                critical=False,
            )

        if "jmkstudio" in extensions:
            jmk_ext = JMKStudioExtension.from_dict(extensions["jmkstudio"])
            builder = builder.add_extension(
                x509.UnrecognizedExtension(
                    JMKSTUDIO_EXTENSION_OID,
                    json.dumps(jmk_ext.to_dict()).encode("utf-8"),
                ),
                critical=False,
            )

        return builder

    def _register_certificate(
        self,
        cert: x509.Certificate,
        cert_type: CertificateType,
        name: str,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> None:
        """注册证书到内部存储。

        Args:
            cert: 证书对象
            cert_type: 证书类型
            name: 证书名称
            extensions: 扩展字段
        """
        serial_number = str(cert.serial_number)
        subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        subject = subject_cn[0].value if subject_cn else name

        self._certificates[serial_number] = {
            "serial_number": serial_number,
            "subject": subject,
            "cert_type": cert_type.value,
            "status": CertificateStatus.VALID.value,
            "issuer": cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            if cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
            else "Unknown",
            "not_valid_before": cert.not_valid_before_utc.isoformat(),
            "not_valid_after": cert.not_valid_after_utc.isoformat(),
            "extensions": extensions or {},
        }

    def get_certificate_info(self, cert_pem: bytes) -> Dict[str, Any]:
        """获取证书信息。

        Args:
            cert_pem: PEM格式的证书

        Returns:
            证书信息字典
        """
        cert = x509.load_pem_x509_certificate(cert_pem)

        subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)

        cert_type = self._get_cert_type_from_extension(cert)

        info = {
            "serial_number": str(cert.serial_number),
            "subject": subject_cn[0].value if subject_cn else "Unknown",
            "issuer": issuer_cn[0].value if issuer_cn else "Unknown",
            "not_valid_before": cert.not_valid_before_utc.isoformat(),
            "not_valid_after": cert.not_valid_after_utc.isoformat(),
            "cert_type": cert_type.value if cert_type else "unknown",
            "signature_algorithm": cert.signature_algorithm_oid._name,
            "version": cert.version.value,
        }

        return info
