"""
Logic Logger - the institutional encoding of the quantum singularity space matrix.
Records all system operations as an immutable, self-iterating log chain.
"""

import hashlib
import time
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from .crypto import generate_id


@dataclass
class LogicEntry:
    entry_id: str
    timestamp: float
    module: str
    action: str
    payload: Dict[str, Any]
    prev_hash: str
    hash: str = ""
    iteration: int = 0

    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        content = json.dumps({
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "module": self.module,
            "action": self.action,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "iteration": self.iteration,
        }, sort_keys=True).encode()
        return hashlib.sha256(content).hexdigest()


class LogicLogger:
    def __init__(self, name: str = "singularity_log"):
        self.name = name
        self._chain: List[LogicEntry] = []
        self._subscribers: List[Callable[[LogicEntry], None]] = []
        self._iteration_count = 0
        self._genesis = self._create_genesis()

    def _create_genesis(self) -> LogicEntry:
        entry = LogicEntry(
            entry_id=generate_id("genesis"),
            timestamp=time.time(),
            module="system",
            action="genesis",
            payload={"name": self.name},
            prev_hash="0" * 64,
            iteration=0,
        )
        self._chain.append(entry)
        return entry

    @property
    def last_hash(self) -> str:
        return self._chain[-1].hash if self._chain else "0" * 64

    @property
    def chain_length(self) -> int:
        return len(self._chain)

    @property
    def iteration(self) -> int:
        return self._iteration_count

    def log(self, module: str, action: str, **payload) -> LogicEntry:
        self._iteration_count += 1
        entry = LogicEntry(
            entry_id=generate_id("log"),
            timestamp=time.time(),
            module=module,
            action=action,
            payload=payload,
            prev_hash=self.last_hash,
            iteration=self._iteration_count,
        )
        self._chain.append(entry)
        for sub in self._subscribers:
            try:
                sub(entry)
            except Exception:
                pass
        return entry

    def subscribe(self, callback: Callable[[LogicEntry], None]):
        self._subscribers.append(callback)

    def verify_chain(self) -> bool:
        for i in range(1, len(self._chain)):
            curr = self._chain[i]
            prev = self._chain[i - 1]
            if curr.prev_hash != prev.hash:
                return False
            if curr.hash != curr._compute_hash():
                return False
        return True

    def get_entries(self, module: Optional[str] = None,
                    action: Optional[str] = None) -> List[LogicEntry]:
        result = self._chain
        if module:
            result = [e for e in result if e.module == module]
        if action:
            result = [e for e in result if e.action == action]
        return list(result)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "chain_length": self.chain_length,
            "iteration": self.iteration,
            "valid": self.verify_chain(),
            "last_hash": self.last_hash,
        }

    def __repr__(self) -> str:
        return (f"LogicLogger(name={self.name}, entries={self.chain_length}, "
                f"iteration={self.iteration}, valid={self.verify_chain()})")
