"""
CA认证系统

提供证书颁发机构（CA）功能，包括证书生成、验证、签名和吊销。
"""

import base64
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class CertificateStatus(Enum):
    """证书状态枚举"""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


class CertificateType(Enum):
    """证书类型枚举"""
    ROOT_CA = "root_ca"
    INTERMEDIATE_CA = "intermediate_ca"
    END_ENTITY = "end_entity"
    SERVER = "server"
    CLIENT = "client"
    CODE_SIGNING = "code_signing"


@dataclass
class CertificateInfo:
    """证书信息数据类"""
    serial_number: str
    subject: str
    issuer: str
    not_before: datetime
    not_after: datetime
    certificate_type: CertificateType
    public_key_fingerprint: str
    status: CertificateStatus = CertificateStatus.VALID
    revocation_reason: Optional[str] = None
    revocation_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "serial_number": self.serial_number,
            "subject": self.subject,
            "issuer": self.issuer,
            "not_before": self.not_before.isoformat(),
            "not_after": self.not_after.isoformat(),
            "certificate_type": self.certificate_type.value,
            "public_key_fingerprint": self.public_key_fingerprint,
            "status": self.status.value,
            "revocation_reason": self.revocation_reason,
            "revocation_date": self.revocation_date.isoformat() if self.revocation_date else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CertificateInfo":
        """从字典创建"""
        return cls(
            serial_number=data["serial_number"],
            subject=data["subject"],
            issuer=data["issuer"],
            not_before=datetime.fromisoformat(data["not_before"]),
            not_after=datetime.fromisoformat(data["not_after"]),
            certificate_type=CertificateType(data["certificate_type"]),
            public_key_fingerprint=data["public_key_fingerprint"],
            status=CertificateStatus(data.get("status", "valid")),
            revocation_reason=data.get("revocation_reason"),
            revocation_date=datetime.fromisoformat(data["revocation_date"]) if data.get("revocation_date") else None,
        )

    def is_expired(self) -> bool:
        """检查证书是否过期"""
        return datetime.utcnow() > self.not_after

    def is_valid(self) -> bool:
        """检查证书是否有效"""
        if self.status != CertificateStatus.VALID:
            return False
        if self.is_expired():
            return False
        return True


@dataclass
class CertificateRevocationList:
    """证书吊销列表"""
    issuer: str
    this_update: datetime
    next_update: datetime
    revoked_certificates: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "issuer": self.issuer,
            "this_update": self.this_update.isoformat(),
            "next_update": self.next_update.isoformat(),
            "revoked_certificates": self.revoked_certificates,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CertificateRevocationList":
        """从字典创建"""
        return cls(
            issuer=data["issuer"],
            this_update=datetime.fromisoformat(data["this_update"]),
            next_update=datetime.fromisoformat(data["next_update"]),
            revoked_certificates=data.get("revoked_certificates", []),
        )


