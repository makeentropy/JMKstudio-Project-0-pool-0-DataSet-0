"""
Base Node - the fundamental memory-resident node with validator shell.

A BaseNode is like an in-memory process: it has lifecycle state,
can receive steganographic data via probes, validates it against
CA certificates, and writes decoded data into the singularity
memory matrix.
"""

import time
import threading
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field

from ..utils import generate_id, LogicLogger, CA, Certificate


class NodeState(Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    VALIDATING = "validating"
    ERROR = "error"
    TERMINATED = "terminated"


class ValidatorShell:
    """
    The 'validator shell' - the security boundary of a base node.
    All data entering or leaving the node must pass through this shell,
    which verifies CA certificates, probe integrity, and data checksums.
    """

    def __init__(self, ca: CA, node_cert: Certificate):
        self.ca = ca
        self.node_cert = node_cert
        self._validations_passed = 0
        self._validations_failed = 0

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "passed": self._validations_passed,
            "failed": self._validations_failed,
        }

    def validate_probe(self, probe_data: Dict[str, Any]) -> bool:
        required = ["probe_id", "payload_hash", "certificate", "signature"]
        if not all(k in probe_data for k in required):
            self._validations_failed += 1
            return False
        cert = probe_data["certificate"]
        if isinstance(cert, Certificate):
            if not self.ca.verify_certificate(cert):
                self._validations_failed += 1
                return False
        self._validations_passed += 1
        return True

    def validate_payload(self, payload: bytes, expected_hash: str) -> bool:
        from ..utils import hash_data
        actual = hash_data(payload)
        result = actual == expected_hash
        if result:
            self._validations_passed += 1
        else:
            self._validations_failed += 1
        return result


@dataclass
class NodeMetrics:
    started_at: float = 0.0
    last_heartbeat: float = 0.0
    probes_received: int = 0
    data_decoded: int = 0
    validation_errors: int = 0
    matrix_writes: int = 0
    matrix_reads: int = 0


