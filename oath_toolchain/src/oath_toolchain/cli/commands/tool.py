"""工具管理命令模块。

提供工具列表、信息查询和执行等功能。
"""
from __future__ import annotations

import json
from typing import Any

import click

from ..context import CLIContext, pass_context


@click.group(name="tool")
def tool_cli() -> None:
    """工具管理命令。

    列出、查询和执行已注册的工具。
    """
    pass


@tool_cli.command(name="list")
@pass_context
def tool_list(ctx: CLIContext) -> None:
    """列出所有已注册的工具。"""
    try:
        tools = ctx.engine.list_tools()
        result = {
            "success": True,
            "action": "tool_list",
            "count": len(tools),
            "tools": tools,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"获取工具列表失败: {e}")


@tool_cli.command(name="info")
@click.option("--name", "-n", required=True, help="工具名称")
@pass_context
def tool_info(ctx: CLIContext, name: str) -> None:
    """查询指定工具的详细信息。"""
    try:
        tool = ctx.engine.get_tool(name)
        result = {
            "success": True,
            "action": "tool_info",
            "tool": tool.metadata,
        }
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"获取工具信息失败: {e}")


@tool_cli.command(name="execute")
@click.option("--name", "-n", required=True, help="工具名称")
@click.option("--action", "-a", required=True, help="执行的操作")
@click.option("--params", "-p", default="{}", help="JSON格式的参数字典")
@pass_context
def tool_execute(ctx: CLIContext, name: str, action: str, params: str) -> None:
    """执行指定工具的操作。

    参数以JSON格式提供，例如: '{"key": "value"}'
    """
    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError as e:
        ctx.error(f"参数格式错误，必须是有效的JSON: {e}")
        return

    try:
        tool = ctx.engine.get_tool(name)
        params_dict["action"] = action
        result = tool.execute(params_dict)
        ctx.output_result(result)
    except Exception as e:
        ctx.error(f"执行工具失败: {e}")
