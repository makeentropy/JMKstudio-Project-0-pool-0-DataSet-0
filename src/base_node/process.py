"""
Memory Process - lightweight in-memory process abstraction.
ProcessManager - orchestrates multiple memory processes (base nodes).
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from enum import Enum

from .node import BaseNode, NodeState
from ..utils import generate_id, LogicLogger


class ProcessState(Enum):
    SPAWNING = "spawning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ZOMBIE = "zombie"
    REAPED = "reaped"


class MemoryProcess:
    """
    Wraps a BaseNode with process-level metadata:
    PID, parent, priority, resource limits, etc.
    Analogous to an OS process but in the steganographic memory space.
    """

    def __init__(self, node: BaseNode, pid: Optional[str] = None,
                 parent_pid: Optional[str] = None, priority: int = 5):
        self.pid = pid or generate_id("proc")
        self.node = node
        self.parent_pid = parent_pid
        self.priority = priority
        self.state = ProcessState.SPAWNING
        self.created_at = time.time()
        self.last_scheduled = 0.0
        self.cpu_time = 0.0
        self._children: List[str] = []

    @property
    def name(self) -> str:
        return self.node.name

    def start(self) -> bool:
        ok = self.node.initialize()
        if ok:
            self.state = ProcessState.ACTIVE
            self.last_scheduled = time.time()
        return ok

    def suspend(self) -> bool:
        if self.state == ProcessState.ACTIVE:
            self.node.pause()
            self.state = ProcessState.SUSPENDED
            return True
        return False

    def resume(self) -> bool:
        if self.state == ProcessState.SUSPENDED:
            self.node.resume()
            self.state = ProcessState.ACTIVE
            self.last_scheduled = time.time()
            return True
        return False

    def kill(self) -> None:
        self.node.terminate()
        self.state = ProcessState.ZOMBIE

    def add_child(self, child_pid: str) -> None:
        self._children.append(child_pid)

    @property
    def children(self) -> List[str]:
        return list(self._children)

    def info(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "parent_pid": self.parent_pid,
            "priority": self.priority,
            "state": self.state.value,
            "node_state": self.node.state.value,
            "created_at": self.created_at,
            "cpu_time": self.cpu_time,
            "children": len(self._children),
        }


class ProcessManager:
    """
    Manages a set of MemoryProcess instances - the 'process table'
    of the steganographic memory system.

    Supports:
    - Fork / spawn
    - Priority scheduling
    - Process tree (parent / child)
    - Reaping zombies
    """

    def __init__(self, ca, logger: Optional[LogicLogger] = None):
        self.ca = ca
        self.logger = logger or LogicLogger("process_manager")
        self._processes: Dict[str, MemoryProcess] = {}
        self._lock = threading.RLock()
        self._next_pid = 1

    @property
    def count(self) -> int:
        return len(self._processes)

    def spawn(self, name: str, parent_pid: Optional[str] = None,
              priority: int = 5, matrix=None) -> Optional[MemoryProcess]:
        with self._lock:
            node = BaseNode(name, self.ca, self.logger)
            if matrix:
                node.attach_matrix(matrix)
            proc = MemoryProcess(node, parent_pid=parent_pid, priority=priority)
            self._processes[proc.pid] = proc

            if parent_pid and parent_pid in self._processes:
                self._processes[parent_pid].add_child(proc.pid)

            self.logger.log("process_manager", "spawn", pid=proc.pid, name=name, parent=parent_pid)

            if proc.start():
                proc.state = ProcessState.ACTIVE
                self.logger.log("process_manager", "started", pid=proc.pid)
                return proc
            else:
                proc.state = ProcessState.ZOMBIE
                self.logger.log("process_manager", "spawn_failed", pid=proc.pid)
                return None

    def get(self, pid: str) -> Optional[MemoryProcess]:
        return self._processes.get(pid)

    def list_processes(self) -> List[MemoryProcess]:
        return list(self._processes.values())

    def suspend(self, pid: str) -> bool:
        proc = self._processes.get(pid)
        if proc and proc.state == ProcessState.ACTIVE:
            result = proc.suspend()
            if result:
                self.logger.log("process_manager", "suspend", pid=pid)
            return result
        return False

    def resume(self, pid: str) -> bool:
        proc = self._processes.get(pid)
        if proc and proc.state == ProcessState.SUSPENDED:
            result = proc.resume()
            if result:
                self.logger.log("process_manager", "resume", pid=pid)
            return result
        return False

    def kill(self, pid: str) -> bool:
        proc = self._processes.get(pid)
        if proc:
            proc.kill()
            self.logger.log("process_manager", "kill", pid=pid)
            return True
        return False

    def reap(self) -> int:
        with self._lock:
            reaped = 0
            to_remove = [pid for pid, p in self._processes.items()
                         if p.state == ProcessState.ZOMBIE]
            for pid in to_remove:
                del self._processes[pid]
                reaped += 1
            if reaped:
                self.logger.log("process_manager", "reap", count=reaped)
            return reaped

    def find_by_tag(self, tag: str) -> List[MemoryProcess]:
        return [p for p in self._processes.values() if p.node.has_tag(tag)]

    def find_by_name(self, name: str) -> List[MemoryProcess]:
        return [p for p in self._processes.values() if p.name == name]

    def ps(self) -> List[dict]:
        return [p.info() for p in self._processes.values()]
