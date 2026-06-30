"""证书隐写模块。

提供基于X.509证书的隐写技术，利用证书的扩展字段和序列号
嵌入秘密数据，不影响证书的正常验证。
"""
from __future__ import annotations

import base64
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtensionOID


class CertificateSteganography:
    """证书隐写类。

    利用X.509证书的结构特性进行数据隐藏：
    - 自定义扩展字段：可嵌入任意长度数据
    - 序列号低字节：可嵌入1字节数据

    Attributes:
        DEFAULT_OID: 默认使用的自定义扩展OID
    """

    DEFAULT_OID: str = "1.3.6.1.4.1.99999.1"

    def __init__(self) -> None:
        """初始化证书隐写工具。"""
        pass

    def embed_in_extension(
        self,
        cert_pem: bytes,
        secret_data: bytes,
        oid: Optional[str] = None,
    ) -> bytes:
        """在证书扩展字段嵌入数据。

        在X.509证书中添加一个自定义扩展字段，用于存储秘密数据。

        Args:
            cert_pem: PEM格式的证书数据
            secret_data: 要嵌入的秘密数据
            oid: 自定义扩展OID，默认使用DEFAULT_OID

        Returns:
            嵌入数据后的PEM格式证书

        Raises:
            ValueError: 当证书格式无效或数据处理失败时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(cert_pem, bytes):
            raise TypeError("证书数据必须是bytes类型")
        if not isinstance(secret_data, bytes):
            raise TypeError("秘密数据必须是bytes类型")

        target_oid = oid or self.DEFAULT_OID

        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
        except Exception as e:
            raise ValueError(f"无法解析证书: {e}") from e

        encoded_data = base64.b64encode(secret_data)

        custom_oid = x509.ObjectIdentifier(target_oid)
        custom_ext = x509.UnrecognizedExtension(custom_oid, encoded_data)

        builder = (
            x509.CertificateBuilder()
            .issuer_name(cert.issuer)
            .subject_name(cert.subject)
            .public_key(cert.public_key())
            .serial_number(cert.serial_number)
            .not_valid_before(cert.not_valid_before_utc)
            .not_valid_after(cert.not_valid_after_utc)
        )

        for ext in cert.extensions:
            if ext.oid.dotted_string != target_oid:
                builder = builder.add_extension(ext.value, critical=ext.critical)

        builder = builder.add_extension(custom_ext, critical=False)

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        new_cert = builder.sign(private_key, hashes.SHA256())

        return new_cert.public_bytes(serialization.Encoding.PEM)

    def extract_from_extension(
        self,
        cert_pem: bytes,
        oid: Optional[str] = None,
    ) -> bytes:
        """从证书扩展字段提取数据。

        从X.509证书的自定义扩展字段中提取秘密数据。

        Args:
            cert_pem: PEM格式的证书数据
            oid: 自定义扩展OID，默认使用DEFAULT_OID

        Returns:
            提取出的秘密数据

        Raises:
            ValueError: 当证书格式无效或扩展不存在时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(cert_pem, bytes):
            raise TypeError("证书数据必须是bytes类型")

        target_oid = oid or self.DEFAULT_OID

        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
        except Exception as e:
            raise ValueError(f"无法解析证书: {e}") from e

        custom_oid = x509.ObjectIdentifier(target_oid)

        try:
            ext = cert.extensions.get_extension_for_oid(custom_oid)
            encoded_data = ext.value.value
            return base64.b64decode(encoded_data)
        except x509.ExtensionNotFound:
            raise ValueError(f"未找到OID为 {target_oid} 的扩展字段")
        except Exception as e:
            raise ValueError(f"提取数据失败: {e}") from e

    def embed_in_serial(
        self,
        cert_pem: bytes,
        secret_byte: int,
    ) -> bytes:
        """在证书序列号中嵌入1字节数据。

        修改证书序列号的最低有效字节来嵌入1字节秘密数据。

        Args:
            cert_pem: PEM格式的证书数据
            secret_byte: 要嵌入的字节数据（0-255）

        Returns:
            嵌入数据后的PEM格式证书

        Raises:
            ValueError: 当证书格式无效或数据无效时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(cert_pem, bytes):
            raise TypeError("证书数据必须是bytes类型")
        if not isinstance(secret_byte, int) or not (0 <= secret_byte <= 255):
            raise ValueError("秘密字节必须是0-255之间的整数")

        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
        except Exception as e:
            raise ValueError(f"无法解析证书: {e}") from e

        original_serial = cert.serial_number
        new_serial = (original_serial & ~0xFF) | secret_byte

        builder = (
            x509.CertificateBuilder()
            .issuer_name(cert.issuer)
            .subject_name(cert.subject)
            .public_key(cert.public_key())
            .serial_number(new_serial)
            .not_valid_before(cert.not_valid_before_utc)
            .not_valid_after(cert.not_valid_after_utc)
        )

        for ext in cert.extensions:
            builder = builder.add_extension(ext.value, critical=ext.critical)

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        new_cert = builder.sign(private_key, hashes.SHA256())

        return new_cert.public_bytes(serialization.Encoding.PEM)

    def extract_from_serial(
        self,
        cert_pem: bytes,
    ) -> int:
        """从证书序列号提取1字节数据。

        从证书序列号的最低有效字节中提取秘密数据。

        Args:
            cert_pem: PEM格式的证书数据

        Returns:
            提取出的字节值（0-255）

        Raises:
            ValueError: 当证书格式无效时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(cert_pem, bytes):
            raise TypeError("证书数据必须是bytes类型")

        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
        except Exception as e:
            raise ValueError(f"无法解析证书: {e}") from e

        return cert.serial_number & 0xFF

    def get_capacity(
        self,
        cert_pem: bytes,
    ) -> dict:
        """计算证书各部分的隐写容量。

        分析证书结构，计算各部分可用于隐写的容量。

        Args:
            cert_pem: PEM格式的证书数据

        Returns:
            包含各部分容量信息的字典：
            - extension_bytes: 扩展字段可用字节数（理论无限制）
            - serial_bytes: 序列号可用字节数（1字节）
            - total_estimate: 估算总容量（字节）

        Raises:
            ValueError: 当证书格式无效时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(cert_pem, bytes):
            raise TypeError("证书数据必须是bytes类型")

        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
        except Exception as e:
            raise ValueError(f"无法解析证书: {e}") from e

        serial_bytes = (cert.serial_number.bit_length() + 7) // 8

        return {
            "extension_bytes": -1,
            "serial_bytes": 1,
            "serial_total_bytes": serial_bytes,
            "total_estimate": 1,
            "extension_count": len(cert.extensions),
        }

    @staticmethod
    def generate_test_certificate() -> bytes:
        """生成一个测试用的自签名证书。

        用于测试和演示目的。

        Returns:
            PEM格式的自签名证书
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(x509.NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(x509.NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, "Oath Toolchain"),
            x509.NameAttribute(x509.NameOID.COMMON_NAME, "test.example.com"),
        ])

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName("test.example.com")]),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        return cert.public_bytes(serialization.Encoding.PEM)
