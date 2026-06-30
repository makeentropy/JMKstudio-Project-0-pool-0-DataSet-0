"""证书生命周期管理模块。

提供证书的签发、续期、吊销、状态检查和CRL生成等全生命周期管理功能。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ...core.crypto.primitives import RSACipher
from .certificate_types import (
    CertificateStatus,
    CertificateType,
    RevocationReason,
)

CERT_TYPE_OID = x509.ObjectIdentifier("1.3.6.1.4.1.99999.4")


class CertificateLifecycleManager:
    """证书生命周期管理器。

    管理证书的完整生命周期，包括签发、续期、吊销、状态检查和CRL生成。

    Attributes:
        _ca_cert: CA证书
        _ca_key: CA私钥
        _certificates: 已签发证书字典
        _revoked_certificates: 已吊销证书字典
        _crl_number: CRL编号
    """

    def __init__(
        self,
        ca_cert_pem: Optional[bytes] = None,
        ca_key_pem: Optional[bytes] = None,
    ) -> None:
        """初始化证书生命周期管理器。

        Args:
            ca_cert_pem: CA证书（PEM格式）
            ca_key_pem: CA私钥（PEM格式）
        """
        self._ca_cert: Optional[x509.Certificate] = None
        self._ca_key: Optional[rsa.RSAPrivateKey] = None
        self._certificates: Dict[str, Dict[str, Any]] = {}
        self._revoked_certificates: Dict[str, Dict[str, Any]] = {}
        self._crl_number: int = 0

        if ca_cert_pem and ca_key_pem:
            self.set_ca(ca_cert_pem, ca_key_pem)

    def set_ca(self, ca_cert_pem: bytes, ca_key_pem: bytes) -> None:
        """设置CA证书和私钥。

        Args:
            ca_cert_pem: CA证书（PEM格式）
            ca_key_pem: CA私钥（PEM格式）
        """
        self._ca_cert = x509.load_pem_x509_certificate(ca_cert_pem)
        self._ca_key = RSACipher.deserialize_private_key(ca_key_pem)

    def issue_cert(
        self,
        subject: str,
        cert_type: CertificateType = CertificateType.END_ENTITY,
        validity_days: int = 365,
        key_size: int = 2048,
        extensions: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bytes, bytes]:
        """签发证书。

        Args:
            subject: 证书主题（Common Name）
            cert_type: 证书类型，默认为END_ENTITY
            validity_days: 证书有效期（天），默认为1年
            key_size: RSA密钥大小，默认为2048位
            extensions: 自定义扩展字段

        Returns:
            (证书PEM, 私钥PEM) 元组

        Raises:
            ValueError: 当CA未设置时
        """
        if self._ca_cert is None or self._ca_key is None:
            raise ValueError("CA证书和私钥未设置，请先调用set_ca()")

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
            .issuer_name(self._ca_cert.subject)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    self._ca_key.public_key()
                ),
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
                x509.UnrecognizedExtension(
                    CERT_TYPE_OID,
                    cert_type.value.encode("utf-8"),
                ),
                critical=False,
            )
        )

        cert = cert_builder.sign(self._ca_key, hashes.SHA256())

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = RSACipher.serialize_private_key(private_key)

        serial_number = str(cert.serial_number)
        self._certificates[serial_number] = {
            "serial_number": serial_number,
            "subject": subject,
            "cert_type": cert_type.value,
            "status": CertificateStatus.VALID.value,
            "not_valid_before": cert.not_valid_before_utc.isoformat(),
            "not_valid_after": cert.not_valid_after_utc.isoformat(),
            "cert_pem": cert_pem,
            "extensions": extensions or {},
        }

        return cert_pem, key_pem

    def renew_cert(
        self,
        cert_pem: bytes,
        private_key_pem: bytes,
        new_validity_days: Optional[int] = None,
    ) -> Tuple[bytes, bytes]:
        """续期证书。

        生成一个新的证书，保持原有的公钥和主题，但更新有效期。

        Args:
            cert_pem: 原证书（PEM格式）
            private_key_pem: 私钥（PEM格式）
            new_validity_days: 新的有效期（天），None表示使用原有效期

        Returns:
            (新证书PEM, 私钥PEM) 元组

        Raises:
            ValueError: 当CA未设置时
            ValueError: 当证书已被吊销时
        """
        if self._ca_cert is None or self._ca_key is None:
            raise ValueError("CA证书和私钥未设置，请先调用set_ca()")

        old_cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(old_cert.serial_number)

        if serial_number in self._revoked_certificates:
            raise ValueError("证书已被吊销，无法续期")

        private_key = RSACipher.deserialize_private_key(private_key_pem)
        public_key = private_key.public_key()

        if new_validity_days is None:
            old_validity = old_cert.not_valid_after_utc - old_cert.not_valid_before_utc
            new_validity_days = old_validity.days

        now = datetime.now(timezone.utc)
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(old_cert.subject)
            .issuer_name(self._ca_cert.subject)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=new_validity_days))
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    self._ca_key.public_key()
                ),
                critical=False,
            )
        )

        for ext in old_cert.extensions:
            if ext.oid in (
                x509.oid.ExtensionOID.SUBJECT_KEY_IDENTIFIER,
                x509.oid.ExtensionOID.AUTHORITY_KEY_IDENTIFIER,
            ):
                continue
            cert_builder = cert_builder.add_extension(ext.value, ext.critical)

        new_cert = cert_builder.sign(self._ca_key, hashes.SHA256())

        new_cert_pem = new_cert.public_bytes(serialization.Encoding.PEM)

        new_serial_number = str(new_cert.serial_number)
        cert_type = self._get_cert_type(old_cert)

        self._certificates[new_serial_number] = {
            "serial_number": new_serial_number,
            "subject": old_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            if old_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            else "Unknown",
            "cert_type": cert_type.value if cert_type else CertificateType.END_ENTITY.value,
            "status": CertificateStatus.VALID.value,
            "not_valid_before": new_cert.not_valid_before_utc.isoformat(),
            "not_valid_after": new_cert.not_valid_after_utc.isoformat(),
            "cert_pem": new_cert_pem,
            "renewed_from": serial_number,
        }

        return new_cert_pem, private_key_pem

    def revoke_cert(
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

        now = datetime.now(timezone.utc)
        self._revoked_certificates[serial_number] = {
            "serial_number": serial_number,
            "reason": reason,
            "revocation_date": now,
            "cert_info": self._certificates[serial_number],
        }

        self._certificates[serial_number]["status"] = CertificateStatus.REVOKED.value

        return True

    def generate_crl(
        self,
        next_update_days: int = 30,
    ) -> bytes:
        """生成证书吊销列表（CRL）。

        Args:
            next_update_days: 下一次更新时间（天）

        Returns:
            PEM格式的CRL

        Raises:
            ValueError: 当CA未设置时
        """
        if self._ca_cert is None or self._ca_key is None:
            raise ValueError("CA证书和私钥未设置，请先调用set_ca()")

        now = datetime.now(timezone.utc)

        builder = x509.CertificateRevocationListBuilder()
        builder = builder.issuer_name(self._ca_cert.subject)
        builder = builder.last_update(now)
        builder = builder.next_update(now + timedelta(days=next_update_days))

        for serial_number, revoked_info in self._revoked_certificates.items():
            revoked_cert = (
                x509.RevokedCertificateBuilder()
                .serial_number(int(serial_number))
                .revocation_date(revoked_info["revocation_date"])
                .build()
            )
            builder = builder.add_revoked_certificate(revoked_cert)

        self._crl_number += 1
        builder = builder.add_extension(
            x509.CRLNumber(self._crl_number),
            critical=False,
        )

        crl = builder.sign(self._ca_key, hashes.SHA256())

        return crl.public_bytes(serialization.Encoding.PEM)

    def check_status(self, cert_pem: bytes) -> str:
        """检查证书状态。

        Args:
            cert_pem: PEM格式的证书

        Returns:
            证书状态字符串（valid/revoked/expired/not_yet_valid）
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
        except Exception:
            return "invalid"

        serial_number = str(cert.serial_number)

        if serial_number in self._revoked_certificates:
            return CertificateStatus.REVOKED.value

        now = datetime.now(timezone.utc)

        if now < cert.not_valid_before_utc:
            return CertificateStatus.NOT_YET_VALID.value

        if now > cert.not_valid_after_utc:
            return CertificateStatus.EXPIRED.value

        return CertificateStatus.VALID.value

    def export_cert_info(self, cert_pem: bytes) -> Dict[str, Any]:
        """导出证书信息。

        Args:
            cert_pem: PEM格式的证书

        Returns:
            证书信息字典
        """
        cert = x509.load_pem_x509_certificate(cert_pem)

        subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)

        cert_type = self._get_cert_type(cert)

        is_ca = False
        try:
            basic_constraints = cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.BASIC_CONSTRAINTS
            )
            is_ca = basic_constraints.value.ca
        except x509.ExtensionNotFound:
            pass

        extensions_info = []
        for ext in cert.extensions:
            extensions_info.append({
                "oid": ext.oid.dotted_string,
                "name": ext.oid._name if hasattr(ext.oid, "_name") else ext.oid.dotted_string,
                "critical": ext.critical,
            })

        return {
            "serial_number": str(cert.serial_number),
            "subject": subject_cn[0].value if subject_cn else "Unknown",
            "issuer": issuer_cn[0].value if issuer_cn else "Unknown",
            "not_valid_before": cert.not_valid_before_utc.isoformat(),
            "not_valid_after": cert.not_valid_after_utc.isoformat(),
            "cert_type": cert_type.value if cert_type else "unknown",
            "is_ca": is_ca,
            "signature_algorithm": cert.signature_algorithm_oid._name,
            "version": cert.version.value,
            "public_key_size": cert.public_key().key_size
            if hasattr(cert.public_key(), "key_size")
            else None,
            "extensions": extensions_info,
            "status": self.check_status(cert_pem),
        }

    def _get_cert_type(self, cert: x509.Certificate) -> Optional[CertificateType]:
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

    def list_certificates(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有证书。

        Args:
            status: 按状态筛选，None表示列出所有

        Returns:
            证书信息列表
        """
        result = []
        for serial_number, cert_info in self._certificates.items():
            if status is None or cert_info.get("status") == status:
                info_copy = dict(cert_info)
                info_copy.pop("cert_pem", None)
                result.append(info_copy)
        return result

    def get_revoked_certificates(self) -> List[Dict[str, Any]]:
        """获取所有已吊销的证书。

        Returns:
            已吊销证书信息列表
        """
        result = []
        for serial_number, revoked_info in self._revoked_certificates.items():
            info = {
                "serial_number": serial_number,
                "reason": revoked_info["reason"],
                "revocation_date": revoked_info["revocation_date"].isoformat(),
            }
            result.append(info)
        return result
