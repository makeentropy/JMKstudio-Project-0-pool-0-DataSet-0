"""
AI LLM Agent Crawler - 顶层 CLI 入口

提供 `ai-crawler` 命令, 作为 toolchain full work 栈的总入口。
通过子命令分发到 bin/ 下的各工具脚本 (snapshot / freefilesync / git-mirror /
agent-skills / workstation), 或直接调用包内核心模块。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from ai_llm_agent_crawler import __version__

console = Console()

# bin/ 目录定位: 优先相对包路径向上查找, 兼容开发模式与安装模式
_BIN_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent / "bin",  # src/pkg -> src -> repo/bin
    Path(__file__).resolve().parent.parent / "bin",  # 兜底
]


def _find_bin_dir() -> Optional[Path]:
    """查找 bin/ 目录。"""
    for cand in _BIN_CANDIDATES:
        if cand.is_dir():
            return cand
    return None


def _run_bin_script(script_name: str, extra_args: Optional[List[str]] = None) -> int:
    """通过 python 运行 bin/ 下的脚本, 转发参数, 返回退出码。"""
    bin_dir = _find_bin_dir()
    if bin_dir is None:
        console.print("[red]未找到 bin/ 目录, 无法运行工具脚本。[/red]")
        console.print("[yellow]请确保从源码仓库运行, 或设置 AI_CRAWLER_BIN 环境变量。[/yellow]")
        return 2
    script = bin_dir / script_name
    if not script.exists():
        console.print(f"[red]脚本不存在: {script}[/red]")
        return 2
    cmd = [sys.executable, str(script)] + (extra_args or [])
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        return 130


# 工具脚本登记表: name -> (script, description)
TOOLCHAIN_TOOLS = {
    "snapshot": ("snapshot_cli.py", "快照备份与恢复 CLI (create/list/restore/verify...)"),
    "snapshot-ui": ("snapshot_ui.py", "快照管理交互式 UI"),
    "freefilesync": ("freefilesync_gen.py", "FreeFileSync 无人值守同步批处理生成器"),
    "git-mirror": ("git_mirror_cli.py", "Git 镜像池管理 (clone/pull/push 到 github)"),
    "agent-skills": ("agent_skills_workscript.py", "agent skills 生成 + 算法 POOL + workScript"),
    "workstation": ("workstation.py", "workspace workstation toolchain 编排 (init/status/doctor/pipeline)"),
}


@click.group(
    invoke_without_command=True,
    help="AI LLM Agent Crawler - toolchain full work 栈总入口。",
)
@click.version_option(__version__, prog_name="ai-crawler")
@click.pass_context
def cli(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print(f"[bold cyan]AI LLM Agent Crawler[/bold cyan] v{__version__}")
        console.print("toolchain full work 栈。使用 [green]--help[/green] 查看子命令。")
        console.print("\n[bold]可用工具:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("命令", style="cyan")
        table.add_column("说明")
        for name, (_, desc) in TOOLCHAIN_TOOLS.items():
            table.add_row(f"ai-crawler run {name}", desc)
        console.print(table)


@cli.command("list", help="列出所有 toolchain 工具。")
def list_tools() -> None:
    bin_dir = _find_bin_dir()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("工具", style="cyan")
    table.add_column("脚本")
    table.add_column("说明")
    table.add_column("存在", justify="center")
    for name, (script, desc) in TOOLCHAIN_TOOLS.items():
        exists = "✓" if bin_dir and (bin_dir / script).exists() else "✗"
        style = "green" if exists == "✓" else "red"
        table.add_row(name, script, desc, f"[{style}]{exists}[/{style}]")
    console.print(table)
    if bin_dir:
        console.print(f"\n[dim]bin/ 目录: {bin_dir}[/dim]")
    else:
        console.print("\n[yellow]未找到 bin/ 目录。[/yellow]")


@cli.command(
    "run",
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
    help="运行指定工具并转发剩余参数。例如: ai-crawler run snapshot --help",
)
@click.argument("tool", type=click.Choice(list(TOOLCHAIN_TOOLS.keys())))
@click.pass_context
def run_tool(ctx: click.Context, tool: str) -> None:
    script, _ = TOOLCHAIN_TOOLS[tool]
    code = _run_bin_script(script, ctx.args)
    if code != 0:
        raise click.exceptions.Exit(code)


@cli.command("doctor", help="诊断环境: 检查 Python 版本 / git / 核心模块导入。")
def doctor() -> None:
    import shutil

    console.print("[bold]环境诊断[/bold]\n")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("项目", style="cyan")
    table.add_column("状态")
    table.add_column("详情")

    # Python
    table.add_row("Python", "[green]OK[/green]", sys.version.split()[0])

    # git
    git_path = shutil.which("git")
    table.add_row("git", "[green]OK[/green]" if git_path else "[red]缺失[/red]", git_path or "未找到")

    # 核心模块导入
    checks = [
        ("ai_llm_agent_crawler.versioning.snapshot_manager", "SnapshotManager"),
        ("ai_llm_agent_crawler.storage.git_mirror_pool", "GitMirrorPool"),
        ("ai_llm_agent_crawler.algorithm.algorithm_pool", "AlgorithmPool"),
        ("ai_llm_agent_crawler.algorithm.performance_budget", "PerformanceBudget"),
        ("ai_llm_agent_crawler.algorithm.data_settlement", "DataSettlement"),
    ]
    for mod_path, symbol in checks:
        try:
            __import__(mod_path)
            table.add_row(symbol, "[green]OK[/green]", mod_path)
        except Exception as e:  # noqa: BLE001
            table.add_row(symbol, "[red]失败[/red]", f"{e}")

    console.print(table)

    # bin 目录
    bin_dir = _find_bin_dir()
    if bin_dir:
        console.print(f"\n[green]✓[/green] bin/ 目录: {bin_dir}")
    else:
        console.print("\n[yellow]⚠ bin/ 目录未找到 (安装模式下工具脚本可能不可用)[/yellow]")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
