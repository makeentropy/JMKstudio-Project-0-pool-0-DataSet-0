"""CLI上下文和装饰器。"""
from __future__ import annotations

import json
import sys
from typing import Any, Optional

import click
import yaml

from ..orchestration.qiankun_engine import QiankunEngine


class CLIContext:
    """CLI上下文对象。

    存储全局配置和引擎实例，在命令间共享。

    Attributes:
        config: 配置字典
        verbose: 是否详细输出
        quiet: 是否静默模式
        output_format: 输出格式 (text/json/yaml)
        engine: 乾坤引擎实例
    """

    def __init__(self) -> None:
        """初始化CLI上下文。"""
        self.config: dict[str, Any] = {}
        self.verbose: bool = False
        self.quiet: bool = False
        self.output_format: str = "text"
        self._engine: Optional[QiankunEngine] = None

    @property
    def engine(self) -> QiankunEngine:
        """获取乾坤引擎实例（懒加载）。

        Returns:
            乾坤引擎实例
        """
        if self._engine is None:
            self._engine = QiankunEngine(
                config={"auto_register_tools": True}
            )
        return self._engine

    def output_result(self, result: dict[str, Any]) -> None:
        """输出结果。

        根据输出格式以不同方式展示结果。

        Args:
            result: 结果字典
        """
        if self.quiet:
            return

        if self.output_format == "json":
            click.echo(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        elif self.output_format == "yaml":
            click.echo(yaml.dump(result, allow_unicode=True, default_flow_style=False))
        else:
            self._output_text(result)

    def _output_text(self, result: dict[str, Any]) -> None:
        """以文本格式输出结果。

        Args:
            result: 结果字典
        """
        success = result.get("success", True)
        if success:
            click.secho("✓ 操作成功", fg="green", bold=True)
        else:
            click.secho("✗ 操作失败", fg="red", bold=True)
            message = result.get("message", "未知错误")
            click.secho(f"  错误信息: {message}", fg="red")

        for key, value in result.items():
            if key in ("success", "message"):
                continue
            if isinstance(value, (dict, list)):
                click.echo(f"  {key}:")
                self._print_nested(value, indent=4)
            else:
                click.echo(f"  {key}: {value}")

    def _print_nested(self, obj: Any, indent: int = 0) -> None:
        """递归打印嵌套结构。

        Args:
            obj: 要打印的对象
            indent: 缩进级别
        """
        prefix = " " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    click.echo(f"{prefix}{k}:")
                    self._print_nested(v, indent + 2)
                else:
                    click.echo(f"{prefix}{k}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    click.echo(f"{prefix}[{i}]:")
                    self._print_nested(item, indent + 2)
                else:
                    click.echo(f"{prefix}[{i}]: {item}")

    def error(self, message: str, exit_code: int = 1) -> None:
        """输出错误信息并退出。

        Args:
            message: 错误消息
            exit_code: 退出码
        """
        if self.output_format == "json":
            click.echo(json.dumps({"success": False, "message": message}, ensure_ascii=False))
        elif self.output_format == "yaml":
            click.echo(yaml.dump({"success": False, "message": message}, allow_unicode=True))
        else:
            click.secho(f"错误: {message}", fg="red", bold=True)
        sys.exit(exit_code)


pass_context = click.make_pass_decorator(CLIContext, ensure=True)

__all__ = ["CLIContext", "pass_context"]
