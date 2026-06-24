"""
base_node - Core validator shell & in-memory process maintenance.

The base_node acts as a "process in memory" - it maintains lifecycle,
validates incoming steganographic data, and coordinates between the
singularity memory matrix, probes, and agent systems.
"""

from .node import BaseNode, NodeState, ValidatorShell
from .process import MemoryProcess, ProcessManager
from .registry import NodeRegistry

__all__ = [
    "BaseNode",
    "NodeState",
    "ValidatorShell",
    "MemoryProcess",
    "ProcessManager",
    "NodeRegistry",
]
