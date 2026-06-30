"""隐写命令模块。

提供多种隐写方法的命令行接口。
"""
from __future__ import annotations

import base64
from typing import Optional

import click

from ..context import CLIContext, pass_context


@click.group(name="stego")
def stego_cli() -> None:
    """隐写命令。

    提供多种隐写方法: XOR隐写、文本隐写、证书隐写等。
    """
    pass


@stego_cli.group(name="embed")
def stego_embed() -> None:
    """嵌入秘密信息。"""
    pass


@stego_cli.group(name="extract")
def stego_extract() -> None:
    """提取秘密信息。"""
    pass


@stego_cli.command(name="analyze")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="载体文件路径")
@click.option("--carrier-type", "-t", default="binary", help="载体类型 (binary/text)")
@pass_context
def stego_analyze(ctx: CLIContext, input_file: str, carrier_type: str) -> None:
    """分析载体隐写容量。"""
    try:
        with open(input_file, "rb") as f:
            carrier_data = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        result = stego_tool.execute({
            "action": "analyze",
            "carrier_data": carrier_data,
            "carrier_type": carrier_type,
        })

        output_result = {
            "success": result.get("success", True),
            "action": "stego_analyze",
            "input": input_file,
            "carrier_type": carrier_type,
            "analysis": result.get("result", {}),
        }
        ctx.output_result(output_result)
    except Exception as e:
        ctx.error(f"隐写分析失败: {e}")


