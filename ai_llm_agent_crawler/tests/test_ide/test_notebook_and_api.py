"""IDE notebook 与 FastAPI 端到端测试。"""

from __future__ import annotations

import pytest

from ai_llm_agent_crawler.ide.notebook import CellType, Notebook


pytestmark = pytest.mark.unit


class TestNotebook:
    def test_add_and_run_code(self) -> None:
        nb = Notebook()
        c = nb.add_cell(CellType.CODE, "1 + 1")
        r = nb.run_cell(c.cell_id)
        assert r.ok is True
        assert r.value == 2

    def test_run_with_stdout(self) -> None:
        nb = Notebook()
        c = nb.add_cell(CellType.CODE, "print('hello')\n40 + 2")
        r = nb.run_cell(c.cell_id)
        assert r.ok is True
        assert "hello" in r.stdout
        assert r.value == 42

    def test_shared_namespace(self) -> None:
        nb = Notebook()
        nb.add_cell(CellType.CODE, "x = 10")
        nb.run_all()
        c2 = nb.add_cell(CellType.CODE, "x * 2")
        r = nb.run_cell(c2.cell_id)
        assert r.ok is True
        assert r.value == 20

    def test_markdown_cell(self) -> None:
        nb = Notebook()
        c = nb.add_cell(CellType.MARKDOWN, "# title")
        r = nb.run_cell(c.cell_id)
        assert r.ok is True
        assert r.value == "# title"

    def test_error_cell(self) -> None:
        nb = Notebook()
        c = nb.add_cell(CellType.CODE, "1 / 0")
        r = nb.run_cell(c.cell_id)
        assert r.ok is False
        assert "ZeroDivisionError" in r.error

    def test_update_and_delete(self) -> None:
        nb = Notebook()
        c = nb.add_cell(CellType.CODE, "x=1")
        assert nb.update_cell(c.cell_id, "y=2") is not None
        assert nb.get_cell(c.cell_id).source == "y=2"
        assert nb.delete_cell(c.cell_id) is True
        assert nb.get_cell(c.cell_id) is None

    def test_run_unknown_cell(self) -> None:
        nb = Notebook()
        with pytest.raises(KeyError):
            nb.run_cell("nope")

    def test_reset(self) -> None:
        nb = Notebook()
        nb.add_cell(CellType.CODE, "z=5")
        nb.run_all()
        nb.reset()
        assert len(nb.cells) == 0
        c = nb.add_cell(CellType.CODE, "z")
        r = nb.run_cell(c.cell_id)
        assert r.ok is False  # z 已被清空

    def test_bootstrap_imports(self) -> None:
        nb = Notebook()
        c = nb.add_cell(CellType.CODE, "LlamaCppAdapter is not None")
        r = nb.run_cell(c.cell_id)
        assert r.ok is True


class TestFastAPIApp:
    """FastAPI 应用测试（需要 fastapi + httpx）。

    使用 TestClient 同步调用，覆盖关键端点。
    """

    @pytest.fixture
    def client(self):
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient

        from ai_llm_agent_crawler.ide.server import create_app

        app = create_app(embed=False)
        with TestClient(app) as c:
            yield c

    def test_health(self, client) -> None:
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    def test_index_html(self, client) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert "Jupyter IDE" in r.text

    def test_notebook_run_code(self, client) -> None:
        r = client.post("/api/notebook/run", json={"code": "2 + 3"})
        assert r.status_code == 200
        data = r.json()
        assert data["result"]["ok"] is True
        assert data["result"]["value"] == 5

    def test_llm_chat(self, client) -> None:
        r = client.post(
            "/api/llm/chat",
            json={"messages": [{"role": "user", "content": "hi"}], "max_tokens": 16},
        )
        assert r.status_code == 200
        assert "text" in r.json()

    def test_llm_audit(self, client) -> None:
        r = client.post(
            "/api/llm/audit",
            json={"target": "t", "content": "some content", "context": {}},
        )
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data

    def test_xor_roundtrip(self, client) -> None:
        enc = client.post(
            "/api/security/xor/encode",
            json={"plaintext": "hello", "dimension": "d", "clock_seed": 1},
        )
        assert enc.status_code == 200
        data_hex = enc.json()["data_hex"]
        dec = client.post(
            "/api/security/xor/decode",
            json={"data_hex": data_hex, "verify": True},
        )
        assert dec.status_code == 200
        assert dec.json()["plaintext"] == "hello"

    def test_blockchain_mine_and_verify(self, client) -> None:
        mine = client.post(
            "/api/security/blockchain/mine",
            json={
                "dictionary_entry": "e",
                "ca_serial": "CA-1",
                "dimension": "d",
                "clock_seed": 1,
                "ciphertext_hex": "aabb",
                "difficulty": 1,
            },
        )
        assert mine.status_code == 200
        verify = client.get("/api/security/blockchain/verify")
        assert verify.status_code == 200
        assert verify.json()["valid"] is True

    def test_skills_flow(self, client) -> None:
        add = client.post(
            "/api/skills/skill",
            json={"name": "s1", "tags": ["t"]},
        )
        assert add.status_code == 200
        ref_id = add.json()["ref_id"]
        like = client.post("/api/skills/like", json={"ref_id": ref_id, "count": 2})
        assert like.json()["likes"] == 2
        settle = client.get("/api/skills/settle")
        assert settle.status_code == 200
        assert settle.json()["total_likes"] >= 2

    def test_tools_running(self, client) -> None:
        r = client.post(
            "/api/tools/running",
            json={"distance_km": 5, "duration_s": 1800, "avg_heart_rate": 150},
        )
        assert r.status_code == 200
        assert r.json()["distance_km"] == 5

    def test_tools_budget(self, client) -> None:
        r = client.post(
            "/api/tools/budget",
            json={"amount": 50, "category": "food", "kind": "expense"},
        )
        assert r.status_code == 200
        g = client.get("/api/tools/budget")
        assert g.json()["summary"]["total_expense"] == 50

    def test_tools_bio(self, client) -> None:
        r = client.post("/api/tools/bio-science", json={"n": 5})
        assert r.status_code == 200
        data = r.json()
        assert len(data["rows"]) == 5
        assert data["stats"]["count"] == 5

    def test_embed_mode_hides_docs(self) -> None:
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient

        from ai_llm_agent_crawler.ide.server import create_app

        app = create_app(embed=True)
        with TestClient(app) as c:
            assert c.get("/docs").status_code == 404
            assert c.get("/openapi.json").status_code == 404
