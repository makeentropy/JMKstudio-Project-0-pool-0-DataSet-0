"""自然身体生物科学示例数据集生成器。"""

from __future__ import annotations

import random
from typing import Any


class BioScienceDataset:
    """生成自然身体生物科学主题的示例数据集。

    用于演示数据科学与 skills pool 的协同（跑步生理指标、心率、摄氧量等）。
    """

    SCHEMA: dict[str, str] = {
        "subject_id": "str",
        "age": "int",
        "sex": "str",
        "height_cm": "float",
        "weight_kg": "float",
        "resting_hr": "int",
        "max_hr": "int",
        "vo2_max": "float",
        "body_fat_pct": "float",
        "activity_level": "str",
    }

    ACTIVITY_LEVELS = ["sedentary", "light", "moderate", "active", "very_active"]

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------ generate
    def generate(self, n: int = 10) -> list[dict[str, Any]]:
        if n <= 0:
            return []
        rows: list[dict[str, Any]] = []
        for i in range(n):
            age = self._rng.randint(18, 75)
            sex = self._rng.choice(["M", "F"])
            height = round(self._rng.uniform(150, 200), 1)
            weight = round(self._rng.uniform(45, 110), 1)
            resting_hr = self._rng.randint(48, 85)
            max_hr = 220 - age + self._rng.randint(-5, 5)
            vo2_max = round(self._rng.uniform(25.0, 65.0), 1)
            body_fat = round(self._rng.uniform(8.0, 35.0), 1)
            activity = self._rng.choice(self.ACTIVITY_LEVELS)
            rows.append(
                {
                    "subject_id": f"S{i + 1:04d}",
                    "age": age,
                    "sex": sex,
                    "height_cm": height,
                    "weight_kg": weight,
                    "resting_hr": resting_hr,
                    "max_hr": max_hr,
                    "vo2_max": vo2_max,
                    "body_fat_pct": body_fat,
                    "activity_level": activity,
                }
            )
        return rows

    # ------------------------------------------------------------------ schema
    def schema(self) -> dict[str, Any]:
        return {
            "name": "bio_science_sample",
            "format": "json",
            "fields": [
                {"name": k, "type": v, "description": _FIELD_DESC[k]}
                for k, v in self.SCHEMA.items()
            ],
        }

    # ------------------------------------------------------------------ stats
    def stats(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"count": 0}
        numeric_keys = [
            "age",
            "height_cm",
            "weight_kg",
            "resting_hr",
            "max_hr",
            "vo2_max",
            "body_fat_pct",
        ]
        stats: dict[str, Any] = {"count": len(rows)}
        for key in numeric_keys:
            values = [r[key] for r in rows]
            stats[key] = {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(sum(values) / len(values), 2),
            }
        return stats


_FIELD_DESC: dict[str, str] = {
    "subject_id": "受试者编号",
    "age": "年龄",
    "sex": "性别",
    "height_cm": "身高(cm)",
    "weight_kg": "体重(kg)",
    "resting_hr": "静息心率(bpm)",
    "max_hr": "最大心率(bpm)",
    "vo2_max": "最大摄氧量(ml/kg/min)",
    "body_fat_pct": "体脂率(%)",
    "activity_level": "活动水平",
}
