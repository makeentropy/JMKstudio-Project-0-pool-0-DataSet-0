"""
Singularity Matrix - the core memory space for steganographic data.

Conceptually a multi-dimensional "singularity" matrix:
- Each cell stores decoded steganographic data
- Dimensions: anchor, tag, time, source node, priority
- Supports query by any combination of dimensions
- Each write creates a new version (immutable log-style)
- Event hooks for change notification (used by agents)
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..utils import generate_id, LogicLogger, hash_data


class MatrixDimension(Enum):
    ANCHOR = "anchor"
    TAG = "tag"
    TIME = "time"
    SOURCE = "source"
    PRIORITY = "priority"


@dataclass
class MatrixCell:
    cell_id: str
    anchor: str
    tag: str
    source: str
    priority: int
    timestamp: float
    version: int
    data: Any
    data_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SingularityMatrix:
    """
    The 'singularity matrix' - multi-dimensional in-memory data store
    for decoded steganographic information.

    Data is organized by:
    - anchor (probe anchor point)
    - tag (categorization)
    - source (node that wrote it)
    - time (version history)
    - priority

    Acts as the central nervous system of the steganographic memory space.
    """

    def __init__(self, name: str = "singularity",
                 logger: Optional[LogicLogger] = None):
        self.matrix_id = generate_id("matrix")
        self.name = name
        self.logger = logger or LogicLogger(f"matrix_{name}")
        self._cells: Dict[str, MatrixCell] = {}
        self._index_anchor: Dict[str, List[str]] = {}
        self._index_tag: Dict[str, List[str]] = {}
        self._index_source: Dict[str, List[str]] = {}
        self._version_counters: Dict[str, int] = {}
        self._listeners: List[Callable[[MatrixCell], None]] = []
        self._lock = threading.RLock()

    @property
    def size(self) -> int:
        return len(self._cells)

    @property
    def anchors(self) -> List[str]:
        return sorted(self._index_anchor.keys())

    @property
    def tags(self) -> List[str]:
        return sorted(self._index_tag.keys())

    @property
    def sources(self) -> List[str]:
        return sorted(self._index_source.keys())

    def subscribe(self, callback: Callable[[MatrixCell], None]) -> None:
        self._listeners.append(callback)

    def _notify(self, cell: MatrixCell) -> None:
        for listener in self._listeners:
            try:
                listener(cell)
            except Exception:
                pass

    def write(self, anchor: str, data: Any, source: str = "unknown",
              tag: str = "default", priority: int = 5,
              metadata: Optional[Dict[str, Any]] = None) -> MatrixCell:
        with self._lock:
            key = f"{anchor}:{tag}:{source}"
            version = self._version_counters.get(key, 0) + 1
            self._version_counters[key] = version

            data_bytes = str(data).encode() if not isinstance(data, bytes) else data
            data_hash = hash_data(data_bytes)

            cell = MatrixCell(
                cell_id=generate_id("cell"),
                anchor=anchor,
                tag=tag,
                source=source,
                priority=priority,
                timestamp=time.time(),
                version=version,
                data=data,
                data_hash=data_hash,
                metadata=metadata or {},
            )
            self._cells[cell.cell_id] = cell
            self._add_to_index(self._index_anchor, anchor, cell.cell_id)
            self._add_to_index(self._index_tag, tag, cell.cell_id)
            self._add_to_index(self._index_source, source, cell.cell_id)

            self.logger.log(
                "matrix", "write",
                cell_id=cell.cell_id, anchor=anchor, tag=tag,
                source=source, version=version,
            )
            self._notify(cell)
            return cell

    def _add_to_index(self, index: Dict[str, List[str]], key: str, cell_id: str) -> None:
        if key not in index:
            index[key] = []
        index[key].append(cell_id)

    def read(self, anchor: str, tag: Optional[str] = None,
             latest_only: bool = True) -> List[MatrixCell]:
        with self._lock:
            cell_ids = self._index_anchor.get(anchor, [])
            cells = [self._cells[cid] for cid in cell_ids if cid in self._cells]
            if tag:
                cells = [c for c in cells if c.tag == tag]
            cells.sort(key=lambda c: c.timestamp, reverse=True)
            if latest_only and cells:
                return [cells[0]]
            return cells

    def query(self, anchor: Optional[str] = None, tag: Optional[str] = None,
              source: Optional[str] = None, priority_ge: Optional[int] = None,
              since: Optional[float] = None, limit: int = 100) -> List[MatrixCell]:
        with self._lock:
            candidates = None

            if anchor:
                ids = set(self._index_anchor.get(anchor, []))
                candidates = ids if candidates is None else candidates & ids
            if tag:
                ids = set(self._index_tag.get(tag, []))
                candidates = ids if candidates is None else candidates & ids
            if source:
                ids = set(self._index_source.get(source, []))
                candidates = ids if candidates is None else candidates & ids

            if candidates is None:
                candidates = set(self._cells.keys())

            cells = [self._cells[cid] for cid in candidates if cid in self._cells]

            if priority_ge is not None:
                cells = [c for c in cells if c.priority >= priority_ge]
            if since is not None:
                cells = [c for c in cells if c.timestamp >= since]

            cells.sort(key=lambda c: (c.priority, c.timestamp), reverse=True)
            return cells[:limit]

    def latest_by_anchor(self) -> Dict[str, MatrixCell]:
        with self._lock:
            result: Dict[str, MatrixCell] = {}
            for cell in self._cells.values():
                if cell.anchor not in result or cell.version > result[cell.anchor].version:
                    result[cell.anchor] = cell
            return result

    def delete_anchor(self, anchor: str) -> int:
        with self._lock:
            cell_ids = self._index_anchor.get(anchor, [])
            count = 0
            for cid in cell_ids:
                if cid in self._cells:
                    cell = self._cells[cid]
                    self._remove_from_index(self._index_tag, cell.tag, cid)
                    self._remove_from_index(self._index_source, cell.source, cid)
                    del self._cells[cid]
                    count += 1
            if anchor in self._index_anchor:
                del self._index_anchor[anchor]
            if count:
                self.logger.log("matrix", "delete_anchor", anchor=anchor, count=count)
            return count

    def _remove_from_index(self, index: Dict[str, List[str]], key: str, cell_id: str) -> None:
        if key in index and cell_id in index[key]:
            index[key].remove(cell_id)
            if not index[key]:
                del index[key]

    def clear(self) -> int:
        with self._lock:
            count = len(self._cells)
            self._cells.clear()
            self._index_anchor.clear()
            self._index_tag.clear()
            self._index_source.clear()
            self._version_counters.clear()
            self.logger.log("matrix", "clear", count=count)
            return count

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "matrix_id": self.matrix_id,
                "name": self.name,
                "total_cells": len(self._cells),
                "anchor_count": len(self._index_anchor),
                "tag_count": len(self._index_tag),
                "source_count": len(self._index_source),
                "listeners": len(self._listeners),
            }

    def __repr__(self) -> str:
        s = self.stats()
        return (f"<SingularityMatrix name={self.name} cells={s['total_cells']} "
                f"anchors={s['anchor_count']} tags={s['tag_count']}>")
