"""Notebook 模型与代码执行。"""

from __future__ import annotations

import io
import time
import traceback
import uuid
from contextlib import redirect_stdout
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class CellType(str, Enum):
    CODE = "code"
    MARKDOWN = "markdown"


@dataclass
class ExecutionResult:
    """单元格执行结果。"""

    ok: bool
    stdout: str = ""
    value: Any = None
    error: str = ""
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["value_repr"] = repr(self.value) if self.value is not None else ""
        # value 保持原样（JSON 可序列化时）
        try:
            import json

            json.dumps(self.value)
            d["value"] = self.value
        except (TypeError, ValueError):
            d["value"] = repr(self.value)
        return d


@dataclass
class Cell:
    """notebook 单元格。"""

    cell_type: CellType
    source: str = ""
    cell_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    result: ExecutionResult | None = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "cell_type": self.cell_type.value,
            "source": self.source,
            "result": self.result.to_dict() if self.result else None,
            "created_at": self.created_at,
        }


class Notebook:
    """内存 notebook，支持 Python 代码执行（共享命名空间）。"""

    def __init__(self, name: str = "untitled") -> None:
        self.name: str = name
        self.cells: list[Cell] = []
        self._globals: dict[str, Any] = {"__name__": "__notebook__"}
        # 注入便捷导入
        self._bootstrap()

    def _bootstrap(self) -> None:
        bootstrap = (
            "from ai_llm_agent_crawler import get_logger, setup_logging\n"
            "from ai_llm_agent_crawler.llm_engine import (\n"
            "    LlamaCppAdapter, LlamaCppConfig, JsAgentClient, JsAgentConfig,\n"
            "    FullAuditAgent, ChatMessage, ChatRole, CompletionRequest,\n"
            ")\n"
            "from ai_llm_agent_crawler.security import (\n"
            "    NoiseDictionary, XorClockCodec, BlockchainEncodingContainer,\n"
            "    AESCipher, HashCalculator,\n"
            ")\n"
            "from ai_llm_agent_crawler.skills_pool import (\n"
            "    SkillsPool, Skill, DatasetEntry, EfficiencyTracker,\n"
            ")\n"
            "from ai_llm_agent_crawler.business_tools import (\n"
            "    RunningTracker, RunRecord, BudgetTool, BioScienceDataset,\n"
            ")\n"
        )
        try:
            exec(bootstrap, self._globals)  # noqa: S102
        except Exception:  # pragma: no cover  - 注入失败不阻断
            pass

    # ------------------------------------------------------------------ cells
    def add_cell(self, cell_type: CellType | str, source: str = "") -> Cell:
        ct = cell_type if isinstance(cell_type, CellType) else CellType(cell_type)
        cell = Cell(cell_type=ct, source=source)
        self.cells.append(cell)
        return cell

    def get_cell(self, cell_id: str) -> Cell | None:
        for c in self.cells:
            if c.cell_id == cell_id:
                return c
        return None

    def update_cell(self, cell_id: str, source: str | None = None) -> Cell | None:
        cell = self.get_cell(cell_id)
        if cell is None:
            return None
        if source is not None:
            cell.source = source
        return cell

    def delete_cell(self, cell_id: str) -> bool:
        cell = self.get_cell(cell_id)
        if cell is None:
            return False
        self.cells.remove(cell)
        return True

    # ------------------------------------------------------------------ exec
    def run_cell(self, cell_id: str) -> ExecutionResult:
        cell = self.get_cell(cell_id)
        if cell is None:
            raise KeyError(f"未找到 cell: {cell_id}")
        if cell.cell_type == CellType.MARKDOWN:
            cell.result = ExecutionResult(ok=True, value=cell.source)
            return cell.result
        return self._run_code(cell)

    def _run_code(self, cell: Cell) -> ExecutionResult:
        import ast

        start = time.perf_counter()
        buf = io.StringIO()
        try:
            code = cell.source
            # 解析 AST，分离末尾表达式语句以便捕获其值（类似 notebook 行为）
            tree = ast.parse(code)
            last_expr_node: ast.Expression | None = None
            if tree.body:
                last_stmt = tree.body[-1]
                if isinstance(last_stmt, ast.Expr):
                    last_expr_node = ast.Expression(body=last_stmt.value)
                    tree.body = tree.body[:-1]

            with redirect_stdout(buf):
                if tree.body:
                    exec(compile(tree, f"<cell {cell.cell_id}>", "exec"), self._globals)  # noqa: S102
                if last_expr_node is not None:
                    value = eval(  # noqa: S307
                        compile(last_expr_node, f"<cell {cell.cell_id}>", "eval"),
                        self._globals,
                    )
                else:
                    value = None
            stdout = buf.getvalue()
            elapsed = (time.perf_counter() - start) * 1000
            result = ExecutionResult(
                ok=True, stdout=stdout, value=value, elapsed_ms=round(elapsed, 3)
            )
        except Exception:  # noqa: BLE001
            elapsed = (time.perf_counter() - start) * 1000
            result = ExecutionResult(
                ok=False,
                stdout=buf.getvalue(),
                error=traceback.format_exc(),
                elapsed_ms=round(elapsed, 3),
            )
        cell.result = result
        return result

    def run_all(self) -> list[ExecutionResult]:
        return [self.run_cell(c.cell_id) for c in self.cells if c.cell_type == CellType.CODE]

    # ------------------------------------------------------------------ export
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "cell_count": len(self.cells),
            "cells": [c.to_dict() for c in self.cells],
        }

    def reset(self) -> None:
        self.cells.clear()
        self._globals = {"__name__": "__notebook__"}
        self._bootstrap()
