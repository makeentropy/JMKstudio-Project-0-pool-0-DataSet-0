"""CA证书体系主工具模块。

提供JMKstudio CA证书体系工具的统一入口，集成CA管理、证书链验证、
证书生命周期管理等功能。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...core.base import OathTool
from ...core.exceptions import ValidationError
from ...core.registry import register_tool
from .certificate_chain import CertificateChain
from .certificate_lifecycle import CertificateLifecycleManager
from .certificate_types import CertificateType
from .jmk_ca import JMKStudioCA


@register_tool
class CASystemTool(OathTool):
    """JMKstudio CA证书体系工具。

    提供完整的CA证书体系管理功能，包括根CA初始化、中间CA创建、
    证书签发、验证、吊销、续期等操作。

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
        _ca: JMKstudio CA实例
    """

    name: str = "ca_system"
    description: str = "JMKstudio CA证书体系工具"
    _version: str = "0.1.0"
    _tags: list[str] = ["crypto", "ca", "certificate", "pki"]
    _category: str = "crypto"

    def __init__(self) -> None:
        """初始化CA证书体系工具。"""
        super().__init__()
        self._ca: Optional[JMKStudioCA] = None
        self._lifecycle: Optional[CertificateLifecycleManager] = None
        self._chain_verifier = CertificateChain()

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具。

        根据action参数执行不同的CA证书体系操作。

        Args:
            params: 输入参数字典，必须包含action字段
                支持的action:
                - init_root: 初始化根CA
                - create_intermediate: 创建中间CA
                - issue_cert: 签发证书
                - verify_cert: 验证证书
                - verify_chain: 验证证书链
                - revoke_cert: 吊销证书
                - renew_cert: 续期证书
                - list_certs: 列出证书
                - cert_info: 证书信息
                - generate_crl: 生成CRL

        Returns:
            执行结果字典

        Raises:
            ValidationError: 当参数验证失败时
        """
        self.validate_params(params)

        action = params.get("action")

        try:
            if action == "init_root":
                return self._action_init_root(params)
            elif action == "create_intermediate":
                return self._action_create_intermediate(params)
            elif action == "issue_cert":
                return self._action_issue_cert(params)
            elif action == "verify_cert":
                return self._action_verify_cert(params)
            elif action == "verify_chain":
                return self._action_verify_chain(params)
            elif action == "revoke_cert":
                return self._action_revoke_cert(params)
            elif action == "renew_cert":
                return self._action_renew_cert(params)
            elif action == "list_certs":
                return self._action_list_certs(params)
            elif action == "cert_info":
                return self._action_cert_info(params)
            elif action == "generate_crl":
                return self._action_generate_crl(params)
            else:
                raise ValidationError(
                    field="action",
                    message=f"不支持的操作: {action}",
                )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                field="execution",
                message=f"执行失败: {str(e)}",
            ) from e

    def validate_params(self, params: dict[str, Any]) -> bool:
        """验证输入参数。

        Args:
            params: 输入参数字典

        Returns:
            验证通过返回True

        Raises:
            ValidationError: 当参数验证失败时
        """
        if "action" not in params:
            raise ValidationError(
                field="action",
                message="缺少必需的action参数",
            )

        action = params["action"]
        valid_actions = [
            "init_root",
            "create_intermediate",
            "issue_cert",
            "verify_cert",
            "verify_chain",
            "revoke_cert",
            "renew_cert",
            "list_certs",
            "cert_info",
            "generate_crl",
        ]

        if action not in valid_actions:
            raise ValidationError(
                field="action",
                message=f"不支持的操作: {action}",
            )

        return True

    def _ensure_ca_initialized(self) -> None:
        """确保CA已初始化。

        Raises:
            ValidationError: 当CA未初始化时
        """
        if self._ca is None:
            raise ValidationError(
                field="ca",
                message="CA未初始化，请先执行init_root操作",
            )

    def _action_init_root(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行初始化根CA操作。"""
        ca_name = params.get("ca_name", "JMKstudio Root CA")
        key_size = params.get("key_size", 4096)
        validity_days = params.get("validity_days", 3650)

        self._ca = JMKStudioCA(ca_name=ca_name)
        cert_pem, key_pem = self._ca.initialize_root(
            key_size=key_size,
            validity_days=validity_days,
        )

        self._lifecycle = CertificateLifecycleManager(cert_pem, key_pem)
        self._chain_verifier.add_trusted_root(cert_pem)

        return {
            "success": True,
            "action": "init_root",
            "ca_name": ca_name,
            "certificate": cert_pem.decode("utf-8"),
            "private_key": key_pem.decode("utf-8"),
        }

    def _action_create_intermediate(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行创建中间CA操作。"""
        self._ensure_ca_initialized()

        ca_name = params.get("ca_name")
        if not ca_name:
            raise ValidationError(
                field="ca_name",
                message="缺少必需的ca_name参数",
            )

        ca_type_str = params.get("ca_type", "intermediate_ca")
        try:
            ca_type = CertificateType.from_string(ca_type_str)
        except ValueError as e:
            raise ValidationError(
                field="ca_type",
                message=f"无效的证书类型: {e}",
            ) from e

        validity_days = params.get("validity_days", 1825)

        cert_pem, key_pem = self._ca.create_intermediate_ca(
            ca_name=ca_name,
            ca_type=ca_type,
            validity_days=validity_days,
        )

        return {
            "success": True,
            "action": "create_intermediate",
            "ca_name": ca_name,
            "ca_type": ca_type_str,
            "certificate": cert_pem.decode("utf-8"),
            "private_key": key_pem.decode("utf-8"),
        }

    def _action_issue_cert(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行签发证书操作。"""
        self._ensure_ca_initialized()

        subject = params.get("subject")
        if not subject:
            raise ValidationError(
                field="subject",
                message="缺少必需的subject参数",
            )

        cert_type_str = params.get("cert_type", "end_entity")
        try:
            cert_type = CertificateType.from_string(cert_type_str)
        except ValueError as e:
            raise ValidationError(
                field="cert_type",
                message=f"无效的证书类型: {e}",
            ) from e

        issuer_ca = params.get("issuer_ca", "root")
        validity_days = params.get("validity_days", 365)
        key_size = params.get("key_size", 2048)
        extensions = params.get("extensions")

        cert_pem, key_pem = self._ca.issue_certificate(
            subject=subject,
            cert_type=cert_type,
            issuer_ca=issuer_ca,
            extensions=extensions,
            validity_days=validity_days,
            key_size=key_size,
        )

        return {
            "success": True,
            "action": "issue_cert",
            "subject": subject,
            "cert_type": cert_type_str,
            "issuer_ca": issuer_ca,
            "certificate": cert_pem.decode("utf-8"),
            "private_key": key_pem.decode("utf-8"),
        }

    def _action_verify_cert(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行验证证书操作。"""
        self._ensure_ca_initialized()

        cert_pem = self._get_cert_param(params, "certificate")

        valid, message = self._ca.verify_certificate(cert_pem)

        return {
            "success": True,
            "action": "verify_cert",
            "valid": valid,
            "message": message,
        }

    def _action_verify_chain(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行验证证书链操作。"""
        cert_pem = self._get_cert_param(params, "certificate")

        intermediate_certs = params.get("intermediate_certs", [])
        intermediate_pems = []
        for cert in intermediate_certs:
            if isinstance(cert, str):
                intermediate_pems.append(cert.encode("utf-8"))
            else:
                intermediate_pems.append(cert)

        chain = self._chain_verifier.build_chain(cert_pem, intermediate_pems)
        valid, message = self._chain_verifier.verify_chain(chain)
        chain_info = self._chain_verifier.get_chain_info(chain)

        return {
            "success": True,
            "action": "verify_chain",
            "valid": valid,
            "message": message,
            "chain_depth": len(chain),
            "chain_info": chain_info,
        }

    def _action_revoke_cert(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行吊销证书操作。"""
        self._ensure_ca_initialized()

        serial_number = params.get("serial_number")
        if not serial_number:
            raise ValidationError(
                field="serial_number",
                message="缺少必需的serial_number参数",
            )

        reason = params.get("reason", "unspecified")

        revoked = self._ca.revoke_certificate(serial_number, reason)

        if self._lifecycle:
            self._lifecycle.revoke_cert(serial_number, reason)

        return {
            "success": True,
            "action": "revoke_cert",
            "revoked": revoked,
            "serial_number": serial_number,
            "reason": reason,
        }

    def _action_renew_cert(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行续期证书操作。"""
        if self._lifecycle is None:
            raise ValidationError(
                field="ca",
                message="CA未初始化，请先执行init_root操作",
            )

        cert_pem = self._get_cert_param(params, "certificate")
        private_key_pem = self._get_cert_param(params, "private_key")
        new_validity_days = params.get("new_validity_days")

        new_cert_pem, new_key_pem = self._lifecycle.renew_cert(
            cert_pem,
            private_key_pem,
            new_validity_days=new_validity_days,
        )

        return {
            "success": True,
            "action": "renew_cert",
            "certificate": new_cert_pem.decode("utf-8"),
            "private_key": new_key_pem.decode("utf-8"),
        }

    def _action_list_certs(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行列出证书操作。"""
        self._ensure_ca_initialized()

        status = params.get("status")

        certs = self._ca.list_certificates(status)

        return {
            "success": True,
            "action": "list_certs",
            "count": len(certs),
            "certificates": certs,
        }

    def _action_cert_info(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行证书信息查询操作。"""
        cert_pem = self._get_cert_param(params, "certificate")

        if self._lifecycle:
            info = self._lifecycle.export_cert_info(cert_pem)
        elif self._ca:
            info = self._ca.get_certificate_info(cert_pem)
        else:
            from cryptography import x509
            from cryptography.x509.oid import NameOID

            cert = x509.load_pem_x509_certificate(cert_pem)
            subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)

            info = {
                "serial_number": str(cert.serial_number),
                "subject": subject_cn[0].value if subject_cn else "Unknown",
                "issuer": issuer_cn[0].value if issuer_cn else "Unknown",
                "not_valid_before": cert.not_valid_before_utc.isoformat(),
                "not_valid_after": cert.not_valid_after_utc.isoformat(),
                "signature_algorithm": cert.signature_algorithm_oid._name,
                "version": cert.version.value,
            }

        return {
            "success": True,
            "action": "cert_info",
            "info": info,
        }

    def _action_generate_crl(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行生成CRL操作。"""
        if self._lifecycle is None:
            raise ValidationError(
                field="ca",
                message="CA未初始化，请先执行init_root操作",
            )

        next_update_days = params.get("next_update_days", 30)

        crl_pem = self._lifecycle.generate_crl(next_update_days=next_update_days)

        return {
            "success": True,
            "action": "generate_crl",
            "crl": crl_pem.decode("utf-8"),
        }

    def _get_cert_param(self, params: dict[str, Any], key: str) -> bytes:
        """获取证书参数。

        Args:
            params: 参数字典
            key: 参数名

        Returns:
            证书字节

        Raises:
            ValidationError: 当参数不存在或类型错误时
        """
        if key not in params:
            raise ValidationError(
                field=key,
                message=f"缺少必需的参数: {key}",
            )

        value = params[key]
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            return value.encode("utf-8")
        else:
            raise ValidationError(
                field=key,
                message=f"参数{key}必须是bytes或str类型",
            )