@stego_embed.command(name="xor")
@click.option("--secret", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="秘密文件路径")
@click.option("--carrier", "-c", required=True, type=click.Path(exists=True, dir_okay=False), help="载体文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--key", "-k", default=None, help="密钥(可选)")
@pass_context
def stego_embed_xor(
    ctx: CLIContext,
    secret: str,
    carrier: str,
    output_file: str,
    key: Optional[str],
) -> None:
    """XOR隐写嵌入。"""
    try:
        with open(secret, "rb") as f:
            secret_data = f.read()
        with open(carrier, "rb") as f:
            carrier_data = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        params = {
            "action": "xor_embed",
            "secret_data": secret_data,
            "carrier_data": carrier_data,
        }
        if key:
            params["key"] = key.encode("utf-8")

        result = stego_tool.execute(params)

        if result.get("success"):
            import base64 as b64
            stego_data = b64.b64decode(result["result"])
            with open(output_file, "wb") as f:
                f.write(stego_data)

            output_result = {
                "success": True,
                "action": "stego_embed_xor",
                "secret": secret,
                "carrier": carrier,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "carrier_size": result.get("carrier_size", 0),
                "method": "XOR Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "XOR隐写嵌入失败"))
    except Exception as e:
        ctx.error(f"XOR隐写嵌入失败: {e}")


@stego_extract.command(name="xor")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="含秘载体文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="秘密文件输出路径")
@click.option("--key", "-k", default=None, help="密钥(可选)")
@pass_context
def stego_extract_xor(
    ctx: CLIContext,
    input_file: str,
    output_file: str,
    key: Optional[str],
) -> None:
    """XOR隐写提取。"""
    try:
        with open(input_file, "rb") as f:
            stego_data = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        params = {
            "action": "xor_extract",
            "stego_data": stego_data,
        }
        if key:
            params["key"] = key.encode("utf-8")

        result = stego_tool.execute(params)

        if result.get("success"):
            import base64 as b64
            secret_data = b64.b64decode(result["result"])
            with open(output_file, "wb") as f:
                f.write(secret_data)

            output_result = {
                "success": True,
                "action": "stego_extract_xor",
                "input": input_file,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "XOR Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "XOR隐写提取失败"))
    except Exception as e:
        ctx.error(f"XOR隐写提取失败: {e}")


@stego_embed.command(name="unicode")
@click.option("--secret", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="秘密文件路径")
@click.option("--carrier", "-c", required=True, type=click.Path(exists=True, dir_okay=False), help="载体文本文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@pass_context
def stego_embed_unicode(
    ctx: CLIContext,
    secret: str,
    carrier: str,
    output_file: str,
) -> None:
    """Unicode隐写嵌入。"""
    try:
        with open(secret, "rb") as f:
            secret_data = f.read()
        with open(carrier, "r", encoding="utf-8") as f:
            text = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        result = stego_tool.execute({
            "action": "text_unicode_embed",
            "text": text,
            "secret_data": secret_data,
        })

        if result.get("success"):
            stego_text = result["result"]
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(stego_text)

            output_result = {
                "success": True,
                "action": "stego_embed_unicode",
                "secret": secret,
                "carrier": carrier,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "Unicode Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "Unicode隐写嵌入失败"))
    except Exception as e:
        ctx.error(f"Unicode隐写嵌入失败: {e}")


@stego_extract.command(name="unicode")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="含秘载体文本文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="秘密文件输出路径")
@pass_context
def stego_extract_unicode(ctx: CLIContext, input_file: str, output_file: str) -> None:
    """Unicode隐写提取。"""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            stego_text = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        result = stego_tool.execute({
            "action": "text_unicode_extract",
            "stego_text": stego_text,
        })

        if result.get("success"):
            import base64 as b64
            secret_data = b64.b64decode(result["result"])
            with open(output_file, "wb") as f:
                f.write(secret_data)

            output_result = {
                "success": True,
                "action": "stego_extract_unicode",
                "input": input_file,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "Unicode Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "Unicode隐写提取失败"))
    except Exception as e:
        ctx.error(f"Unicode隐写提取失败: {e}")


@stego_embed.command(name="whitespace")
@click.option("--secret", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="秘密文件路径")
@click.option("--carrier", "-c", required=True, type=click.Path(exists=True, dir_okay=False), help="载体文本文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@pass_context
def stego_embed_whitespace(
    ctx: CLIContext,
    secret: str,
    carrier: str,
    output_file: str,
) -> None:
    """空格隐写嵌入。"""
    try:
        with open(secret, "rb") as f:
            secret_data = f.read()
        with open(carrier, "r", encoding="utf-8") as f:
            text = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        result = stego_tool.execute({
            "action": "text_whitespace_embed",
            "text": text,
            "secret_data": secret_data,
        })

        if result.get("success"):
            stego_text = result["result"]
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(stego_text)

            output_result = {
                "success": True,
                "action": "stego_embed_whitespace",
                "secret": secret,
                "carrier": carrier,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "Whitespace Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "空格隐写嵌入失败"))
    except Exception as e:
        ctx.error(f"空格隐写嵌入失败: {e}")


@stego_extract.command(name="whitespace")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="含秘载体文本文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="秘密文件输出路径")
@pass_context
def stego_extract_whitespace(ctx: CLIContext, input_file: str, output_file: str) -> None:
    """空格隐写提取。"""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            stego_text = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        result = stego_tool.execute({
            "action": "text_whitespace_extract",
            "stego_text": stego_text,
        })

        if result.get("success"):
            import base64 as b64
            secret_data = b64.b64decode(result["result"])
            with open(output_file, "wb") as f:
                f.write(secret_data)

            output_result = {
                "success": True,
                "action": "stego_extract_whitespace",
                "input": input_file,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "Whitespace Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "空格隐写提取失败"))
    except Exception as e:
        ctx.error(f"空格隐写提取失败: {e}")


@stego_embed.command(name="case")
@click.option("--secret", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="秘密文件路径")
@click.option("--carrier", "-c", required=True, type=click.Path(exists=True, dir_okay=False), help="载体文本文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@pass_context
def stego_embed_case(
    ctx: CLIContext,
    secret: str,
    carrier: str,
    output_file: str,
) -> None:
    """大小写隐写嵌入。"""
    try:
        with open(secret, "rb") as f:
            secret_data = f.read()
        with open(carrier, "r", encoding="utf-8") as f:
            text = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        result = stego_tool.execute({
            "action": "text_case_embed",
            "text": text,
            "secret_data": secret_data,
        })

        if result.get("success"):
            stego_text = result["result"]
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(stego_text)

            output_result = {
                "success": True,
                "action": "stego_embed_case",
                "secret": secret,
                "carrier": carrier,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "Case Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "大小写隐写嵌入失败"))
    except Exception as e:
        ctx.error(f"大小写隐写嵌入失败: {e}")


@stego_extract.command(name="case")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="含秘载体文本文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="秘密文件输出路径")
@pass_context
def stego_extract_case(ctx: CLIContext, input_file: str, output_file: str) -> None:
    """大小写隐写提取。"""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            stego_text = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        result = stego_tool.execute({
            "action": "text_case_extract",
            "stego_text": stego_text,
        })

        if result.get("success"):
            import base64 as b64
            secret_data = b64.b64decode(result["result"])
            with open(output_file, "wb") as f:
                f.write(secret_data)

            output_result = {
                "success": True,
                "action": "stego_extract_case",
                "input": input_file,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "Case Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "大小写隐写提取失败"))
    except Exception as e:
        ctx.error(f"大小写隐写提取失败: {e}")


@stego_embed.command(name="cert")
@click.option("--secret", "-s", required=True, type=click.Path(exists=True, dir_okay=False), help="秘密文件路径")
@click.option("--carrier", "-c", required=True, type=click.Path(exists=True, dir_okay=False), help="证书载体文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出证书文件路径")
@click.option("--oid", default=None, help="扩展字段OID(可选)")
@pass_context
def stego_embed_cert(
    ctx: CLIContext,
    secret: str,
    carrier: str,
    output_file: str,
    oid: Optional[str],
) -> None:
    """证书扩展字段隐写嵌入。"""
    try:
        with open(secret, "rb") as f:
            secret_data = f.read()
        with open(carrier, "rb") as f:
            cert_pem = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        params = {
            "action": "cert_embed",
            "cert_pem": cert_pem,
            "secret_data": secret_data,
        }
        if oid:
            params["oid"] = oid

        result = stego_tool.execute(params)

        if result.get("success"):
            stego_cert = result["result"]
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(stego_cert)

            output_result = {
                "success": True,
                "action": "stego_embed_cert",
                "secret": secret,
                "carrier": carrier,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "Certificate Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "证书隐写嵌入失败"))
    except Exception as e:
        ctx.error(f"证书隐写嵌入失败: {e}")


@stego_extract.command(name="cert")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="含秘证书文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="秘密文件输出路径")
@click.option("--oid", default=None, help="扩展字段OID(可选)")
@pass_context
def stego_extract_cert(
    ctx: CLIContext,
    input_file: str,
    output_file: str,
    oid: Optional[str],
) -> None:
    """证书扩展字段隐写提取。"""
    try:
        with open(input_file, "rb") as f:
            cert_pem = f.read()

        from ...tools.steganography.tool import SteganographyTool
        stego_tool = SteganographyTool()

        params = {
            "action": "cert_extract",
            "cert_pem": cert_pem,
        }
        if oid:
            params["oid"] = oid

        result = stego_tool.execute(params)

        if result.get("success"):
            import base64 as b64
            secret_data = b64.b64decode(result["result"])
            with open(output_file, "wb") as f:
                f.write(secret_data)

            output_result = {
                "success": True,
                "action": "stego_extract_cert",
                "input": input_file,
                "output": output_file,
                "secret_size": result.get("secret_size", 0),
                "method": "Certificate Steganography",
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "证书隐写提取失败"))
    except Exception as e:
        ctx.error(f"证书隐写提取失败: {e}")
