"""H5 内嵌 Jupyter IDE FastAPI 服务端。

启动方式：
    python -m ai_llm_agent_crawler.ide.server
    # 或
    ai-crawler ide --host 0.0.0.0 --port 8000

提供：
- ``/``              —— H5 内嵌 IDE 前端（浏览器预览）；
- ``/api/notebook/*``—— notebook 单元格管理与执行；
- ``/api/llm/*``     —— llama 引擎 / JS agent / full agent 审计与迭代；
- ``/api/security/*``—— XOR 时钟编解码、区块链编码容器；
- ``/api/skills/*``  —— skills/dataset 集赞积攒与清算；
- ``/api/tools/*``   —— 跑步 / 预算 / 生物科学数据集。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ai_llm_agent_crawler.ide.notebook import CellType, Notebook
from ai_llm_agent_crawler.llm_engine import (
    ChatMessage,
    CompletionRequest,
    FullAuditAgent,
    JsAgentClient,
    JsAgentConfig,
    LlamaCppAdapter,
    LlamaCppConfig,
)
from ai_llm_agent_crawler.security import (
    BlockchainEncodingContainer,
    XorClockCodec,
)
from ai_llm_agent_crawler.skills_pool import (
    DatasetEntry,
    EfficiencyTracker,
    Skill,
    SkillsPool,
)
from ai_llm_agent_crawler.business_tools import (
    BioScienceDataset,
    BudgetTool,
    RunningTracker,
)

# Pydantic 请求模型（模块级定义，确保 FastAPI 能通过 get_type_hints 解析）
from pydantic import BaseModel


class CellIn(BaseModel):
    cell_type: str = "code"
    source: str = ""


class CellUpdate(BaseModel):
    source: str | None = None


class CodeIn(BaseModel):
    code: str


class ChatIn(BaseModel):
    messages: list[dict[str, Any]]
    temperature: float = 0.7
    max_tokens: int = 1024


class AuditIn(BaseModel):
    target: str
    content: str
    context: dict[str, Any] = {}


class IterateIn(BaseModel):
    baseline_ms: float
    baseline_payload: dict[str, Any] = {}


class XorIn(BaseModel):
    plaintext: str
    dimension: str
    clock_seed: int


class XorDecodeIn(BaseModel):
    data_hex: str
    verify: bool = True


class MineIn(BaseModel):
    dictionary_entry: str
    ca_serial: str
    dimension: str
    clock_seed: int
    ciphertext_hex: str
    difficulty: int = 2


class SkillIn(BaseModel):
    name: str
    description: str = ""
    code: str = ""
    tags: list[str] = []
    author: str = "anonymous"


class DatasetIn(BaseModel):
    name: str
    format: str = "json"
    rows: int = 0
    size_bytes: int = 0
    tags: list[str] = []


class LikeIn(BaseModel):
    ref_id: str
    count: int = 1


class RunIn(BaseModel):
    distance_km: float
    duration_s: float
    avg_heart_rate: int = 0
    weight_kg: float = 65.0
    note: str = ""


class BudgetIn(BaseModel):
    amount: float
    category: str
    kind: str = "expense"
    note: str = ""


class BioIn(BaseModel):
    n: int = 10


_STATIC_DIR = Path(__file__).parent / "static"

# 全局运行时状态（单进程内存）
_NOTEBOOK = Notebook(name="trae-h5-ide")
_LLM_ENGINE = LlamaCppAdapter(LlamaCppConfig(mode=os.environ.get("LLAMA_MODE", "stub")))
_JS_AGENT = JsAgentClient(JsAgentConfig(mode=os.environ.get("JS_AGENT_MODE", "stub")))
_FULL_AGENT = FullAuditAgent(_LLM_ENGINE, _JS_AGENT)
_SKILLS_POOL = SkillsPool()
_EFF_TRACKER = EfficiencyTracker()
_RUNNER = RunningTracker()
_BUDGET = BudgetTool()
_BIO = BioScienceDataset()


def _build_models() -> tuple:
    """已弃用：模型已移至模块级。保留以兼容旧调用。"""
    return (
        CellIn, CellUpdate, CodeIn, ChatIn, AuditIn, IterateIn,
        XorIn, XorDecodeIn, MineIn, SkillIn, DatasetIn, LikeIn,
        RunIn, BudgetIn, BioIn,
    )


def create_app(embed: bool = False) -> Any:
    """创建 FastAPI 应用。

    Args:
        embed: 为 True 时进入「商用隐藏」模式：关闭 API 文档（/docs, /redoc），
            前端隐藏开发者标识，适合 H5 内嵌商用部署。
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(
        title="Trae H5 Embedded Jupyter IDE",
        docs_url=None if embed else "/docs",
        redoc_url=None if embed else "/redoc",
        openapi_url=None if embed else "/openapi.json",
    )

    # ============================================================ root
    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        idx = _STATIC_DIR / "index.html"
        html = idx.read_text(encoding="utf-8")
        if embed:
            html = html.replace("data-embed=\"false\"", "data-embed=\"true\"")
        return HTMLResponse(html)

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "embed": embed,
            "llm": _LLM_ENGINE.health(),
            "js_agent": _JS_AGENT.health(),
            "skills": len(_SKILLS_POOL),
            "cells": len(_NOTEBOOK.cells),
        }

    # ============================================================ notebook
    @app.get("/api/notebook")
    def nb_get() -> dict[str, Any]:
        return _NOTEBOOK.to_dict()

    @app.post("/api/notebook/cell")
    def nb_add_cell(cell: CellIn) -> dict[str, Any]:
        c = _NOTEBOOK.add_cell(cell.cell_type, cell.source)
        return c.to_dict()

    @app.patch("/api/notebook/cell/{cell_id}")
    def nb_update_cell(cell_id: str, body: CellUpdate) -> dict[str, Any]:
        c = _NOTEBOOK.update_cell(cell_id, body.source)
        if c is None:
            raise HTTPException(404, "cell not found")
        return c.to_dict()

    @app.delete("/api/notebook/cell/{cell_id}")
    def nb_delete_cell(cell_id: str) -> dict[str, Any]:
        ok = _NOTEBOOK.delete_cell(cell_id)
        return {"ok": ok}

    @app.post("/api/notebook/cell/{cell_id}/run")
    def nb_run_cell(cell_id: str) -> dict[str, Any]:
        try:
            r = _NOTEBOOK.run_cell(cell_id)
            return r.to_dict()
        except KeyError as e:
            raise HTTPException(404, str(e))

    @app.post("/api/notebook/run")
    def nb_run_code(body: CodeIn) -> dict[str, Any]:
        cell = _NOTEBOOK.add_cell(CellType.CODE, body.code)
        r = _NOTEBOOK.run_cell(cell.cell_id)
        return {"cell_id": cell.cell_id, "result": r.to_dict()}

    @app.post("/api/notebook/run-all")
    def nb_run_all() -> dict[str, Any]:
        results = _NOTEBOOK.run_all()
        return {"results": [r.to_dict() for r in results]}

    @app.post("/api/notebook/reset")
    def nb_reset() -> dict[str, Any]:
        _NOTEBOOK.reset()
        return {"ok": True}

    # ============================================================ llm
    @app.get("/api/llm/health")
    def llm_health() -> dict[str, Any]:
        return _LLM_ENGINE.health()

    @app.post("/api/llm/chat")
    def llm_chat(body: ChatIn) -> dict[str, Any]:
        msgs = [ChatMessage.from_dict(m) for m in body.messages]
        req = CompletionRequest(
            messages=msgs,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )
        resp = _LLM_ENGINE.complete(req)
        return {
            "text": resp.text,
            "usage": resp.usage,
            "elapsed_ms": resp.elapsed_ms,
            "request_id": resp.request_id,
        }

    @app.get("/api/llm/js-agent")
    def llm_js_agent() -> dict[str, Any]:
        return _JS_AGENT.health()

    @app.post("/api/llm/audit")
    def llm_audit(body: AuditIn) -> dict[str, Any]:
        report = _FULL_AGENT.audit(body.target, body.content, body.context)
        return {
            "target": report.target,
            "summary": report.summary,
            "issues": report.issues,
            "metrics": report.metrics,
            "recommendations": report.recommendations,
            "severity": report.severity,
            "passed": report.passed,
        }

    @app.post("/api/llm/iterate")
    def llm_iterate(body: IterateIn) -> dict[str, Any]:
        it = _FULL_AGENT.iterate(body.baseline_ms, body.baseline_payload)
        _EFF_TRACKER.record(it)
        return {
            "version": it.version,
            "baseline_ms": it.baseline_ms,
            "optimized_ms": it.optimized_ms,
            "savings_ratio": it.savings_ratio,
            "speedup": round(it.speedup, 4),
            "changes": it.changes,
        }

    @app.get("/api/llm/summary")
    def llm_summary() -> dict[str, Any]:
        return {**_FULL_AGENT.summary(), "efficiency": _EFF_TRACKER.summary()}

    # ============================================================ security
    @app.post("/api/security/xor/encode")
    def sec_xor_encode(body: XorIn) -> dict[str, Any]:
        codec = XorClockCodec()
        payload = codec.encode(body.plaintext.encode("utf-8"), body.dimension, body.clock_seed)
        return {
            "data_hex": payload.to_bytes().hex(),
            "fingerprint": payload.fingerprint,
            "dimension": payload.dimension,
            "clock_seed": payload.clock_seed,
        }

    @app.post("/api/security/xor/decode")
    def sec_xor_decode(body: XorDecodeIn) -> dict[str, Any]:
        from ai_llm_agent_crawler.security import XorClockPayload

        codec = XorClockCodec()
        try:
            p = XorClockPayload.from_bytes(bytes.fromhex(body.data_hex))
            plain = codec.decode(p, verify=body.verify)
            return {"plaintext": plain.decode("utf-8", errors="replace"), "ok": True}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    @app.get("/api/security/blockchain")
    def sec_chain_get() -> dict[str, Any]:
        return _get_chain().to_dict()

    @app.post("/api/security/blockchain/mine")
    def sec_chain_mine(body: MineIn) -> dict[str, Any]:
        chain = _get_chain()
        rec = chain.mine_wallet(
            dictionary_entry=body.dictionary_entry,
            ca_serial=body.ca_serial,
            dimension=body.dimension,
            clock_seed=body.clock_seed,
            ciphertext=bytes.fromhex(body.ciphertext_hex),
            difficulty=body.difficulty,
        )
        return rec.to_dict()

    @app.get("/api/security/blockchain/verify")
    def sec_chain_verify() -> dict[str, Any]:
        return {"valid": _get_chain().verify_chain(), "length": len(_get_chain().records)}

    # ============================================================ skills
    @app.get("/api/skills")
    def skills_list() -> dict[str, Any]:
        return _SKILLS_POOL.to_dict()

    @app.post("/api/skills/skill")
    def skills_add_skill(body: SkillIn) -> dict[str, Any]:
        s = Skill(
            name=body.name,
            description=body.description,
            code=body.code,
            tags=body.tags,
            author=body.author,
        )
        return _SKILLS_POOL.register_skill(s).to_dict()

    @app.post("/api/skills/dataset")
    def skills_add_dataset(body: DatasetIn) -> dict[str, Any]:
        d = DatasetEntry(
            name=body.name,
            format=body.format,
            rows=body.rows,
            size_bytes=body.size_bytes,
            tags=body.tags,
        )
        return _SKILLS_POOL.register_dataset(d).to_dict()

    @app.post("/api/skills/like")
    def skills_like(body: LikeIn) -> dict[str, Any]:
        likes = _SKILLS_POOL.like(body.ref_id, body.count)
        return {"ref_id": body.ref_id, "likes": likes}

    @app.get("/api/skills/settle")
    def skills_settle() -> dict[str, Any]:
        return _SKILLS_POOL.settle()

    @app.get("/api/skills/efficiency")
    def skills_efficiency() -> dict[str, Any]:
        return _EFF_TRACKER.summary()

    # ============================================================ tools
    @app.get("/api/tools/running")
    def tools_running_get() -> dict[str, Any]:
        return _RUNNER.to_dict()

    @app.post("/api/tools/running")
    def tools_running_add(body: RunIn) -> dict[str, Any]:
        from ai_llm_agent_crawler.business_tools import RunRecord

        r = _RUNNER.add(
            RunRecord(
                distance_km=body.distance_km,
                duration_s=body.duration_s,
                avg_heart_rate=body.avg_heart_rate,
                weight_kg=body.weight_kg,
                note=body.note,
            )
        )
        return r.to_dict()

    @app.get("/api/tools/budget")
    def tools_budget_get() -> dict[str, Any]:
        return _BUDGET.to_dict()

    @app.post("/api/tools/budget")
    def tools_budget_add(body: BudgetIn) -> dict[str, Any]:
        if body.kind == "income":
            e = _BUDGET.add_income(body.amount, body.category, body.note)
        else:
            e = _BUDGET.add_expense(body.amount, body.category, body.note)
        return e.to_dict()

    @app.post("/api/tools/bio-science")
    def tools_bio_generate(body: BioIn) -> dict[str, Any]:
        rows = _BIO.generate(body.n)
        return {"schema": _BIO.schema(), "rows": rows, "stats": _BIO.stats(rows)}

    # 静态资源
    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    return app


# 区块链容器存于 app state（每次启动新建）
_CHAIN: BlockchainEncodingContainer | None = None


def _get_chain() -> BlockchainEncodingContainer:
    global _CHAIN
    if _CHAIN is None:
        _CHAIN = BlockchainEncodingContainer(chain_id="trae-ide-chain")
    return _CHAIN


def main() -> None:
    import uvicorn

    host = os.environ.get("IDE_HOST", "0.0.0.0")
    port = int(os.environ.get("IDE_PORT", "8000"))
    embed = os.environ.get("IDE_EMBED", "false").lower() in ("1", "true", "yes")
    app = create_app(embed=embed)
    print(f"[ide] serving on http://{host}:{port} (embed={embed})")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
