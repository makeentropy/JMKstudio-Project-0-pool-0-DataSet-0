"""加密命令模块。

提供多种加密方法的命令行接口。
"""
from __future__ import annotations

import base64
import json
from typing import Optional

import click

from ..context import CLIContext, pass_context


@click.group(name="encrypt")
def encrypt_cli() -> None:
    """加密命令。

    支持多种加密方法: AES, RSA, KARMACA, 几何加密, 完整加密管道。
    """
    pass


@encrypt_cli.command(name="aes")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="密钥文件路径")
@pass_context
def encrypt_aes(ctx: CLIContext, input_file: str, output_file: str, key: str) -> None:
    """使用AES-GCM加密文件。"""
    try:
        with open(input_file, "rb") as f:
            plaintext = f.read()
        with open(key, "rb") as f:
            key_bytes = f.read()

        from ...core.crypto.primitives import AESCipher
        ciphertext, nonce, tag = AESCipher.encrypt(plaintext, key_bytes)

        with open(output_file, "wb") as f:
            f.write(nonce + tag + ciphertext)

        result = {
            "success": True,
            "action": "encrypt_aes",
            "input": input_file,
            "output": output_file,
            "input_size": len(plaintext),
            "output_size": len(nonce) + len(tag) + len(ciphertext),
            "method": "AES-256-GCM",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"AES加密失败: {e}")


@encrypt_cli.command(name="rsa")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="公钥文件路径")
@pass_context
def encrypt_rsa(ctx: CLIContext, input_file: str, output_file: str, key: str) -> None:
    """使用RSA-OAEP加密文件。"""
    try:
        with open(input_file, "rb") as f:
            plaintext = f.read()
        with open(key, "rb") as f:
            public_key_pem = f.read()

        from ...core.crypto.primitives import RSACipher
        public_key = RSACipher.deserialize_public_key(public_key_pem)
        ciphertext = RSACipher.encrypt(plaintext, public_key)

        with open(output_file, "wb") as f:
            f.write(ciphertext)

        result = {
            "success": True,
            "action": "encrypt_rsa",
            "input": input_file,
            "output": output_file,
            "input_size": len(plaintext),
            "output_size": len(ciphertext),
            "method": "RSA-OAEP",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"RSA加密失败: {e}")


@encrypt_cli.command(name="karmaca")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="空间字典文件路径(JSON)")
@click.option("--coordinate", "-c", required=True, help="坐标点，逗号分隔，例如: '1.0,2.0,3.0'")
@click.option("--no-interpolation", is_flag=True, help="不使用插值密钥")
@pass_context
def encrypt_karmaca(
    ctx: CLIContext,
    input_file: str,
    output_file: str,
    key: str,
    coordinate: str,
    no_interpolation: bool,
) -> None:
    """使用KARMACA空间字典加密文件。"""
    try:
        with open(input_file, "rb") as f:
            plaintext = f.read()
        with open(key, "r", encoding="utf-8") as f:
            space_dict_data = json.load(f)

        coord_list = [float(x.strip()) for x in coordinate.split(",")]

        from ...tools.karmaca.encryption import KarmacaEncryption
        from ...tools.karmaca.space_dict import KarmaSpaceDict
        from ...core.math.vector import Vector

        space_dict = KarmaSpaceDict()
        space_dict.from_dict(space_dict_data)

        karmaca = KarmacaEncryption()
        ciphertext = karmaca.encrypt(
            plaintext,
            Vector(coord_list),
            space_dict,
            use_interpolation=not no_interpolation,
        )

        with open(output_file, "wb") as f:
            f.write(ciphertext)

        result = {
            "success": True,
            "action": "encrypt_karmaca",
            "input": input_file,
            "output": output_file,
            "input_size": len(plaintext),
            "output_size": len(ciphertext),
            "method": "KARMACA",
            "dimensions": len(coord_list),
            "interpolation": not no_interpolation,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"KARMACA加密失败: {e}")


@encrypt_cli.command(name="geometric")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, help="密钥字符串")
@click.option("--dimensions", "-d", type=int, default=4, help="几何哈希维度")
@pass_context
def encrypt_geometric(
    ctx: CLIContext,
    input_file: str,
    output_file: str,
    key: str,
    dimensions: int,
) -> None:
    """使用几何哈希派生密钥进行AES加密。"""
    try:
        with open(input_file, "rb") as f:
            plaintext = f.read()

        from ...tools.geometric_proof.geometric_hash import GeometricHash
        from ...core.crypto.primitives import AESCipher
        from ...core.crypto.kdf import KDF

        gh = GeometricHash(dimensions=dimensions, hash_alg="sha256")
        key_hash = gh.hash_data(key.encode("utf-8"))
        derived_key = KDF.hkdf(
            key_hash,
            salt=b"geometric_encryption",
            info=b"geometric_encryption_key",
            length=32,
        )

        ciphertext, nonce, tag = AESCipher.encrypt(plaintext, derived_key)

        with open(output_file, "wb") as f:
            f.write(nonce + tag + ciphertext)

        result = {
            "success": True,
            "action": "encrypt_geometric",
            "input": input_file,
            "output": output_file,
            "input_size": len(plaintext),
            "output_size": len(nonce) + len(tag) + len(ciphertext),
            "method": "Geometric-Hash + AES-256-GCM",
            "dimensions": dimensions,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"几何加密失败: {e}")


@encrypt_cli.command(name="full")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, help="加密密钥")
@pass_context
def encrypt_full(ctx: CLIContext, input_file: str, output_file: str, key: str) -> None:
    """完整加密管道（多层加密）。"""
    try:
        with open(input_file, "rb") as f:
            plaintext = f.read()

        from ...core.crypto.primitives import AESCipher
        from ...core.crypto.kdf import KDF
        from ...core.crypto.hash import Hash

        key_bytes = key.encode("utf-8") if isinstance(key, str) else key

        layer1_key = KDF.hkdf(
            key_bytes, salt=b"layer1", info=b"full_encryption_layer1", length=32
        )
        layer1_ct, nonce1, tag1 = AESCipher.encrypt(plaintext, layer1_key)

        layer2_key = KDF.hkdf(
            key_bytes, salt=b"layer2", info=b"full_encryption_layer2", length=32
        )
        layer2_data = nonce1 + tag1 + layer1_ct
        layer2_ct, nonce2, tag2 = AESCipher.encrypt(layer2_data, layer2_key)

        final_data = nonce2 + tag2 + layer2_ct

        with open(output_file, "wb") as f:
            f.write(final_data)

        result = {
            "success": True,
            "action": "encrypt_full",
            "input": input_file,
            "output": output_file,
            "input_size": len(plaintext),
            "output_size": len(final_data),
            "method": "Full Pipeline (AES-256-GCM x2)",
            "layers": 2,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"完整加密失败: {e}")
