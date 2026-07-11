#!/usr/bin/env python
"""
FreeFileSync 无人值守同步批处理文件生成器

生成 FreeFileSync 的 .ffs_batch 配置 + 调用它的 .bat/.sh 批处理文件,
实现无人值守定时同步。支持多同步对管理。

用法:
    python freefilesync_gen.py add --name daily --src D:\\data --dst E:\\backup
    python freefilesync_gen.py gen --name daily
    python freefilesync_gen.py gen-all
    python freefilesync_gen.py list
    python freefilesync_gen.py run --name daily
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# FreeFileSync 默认安装路径 (Windows)
FFS_DEFAULT_PATHS_WIN = [
    r"C:\Program Files\FreeFileSync\FreeFileSync.exe",
    r"C:\Program Files (x86)\FreeFileSync\FreeFileSync.exe",
    r"D:\Program Files\FreeFileSync\FreeFileSync.exe",
]
# Linux/macOS
FFS_DEFAULT_PATHS_UNIX = ["/usr/bin/FreeFileSync", "/usr/local/bin/FreeFileSync", "/opt/FreeFileSync/FreeFileSync"]


class SyncPair:
    """单个同步对配置。"""

    def __init__(
        self,
        name: str,
        source: str,
        target: str,
        compare_mode: str = "content",  # content | size | fileTime
        sync_variant: str = "mirror",  # mirror | update | twoWay
        include_filter: str = "*",
        exclude_filter: str = "",
        handle_deprecated: str = "delete",  # delete | recycle | ignore
        versioning_folder: Optional[str] = None,
        versioning_style: str = "replace",  # replace | timestamp
    ) -> None:
        self.name = name
        self.source = source
        self.target = target
        self.compare_mode = compare_mode
        self.sync_variant = sync_variant
        self.include_filter = include_filter
        self.exclude_filter = exclude_filter
        self.handle_deprecated = handle_deprecated
        self.versioning_folder = versioning_folder
        self.versioning_style = versioning_style

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "target": self.target,
            "compare_mode": self.compare_mode,
            "sync_variant": self.sync_variant,
            "include_filter": self.include_filter,
            "exclude_filter": self.exclude_filter,
            "handle_deprecated": self.handle_deprecated,
            "versioning_folder": self.versioning_folder,
            "versioning_style": self.versioning_style,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SyncPair":
        return cls(**d)


class FreeFileSyncGenerator:
    """FreeFileSync 批处理生成器, 管理多个同步对。"""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or Path("ffs_sync_pairs.json")
        self.pairs: Dict[str, SyncPair] = {}
        self._load()

    def _load(self) -> None:
        if self.config_path.exists():
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            for name, pair_data in data.get("pairs", {}).items():
                self.pairs[name] = SyncPair.from_dict(pair_data)

    def _save(self) -> None:
        data = {
            "pairs": {n: p.to_dict() for n, p in self.pairs.items()},
            "updated_at": datetime.now().isoformat(),
        }
        self.config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_pair(self, pair: SyncPair) -> None:
        self.pairs[pair.name] = pair
        self._save()
        console.print(f"[green]已添加同步对: {pair.name}[/green]")

    def remove_pair(self, name: str) -> bool:
        if name in self.pairs:
            del self.pairs[name]
            self._save()
            return True
        return False

    def list_pairs(self) -> List[SyncPair]:
        return list(self.pairs.values())

    def find_ffs_executable(self) -> Optional[str]:
        """查找 FreeFileSync 可执行文件路径。"""
        candidates = FFS_DEFAULT_PATHS_WIN if os.name == "nt" else FFS_DEFAULT_PATHS_UNIX
        for p in candidates:
            if Path(p).exists():
                return p
        # 尝试 PATH
        found = shutil.which("FreeFileSync")
        return found

    def generate_ffs_batch(self, pair: SyncPair, output_dir: Path) -> Path:
        """生成单个 .ffs_batch XML 配置文件。"""
        output_dir.mkdir(parents=True, exist_ok=True)
        batch_path = output_dir / f"{pair.name}.ffs_batch"

        # FreeFileSync 批处理 XML 结构
        root = ET.Element("FreeFileSync", {"XmlType": "BATCH", "XmlVersion": "11.9"})
        main = ET.SubElement(root, "Main")
        ET.SubElement(main, "Batch").set("Value", pair.name)
        ET.SubElement(main, "ErrorHandling").set("Value", "ignore")
        ET.SubElement(main, "PostSyncAction").set("Value", "none")

        cmp_cfg = ET.SubElement(root, "Compare")
        cmp_cfg.set("Variant", pair.compare_mode)
        cmp_cfg.set("TimeShift", "0")
        cmp_cfg.set("IgnoreTimeShift", "false")

        sync_cfg = ET.SubElement(root, "Synchronize")
        sync_cfg.set("Variant", pair.sync_variant)
        sync_cfg.set("DetectMovedFiles", "false")

        folders = ET.SubElement(root, "Folders")
        pair_el = ET.SubElement(folders, "Pair")
        ET.SubElement(pair_el, "Source").text = pair.source
        ET.SubElement(pair_el, "Target").text = pair.target

        filters = ET.SubElement(root, "Filter")
        ET.SubElement(filters, "Include").set("Value", pair.include_filter)
        ET.SubElement(filters, "Exclude").set("Value", pair.exclude_filter)

        # 处理已删除文件
        deprec = ET.SubElement(root, "HandleDeleted")
        deprec.set("Source", pair.handle_deprecated)
        deprec.set("Target", pair.handle_deprecated)
        if pair.versioning_folder:
            ET.SubElement(deprec, "VersioningFolder").text = pair.versioning_folder
            ET.SubElement(deprec, "VersioningStyle").set("Value", pair.versioning_style)

        # 美化并写入
        ET.indent(root, space="  ")
        tree = ET.ElementTree(root)
        tree.write(batch_path, encoding="utf-8", xml_declaration=True)
        return batch_path

    def generate_runner_batch(
        self,
        pair: SyncPair,
        ffs_batch_path: Path,
        output_dir: Path,
        ffs_exe: Optional[str] = None,
    ) -> Path:
        """生成调用 FreeFileSync 的 .bat (Windows) / .sh (Unix) 批处理。"""
        exe = ffs_exe or self.find_ffs_executable() or "FreeFileSync"
        if os.name == "nt":
            bat_path = output_dir / f"run_{pair.name}.bat"
            content = (
                "@echo off\n"
                f"REM FreeFileSync 无人值守同步: {pair.name}\n"
                f"REM 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f'set FFS_EXE="{exe}"\n'
                f'set BATCH_FILE="{ffs_batch_path}"\n'
                "if not exist %FFS_EXE% (\n"
                "    echo [ERROR] FreeFileSync.exe 未找到: %FFS_EXE%\n"
                "    exit /b 1\n"
                ")\n"
                '"%FFS_EXE%" "%BATCH_FILE%" /NoQuestions\n'
                "if %errorlevel%==0 (\n"
                f"    echo [OK] 同步完成: {pair.name}\n"
                ") else (\n"
                f"    echo [FAIL] 同步失败: {pair.name} ^(code %errorlevel%^)\n"
                "    exit /b %errorlevel%\n"
                ")\n"
            )
            bat_path.write_text(content, encoding="utf-8")
            return bat_path
        else:
            sh_path = output_dir / f"run_{pair.name}.sh"
            content = (
                "#!/usr/bin/env bash\n"
                f"# FreeFileSync 无人值守同步: {pair.name}\n"
                f"# 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "set -euo pipefail\n"
                f'FFS_EXE="{exe}"\n'
                f'BATCH_FILE="{ffs_batch_path}"\n'
                'if ! command -v "$FFS_EXE" >/dev/null 2>&1; then\n'
                '    echo "[ERROR] FreeFileSync 未找到: $FFS_EXE"\n'
                "    exit 1\n"
                "fi\n"
                '"$FFS_EXE" "$BATCH_FILE" --NoQuestions\n'
                f'echo "[OK] 同步完成: {pair.name}"\n'
            )
            sh_path.write_text(content, encoding="utf-8")
            os.chmod(sh_path, 0o755)
            return sh_path

    def generate_all(self, output_dir: Path) -> List[Path]:
        """为所有同步对生成批处理文件。"""
        generated: List[Path] = []
        for pair in self.pairs.values():
            batch = self.generate_ffs_batch(pair, output_dir)
            runner = self.generate_runner_batch(pair, batch, output_dir)
            generated.extend([batch, runner])
        return generated

    def run_pair(self, name: str) -> int:
        """直接运行某个同步对。"""
        pair = self.pairs.get(name)
        if pair is None:
            console.print(f"[red]同步对不存在: {name}[/red]")
            return 1
        exe = self.find_ffs_executable()
        if not exe:
            console.print("[red]未找到 FreeFileSync 可执行文件[/red]")
            return 1
        tmp_dir = Path("ffs_tmp")
        batch = self.generate_ffs_batch(pair, tmp_dir)
        console.print(f"[cyan]运行同步: {name} ({exe})[/cyan]")
        result = subprocess.run([exe, str(batch), "/NoQuestions" if os.name == "nt" else "--NoQuestions"])
        return result.returncode


# ============================== CLI ==============================


@click.group()
@click.option(
    "--config",
    type=click.Path(path_type=Path),
    default=Path("ffs_sync_pairs.json"),
    help="同步对配置文件",
)
@click.pass_context
def cli(ctx: click.Context, config: Path) -> None:
    """FreeFileSync 无人值守同步批处理生成器。"""
    ctx.obj = FreeFileSyncGenerator(config_path=config)


@cli.command("add")
@click.option("--name", required=True, help="同步对名称")
@click.option("--src", required=True, help="源目录")
@click.option("--dst", required=True, help="目标目录")
@click.option(
    "--variant",
    default="mirror",
    type=click.Choice(["mirror", "update", "twoWay"]),
    help="同步变体",
)
@click.option(
    "--compare",
    default="content",
    type=click.Choice(["content", "size", "fileTime"]),
    help="比较模式",
)
@click.option("--exclude", default="", help="排除过滤器")
@click.option("--versioning", default=None, help="版本化目录 (回收站)")
@click.pass_obj
def add_pair(
    gen: FreeFileSyncGenerator,
    name: str,
    src: str,
    dst: str,
    variant: str,
    compare: str,
    exclude: str,
    versioning: Optional[str],
) -> None:
    pair = SyncPair(
        name=name,
        source=src,
        target=dst,
        compare_mode=compare,
        sync_variant=variant,
        exclude_filter=exclude,
        versioning_folder=versioning,
    )
    gen.add_pair(pair)


@cli.command("remove")
@click.option("--name", required=True)
@click.pass_obj
def remove_pair(gen: FreeFileSyncGenerator, name: str) -> None:
    if gen.remove_pair(name):
        console.print(f"[green]已删除: {name}[/green]")
    else:
        console.print(f"[red]不存在: {name}[/red]")


@cli.command("list")
@click.pass_obj
def list_pairs(gen: FreeFileSyncGenerator) -> None:
    pairs = gen.list_pairs()
    if not pairs:
        console.print("[yellow]无同步对[/yellow]")
        return
    table = Table(title="FreeFileSync 同步对", show_lines=True)
    table.add_column("名称", style="cyan")
    table.add_column("源")
    table.add_column("目标")
    table.add_column("变体")
    table.add_column("比较")
    for p in pairs:
        table.add_row(p.name, p.source, p.target, p.sync_variant, p.compare_mode)
    console.print(table)


@cli.command("gen")
@click.option("--name", required=True, help="同步对名称")
@click.option("--out", default=Path("ffs_generated"), type=click.Path(path_type=Path), help="输出目录")
@click.pass_obj
def gen_one(gen: FreeFileSyncGenerator, name: str, out: Path) -> None:
    pair = gen.pairs.get(name)
    if pair is None:
        console.print(f"[red]不存在: {name}[/red]")
        sys.exit(1)
    batch = gen.generate_ffs_batch(pair, out)
    runner = gen.generate_runner_batch(pair, batch, out)
    console.print(Panel.fit(
        f"[green]生成成功[/green]\nFFS 批处理: {batch}\n运行器: {runner}",
        title=name,
    ))


@cli.command("gen-all")
@click.option("--out", default=Path("ffs_generated"), type=click.Path(path_type=Path), help="输出目录")
@click.pass_obj
def gen_all(gen: FreeFileSyncGenerator, out: Path) -> None:
    files = gen.generate_all(out)
    console.print(f"[green]生成 {len(files)} 个文件 -> {out}[/green]")
    for f in files:
        console.print(f"  - {f}")


@cli.command("run")
@click.option("--name", required=True)
@click.pass_obj
def run(gen: FreeFileSyncGenerator, name: str) -> None:
    code = gen.run_pair(name)
    sys.exit(code)


@cli.command("detect")
@click.pass_obj
def detect(gen: FreeFileSyncGenerator) -> None:
    exe = gen.find_ffs_executable()
    if exe:
        console.print(f"[green]FreeFileSync: {exe}[/green]")
    else:
        console.print("[yellow]未找到 FreeFileSync (仍可生成批处理模板)[/yellow]")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