class CertificateAuthority:
    """
    证书颁发机构

    负责证书的签发、验证、吊销等管理。
    """

    def __init__(
        self,
        name: str,
        key_size: int = 4096,
        validity_days: int = 3650,
    ):
        """
        初始化CA

        Args:
            name: CA名称
            key_size: RSA密钥大小
            validity_days: 证书有效期（天）
        """
        self.name = name
        self.key_size = key_size
        self.validity_days = validity_days
        self._private_key: Optional[rsa.RSAPrivateKey] = None
        self._certificate: Optional[x509.Certificate] = None
        self._certificate_info: Optional[CertificateInfo] = None
        self._issued_certificates: Dict[str, CertificateInfo] = {}
        self._revoked_certificates: Set[str] = set()
        self._crl: Optional[CertificateRevocationList] = None

    def initialize(self) -> None:
        """初始化CA，生成根证书"""
        # 生成私钥
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend()
        )

        # 创建主题
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.name),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{self.name} Root CA"),
        ])

        # 创建根证书
        self._certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self._private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=self.validity_days))
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
                x509.SubjectKeyIdentifier.from_public_key(self._private_key.public_key()),
                critical=False,
            )
            .sign(self._private_key, hashes.SHA256(), default_backend())
        )

        # 创建证书信息
        self._certificate_info = CertificateInfo(
            serial_number=str(self._certificate.serial_number),
            subject=self._certificate.subject.rfc4514_string(),
            issuer=self._certificate.issuer.rfc4514_string(),
            not_before=self._certificate.not_valid_before_utc.replace(tzinfo=None),
            not_after=self._certificate.not_valid_after_utc.replace(tzinfo=None),
            certificate_type=CertificateType.ROOT_CA,
            public_key_fingerprint=self._calculate_fingerprint(self._certificate),
        )

        logger.info(f"CA初始化完成: {self.name}")

    def _calculate_fingerprint(self, certificate: x509.Certificate) -> str:
        """计算证书指纹"""
        return hashlib.sha256(certificate.public_bytes(serialization.Encoding.DER)).hexdigest()

    def issue_certificate(
        self,
        subject_name: str,
        certificate_type: CertificateType = CertificateType.END_ENTITY,
        validity_days: Optional[int] = None,
        key_size: Optional[int] = None,
        san_dns_names: Optional[List[str]] = None,
        san_ip_addresses: Optional[List[str]] = None,
    ) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """
        签发证书

        Args:
            subject_name: 主题名称（CN）
            certificate_type: 证书类型
            validity_days: 有效期（天），不指定则使用CA默认值
            key_size: 密钥大小，不指定则使用CA默认值
            san_dns_names: 主题备用名称（DNS）
            san_ip_addresses: 主题备用名称（IP）

        Returns:
            (证书, 私钥) 元组
        """
        if not self._private_key or not self._certificate:
            raise RuntimeError("CA未初始化，请先调用initialize()")

        if validity_days is None:
            validity_days = min(self.validity_days, 365)  # 非根证书最长1年

        if key_size is None:
            key_size = self.key_size

        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )

        # 创建主题
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.name),
            x509.NameAttribute(NameOID.COMMON_NAME, subject_name),
        ])

        # 构建证书
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self._certificate.subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
        )

        # 添加扩展
        extensions = self._get_extensions_for_type(
            certificate_type, private_key.public_key(), san_dns_names, san_ip_addresses
        )
        for ext in extensions:
            builder = builder.add_extension(ext[0], critical=ext[1])

        # 签名
        certificate = builder.sign(self._private_key, hashes.SHA256(), default_backend())

        # 记录证书信息
        cert_info = CertificateInfo(
            serial_number=str(certificate.serial_number),
            subject=certificate.subject.rfc4514_string(),
            issuer=certificate.issuer.rfc4514_string(),
            not_before=certificate.not_valid_before_utc.replace(tzinfo=None),
            not_after=certificate.not_valid_after_utc.replace(tzinfo=None),
            certificate_type=certificate_type,
            public_key_fingerprint=self._calculate_fingerprint(certificate),
        )

        self._issued_certificates[cert_info.serial_number] = cert_info
        logger.info(f"签发证书: {subject_name}, 序列号: {cert_info.serial_number}")

        return certificate, private_key

    def _get_extensions_for_type(
        self,
        certificate_type: CertificateType,
        public_key: rsa.RSAPublicKey,
        san_dns_names: Optional[List[str]] = None,
        san_ip_addresses: Optional[List[str]] = None,
    ) -> List[tuple]:
        """根据证书类型获取扩展"""
        extensions = []

        # 基本约束
        if certificate_type in [CertificateType.ROOT_CA, CertificateType.INTERMEDIATE_CA]:
            extensions.append((
                x509.BasicConstraints(ca=True, path_length=None),
                True
            ))
        else:
            extensions.append((
                x509.BasicConstraints(ca=False, path_length=None),
                True
            ))

        # 密钥用途
        if certificate_type == CertificateType.SERVER:
            key_usage = x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            )
        elif certificate_type == CertificateType.CLIENT:
            key_usage = x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            )
        elif certificate_type in [CertificateType.ROOT_CA, CertificateType.INTERMEDIATE_CA]:
            key_usage = x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            )
        else:
            key_usage = x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            )
        extensions.append((key_usage, True))

        # 扩展密钥用途
        if certificate_type == CertificateType.SERVER:
            eku = x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH])
            extensions.append((eku, False))
        elif certificate_type == CertificateType.CLIENT:
            eku = x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH])
            extensions.append((eku, False))
        elif certificate_type == CertificateType.CODE_SIGNING:
            eku = x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CODE_SIGNING])
            extensions.append((eku, False))

        # 主题密钥标识符
        extensions.append((
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            False
        ))

        # 主题备用名称
        san_list = []
        if san_dns_names:
            for name in san_dns_names:
                san_list.append(x509.DNSName(name))
        if san_ip_addresses:
            for ip in san_ip_addresses:
                san_list.append(x509.IPAddress(ip))
        if san_list:
            extensions.append((
                x509.SubjectAlternativeName(san_list),
                False
            ))

        return extensions

    def verify_certificate(
        self,
        certificate: x509.Certificate,
        check_revocation: bool = True,
    ) -> tuple[bool, str]:
        """
        验证证书

        Args:
            certificate: 要验证的证书
            check_revocation: 是否检查吊销状态

        Returns:
            (是否有效, 原因说明) 元组
        """
        if not self._certificate:
            return False, "CA未初始化"

        # 检查签名
        try:
            issuer_public_key = self._certificate.public_key()
            # 使用正确的签名验证方式
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
            issuer_public_key.verify(
                certificate.signature,
                certificate.tbs_certificate_bytes,
                asym_padding.PKCS1v15(),
                certificate.signature_hash_algorithm,
            )
        except Exception as e:
            return False, f"签名验证失败: {str(e)}"

        # 检查有效期
        now = datetime.utcnow()
        if now < certificate.not_valid_before_utc.replace(tzinfo=None):
            return False, "证书尚未生效"
        if now > certificate.not_valid_after_utc.replace(tzinfo=None):
            return False, "证书已过期"

        # 检查吊销状态
        if check_revocation:
            serial = str(certificate.serial_number)
            if serial in self._revoked_certificates:
                return False, "证书已被吊销"

        return True, "证书有效"

    def revoke_certificate(
        self,
        serial_number: str,
        reason: str = "unspecified",
    ) -> bool:
        """
        吊销证书

        Args:
            serial_number: 证书序列号
            reason: 吊销原因

        Returns:
            是否吊销成功
        """
        if serial_number in self._revoked_certificates:
            logger.warning(f"证书已吊销: {serial_number}")
            return False

        self._revoked_certificates.add(serial_number)

        # 更新证书信息
        if serial_number in self._issued_certificates:
            cert_info = self._issued_certificates[serial_number]
            cert_info.status = CertificateStatus.REVOKED
            cert_info.revocation_reason = reason
            cert_info.revocation_date = datetime.utcnow()

        logger.info(f"吊销证书: {serial_number}, 原因: {reason}")
        return True

    def generate_crl(
        self,
        validity_days: int = 7,
    ) -> CertificateRevocationList:
        """
        生成证书吊销列表

        Args:
            validity_days: CRL有效期（天）

        Returns:
            证书吊销列表
        """
        now = datetime.utcnow()
        revoked_list = []

        for serial in self._revoked_certificates:
            cert_info = self._issued_certificates.get(serial)
            if cert_info:
                revoked_list.append({
                    "serial_number": serial,
                    "revocation_date": cert_info.revocation_date.isoformat() if cert_info.revocation_date else now.isoformat(),
                    "reason": cert_info.revocation_reason or "unspecified",
                })

        self._crl = CertificateRevocationList(
            issuer=self._certificate.subject.rfc4514_string() if self._certificate else "",
            this_update=now,
            next_update=now + timedelta(days=validity_days),
            revoked_certificates=revoked_list,
        )

        logger.info(f"生成CRL: {len(revoked_list)}条记录")
        return self._crl

    def get_certificate_info(self, serial_number: str) -> Optional[CertificateInfo]:
        """
        获取证书信息

        Args:
            serial_number: 证书序列号

        Returns:
            证书信息或None
        """
        return self._issued_certificates.get(serial_number)

    def list_certificates(
        self,
        status: Optional[CertificateStatus] = None,
        cert_type: Optional[CertificateType] = None,
    ) -> List[CertificateInfo]:
        """
        列出证书

        Args:
            status: 证书状态过滤
            cert_type: 证书类型过滤

        Returns:
            证书信息列表
        """
        certificates = list(self._issued_certificates.values())

        if status:
            certificates = [c for c in certificates if c.status == status]
        if cert_type:
            certificates = [c for c in certificates if c.certificate_type == cert_type]

        return certificates

    def export_ca_certificate(self, format: str = "PEM") -> bytes:
        """
        导出CA证书

        Args:
            format: 导出格式 (PEM 或 DER)

        Returns:
            证书数据
        """
        if not self._certificate:
            raise RuntimeError("CA未初始化")

        if format.upper() == "PEM":
            return self._certificate.public_bytes(serialization.Encoding.PEM)
        elif format.upper() == "DER":
            return self._certificate.public_bytes(serialization.Encoding.DER)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def export_ca_private_key(
        self,
        password: Optional[bytes] = None,
        format: str = "PEM",
    ) -> bytes:
        """
        导出CA私钥

        Args:
            password: 加密密码
            format: 导出格式

        Returns:
            私钥数据
        """
        if not self._private_key:
            raise RuntimeError("CA未初始化")

        encryption: serialization.KeySerializationEncryption
        if password:
            encryption = serialization.BestAvailableEncryption(password)
        else:
            encryption = serialization.NoEncryption()

        if format.upper() == "PEM":
            return self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption,
            )
        elif format.upper() == "DER":
            return self._private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption,
            )
        else:
            raise ValueError(f"不支持的格式: {format}")

    def get_certificate_by_serial(self, serial_number: str) -> Optional[CertificateInfo]:
        """根据序列号获取证书信息"""
        return self._issued_certificates.get(serial_number)


