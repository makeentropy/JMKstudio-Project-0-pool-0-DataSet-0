"""
Skill向量机模块

提供Skill向量化、向量运算、Skill组合、搜索和排序功能。
"""

import hashlib
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.agent.models import (
    Skill,
    SkillLibrary,
    SkillType,
    SkillVector,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class SkillVectorMachine:
    """Skill向量机"""

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions
        self._skill_vectors: Dict[str, SkillVector] = {}
        self._type_centroids: Dict[str, np.ndarray] = {}
        self.logger = get_logger(f"{__name__}.SkillVectorMachine")

    def encode_skill(self, skill: Skill) -> SkillVector:
        vec = SkillVector(
            vector_id=str(uuid.uuid4()),
            skill_id=skill.skill_id,
            dimensions=self.dimensions,
            skill_type=skill.skill_type,
            effectiveness=skill.success_rate,
            efficiency=min(1.0, skill.avg_reward / 100.0) if skill.avg_reward > 0 else 0.5,
            creativity=skill.creativity_level,
            adaptability=1.0 - skill.complexity,
        )

        values = self._generate_skill_vector(skill)
        vec.from_numpy(values)
        self._skill_vectors[skill.skill_id] = vec
        return vec

    def _generate_skill_vector(self, skill: Skill) -> np.ndarray:
        base = np.zeros(self.dimensions)

        type_hash = int(hashlib.md5(skill.skill_type.value.encode()).hexdigest(), 16)
        rng = np.random.RandomState(type_hash & 0xFFFFFFFF)
        type_signal = rng.randn(self.dimensions) * 0.3

        name_hash = int(hashlib.md5(skill.name.encode()).hexdigest(), 16)
        rng2 = np.random.RandomState(name_hash & 0xFFFFFFFF)
        name_signal = rng2.randn(self.dimensions) * 0.2

        if skill.parameters:
            param_vector = self._encode_parameters(skill.parameters)
        else:
            param_vector = np.zeros(self.dimensions)

        combined = 0.4 * type_signal + 0.3 * name_signal + 0.3 * param_vector
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        return combined

    def _encode_parameters(self, params: Dict[str, Any]) -> np.ndarray:
        vec = np.zeros(self.dimensions)
        for i, (key, value) in enumerate(params.items()):
            idx = i % self.dimensions
            if isinstance(value, (int, float)):
                vec[idx] = float(value)
            elif isinstance(value, bool):
                vec[idx] = 1.0 if value else 0.0
            elif isinstance(value, str):
                h = int(hashlib.md5(value.encode()).hexdigest(), 16)
                vec[idx] = (h % 1000) / 1000.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def add_skill(self, skill: Skill) -> SkillVector:
        return self.encode_skill(skill)

    def get_vector(self, skill_id: str) -> Optional[SkillVector]:
        return self._skill_vectors.get(skill_id)

    def similarity(self, skill_a: str, skill_b: str) -> float:
        va = self._skill_vectors.get(skill_a)
        vb = self._skill_vectors.get(skill_b)
        if not va or not vb:
            return 0.0
        return va.cosine_similarity(vb)

    def add_skills_from_library(self, library: SkillLibrary) -> int:
        count = 0
        for skill in library.skills.values():
            self.encode_skill(skill)
            count += 1
        self.logger.info(f"Encoded {count} skills from library")
        return count

    def compute_type_centroids(self) -> Dict[str, np.ndarray]:
        type_vectors: Dict[str, List[np.ndarray]] = {}
        for sv in self._skill_vectors.values():
            t = sv.skill_type.value
            if t not in type_vectors:
                type_vectors[t] = []
            type_vectors[t].append(sv.to_numpy())

        centroids = {}
        for t, vecs in type_vectors.items():
            if vecs:
                centroids[t] = np.mean(vecs, axis=0)
        self._type_centroids = centroids
        return centroids

    def get_type_centroid(self, skill_type: SkillType) -> Optional[np.ndarray]:
        if not self._type_centroids:
            self.compute_type_centroids()
        return self._type_centroids.get(skill_type.value)


class SkillComposer:
    """Skill组合器"""

    def __init__(self, vector_machine: SkillVectorMachine):
        self.vector_machine = vector_machine
        self.logger = get_logger(f"{__name__}.SkillComposer")

    def compose(self, skill_ids: List[str], weights: Optional[List[float]] = None) -> np.ndarray:
        vectors = []
        for sid in skill_ids:
            sv = self.vector_machine.get_vector(sid)
            if sv:
                vectors.append(sv.to_numpy())

        if not vectors:
            return np.zeros(self.vector_machine.dimensions)

        if weights is None:
            weights = [1.0 / len(vectors)] * len(vectors)

        if len(weights) != len(vectors):
            weights = [1.0 / len(vectors)] * len(vectors)

        combined = np.zeros(self.vector_machine.dimensions)
        for vec, w in zip(vectors, weights):
            combined += w * vec

        total_weight = sum(weights)
        if total_weight > 0:
            combined /= total_weight

        norm = np.linalg.norm(combined)
        if norm > 0:
            combined /= norm

        return combined

    def interpolate(self, skill_a: str, skill_b: str, alpha: float = 0.5) -> np.ndarray:
        va = self.vector_machine.get_vector(skill_a)
        vb = self.vector_machine.get_vector(skill_b)
        if not va or not vb:
            return np.zeros(self.vector_machine.dimensions)

        vec_a = va.to_numpy()
        vec_b = vb.to_numpy()
        interpolated = (1 - alpha) * vec_a + alpha * vec_b
        norm = np.linalg.norm(interpolated)
        if norm > 0:
            interpolated /= norm
        return interpolated

    def blend(self, skill_ids: List[str], blend_mode: str = "average") -> np.ndarray:
        if blend_mode == "average":
            return self.compose(skill_ids)
        elif blend_mode == "weighted":
            n = len(skill_ids)
            weights = [1.0 / (i + 1) for i in range(n)]
            total = sum(weights)
            weights = [w / total for w in weights]
            return self.compose(skill_ids, weights)
        elif blend_mode == "max":
            vectors = []
            for sid in skill_ids:
                sv = self.vector_machine.get_vector(sid)
                if sv:
                    vectors.append(sv.to_numpy())
            if not vectors:
                return np.zeros(self.vector_machine.dimensions)
            return np.max(vectors, axis=0)
        else:
            return self.compose(skill_ids)

    def generate_derived_skill(
        self,
        base_skills: List[str],
        name: str,
        skill_type: SkillType = SkillType.ADAPTIVE,
        weights: Optional[List[float]] = None,
    ) -> Skill:
        combined_vector = self.compose(base_skills, weights)

        new_skill = Skill(
            skill_id=str(uuid.uuid4()),
            name=name,
            skill_type=skill_type,
            description=f"Derived from skills: {', '.join(base_skills)}",
            success_rate=0.5,
            complexity=0.7,
            creativity_level=0.8,
            parent_skill=base_skills[0] if base_skills else None,
            child_skills=base_skills,
        )

        sv = SkillVector(
            vector_id=str(uuid.uuid4()),
            skill_id=new_skill.skill_id,
            dimensions=self.vector_machine.dimensions,
            skill_type=skill_type,
        )
        sv.from_numpy(combined_vector)
        new_skill.add_vector(sv, "default")

        self.vector_machine._skill_vectors[new_skill.skill_id] = sv
        self.logger.info(f"Generated derived skill: {name} from {len(base_skills)} base skills")
        return new_skill


class SkillSearchEngine:
    """Skill搜索引擎"""

    def __init__(self, vector_machine: SkillVectorMachine):
        self.vector_machine = vector_machine
        self.logger = get_logger(f"{__name__}.SkillSearchEngine")

    def search_by_vector(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        skill_type: Optional[SkillType] = None,
    ) -> List[Tuple[SkillVector, float]]:
        results = []
        for sv in self.vector_machine._skill_vectors.values():
            if skill_type and sv.skill_type != skill_type:
                continue
            sim = sv.cosine_similarity(SkillVector(
                dimensions=len(query_vector),
                values=query_vector.tolist(),
            ))
            results.append((sv, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_by_skill(
        self,
        skill_id: str,
        top_k: int = 10,
        include_self: bool = False,
    ) -> List[Tuple[SkillVector, float]]:
        query = self.vector_machine.get_vector(skill_id)
        if not query:
            return []

        results = self.search_by_vector(query.to_numpy(), top_k + 1)
        if not include_self:
            results = [(sv, sim) for sv, sim in results if sv.skill_id != skill_id]
        return results[:top_k]

    def search_by_type(
        self,
        skill_type: SkillType,
        top_k: int = 10,
    ) -> List[Tuple[SkillVector, float]]:
        centroid = self.vector_machine.get_type_centroid(skill_type)
        if centroid is None:
            return []
        return self.search_by_vector(centroid, top_k, skill_type)

    def search_analogous(
        self,
        source_skill: str,
        target_type: SkillType,
        top_k: int = 5,
    ) -> List[Tuple[SkillVector, float]]:
        source_vec = self.vector_machine.get_vector(source_skill)
        if not source_vec:
            return []

        source_type = source_vec.skill_type
        source_centroid = self.vector_machine.get_type_centroid(source_type)
        target_centroid = self.vector_machine.get_type_centroid(target_type)

        if source_centroid is None or target_centroid is None:
            return []

        offset = source_vec.to_numpy() - source_centroid
        query = target_centroid + offset
        norm = np.linalg.norm(query)
        if norm > 0:
            query /= norm

        return self.search_by_vector(query, top_k, target_type)


class SkillRanker:
    """Skill排序器"""

    def __init__(self, vector_machine: SkillVectorMachine):
        self.vector_machine = vector_machine

    def rank_by_effectiveness(
        self,
        skill_ids: List[str],
        descending: bool = True,
    ) -> List[Tuple[str, float]]:
        scored = []
        for sid in skill_ids:
            sv = self.vector_machine.get_vector(sid)
            if sv:
                scored.append((sid, sv.effectiveness))
        scored.sort(key=lambda x: x[1], reverse=descending)
        return scored

    def rank_by_similarity(
        self,
        skill_ids: List[str],
        query_vector: np.ndarray,
    ) -> List[Tuple[str, float]]:
        scored = []
        query_sv = SkillVector(dimensions=len(query_vector), values=query_vector.tolist())
        for sid in skill_ids:
            sv = self.vector_machine.get_vector(sid)
            if sv:
                scored.append((sid, sv.cosine_similarity(query_sv)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def rank_composite(
        self,
        skill_ids: List[str],
        weights: Optional[Dict[str, float]] = None,
    ) -> List[Tuple[str, float]]:
        weights = weights or {
            "effectiveness": 0.4,
            "efficiency": 0.2,
            "creativity": 0.2,
            "adaptability": 0.2,
        }
        scored = []
        for sid in skill_ids:
            sv = self.vector_machine.get_vector(sid)
            if sv:
                score = (
                    weights.get("effectiveness", 0) * sv.effectiveness
                    + weights.get("efficiency", 0) * sv.efficiency
                    + weights.get("creativity", 0) * sv.creativity
                    + weights.get("adaptability", 0) * sv.adaptability
                )
                scored.append((sid, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def rank_for_context(
        self,
        skill_ids: List[str],
        context_vector: np.ndarray,
        context_weight: float = 0.5,
    ) -> List[Tuple[str, float]]:
        context_scores = self.rank_by_similarity(skill_ids, context_vector)
        composite_scores = self.rank_composite(skill_ids)

        context_dict = {sid: score for sid, score in context_scores}
        composite_dict = {sid: score for sid, score in composite_scores}

        combined = []
        for sid in skill_ids:
            cs = context_dict.get(sid, 0.0)
            ps = composite_dict.get(sid, 0.0)
            total = context_weight * cs + (1 - context_weight) * ps
            combined.append((sid, total))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined


class VectorSkillGenerator:
    """向量Skill生成器 - 从向量空间生成新Skill"""

    def __init__(self, vector_machine: SkillVectorMachine):
        self.vector_machine = vector_machine
        self.logger = get_logger(f"{__name__}.VectorSkillGenerator")

    def generate_random_skill(
        self,
        skill_type: SkillType = SkillType.ADAPTIVE,
        name: Optional[str] = None,
    ) -> Skill:
        vector = np.random.randn(self.vector_machine.dimensions)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        skill = Skill(
            skill_id=str(uuid.uuid4()),
            name=name or f"random_skill_{np.random.randint(10000)}",
            skill_type=skill_type,
            success_rate=0.3 + 0.5 * np.random.random(),
            complexity=np.random.random(),
            creativity_level=np.random.random(),
        )

        sv = SkillVector(
            vector_id=str(uuid.uuid4()),
            skill_id=skill.skill_id,
            dimensions=self.vector_machine.dimensions,
            skill_type=skill_type,
        )
        sv.from_numpy(vector)
        skill.add_vector(sv, "default")
        self.vector_machine._skill_vectors[skill.skill_id] = sv
        return skill

    def generate_from_vector(
        self,
        vector: np.ndarray,
        skill_type: SkillType = SkillType.ADAPTIVE,
        name: str = "generated_skill",
    ) -> Skill:
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        skill = Skill(
            skill_id=str(uuid.uuid4()),
            name=name,
            skill_type=skill_type,
            success_rate=0.5,
            complexity=0.5,
            creativity_level=0.7,
        )

        sv = SkillVector(
            vector_id=str(uuid.uuid4()),
            skill_id=skill.skill_id,
            dimensions=self.vector_machine.dimensions,
            skill_type=skill_type,
        )
        sv.from_numpy(vector)
        skill.add_vector(sv, "default")
        self.vector_machine._skill_vectors[skill.skill_id] = sv
        return skill

    def interpolate_skills(
        self,
        skill_a: str,
        skill_b: str,
        n_points: int = 5,
    ) -> List[Skill]:
        va = self.vector_machine.get_vector(skill_a)
        vb = self.vector_machine.get_vector(skill_b)
        if not va or not vb:
            return []

        vec_a = va.to_numpy()
        vec_b = vb.to_numpy()

        skills = []
        for i in range(n_points):
            alpha = i / max(1, n_points - 1)
            interpolated = (1 - alpha) * vec_a + alpha * vec_b
            norm = np.linalg.norm(interpolated)
            if norm > 0:
                interpolated /= norm

            skill = self.generate_from_vector(
                interpolated,
                va.skill_type,
                f"interpolated_{alpha:.2f}",
            )
            skills.append(skill)

        self.logger.info(f"Generated {n_points} interpolated skills")
        return skills

    def mutate_skill(
        self,
        skill_id: str,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
    ) -> Optional[Skill]:
        sv = self.vector_machine.get_vector(skill_id)
        if not sv:
            return None

        vector = sv.to_numpy().copy()
        n_mutations = int(len(vector) * mutation_rate)
        indices = np.random.choice(len(vector), n_mutations, replace=False)
        mutation = np.random.randn(n_mutations) * mutation_strength
        vector[indices] += mutation

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        mutated = self.generate_from_vector(
            vector,
            sv.skill_type,
            f"mutated_{skill_id[:8]}",
        )
        mutated.parent_skill = skill_id
        return mutated

    def evolve_population(
        self,
        skill_ids: List[str],
        population_size: int = 20,
        generations: int = 10,
        fitness_fn: Optional[Callable[[Skill], float]] = None,
    ) -> List[Skill]:
        population = []
        for sid in skill_ids:
            sv = self.vector_machine.get_vector(sid)
            if sv:
                skill = self.generate_from_vector(sv.to_numpy(), sv.skill_type, f"parent_{sid[:8]}")
                population.append(skill)

        for i in range(len(population), population_size):
            population.append(self.generate_random_skill(name=f"random_{i}"))

        for gen in range(generations):
            if fitness_fn:
                fitnesses = [fitness_fn(s) for s in population]
            else:
                fitnesses = [s.success_rate for s in population]

            sorted_indices = np.argsort(fitnesses)[::-1]
            top_half = [population[i] for i in sorted_indices[:population_size // 2]]

            new_population = top_half[:]
            while len(new_population) < population_size:
                parent_a = np.random.choice(len(top_half))
                parent_b = np.random.choice(len(top_half))

                vec_a = top_half[parent_a].get_vector("default")
                vec_b = top_half[parent_b].get_vector("default")

                if vec_a and vec_b:
                    child_vec = 0.5 * vec_a.to_numpy() + 0.5 * vec_b.to_numpy()
                    child_vec += np.random.randn(len(child_vec)) * 0.05
                    norm = np.linalg.norm(child_vec)
                    if norm > 0:
                        child_vec /= norm

                    child = self.generate_from_vector(
                        child_vec,
                        vec_a.skill_type,
                        f"gen_{gen}_child_{len(new_population)}",
                    )
                    new_population.append(child)

            population = new_population

        self.logger.info(f"Evolved population for {generations} generations")
        return population
