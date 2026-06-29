"""
向量机解决方案模块

整合所有模块，提供完整的熵驱动策略生成和向量机解决方案。
包括：维度空间映射、Mind向量生成、策略向量机、Agent Skill向量机等。
"""

import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.agent.models import (
    ActionType,
    AgentConfig,
    Observation,
    Strategy,
    StrategyType,
)
from ai_llm_agent_crawler.agent.skill_vector_machine import (
    SkillComposer,
    SkillRanker,
    SkillSearchEngine,
    SkillVectorMachine,
    VectorSkillGenerator,
)
from ai_llm_agent_crawler.agent.strategy_agent import StrategyAgent
from ai_llm_agent_crawler.agent.strategy_generator import (
    AdaptiveStrategyGenerator,
    EntropyDrivenStrategy,
    InfiniteStrategyGenerator,
    MultiStrategyEnsemble,
)
from ai_llm_agent_crawler.mind.models import (
    MindDataset,
    MindVector,
)
from ai_llm_agent_crawler.mind.pool import (
    DataPool,
    PoolIndex,
)
from ai_llm_agent_crawler.terrain.entropy import (
    InformationEntropy,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class DimensionSpaceMapper:
    """维度空间映射器"""

    def __init__(self, input_dim: int = 128, output_dim: int = 256):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.projection_matrix = self._initialize_projection()
        self.dimension_labels: Dict[str, int] = {}
        self.logger = get_logger(f"{__name__}.DimensionSpaceMapper")

    def _initialize_projection(self) -> np.ndarray:
        matrix = np.random.randn(self.input_dim, self.output_dim)
        q, r = np.linalg.qr(matrix)
        return q[:, :self.output_dim]

    def map_to_high_dim(self, vector: np.ndarray) -> np.ndarray:
        if len(vector) != self.input_dim:
            vector = np.pad(vector, (0, max(0, self.input_dim - len(vector))))[:self.input_dim]
        return vector @ self.projection_matrix

    def map_to_low_dim(self, vector: np.ndarray, target_dim: int = 2) -> np.ndarray:
        if len(vector) < target_dim:
            return np.pad(vector, (0, target_dim - len(vector)))

        if len(vector) <= 2:
            return vector[:target_dim]

        u, s, vh = np.linalg.svd(vector.reshape(1, -1), full_matrices=False)
        return vh[0, :target_dim]

    def project_terrain_to_mind(self, terrain_data: np.ndarray) -> MindVector:
        flat = terrain_data.flatten()
        vector = self.map_to_high_dim(flat[:self.input_dim])
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        mv = MindVector(
            vector_id=str(uuid.uuid4()),
            dimensions=self.output_dim,
            vector_type="spatial",
        )
        mv.from_numpy(vector)
        return mv

    def project_strategy_to_skill(self, strategy_vector: np.ndarray) -> np.ndarray:
        return self.map_to_high_dim(strategy_vector[:self.input_dim])

    def add_dimension_label(self, label: str, index: int) -> None:
        self.dimension_labels[label] = index

    def get_dimension_vector(self, label: str) -> Optional[np.ndarray]:
        if label not in self.dimension_labels:
            return None
        idx = self.dimension_labels[label]
        vec = np.zeros(self.output_dim)
        vec[idx] = 1.0
        return vec


class MindVectorGenerator:
    """Mind向量生成器"""

    def __init__(self, dimensions: int = 512):
        self.dimensions = dimensions
        self._basis_vectors: Dict[str, np.ndarray] = {}
        self._initialize_basis()
        self.logger = get_logger(f"{__name__}.MindVectorGenerator")

    def _initialize_basis(self) -> None:
        basis_concepts = [
            "risk", "return", "volatility", "momentum", "mean_reversion",
            "trend", "liquidity", "sentiment", "fundamental", "technical",
            "entropy", "information", "complexity", "adaptation", "exploration",
            "exploitation", "diversification", "concentration", "efficiency", "robustness",
        ]

        for concept in basis_concepts:
            vector = np.random.randn(self.dimensions)
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector /= norm
            self._basis_vectors[concept] = vector

    def generate_from_concepts(
        self,
        concept_weights: Dict[str, float],
    ) -> MindVector:
        vector = np.zeros(self.dimensions)

        for concept, weight in concept_weights.items():
            if concept in self._basis_vectors:
                vector += weight * self._basis_vectors[concept]

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        mv = MindVector(
            vector_id=str(uuid.uuid4()),
            dimensions=self.dimensions,
            vector_type="semantic",
            metadata={"concepts": list(concept_weights.keys())},
        )
        mv.from_numpy(vector)
        return mv

    def generate_from_entropy(self, entropy_value: float, entropy_type: str = "shannon") -> MindVector:
        entropy_value = max(0.0, min(1.0, entropy_value))

        base = np.zeros(self.dimensions)
        for i in range(self.dimensions):
            phase = (i / self.dimensions) * 2 * np.pi * entropy_value * 10
            base[i] = np.sin(phase + entropy_value * np.pi)

        noise = np.random.randn(self.dimensions) * (1 - entropy_value) * 0.1
        vector = base + noise

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        mv = MindVector(
            vector_id=str(uuid.uuid4()),
            dimensions=self.dimensions,
            vector_type="entropy",
            metadata={"entropy_type": entropy_type, "entropy_value": entropy_value},
        )
        mv.from_numpy(vector)
        return mv

    def generate_principle_vector(self, principle: str) -> MindVector:
        vector = np.zeros(self.dimensions)

        h = hash(principle) & 0xFFFFFFFF
        rng = np.random.RandomState(h)
        random_vec = rng.randn(self.dimensions)

        chars = [ord(c) for c in principle]
        for i in range(min(len(chars) * 10, self.dimensions)):
            char_idx = i // 10
            bit_idx = i % 10
            if char_idx < len(chars):
                char_val = chars[char_idx]
                if (char_val >> bit_idx) & 1:
                    vector[i] = 1.0

        combined = 0.5 * vector + 0.5 * random_vec
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined /= norm

        mv = MindVector(
            vector_id=str(uuid.uuid4()),
            dimensions=self.dimensions,
            vector_type="abstract",
            metadata={"principle": principle},
        )
        mv.from_numpy(combined)
        return mv

    def generate_dataset_vectors(self, dataset: MindDataset) -> List[MindVector]:
        vectors = []
        for sample in dataset.samples:
            vec = self.generate_from_concepts(
                {"information": sample.get("information_content", 0.5)}
            )
            vectors.append(vec)
        return vectors

    def interpolate(self, vector_a: MindVector, vector_b: MindVector, alpha: float) -> MindVector:
        va = vector_a.to_numpy()
        vb = vector_b.to_numpy()
        interpolated = (1 - alpha) * va + alpha * vb
        norm = np.linalg.norm(interpolated)
        if norm > 0:
            interpolated /= norm

        mv = MindVector(
            vector_id=str(uuid.uuid4()),
            dimensions=self.dimensions,
            vector_type="semantic",
            metadata={"alpha": alpha},
        )
        mv.from_numpy(interpolated)
        return mv

    def analogy(self, a: MindVector, b: MindVector, c: MindVector) -> MindVector:
        va = a.to_numpy()
        vb = b.to_numpy()
        vc = c.to_numpy()

        result = vb - va + vc
        norm = np.linalg.norm(result)
        if norm > 0:
            result /= norm

        mv = MindVector(
            vector_id=str(uuid.uuid4()),
            dimensions=self.dimensions,
            vector_type="abstract",
        )
        mv.from_numpy(result)
        return mv

    def get_basis_concepts(self) -> List[str]:
        return list(self._basis_vectors.keys())


class StrategyVectorMachine:
    """策略向量机"""

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions
        self.strategy_vectors: Dict[str, np.ndarray] = {}
        self.skill_machine = SkillVectorMachine(dimensions)
        self.composer = SkillComposer(self.skill_machine)
        self.search_engine = SkillSearchEngine(self.skill_machine)
        self.ranker = SkillRanker(self.skill_machine)
        self.generator = VectorSkillGenerator(self.skill_machine)
        self.logger = get_logger(f"{__name__}.StrategyVectorMachine")

    def encode_strategy(self, strategy: Strategy) -> np.ndarray:
        if strategy.strategy_vector and len(strategy.strategy_vector) == self.dimensions:
            vec = np.array(strategy.strategy_vector)
        else:
            vec = self._generate_strategy_vector(strategy)
            strategy.strategy_vector = vec.tolist()

        self.strategy_vectors[strategy.strategy_id] = vec
        return vec

    def _generate_strategy_vector(self, strategy: Strategy) -> np.ndarray:
        base = np.zeros(self.dimensions)

        type_hash = hash(strategy.strategy_type.value) & 0xFFFFFFFF
        rng = np.random.RandomState(type_hash)
        type_vec = rng.randn(self.dimensions) * 0.4

        entropy_signal = np.sin(
            np.linspace(0, strategy.entropy_level * 4 * np.pi, self.dimensions)
        ) * 0.3

        param_vector = np.zeros(self.dimensions)
        if strategy.parameters:
            for i, (key, value) in enumerate(strategy.parameters.items()):
                idx = i % self.dimensions
                if isinstance(value, (int, float)):
                    param_vector[idx] = float(value) / 100.0

        combined = type_vec + entropy_signal + param_vector * 0.3
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined /= norm
        return combined

    def similarity(self, strategy_a: str, strategy_b: str) -> float:
        va = self.strategy_vectors.get(strategy_a)
        vb = self.strategy_vectors.get(strategy_b)
        if va is None or vb is None:
            return 0.0
        return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))

    def find_similar_strategies(
        self,
        query_strategy: str,
        candidates: List[str],
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        vq = self.strategy_vectors.get(query_strategy)
        if vq is None:
            return []

        results = []
        for sid in candidates:
            vs = self.strategy_vectors.get(sid)
            if vs is not None:
                sim = float(np.dot(vq, vs) / (np.linalg.norm(vq) * np.linalg.norm(vs)))
                results.append((sid, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def blend_strategies(self, strategy_ids: List[str], weights: Optional[List[float]] = None) -> np.ndarray:
        vectors = []
        for sid in strategy_ids:
            v = self.strategy_vectors.get(sid)
            if v is not None:
                vectors.append(v)

        if not vectors:
            return np.zeros(self.dimensions)

        if weights is None:
            weights = [1.0 / len(vectors)] * len(vectors)

        combined = np.zeros(self.dimensions)
        for vec, w in zip(vectors, weights):
            combined += w * vec

        norm = np.linalg.norm(combined)
        if norm > 0:
            combined /= norm
        return combined

    def generate_strategy_from_vector(
        self,
        vector: np.ndarray,
        name: str = "vector_generated_strategy",
    ) -> Strategy:
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        entropy = self._extract_entropy_from_vector(vector)
        strategy_type = self._extract_type_from_vector(vector)

        strategy = Strategy(
            strategy_id=str(uuid.uuid4()),
            name=name,
            strategy_type=strategy_type,
            description="Strategy generated from vector space",
            entropy_level=entropy,
            strategy_vector=vector.tolist(),
        )

        self.strategy_vectors[strategy.strategy_id] = vector
        return strategy

    def _extract_entropy_from_vector(self, vector: np.ndarray) -> float:
        fft = np.fft.fft(vector)
        power = np.abs(fft) ** 2
        total = np.sum(power)
        if total == 0:
            return 0.5
        prob = power / total
        entropy = -np.sum(prob * np.log2(prob + 1e-10))
        max_entropy = np.log2(len(vector))
        return float(min(1.0, entropy / max_entropy))

    def _extract_type_from_vector(self, vector: np.ndarray) -> StrategyType:
        types = list(StrategyType)
        max_sim = -1
        best_type = types[0]

        for st in types:
            type_hash = hash(st.value) & 0xFFFFFFFF
            rng = np.random.RandomState(type_hash)
            type_vec = rng.randn(self.dimensions)
            norm = np.linalg.norm(type_vec)
            if norm > 0:
                type_vec /= norm

            sim = float(np.dot(vector, type_vec))
            if sim > max_sim:
                max_sim = sim
                best_type = st

        return best_type


class EntropyVectorMachine:
    """熵向量机 - 制造熵的向量机"""

    def __init__(self, dimensions: int = 512):
        self.dimensions = dimensions
        self.entropy_generators = {
            "shannon": InformationEntropy(),
        }
        self._entropy_vectors: Dict[float, np.ndarray] = {}
        self.logger = get_logger(f"{__name__}.EntropyVectorMachine")

    def entropy_to_vector(self, entropy_value: float, entropy_type: str = "shannon") -> np.ndarray:
        entropy_value = round(max(0.0, min(1.0, entropy_value)), 6)

        if entropy_value in self._entropy_vectors:
            return self._entropy_vectors[entropy_value].copy()

        vector = np.zeros(self.dimensions)

        for i in range(self.dimensions):
            position = i / self.dimensions
            frequency = 1 + entropy_value * 50
            phase = position * frequency * 2 * np.pi
            vector[i] = np.sin(phase) * (0.5 + 0.5 * entropy_value)

        noise = np.random.randn(self.dimensions) * 0.1 * entropy_value
        vector += noise

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        self._entropy_vectors[entropy_value] = vector
        return vector.copy()

    def vector_to_entropy(self, vector: np.ndarray) -> float:
        fft = np.fft.fft(vector)
        power_spectrum = np.abs(fft) ** 2

        total_power = np.sum(power_spectrum)
        if total_power == 0:
            return 0.5

        normalized = power_spectrum / total_power
        entropy = -np.sum(normalized * np.log2(normalized + 1e-10))
        max_entropy = np.log2(len(vector))

        return float(min(1.0, entropy / max_entropy))

    def increase_entropy(self, vector: np.ndarray, amount: float = 0.1) -> np.ndarray:
        current_entropy = self.vector_to_entropy(vector)
        target_entropy = min(1.0, current_entropy + amount)

        target_vector = self.entropy_to_vector(target_entropy)

        alpha = amount / max(0.001, target_entropy - current_entropy + 1e-10)
        alpha = min(1.0, alpha)

        result = (1 - alpha) * vector + alpha * target_vector
        norm = np.linalg.norm(result)
        if norm > 0:
            result /= norm

        return result

    def decrease_entropy(self, vector: np.ndarray, amount: float = 0.1) -> np.ndarray:
        current_entropy = self.vector_to_entropy(vector)
        target_entropy = max(0.0, current_entropy - amount)

        target_vector = self.entropy_to_vector(target_entropy)

        alpha = amount / max(0.001, current_entropy - target_entropy + 1e-10)
        alpha = min(1.0, alpha)

        result = (1 - alpha) * vector + alpha * target_vector
        norm = np.linalg.norm(result)
        if norm > 0:
            result /= norm

        return result

    def make_entropy(
        self,
        source_vector: np.ndarray,
        target_entropy: float,
        precision: float = 0.01,
        max_iterations: int = 100,
    ) -> Tuple[np.ndarray, float]:
        current = source_vector.copy()
        current_entropy = self.vector_to_entropy(current)

        for _ in range(max_iterations):
            diff = target_entropy - current_entropy

            if abs(diff) < precision:
                break

            step = abs(diff) * 0.5
            if diff > 0:
                current = self.increase_entropy(current, step)
            else:
                current = self.decrease_entropy(current, step)

            current_entropy = self.vector_to_entropy(current)

        return current, current_entropy

    def generate_entropy_spectrum(self, n_levels: int = 100) -> List[np.ndarray]:
        vectors = []
        for i in range(n_levels):
            entropy = i / max(1, n_levels - 1)
            vec = self.entropy_to_vector(entropy)
            vectors.append(vec)
        return vectors

    def entropy_transfer(
        self,
        source: np.ndarray,
        target: np.ndarray,
        transfer_rate: float = 0.1,
    ) -> Tuple[np.ndarray, np.ndarray]:
        source_entropy = self.vector_to_entropy(source)
        target_entropy = self.vector_to_entropy(target)

        diff = source_entropy - target_entropy
        transfer_amount = diff * transfer_rate

        if transfer_amount > 0:
            new_source = self.decrease_entropy(source, transfer_amount)
            new_target = self.increase_entropy(target, transfer_amount)
        else:
            new_source = self.increase_entropy(source, abs(transfer_amount))
            new_target = self.decrease_entropy(target, abs(transfer_amount))

        return new_source, new_target


class VectorMachineSolution:
    """向量机完整解决方案"""

    def __init__(
        self,
        mind_dimensions: int = 512,
        skill_dimensions: int = 256,
        strategy_dimensions: int = 256,
    ):
        self.mind_dimensions = mind_dimensions
        self.skill_dimensions = skill_dimensions
        self.strategy_dimensions = strategy_dimensions

        self.mind_generator = MindVectorGenerator(mind_dimensions)
        self.skill_machine = SkillVectorMachine(skill_dimensions)
        self.strategy_machine = StrategyVectorMachine(strategy_dimensions)
        self.entropy_machine = EntropyVectorMachine(mind_dimensions)
        self.dimension_mapper = DimensionSpaceMapper(skill_dimensions, mind_dimensions)

        self.data_pool: Optional[DataPool] = None
        self.pool_index: Optional[PoolIndex] = None

        self.logger = get_logger(f"{__name__}.VectorMachineSolution")

    def initialize_data_pool(self, pool_name: str = "mind_pool") -> DataPool:
        self.data_pool = DataPool(pool_name=pool_name)
        self.pool_index = PoolIndex(self.data_pool)
        self.logger.info(f"Initialized data pool: {pool_name}")
        return self.data_pool

    def generate_mind_dataset(
        self,
        n_principles: int = 100,
        n_generated: int = 900,
    ) -> MindDataset:
        from ai_llm_agent_crawler.mind.models import MindDataset, DatasetType

        dataset = MindDataset(
            dataset_id=str(uuid.uuid4()),
            name="complete_mind_dataset",
            dataset_type=DatasetType.HYBRID,
            description="Complete mind dataset with principles and generated samples",
        )

        principles = [
            "risk_management", "diversification", "momentum", "mean_reversion",
            "trend_following", "statistical_arbitrage", "pair_trading", "market_making",
            "volatility_trading", "carry_trade", "value_investing", "growth_investing",
            "technical_analysis", "fundamental_analysis", "sentiment_analysis",
            "quantitative_trading", "algorithmic_trading", "high_frequency_trading",
            "smart_beta", "factor_investing", "esg_investing", "thematic_investing",
            "sector_rotation", "asset_allocation", "rebalancing", "tactical_allocation",
            "strategic_allocation", "dynamic_hedging", "static_hedging", "delta_hedging",
            "gamma_scalping", "vega_trading", "theta_decay", "time_decay",
            "convergence_trading", "divergence_trading", "relative_value",
            "event_driven", "merger_arbitrage", "convertible_arbitrage",
            "fixed_income_arbitrage", "capital_structure_arbitrage",
        ]

        for i, principle in enumerate(principles[:n_principles]):
            vec = self.mind_generator.generate_principle_vector(principle)
            dataset.add_sample(
                sample_id=f"principle_{i}",
                features=vec.to_numpy().tolist(),
                label=principle,
                sample_type="principle",
            )

        for i in range(n_generated):
            entropy = i / max(1, n_generated - 1)
            vec = self.mind_generator.generate_from_entropy(entropy)
            dataset.add_sample(
                sample_id=f"generated_{i}",
                features=vec.to_numpy().tolist(),
                label=f"entropy_{entropy:.3f}",
                sample_type="generated",
            )

        self.logger.info(f"Generated mind dataset with {dataset.size} samples")
        return dataset

    def build_skill_library(self, n_skills: int = 50) -> "SkillLibrary":
        from ai_llm_agent_crawler.agent.models import SkillLibrary, Skill, SkillType

        library = SkillLibrary()

        skill_templates = [
            ("trend_following", SkillType.TRADING),
            ("mean_reversion", SkillType.TRADING),
            ("momentum", SkillType.ANALYSIS),
            ("volatility_prediction", SkillType.ANALYSIS),
            ("risk_assessment", SkillType.RISK_MANAGEMENT),
            ("portfolio_optimization", SkillType.OPTIMIZATION),
            ("market_making", SkillType.TRADING),
            ("statistical_arbitrage", SkillType.ARBITRAGE),
            ("sentiment_analysis", SkillType.ANALYSIS),
            ("pattern_recognition", SkillType.LEARNING),
            ("adaptive_learning", SkillType.LEARNING),
            ("entropy_measurement", SkillType.ANALYSIS),
            ("dimension_reduction", SkillType.OPTIMIZATION),
            ("strategy_generation", SkillType.LEARNING),
            ("exploration_balance", SkillType.ADAPTIVE),
            ("creativity_generation", SkillType.CREATIVE),
            ("analogical_reasoning", SkillType.LEARNING),
            ("transfer_learning", SkillType.LEARNING),
        ]

        for name, stype in skill_templates[:min(n_skills, len(skill_templates))]:
            skill = Skill(
                skill_id=str(uuid.uuid4()),
                name=name,
                skill_type=stype,
                description=f"Skill for {name}",
                success_rate=0.5 + 0.3 * np.random.random(),
                complexity=np.random.random(),
                creativity_level=np.random.random(),
            )
            library.add_skill(skill)
            self.skill_machine.encode_skill(skill)

        remaining = max(0, n_skills - len(skill_templates))
        generator = VectorSkillGenerator(self.skill_machine)
        for i in range(remaining):
            skill = generator.generate_random_skill(
                SkillType.ADAPTIVE,
                name=f"synthetic_skill_{i}",
            )
            library.add_skill(skill)

        self.logger.info(f"Built skill library with {len(library.skills)} skills")
        return library

    def generate_strategy_spectrum(self, n_strategies: int = 100) -> List[Strategy]:
        strategies = []
        entropy_gen = EntropyDrivenStrategy(self.skill_machine)

        for i in range(n_strategies):
            entropy = i / max(1, n_strategies - 1)
            strategy = entropy_gen.generate_from_entropy(entropy)
            self.strategy_machine.encode_strategy(strategy)
            strategies.append(strategy)

        self.logger.info(f"Generated strategy spectrum with {n_strategies} strategies")
        return strategies

    def create_adaptive_agent(
        self,
        strategies: Optional[List[Strategy]] = None,
        config: Optional[AgentConfig] = None,
    ) -> StrategyAgent:
        if config is None:
            config = AgentConfig()

        agent = StrategyAgent(config)

        if strategies:
            for i, strategy in enumerate(strategies):
                weight = 1.0 / (i + 1)
                agent.add_strategy(strategy, weight)

        self.logger.info(f"Created adaptive agent with {len(strategies or [])} strategies")
        return agent

    def make_entropy_solution(
        self,
        initial_vector: Optional[np.ndarray] = None,
        target_entropy: float = 0.7,
    ) -> Dict[str, Any]:
        if initial_vector is None:
            initial_vector = np.random.randn(self.mind_dimensions)
            norm = np.linalg.norm(initial_vector)
            if norm > 0:
                initial_vector /= norm

        initial_entropy = self.entropy_machine.vector_to_entropy(initial_vector)

        result_vector, final_entropy = self.entropy_machine.make_entropy(
            initial_vector, target_entropy
        )

        mind_vector = MindVector(
            vector_id=str(uuid.uuid4()),
            dimensions=self.mind_dimensions,
            vector_type="entropy",
            metadata={
                "initial_entropy": initial_entropy,
                "target_entropy": target_entropy,
                "final_entropy": final_entropy,
            },
        )
        mind_vector.from_numpy(result_vector)

        return {
            "initial_vector": initial_vector,
            "result_vector": result_vector,
            "mind_vector": mind_vector,
            "initial_entropy": initial_entropy,
            "target_entropy": target_entropy,
            "final_entropy": final_entropy,
            "entropy_change": final_entropy - initial_entropy,
        }

    def get_system_summary(self) -> Dict[str, Any]:
        return {
            "mind_dimensions": self.mind_dimensions,
            "skill_dimensions": self.skill_dimensions,
            "strategy_dimensions": self.strategy_dimensions,
            "mind_concepts": len(self.mind_generator.get_basis_concepts()),
            "skills_encoded": len(self.skill_machine._skill_vectors),
            "strategies_encoded": len(self.strategy_machine.strategy_vectors),
            "data_pool": self.data_pool.pool_name if self.data_pool else None,
        }
