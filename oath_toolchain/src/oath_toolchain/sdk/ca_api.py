"""CA证书API模块。

提供CA证书体系管理的高层API，包括根CA初始化、中间CA创建、
证书签发、验证、吊销等功能。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core.crypto.primitives import RSACipher


class CAAPI:
    """CA证书API类。

    提供完整的CA证书体系管理功能，包括根CA初始化、中间CA创建、
    证书签发、验证、吊销、续期等操作。

    Attributes:
        engine: 乾坤引擎实例
    """

    def __init__(self, engine: Any) -> None:
        """初始化CA证书API。

        Args:
            engine: 乾坤引擎实例
        """
        self._engine = engine
        self._ca_tool = None
        self._ensure_tool()

    def _ensure_tool(self) -> None:
        """确保CA工具已初始化。"""
        try:
            self._ca_tool = self._engine.get_tool("ca_system")
        except Exception:
            from ..tools.ca_system.tool import CASystemTool
            self._ca_tool = CASystemTool()
            try:
                self._engine.register_tool(self._ca_tool)
            except Exception:
                pass

    def init_root_ca(self, name: str = "JMKstudio Root CA") -> Dict[str, Any]:
        """初始化根CA。

        Args:
            name: 根CA名称，默认为"JMKstudio Root CA"

        Returns:
            根CA信息字典，包含：
                - success: 是否成功
                - ca_name: CA名称
                - certificate: 根证书PEM字符串
                - private_key: 根私钥PEM字符串
        """
        result = self._ca_tool.execute({
            "action": "init_root",
            "ca_name": name,
        })
        return result

    def create_intermediate_ca(
        self,
        name: str,
        ca_type: str = "intermediate_ca",
    ) -> Dict[str, Any]:
        """创建中间CA。

        Args:
            name: 中间CA名称
            ca_type: CA类型，默认为"intermediate_ca"

        Returns:
            中间CA信息字典，包含：
                - success: 是否成功
                - ca_name: CA名称
                - ca_type: CA类型
                - certificate: 证书PEM字符串
                - private_key: 私钥PEM字符串
        """
        result = self._ca_tool.execute({
            "action": "create_intermediate",
            "ca_name": name,
            "ca_type": ca_type,
        })
        return result

    def issue_certificate(
        self,
        subject: str,
        cert_type: str = 'end_entity',
        issuer: str = 'root',
    ) -> Dict[str, Any]:
        """签发证书。

        Args:
            subject: 证书主题（通用名称）
            cert_type: 证书类型，默认为'end_entity'
            issuer: 签发者，默认为'root'

        Returns:
            证书信息字典，包含：
                - success: 是否成功
                - subject: 证书主题
                - cert_type: 证书类型
                - issuer_ca: 签发CA
                - certificate: 证书PEM字符串
                - private_key: 私钥PEM字符串
        """
        result = self._ca_tool.execute({
            "action": "issue_cert",
            "subject": subject,
            "cert_type": cert_type,
            "issuer_ca": issuer,
        })
        return result

    def verify_certificate(self, cert_pem: bytes) -> Dict[str, Any]:
        """验证证书。

        Args:
            cert_pem: PEM格式的证书字节

        Returns:
            验证结果字典，包含：
                - success: 是否成功
                - valid: 证书是否有效
                - message: 验证消息
        """
        result = self._ca_tool.execute({
            "action": "verify_cert",
            "certificate": cert_pem,
        })
        return result

    def revoke_certificate(
        self,
        serial_number: str,
        reason: str = "unspecified",
    ) -> bool:
        """吊销证书。

        Args:
            serial_number: 证书序列号
            reason: 吊销原因，默认为"unspecified"

        Returns:
            吊销成功返回True，否则返回False
        """
        result = self._ca_tool.execute({
            "action": "revoke_cert",
            "serial_number": serial_number,
            "reason": reason,
        })
        return result.get("revoked", False)

    def list_certificates(self, status: str = None) -> List[Dict[str, Any]]:
        """列出证书。

        Args:
            status: 证书状态过滤，可选

        Returns:
            证书列表
        """
        params = {"action": "list_certs"}
        if status is not None:
            params["status"] = status

        result = self._ca_tool.execute(params)
        return result.get("certificates", [])

    def get_cert_info(self, cert_pem: bytes) -> Dict[str, Any]:
        """获取证书信息。

        Args:
            cert_pem: PEM格式的证书字节

        Returns:
            证书信息字典
        """
        result = self._ca_tool.execute({
            "action": "cert_info",
            "certificate": cert_pem,
        })
        return result.get("info", {})

    def sign_with_cert(
        self,
        data: bytes,
        cert_pem: bytes,
        key_pem: bytes,
    ) -> bytes:
        """使用证书私钥签名数据。

        Args:
            data: 待签名的数据
            cert_pem: PEM格式的证书字节
            key_pem: PEM格式的私钥字节

        Returns:
            签名数据
        """
        private_key = RSACipher.deserialize_private_key(key_pem)
        return RSACipher.sign(data, private_key)

    def verify_with_cert(
        self,
        data: bytes,
        signature: bytes,
        cert_pem: bytes,
    ) -> bool:
        """使用证书公钥验证签名。

        Args:
            data: 原始数据
            signature: 签名数据
            cert_pem: PEM格式的证书字节

        Returns:
            验证通过返回True，否则返回False
        """
        from cryptography import x509
        cert = x509.load_pem_x509_certificate(cert_pem)
        public_key = cert.public_key()
        from cryptography.hazmat.primitives.asymmetric import rsa
        if isinstance(public_key, rsa.RSAPublicKey):
            return RSACipher.verify(data, signature, public_key)
        return False
