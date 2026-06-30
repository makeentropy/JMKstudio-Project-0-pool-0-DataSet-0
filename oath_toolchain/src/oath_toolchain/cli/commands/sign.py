"""签名命令模块。

提供多种签名方法的命令行接口。
"""
from __future__ import annotations

from typing import Optional

import click

from ..context import CLIContext, pass_context


@click.group(name="sign")
def sign_cli() -> None:
    """签名命令。

    支持多种签名方法: RSA, HMAC, 几何证明, 多重签名。
    """
    pass


@sign_cli.command(name="rsa")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="签名输出文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="私钥文件路径")
@pass_context
def sign_rsa(ctx: CLIContext, input_file: str, output_file: str, key: str) -> None:
    """使用RSA-PSS签名文件。"""
    try:
        with open(input_file, "rb") as f:
            data = f.read()
        with open(key, "rb") as f:
            private_key_pem = f.read()

        from ...core.crypto.primitives import RSACipher
        private_key = RSACipher.deserialize_private_key(private_key_pem)
        signature = RSACipher.sign(data, private_key)

        with open(output_file, "wb") as f:
            f.write(signature)

        result = {
            "success": True,
            "action": "sign_rsa",
            "input": input_file,
            "output": output_file,
            "signature_size": len(signature),
            "method": "RSA-PSS",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"RSA签名失败: {e}")


@sign_cli.command(name="hmac")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="签名输出文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="密钥文件路径")
@click.option("--alg", "-a", type=click.Choice(["sha256", "sha512"], case_sensitive=False), default="sha256", help="哈希算法")
@pass_context
def sign_hmac(
    ctx: CLIContext,
    input_file: str,
    output_file: str,
    key: str,
    alg: str,
) -> None:
    """使用HMAC签名文件。"""
    try:
        import hmac
        import hashlib

        with open(input_file, "rb") as f:
            data = f.read()
        with open(key, "rb") as f:
            key_bytes = f.read()

        hash_func = hashlib.sha256 if alg.lower() == "sha256" else hashlib.sha512
        signature = hmac.new(key_bytes, data, hash_func).digest()

        with open(output_file, "wb") as f:
            f.write(signature)

        result = {
            "success": True,
            "action": "sign_hmac",
            "input": input_file,
            "output": output_file,
            "signature_size": len(signature),
            "algorithm": alg.upper(),
            "method": "HMAC",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"HMAC签名失败: {e}")


@sign_cli.command(name="geometric")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="证明输出文件路径(JSON)")
@click.option("--key", "-k", required=True, help="秘密密钥字符串")
@click.option("--dimensions", "-d", type=int, default=4, help="几何证明维度")
@click.option("--num-proof-points", "-n", type=int, default=8, help="证明点数量")
@pass_context
def sign_geometric(
    ctx: CLIContext,
    input_file: str,
    output_file: str,
    key: str,
    dimensions: int,
    num_proof_points: int,
) -> None:
    """生成几何证明签名。"""
    try:
        import json

        with open(input_file, "rb") as f:
            data = f.read()

        from ...tools.geometric_proof.proof_generator import GeometricProof

        gp = GeometricProof(
            dimensions=dimensions,
            hash_alg="sha256",
            num_proof_points=num_proof_points,
        )
        proof = gp.generate_proof(data, key.encode("utf-8"))

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(proof, f, indent=2, ensure_ascii=False, default=str)

        result = {
            "success": True,
            "action": "sign_geometric",
            "input": input_file,
            "output": output_file,
            "dimensions": dimensions,
            "num_proof_points": num_proof_points,
            "method": "Geometric Proof",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"几何证明签名失败: {e}")


@sign_cli.command(name="multi")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="签名输出文件路径")
@click.option("--keys", "-k", required=True, multiple=True, type=click.Path(exists=True, dir_okay=False), help="私钥文件路径（可多次指定）")
@pass_context
def sign_multi(ctx: CLIContext, input_file: str, output_file: str, keys: tuple[str, ...]) -> None:
    """多重签名（RSA + HMAC）。"""
    try:
        import json

        with open(input_file, "rb") as f:
            data = f.read()

        from ...core.crypto.primitives import RSACipher

        signatures = []
        for i, key_path in enumerate(keys):
            with open(key_path, "rb") as f:
                key_data = f.read()

            try:
                private_key = RSACipher.deserialize_private_key(key_data)
                sig = RSACipher.sign(data, private_key)
                import base64
                signatures.append({
                    "index": i,
                    "type": "RSA",
                    "signature": base64.b64encode(sig).decode("utf-8"),
                })
            except Exception:
                import hmac
                import hashlib
                sig = hmac.new(key_data, data, hashlib.sha256).digest()
                import base64
                signatures.append({
                    "index": i,
                    "type": "HMAC",
                    "signature": base64.b64encode(sig).decode("utf-8"),
                })

        result_data = {
            "input": input_file,
            "signatures": signatures,
            "count": len(signatures),
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        result = {
            "success": True,
            "action": "sign_multi",
            "input": input_file,
            "output": output_file,
            "signature_count": len(signatures),
            "method": "Multi-Signature",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"多重签名失败: {e}")
