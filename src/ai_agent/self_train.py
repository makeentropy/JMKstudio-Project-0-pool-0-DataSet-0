"""
Self Trainer - autonomous training from steganographic memory data.

Implements the 'dataset autonomous training generation logic log
self-iteration' concept: the agent learns from data in the memory
matrix, updates its internal model, and generates logic logs that
feed back into the system.
"""

import time
import hashlib
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque

from ..memory_matrix import SingularityMatrix, MatrixCell
from ..utils import LogicLogger, hash_data


@dataclass
class TrainingSample:
    sample_id: str
    input_data: Any
    output_data: Any
    tag: str
    weight: float
    timestamp: float
    source: str = "unknown"


class TrainingMemory:
    """
    The agent's training memory - stores patterns learned from
    the steganographic memory space.

    Implements a simple associative memory that the self-trainer
    uses to 'learn' from incoming data.
    """

    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self._samples: deque = deque(maxlen=max_samples)
        self._patterns: Dict[str, float] = {}
        self._associations: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)

    def add_sample(self, sample: TrainingSample) -> None:
        with self._lock:
            self._samples.append(sample)
            self._extract_patterns(sample)

    def _extract_patterns(self, sample: TrainingSample) -> None:
        data_str = str(sample.input_data) if not isinstance(sample.input_data, str) else sample.input_data
        words = data_str.split()
        for word in words:
            key = f"{sample.tag}:{word}"
            self._patterns[key] = self._patterns.get(key, 0) + sample.weight

    def get_patterns(self, tag: Optional[str] = None, top_n: int = 20) -> List[Tuple[str, float]]:
        with self._lock:
            patterns = self._patterns
            if tag:
                patterns = {k: v for k, v in patterns.items() if k.startswith(f"{tag}:")}
            return sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def find_associated(self, tag: str) -> List[str]:
        with self._lock:
            return list(self._associations.get(tag, []))

    def associate(self, tag_a: str, tag_b: str) -> None:
        with self._lock:
            if tag_a not in self._associations:
                self._associations[tag_a] = []
            if tag_b not in self._associations[tag_a]:
                self._associations[tag_a].append(tag_b)


class SelfTrainer:
    """
    Self-trainer - autonomously learns from data in the memory matrix.

    The 'autonomous training' concept: continuously scans the matrix
    for new data, extracts patterns, builds associations, and updates
    the training memory. Each training iteration generates a logic log
    entry, contributing to the self-iteration cycle.
    """

    def __init__(self, matrix: SingularityMatrix,
                 logger: Optional[LogicLogger] = None,
                 interval: float = 3.0):
        self.matrix = matrix
        self.logger = logger or LogicLogger("self_trainer")
        self.interval = interval
        self.memory = TrainingMemory()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_check: float = 0.0
        self._training_cycles: int = 0
        self._lock = threading.RLock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def training_cycles(self) -> int:
        return self._training_cycles

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self.logger.log("self_trainer", "started")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.logger.log("self_trainer", "stopped")

    def _run(self) -> None:
        while self._running:
            try:
                self._training_step()
            except Exception as e:
                self.logger.log("self_trainer", "step_error", error=str(e))
            time.sleep(self.interval)

    def _training_step(self) -> None:
        self._training_cycles += 1
        since = self._last_check
        self._last_check = time.time()

        new_cells = self.matrix.query(since=since, limit=100)

        for cell in new_cells:
            sample = TrainingSample(
                sample_id=cell.cell_id,
                input_data=cell.data,
                output_data=cell.metadata,
                tag=cell.tag,
                weight=cell.priority / 10.0,
                timestamp=cell.timestamp,
                source=cell.source,
            )
            self.memory.add_sample(sample)

        tags = set(cell.tag for cell in new_cells)
        if len(tags) >= 2:
            tag_list = list(tags)
            for i in range(len(tag_list)):
                for j in range(i + 1, len(tag_list)):
                    self.memory.associate(tag_list[i], tag_list[j])
                    self.memory.associate(tag_list[j], tag_list[i])

        if new_cells:
            self.logger.log(
                "self_trainer", "training_iteration",
                cycle=self._training_cycles,
                new_samples=len(new_cells),
                total_samples=self.memory.sample_count,
                patterns=self.memory.pattern_count,
            )

    def train_on_cell(self, cell: MatrixCell) -> None:
        sample = TrainingSample(
            sample_id=cell.cell_id,
            input_data=cell.data,
            output_data=cell.metadata,
            tag=cell.tag,
            weight=cell.priority / 10.0,
            timestamp=cell.timestamp,
            source=cell.source,
        )
        self.memory.add_sample(sample)

    def get_insights(self, tag: Optional[str] = None) -> Dict[str, Any]:
        patterns = self.memory.get_patterns(tag=tag, top_n=10)
        return {
            "training_cycles": self._training_cycles,
            "total_samples": self.memory.sample_count,
            "total_patterns": self.memory.pattern_count,
            "top_patterns": patterns,
        }

    def __repr__(self) -> str:
        return (f"<SelfTrainer cycles={self._training_cycles} "
                f"samples={self.memory.sample_count} "
                f"patterns={self.memory.pattern_count}>")
