"""
Probe Manager - manages a fleet of probes.

Handles probe lifecycle, dimension space pool interaction,
and routing of probe requests to the appropriate memory spaces.
"""

import threading
from typing import Dict, List, Optional, Any

from .probe import Probe, ProbeState, MediumType
from ..memory_matrix import MemoryPool
from ..utils import CA, LogicLogger


class ProbeManager:
    """
    Central manager for all probes.

    Responsibilities:
    - Create / destroy probes
    - Route encoded data to the right memory space
    - Coordinate with the dimension space pool
    - Provide the 'probe interface request' mechanism
    """

    def __init__(self, ca: CA, pool: Optional[MemoryPool] = None,
                 logger: Optional[LogicLogger] = None):
        self.ca = ca
        self.pool = pool
        self.logger = logger or LogicLogger("probe_manager")
        self._probes: Dict[str, Probe] = {}
        self._lock = threading.RLock()

    @property
    def count(self) -> int:
        return len(self._probes)

    def create_probe(self, name: str,
                     medium_type: MediumType = MediumType.BYTES) -> Probe:
        with self._lock:
            matrix = self.pool.matrix if self.pool else None
            probe = Probe(name, self.ca, matrix=matrix,
                          medium_type=medium_type, logger=self.logger)
            self._probes[probe.probe_id] = probe
            self.logger.log("probe_manager", "created",
                           probe_id=probe.probe_id, name=name)
            return probe

    def get_probe(self, probe_id: str) -> Optional[Probe]:
        return self._probes.get(probe_id)

    def find_by_name(self, name: str) -> Optional[Probe]:
        for p in self._probes.values():
            if p.name == name:
                return p
        return None

    def list_probes(self) -> List[dict]:
        return [p.get_status() for p in self._probes.values()]

    def remove_probe(self, probe_id: str) -> bool:
        with self._lock:
            if probe_id in self._probes:
                del self._probes[probe_id]
                self.logger.log("probe_manager", "removed", probe_id=probe_id)
                return True
            return False

    def generate_probe_request(self, probe_name: str, data: bytes,
                                tag: str = "default") -> Optional[Dict[str, Any]]:
        probe = self.find_by_name(probe_name)
        if not probe:
            probe = self.create_probe(probe_name)
        return probe.build_probe_request(data, tag=tag)

    def decode_probe_request(self, probe_request: Dict[str, Any],
                              target_space: Optional[str] = None) -> Optional[bytes]:
        from ..steganography import StegoMedium, MediumType, AnchorPoint
        probe_id = probe_request.get("probe_id")
        probe = self._probes.get(probe_id)
        if not probe:
            return None

        medium_type = MediumType(probe_request.get("medium_type", "bytes"))
        medium = StegoMedium(probe_request["payload"], medium_type)

        anchor_id = probe_request.get("anchor", "")
        anchor = None
        for a in probe.anchors:
            if a.anchor_id == anchor_id:
                anchor = a
                break
        if not anchor:
            return None

        data = probe.decode_from_medium(medium, anchor)
        if data is not None and self.pool and target_space:
            space = self.pool.get_space(target_space)
            if space:
                pass
        return data

    def attach_pool(self, pool: MemoryPool) -> None:
        self.pool = pool
        for probe in self._probes.values():
            probe.attach_matrix(pool.matrix)
        self.logger.log("probe_manager", "pool_attached", pool_id=pool.pool_id)

    def stats(self) -> Dict[str, Any]:
        total_encoded = sum(p.metrics.data_encoded_bytes for p in self._probes.values())
        total_decoded = sum(p.metrics.data_decoded_bytes for p in self._probes.values())
        total_writes = sum(p.metrics.matrix_writes for p in self._probes.values())
        return {
            "probe_count": len(self._probes),
            "total_encoded_bytes": total_encoded,
            "total_decoded_bytes": total_decoded,
            "total_matrix_writes": total_writes,
            "has_pool": self.pool is not None,
        }
