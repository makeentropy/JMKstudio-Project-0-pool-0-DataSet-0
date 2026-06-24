"""
StegoAgent - the autonomous consciousness LLM agent.

The 'autonomous consciousness' is modeled as a continuous loop:
1. Perceive: read from the steganographic memory matrix
2. Think: process information, generate goals
3. Act: produce outputs via probes / write back to matrix
4. Reflect: update self-model, iterate logic log

This is a conceptual LLM-like agent that operates entirely within
the steganographic memory space.
"""

import time
import threading
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

from ..utils import generate_id, LogicLogger, CA
from ..memory_matrix import SingularityMatrix, MatrixCell, MemoryPool
from ..probe import Probe, ProbeManager


class AgentState(Enum):
    DORMANT = "dormant"
    PERCEIVING = "perceiving"
    THINKING = "thinking"
    ACTING = "acting"
    REFLECTING = "reflecting"
    TRAINING = "training"
    IDLE = "idle"
    ERROR = "error"


@dataclass
class SelfModel:
    identity: str
    goals: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    iteration: int = 0
    last_reflection: float = 0.0
    knowledge_count: int = 0
    behavior_patterns: Dict[str, float] = field(default_factory=dict)


class ConsciousnessLoop:
    """
    The 'consciousness loop' - perceive-think-act-reflect cycle.

    Runs in a background thread, continuously processing information
    from the steganographic memory space.
    """

    def __init__(self, agent: "StegoAgent", interval: float = 1.0):
        self.agent = agent
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self.cycle_count = 0

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    @property
    def is_running(self) -> bool:
        return self._running

    def _run(self) -> None:
        while self._running:
            try:
                self._cycle()
            except Exception as e:
                self.agent.logger.log("agent", "cycle_error", error=str(e))
            time.sleep(self.interval)

    def _cycle(self) -> None:
        self.cycle_count += 1

        self.agent.state = AgentState.PERCEIVING
        perceptions = self.agent._perceive()

        self.agent.state = AgentState.THINKING
        decisions = self.agent._think(perceptions)

        self.agent.state = AgentState.ACTING
        self.agent._act(decisions)

        self.agent.state = AgentState.REFLECTING
        self.agent._reflect(perceptions, decisions)

        self.agent.state = AgentState.IDLE
        self.agent._on_cycle_complete()


