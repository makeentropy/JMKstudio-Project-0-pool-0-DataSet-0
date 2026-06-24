"""
Data Order - scientific data ordering / 数据秩序.

Implements the '排序,数据秩序' concept: a systematic approach to
sorting and ordering data within the steganographic dimension space.
Includes multiple sorting algorithms, custom order rules, and
order stability metrics.
"""

import time
import hashlib
from enum import Enum
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field


class SortAlgorithm(Enum):
    QUICK = "quick"
    MERGE = "merge"
    TIM = "tim"
    BUBBLE = "bubble"
    INSERTION = "insertion"
    HEAP = "heap"
    RADIX = "radix"


class OrderDirection(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


@dataclass
class OrderRule:
    rule_id: str
    name: str
    field: str
    direction: OrderDirection
    priority: int = 0
    transform: Optional[Callable] = None

    def apply_key(self, item: Any) -> Any:
        if isinstance(item, dict):
            val = item.get(self.field)
        else:
            val = getattr(item, self.field, None)
        if self.transform:
            val = self.transform(val)
        if self.direction == OrderDirection.DESCENDING:
            return self._negate(val)
        return val

    def _negate(self, val: Any) -> Any:
        if isinstance(val, (int, float)):
            return -val
        if isinstance(val, str):
            return "".join(chr(255 - ord(c)) for c in val)
        return val


@dataclass
class SortResult:
    sorted_items: List[Any]
    algorithm: SortAlgorithm
    duration: float
    comparisons: int
    swaps: int
    stable: bool = True


class SortEngine:
    """
    Sort engine with multiple algorithms - the core of '数据秩序'.

    Supports:
    - Multiple sort algorithms
    - Multi-key ordering via OrderRule chains
    - Performance metrics (comparisons, swaps, time)
    - Stability verification
    """

    def __init__(self):
        self._comparisons = 0
        self._swaps = 0

    def sort(self, items: List[Any],
             rules: Optional[List[OrderRule]] = None,
             algorithm: SortAlgorithm = SortAlgorithm.TIM) -> SortResult:
        self._comparisons = 0
        self._swaps = 0
        start = time.time()

        items_copy = list(items)

        key_func = self._build_key_func(rules) if rules else None

        if algorithm == SortAlgorithm.QUICK:
            self._quicksort(items_copy, 0, len(items_copy) - 1, key_func)
        elif algorithm == SortAlgorithm.MERGE:
            items_copy = self._mergesort(items_copy, key_func)
        elif algorithm == SortAlgorithm.HEAP:
            self._heapsort(items_copy, key_func)
        elif algorithm == SortAlgorithm.BUBBLE:
            self._bubblesort(items_copy, key_func)
        elif algorithm == SortAlgorithm.INSERTION:
            self._insertionsort(items_copy, key_func)
        elif algorithm == SortAlgorithm.RADIX:
            items_copy = self._radixsort(items_copy, key_func)
        else:
            items_copy.sort(key=key_func)

        duration = time.time() - start
        stable = self._check_stability(items, items_copy, key_func)

        return SortResult(
            sorted_items=items_copy,
            algorithm=algorithm,
            duration=duration,
            comparisons=self._comparisons,
            swaps=self._swaps,
            stable=stable,
        )

    def _build_key_func(self, rules: List[OrderRule]) -> Callable:
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)

        def key_func(item):
            return tuple(rule.apply_key(item) for rule in sorted_rules)

        return key_func

    def _compare(self, a, b, key_func=None) -> int:
        self._comparisons += 1
        ka = key_func(a) if key_func else a
        kb = key_func(b) if key_func else b
        if ka < kb:
            return -1
        elif ka > kb:
            return 1
        return 0

    def _swap(self, items: List, i: int, j: int) -> None:
        self._swaps += 1
        items[i], items[j] = items[j], items[i]

    def _quicksort(self, items, low, high, key_func):
        if low < high:
            pi = self._partition(items, low, high, key_func)
            self._quicksort(items, low, pi - 1, key_func)
            self._quicksort(items, pi + 1, high, key_func)

    def _partition(self, items, low, high, key_func):
        pivot = items[high]
        i = low - 1
        for j in range(low, high):
            if self._compare(items[j], pivot, key_func) <= 0:
                i += 1
                self._swap(items, i, j)
        self._swap(items, i + 1, high)
        return i + 1

    def _mergesort(self, items, key_func):
        if len(items) <= 1:
            return items
        mid = len(items) // 2
        left = self._mergesort(items[:mid], key_func)
        right = self._mergesort(items[mid:], key_func)
        return self._merge(left, right, key_func)

    def _merge(self, left, right, key_func):
        result = []
        i = j = 0
        while i < len(left) and j < len(right):
            if self._compare(left[i], right[j], key_func) <= 0:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        return result

    def _heapsort(self, items, key_func):
        n = len(items)
        for i in range(n // 2 - 1, -1, -1):
            self._heapify(items, n, i, key_func)
        for i in range(n - 1, 0, -1):
            self._swap(items, 0, i)
            self._heapify(items, i, 0, key_func)

    def _heapify(self, items, n, i, key_func):
        largest = i
        left = 2 * i + 1
        right = 2 * i + 2
        if left < n and self._compare(items[left], items[largest], key_func) > 0:
            largest = left
        if right < n and self._compare(items[right], items[largest], key_func) > 0:
            largest = right
        if largest != i:
            self._swap(items, i, largest)
            self._heapify(items, n, largest, key_func)

    def _bubblesort(self, items, key_func):
        n = len(items)
        for i in range(n):
            swapped = False
            for j in range(0, n - i - 1):
                if self._compare(items[j], items[j + 1], key_func) > 0:
                    self._swap(items, j, j + 1)
                    swapped = True
            if not swapped:
                break

    def _insertionsort(self, items, key_func):
        for i in range(1, len(items)):
            key_item = items[i]
            j = i - 1
            while j >= 0 and self._compare(items[j], key_item, key_func) > 0:
                items[j + 1] = items[j]
                self._swaps += 1
                j -= 1
            items[j + 1] = key_item

    def _radixsort(self, items, key_func):
        if not items:
            return items
        if key_func:
            keys = [key_func(it) for it in items]
        else:
            keys = items
        max_val = max((k for k in keys if isinstance(k, (int, float))), default=0)
        if max_val == 0:
            return items
        exp = 1
        arr = list(items)
        while max_val // exp > 0:
            self._counting_sort(arr, exp, key_func)
            exp *= 10
        return arr

    def _counting_sort(self, items, exp, key_func):
        n = len(items)
        output = [0] * n
        count = [0] * 10
        for i in range(n):
            k = key_func(items[i]) if key_func else items[i]
            if isinstance(k, (int, float)):
                index = int(k / exp) % 10
                count[index] += 1
        for i in range(1, 10):
            count[i] += count[i - 1]
        for i in range(n - 1, -1, -1):
            k = key_func(items[i]) if key_func else items[i]
            if isinstance(k, (int, float)):
                index = int(k / exp) % 10
                output[count[index] - 1] = items[i]
                count[index] -= 1
        for i in range(n):
            items[i] = output[i]

    def _check_stability(self, original, sorted_list, key_func) -> bool:
        if not key_func:
            return True
        groups_orig: Dict[Any, List] = {}
        for item in original:
            k = key_func(item)
            if k not in groups_orig:
                groups_orig[k] = []
            groups_orig[k].append(id(item))
        groups_sorted: Dict[Any, List] = {}
        for item in sorted_list:
            k = key_func(item)
            if k not in groups_sorted:
                groups_sorted[k] = []
            groups_sorted[k].append(id(item))
        for k in groups_orig:
            if k in groups_sorted:
                if groups_orig[k] != groups_sorted[k]:
                    return False
        return True


class DataOrder:
    """
    Data Order system - the '数据秩序' concept.

    Manages ordering rules, sort operations, and maintains data
    in a well-ordered state within the dimension space.
    """

    def __init__(self):
        self._rules: Dict[str, OrderRule] = {}
        self._sort_engine = SortEngine()
        self._order_history: List[SortResult] = []

    def create_rule(self, name: str, field: str,
                    direction: OrderDirection = OrderDirection.ASCENDING,
                    priority: int = 0,
                    transform: Optional[Callable] = None) -> OrderRule:
        rule = OrderRule(
            rule_id=generate_id_rule(),
            name=name,
            field=field,
            direction=direction,
            priority=priority,
            transform=transform,
        )
        self._rules[rule.rule_id] = rule
        return rule

    def apply_order(self, items: List[Any],
                    rule_names: Optional[List[str]] = None,
                    algorithm: SortAlgorithm = SortAlgorithm.TIM) -> SortResult:
        rules = []
        if rule_names:
            for name in rule_names:
                for rule in self._rules.values():
                    if rule.name == name:
                        rules.append(rule)
                        break
        else:
            rules = list(self._rules.values())

        result = self._sort_engine.sort(items, rules=rules or None, algorithm=algorithm)
        self._order_history.append(result)
        return result

    @property
    def rules(self) -> List[OrderRule]:
        return list(self._rules.values())

    @property
    def sort_count(self) -> int:
        return len(self._order_history)

    def stats(self) -> Dict[str, Any]:
        total_time = sum(r.duration for r in self._order_history)
        return {
            "rules_count": len(self._rules),
            "sort_operations": len(self._order_history),
            "total_sort_time": total_time,
            "avg_sort_time": total_time / len(self._order_history) if self._order_history else 0,
        }


def generate_id_rule() -> str:
    from ..utils import generate_id
    return generate_id("rule")
