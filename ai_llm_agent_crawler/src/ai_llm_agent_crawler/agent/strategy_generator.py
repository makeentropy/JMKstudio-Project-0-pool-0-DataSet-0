"""
策略生成模块

提供熵驱动策略、自适应策略、多策略集成、无限细腻策略生成等功能。
"""

import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.agent.models import (
    ActionType,
    Observation,
    RiskProfile,
    Strategy,
    StrategyConfig,
    StrategyType,
)
from ai_llm_agent_crawler.agent.skill_vector_machine import SkillVectorMachine
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class StrategyGenerator:
    """策略生成器基类"""

    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()
        self._strategies: Dict[str, Strategy] = {}
        self.logger = get_logger(f"{__name__}.StrategyGenerator")

    def generate(self, observation: Optional[Observation] = None) -> Strategy:
        strategy = Strategy(
            strategy_id=str(uuid.uuid4()),
            name=f"strategy_{len(self._strategies):04d}",
            strategy_type=self.config.strategy_type,
            risk_profile=self.config.risk_profile,
            parameters=self.config.parameters.copy(),
            entropy_level=0.5,
        )
        self._strategies[strategy.strategy_id] = strategy
        return strategy

    def evaluate(self, strategy: Strategy, observation: Observation) -> Strategy:
        strategy.performance_score = 0.5 + 0.5 * np.random.random()
        strategy.adaptability_score = 0.5 + 0.5 * np.random.random()
        strategy.updated_at = np.datetime64('now').astype(datetime) if False else __import__('datetime').datetime.now()
        return strategy

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[Strategy]:
        return list(self._strategies.values())


class EntropyDrivenStrategy:
    """熵驱动策略生成器"""

    def __init__(self, vector_machine: Optional[SkillVectorMachine] = None):
        self.vector_machine = vector_machine or SkillVectorMachine()
        self._entropy_history: List[float] = []
        self._strategy_cache: Dict[float, Strategy] = {}
        self.logger = get_logger(f"{__name__}.EntropyDrivenStrategy")

    def generate_from_entropy(self, entropy_value: float, market_state: Optional[Dict[str, Any]] = None) -> Strategy:
        entropy_value = max(0.0, min(1.0, entropy_value))

        strategy_type = self._select_strategy_type(entropy_value)
        risk_profile = self._select_risk_profile(entropy_value)

        strategy = Strategy(
            strategy_id=str(uuid.uuid4()),
            name=f"entropy_strategy_{entropy_value:.3f}",
            strategy_type=strategy_type,
            description=f"Strategy generated for entropy level {entropy_value:.3f}",
            risk_profile=risk_profile,
            entropy_level=entropy_value,
            parameters=self._generate_parameters(entropy_value, market_state),
        )

        strategy_vector = self._generate_strategy_vector(entropy_value, strategy_type)
        strategy.strategy_vector = strategy_vector.tolist()

        self._entropy_history.append(entropy_value)
        self.logger.info(f"Generated entropy-driven strategy at level {entropy_value:.3f}")
        return strategy

    def _select_strategy_type(self, entropy: float) -> StrategyType:
        if entropy < 0.2:
            return StrategyType.TREND_FOLLOWING
        elif entropy < 0.4:
            return StrategyType.MOMENTUM
        elif entropy < 0.6:
            return StrategyType.MEAN_REVERSION
        elif entropy < 0.8:
            return StrategyType.STATISTICAL_ARBITRAGE
        else:
            return StrategyType.EXPLORATORY

    def _select_risk_profile(self, entropy: float) -> RiskProfile:
        if entropy < 0.2:
            return RiskProfile.CONSERVATIVE
        elif entropy < 0.4:
            return RiskProfile.MODERATE
        elif entropy < 0.6:
            return RiskProfile.AGGRESSIVE
        else:
            return RiskProfile.SPECULATIVE

    def _generate_parameters(self, entropy: float, market_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "entropy_level": entropy,
            "lookback_period": int(20 + 80 * (1 - entropy)),
            "position_size": 0.1 + 0.2 * entropy,
            "stop_loss": 0.02 + 0.08 * (1 - entropy),
            "take_profit": 0.04 + 0.16 * entropy,
            "rebalance_frequency": int(1 + 9 * entropy),
            "exploration_rate": 0.01 + 0.19 * entropy,
            "adaptation_rate": 0.1 + 0.4 * entropy,
            "confidence_threshold": 0.9 - 0.4 * entropy,
            "leverage": 1.0 + 4.0 * entropy,
        }

    def _generate_strategy_vector(self, entropy: float, strategy_type: StrategyType) -> np.ndarray:
        dims = 128
        base = np.zeros(dims)

        type_hash = hash(strategy_type.value) % (2**32)
        rng = np.random.RandomState(type_hash)
        type_signal = rng.randn(dims) * 0.5

        entropy_signal = np.sin(np.linspace(0, entropy * 4 * np.pi, dims)) * 0.3

        combined = type_signal + entropy_signal
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined /= norm
        return combined

    def adapt_strategy(self, strategy: Strategy, new_entropy: float) -> Strategy:
        old_entropy = strategy.entropy_level
        blend_factor = min(1.0, abs(new_entropy - old_entropy) * 2)

        new_strategy = self.generate_from_entropy(new_entropy)
        new_strategy.strategy_id = strategy.strategy_id
        new_strategy.name = strategy.name
        new_strategy.version = self._increment_version(strategy.version)
        new_strategy.parent_strategy = strategy.strategy_id

        return new_strategy

    def _increment_version(self, version: str) -> str:
        parts = version.split(".")
        if len(parts) == 3:
            major, minor, patch = parts
            patch = str(int(patch) + 1)
            return f"{major}.{minor}.{patch}"
        return "1.0.1"

    def get_entropy_trend(self, window: int = 20) -> float:
        if len(self._entropy_history) < 2:
            return 0.0
        recent = self._entropy_history[-window:]
        if len(recent) < 2:
            return 0.0
        x = np.arange(len(recent))
        slope, _ = np.polyfit(x, recent, 1)
        return float(slope)


