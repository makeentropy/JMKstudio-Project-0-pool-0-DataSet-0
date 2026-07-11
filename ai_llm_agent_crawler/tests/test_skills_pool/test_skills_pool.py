"""skills_pool 模块测试。"""

from __future__ import annotations

import pytest

from ai_llm_agent_crawler.llm_engine import EfficiencyIteration
from ai_llm_agent_crawler.skills_pool import (
    DatasetEntry,
    EfficiencyTracker,
    PerformanceMetric,
    Skill,
    SkillsPool,
)


@pytest.fixture
def pool() -> SkillsPool:
    return SkillsPool()


@pytest.fixture
def tracker() -> EfficiencyTracker:
    return EfficiencyTracker()


class TestSkill:
    def test_to_dict_basic(self) -> None:
        s = Skill(name="runner", description="d", tags=["run"])
        d = s.to_dict()
        assert d["name"] == "runner"
        assert d["likes"] == 0
        assert "metrics" not in d

    def test_to_dict_with_metrics(self) -> None:
        s = Skill(
            name="x",
            metrics=PerformanceMetric(elapsed_ms=12.3, tokens=10),
        )
        d = s.to_dict()
        assert d["metrics"]["elapsed_ms"] == 12.3


class TestSkillsPool:
    def test_register_and_get(self, pool: SkillsPool) -> None:
        s = Skill(name="s1")
        pool.register_skill(s)
        assert pool.get_skill(s.skill_id) is not None

    def test_register_dataset(self, pool: SkillsPool) -> None:
        d = DatasetEntry(name="ds1", rows=100)
        pool.register_dataset(d)
        assert pool.get_dataset(d.entry_id) is not None
        assert len(pool.list_entries(kind="dataset")) == 1

    def test_like_skill(self, pool: SkillsPool) -> None:
        s = Skill(name="s")
        pool.register_skill(s)
        likes = pool.like(s.skill_id, 3)
        assert likes == 3
        assert pool.get_skill(s.skill_id).likes == 3

    def test_like_unknown(self, pool: SkillsPool) -> None:
        with pytest.raises(KeyError):
            pool.like("nope")

    def test_like_invalid_count(self, pool: SkillsPool) -> None:
        with pytest.raises(ValueError):
            pool.like("x", 0)

    def test_search(self, pool: SkillsPool) -> None:
        pool.register_skill(Skill(name="running-tracker", tags=["run"]))
        pool.register_skill(Skill(name="budget", tags=["money"]))
        res = pool.search("run")
        assert len(res) == 1
        assert res[0].payload["name"] == "running-tracker"

    def test_settle(self, pool: SkillsPool) -> None:
        s = Skill(name="s", likes=5)
        pool.register_skill(s)
        pool.register_dataset(DatasetEntry(name="d"))
        settle = pool.settle()
        assert settle["total_entries"] == 2
        assert settle["total_likes"] == 5
        assert settle["top"][0]["ref_id"] == s.skill_id

    def test_len(self, pool: SkillsPool) -> None:
        pool.register_skill(Skill(name="s"))
        assert len(pool) == 1


class TestEfficiencyTracker:
    def test_record_and_list(self, tracker: EfficiencyTracker) -> None:
        it = EfficiencyIteration(
            version="v1", baseline_ms=100.0, optimized_ms=80.0, savings_ratio=0.2
        )
        tracker.record(it)
        assert len(tracker.list_iterations()) == 1

    def test_record_raw(self, tracker: EfficiencyTracker) -> None:
        tracker.record_raw("v1", 100.0, 75.0)
        assert tracker.best_speedup() == pytest.approx(100.0 / 75.0)
        assert tracker.total_savings_ms() == pytest.approx(25.0)

    def test_avg_savings_ratio(self, tracker: EfficiencyTracker) -> None:
        tracker.record_raw("v1", 100.0, 80.0)
        tracker.record_raw("v2", 100.0, 60.0)
        assert tracker.avg_savings_ratio() == pytest.approx(0.3, abs=1e-6)

    def test_empty_summary(self, tracker: EfficiencyTracker) -> None:
        s = tracker.summary()
        assert s["count"] == 0
        assert s["best_speedup"] == 0.0
