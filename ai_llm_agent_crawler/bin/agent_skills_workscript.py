#!/usr/bin/env python
"""
Agent Skills workScript 运行器

功能:
1. 注册内置算法到算法 POOL (gen 算法 POOL)
2. 生成引用新模块 (snapshot / git mirror / settlement / budget) 的 skill
3. 运行 workScript (JSON 工作流, 串联 skill/算法执行)
4. 列出 skill 与算法

用法:
    python agent_skills_workscript.py register-builtin
    python agent_skills_workscript.py list-algos
    python agent_skills_workscript.py gen-skill --type settlement --name my_settle
    python agent_skills_workscript.py run --script workscript.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ai_llm_agent_crawler.algorithm.algorithm_pool import (  # noqa: E402
    AlgorithmPool,
    get_default_pool,
)
from ai_llm_agent_crawler.algorithm.data_settlement import DataSettlement  # noqa: E402
from ai_llm_agent_crawler.algorithm.performance_budget import (  # noqa: E402
    BudgetStatus,
    PerformanceBudget,
    ResourceKind,
)
from ai_llm_agent_crawler.utils.logging import get_logger  # noqa: E402

console = Console()
logger = get_logger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


# ====================== 内置算法注册 ======================


def register_builtin_algorithms(pool: AlgorithmPool) -> None:
    """向算法 POOL 注册内置算法 (gen 算法 POOL)。"""

    @pool.register(
        "dedup_hash",
        category="dedup",
        description="基于哈希集合去重",
        complexity="O(n)",
        accuracy=0.95,
        tags=["dedup", "hash"],
    )
    def dedup_hash(data: List[Any]) -> List[Any]:
        seen = set()
        result = []
        for item in data:
            key = json.dumps(item, sort_keys=True, default=str) if not isinstance(item, (str, int, float)) else item
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @pool.register(
        "dedup_pandas",
        category="dedup",
        description="基于 pandas DataFrame 去重",
        complexity="O(n)",
        accuracy=0.99,
        tags=["dedup", "pandas"],
    )
    def dedup_pandas(data: Any) -> Any:
        import pandas as pd

        if isinstance(data, pd.DataFrame):
            return data.drop_duplicates().reset_index(drop=True)
        return data

    @pool.register(
        "sort_quick",
        category="sort",
        description="快速排序 (内置 sorted)",
        complexity="O(n log n)",
        accuracy=1.0,
        tags=["sort"],
    )
    def sort_quick(data: List[Any], reverse: bool = False) -> List[Any]:
        return sorted(data, reverse=reverse)

    @pool.register(
        "hash_sha256",
        category="hash",
        description="SHA-256 哈希",
        complexity="O(n)",
        accuracy=1.0,
        tags=["hash", "sha256"],
    )
    def hash_sha256(data: str) -> str:
        return hashlib.sha256(str(data).encode("utf-8")).hexdigest()

    @pool.register(
        "settlement_reconcile",
        category="settlement",
        description="数据集对账清算",
        complexity="O(n)",
        accuracy=0.98,
        tags=["settlement", "reconcile"],
    )
    def settlement_reconcile(left: Any, right: Any, key: str = "id") -> Dict[str, Any]:
        import pandas as pd

        left_df = left if isinstance(left, pd.DataFrame) else pd.DataFrame(left)
        right_df = right if isinstance(right, pd.DataFrame) else pd.DataFrame(right)
        settler = DataSettlement(include_details=False)
        report = settler.settle(left_df, right_df, key=key)
        return report.model_dump()

    @pool.register(
        "budget_check",
        category="budget",
        description="性能预算检查",
        complexity="O(1)",
        accuracy=1.0,
        tags=["budget", "performance"],
    )
    def budget_check(usages: Dict[str, float], limits: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        pb = PerformanceBudget()
        limits = limits or {}
        defaults = {
            "cpu": 80.0,
            "memory": 8 * 1024**3,
            "disk": 100 * 1024**3,
            "concurrency": 100.0,
        }
        defaults.update(limits)
        for kind_name, limit in defaults.items():
            try:
                kind = ResourceKind(kind_name)
            except ValueError:
                continue
            pb.set_budget(kind, limit=limit)
        statuses = {}
        for kind_name, usage in usages.items():
            try:
                kind = ResourceKind(kind_name)
            except ValueError:
                continue
            statuses[kind_name] = pb.record(kind, usage).value
        return {"statuses": statuses, "health": pb.health_report()}


# ====================== Skill 生成器 ======================


SKILL_TEMPLATES = {
    "settlement": {
        "class": "DataSettlementSkill",
        "description": "数据清算分析 Skill (基于 DataSettlement)",
        "skill_type": "analyzer",
        "code": '''"""
{class_name} - 数据清算分析 Skill