class AdaptiveStrategyGenerator:
    """自适应策略生成器"""

    def __init__(self, base_strategies: Optional[List[Strategy]] = None):
        self.base_strategies = base_strategies or []
        self._performance_history: Dict[str, List[float]] = {}
        self._adaptation_count: Dict[str, int] = {}
        self.logger = get_logger(f"{__name__}.AdaptiveStrategyGenerator")

    def add_base_strategy(self, strategy: Strategy) -> None:
        self.base_strategies.append(strategy)
        self._performance_history[strategy.strategy_id] = []
        self._adaptation_count[strategy.strategy_id] = 0

    def select_best_strategy(self, observation: Observation) -> Optional[Strategy]:
        if not self.base_strategies:
            return None

        scored = []
        for strategy in self.base_strategies:
            score = self._score_strategy(strategy, observation)
            scored.append((strategy, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None

    def _score_strategy(self, strategy: Strategy, observation: Observation) -> float:
        perf_weight = 0.4
        adapt_weight = 0.3
        match_weight = 0.3

        perf_score = strategy.performance_score

        adapt_score = strategy.adaptability_score

        match_score = 0.5
        if observation.entropy_readings:
            market_entropy = np.mean(list(observation.entropy_readings.values()))
            match_score = 1.0 - abs(strategy.entropy_level - market_entropy)

        return perf_weight * perf_score + adapt_weight * adapt_score + match_weight * match_score

    def adapt_strategy(self, strategy: Strategy, observation: Observation, reward: float) -> Strategy:
        strategy_id = strategy.strategy_id
        if strategy_id not in self._performance_history:
            self._performance_history[strategy_id] = []

        self._performance_history[strategy_id].append(reward)
        history = self._performance_history[strategy_id]

        if len(history) > 10:
            recent = history[-10:]
            perf_trend = np.mean(recent[-5:]) - np.mean(recent[:5])

            if perf_trend < -0.1:
                strategy.adaptability_score = max(0.0, min(1.0, strategy.adaptability_score + 0.1))
                strategy.parameters["exploration_rate"] = min(
                    0.5, strategy.parameters.get("exploration_rate", 0.1) + 0.05
                )
                self._adaptation_count[strategy_id] = self._adaptation_count.get(strategy_id, 0) + 1
                self.logger.info(f"Adapted strategy {strategy_id} (adaptation #{self._adaptation_count[strategy_id]})")

        strategy.updated_at = __import__('datetime').datetime.now()
        return strategy

    def generate_adapted_variant(
        self,
        base_strategy: Strategy,
        observation: Observation,
        adaptation_rate: float = 0.1,
    ) -> Strategy:
        new_strategy = Strategy(
            strategy_id=str(uuid.uuid4()),
            name=f"{base_strategy.name}_v{self._adaptation_count.get(base_strategy.strategy_id, 0) + 1}",
            strategy_type=base_strategy.strategy_type,
            description=f"Adapted from {base_strategy.strategy_id}",
            risk_profile=base_strategy.risk_profile,
            parameters=base_strategy.parameters.copy(),
            parent_strategy=base_strategy.strategy_id,
        )

        for key in new_strategy.parameters:
            if isinstance(new_strategy.parameters[key], (int, float)):
                change = np.random.randn() * adaptation_rate * 0.1
                new_strategy.parameters[key] = max(
                    0.0, new_strategy.parameters[key] * (1 + change)
                )

        new_strategy.entropy_level = max(
            0.0, min(1.0, base_strategy.entropy_level + np.random.randn() * 0.1)
        )
        new_strategy.strategy_vector = list(
            np.array(base_strategy.strategy_vector) + np.random.randn(len(base_strategy.strategy_vector)) * 0.05
        ) if base_strategy.strategy_vector else []

        self.logger.info(f"Generated adapted variant of {base_strategy.strategy_id}")
        return new_strategy


class MultiStrategyEnsemble:
    """多策略集成"""

    def __init__(self, strategies: Optional[List[Strategy]] = None):
        self.strategies = strategies or []
        self.weights: List[float] = []
        self._normalize_weights()
        self.logger = get_logger(f"{__name__}.MultiStrategyEnsemble")

    def add_strategy(self, strategy: Strategy, weight: float = 1.0) -> None:
        self.strategies.append(strategy)
        self.weights.append(weight)
        self._normalize_weights()

    def remove_strategy(self, strategy_id: str) -> bool:
        for i, s in enumerate(self.strategies):
            if s.strategy_id == strategy_id:
                self.strategies.pop(i)
                self.weights.pop(i)
                self._normalize_weights()
                return True
        return False

    def _normalize_weights(self) -> None:
        total = sum(self.weights)
        if total > 0:
            self.weights = [w / total for w in self.weights]

    def update_weights_from_performance(self, performance_scores: List[float]) -> None:
        if len(performance_scores) != len(self.strategies):
            return

        for i, score in enumerate(performance_scores):
            self.weights[i] = max(0.01, score)
        self._normalize_weights()

    def ensemble_action(self, actions: List[ActionType]) -> ActionType:
        if not actions:
            return ActionType.HOLD

        vote_counts: Dict[str, float] = {}
        for i, action in enumerate(actions):
            if i < len(self.weights):
                vote_counts[action.value] = vote_counts.get(action.value, 0) + self.weights[i]

        if not vote_counts:
            return ActionType.HOLD

        best_action = max(vote_counts, key=vote_counts.get)
        return ActionType(best_action)

    def ensemble_parameters(self) -> Dict[str, Any]:
        if not self.strategies:
            return {}

        all_params = set()
        for s in self.strategies:
            all_params.update(s.parameters.keys())

        ensemble_params = {}
        for key in all_params:
            values = []
            weights = []
            for i, s in enumerate(self.strategies):
                if key in s.parameters and isinstance(s.parameters[key], (int, float)):
                    values.append(s.parameters[key])
                    weights.append(self.weights[i] if i < len(self.weights) else 1.0)

            if values:
                total_weight = sum(weights)
                if total_weight > 0:
                    ensemble_params[key] = sum(v * w for v, w in zip(values, weights)) / total_weight

        return ensemble_params

    def diversity_score(self) -> float:
        if len(self.strategies) < 2:
            return 0.0

        vectors = []
        for s in self.strategies:
            if s.strategy_vector:
                vectors.append(np.array(s.strategy_vector))

        if len(vectors) < 2:
            return 0.0

        total_sim = 0.0
        count = 0
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                sim = np.dot(vectors[i], vectors[j]) / (
                    np.linalg.norm(vectors[i]) * np.linalg.norm(vectors[j])
                )
                total_sim += sim
                count += 1

        avg_sim = total_sim / count if count > 0 else 1.0
        return 1.0 - avg_sim


class InfiniteStrategyGenerator:
    """无限细腻策略生成器"""

    def __init__(
        self,
        vector_machine: Optional[SkillVectorMachine] = None,
        base_strategies: Optional[List[Strategy]] = None,
    ):
        self.vector_machine = vector_machine or SkillVectorMachine()
        self.base_strategies = base_strategies or []
        self._generated_count = 0
        self._strategy_space: Dict[str, Strategy] = {}
        self.logger = get_logger(f"{__name__}.InfiniteStrategyGenerator")

    def generate_continuous_variation(
        self,
        base_strategy: Strategy,
        parameter: str,
        n_variations: int = 100,
        range_factor: float = 2.0,
    ) -> List[Strategy]:
        if parameter not in base_strategy.parameters:
            return []

        base_value = base_strategy.parameters[parameter]
        min_val = base_value / range_factor
        max_val = base_value * range_factor

        variations = []
        for i in range(n_variations):
            alpha = i / max(1, n_variations - 1)
            new_value = min_val + alpha * (max_val - min_val)

            strategy = Strategy(
                strategy_id=str(uuid.uuid4()),
                name=f"{base_strategy.name}_{parameter}_{i:04d}",
                strategy_type=base_strategy.strategy_type,
                description=f"Variation of {base_strategy.strategy_id} with {parameter}={new_value:.4f}",
                risk_profile=base_strategy.risk_profile,
                parameters=base_strategy.parameters.copy(),
                parent_strategy=base_strategy.strategy_id,
            )
            strategy.parameters[parameter] = new_value
            strategy.entropy_level = min(1.0, base_strategy.entropy_level + (alpha - 0.5) * 0.2)
            variations.append(strategy)
            self._generated_count += 1

        self.logger.info(f"Generated {n_variations} continuous variations for {parameter}")
        return variations

    def generate_parameter_sweep(
        self,
        base_strategy: Strategy,
        parameters: List[str],
        n_per_param: int = 10,
    ) -> List[Strategy]:
        strategies = [base_strategy]

        for param in parameters:
            new_strategies = []
            for s in strategies:
                variations = self.generate_continuous_variation(s, param, n_per_param)
                new_strategies.extend(variations)
            strategies = new_strategies

        return strategies

    def generate_in_entropy_dimension(
        self,
        entropy_levels: int = 100,
    ) -> List[Strategy]:
        entropy_gen = EntropyDrivenStrategy(self.vector_machine)
        strategies = []

        for i in range(entropy_levels):
            entropy = i / max(1, entropy_levels - 1)
            strategy = entropy_gen.generate_from_entropy(entropy)
            strategies.append(strategy)
            self._strategy_space[strategy.strategy_id] = strategy

        self._generated_count += entropy_levels
        self.logger.info(f"Generated {entropy_levels} strategies across entropy dimension")
        return strategies

    def generate_multi_dimensional_grid(
        self,
        dimensions: Dict[str, Tuple[float, float]],
        steps_per_dim: int = 10,
    ) -> List[Strategy]:
        dim_names = list(dimensions.keys())
        n_dims = len(dim_names)

        if n_dims == 0:
            return []

        ranges = [np.linspace(dimensions[d][0], dimensions[d][1], steps_per_dim) for d in dim_names]
        grids = np.meshgrid(*ranges)
        grid_points = np.column_stack([g.flatten() for g in grids])

        strategies = []
        for point in grid_points:
            params = {dim_names[i]: float(point[i]) for i in range(n_dims)}
            entropy = np.mean(point) if n_dims > 0 else 0.5

            strategy = Strategy(
                strategy_id=str(uuid.uuid4()),
                name=f"grid_strategy_{self._generated_count:06d}",
                strategy_type=StrategyType.ADAPTIVE,
                description=f"Strategy at grid point {list(point)}",
                risk_profile=RiskProfile.MODERATE,
                parameters=params,
                entropy_level=max(0.0, min(1.0, entropy)),
            )
            strategies.append(strategy)
            self._generated_count += 1

        self.logger.info(f"Generated {len(strategies)} strategies in {n_dims}-dimensional grid")
        return strategies

    def generate_random_walk(
        self,
        start_strategy: Strategy,
        n_steps: int = 1000,
        step_size: float = 0.01,
    ) -> List[Strategy]:
        strategies = [start_strategy]
        current = start_strategy

        for step in range(n_steps):
            new_params = current.parameters.copy()
            for key in new_params:
                if isinstance(new_params[key], (int, float)):
                    change = np.random.randn() * step_size
                    new_params[key] = max(0.0001, new_params[key] * (1 + change))

            new_strategy = Strategy(
                strategy_id=str(uuid.uuid4()),
                name=f"walk_strategy_{step:06d}",
                strategy_type=current.strategy_type,
                description=f"Random walk step {step} from {current.strategy_id}",
                risk_profile=current.risk_profile,
                parameters=new_params,
                parent_strategy=current.strategy_id,
                entropy_level=max(0.0, min(1.0, current.entropy_level + np.random.randn() * 0.01)),
            )
            strategies.append(new_strategy)
            current = new_strategy
            self._generated_count += 1

        self.logger.info(f"Generated random walk of {n_steps} strategies")
        return strategies

    @property
    def generated_count(self) -> int:
        return self._generated_count
