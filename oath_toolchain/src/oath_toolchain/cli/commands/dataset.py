"""数据集命令模块。

提供数据集管理的命令行接口。
"""
from __future__ import annotations

import json
from typing import Optional

import click

from ..context import CLIContext, pass_context


_dataset_instance = None


def _get_dataset_tool(ctx: CLIContext):
    """获取数据集工具实例。"""
    global _dataset_instance
    if _dataset_instance is None:
        from ...tools.dataset_pool.tool import DatasetPoolTool
        _dataset_instance = DatasetPoolTool()
    return _dataset_instance


@click.group(name="dataset")
def dataset_cli() -> None:
    """数据集管理命令。

    提供数据集的创建、查询、删除、版本控制等功能。
    """
    pass


@dataset_cli.command(name="create")
@click.option("--name", "-n", required=True, help="数据集名称")
@click.option("--input", "-i", "input_file", required=True, type=click.Path(exists=True, dir_okay=False), help="输入数据文件路径(JSON)")
@click.option("--description", "-d", default="", help="数据集描述")
@pass_context
def dataset_create(ctx: CLIContext, name: str, input_file: str, description: str) -> None:
    """创建数据集。"""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        dataset_tool = _get_dataset_tool(ctx)
        result = dataset_tool.execute({
            "action": "create",
            "name": name,
            "data": data,
            "format": "json",
            "description": description,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "dataset_create",
                "dataset_id": result.get("dataset_id"),
                "dataset": result.get("dataset"),
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "创建数据集失败"))
    except Exception as e:
        ctx.error(f"创建数据集失败: {e}")


@dataset_cli.command(name="list")
@click.option("--limit", "-l", type=int, default=100, help="返回数量限制")
@click.option("--offset", "-o", type=int, default=0, help="偏移量")
@pass_context
def dataset_list(ctx: CLIContext, limit: int, offset: int) -> None:
    """列出数据集。"""
    try:
        dataset_tool = _get_dataset_tool(ctx)
        result = dataset_tool.execute({
            "action": "list",
            "limit": limit,
            "offset": offset,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "dataset_list",
                "count": result.get("count", 0),
                "datasets": result.get("datasets", []),
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "列出数据集失败"))
    except Exception as e:
        ctx.error(f"列出数据集失败: {e}")


@dataset_cli.command(name="get")
@click.option("--id", "dataset_id", required=True, help="数据集ID")
@pass_context
def dataset_get(ctx: CLIContext, dataset_id: str) -> None:
    """获取数据集详情。"""
    try:
        dataset_tool = _get_dataset_tool(ctx)
        result = dataset_tool.execute({
            "action": "get",
            "dataset_id": dataset_id,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "dataset_get",
                "dataset_id": result.get("dataset_id"),
                "dataset": result.get("dataset"),
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "获取数据集失败"))
    except Exception as e:
        ctx.error(f"获取数据集失败: {e}")


@dataset_cli.command(name="delete")
@click.option("--id", "dataset_id", required=True, help="数据集ID")
@pass_context
def dataset_delete(ctx: CLIContext, dataset_id: str) -> None:
    """删除数据集。"""
    try:
        dataset_tool = _get_dataset_tool(ctx)
        result = dataset_tool.execute({
            "action": "delete",
            "dataset_id": dataset_id,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "dataset_delete",
                "dataset_id": dataset_id,
                "deleted": result.get("success", False),
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "删除数据集失败"))
    except Exception as e:
        ctx.error(f"删除数据集失败: {e}")


@dataset_cli.command(name="export")
@click.option("--id", "dataset_id", required=True, help="数据集ID")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(dir_okay=False), help="输出文件路径")
@click.option("--format", "-f", "fmt", default="json", help="输出格式 (json)")
@pass_context
def dataset_export(ctx: CLIContext, dataset_id: str, output_file: str, fmt: str) -> None:
    """导出数据集。"""
    try:
        dataset_tool = _get_dataset_tool(ctx)
        result = dataset_tool.execute({
            "action": "get",
            "dataset_id": dataset_id,
        })

        if result.get("success"):
            dataset = result.get("dataset", {})
            data = dataset.get("data", {})

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            output_result = {
                "success": True,
                "action": "dataset_export",
                "dataset_id": dataset_id,
                "output": output_file,
                "format": fmt,
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "导出数据集失败"))
    except Exception as e:
        ctx.error(f"导出数据集失败: {e}")


@dataset_cli.group(name="tag")
def dataset_tag() -> None:
    """数据集标签管理。"""
    pass


@dataset_tag.command(name="add")
@click.option("--id", "dataset_id", required=True, help="数据集ID")
@click.option("--tag", "-t", required=True, help="标签键")
@click.option("--value", "-v", required=True, help="标签值")
@pass_context
def dataset_tag_add(ctx: CLIContext, dataset_id: str, tag: str, value: str) -> None:
    """添加数据集标签。"""
    try:
        dataset_tool = _get_dataset_tool(ctx)
        result = dataset_tool.execute({
            "action": "set_meta",
            "dataset_id": dataset_id,
            "key": tag,
            "value": value,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "dataset_tag_add",
                "dataset_id": dataset_id,
                "tag": tag,
                "value": value,
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "添加标签失败"))
    except Exception as e:
        ctx.error(f"添加标签失败: {e}")


@dataset_cli.group(name="version")
def dataset_version() -> None:
    """数据集版本管理。"""
    pass


@dataset_version.command(name="commit")
@click.option("--id", "dataset_id", required=True, help="数据集ID")
@click.option("--message", "-m", required=True, help="提交消息")
@pass_context
def dataset_version_commit(ctx: CLIContext, dataset_id: str, message: str) -> None:
    """提交数据集版本。"""
    try:
        dataset_tool = _get_dataset_tool(ctx)
        result = dataset_tool.execute({
            "action": "commit",
            "dataset_id": dataset_id,
            "message": message,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "dataset_version_commit",
                "dataset_id": dataset_id,
                "version": result.get("version"),
                "message": message,
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "提交版本失败"))
    except Exception as e:
        ctx.error(f"提交版本失败: {e}")


@dataset_version.command(name="list")
@click.option("--id", "dataset_id", required=True, help="数据集ID")
@pass_context
def dataset_version_list(ctx: CLIContext, dataset_id: str) -> None:
    """列出数据集版本。"""
    try:
        dataset_tool = _get_dataset_tool(ctx)
        result = dataset_tool.execute({
            "action": "versions",
            "dataset_id": dataset_id,
        })

        if result.get("success"):
            output_result = {
                "success": True,
                "action": "dataset_version_list",
                "dataset_id": dataset_id,
                "count": result.get("count", 0),
                "versions": result.get("versions", []),
            }
            ctx.output_result(output_result)
        else:
            ctx.error(result.get("message", "列出版本失败"))
    except Exception as e:
        ctx.error(f"列出版本失败: {e}")
