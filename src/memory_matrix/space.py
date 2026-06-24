"""
Stego Memory Space & Memory Pool - the dimension space for data science.

The 'probe generation dimension space pool' and 'data science dimension
space dataset' concepts: a pool is a named collection of memory spaces,
each containing multiple datasets organized by dimensional ordering.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .matrix import SingularityMatrix, MatrixCell
from ..utils import generate_id, LogicLogger


class OrderType(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"
    NATURAL = "natural"
    CUSTOM = "custom"


@dataclass
class DataSet:
    dataset_id: str
    name: str
    dimension: str
    cells: List[MatrixCell] = field(default_factory=list)
    order: OrderType = OrderType.NATURAL
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.cells)

    def sort(self, order: OrderType = OrderType.ASCENDING,
             key: Optional[Callable] = None) -> None:
        self.order = order
        if order == OrderType.ASCENDING:
            self.cells.sort(key=lambda c: c.timestamp)
        elif order == OrderType.DESCENDING:
            self.cells.sort(key=lambda c: c.timestamp, reverse=True)
        elif order == OrderType.CUSTOM and key:
            self.cells.sort(key=key)


class StegoMemorySpace:
    """
    A named memory space within the singularity matrix, representing
    a 'dimension' in the conceptual model. Each space can contain
    multiple datasets organized by data order rules.
    """

    def __init__(self, name: str, matrix: SingularityMatrix,
                 logger: Optional[LogicLogger] = None):
        self.space_id = generate_id("space")
        self.name = name
        self.matrix = matrix
        self.logger = logger or LogicLogger(f"space_{name}")
        self._datasets: Dict[str, DataSet] = {}
        self._lock = threading.RLock()

    @property
    def dataset_count(self) -> int:
        return len(self._datasets)

    def create_dataset(self, name: str, dimension: str = "default",
                       anchor_filter: Optional[str] = None,
                       tag_filter: Optional[str] = None,
                       order: OrderType = OrderType.NATURAL) -> DataSet:
        with self._lock:
            cells = self.matrix.query(anchor=anchor_filter, tag=tag_filter)
            ds = DataSet(
                dataset_id=generate_id("ds"),
                name=name,
                dimension=dimension,
                cells=cells,
                order=order,
            )
            if order != OrderType.NATURAL:
                ds.sort(order)
            self._datasets[ds.dataset_id] = ds
            self.logger.log("memory_space", "dataset_created",
                            name=name, dimension=dimension, size=ds.size)
            return ds

    def get_dataset(self, dataset_id: str) -> Optional[DataSet]:
        return self._datasets.get(dataset_id)

    def find_dataset(self, name: str) -> Optional[DataSet]:
        for ds in self._datasets.values():
            if ds.name == name:
                return ds
        return None

    def list_datasets(self) -> List[dict]:
        return [
            {
                "dataset_id": ds.dataset_id,
                "name": ds.name,
                "dimension": ds.dimension,
                "size": ds.size,
                "order": ds.order.value,
                "created_at": ds.created_at,
            }
            for ds in self._datasets.values()
        ]

    def refresh_dataset(self, dataset_id: str) -> Optional[DataSet]:
        with self._lock:
            ds = self._datasets.get(dataset_id)
            if not ds:
                return None
            cells = self.matrix.query(tag=ds.dimension)
            ds.cells = cells
            if ds.order != OrderType.NATURAL:
                ds.sort(ds.order)
            self.logger.log("memory_space", "dataset_refreshed",
                            dataset_id=dataset_id, size=ds.size)
            return ds

    def delete_dataset(self, dataset_id: str) -> bool:
        with self._lock:
            if dataset_id in self._datasets:
                del self._datasets[dataset_id]
                self.logger.log("memory_space", "dataset_deleted",
                                dataset_id=dataset_id)
                return True
            return False


class MemoryPool:
    """
    The 'dimension space pool' - a collection of stego memory spaces,
    each representing a different dimension. Probes generate dimensions
    by writing into the pool; data science agents read from it.
    """

    def __init__(self, name: str = "dimension_pool",
                 logger: Optional[LogicLogger] = None):
        self.pool_id = generate_id("pool")
        self.name = name
        self.logger = logger or LogicLogger(f"pool_{name}")
        self._spaces: Dict[str, StegoMemorySpace] = {}
        self._matrix = SingularityMatrix(f"{name}_matrix", self.logger)
        self._lock = threading.RLock()

    @property
    def matrix(self) -> SingularityMatrix:
        return self._matrix

    @property
    def space_count(self) -> int:
        return len(self._spaces)

    def create_space(self, name: str) -> StegoMemorySpace:
        with self._lock:
            if name in self._spaces:
                return self._spaces[name]
            space = StegoMemorySpace(name, self._matrix, self.logger)
            self._spaces[name] = space
            self.logger.log("memory_pool", "space_created", name=name)
            return space

    def get_space(self, name: str) -> Optional[StegoMemorySpace]:
        return self._spaces.get(name)

    def list_spaces(self) -> List[dict]:
        return [
            {
                "space_id": s.space_id,
                "name": s.name,
                "datasets": s.dataset_count,
            }
            for s in self._spaces.values()
        ]

    def stats(self) -> Dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "name": self.name,
            "spaces": len(self._spaces),
            "matrix_stats": self._matrix.stats(),
        }

    def __repr__(self) -> str:
        return (f"<MemoryPool name={self.name} spaces={len(self._spaces)} "
                f"matrix_cells={self._matrix.size}>")