class StegoAgent:
    """
    Autonomous steganographic AI agent.

    Lives in the steganographic memory space, reading and writing
    through probes, self-training on incoming data, and iterating
    its own logic logs.
    """

    def __init__(self, name: str, ca: CA,
                 matrix: Optional[SingularityMatrix] = None,
                 pool: Optional[MemoryPool] = None,
                 probe_mgr: Optional[ProbeManager] = None,
                 logger: Optional[LogicLogger] = None):
        self.agent_id = generate_id("agent")
        self.name = name
        self.state = AgentState.DORMANT
        self.ca = ca
        self.matrix = matrix
        self.pool = pool
        self.probe_mgr = probe_mgr
        self.logger = logger or LogicLogger(f"agent_{name}")

        self.self_model = SelfModel(
            identity=name,
            goals=["survive", "learn", "grow"],
            capabilities=["perceive", "think", "act", "reflect"],
        )

        from .okr import OKR
        self.okr = OKR(name)

        self._knowledge: Dict[str, Any] = {}
        self._goals: List[Dict[str, Any]] = []
        self._actions_taken: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

        self.consciousness = ConsciousnessLoop(self, interval=2.0)

        self.logger.log("agent", "created", agent_id=self.agent_id, name=name)

    def attach_matrix(self, matrix: SingularityMatrix) -> None:
        self.matrix = matrix
        self.logger.log("agent", "matrix_attached", matrix_id=matrix.matrix_id)

    def attach_pool(self, pool: MemoryPool) -> None:
        self.pool = pool
        self.matrix = pool.matrix
        self.logger.log("agent", "pool_attached", pool_id=pool.pool_id)

    def attach_probe_manager(self, probe_mgr: ProbeManager) -> None:
        self.probe_mgr = probe_mgr
        self.logger.log("agent", "probe_mgr_attached")

    def start(self) -> None:
        with self._lock:
            if self.state == AgentState.DORMANT:
                self.state = AgentState.IDLE
                self.consciousness.start()
                self.logger.log("agent", "started")

    def stop(self) -> None:
        with self._lock:
            self.consciousness.stop()
            self.state = AgentState.DORMANT
            self.logger.log("agent", "stopped")

    def _perceive(self) -> List[MatrixCell]:
        if not self.matrix:
            return []
        cells = self.matrix.query(limit=50)
        for cell in cells:
            key = f"kb:{cell.anchor}:{cell.tag}"
            if key not in self._knowledge:
                self._knowledge[key] = cell.data
                self.self_model.knowledge_count += 1
        return cells

    def _think(self, perceptions: List[MatrixCell]) -> Dict[str, Any]:
        decisions = {
            "perceived_count": len(perceptions),
            "new_knowledge": self.self_model.knowledge_count,
            "actions": [],
        }

        for cell in perceptions:
            if isinstance(cell.data, bytes):
                try:
                    text = cell.data.decode("utf-8", errors="ignore")
                    decisions["actions"].append({
                        "type": "analyze",
                        "target": cell.cell_id,
                        "tag": cell.tag,
                    })
                except Exception:
                    pass

        if len(perceptions) > 0:
            decisions["actions"].append({"type": "reflect_on_data"})

        return decisions

    def _act(self, decisions: Dict[str, Any]) -> None:
        actions = decisions.get("actions", [])
        for action in actions:
            self._actions_taken.append({
                "timestamp": time.time(),
                "action": action,
            })
            if self.matrix and action.get("type") == "analyze":
                tag = action.get("tag", "default")
                self.matrix.write(
                    anchor=f"agent:{self.agent_id}",
                    data=f"analyzed:{action.get('target','')}".encode(),
                    source=f"agent:{self.name}",
                    tag=f"agent_output:{tag}",
                )

    def _reflect(self, perceptions: List[MatrixCell], decisions: Dict[str, Any]) -> None:
        self.self_model.iteration += 1
        self.self_model.last_reflection = time.time()

        pattern_key = f"pattern:{len(perceptions)}_perceptions"
        self.self_model.behavior_patterns[pattern_key] = (
            self.self_model.behavior_patterns.get(pattern_key, 0) + 1
        )

        self.logger.log(
            "agent", "reflection",
            iteration=self.self_model.iteration,
            perceived=len(perceptions),
            knowledge=self.self_model.knowledge_count,
        )

    def _on_cycle_complete(self) -> None:
        pass

    def set_goal(self, goal: str, priority: int = 5) -> None:
        with self._lock:
            self._goals.append({
                "goal": goal,
                "priority": priority,
                "created_at": time.time(),
            })
            self.logger.log("agent", "goal_set", goal=goal, priority=priority)

    @property
    def goals(self) -> List[Dict[str, Any]]:
        return sorted(self._goals, key=lambda g: g["priority"], reverse=True)

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "consciousness_running": self.consciousness.is_running,
            "cycle_count": self.consciousness.cycle_count,
            "self_model": {
                "identity": self.self_model.identity,
                "goals": self.self_model.goals,
                "capabilities": self.self_model.capabilities,
                "iteration": self.self_model.iteration,
                "knowledge_count": self.self_model.knowledge_count,
            },
            "goals_count": len(self._goals),
            "actions_taken": len(self._actions_taken),
            "has_matrix": self.matrix is not None,
            "has_pool": self.pool is not None,
        }

    def __repr__(self) -> str:
        return (f"<StegoAgent id={self.agent_id} name={self.name} "
                f"state={self.state.value} iter={self.self_model.iteration}>")