class BaseNode:
    """
    Base node - a self-contained in-memory process component.

    Responsibilities:
    - Maintain lifecycle state
    - Validate incoming steganographic probes
    - Decode steganographic data
    - Organize decoded data into the steganographic memory space
      (singularity matrix interface)
    - Execute registered callbacks / handlers
    """

    def __init__(self, name: str, ca: CA, logger: Optional[LogicLogger] = None):
        self.node_id = generate_id("node")
        self.name = name
        self.state = NodeState.CREATED
        self.logger = logger or LogicLogger(f"node_{name}")

        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        self._private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        self._public_key = self._private_key.public_key()
        self.certificate = ca.issue_certificate(self.node_id, self._public_key)
        self.validator = ValidatorShell(ca, self.certificate)

        self.metrics = NodeMetrics()
        self._handlers: Dict[str, List[Callable]] = {}
        self._tags: set = set()
        self._lock = threading.RLock()
        self._memory_matrix = None

        self.logger.log("base_node", "created", node_id=self.node_id, name=name)

    def attach_matrix(self, matrix) -> None:
        self._memory_matrix = matrix
        self.logger.log("base_node", "matrix_attached", matrix_id=getattr(matrix, "matrix_id", "unknown"))

    @property
    def tags(self) -> List[str]:
        return sorted(self._tags)

    def add_tag(self, tag: str) -> None:
        with self._lock:
            self._tags.add(tag)
            self.logger.log("base_node", "tag_added", tag=tag)

    def remove_tag(self, tag: str) -> bool:
        with self._lock:
            if tag in self._tags:
                self._tags.remove(tag)
                self.logger.log("base_node", "tag_removed", tag=tag)
                return True
            return False

    def has_tag(self, tag: str) -> bool:
        return tag in self._tags

    def register_handler(self, event: str, handler: Callable) -> None:
        with self._lock:
            if event not in self._handlers:
                self._handlers[event] = []
            self._handlers[event].append(handler)
            self.logger.log("base_node", "handler_registered", event=event)

    def _emit(self, event: str, **data) -> None:
        handlers = self._handlers.get(event, [])
        for h in handlers:
            try:
                h(self, **data)
            except Exception as e:
                self.logger.log("base_node", "handler_error", event=event, error=str(e))

    def initialize(self) -> bool:
        with self._lock:
            if self.state != NodeState.CREATED:
                return False
            self.state = NodeState.INITIALIZING
            self.metrics.started_at = time.time()
            self.logger.log("base_node", "initializing")
            try:
                self._on_initialize()
                self.state = NodeState.RUNNING
                self.metrics.last_heartbeat = time.time()
                self.logger.log("base_node", "initialized")
                self._emit("initialized")
                return True
            except Exception as e:
                self.state = NodeState.ERROR
                self.logger.log("base_node", "init_failed", error=str(e))
                return False

    def _on_initialize(self) -> None:
        pass

    def heartbeat(self) -> None:
        with self._lock:
            if self.state == NodeState.RUNNING:
                self.metrics.last_heartbeat = time.time()

    def pause(self) -> bool:
        with self._lock:
            if self.state == NodeState.RUNNING:
                self.state = NodeState.PAUSED
                self.logger.log("base_node", "paused")
                self._emit("paused")
                return True
            return False

    def resume(self) -> bool:
        with self._lock:
            if self.state == NodeState.PAUSED:
                self.state = NodeState.RUNNING
                self.logger.log("base_node", "resumed")
                self._emit("resumed")
                return True
            return False

    def receive_probe(self, probe_data: Dict[str, Any]) -> Optional[Any]:
        with self._lock:
            if self.state not in (NodeState.RUNNING, NodeState.VALIDATING):
                self.logger.log("base_node", "probe_rejected", reason="node_not_running")
                return None

            self.metrics.probes_received += 1
            self.state = NodeState.VALIDATING

            if not self.validator.validate_probe(probe_data):
                self.metrics.validation_errors += 1
                self.state = NodeState.RUNNING
                self.logger.log("base_node", "probe_validation_failed")
                return None

            decoded = self._decode_stego(probe_data)
            if decoded is None:
                self.metrics.validation_errors += 1
                self.state = NodeState.RUNNING
                self.logger.log("base_node", "stego_decode_failed")
                return None

            self.metrics.data_decoded += len(decoded) if isinstance(decoded, (bytes, str)) else 1

            if self._memory_matrix is not None:
                self._write_to_matrix(decoded, probe_data)
                self.metrics.matrix_writes += 1

            self.state = NodeState.RUNNING
            self._emit("probe_processed", data=decoded, probe=probe_data)
            self.logger.log("base_node", "probe_processed", probe_id=probe_data.get("probe_id"))
            return decoded

    def _decode_stego(self, probe_data: Dict[str, Any]) -> Optional[Any]:
        from ..steganography import StegoDecoder
        try:
            decoder = StegoDecoder()
            return decoder.decode(probe_data.get("payload", b""))
        except Exception as e:
            self.logger.log("base_node", "decode_error", error=str(e))
            return None

    def _write_to_matrix(self, decoded: Any, probe_data: Dict[str, Any]) -> None:
        if self._memory_matrix is None:
            return
        anchor = probe_data.get("anchor", "default")
        self._memory_matrix.write(anchor, decoded, source=self.node_id)

    def terminate(self) -> None:
        with self._lock:
            if self.state == NodeState.TERMINATED:
                return
            self.state = NodeState.TERMINATED
            self.logger.log("base_node", "terminated")
            self._emit("terminated")

    def get_status(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "state": self.state.value,
            "tags": self.tags,
            "metrics": {
                "uptime": time.time() - self.metrics.started_at if self.metrics.started_at else 0,
                "probes_received": self.metrics.probes_received,
                "data_decoded": self.metrics.data_decoded,
                "validation_errors": self.metrics.validation_errors,
                "matrix_writes": self.metrics.matrix_writes,
                "matrix_reads": self.metrics.matrix_reads,
            },
            "validation_stats": self.validator.stats,
            "has_matrix": self._memory_matrix is not None,
        }

    def __repr__(self) -> str:
        return f"<BaseNode id={self.node_id} name={self.name} state={self.state.value}>"
