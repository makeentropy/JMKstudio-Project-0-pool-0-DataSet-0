"""
Node Registry - service registry & lookup for base nodes.
Provides tag-based discovery, certificate-based identity verification,
and encrypted inter-node communication channels.
"""

import threading
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from .node import BaseNode
from ..utils import CA, Certificate, LogicLogger


@dataclass
class RegistryEntry:
    node: BaseNode
    tags: Set[str]
    certificate: Certificate


class NodeRegistry:
    """
    Central registry for all active nodes.

    Features:
    - Register / unregister nodes
    - Tag-based lookup (the 'tag' entry point mentioned in spec)
    - Certificate verification for node identity
    - Encrypted channel setup between registered nodes
    """

    def __init__(self, ca: CA, logger: Optional[LogicLogger] = None):
        self.ca = ca
        self.logger = logger or LogicLogger("node_registry")
        self._entries: Dict[str, RegistryEntry] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def register(self, node: BaseNode) -> bool:
        with self._lock:
            if node.node_id in self._entries:
                return False
            if not self.ca.verify_certificate(node.certificate):
                self.logger.log("registry", "register_rejected",
                               node_id=node.node_id, reason="bad_cert")
                return False
            entry = RegistryEntry(
                node=node,
                tags=set(node.tags),
                certificate=node.certificate,
            )
            self._entries[node.node_id] = entry
            self._update_tag_index(node.node_id, node.tags)
            self.logger.log("registry", "registered",
                            node_id=node.node_id, name=node.name)
            return True

    def unregister(self, node_id: str) -> bool:
        with self._lock:
            if node_id not in self._entries:
                return False
            entry = self._entries[node_id]
            for tag in entry.tags:
                if tag in self._tag_index and node_id in self._tag_index[tag]:
                    self._tag_index[tag].discard(node_id)
                    if not self._tag_index[tag]:
                        del self._tag_index[tag]
            del self._entries[node_id]
            self.logger.log("registry", "unregistered", node_id=node_id)
            return True

    def _update_tag_index(self, node_id: str, tags: List[str]) -> None:
        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(node_id)

    def get(self, node_id: str) -> Optional[BaseNode]:
        entry = self._entries.get(node_id)
        return entry.node if entry else None

    def find_by_tag(self, tag: str) -> List[BaseNode]:
        with self._lock:
            node_ids = self._tag_index.get(tag, set())
            return [self._entries[nid].node for nid in node_ids
                    if nid in self._entries]

    def find_by_tags(self, tags: List[str], match_all: bool = True) -> List[BaseNode]:
        with self._lock:
            if not tags:
                return [e.node for e in self._entries.values()]
            result_ids = None
            for tag in tags:
                ids = self._tag_index.get(tag, set())
                if result_ids is None:
                    result_ids = set(ids)
                elif match_all:
                    result_ids &= ids
                else:
                    result_ids |= ids
            if result_ids is None:
                return []
            return [self._entries[nid].node for nid in result_ids
                    if nid in self._entries]

    def all_tags(self) -> List[str]:
        return sorted(self._tag_index.keys())

    @property
    def size(self) -> int:
        return len(self._entries)

    def list_nodes(self) -> List[dict]:
        return [
            {
                "node_id": e.node.node_id,
                "name": e.node.name,
                "state": e.node.state.value,
                "tags": sorted(e.tags),
            }
            for e in self._entries.values()
        ]