引用 ai_llm_agent_crawler.algorithm.data_settlement.DataSettlement,
对两个数据集进行对账清算。
"""

from typing import Any, Dict, Optional

import pandas as pd

from ai_llm_agent_crawler.algorithm.data_settlement import DataSettlement, SettlementReport
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class {class_name}:
    """数据清算分析 skill"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {{}}
        self.name = "{name}"
        self.version = "1.0.0"
        self.settler = DataSettlement(
            tolerance=self.config.get("tolerance", 0.0),
            include_details=self.config.get("include_details", False),
        )

    def process(self, left: pd.DataFrame, right: pd.DataFrame, key: str = "id", **kwargs) -> SettlementReport:
        """执行清算。"""
        return self.settler.settle(left, right, key=key, **kwargs)

    def validate(self, report: SettlementReport) -> bool:
        """验证清算结果有效。"""
        return report.left_count >= 0 and report.right_count >= 0

    def summary(self, report: SettlementReport) -> str:
        return self.settler.summary(report)
''',
    },
    "snapshot": {
        "class": "SnapshotBackupSkill",
        "description": "快照备份 Skill (基于 SnapshotManager)",
        "skill_type": "processor",
        "code": '''"""
{class_name} - 快照备份 Skill

引用 ai_llm_agent_crawler.versioning.snapshot_manager.SnapshotManager,
提供快照备份能力的 skill 封装。
"""

from pathlib import Path
from typing import Any, Dict, Optional

from ai_llm_agent_crawler.utils.logging import get_logger
from ai_llm_agent_crawler.versioning.snapshot_manager import (
    CompressionType,
    SnapshotManager,
    SnapshotMetadata,
)

logger = get_logger(__name__)


class {class_name}:
    """快照备份 skill"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {{}}
        self.name = "{name}"
        self.version = "1.0.0"
        self.manager = SnapshotManager()

    def process(
        self,
        entity_id: str,
        source_path: str,
        compression: str = "none",
        **kwargs,
    ) -> SnapshotMetadata:
        """创建快照备份。"""
        comp = CompressionType(compression)
        return self.manager.create_full_snapshot(
            entity_id=entity_id,
            source_path=Path(source_path),
            compression_type=comp,
            **kwargs,
        )

    def validate(self, meta: SnapshotMetadata) -> bool:
        return meta.snapshot_id is not None and meta.checksum != ""
''',
    },
    "budget": {
        "class": "PerformanceBudgetSkill",
        "description": "性能预算 Skill (基于 PerformanceBudget)",
        "skill_type": "analyzer",
        "code": '''"""
{class_name} - 性能预算 Skill

引用 ai_llm_agent_crawler.algorithm.performance_budget.PerformanceBudget,
提供系统资源预算监控的 skill 封装。
"""

from typing import Any, Dict, Optional

from ai_llm_agent_crawler.algorithm.performance_budget import (
    BudgetStatus,
    PerformanceBudget,
    ResourceKind,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class {class_name}:
    """性能预算 skill"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {{}}
        self.name = "{name}"
        self.version = "1.0.0"
        self.budget = PerformanceBudget()
        for kind_name, limit in self.config.get("limits", {{}}).items():
            try:
                self.budget.set_budget(ResourceKind(kind_name), limit=limit)
            except ValueError:
                logger.warning(f"未知资源种类: {{kind_name}}")

    def process(self, usages: Dict[str, float]) -> Dict[str, Any]:
        """记录资源使用并返回健康报告。"""
        for kind_name, usage in usages.items():
            try:
                self.budget.record(ResourceKind(kind_name), usage)
            except ValueError:
                continue
        return self.budget.health_report()

    def validate(self, report: Dict[str, Any]) -> bool:
        return "overall_status" in report
