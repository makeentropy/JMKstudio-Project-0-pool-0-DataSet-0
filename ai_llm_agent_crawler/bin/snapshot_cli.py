#!/usr/bin/env python
"""
Snapshot 备份恢复 CLI 管理脚本

基于 rich + click 实现的终端彩色命令行工具，封装 SnapshotManager，
提供快照创建/列出/恢复/验证/删除/清理/统计等命令。

用法示例:
    python snapshot_cli.py create-full --entity mydata --source ./data
    python snapshot_cli.py create-inc --entity mydata --source ./data
    python snapshot_cli.py list --entity mydata
    python snapshot_cli.py restore --entity mydata --id snap_xxx --out ./restored
    python snapshot_cli.py verify --entity mydata --id snap_xxx
    python snapshot_cli.py stats --entity mydata
    python snapshot_cli.py cleanup --entity mydata --keep 10
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# 允许直接从 bin/ 运行: 把 src 加入 sys.path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ai_llm_agent_crawler.utils.logging import get_logger  # noqa: E402
from ai_llm_agent_crawler.versioning.snapshot_manager import (  # noqa: E402
    CompressionType,
    SnapshotManager,
    SnapshotStatus,
    SnapshotType,
)

console = Console()
logger = get_logger(__name__)


def _get_manager(storage_path: Optional[Path] = None) -> SnapshotManager:
    """构造 SnapshotManager，可选自定义存储路径。"""
    if storage_path:
        # 延迟导入以避免循环
        from ai_llm_agent_crawler.versioning.snapshot_manager import SnapshotStorage

        storage = SnapshotStorage(storage_path=storage_path)
        return SnapshotManager(storage=storage)
    return SnapshotManager()


def _parse_compression(value: str) -> CompressionType:
    """解析压缩类型字符串。"""
    try:
        return CompressionType(value)
    except ValueError:
        raise click.BadParameter(
            f"无效压缩类型: {value}. 可选: {[c.value for c in CompressionType]}"
        )


@click.group(help="Snapshot 备份恢复管理 CLI")
@click.option(
    "--storage",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="快照存储根目录 (默认使用 settings.dataset_output_dir/snapshots)",
)
@click.option("--debug/--no-debug", default=False, help="调试模式")
@click.pass_context
def cli(ctx: click.Context, storage: Optional[Path], debug: bool) -> None:
    """CLI 入口组。"""
    ctx.ensure_object(dict)
    ctx.obj["storage"] = storage
    ctx.obj["debug"] = debug


@cli.command("create-full", help="创建完整快照")
@click.option("--entity", required=True, help="实体 ID")
@click.option("--source", required=True, type=click.Path(exists=True, path_type=Path), help="源路径")
@click.option("--name", default=None, help="快照名称")
@click.option("--desc", default="", help="快照描述")
@click.option(
    "--compression",
    default="none",
    type=click.Choice([c.value for c in CompressionType]),
    help="压缩类型",
)
@click.option("--created-by", default="cli", help="创建者")
@click.pass_context
def create_full(
    ctx: click.Context,
    entity: str,
    source: Path,
    name: Optional[str],
    desc: str,
    compression: str,
    created_by: str,
) -> None:
    manager = _get_manager(ctx.obj["storage"])
    comp = _parse_compression(compression)
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as prog:
        task = prog.add_task(f"创建完整快照 {entity} ...", total=None)
        meta = manager.create_full_snapshot(
            entity_id=entity,
            source_path=source,
            name=name,
            description=desc,
            compression_type=comp,
            created_by=created_by,
        )
        prog.update(task, completed=True)
    console.print(Panel.fit(
        f"[green]完整快照创建成功[/green]\n"
        f"ID: {meta.snapshot_id}\n"
        f"类型: {meta.snapshot_type.value}\n"
        f"原始大小: {meta.original_size} bytes\n"
        f"压缩大小: {meta.compressed_size} bytes\n"
        f"压缩率: {meta.compression_ratio:.2%}\n"
        f"校验和: {meta.checksum[:16]}...\n"
        f"存储路径: {meta.storage_path}",
        title="Snapshot",
    ))


@cli.command("create-inc", help="创建增量快照")
@click.option("--entity", required=True, help="实体 ID")
@click.option("--source", required=True, type=click.Path(exists=True, path_type=Path), help="源路径")
@click.option("--parent", default=None, help="父快照 ID (默认最新完整快照)")
@click.option("--name", default=None, help="快照名称")
@click.option("--desc", default="", help="快照描述")
@click.option(
    "--compression",
    default="none",
    type=click.Choice([c.value for c in CompressionType]),
    help="压缩类型",
)
@click.option("--created-by", default="cli", help="创建者")
@click.pass_context
def create_inc(
    ctx: click.Context,
    entity: str,
    source: Path,
    parent: Optional[str],
    name: Optional[str],
    desc: str,
    compression: str,
    created_by: str,
) -> None:
    manager = _get_manager(ctx.obj["storage"])
    comp = _parse_compression(compression)
    meta = manager.create_incremental_snapshot(
        entity_id=entity,
        source_path=source,
        parent_snapshot_id=parent,
        name=name,
        description=desc,
        compression_type=comp,
        created_by=created_by,
    )
    console.print(Panel.fit(
        f"[green]增量快照创建成功[/green]\n"
        f"ID: {meta.snapshot_id}\n"
        f"父快照: {meta.parent_snapshot}\n"
        f"增量大小: {meta.delta_size} bytes\n"
        f"新增: {len(meta.added_files)} / 修改: {len(meta.changed_files)} / 删除: {len(meta.deleted_files)}",
        title="Snapshot",
    ))


@cli.command("list", help="列出快照")
@click.option("--entity", required=True, help="实体 ID")
@click.option(
    "--type",
    default=None,
    type=click.Choice([t.value for t in SnapshotType]),
    help="按类型筛选",
)
@click.option(
    "--status",
    default=None,
    type=click.Choice([s.value for s in SnapshotStatus]),
    help="按状态筛选",
)
@click.pass_context
def list_snapshots(
    ctx: click.Context,
    entity: str,
    type: Optional[str],
    status: Optional[str],
) -> None:
    manager = _get_manager(ctx.obj["storage"])
    snap_type = SnapshotType(type) if type else None
    snap_status = SnapshotStatus(status) if status else None
    snapshots = manager.list_snapshots(entity, snap_type, snap_status)
    if not snapshots:
        console.print(f"[yellow]实体 {entity} 无快照[/yellow]")
        return
    table = Table(title=f"快照列表 - {entity}", show_lines=True)
    table.add_column("ID", style="cyan")
    table.add_column("类型")
    table.add_column("状态")
    table.add_column("压缩")
    table.add_column("大小", justify="right")
    table.add_column("创建时间")
    table.add_column("父快照")
    for s in snapshots:
        table.add_row(
            s.snapshot_id,
            s.snapshot_type.value,
            s.status.value,
            s.compression_type.value,
            str(s.compressed_size),
            s.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            s.parent_snapshot or "-",
        )
    console.print(table)


@cli.command("restore", help="恢复快照")
@click.option("--entity", required=True, help="实体 ID")
@click.option("--id", "snapshot_id", required=True, help="快照 ID")
@click.option("--out", required=True, type=click.Path(path_type=Path), help="输出路径")
@click.option("--no-verify", is_flag=True, default=False, help="跳过完整性验证")
@click.pass_context
def restore(
    ctx: click.Context,
    entity: str,
    snapshot_id: str,
    out: Path,
    no_verify: bool,
) -> None:
    manager = _get_manager(ctx.obj["storage"])
    ok = manager.restore_snapshot(entity, snapshot_id, out, verify_integrity=not no_verify)
    if ok:
        console.print(Panel.fit(f"[green]恢复成功[/green] -> {out}", title="Restore"))
    else:
        console.print(f"[red]恢复失败: {snapshot_id}[/red]")
        sys.exit(1)


@cli.command("verify", help="验证快照完整性")
@click.option("--entity", required=True, help="实体 ID")
@click.option("--id", "snapshot_id", required=True, help="快照 ID")
@click.pass_context
def verify(ctx: click.Context, entity: str, snapshot_id: str) -> None:
    manager = _get_manager(ctx.obj["storage"])
    ok = manager.verify_snapshot(entity, snapshot_id)
    if ok:
        console.print(f"[green]快照 {snapshot_id} 验证通过[/green]")
    else:
        console.print(f"[red]快照 {snapshot_id} 验证失败[/red]")
        sys.exit(1)


@cli.command("delete", help="删除快照")
@click.option("--entity", required=True, help="实体 ID")
@click.option("--id", "snapshot_id", required=True, help="快照 ID")
@click.option("--force", is_flag=True, default=False, help="强制删除 (含依赖的增量快照)")
@click.pass_context
def delete(ctx: click.Context, entity: str, snapshot_id: str, force: bool) -> None:
    manager = _get_manager(ctx.obj["storage"])
    ok = manager.delete_snapshot(entity, snapshot_id, force=force)
    if ok:
        console.print(f"[green]已删除: {snapshot_id}[/green]")
    else:
        console.print(f"[red]删除失败: {snapshot_id}[/red]")
        sys.exit(1)


@cli.command("cleanup", help="清理旧快照")
@click.option("--entity", required=True, help="实体 ID")
@click.option("--keep", default=10, type=int, help="保留数量")
@click.option("--no-keep-full", is_flag=True, default=False, help="不强制保留完整快照")
@click.pass_context
def cleanup(ctx: click.Context, entity: str, keep: int, no_keep_full: bool) -> None:
    manager = _get_manager(ctx.obj["storage"])
    deleted = manager.cleanup_old_snapshots(entity, keep_count=keep, keep_full_snapshots=not no_keep_full)
    console.print(f"[green]清理完成: 删除 {deleted} 个快照[/green]")


@cli.command("stats", help="快照统计")
@click.option("--entity", required=True, help="实体 ID")
@click.pass_context
def stats(ctx: click.Context, entity: str) -> None:
    manager = _get_manager(ctx.obj["storage"])
    s = manager.get_snapshot_statistics(entity)
    console.print(Panel.fit(
        f"实体: {s['entity_id']}\n"
        f"快照总数: {s['total_snapshots']}\n"
        f"完整快照: {s['full_snapshots']}\n"
        f"增量快照: {s['incremental_snapshots']}\n"
        f"压缩快照: {s['compressed_snapshots']}\n"
        f"总大小: {s['total_size']} bytes\n"
        f"原始总大小: {s['total_original_size']} bytes\n"
        f"平均压缩率: {s['avg_compression_ratio']:.2%}\n"
        f"已验证: {s['verified_snapshots']}\n"
        f"最新快照: {s['latest_snapshot_id']}",
        title="Snapshot 统计",
    ))


@cli.command("info", help="查看快照详情")
@click.option("--entity", required=True, help="实体 ID")
@click.option("--id", "snapshot_id", required=True, help="快照 ID")
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON 输出")
@click.pass_context
def info(ctx: click.Context, entity: str, snapshot_id: str, as_json: bool) -> None:
    manager = _get_manager(ctx.obj["storage"])
    meta = manager.get_snapshot(entity, snapshot_id)
    if meta is None:
        console.print(f"[red]快照不存在: {snapshot_id}[/red]")
        sys.exit(1)
    data = meta.model_dump()
    if as_json:
        console.print_json(json.dumps(data, default=str, ensure_ascii=False))
    else:
        console.print(Panel.fit(
            "\n".join(f"[cyan]{k}[/cyan]: {v}" for k, v in data.items()),
            title=f"快照 {snapshot_id}",
        ))


def main() -> None:
    """CLI 主入口。"""
    cli(obj={})


if __name__ == "__main__":
    main()
