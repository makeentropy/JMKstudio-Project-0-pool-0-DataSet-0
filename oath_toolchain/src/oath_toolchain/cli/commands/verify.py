"""验证命令模块。

提供多种验证方法的命令行接口。
"""
from __future__ import annotations

import base64
import json
from typing import Optional

import click

from ..context import CLIContext, pass_context


@click.group(name="verify")
def verify_cli() -> None:
    """验证命令。

    支持多种验证方法: RSA, HMAC, 几何证明, 多重签名, 证书验证。
    """
    pass


@verify_cli.command(name="rsa")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--signature", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="签名文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="公钥文件路径")
@pass_context
def verify_rsa(ctx: CLIContext, input_file: str, signature: str, key: str) -> None:
    """验证RSA-PSS签名。"""
    try:
        with open(input_file, "rb") as f:
            data = f.read()
        with open(signature, "rb") as f:
            sig_data = f.read()
        with open(key, "rb") as f:
            public_key_pem = f.read()

        from ...core.crypto.primitives import RSACipher
        public_key = RSACipher.deserialize_public_key(public_key_pem)
        valid = RSACipher.verify(data, sig_data, public_key)

        result = {
            "success": True,
            "action": "verify_rsa",
            "input": input_file,
            "signature": signature,
            "valid": valid,
            "method": "RSA-PSS",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"RSA验证失败: {e}")


@verify_cli.command(name="hmac")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--signature", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="签名文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="密钥文件路径")
@click.option("--alg", "-a", type=click.Choice(["sha256", "sha512"], case_sensitive=False), default="sha256", help="哈希算法")
@pass_context
def verify_hmac(
    ctx: CLIContext,
    input_file: str,
    signature: str,
    key: str,
    alg: str,
) -> None:
    """验证HMAC签名。"""
    try:
        import hmac
        import hashlib

        with open(input_file, "rb") as f:
            data = f.read()
        with open(signature, "rb") as f:
            sig_data = f.read()
        with open(key, "rb") as f:
            key_bytes = f.read()

        hash_func = hashlib.sha256 if alg.lower() == "sha256" else hashlib.sha512
        expected_sig = hmac.new(key_bytes, data, hash_func).digest()

        import hmac as hmac_mod
        valid = hmac_mod.compare_digest(expected_sig, sig_data)

        result = {
            "success": True,
            "action": "verify_hmac",
            "input": input_file,
            "signature": signature,
            "valid": valid,
            "algorithm": alg.upper(),
            "method": "HMAC",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"HMAC验证失败: {e}")


@verify_cli.command(name="geometric")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--signature", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="证明文件路径(JSON)")
@click.option("--dimensions", "-d", type=int, default=4, help="几何证明维度")
@pass_context
def verify_geometric(
    ctx: CLIContext,
    input_file: str,
    signature: str,
    dimensions: int,
) -> None:
    """验证几何证明签名。"""
    try:
        with open(input_file, "rb") as f:
            data = f.read()
        with open(signature, "r", encoding="utf-8") as f:
            proof = json.load(f)

        from ...tools.geometric_proof.proof_generator import GeometricProof

        gp = GeometricProof(dimensions=dimensions, hash_alg="sha256")
        valid = gp.verify_proof(data, proof)

        result = {
            "success": True,
            "action": "verify_geometric",
            "input": input_file,
            "signature": signature,
            "valid": valid,
            "dimensions": dimensions,
            "method": "Geometric Proof",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"几何证明验证失败: {e}")


@verify_cli.command(name="multi")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--signature", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="多重签名文件路径(JSON)")
@click.option("--keys", "-k", required=True, multiple=True, type=click.Path(exists=True, dir_okay=False), help="公钥文件路径（可多次指定）")
@pass_context
def verify_multi(
    ctx: CLIContext,
    input_file: str,
    signature: str,
    keys: tuple[str, ...],
) -> None:
    """验证多重签名。"""
    try:
        with open(input_file, "rb") as f:
            data = f.read()
        with open(signature, "r", encoding="utf-8") as f:
            sig_data = json.load(f)

        from ...core.crypto.primitives import RSACipher

        signatures = sig_data.get("signatures", [])
        results = []
        all_valid = True

        for i, key_path in enumerate(keys):
            if i >= len(signatures):
                break

            sig_info = signatures[i]
            sig_bytes = base64.b64decode(sig_info["signature"])

            with open(key_path, "rb") as f:
                key_data = f.read()

            if sig_info["type"] == "RSA":
                try:
                    public_key = RSACipher.deserialize_public_key(key_data)
                    valid = RSACipher.verify(data, sig_bytes, public_key)
                except Exception:
                    valid = False
            else:
                import hmac
                import hashlib
                expected = hmac.new(key_data, data, hashlib.sha256).digest()
                import hmac as hmac_mod
                valid = hmac_mod.compare_digest(expected, sig_bytes)

            if not valid:
                all_valid = False

            results.append({
                "index": i,
                "type": sig_info["type"],
                "valid": valid,
            })

        result = {
            "success": True,
            "action": "verify_multi",
            "input": input_file,
            "signature": signature,
            "all_valid": all_valid,
            "results": results,
            "method": "Multi-Signature",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"多重签名验证失败: {e}")


@verify_cli.command(name="cert")
@click.option("--cert", "-c", "cert_file", required=True, type=click.Path(exists=True, dir_okay=False), help="证书文件路径")
@click.option("--ca-cert", "ca_cert_file", default=None, type=click.Path(exists=True, dir_okay=False), help="CA证书文件路径")
@pass_context
def verify_cert(ctx: CLIContext, cert_file: str, ca_cert_file: Optional[str]) -> None:
    """验证证书有效性。"""
    try:
        with open(cert_file, "rb") as f:
            cert_pem = f.read()

        from ...tools.ca_system.certificate_chain import CertificateChain

        chain_verifier = CertificateChain()

        if ca_cert_file:
            with open(ca_cert_file, "rb") as f:
                ca_pem = f.read()
            chain_verifier.add_trusted_root(ca_pem)
            chain = chain_verifier.build_chain(cert_pem, [])
            valid, message = chain_verifier.verify_chain(chain)
        else:
            from cryptography import x509
            cert = x509.load_pem_x509_certificate(cert_pem)
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            valid = cert.not_valid_before_utc <= now <= cert.not_valid_after_utc
            message = "证书在有效期内" if valid else "证书已过期或尚未生效"

        result = {
            "success": True,
            "action": "verify_cert",
            "certificate": cert_file,
            "valid": valid,
            "message": message,
            "method": "Certificate Verification",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"证书验证失败: {e}")
