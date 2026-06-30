"""CA证书命令模块。

提供CA证书管理的命令行接口。
"""
from __future__ import annotations

from typing import Optional

import click

from ..context import CLIContext, pass_context


_ca_instance = None


def _load_ca_and_get_tool(ctx: CLIContext, ca_cert_path: str, ca_key_path: str):
    """加载CA证书和私钥，返回配置好的CA工具。"""
    ca_tool = _get_ca_tool(ctx)

    with open(ca_cert_path, "r", encoding="utf-8") as f:
        ca_cert_pem = f.read()
    with open(ca_key_path, "r", encoding="utf-8") as f:
        ca_key_pem = f.read()

    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    from ...tools.ca_system.jmk_ca import JMKStudioCA
    ca = JMKStudioCA(ca_name="CA")
    ca._root_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode("utf-8"), default_backend())
    ca._root_key = serialization.load_pem_private_key(ca_key_pem.encode("utf-8"), password=None, backend=default_backend())
    ca_tool._ca = ca
    return ca_tool


def _get_ca_tool(ctx: CLIContext):
    """获取CA工具实例。"""
    global _ca_instance
    if _ca_instance is None:
        from ...tools.ca_system.tool import CASystemTool
        _ca_instance = CASystemTool()
    return _ca_instance


@click.group(name="ca")
def ca_cli() -> None:
    """CA证书管理命令。

    提供根CA初始化、中间CA创建、证书签发、验证、吊销等功能。
    """
    pass


@ca_cli.command(name="init-root")
@click.option("--name", "-n", default="JMKstudio Root CA", help="根CA名称")
@click.option("--key-size", type=int, default=4096, help="密钥位数")
@click.option("--validity-days", type=int, default=3650, help="有效期(天)")
@click.option("--cert-out", default="root_ca.crt", type=click.Path(dir_okay=False), help="证书输出路径")
@click.option("--key-out", default="root_ca.key", type=click.Path(dir_okay=False), help="私钥输出路径")
@pass_context
def ca_init_root(
    ctx: CLIContext,
    name: str,
    key_size: int,
    validity_days: int,
    cert_out: str,
    key_out: str,
) -> None:
    """初始化根CA。"""
    try:
        ca_tool = _get_ca_tool(ctx)
        result = ca_tool.execute({
            "action": "init_root",
            "ca_name": name,
            "key_size": key_size,
            "validity_days": validity_days,
        })

        if result.get("success"):
            cert_pem = result.get("certificate", "")
            key_pem = result.get("private_key", "")

            with open(cert_out, "w", encoding="utf-8") as f:
                f.write(cert_pem)
            with open(key_out, "w", encoding="utf-8") as f:
                f.write(key_pem)

            output_result = {
                "success": True,
                "action": "ca_init_root",
                "ca_name": name,
                "certificate": cert_out,
                "private_key": key_out,
                "key_size": key_size,
                "validity_days": validity_days,
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "根CA初始化失败"))
    except Exception as e:
        ctx.error(f"根CA初始化失败: {e}")


@ca_cli.command(name="create-intermediate")
@click.option("--name", "-n", required=True, help="中间CA名称")
@click.option("--type", "-t", "ca_type", default="intermediate_ca", help="CA类型")
@click.option("--validity-days", type=int, default=1825, help="有效期(天)")
@click.option("--root-cert", required=True, type=click.Path(exists=True, dir_okay=False), help="根CA证书路径")
@click.option("--root-key", required=True, type=click.Path(exists=True, dir_okay=False), help="根CA私钥路径")
@click.option("--cert-out", default="intermediate_ca.crt", type=click.Path(dir_okay=False), help="证书输出路径")
@click.option("--key-out", default="intermediate_ca.key", type=click.Path(dir_okay=False), help="私钥输出路径")
@pass_context
def ca_create_intermediate(
    ctx: CLIContext,
    name: str,
    ca_type: str,
    validity_days: int,
    root_cert: str,
    root_key: str,
    cert_out: str,
    key_out: str,
) -> None:
    """创建中间CA。"""
    try:
        ca_tool = _load_ca_and_get_tool(ctx, root_cert, root_key)

        result = ca_tool.execute({
            "action": "create_intermediate",
            "ca_name": name,
            "ca_type": ca_type,
            "validity_days": validity_days,
        })

        if result.get("success"):
            cert_pem = result.get("certificate", "")
            key_pem = result.get("private_key", "")

            with open(cert_out, "w", encoding="utf-8") as f:
                f.write(cert_pem)
            with open(key_out, "w", encoding="utf-8") as f:
                f.write(key_pem)

            output_result = {
                "success": True,
                "action": "ca_create_intermediate",
                "ca_name": name,
                "ca_type": ca_type,
                "certificate": cert_out,
                "private_key": key_out,
                "validity_days": validity_days,
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "创建中间CA失败"))
    except Exception as e:
        ctx.error(f"创建中间CA失败: {e}")


