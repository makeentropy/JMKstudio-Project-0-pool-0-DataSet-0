"""证书链管理模块。

提供证书链的构建、验证和信息获取功能，支持多级CA证书链的处理。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.x509.oid import NameOID

from .certificate_types import CertificateType


CERT_TYPE_OID = x509.ObjectIdentifier("1.3.6.1.4.1.99999.4")


class CertificateChain:
    """证书链管理器。

    提供证书链的构建、验证和信息查询功能，支持多级证书链的处理。

    Attributes:
        _trusted_roots: 受信任的根证书列表
    """

    def __init__(self, trusted_roots: Optional[List[bytes]] = None) -> None:
        """初始化证书链管理器。

        Args:
            trusted_roots: 受信任的根证书列表（PEM格式）
        """
        self._trusted_roots: List[x509.Certificate] = []
        if trusted_roots:
            for root_pem in trusted_roots:
                root_cert = x509.load_pem_x509_certificate(root_pem)
                self._trusted_roots.append(root_cert)

    def add_trusted_root(self, root_pem: bytes) -> None:
        """添加受信任的根证书。

        Args:
            root_pem: PEM格式的根证书
        """
        root_cert = x509.load_pem_x509_certificate(root_pem)
        self._trusted_roots.append(root_cert)

    def build_chain(
        self,
        end_cert: bytes,
        intermediate_certs: Optional[List[bytes]] = None,
    ) -> List[bytes]:
        """构建证书链。

        从终端实体证书开始，逐级向上查找签发者，构建完整的证书链。

        Args:
            end_cert: 终端实体证书（PEM格式）
            intermediate_certs: 中间证书列表（PEM格式）

        Returns:
            证书链列表，按终端实体到根的顺序排列（PEM格式）

        Raises:
            ValueError: 当无法构建完整的证书链时
        """
        end_certificate = x509.load_pem_x509_certificate(end_cert)

        intermediates = []
        if intermediate_certs:
            for cert_pem in intermediate_certs:
                intermediates.append(x509.load_pem_x509_certificate(cert_pem))

        chain = [end_certificate]
        current_cert = end_certificate

        while True:
            issuer = current_cert.issuer

            if self._is_self_signed(current_cert):
                break

            next_cert = self._find_issuer(issuer, intermediates)
            if next_cert is None:
                next_cert = self._find_issuer(issuer, self._trusted_roots)

            if next_cert is None:
                break

            chain.append(next_cert)
            current_cert = next_cert

            if self._is_self_signed(current_cert):
                break

        return [cert.public_bytes(serialization.Encoding.PEM) for cert in chain]

    def verify_chain(self, cert_chain: List[bytes]) -> Tuple[bool, str]:
        """验证证书链。

        验证证书链中的每一级签名，确保整个链条的有效性。

        Args:
            cert_chain: 证书链列表，按终端实体到根的顺序排列（PEM格式）

        Returns:
            (验证结果, 消息) 元组
        """
        if not cert_chain:
            return False, "证书链为空"

        try:
            certificates = [
                x509.load_pem_x509_certificate(cert_pem) for cert_pem in cert_chain
            ]
        except Exception as e:
            return False, f"证书解析失败: {str(e)}"

        now = datetime.now(timezone.utc)

        for i, cert in enumerate(certificates):
            if now < cert.not_valid_before_utc:
                return False, f"证书链第{i + 1}级证书尚未生效"
            if now > cert.not_valid_after_utc:
                return False, f"证书链第{i + 1}级证书已过期"

        for i in range(len(certificates) - 1):
            child_cert = certificates[i]
            parent_cert = certificates[i + 1]

            if child_cert.issuer != parent_cert.subject:
                return False, f"证书链第{i + 1}级与第{i + 2}级颁发者不匹配"

            try:
                parent_public_key = parent_cert.public_key()
                parent_public_key.verify(
                    child_cert.signature,
                    child_cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    child_cert.signature_hash_algorithm,
                )
            except InvalidSignature:
                return False, f"证书链第{i + 1}级签名验证失败"
            except Exception as e:
                return False, f"证书链验证出错: {str(e)}"

            try:
                basic_constraints = parent_cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.BASIC_CONSTRAINTS
                )
                if not basic_constraints.value.ca:
                    return False, f"证书链第{i + 2}级不是CA证书"
            except x509.ExtensionNotFound:
                return False, f"证书链第{i + 2}级缺少BasicConstraints扩展"

        root_cert = certificates[-1]
        if self._is_self_signed(root_cert):
            if self._trusted_roots:
                is_trusted = any(
                    self._certs_equal(root_cert, trusted)
                    for trusted in self._trusted_roots
                )
                if not is_trusted:
                    return False, "根证书不在信任列表中"

        return True, "证书链验证通过"

    def get_chain_depth(self, cert_chain: List[bytes]) -> int:
        """获取证书链深度。

        Args:
            cert_chain: 证书链列表（PEM格式）

        Returns:
            证书链深度（证书数量）
        """
        return len(cert_chain)

    def get_chain_info(self, cert_chain: List[bytes]) -> List[Dict[str, Any]]:
        """获取链中每个证书的信息。

        Args:
            cert_chain: 证书链列表（PEM格式）

        Returns:
            证书信息列表
        """
        info_list = []
        for i, cert_pem in enumerate(cert_chain):
            try:
                cert = x509.load_pem_x509_certificate(cert_pem)
                info = self._get_cert_info(cert, i)
                info_list.append(info)
            except Exception as e:
                info_list.append({
                    "index": i,
                    "error": f"解析失败: {str(e)}",
                })
        return info_list

    def _is_self_signed(self, cert: x509.Certificate) -> bool:
        """判断证书是否为自签名证书。

        Args:
            cert: 证书对象

        Returns:
            自签名返回True，否则返回False
        """
        if cert.issuer != cert.subject:
            return False

        try:
            public_key = cert.public_key()
            public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
            return True
        except Exception:
            return False

    def _find_issuer(
        self,
        issuer_name: x509.Name,
        cert_pool: List[x509.Certificate],
    ) -> Optional[x509.Certificate]:
        """在证书池中查找颁发者。

        Args:
            issuer_name: 颁发者名称
            cert_pool: 证书池

        Returns:
            找到的颁发者证书，未找到返回None
        """
        for cert in cert_pool:
            if cert.subject == issuer_name:
                return cert
        return None

    def _certs_equal(self, cert1: x509.Certificate, cert2: x509.Certificate) -> bool:
        """比较两个证书是否相同。

        Args:
            cert1: 证书1
            cert2: 证书2

        Returns:
            相同返回True，否则返回False
        """
        return cert1.public_bytes(serialization.Encoding.DER) == cert2.public_bytes(serialization.Encoding.DER)

    def _get_cert_info(self, cert: x509.Certificate, index: int) -> Dict[str, Any]:
        """获取证书信息。

        Args:
            cert: 证书对象
            index: 在链中的索引

        Returns:
            证书信息字典
        """
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

        return {
            "index": index,
            "serial_number": str(cert.serial_number),
            "subject": subject_cn[0].value if subject_cn else "Unknown",
            "issuer": issuer_cn[0].value if issuer_cn else "Unknown",
            "not_valid_before": cert.not_valid_before_utc.isoformat(),
            "not_valid_after": cert.not_valid_after_utc.isoformat(),
            "cert_type": cert_type.value if cert_type else "unknown",
            "is_ca": is_ca,
            "signature_algorithm": cert.signature_algorithm_oid._name,
            "version": cert.version.value,
            "is_self_signed": self._is_self_signed(cert),
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
