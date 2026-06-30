"""CLI主入口模块。

神誓工具链命令行界面的主入口，提供统一的命令行访问接口。
"""
from __future__ import annotations

import sys
from typing import Optional

import click

from ..core.exceptions import OathToolchainError
from .context import CLIContext, pass_context

from ..tools.ca_system.tool import CASystemTool
from ..tools.steganography.tool import SteganographyTool
from ..tools.dataset_pool.tool import DatasetPoolTool
from ..tools.geometric_proof.tool import GeometricProofTool
from ..tools.karma_tags.tool import KarmaTagTool
from ..tools.karmaca.encryption import KarmacaEncryption
from ..tools.nlptcmodel.key_generator import NLPTCKeyGenerator


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    help="配置文件路径",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="详细输出模式",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="静默模式，只输出结果",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "yaml"], case_sensitive=False),
    default="text",
    help="输出格式 (text/json/yaml)",
)
@pass_context
def cli(
    ctx: CLIContext,
    config: Optional[str],
    verbose: bool,
    quiet: bool,
    output: str,
) -> None:
    """神誓工具链 (Oath Toolchain) - 统一加密工具链命令行接口。

    提供加密、解密、签名、验证、CA管理、隐写、数据集管理等功能。
    """
    import json
    import yaml

    ctx.verbose = verbose
    ctx.quiet = quiet
    ctx.output_format = output.lower()

    if config:
        try:
            with open(config, "r", encoding="utf-8") as f:
                if config.endswith(".json"):
                    ctx.config = json.load(f)
                else:
                    ctx.config = yaml.safe_load(f) or {}
        except Exception as e:
            ctx.error(f"加载配置文件失败: {e}")

    if verbose and not quiet:
        click.secho("神誓工具链 v0.1.0", fg="cyan", bold=True)
        click.echo("正在初始化引擎...")


from .commands.encrypt import encrypt_cli
from .commands.decrypt import decrypt_cli
from .commands.keygen import keygen_cli
from .commands.sign import sign_cli
from .commands.verify import verify_cli
from .commands.ca import ca_cli
from .commands.stego import stego_cli
from .commands.dataset import dataset_cli
from .commands.pipeline import pipeline_cli
from .commands.tool import tool_cli

cli.add_command(encrypt_cli)
cli.add_command(decrypt_cli)
cli.add_command(keygen_cli)
cli.add_command(sign_cli)
cli.add_command(verify_cli)
cli.add_command(ca_cli)
cli.add_command(stego_cli)
cli.add_command(dataset_cli)
cli.add_command(pipeline_cli)
cli.add_command(tool_cli)


def main() -> None:
    """主入口函数。"""
    try:
        cli()
    except OathToolchainError as e:
        click.secho(f"错误: {e.message}", fg="red", bold=True)
        if e.details:
            click.echo(f"详情: {e.details}")
        sys.exit(1)
    except click.ClickException:
        raise
    except Exception as e:
        click.secho(f"未知错误: {e}", fg="red", bold=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
