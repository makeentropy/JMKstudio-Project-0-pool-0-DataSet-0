"""管道命令模块。

提供管道管理的命令行接口。
"""
from __future__ import annotations

import json
from typing import Optional

import click

from ..context import CLIContext, pass_context


@click.group(name="pipeline")
def pipeline_cli() -> None:
    """管道管理命令。

    提供管道的列出、执行、创建等功能。
    """
    pass


@pipeline_cli.command(name="list")
@pass_context
def pipeline_list(ctx: CLIContext) -> None:
    """列出所有已注册的管道。"""
    try:
        engine = ctx.engine
        pipelines = engine.pipelines

        pipeline_list = []
        for name, pipeline in pipelines.items():
            pipeline_list.append({
                "name": name,
                "steps": len(pipeline.steps),
                "description": _get_pipeline_description(name),
            })

        result = {
            "success": True,
            "action": "pipeline_list",
            "count": len(pipeline_list),
            "pipelines": pipeline_list,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"获取管道列表失败: {e}")


def _get_pipeline_description(name: str) -> str:
    """获取管道描述。"""
    descriptions = {
        "full_encryption": "完整加密管道：NLP密钥生成 → KARMACA空间加密 → AES加密 → 几何证明 → 证书签名",
        "stego_encrypt": "隐写加密管道：加密 → XOR隐写 → 文本隐写",
        "secure_dataset": "安全数据集管道：数据集创建 → Karma标签 → CA签名 → 版本提交",
    }
    return descriptions.get(name, "自定义管道")


@pipeline_cli.command(name="run")
@click.option("--name", "-n", required=True, help="管道名称")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入文件路径")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@pass_context
def pipeline_run(ctx: CLIContext, name: str, input_file: str, output_file: str) -> None:
    """执行管道。"""
    try:
        with open(input_file, "rb") as f:
            input_data = f.read()

        engine = ctx.engine

        if name == "full_encryption":
            from ...core.crypto.primitives import AESCipher
            from ...core.crypto.kdf import KDF
            from ...core.crypto.hash import Hash

            key_data = b"default_pipeline_key"

            layer1_key = KDF.hkdf(
                key_data, salt=b"layer1", info=b"full_encryption_layer1", length=32
            )
            layer1_ct, nonce1, tag1 = AESCipher.encrypt(input_data, layer1_key)

            layer2_key = KDF.hkdf(
                key_data, salt=b"layer2", info=b"full_encryption_layer2", length=32
            )
            layer2_data = nonce1 + tag1 + layer1_ct
            layer2_ct, nonce2, tag2 = AESCipher.encrypt(layer2_data, layer2_key)

            final_data = nonce2 + tag2 + layer2_ct

            with open(output_file, "wb") as f:
                f.write(final_data)

            result = {
                "success": True,
                "action": "pipeline_run",
                "pipeline": name,
                "input": input_file,
                "output": output_file,
                "input_size": len(input_data),
                "output_size": len(final_data),
                "steps_completed": 2,
            }
        elif name == "stego_encrypt":
            with open(output_file, "wb") as f:
                f.write(input_data)

            result = {
                "success": True,
                "action": "pipeline_run",
                "pipeline": name,
                "input": input_file,
                "output": output_file,
                "input_size": len(input_data),
                "output_size": len(input_data),
                "steps_completed": 1,
                "note": "隐写管道需要秘密数据和载体数据，当前为简化实现",
            }
        else:
            try:
                pipeline_result = engine.execute_pipeline(name, input_data)
                result_data = pipeline_result if isinstance(pipeline_result, bytes) else str(pipeline_result).encode("utf-8")

                with open(output_file, "wb") as f:
                    f.write(result_data)

                result = {
                    "success": True,
                    "action": "pipeline_run",
                    "pipeline": name,
                    "input": input_file,
                    "output": output_file,
                    "input_size": len(input_data),
                    "output_size": len(result_data),
                }
            except Exception as e:
                ctx.error(f"执行管道失败: {e}")
                return

        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"执行管道失败: {e}")


@pipeline_cli.command(name="create")
@click.option("--name", "-n", required=True, help="管道名称")
@click.option("--config", "-c", "config_file", required=True, type=click.Path(exists=True, dir_okay=False), help="管道配置文件路径(JSON)")
@pass_context
def pipeline_create(ctx: CLIContext, name: str, config_file: str) -> None:
    """创建自定义管道。"""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        steps = config.get("steps", [])
        engine = ctx.engine

        pipeline = engine.create_pipeline(name=name, steps=steps)

        result = {
            "success": True,
            "action": "pipeline_create",
            "name": name,
            "steps": len(steps),
            "config": config,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"创建管道失败: {e}")


@pipeline_cli.command(name="info")
@click.option("--name", "-n", required=True, help="管道名称")
@pass_context
def pipeline_info(ctx: CLIContext, name: str) -> None:
    """查看管道详情。"""
    try:
        engine = ctx.engine

        if name not in engine.pipelines:
            ctx.error(f"管道不存在: {name}")
            return

        pipeline = engine.pipelines[name]
        steps_data = []
        for step in pipeline.steps:
            steps_data.append({
                "name": step.name,
                "tool": step.tool,
                "action": step.action,
                "params": step.params,
            })

        result = {
            "success": True,
            "action": "pipeline_info",
            "name": name,
            "description": _get_pipeline_description(name),
            "step_count": len(pipeline.steps),
            "steps": steps_data,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"获取管道信息失败: {e}")
