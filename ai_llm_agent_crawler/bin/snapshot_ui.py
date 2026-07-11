#!/usr/bin/env python
"""
Snapshot 备份恢复交互式 UI 管理脚本

基于 rich 的交互式菜单 UI，封装 SnapshotManager，提供无需记忆命令的
向导式快照管理体验。适合不熟悉 CLI 参数的用户。

运行: python snapshot_ui.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

# 允许直接从 bin/ 运行
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ai_llm_agent_crawler.utils.logging import get_logger  # noqa: E402
from ai_llm_agent_crawler.versioning.snapshot_manager import (  # noqa: E402
    CompressionType,
    SnapshotManager,
    SnapshotType,
)

console = Console()
logger = get_logger(__name__)


class SnapshotUI:
    """Snapshot 交互式 UI 控制器。"""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        if storage_path:
            from ai_llm_agent_crawler.versioning.snapshot_manager import SnapshotStorage

            storage = SnapshotStorage(storage_path=storage_path)
            self.manager = SnapshotManager(storage=storage)
        else:
            self.manager = SnapshotManager()
        self._storage_path = storage_path

    def banner(self) -> None:
        """打印标题面板。"""
        console.print(Panel.fit(
            "[bold cyan]Snapshot 备份恢复管理[/bold cyan]\n"
            "基于 SnapshotManager 的交互式管理工具",
            border_style="cyan",
        ))

    def menu(self) -> None:
        """主菜单循环。"""
        options = {
            "1": ("创建完整快照", self.create_full),
            "2": ("创建增量快照", self.create_inc),
            "3": ("列出快照", self.list_snapshots),
            "4": ("恢复快照", self.restore),
            "5": ("验证快照", self.verify),
            "6": ("删除快照", self.delete),
            "7": ("清理旧快照", self.cleanup),
            "8": ("快照统计", self.stats),
            "9": ("查看快照详情", self.info),
            "0": ("退出", self.quit),
        }
        while True:
            self.banner()
            table = Table(title="主菜单", show_header=False, box=None)
            table.add_column("key", style="cyan", width=4)
            table.add_column("action")
            for key, (label, _) in options.items():
                table.add_row(key, label)
            console.print(table)
            choice = Prompt.ask("选择操作", choices=list(options.keys()), default="0")
            _, action = options[choice]
            try:
                action()
            except KeyboardInterrupt:
                console.print("\n[yellow]已中断[/yellow]")
            except Exception as e:
                console.print(f"[red]错误: {e}[/red]")
                logger.error(f"UI 操作失败: {e}")
            if choice == "0":
                break
            console.print()

    def _ask_entity(self) -> str:
        return Prompt.ask("实体 ID")

    def _ask_source(self) -> Path:
        p = Prompt.ask("源路径")
        path = Path(p)
        if not path.exists():
            console.print(f"[red]路径不存在: {path}[/red]")
            raise FileNotFoundError(path)
        return path

    def _ask_compression(self) -> CompressionType:
        choices = [c.value for c in CompressionType]
        comp = Prompt.ask("压缩类型", choices=choices, default="none")
        return CompressionType(comp)

    def create_full(self) -> None:
        entity = self._ask_entity()
        source = self._ask_source()
        name = Prompt.ask("快照名称", default="")
        desc = Prompt.ask("描述", default="")
        comp = self._ask_compression()
        meta = self.manager.create_full_snapshot(
            entity_id=entity,
            source_path=source,
            name=name or None,
            description=desc,
            compression_type=comp,
        )
        console.print(Panel.fit(
            f"[green]完整快照创建成功[/green]\nID: {meta.snapshot_id}\n"
            f"大小: {meta.compressed_size} bytes\n校验和: {meta.checksum[:16]}...",
            title="完成",
        ))

    def create_inc(self) -> None:
        entity = self._ask_entity()
        source = self._ask_source()
        parent = Prompt.ask("父快照 ID (留空使用最新完整快照)", default="")
        comp = self._ask_compression()
        meta = self.manager.create_incremental_snapshot(
            entity_id=entity,
            source_path=source,
            parent_snapshot_id=parent or None,
            compression_type=comp,
        )
        console.print(Panel.fit(
            f"[green]增量快照创建成功[/green]\nID: {meta.snapshot_id}\n"
            f"增量大小: {meta.delta_size} bytes",
            title="完成",
        ))

    def list_snapshots(self) -> None:
        entity = self._ask_entity()
        snapshots = self.manager.list_snapshots(entity)
        if not snapshots:
            console.print(f"[yellow]实体 {entity} 无快照[/yellow]")
            return
        table = Table(title=f"快照列表 - {entity}", show_lines=True)
        table.add_column("ID", style="cyan")
        table.add_column("类型")
        table.add_column("状态")
        table.add_column("大小", justify="right")
        table.add_column("创建时间")
        for s in snapshots:
            table.add_row(
                s.snapshot_id,
                s.snapshot_type.value,
                s.status.value,
                str(s.compressed_size),
                s.created_at.strftime("%Y-%m-%d %H:%M"),
            )
        console.print(table)

    def restore(self) -> None:
        entity = self._ask_entity()
        snapshot_id = Prompt.ask("快照 ID")
        out = Path(Prompt.ask("输出路径"))
        verify = Confirm.ask("恢复前验证完整性", default=True)
        ok = self.manager.restore_snapshot(entity, snapshot_id, out, verify_integrity=verify)
        console.print("[green]恢复成功[/green]" if ok else "[red]恢复失败[/red]")

    def verify(self) -> None:
        entity = self._ask_entity()
        snapshot_id = Prompt.ask("快照 ID")
        ok = self.manager.verify_snapshot(entity, snapshot_id)
        console.print(f"[green]验证通过: {snapshot_id}[/green]" if ok else f"[red]验证失败: {snapshot_id}[/red]")

    def delete(self) -> None:
        entity = self._ask_entity()
        snapshot_id = Prompt.ask("快照 ID")
        force = Confirm.ask("强制删除 (含依赖的增量快照)", default=False)
        ok = self.manager.delete_snapshot(entity, snapshot_id, force=force)
        console.print(f"[green]已删除: {snapshot_id}[/green]" if ok else "[red]删除失败[/red]")

    def cleanup(self) -> None:
        entity = self._ask_entity()
        keep = IntPrompt.ask("保留数量", default=10)
        deleted = self.manager.cleanup_old_snapshots(entity, keep_count=keep)
        console.print(f"[green]清理完成: 删除 {deleted} 个快照[/green]")

    def stats(self) -> None:
        entity = self._ask_entity()
        s = self.manager.get_snapshot_statistics(entity)
        console.print(Panel.fit(
            f"快照总数: {s['total_snapshots']}\n"
            f"完整: {s['full_snapshots']} / 增量: {s['incremental_snapshots']}\n"
            f"总大小: {s['total_size']} bytes\n"
            f"平均压缩率: {s['avg_compression_ratio']:.2%}",
            title=f"统计 - {entity}",
        ))

    def info(self) -> None:
        entity = self._ask_entity()
        snapshot_id = Prompt.ask("快照 ID")
        meta = self.manager.get_snapshot(entity, snapshot_id)
        if meta is None:
            console.print(f"[red]快照不存在: {snapshot_id}[/red]")
            return
        data = meta.model_dump()
        console.print(Panel.fit(
            "\n".join(f"[cyan]{k}[/cyan]: {v}" for k, v in data.items()),
            title=f"快照 {snapshot_id}",
        ))

    def quit(self) -> None:
        console.print("[cyan]再见[/cyan]")


def main() -> None:
    """UI 主入口。"""
    storage = None
    if len(sys.argv) > 1:
        storage = Path(sys.argv[1])
    ui = SnapshotUI(storage_path=storage)
    try:
        ui.menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]已退出[/yellow]")


if __name__ == "__main__":
    main()