class CertificateStore:
    """
    证书存储

    管理证书和私钥的存储。
    """

    def __init__(self):
        """初始化证书存储"""
        self._certificates: Dict[str, Dict[str, Any]] = {}
        self._private_keys: Dict[str, bytes] = {}

    def store_certificate(
        self,
        alias: str,
        certificate: x509.Certificate,
        private_key: Optional[rsa.RSAPrivateKey] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        存储证书

        Args:
            alias: 证书别名
            certificate: 证书对象
            private_key: 私钥（可选）
            metadata: 元数据
        """
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)

        self._certificates[alias] = {
            "certificate": cert_pem,
            "serial_number": str(certificate.serial_number),
            "subject": certificate.subject.rfc4514_string(),
            "issuer": certificate.issuer.rfc4514_string(),
            "not_before": certificate.not_valid_before_utc.isoformat(),
            "not_after": certificate.not_valid_after_utc.isoformat(),
            "metadata": metadata or {},
        }

        if private_key:
            self._private_keys[alias] = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

        logger.info(f"存储证书: {alias}")

    def get_certificate(self, alias: str) -> Optional[x509.Certificate]:
        """
        获取证书

        Args:
            alias: 证书别名

        Returns:
            证书对象或None
        """
        cert_data = self._certificates.get(alias)
        if not cert_data:
            return None

        return x509.load_pem_x509_certificate(cert_data["certificate"], default_backend())

    def get_private_key(self, alias: str) -> Optional[rsa.RSAPrivateKey]:
        """
        获取私钥

        Args:
            alias: 证书别名

        Returns:
            私钥对象或None
        """
        key_data = self._private_keys.get(alias)
        if not key_data:
            return None

        return serialization.load_pem_private_key(key_data, password=None, backend=default_backend())

    def get_certificate_info(self, alias: str) -> Optional[Dict[str, Any]]:
        """
        获取证书信息

        Args:
            alias: 证书别名

        Returns:
            证书信息或None
        """
        cert_data = self._certificates.get(alias)
        if not cert_data:
            return None

        return {
            "serial_number": cert_data["serial_number"],
            "subject": cert_data["subject"],
            "issuer": cert_data["issuer"],
            "not_before": cert_data["not_before"],
            "not_after": cert_data["not_after"],
            "metadata": cert_data.get("metadata", {}),
        }

    def delete_certificate(self, alias: str) -> bool:
        """
        删除证书

        Args:
            alias: 证书别名

        Returns:
            是否删除成功
        """
        if alias in self._certificates:
            del self._certificates[alias]
            if alias in self._private_keys:
                del self._private_keys[alias]
            logger.info(f"删除证书: {alias}")
            return True
        return False

    def list_certificates(self) -> List[str]:
        """列出所有证书别名"""
        return list(self._certificates.keys())

    def export_store(self) -> Dict[str, Any]:
        """导出证书存储"""
        return {
            "certificates": self._certificates,
            "private_keys": {k: base64.b64encode(v).decode("utf-8") for k, v in self._private_keys.items()},
        }

    def import_store(self, data: Dict[str, Any]) -> None:
        """导入证书存储"""
        self._certificates = data.get("certificates", {})
        private_keys_data = data.get("private_keys", {})
        self._private_keys = {k: base64.b64decode(v) for k, v in private_keys_data.items()}
        logger.info(f"导入{len(self._certificates)}个证书")


class CertificateVerifier:
    """
    证书验证器

    验证证书链和证书有效性。
    """

    def __init__(self, trusted_cas: Optional[List[x509.Certificate]] = None):
        """
        初始化验证器

        Args:
            trusted_cas: 受信任的CA证书列表
        """
        self._trusted_cas: Dict[str, x509.Certificate] = {}
        if trusted_cas:
            for ca_cert in trusted_cas:
                self.add_trusted_ca(ca_cert)

    def add_trusted_ca(self, certificate: x509.Certificate) -> None:
        """
        添加受信任的CA

        Args:
            certificate: CA证书
        """
        subject = certificate.subject.rfc4514_string()
        self._trusted_cas[subject] = certificate
        logger.info(f"添加受信任CA: {subject}")

    def verify_chain(
        self,
        certificate: x509.Certificate,
        intermediate_certs: Optional[List[x509.Certificate]] = None,
    ) -> tuple[bool, str]:
        """
        验证证书链

        Args:
            certificate: 要验证的证书
            intermediate_certs: 中间证书列表

        Returns:
            (是否有效, 原因说明) 元组
        """
        intermediate_certs = intermediate_certs or []

        # 检查有效期
        now = datetime.utcnow()
        if now < certificate.not_valid_before_utc.replace(tzinfo=None):
            return False, "证书尚未生效"
        if now > certificate.not_valid_after_utc.replace(tzinfo=None):
            return False, "证书已过期"

        # 查找签发者
        issuer_name = certificate.issuer.rfc4514_string()
        issuer_cert = self._trusted_cas.get(issuer_name)

        if not issuer_cert:
            # 在中间证书中查找
            for intermediate in intermediate_certs:
                if intermediate.subject.rfc4514_string() == issuer_name:
                    issuer_cert = intermediate
                    break

        if not issuer_cert:
            return False, f"未找到签发者证书: {issuer_name}"

        # 验证签名
        try:
            issuer_public_key = issuer_cert.public_key()
            from cryptography.hazmat.primitives.asymmetric import padding
            issuer_public_key.verify(
                certificate.signature,
                certificate.tbs_certificate_bytes,
                padding.PKCS1v15(),
                certificate.signature_hash_algorithm,
            )
        except Exception as e:
            return False, f"签名验证失败: {str(e)}"

        # 如果签发者是中间CA，递归验证
        try:
            basic_constraints = issuer_cert.extensions.get_extension_for_class(x509.BasicConstraints)
            if basic_constraints.value.ca:
                # 验证中间证书
                if issuer_cert.subject.rfc4514_string() not in self._trusted_cas:
                    return self.verify_chain(issuer_cert, intermediate_certs)
        except x509.ExtensionNotFound:
            pass

        return True, "证书链验证成功"

    def verify_signature(
        self,
        data: bytes,
        signature: bytes,
        certificate: x509.Certificate,
        hash_algorithm: str = "SHA256",
    ) -> bool:
        """
        验证签名

        Args:
            data: 原始数据
            signature: 签名
            certificate: 签名证书
            hash_algorithm: 哈希算法

        Returns:
            是否验证成功
        """
        from cryptography.hazmat.primitives.asymmetric import padding

        public_key = certificate.public_key()

        hash_obj = getattr(hashes, hash_algorithm.upper(), hashes.SHA256)()

        try:
            public_key.verify(
                signature,
                data,
                padding.PKCS1v15(),
                hash_obj,
            )
            return True
        except Exception:
            return False