''',
    },
}


def gen_skill_files(skill_type: str, name: str, skills_dir: Path) -> Path:
    """生成一个 skill 目录及其文件, 引用对应模块。返回目录路径。"""
    if skill_type not in SKILL_TEMPLATES:
        raise ValueError(f"未知 skill 类型: {skill_type}, 可选: {list(SKILL_TEMPLATES.keys())}")
    template = SKILL_TEMPLATES[skill_type]
    hash_part = hashlib.md5(f"{skill_type}_{name}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
    skill_id = f"{name}_{hash_part}"
    skill_dir = skills_dir / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)

    code = template["code"].format(class_name=template["class"], name=name)
    (skill_dir / "skill.py").write_text(code, encoding="utf-8")

    metadata = {
        "id": skill_id,
        "name": name,
        "version": "1.0.0",
        "description": template["description"],
        "skill_type": template["skill_type"],
        "status": "draft",
        "dataset_id": "",
        "dataset_name": "",
        "dataset_version": "1.0.0",
        "generated_from": "workscript",
        "dependencies": ["ai_llm_agent_crawler"],
        "config": {},
        "accuracy": 0.0,
        "efficiency": 0.0,
        "success_rate": 0.0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "published_at": None,
        "tags": [skill_type],
        "categories": [],
        "author": "workscript",
        "license": "MIT",
    }
    (skill_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (skill_dir / "config.json").write_text(
        json.dumps({"skill_type": skill_type, "name": name}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (skill_dir / "tests.json").write_text(
        json.dumps([
            {"name": "basic_test", "description": "基本功能测试", "input": {}, "expected_output": "valid"},
        ], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (skill_dir / "README.md").write_text(
        f"# {name} Skill\n\n{template['description']}\n\n"
        f"由 agent_skills_workscript.py 生成, 引用 {skill_type} 模块。\n",
        encoding="utf-8",
    )
    return skill_dir


# ====================== workScript 运行器 ======================


class WorkScriptRunner:
    """workScript 工作流运行器: 按 JSON 步骤串联算法执行。"""

    def __init__(self, pool: AlgorithmPool) -> None:
        self.pool = pool
        self.context: Dict[str, Any] = {}

    def run(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行 workScript。

        script 结构:
            {
              "name": "...",
              "steps": [
                {"id": "step1", "algo": "dedup_hash", "args": [...], "kwargs": {...}, "input_from": "step0"},
                ...
              ]
            }
        """
        results: Dict[str, Any] = {}
        for step in script.get("steps", []):
            sid = step["id"]
            algo = step["algo"]
            args = step.get("args", [])
            kwargs = step.get("kwargs", {})
            # 从上一步取输入
            input_from = step.get("input_from")
            if input_from:
                args = [results[input_from]] + list(args)
            console.print(f"[cyan]执行步骤[/cyan] {sid}: {algo}")
            try:
                result = self.pool.execute(algo, *args, **kwargs)
                results[sid] = result
                self.context[sid] = result
            except Exception as e:
                console.print(f"[red]步骤 {sid} 失败: {e}[/red]")
                results[sid] = {"error": str(e)}
        return {"name": script.get("name", "workscript"), "results": results}


# ====================== CLI ======================


@click.group()
def cli() -> None:
    """Agent skills workScript 运行器。"""


@cli.command("register-builtin")
def register_builtin() -> None:
    pool = get_default_pool()
    before = len(pool.list_names())
    register_builtin_algorithms(pool)
    after = len(pool.list_names())
    console.print(f"[green]注册内置算法: +{after - before} (总计 {after})[/green]")


@cli.command("list-algos")
def list_algos() -> None:
    pool = get_default_pool()
    if not pool.list_names():
        register_builtin_algorithms(pool)
    entries = pool.list_all()
    table = Table(title="算法 POOL", show_lines=True)
    table.add_column("名称", style="cyan")
    table.add_column("类别")
    table.add_column("复杂度")
    table.add_column("准确率", justify="right")
    table.add_column("状态")
    table.add_column("调用数", justify="right")
    for e in entries:
        table.add_row(
            e.name, e.category, e.complexity, f"{e.accuracy:.2f}", e.status, str(e.stat.call_count)
        )
    console.print(table)


@cli.command("gen-skill")
@click.option("--type", "skill_type", required=True, type=click.Choice(list(SKILL_TEMPLATES.keys())))
@click.option("--name", required=True, help="skill 名称")
@click.option("--skills-dir", default=SKILLS_DIR, type=click.Path(path_type=Path))
def gen_skill(skill_type: str, name: str, skills_dir: Path) -> None:
    skill_dir = gen_skill_files(skill_type, name, skills_dir)
    console.print(Panel.fit(
        f"[green]Skill 生成成功[/green]\n类型: {skill_type}\n名称: {name}\n路径: {skill_dir}",
        title="gen-skill",
    ))


@cli.command("list-skills")
@click.option("--skills-dir", default=SKILLS_DIR, type=click.Path(path_type=Path))
def list_skills(skills_dir: Path) -> None:
    if not skills_dir.exists():
        console.print(f"[yellow]skills 目录不存在: {skills_dir}[/yellow]")
        return
    table = Table(title="Skills", show_lines=True)
    table.add_column("ID", style="cyan")
    table.add_column("名称")
    table.add_column("类型")
    table.add_column("版本")
    table.add_column("状态")
    for d in sorted(skills_dir.iterdir()):
        meta_path = d / "metadata.json"
        if d.is_dir() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            table.add_row(
                meta.get("id", d.name),
                meta.get("name", ""),
                meta.get("skill_type", ""),
                meta.get("version", ""),
                meta.get("status", ""),
            )
    console.print(table)


@cli.command("run")
@click.option("--script", required=True, type=click.Path(exists=True, path_type=Path), help="workScript JSON 文件")
def run_workscript(script: Path) -> None:
    pool = get_default_pool()
    register_builtin_algorithms(pool)
    data = json.loads(script.read_text(encoding="utf-8"))
    runner = WorkScriptRunner(pool)
    result = runner.run(data)
    console.print_json(json.dumps(result, ensure_ascii=False, default=str))


@cli.command("pool-report")
def pool_report() -> None:
    pool = get_default_pool()
    if not pool.list_names():
        register_builtin_algorithms(pool)
    report = pool.pool_report()
    console.print(Panel.fit(
        f"算法总数: {report['total_algorithms']}\n"
        f"分类: {report['by_category']}\n"
        f"状态: {report['by_status']}\n"
        f"总调用: {report['total_calls']}",
        title="算法 POOL 报告",
    ))


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
