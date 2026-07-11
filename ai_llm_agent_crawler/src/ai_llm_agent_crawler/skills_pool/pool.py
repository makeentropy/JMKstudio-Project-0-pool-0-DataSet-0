"""Skills POOL —— 开放性能效率池。"""

from __future__ import annotations

import threading
from typing import Any, Iterable

from ai_llm_agent_crawler.skills_pool.models import (
    DatasetEntry,
    PoolEntry,
    Skill,
)


class SkillsPool:
    """开放性能效率 POOL。

    线程安全地登记 / 检索 / 点赞（集赞） / 清算 skills 与 datasets。
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._skills: dict[str, Skill] = {}
        self._datasets: dict[str, DatasetEntry] = {}
        self._entries: list[PoolEntry] = []

    # ------------------------------------------------------------------ register
    def register_skill(self, skill: Skill) -> PoolEntry:
        with self._lock:
            self._skills[skill.skill_id] = skill
            entry = PoolEntry(
                kind="skill",
                ref_id=skill.skill_id,
                payload=skill.to_dict(),
                likes=skill.likes,
            )
            self._entries.append(entry)
            return entry

    def register_dataset(self, dataset: DatasetEntry) -> PoolEntry:
        with self._lock:
            self._datasets[dataset.entry_id] = dataset
            entry = PoolEntry(
                kind="dataset",
                ref_id=dataset.entry_id,
                payload=dataset.to_dict(),
            )
            self._entries.append(entry)
            return entry

    # ------------------------------------------------------------------ like (集赞)
    def like(self, ref_id: str, count: int = 1) -> int:
        if count <= 0:
            raise ValueError("count 必须为正")
        with self._lock:
            if ref_id in self._skills:
                self._skills[ref_id].likes += count
                # 同步更新 PoolEntry.likes，确保 settle() 汇总正确
                for e in self._entries:
                    if e.ref_id == ref_id:
                        e.likes = self._skills[ref_id].likes
                        break
                return self._skills[ref_id].likes
            if ref_id in self._datasets:
                # dataset 用 PoolEntry.likes 承载
                for e in self._entries:
                    if e.ref_id == ref_id:
                        e.likes += count
                        return e.likes
            raise KeyError(f"未找到 ref_id: {ref_id}")

    # ------------------------------------------------------------------ query
    def get_skill(self, skill_id: str) -> Skill | None:
        with self._lock:
            return self._skills.get(skill_id)

    def get_dataset(self, entry_id: str) -> DatasetEntry | None:
        with self._lock:
            return self._datasets.get(entry_id)

    def list_entries(self, kind: str | None = None) -> list[PoolEntry]:
        with self._lock:
            if kind is None:
                return list(self._entries)
            return [e for e in self._entries if e.kind == kind]

    def search(self, keyword: str) -> list[PoolEntry]:
        kw = keyword.lower()
        with self._lock:
            results: list[PoolEntry] = []
            for e in self._entries:
                name = str(e.payload.get("name", "")).lower()
                tags = " ".join(str(t) for t in e.payload.get("tags", [])).lower()
                if kw in name or kw in tags:
                    results.append(e)
            return results

    # ------------------------------------------------------------------ settle (清算)
    def settle(self) -> dict[str, Any]:
        """清算 POOL：汇总条目数、总赞数、TOP 条目。"""
        with self._lock:
            total = len(self._entries)
            total_likes = sum(e.likes for e in self._entries)
            top = sorted(self._entries, key=lambda e: e.likes, reverse=True)[:5]
            return {
                "total_entries": total,
                "total_skills": len(self._skills),
                "total_datasets": len(self._datasets),
                "total_likes": total_likes,
                "top": [e.to_dict() for e in top],
            }

    # ------------------------------------------------------------------ export
    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "skills": [s.to_dict() for s in self._skills.values()],
                "datasets": [d.to_dict() for d in self._datasets.values()],
                "entries": [e.to_dict() for e in self._entries],
            }

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
