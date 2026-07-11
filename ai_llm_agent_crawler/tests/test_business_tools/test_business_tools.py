"""business_tools 模块测试。"""

from __future__ import annotations

import pytest

from ai_llm_agent_crawler.business_tools import (
    BioScienceDataset,
    BudgetEntry,
    BudgetTool,
    RunRecord,
    RunningTracker,
)


class TestRunRecord:
    def test_pace_and_speed(self) -> None:
        r = RunRecord(distance_km=5.0, duration_s=1800.0)
        assert r.pace_sec_per_km == pytest.approx(360.0)
        assert r.speed_kmh == pytest.approx(10.0)

    def test_calories_with_hr(self) -> None:
        r = RunRecord(distance_km=5.0, duration_s=1800.0, avg_heart_rate=150, weight_kg=70)
        assert r.calories > 0

    def test_calories_without_hr(self) -> None:
        r = RunRecord(distance_km=10.0, duration_s=3600.0, weight_kg=70)
        assert r.calories == pytest.approx(10 * 70 * 1.03)

    def test_to_dict(self) -> None:
        r = RunRecord(distance_km=1.0, duration_s=60.0)
        d = r.to_dict()
        assert d["distance_km"] == 1.0
        assert "pace_sec_per_km" in d


class TestRunningTracker:
    def test_add_and_summary(self) -> None:
        t = RunningTracker()
        t.add_simple(5.0, 1800.0)
        t.add_simple(10.0, 3600.0)
        s = t.summary()
        assert s["count"] == 2
        assert s["total_km"] == pytest.approx(15.0)

    def test_invalid_distance(self) -> None:
        with pytest.raises(ValueError):
            RunningTracker().add_simple(0, 100)

    def test_invalid_duration(self) -> None:
        with pytest.raises(ValueError):
            RunningTracker().add_simple(5, 0)

    def test_empty_summary(self) -> None:
        assert RunningTracker().summary()["count"] == 0


class TestBudgetTool:
    def test_expense_income_balance(self) -> None:
        b = BudgetTool()
        b.add_income(1000, "salary")
        b.add_expense(200, "food")
        b.add_expense(100, "transport")
        assert b.balance() == pytest.approx(700.0)

    def test_invalid_amount(self) -> None:
        with pytest.raises(ValueError):
            BudgetTool().add_expense(-5, "x")

    def test_by_category(self) -> None:
        b = BudgetTool()
        b.add_expense(50, "food")
        b.add_income(50, "food")
        cat = b.by_category()["food"]
        assert cat["net"] == 0.0

    def test_summary(self) -> None:
        b = BudgetTool()
        b.add_expense(30, "food")
        s = b.summary()
        assert s["total_expense"] == 30
        assert s["balance"] == -30

    def test_budget_entry_invalid_kind(self) -> None:
        with pytest.raises(ValueError):
            BudgetEntry(amount=1, category="x", kind="bad")


class TestBioScienceDataset:
    def test_generate(self) -> None:
        bio = BioScienceDataset(seed=1)
        rows = bio.generate(5)
        assert len(rows) == 5
        assert all("subject_id" in r for r in rows)
        assert all("vo2_max" in r for r in rows)

    def test_generate_zero(self) -> None:
        assert BioScienceDataset().generate(0) == []

    def test_schema(self) -> None:
        s = BioScienceDataset().schema()
        assert s["name"] == "bio_science_sample"
        assert any(f["name"] == "vo2_max" for f in s["fields"])

    def test_stats(self) -> None:
        bio = BioScienceDataset(seed=2)
        rows = bio.generate(20)
        stats = bio.stats(rows)
        assert stats["count"] == 20
        assert "age" in stats
        assert "min" in stats["age"]

    def test_deterministic(self) -> None:
        a = BioScienceDataset(seed=42).generate(3)
        b = BioScienceDataset(seed=42).generate(3)
        assert a == b

    def test_empty_stats(self) -> None:
        assert BioScienceDataset().stats([])["count"] == 0
