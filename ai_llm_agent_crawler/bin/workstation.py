#!/usr/bin/env python
"""
Workspace Workstation Toolchain (full work 栈)

统一编排所有工具链组件的入口:
- snapshot CLI/UI (备份恢复)
- FreeFileSync 同步生成器
- git 镜像池 (pool/img, push github)
- 算法 POOL + 性能预算 + 数据清算
- agent skills workScript

提供:
- init: 初始化 workspace 目录结构
- status: 工具链状态总览
- doctor: 健康检查 (依赖/路径)
- run <component>: 转发到对应子工具
- pipeline: 一键流水线 (snapshot -> sync -> mirror push -> settle)

用法:
    python workstation.py init
    python workstation.py status
    python workstation.py doctor
    python workstation.py pipeline --entity mydata --source ./data
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

console = Console()

# workspace 根目录默认为项目根
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

# toolchain 组件清单: 名称 -> 描述/路径
TOOLCHAIN_COMPONENTS = {
    "snapshot_cli": {
        "desc": "Snapshot 备份恢复 CLI",
        "script": "bin/snapshot_cli.py",
        "module": "ai_llm_agent_crawler.versioning.snapshot_manager",
    },
    "snapshot_ui": {
        "desc": "Snapshot 交互式 UI",
        "script": "bin/snapshot_ui.py",
        "module": "ai_llm_agent_crawler.versioning.snapshot_manager",
    },
    "freefilesync_gen": {
        "desc": "FreeFileSync 无人值守同步生成器",
        "script": "bin/freefilesync_gen.py",
        "module": None,
    },
    "git_mirror_cli": {
        "desc": "Git 镜像池 CLI (pool/img, push github)",
        "script": "bin/git_mirror_cli.py",
        "module": "ai_llm_agent_crawler.storage.git_mirror_pool",
    },
    "agent_skills_workscript": {
        "desc": "Agent skills workScript + 算法 POOL",
        "script": "bin/agent_skills_workscript.py",
        "module": "ai_llm_agent_crawler.algorithm.algorithm_pool",
    },
    "algorithm_pool": {
        "desc": "算法 POOL 注册表",
        "script": None,
        "module": "ai_llm_agent_crawler.algorithm.algorithm_pool",
    },
    "performance_budget": {
        "desc": "系统性能预算",
        "script": None,
        "module": "ai_llm_agent_crawler.algorithm.performance_budget",
    },
    "data_settlement": {
        "desc": "数据清算分析",
        "script": None,
        "module": "ai_llm_agent_crawler.algorithm.data_settlement",
    },
}

# workspace 目录布局
WORKSPACE_DIRS = [
    "data/datasets",
    "data/snapshots",
    "data/versions",
    "git_mirror_pool",
    "skills",
    "ffs_generated",
    "logs",
    "workscripts",
]


def _bin_path(name: str) -> Path:
    return WORKSPACE_ROOT / TOOLCHAIN_COMPONENTS[name]["script"]


def _check_module(module: str) -> bool:
    try:
        __import__(module)
        return True
    except Exception:
        return False


def _check_script(path: Path) -> bool:
    return path.exists()


# ============================== CLI ==============================


@click.group()
def cli() -> None:
    """Workspace Workstation Toolchain (full work 栈)。"""


@cli.command("init")
@click.option("--root", default=WORKSPACE_ROOT, type=click.Path(path_type=Path), help="workspace 根目录")
def init_cmd(root: Path) -> None:
    """初始化 workspace 目录结构。"""
    created: List[str] = []
    for d in WORKSPACE_DIRS:
        target = root / d
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))
    if created:
        console.print(f"[green]已创建 {len(created)} 个目录:[/green]")
        for c in created:
            console.print(f"  - {c}")
    else:
        console.print("[yellow]workspace 目录已存在, 无需初始化[/yellow]")


@cli.command("status")
def status_cmd() -> None:
    """工具链状态总览。"""
    table = Table(title="Workstation Toolchain 状态", show_lines=True)
    table.add_column("组件", style="cyan")
    table.add_column("描述")
    table.add_column("脚本", justify="center")
    table.add_column("模块", justify="center")
    for name, info in TOOLCHAIN_COMPONENTS.items():
        script_ok = True
        if info["script"]:
            script_ok = _check_script(_bin_path(name))
        module_ok = True
        if info["module"]:
            module_ok = _check_module(info["module"])
        table.add_row(
            name,
            info["desc"],
            ("✓" if script_ok else "✗") if info["script"] else "-",
            ("✓" if module_ok else "✗") if info["module"] else "-",
        )
    console.print(table)

    # workspace 目录状态
    dir_table = Table(title="Workspace 目录")
    dir_table.add_column("目录", style="cyan")
    dir_table.add_column("存在", justify="center")
    dir_table.add_column("条目数", justify="right")
    for d in WORKSPACE_DIRS:
        p = WORKSPACE_ROOT / d
        exists = p.exists()
        count = str(len(list(p.iterdir()))) if exists and p.is_dir() else "-"
        dir_table.add_row(d, "✓" if exists else "✗", count)
    console.print(dir_table)


@cli.command("doctor")
def doctor_cmd() -> None:
    """健康检查 (依赖/路径/python 版本/git)。"""
    issues: List[str] = []

    # python 版本
    py_ver = sys.version.split()[0]
    console.print(f"Python: [cyan]{py_ver}[/cyan]")
    if sys.version_info < (3, 10):
        issues.append("Python 版本 < 3.10 (项目要求 >=3.10)")

    # git
    git_path = shutil.which("git")
    if git_path:
        console.print(f"git: [cyan]{git_path}[/cyan]")
    else:
        issues.append("git 未安装 (git 镜像池需要)")

    # FreeFileSync
    ffs_path = shutil.which("FreeFileSync")
    if ffs_path:
        console.print(f"FreeFileSync: [cyan]{ffs_path}[/cyan]")
    else:
        console.print("[yellow]FreeFileSync: 未安装 (仍可生成批处理模板)[/yellow]")

    # 核心模块导入
    core_modules = [
        "ai_llm_agent_crawler.versioning.snapshot_manager",
        "ai_llm_agent_crawler.storage.git_mirror_pool",
        "ai_llm_agent_crawler.algorithm.algorithm_pool",
        "ai_llm_agent_crawler.algorithm.performance_budget",
        "ai_llm_agent_crawler.algorithm.data_settlement",
    ]
    for m in core_modules:
        if _check_module(m):
            console.print(f"模块 {m}: [green]✓[/green]")
        else:
            issues.append(f"模块导入失败: {m}")
            console.print(f"模块 {m}: [red]✗[/red]")

    if issues:
        console.print(Panel.fit(
            "\n".join(f"[red]- {i}[/red]" for i in issues),
            title=f"[red]发现 {len(issues)} 个问题[/red]",
        ))
        sys.exit(1)
    else:
        console.print(Panel.fit("[green]所有检查通过[/green]", title="Doctor"))


@cli.command("run")
@click.argument("component", type=click.Choice([k for k, v in TOOLCHAIN_COMPONENTS.items() if v["script"]]))
@click.argument("args", nargs=-1)
def run_cmd(component: str, args: tuple) -> None:
    """转发到对应子工具: run <component> [args...]"""
    script = _bin_path(component)
    if not script.exists():
        console.print(f"[red]脚本不存在: {script}[/red]")
        sys.exit(1)
    py = sys.executable
    cmd = [py, str(script), *args]
    console.print(f"[cyan]运行:[/cyan] {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


@cli.command("pipeline")
@click.option("--entity", required=True, help="实体 ID")
@click.option("--source", required=True, type=click.Path(exists=True, path_type=Path), help="源数据路径")
@click.option("--mirror-name", default=None, help="同步到 git 镜像池的镜像名 (可选)")
@click.option("--github-remote", default=None, help="github push 目标 (可选)")
@click.option("--skip-sync", is_flag=True, default=False, help="跳过 FreeFileSync 同步")
@click.option("--skip-mirror", is_flag=True, default=False, help="跳过 git 镜像池推送")
def pipeline_cmd(
    entity: str,
    source: Path,
    mirror_name: Optional[str],
    github_remote: Optional[str],
    skip_sync: bool,
    skip_mirror: bool,
) -> None:
    """
    一键流水线: snapshot -> (sync) -> (mirror push) -> settle

    1. 对 source 创建完整快照
    2. 可选: 用 FreeFileSync 同步到备份目录
    3. 可选: 推送快照目录到 git 镜像池/github
    4. 生成数据清算报告 (本次 vs 上次)
    """
    from ai_llm_agent_crawler.algorithm.data_settlement import DataSettlement
    from ai_llm_agent_crawler.versioning.snapshot_manager import (
        CompressionType,
        SnapshotManager,
    )
    import pandas as pd

    py = sys.executable
    bin_dir = WORKSPACE_ROOT / "bin"

    # Step 1: 快照
    console.print(Panel.fit("[cyan]Step 1/4: 创建快照[/cyan]", title="Pipeline"))
    snap_mgr = SnapshotManager()
    meta = snap_mgr.create_full_snapshot(
        entity_id=entity,
        source_path=source,
        compression_type=CompressionType.TAR_GZ,
        created_by="workstation-pipeline",
    )
    console.print(f"[green]快照:[/green] {meta.snapshot_id} ({meta.compressed_size} bytes)")

    # Step 2: FreeFileSync 同步 (可选)
    if not skip_sync:
        console.print(Panel.fit("[cyan]Step 2/4: FreeFileSync 同步 (跳过, 需配置同步对)[/cyan]", title="Pipeline"))
        console.print("[yellow]提示: 用 'python bin/freefilesync_gen.py add ...' 配置同步对后, 生成批处理[/yellow]")

    # Step 3: git 镜像池推送 (可选)
    if not skip_mirror and mirror_name:
        console.print(Panel.fit("[cyan]Step 3/4: git 镜像池推送[/cyan]", title="Pipeline"))
        cmd = [
            py, str(bin_dir / "git_mirror_cli.py"),
            "--pool-root", str(WORKSPACE_ROOT / "git_mirror_pool"),
            "push", "--name", mirror_name,
        ]
        if github_remote:
            console.print("[yellow]github_remote 需镜像已配置, 见 git_mirror_cli add --github[/yellow]")
        subprocess.run(cmd)
    else:
        console.print(Panel.fit("[cyan]Step 3/4: git 镜像池推送 (跳过)[/cyan]", title="Pipeline"))

    # Step 4: 数据清算 (本次快照元数据 vs 历史)
    console.print(Panel.fit("[cyan]Step 4/4: 数据清算分析[/cyan]", title="Pipeline"))
    snapshots = snap_mgr.list_snapshots(entity)
    if len(snapshots) >= 2:
        # 构造元数据 DataFrame 对比最近两次
        rows = []
        for s in snapshots[-2:]:
            rows.append({
                "id": s.snapshot_id,
                "size": s.compressed_size,
                "file_count": s.file_count,
                "type": s.snapshot_type.value,
            })
        left_df = pd.DataFrame([rows[0]])
        right_df = pd.DataFrame([rows[1]])
        settler = DataSettlement()
        report = settler.settle(left_df, right_df, key="id", left_name="prev", right_name="curr")
        console.print(settler.summary(report))
    else:
        console.print("[yellow]快照数 < 2, 跳过清算 (需至少 2 次快照才能对账)[/yellow]")

    console.print(Panel.fit("[green]Pipeline 完成[/green]", title="Pipeline"))


@cli.command("components")
def components_cmd() -> None:
    """列出所有 toolchain 组件。"""
    table = Table(title="Toolchain 组件")
    table.add_column("名称", style="cyan")
    table.add_column("描述")
    table.add_column("脚本路径")
    for name, info in TOOLCHAIN_COMPONENTS.items():
        table.add_row(name, info["desc"], info["script"] or "(仅模块)")
    console.print(table)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
