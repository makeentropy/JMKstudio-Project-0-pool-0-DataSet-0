"""
策略Agent模块

提供自主决策、策略执行、记忆系统、学习系统等Agent功能。
"""

from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.agent.models import (
    Action,
    ActionType,
    Agent,
    AgentConfig,
    AgentState,
    Observation,
    Policy,
    Reward,
    Skill,
    Strategy,
)
from ai_llm_agent_crawler.agent.skill_vector_machine import SkillVectorMachine
from ai_llm_agent_crawler.agent.strategy_generator import (
    AdaptiveStrategyGenerator,
    EntropyDrivenStrategy,
    MultiStrategyEnsemble,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class MemorySystem:
    """记忆系统"""

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.short_term: Deque[Observation] = deque(maxlen=capacity // 10)
        self.long_term: Deque[Tuple[Observation, Action, Reward, Observation]] = deque(maxlen=capacity)
        self.episodic: List[List[Dict[str, Any]]] = []
        self.semantic: Dict[str, Any] = {}
        self.procedural: Dict[str, Skill] = {}
        self.attention_weights: Dict[str, float] = {}
        self.logger = get_logger(f"{__name__}.MemorySystem")

    def store_short_term(self, observation: Observation) -> None:
        self.short_term.append(observation)

    def store_experience(
        self,
        observation: Observation,
        action: Action,
        reward: Reward,
        next_observation: Observation,
    ) -> None:
        self.long_term.append((observation, action, reward, next_observation))
        self._update_attention(action.skill_used or "default", reward.value)

    def store_episode(self, episode: List[Dict[str, Any]]) -> None:
        self.episodic.append(episode)

    def store_semantic(self, key: str, value: Any) -> None:
        self.semantic[key] = value

    def store_skill(self, skill: Skill) -> None:
        self.procedural[skill.skill_id] = skill

    def retrieve_short_term(self, n: int = 10) -> List[Observation]:
        return list(self.short_term)[-n:]

    def retrieve_experiences(self, n: int = 32) -> List[Tuple[Observation, Action, Reward, Observation]]:
        if len(self.long_term) < n:
            return list(self.long_term)
        indices = np.random.choice(len(self.long_term), n, replace=False)
        return [self.long_term[i] for i in indices]

    def retrieve_prioritized(self, n: int = 32) -> List[Tuple[Observation, Action, Reward, Observation]]:
        if len(self.long_term) == 0:
            return []

        priorities = []
        for exp in self.long_term:
            _, _, reward, _ = exp
            priorities.append(abs(reward.value) + 0.01)

        total = sum(priorities)
        probs = [p / total for p in priorities]

        indices = np.random.choice(len(self.long_term), min(n, len(self.long_term)), replace=False, p=probs)
        return [self.long_term[i] for i in indices]

    def retrieve_episodes(self, n: int = 5) -> List[List[Dict[str, Any]]]:
        if len(self.episodic) < n:
            return self.episodic
        return self.episodic[-n:]

    def retrieve_semantic(self, key: str) -> Optional[Any]:
        return self.semantic.get(key)

    def retrieve_skill(self, skill_id: str) -> Optional[Skill]:
        return self.procedural.get(skill_id)

    def _update_attention(self, key: str, reward: float) -> None:
        current = self.attention_weights.get(key, 0.5)
        self.attention_weights[key] = current + 0.1 * reward
        self.attention_weights[key] = max(0.0, min(1.0, self.attention_weights[key]))

    def get_attended_skills(self, top_k: int = 10) -> List[str]:
        sorted_skills = sorted(
            self.attention_weights.items(), key=lambda x: x[1], reverse=True
        )
        return [s[0] for s in sorted_skills[:top_k]]

    def size(self) -> Dict[str, int]:
        return {
            "short_term": len(self.short_term),
            "long_term": len(self.long_term),
            "episodic": len(self.episodic),
            "semantic": len(self.semantic),
            "procedural": len(self.procedural),
        }


class DecisionEngine:
    """决策引擎"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.epsilon = self.config.exploration_rate
        self.epsilon_min = self.config.min_exploration_rate
        self.epsilon_decay = self.config.exploration_decay
        self.policy = Policy()
        self.value_estimates: Dict[str, float] = {}
        self.logger = get_logger(f"{__name__}.DecisionEngine")

    def decide(
        self,
        observation: Observation,
        available_actions: List[ActionType],
        strategies: List[Strategy],
    ) -> Tuple[Action, Strategy]:
        best_strategy = self._select_strategy(observation, strategies)

        if np.random.random() < self.epsilon:
            action = self._explore(observation, available_actions)
        else:
            action = self._exploit(observation, available_actions, best_strategy)

        action.strategy_used = best_strategy.strategy_id
        return action, best_strategy

    def _select_strategy(self, observation: Observation, strategies: List[Strategy]) -> Strategy:
        if not strategies:
            return Strategy()

        scored = []
        for strategy in strategies:
            score = self._score_strategy(strategy, observation)
            scored.append((strategy, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def _score_strategy(self, strategy: Strategy, observation: Observation) -> float:
        perf_score = strategy.performance_score * 0.3
        adapt_score = strategy.adaptability_score * 0.2

        entropy_match = 0.0
        if observation.entropy_readings:
            avg_entropy = np.mean(list(observation.entropy_readings.values()))
            entropy_match = 1.0 - abs(strategy.entropy_level - avg_entropy)
        entropy_match *= 0.3

        risk_match = 0.5 * 0.2

        return perf_score + adapt_score + entropy_match + risk_match

    def _explore(self, observation: Observation, available_actions: List[ActionType]) -> Action:
        action_type = np.random.choice(available_actions)
        return Action(
            action_type=action_type,
            confidence=0.3 + 0.7 * np.random.random(),
            expected_outcome=np.random.randn() * 0.5,
            risk_assessment=np.random.random(),
        )

    def _exploit(
        self,
        observation: Observation,
        available_actions: List[ActionType],
        strategy: Strategy,
    ) -> Action:
        action_scores = {}
        for action in available_actions:
            key = f"{strategy.strategy_id}_{action.value}"
            action_scores[action] = self.value_estimates.get(key, 0.5)

        best_action = max(action_scores, key=action_scores.get)
        confidence = 0.5 + 0.5 * action_scores[best_action]

        return Action(
            action_type=best_action,
            confidence=min(1.0, confidence),
            expected_outcome=action_scores[best_action],
            risk_assessment=1.0 - confidence,
        )

    def update_value(self, strategy_id: str, action_type: str, reward: float) -> None:
        key = f"{strategy_id}_{action_type}"
        old_value = self.value_estimates.get(key, 0.0)
        self.value_estimates[key] = old_value + self.config.learning_rate * (reward - old_value)

    def decay_exploration(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def reset(self) -> None:
        self.epsilon = self.config.exploration_rate


class LearningSystem:
    """学习系统"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.learning_rate = self.config.learning_rate
        self.training_step = 0
        self.losses: List[float] = []
        self.rewards_history: List[float] = []
        self.logger = get_logger(f"{__name__}.LearningSystem")

    def learn_from_experience(
        self,
        experiences: List[Tuple[Observation, Action, Reward, Observation]],
    ) -> float:
        if not experiences:
            return 0.0

        total_loss = 0.0
        for obs, action, reward, next_obs in experiences:
            loss = self._update_step(obs, action, reward, next_obs)
            total_loss += loss
            self.training_step += 1

        avg_loss = total_loss / len(experiences)
        self.losses.append(avg_loss)

        total_reward = sum(r.value for _, _, r, _ in experiences)
        self.rewards_history.append(total_reward / len(experiences))

        return avg_loss

    def _update_step(
        self,
        observation: Observation,
        action: Action,
        reward: Reward,
        next_observation: Observation,
    ) -> float:
        current_value = reward.immediate_reward
        target = reward.immediate_reward + self.config.learning_rate * reward.delayed_reward
        loss = abs(target - current_value)
        return loss

    def update_strategy(
        self,
        strategy: Strategy,
        result: "StrategyResult",
    ) -> Strategy:
        if result.pnl > 0:
            strategy.performance_score = min(1.0, strategy.performance_score + 0.01)
        else:
            strategy.performance_score = max(0.0, strategy.performance_score - 0.01)

        if result.entropy_change != 0:
            strategy.adaptability_score = min(1.0, strategy.adaptability_score + 0.005)

        strategy.win_rate = (strategy.win_rate * strategy.total_trades + (1 if result.pnl > 0 else 0)) / (strategy.total_trades + 1) if hasattr(strategy, 'total_trades') else (1 if result.pnl > 0 else 0)

        return strategy

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "training_steps": self.training_step,
            "avg_loss": np.mean(self.losses[-100:]) if self.losses else 0.0,
            "avg_reward": np.mean(self.rewards_history[-100:]) if self.rewards_history else 0.0,
            "recent_rewards": self.rewards_history[-10:],
        }


class AgentBrain:
    """Agent大脑 - 整合记忆、决策和学习"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.memory = MemorySystem(self.config.memory_size)
        self.decision_engine = DecisionEngine(self.config)
        self.learning_system = LearningSystem(self.config)
        self.vector_machine = SkillVectorMachine(self.config.skill_vector_size)
        self.entropy_strategy = EntropyDrivenStrategy(self.vector_machine)
        self.adaptive_gen = AdaptiveStrategyGenerator()
        self.ensemble = MultiStrategyEnsemble()
        self.mind_state = np.zeros(self.config.mind_vector_size)
        self.logger = get_logger(f"{__name__}.AgentBrain")

    def perceive(self, observation: Observation) -> None:
        self.memory.store_short_term(observation)
        self._update_mind_state(observation)

    def decide(
        self,
        available_actions: List[ActionType],
        strategies: Optional[List[Strategy]] = None,
    ) -> Tuple[Action, Strategy]:
        if not strategies:
            strategies = self.ensemble.strategies

        if not strategies and self.memory.short_term:
            latest_obs = self.memory.short_term[-1]
            entropy = np.mean(list(latest_obs.entropy_readings.values())) if latest_obs.entropy_readings else 0.5
            new_strategy = self.entropy_strategy.generate_from_entropy(entropy)
            self.ensemble.add_strategy(new_strategy)
            strategies = [new_strategy]

        action, strategy = self.decision_engine.decide(
            self.memory.short_term[-1] if self.memory.short_term else Observation(),
            available_actions,
            strategies,
        )
        return action, strategy

    def learn(self, reward: Reward, next_observation: Observation) -> None:
        if len(self.memory.short_term) >= 2:
            prev_obs = self.memory.short_term[-2]
            action = Action()
            self.memory.store_experience(prev_obs, action, reward, next_observation)

        if len(self.memory.long_term) >= self.config.batch_size:
            experiences = self.memory.retrieve_prioritized(self.config.batch_size)
            loss = self.learning_system.learn_from_experience(experiences)
            self.decision_engine.decay_exploration()

    def _update_mind_state(self, observation: Observation) -> None:
        new_state = np.random.randn(self.config.mind_vector_size) * 0.01
        self.mind_state = (1 - self.config.adaptation_rate) * self.mind_state + self.config.adaptation_rate * new_state

        norm = np.linalg.norm(self.mind_state)
        if norm > 0:
            self.mind_state /= norm

    def add_strategy(self, strategy: Strategy, weight: float = 1.0) -> None:
        self.ensemble.add_strategy(strategy, weight)
        self.adaptive_gen.add_base_strategy(strategy)

    def get_mind_state(self) -> np.ndarray:
        return self.mind_state.copy()

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "memory": self.memory.size(),
            "learning": self.learning_system.get_statistics(),
            "exploration_rate": self.decision_engine.epsilon,
            "strategies_count": len(self.ensemble.strategies),
            "mind_state_norm": float(np.linalg.norm(self.mind_state)),
        }


class StrategyAgent:
    """策略Agent - 自主决策、学习和适应的智能体"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.agent = Agent(
            agent_id=str(__import__('uuid').uuid4()),
            name=self.config.agent_name,
            initial_balance=self.config.initial_balance,
            balance=self.config.initial_balance,
            risk_profile=self.config.risk_profile,
            learning_rate=self.config.learning_rate,
            exploration_rate=self.config.exploration_rate,
            entropy_bonus=0.01,
            adaptation_rate=self.config.adaptation_rate,
            creativity_level=self.config.creativity_level,
        )
        self.brain = AgentBrain(self.config)
        self.available_actions = list(ActionType)
        self.step_count = 0
        self.episode_count = 0
        self.logger = get_logger(f"{__name__}.StrategyAgent")

    def observe(self, observation: Observation) -> None:
        self.agent.state = AgentState.OBSERVING
        self.brain.perceive(observation)
        self.agent.current_observation = observation
        self.step_count += 1

    def think(self) -> Tuple[Action, Strategy]:
        self.agent.state = AgentState.THINKING
        action, strategy = self.brain.decide(self.available_actions)
        self.agent.last_action = action
        self.agent.current_strategy = strategy.strategy_id
        return action, strategy

    def act(self, action: Action) -> Action:
        self.agent.state = AgentState.ACTING
        self.agent.last_action = action
        return action

    def learn(self, reward: Reward, next_observation: Observation) -> None:
        self.agent.state = AgentState.LEARNING
        self.agent.last_reward = reward
        self.brain.learn(reward, next_observation)
        self.agent.total_pnl += reward.value
        self.agent.win_rate = (self.agent.win_rate * self.agent.total_trades + (1 if reward.value > 0 else 0)) / (self.agent.total_trades + 1) if self.agent.total_trades > 0 else (1 if reward.value > 0 else 0)
        self.agent.total_trades += 1

    def step(self, observation: Observation) -> Tuple[Action, Strategy, Reward]:
        self.observe(observation)
        action, strategy = self.think()
        self.act(action)

        reward = Reward(
            value=0.0,
            immediate_reward=0.0,
            delayed_reward=0.0,
        )
        self.learn(reward, observation)

        return action, strategy, reward

    def adapt(self) -> None:
        self.agent.state = AgentState.ADAPTING
        self.logger.info(f"Agent adapting at step {self.step_count}")

    def add_strategy(self, strategy: Strategy, weight: float = 1.0) -> None:
        self.brain.add_strategy(strategy, weight)
        self.agent.strategies.append(strategy.strategy_id)

    def get_state(self) -> AgentState:
        return self.agent.state

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "step": self.step_count,
            "episode": self.episode_count,
            "agent": {
                "balance": self.agent.balance,
                "total_pnl": self.agent.total_pnl,
                "total_trades": self.agent.total_trades,
                "win_rate": self.agent.win_rate,
                "state": self.agent.state.value,
            },
            "brain": self.brain.get_statistics(),
        }

    def reset(self) -> None:
        self.agent.balance = self.config.initial_balance
        self.agent.total_pnl = 0.0
        self.agent.total_trades = 0
        self.agent.win_rate = 0.0
        self.agent.state = AgentState.IDLE
        self.step_count = 0
        self.brain.decision_engine.reset()
        self.logger.info("Agent reset")
