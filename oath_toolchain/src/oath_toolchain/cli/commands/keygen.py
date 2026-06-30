"""密钥生成命令模块。

提供多种密钥生成方法的命令行接口。
"""
from __future__ import annotations

import json
from typing import Optional

import click

from ..context import CLIContext, pass_context


@click.group(name="keygen")
def keygen_cli() -> None:
    """密钥生成命令。

    支持多种密钥类型: RSA, AES, NLP, KARMACA, 组合密钥。
    """
    pass


@keygen_cli.command(name="aes")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出密钥文件路径")
@click.option("--bits", type=int, default=256, help="密钥位数 (128/192/256)")
@pass_context
def keygen_aes(ctx: CLIContext, output_file: str, bits: int) -> None:
    """生成AES密钥。"""
    try:
        from ...core.crypto.primitives import AESCipher

        key = AESCipher.generate_key(bits)

        with open(output_file, "wb") as f:
            f.write(key)

        result = {
            "success": True,
            "action": "keygen_aes",
            "output": output_file,
            "key_size": bits,
            "key_size_bytes": len(key),
            "method": "AES",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"生成AES密钥失败: {e}")


@keygen_cli.command(name="rsa")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出私钥文件路径")
@click.option("--pubout", "pubkey_file", default=None, type=click.Path(dir_okay=False), help="输出公钥文件路径")
@click.option("--bits", type=int, default=4096, help="密钥位数")
@pass_context
def keygen_rsa(ctx: CLIContext, output_file: str, pubkey_file: Optional[str], bits: int) -> None:
    """生成RSA密钥对。"""
    try:
        from ...core.crypto.primitives import RSACipher

        private_key, public_key = RSACipher.generate_keypair(key_size=bits)

        private_pem = RSACipher.serialize_private_key(private_key)
        with open(output_file, "wb") as f:
            f.write(private_pem)

        if pubkey_file:
            public_pem = RSACipher.serialize_public_key(public_key)
            with open(pubkey_file, "wb") as f:
                f.write(public_pem)

        result = {
            "success": True,
            "action": "keygen_rsa",
            "private_key": output_file,
            "public_key": pubkey_file or "未单独保存",
            "key_size": bits,
            "method": "RSA",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"生成RSA密钥失败: {e}")


@keygen_cli.command(name="nlp")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出密钥文件路径")
@click.option("--text", "-t", required=True, help="用于生成密钥的文本")
@click.option("--mode", "-m", type=click.Choice(["semantic", "entropy", "hybrid"], case_sensitive=False), default="hybrid", help="密钥生成模式")
@click.option("--bits", type=int, default=256, help="密钥位数")
@click.option("--iterations", type=int, default=100000, help="迭代次数")
@pass_context
def keygen_nlp(
    ctx: CLIContext,
    output_file: str,
    text: str,
    mode: str,
    bits: int,
    iterations: int,
) -> None:
    """使用NLP从文本生成密钥。"""
    try:
        from ...tools.nlptcmodel.key_generator import NLPTCKeyGenerator

        keygen = NLPTCKeyGenerator()
        key_size_bytes = bits // 8
        key = keygen.generate_key(
            text=text,
            key_size=key_size_bytes,
            mode=mode.lower(),
            iterations=iterations,
        )

        with open(output_file, "wb") as f:
            f.write(key)

        result = {
            "success": True,
            "action": "keygen_nlp",
            "output": output_file,
            "key_size": bits,
            "mode": mode.lower(),
            "iterations": iterations,
            "method": "NLPTC",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"生成NLP密钥失败: {e}")


@keygen_cli.command(name="karmaca")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出空间字典文件路径(JSON)")
@click.option("--dimensions", "-d", type=int, default=3, help="空间字典维度")
@click.option("--size", "-s", type=int, default=100, help="字典大小（总点数）")
@pass_context
def keygen_karmaca(ctx: CLIContext, output_file: str, dimensions: int, size: int) -> None:
    """生成KARMACA空间字典密钥。"""
    try:
        from ...tools.karmaca.space_dict import KarmaSpaceDict
        from ...core.math.vector import Vector
        from ...core.crypto.random import get_random_bytes

        space_dict = KarmaSpaceDict(dimensions=dimensions)

        points = []
        keys = []
        import random
        for i in range(size):
            coord = [random.uniform(-10.0, 10.0) for _ in range(dimensions)]
            points.append(Vector(coord))
            keys.append(get_random_bytes(32))

        space_dict.build(points, keys)

        space_dict_data = space_dict.to_dict()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(space_dict_data, f, indent=2, ensure_ascii=False)

        result = {
            "success": True,
            "action": "keygen_karmaca",
            "output": output_file,
            "dimensions": dimensions,
            "size": size,
            "total_points": size,
            "method": "KARMACA Space Dictionary",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"生成KARMACA空间字典失败: {e}")


@keygen_cli.command(name="combined")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出组合密钥文件路径")
@click.option("--text", "-t", required=True, help="NLP密钥文本")
@click.option("--bits", type=int, default=256, help="最终密钥位数")
@pass_context
def keygen_combined(ctx: CLIContext, output_file: str, text: str, bits: int) -> None:
    """生成组合密钥（NLP + 几何哈希）。"""
    try:
        from ...tools.nlptcmodel.key_generator import NLPTCKeyGenerator
        from ...tools.geometric_proof.geometric_hash import GeometricHash
        from ...core.crypto.kdf import KDF
        from ...core.crypto.hash import Hash

        nlp_keygen = NLPTCKeyGenerator()
        nlp_key = nlp_keygen.generate_key(text=text, key_size=32, mode="hybrid")

        gh = GeometricHash(dimensions=4, hash_alg="sha256")
        geo_hash = gh.hash_data(text.encode("utf-8"))

        combined = bytearray()
        combined.extend(nlp_key)
        combined.extend(geo_hash)
        combined.extend(b"combined_key_salt")

        final_key = KDF.hkdf(
            bytes(combined),
            salt=b"oath_combined_key",
            info=b"combined_key_derivation",
            length=bits // 8,
        )

        with open(output_file, "wb") as f:
            f.write(final_key)

        result = {
            "success": True,
            "action": "keygen_combined",
            "output": output_file,
            "key_size": bits,
            "components": ["NLPTC", "Geometric Hash"],
            "method": "Combined (NLP + Geometric)",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"生成组合密钥失败: {e}")
