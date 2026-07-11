#!/usr/bin/env python
"""
Git 镜像池 CLI (pool/img 方案)

封装 GitMirrorPool, 管理开源仓库镜像 + push 到 github.com。

用法:
    python git_mirror_cli.py add --name flask --url https://github.com/pallets/flask.git
    python git_mirror_cli.py add --name flask --url <url> --github https://github.com/myorg/flask.git
    python git_mirror_cli.py clone --name flask
    python git_mirror_cli.py pull --name flask
    python git_mirror_cli.py pull-all
    python git_mirror_cli.py push --name flask
    python git_mirror_cli.py list
    python git_mirror_cli.py status
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ai_llm_agent_crawler.storage.git_mirror_pool import (  # noqa: E402
    GitMirrorPool,
    MirrorStatus,
)

console = Console()


def _get_pool(pool_root: Path, github_prefix: Optional[str]) -> GitMirrorPool:
    return GitMirrorPool(pool_root=pool_root, default_github_remote=github_prefix)


@click.group()
@click.option("--pool-root", default=Path("git_mirror_pool"), type=click.Path(path_type=Path), help="镜像池根目录")
@click.option("--github-prefix", default=None, help="默认 github.com 推送前缀 (如 https://github.com/myorg/)")
@click.pass_context
def cli(ctx: click.Context, pool_root: Path, github_prefix: Optional[str]) -> None:
    """Git 镜像池管理 CLI。"""
    ctx.obj = _get_pool(pool_root, github_prefix)


@cli.command("add")
@click.option("--name", required=True, help="镜像名称")
@click.option("--url", required=True, help="上游开源仓库 URL")
@click.option("--github", default=None, help="github.com 推送目标 URL")
@click.option("--desc", default="", help="描述")
@click.option("--clone-now", is_flag=True, default=False, help="立即克隆")
@click.pass_obj
def add(pool: GitMirrorPool, name: str, url: str, github: Optional[str], desc: str, clone_now: bool) -> None:
    entry = pool.add_mirror(name=name, source_url=url, github_remote=github, description=desc, clone_now=clone_now)
    console.print(Panel.fit(
        f"[green]已添加镜像[/green]\n名称: {entry.name}\n源: {entry.source_url}\n"
        f"github: {entry.github_remote or '(未配置)'}",
        title="Add",
    ))


@cli.command("clone")
@click.option("--name", required=True)
@click.pass_obj
def clone(pool: GitMirrorPool, name: str) -> None:
    entry = pool.clone(name)
    console.print(f"[green]克隆成功: {name} @ {entry.last_commit}[/green]")


@cli.command("pull")
@click.option("--name", required=True)
@click.pass_obj
def pull(pool: GitMirrorPool, name: str) -> None:
    entry = pool.pull(name)
    console.print(f"[green]拉取成功: {name} @ {entry.last_commit}[/green]")


@cli.command("pull-all")
@click.pass_obj
def pull_all(pool: GitMirrorPool) -> None:
    results = pool.pull_all()
    ok = sum(1 for v in results.values() if v)
    console.print(f"[green]拉取完成: {ok}/{len(results)} 成功[/green]")
    for name, ok in results.items():
        console.print(f"  {'[OK]' if ok else '[FAIL]'} {name}")


@cli.command("push")
@click.option("--name", required=True)
@click.pass_obj
def push(pool: GitMirrorPool, name: str) -> None:
    entry = pool.push_to_github(name)
    console.print(f"[green]推送成功: {name} -> {entry.github_remote}[/green]")


@cli.command("push-all")
@click.pass_obj
def push_all(pool: GitMirrorPool) -> None:
    results = pool.push_all_to_github()
    ok = sum(1 for v in results.values() if v)
    console.print(f"[green]推送完成: {ok}/{len(results)} 成功[/green]")


@cli.command("remove")
@click.option("--name", required=True)
@click.option("--keep-files", is_flag=True, default=False, help="保留本地镜像文件")
@click.pass_obj
def remove(pool: GitMirrorPool, name: str, keep_files: bool) -> None:
    if pool.remove_mirror(name, delete_files=not keep_files):
        console.print(f"[green]已移除: {name}[/green]")
    else:
        console.print(f"[red]不存在: {name}[/red]")


@cli.command("list")
@click.pass_obj
def list_cmd(pool: GitMirrorPool) -> None:
    entries = pool.list_entries()
    if not entries:
        console.print("[yellow]镜像池为空[/yellow]")
        return
    table = Table(title="Git 镜像池", show_lines=True)
    table.add_column("名称", style="cyan")
    table.add_column("状态")
    table.add_column("最近 commit")
    table.add_column("分支数", justify="right")
    table.add_column("Tag数", justify="right")
    table.add_column("最近同步")
    table.add_column("github")
    for e in entries:
        table.add_row(
            e.name,
            e.status,
            (e.last_commit or "-")[:12],
            str(len(e.branches)),
            str(len(e.tags)),
            e.last_sync_at or "-",
            "✓" if e.github_remote else "-",
        )
    console.print(table)


@cli.command("status")
@click.pass_obj
def status(pool: GitMirrorPool) -> None:
    s = pool.pool_status()
    console.print(Panel.fit(
        f"池根目录: {s['pool_root']}\n"
        f"镜像总数: {s['total_mirrors']}\n"
        f"github 已配置: {s['github_configured']}\n"
        f"状态分布: {s['by_status']}",
        title="镜像池状态",
    ))


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
