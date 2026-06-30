"""解密命令模块。

提供多种解密方法的命令行接口。
"""
from __future__ import annotations

import json
from typing import Optional

import click

from ..context import CLIContext, pass_context


@click.group(name="decrypt")
def decrypt_cli() -> None:
    """解密命令。

    支持多种解密方法: AES, RSA, KARMACA, 几何解密, 完整解密管道。
    """
    pass


@decrypt_cli.command(name="aes")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="密钥文件路径")
@pass_context
def decrypt_aes(ctx: CLIContext, input_file: str, output_file: str, key: str) -> None:
    """使用AES-GCM解密文件。"""
    try:
        with open(input_file, "rb") as f:
            data = f.read()
        with open(key, "rb") as f:
            key_bytes = f.read()

        nonce = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]

        from ...core.crypto.primitives import AESCipher
        plaintext = AESCipher.decrypt(ciphertext, key_bytes, nonce, tag)

        with open(output_file, "wb") as f:
            f.write(plaintext)

        result = {
            "success": True,
            "action": "decrypt_aes",
            "input": input_file,
            "output": output_file,
            "input_size": len(data),
            "output_size": len(plaintext),
            "method": "AES-256-GCM",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"AES解密失败: {e}")


@decrypt_cli.command(name="rsa")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="私钥文件路径")
@pass_context
def decrypt_rsa(ctx: CLIContext, input_file: str, output_file: str, key: str) -> None:
    """使用RSA-OAEP解密文件。"""
    try:
        with open(input_file, "rb") as f:
            ciphertext = f.read()
        with open(key, "rb") as f:
            private_key_pem = f.read()

        from ...core.crypto.primitives import RSACipher
        private_key = RSACipher.deserialize_private_key(private_key_pem)
        plaintext = RSACipher.decrypt(ciphertext, private_key)

        with open(output_file, "wb") as f:
            f.write(plaintext)

        result = {
            "success": True,
            "action": "decrypt_rsa",
            "input": input_file,
            "output": output_file,
            "input_size": len(ciphertext),
            "output_size": len(plaintext),
            "method": "RSA-OAEP",
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"RSA解密失败: {e}")


@decrypt_cli.command(name="karmaca")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, type=click.Path(exists=True, dir_okay=False), help="空间字典文件路径(JSON)")
@click.option("--coordinate", "-c", required=True, help="坐标点，逗号分隔，例如: '1.0,2.0,3.0'")
@click.option("--no-interpolation", is_flag=True, help="不使用插值密钥")
@pass_context
def decrypt_karmaca(
    ctx: CLIContext,
    input_file: str,
    output_file: str,
    key: str,
    coordinate: str,
    no_interpolation: bool,
) -> None:
    """使用KARMACA空间字典解密文件。"""
    try:
        with open(input_file, "rb") as f:
            ciphertext = f.read()
        with open(key, "r", encoding="utf-8") as f:
            space_dict_data = json.load(f)

        coord_list = [float(x.strip()) for x in coordinate.split(",")]

        from ...tools.karmaca.encryption import KarmacaEncryption
        from ...tools.karmaca.space_dict import KarmaSpaceDict
        from ...core.math.vector import Vector

        space_dict = KarmaSpaceDict()
        space_dict.from_dict(space_dict_data)

        karmaca = KarmacaEncryption()
        plaintext = karmaca.decrypt(
            ciphertext,
            Vector(coord_list),
            space_dict,
            use_interpolation=not no_interpolation,
        )

        with open(output_file, "wb") as f:
            f.write(plaintext)

        result = {
            "success": True,
            "action": "decrypt_karmaca",
            "input": input_file,
            "output": output_file,
            "input_size": len(ciphertext),
            "output_size": len(plaintext),
            "method": "KARMACA",
            "dimensions": len(coord_list),
            "interpolation": not no_interpolation,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"KARMACA解密失败: {e}")


@decrypt_cli.command(name="geometric")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, help="密钥字符串")
@click.option("--dimensions", "-d", type=int, default=4, help="几何哈希维度")
@pass_context
def decrypt_geometric(
    ctx: CLIContext,
    input_file: str,
    output_file: str,
    key: str,
    dimensions: int,
) -> None:
    """使用几何哈希派生密钥进行AES解密。"""
    try:
        with open(input_file, "rb") as f:
            data = f.read()

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

        nonce = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]

        plaintext = AESCipher.decrypt(ciphertext, derived_key, nonce, tag)

        with open(output_file, "wb") as f:
            f.write(plaintext)

        result = {
            "success": True,
            "action": "decrypt_geometric",
            "input": input_file,
            "output": output_file,
            "input_size": len(data),
            "output_size": len(plaintext),
            "method": "Geometric-Hash + AES-256-GCM",
            "dimensions": dimensions,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"几何解密失败: {e}")


@decrypt_cli.command(name="full")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", required=True, help="解密密钥")
@pass_context
def decrypt_full(ctx: CLIContext, input_file: str, output_file: str, key: str) -> None:
    """完整解密管道（多层解密）。"""
    try:
        with open(input_file, "rb") as f:
            data = f.read()

        from ...core.crypto.primitives import AESCipher
        from ...core.crypto.kdf import KDF

        key_bytes = key.encode("utf-8") if isinstance(key, str) else key

        nonce2 = data[:12]
        tag2 = data[12:28]
        layer2_ct = data[28:]

        layer2_key = KDF.hkdf(
            key_bytes, salt=b"layer2", info=b"full_encryption_layer2", length=32
        )
        layer2_data = AESCipher.decrypt(layer2_ct, layer2_key, nonce2, tag2)

        nonce1 = layer2_data[:12]
        tag1 = layer2_data[12:28]
        layer1_ct = layer2_data[28:]

        layer1_key = KDF.hkdf(
            key_bytes, salt=b"layer1", info=b"full_encryption_layer1", length=32
        )
        plaintext = AESCipher.decrypt(layer1_ct, layer1_key, nonce1, tag1)

        with open(output_file, "wb") as f:
            f.write(plaintext)

        result = {
            "success": True,
            "action": "decrypt_full",
            "input": input_file,
            "output": output_file,
            "input_size": len(data),
            "output_size": len(plaintext),
            "method": "Full Pipeline (AES-256-GCM x2)",
            "layers": 2,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"完整解密失败: {e}")
