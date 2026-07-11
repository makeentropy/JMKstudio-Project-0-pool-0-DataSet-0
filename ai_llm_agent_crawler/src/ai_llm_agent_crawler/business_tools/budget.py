"""预算工具。"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class BudgetEntry:
    """一条预算流水。"""

    amount: float
    category: str
    kind: str = "expense"  # expense | income
    timestamp: float = field(default_factory=time.time)
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("expense", "income"):
            raise ValueError(f"kind 必须为 expense/income，得到 {self.kind}")

    @property
    def signed_amount(self) -> float:
        return -abs(self.amount) if self.kind == "expense" else abs(self.amount)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["signed_amount"] = self.signed_amount
        return d


class BudgetTool:
    """预算工具：收支登记、分类汇总、结余计算。"""

    def __init__(self, currency: str = "CNY") -> None:
        self.currency: str = currency
        self._entries: list[BudgetEntry] = []

    def add_expense(self, amount: float, category: str, note: str = "") -> BudgetEntry:
        if amount <= 0:
            raise ValueError("amount 必须为正")
        e = BudgetEntry(amount=amount, category=category, kind="expense", note=note)
        self._entries.append(e)
        return e

    def add_income(self, amount: float, category: str, note: str = "") -> BudgetEntry:
        if amount <= 0:
            raise ValueError("amount 必须为正")
        e = BudgetEntry(amount=amount, category=category, kind="income", note=note)
        self._entries.append(e)
        return e

    def balance(self) -> float:
        return sum(e.signed_amount for e in self._entries)

    def by_category(self) -> dict[str, dict[str, float]]:
        agg: dict[str, dict[str, float]] = {}
        for e in self._entries:
            cat = agg.setdefault(e.category, {"income": 0.0, "expense": 0.0, "net": 0.0})
            cat[e.kind] += e.amount
            cat["net"] = cat["income"] - cat["expense"]
        return agg

    def summary(self) -> dict[str, Any]:
        income = sum(e.amount for e in self._entries if e.kind == "income")
        expense = sum(e.amount for e in self._entries if e.kind == "expense")
        return {
            "currency": self.currency,
            "count": len(self._entries),
            "total_income": round(income, 2),
            "total_expense": round(expense, 2),
            "balance": round(income - expense, 2),
            "by_category": {
                k: {kk: round(vv, 2) for kk, vv in v.items()}
                for k, v in self.by_category().items()
            },
        }

    def list_entries(self) -> list[BudgetEntry]:
        return list(self._entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self._entries],
            "summary": self.summary(),
        }