@ca_cli.command(name="issue")
@click.option("--subject", "-s", required=True, help="证书主体")
@click.option("--type", "-t", "cert_type", default="end_entity", help="证书类型")
@click.option("--validity-days", type=int, default=365, help="有效期(天)")
@click.option("--key-size", type=int, default=2048, help="密钥位数")
@click.option("--ca-cert", required=True, type=click.Path(exists=True, dir_okay=False), help="CA证书路径")
@click.option("--ca-key", required=True, type=click.Path(exists=True, dir_okay=False), help="CA私钥路径")
@click.option("--cert-out", default="cert.crt", type=click.Path(dir_okay=False), help="证书输出路径")
@click.option("--key-out", default="cert.key", type=click.Path(dir_okay=False), help="私钥输出路径")
@pass_context
def ca_issue(
    ctx: CLIContext,
    subject: str,
    cert_type: str,
    validity_days: int,
    key_size: int,
    ca_cert: str,
    ca_key: str,
    cert_out: str,
    key_out: str,
) -> None:
    """签发证书。"""
    try:
        ca_tool = _load_ca_and_get_tool(ctx, ca_cert, ca_key)

        result = ca_tool.execute({
            "action": "issue_cert",
            "subject": subject,
            "cert_type": cert_type,
            "validity_days": validity_days,
            "key_size": key_size,
        })

        if result.get("success"):
            cert_pem = result.get("certificate", "")
            key_pem = result.get("private_key", "")

            with open(cert_out, "w", encoding="utf-8") as f:
                f.write(cert_pem)
            with open(key_out, "w", encoding="utf-8") as f:
                f.write(key_pem)

            output_result = {
                "success": True,
                "action": "ca_issue",
                "subject": subject,
                "cert_type": cert_type,
                "certificate": cert_out,
                "private_key": key_out,
                "validity_days": validity_days,
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "签发证书失败"))
    except Exception as e:
        ctx.error(f"签发证书失败: {e}")


@ca_cli.command(name="verify")
@click.option("--cert", "-c", "cert_file", required=True, type=click.Path(exists=True, dir_okay=False), help="待验证证书路径")
@click.option("--ca-cert", "ca_cert_file", default=None, type=click.Path(exists=True, dir_okay=False), help="CA证书路径")
@pass_context
def ca_verify(ctx: CLIContext, cert_file: str, ca_cert_file: Optional[str]) -> None:
    """验证证书。"""
    try:
        with open(cert_file, "r", encoding="utf-8") as f:
            cert_pem = f.read()

        ca_tool = _get_ca_tool(ctx)

        if ca_cert_file:
            with open(ca_cert_file, "r", encoding="utf-8") as f:
                ca_cert_pem = f.read()

            from ...tools.ca_system.certificate_chain import CertificateChain
            chain_verifier = CertificateChain()
            chain_verifier.add_trusted_root(ca_cert_pem.encode("utf-8"))
            chain = chain_verifier.build_chain(cert_pem.encode("utf-8"), [])
            valid, message = chain_verifier.verify_chain(chain)
        else:
            from cryptography import x509
            from datetime import datetime, timezone
            cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
            now = datetime.now(timezone.utc)
            valid = cert.not_valid_before_utc <= now <= cert.not_valid_after_utc
            message = "证书在有效期内" if valid else "证书已过期或尚未生效"

        result = {
            "success": True,
            "action": "ca_verify",
            "certificate": cert_file,
            "valid": valid,
            "message": message,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"验证证书失败: {e}")


@ca_cli.command(name="revoke")
@click.option("--serial", "-s", required=True, help="证书序列号")
@click.option("--reason", "-r", default="unspecified", help="吊销原因")
@click.option("--ca-cert", required=True, type=click.Path(exists=True, dir_okay=False), help="CA证书路径")
@click.option("--ca-key", required=True, type=click.Path(exists=True, dir_okay=False), help="CA私钥路径")
@pass_context
def ca_revoke(
    ctx: CLIContext,
    serial: str,
    reason: str,
    ca_cert: str,
    ca_key: str,
) -> None:
    """吊销证书。"""
    try:
        ca_tool = _load_ca_and_get_tool(ctx, ca_cert, ca_key)

        result = ca_tool.execute({
            "action": "revoke_cert",
            "serial_number": serial,
            "reason": reason,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "ca_revoke",
                "serial_number": serial,
                "reason": reason,
                "revoked": result.get("revoked", False),
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "吊销证书失败"))
    except Exception as e:
        ctx.error(f"吊销证书失败: {e}")


@ca_cli.command(name="list")
@click.option("--status", "-s", default=None, help="按状态筛选")
@click.option("--ca-cert", required=True, type=click.Path(exists=True, dir_okay=False), help="CA证书路径")
@click.option("--ca-key", required=True, type=click.Path(exists=True, dir_okay=False), help="CA私钥路径")
@pass_context
def ca_list(ctx: CLIContext, status: Optional[str], ca_cert: str, ca_key: str) -> None:
    """列出证书。"""
    try:
        ca_tool = _load_ca_and_get_tool(ctx, ca_cert, ca_key)

        result = ca_tool.execute({
            "action": "list_certs",
            "status": status,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "ca_list",
                "count": result.get("count", 0),
                "certificates": result.get("certificates", []),
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "列出证书失败"))
    except Exception as e:
        ctx.error(f"列出证书失败: {e}")


@ca_cli.command(name="info")
@click.option("--cert", "-c", "cert_file", required=True, type=click.Path(exists=True, dir_okay=False), help="证书文件路径")
@pass_context
def ca_info(ctx: CLIContext, cert_file: str) -> None:
    """查看证书信息。"""
    try:
        with open(cert_file, "r", encoding="utf-8") as f:
            cert_pem = f.read()

        ca_tool = _get_ca_tool(ctx)
        result = ca_tool.execute({
            "action": "cert_info",
            "certificate": cert_pem,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "ca_info",
                "certificate": cert_file,
                "info": result.get("info", {}),
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "获取证书信息失败"))
    except Exception as e:
        ctx.error(f"获取证书信息失败: {e}")
