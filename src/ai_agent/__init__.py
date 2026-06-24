"""
ai_agent - Autonomous consciousness LLM agent with self-training.

The agent:
- Has 'autonomous consciousness' via goal-driven behavior
- Self-trains on incoming data from the steganographic memory matrix
- Generates logic logs that feed back into the system (self-iteration)
- Operates through the probe interface for steganographic I/O
- Manages OKRs for goal tracking
"""

from .agent import StegoAgent, AgentState, ConsciousnessLoop
from .self_train import SelfTrainer, TrainingMemory
from .okr import OKR, Objective, KeyResult

__all__ = [
    "StegoAgent",
    "AgentState",
    "ConsciousnessLoop",
    "SelfTrainer",
    "TrainingMemory",
    "OKR",
    "Objective",
    "KeyResult",
]
