"""
Mind数据集生成模块

提供原理数据集、生成模型数据集、熵驱动数据集等生成功能。
"""

import hashlib
import json
import random
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.mind.models import (
    DataSourceType,
    MindDataRecord,
    MindDataset,
    MindDataType,
    MindVector,
    MindVectorType,
    QualityGrade,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class PrincipleDatasetGenerator:
    """原理数据集生成器"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self._rng = np.random.RandomState(42)
        self.logger = get_logger(f"{__name__}.PrincipleDatasetGenerator")

    def generate_principles(
        self,
        count: int = 1000,
        categories: Optional[List[str]] = None,
    ) -> MindDataset:
        categories = categories or [
            "entropy", "information", "thermodynamics", "computation",
            "cognition", "pattern", "structure", "dynamics",
            "optimization", "representation",
        ]

        records = []
        for i in range(count):
            category = categories[i % len(categories)]
            record = self._generate_principle_record(i, category)
            records.append(record)

        dataset = MindDataset(
            dataset_id=str(uuid.uuid4()),
            name=f"principle_dataset_{len(records)}",
            description="Generated principle dataset for mind model",
            data_type=MindDataType.PRINCIPLE,
            vector_type=MindVectorType.SEMANTIC,
            dimensions=self.dimensions,
            source_type=DataSourceType.SYNTHETIC,
        )
        dataset.add_records(records)
        self.logger.info(f"Generated {len(records)} principle records")
        return dataset

    def _generate_principle_record(self, index: int, category: str) -> MindDataRecord:
        principle_templates = {
            "entropy": [
                "Entropy measures the degree of disorder in a system",
                "Higher entropy states are more probable than lower ones",
                "The second law states that total entropy never decreases",
                "Information entropy quantifies uncertainty in a message",
                "Maximum entropy distributions are least informative",
            ],
            "information": [
                "Information is the resolution of uncertainty",
                "More information reduces entropy proportionally",
                "Information can be encoded in various representations",
                "The information content of an event is -log(probability)",
                "Mutual information measures shared uncertainty",
            ],
            "computation": [
                "Computation transforms information through rules",
                "Universal computation can simulate any other computation",
                "Computational complexity classifies problem difficulty",
                "Parallel computation divides problems across processes",
                "Probabilistic computation trades certainty for speed",
            ],
            "dynamics": [
                "Dynamical systems evolve over time according to rules",
                "Chaotic systems exhibit sensitive dependence on initial conditions",
                "Attractors describe long-term behavior of systems",
                "Phase transitions occur at critical parameter values",
                "Feedback loops amplify or dampen system changes",
            ],
        }

        templates = principle_templates.get(category, ["Abstract principle governing systems behavior"])
        template = templates[index % len(templates)]

        vector_values = self._generate_principle_vector(category, index)
        vector = MindVector(
            vector_type=MindVectorType.SEMANTIC,
            dimensions=self.dimensions,
        )
        vector.from_numpy(vector_values)

        quality = 0.6 + 0.4 * random.random()
        entropy = 0.3 + 0.5 * random.random()

        record = MindDataRecord(
            record_id=f"principle_{index:08d}",
            data_type=MindDataType.PRINCIPLE,
            content=template,
            structured_data={
                "category": category,
                "principle_id": index,
                "abstraction_level": 0.5 + 0.5 * random.random(),
                "generality": 0.3 + 0.7 * random.random(),
            },
            quality_score=quality,
            quality_grade=self._quality_grade(quality),
            source_type=DataSourceType.SYNTHETIC,
            entropy_value=entropy,
            dimensionality=self.dimensions,
            tags=[category, "principle", f"gen_{index % 10}"],
            categories=[category],
            version="1.0.0",
        )
        record.add_vector(vector)
        return record

    def _generate_principle_vector(self, category: str, index: int) -> np.ndarray:
        base = np.zeros(self.dimensions)
        category_hash = int(hashlib.md5(category.encode()).hexdigest(), 16)
        self._rng.seed(category_hash + index)
        vector = self._rng.randn(self.dimensions)
        vector = vector / np.linalg.norm(vector)

        semantic_signal = np.zeros(self.dimensions)
        n_components = min(50, self.dimensions // 10)
        components = self._rng.choice(self.dimensions, n_components, replace=False)
        semantic_signal[components] = self._rng.randn(n_components) * 0.5

        combined = vector + 0.3 * semantic_signal
        combined = combined / np.linalg.norm(combined)
        return combined

    def _quality_grade(self, score: float) -> QualityGrade:
        if score >= 0.9:
            return QualityGrade.GOLD
        elif score >= 0.7:
            return QualityGrade.SILVER
        elif score >= 0.5:
            return QualityGrade.BRONZE
        else:
            return QualityGrade.RAW


class GenerativeDatasetGenerator:
    """生成模型数据集生成器"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self._rng = np.random.RandomState(42)
        self.logger = get_logger(f"{__name__}.GenerativeDatasetGenerator")

    def generate_generative_dataset(
        self,
        count: int = 2000,
        base_dataset: Optional[MindDataset] = None,
    ) -> MindDataset:
        records = []
        base_records = base_dataset.records if base_dataset else []

        for i in range(count):
            record = self._generate_generative_record(i, base_records)
            records.append(record)

        dataset = MindDataset(
            dataset_id=str(uuid.uuid4()),
            name=f"generative_dataset_{len(records)}",
            description="Generated dataset from generative model",
            data_type=MindDataType.GENERATIVE,
            vector_type=MindVectorType.SEMANTIC,
            dimensions=self.dimensions,
            source_type=DataSourceType.MODEL_GENERATED,
        )
        dataset.add_records(records)
        self.logger.info(f"Generated {len(records)} generative records")
        return dataset

    def _generate_generative_record(
        self,
        index: int,
        base_records: List[MindDataRecord],
    ) -> MindDataRecord:
        if base_records and random.random() < 0.7:
            base = random.choice(base_records)
            record = self._derive_from_base(base, index)
        else:
            record = self._generate_random_generative(index)
        return record

    def _derive_from_base(self, base: MindDataRecord, index: int) -> MindDataRecord:
        base_vector = base.get_vector(base.vectors[list(base.vectors.keys())[0]].vector_type.value) if base.vectors else None

        if base_vector:
            noise = self._rng.randn(self.dimensions) * 0.2
            new_values = base_vector.to_numpy() + noise
            new_values = new_values / np.linalg.norm(new_values)
        else:
            new_values = self._rng.randn(self.dimensions)
            new_values = new_values / np.linalg.norm(new_values)

        new_vector = MindVector(
            vector_type=MindVectorType.SEMANTIC,
            dimensions=self.dimensions,
        )
        new_vector.from_numpy(new_values)

        quality = base.quality_score * (0.7 + 0.3 * random.random())
        entropy = base.entropy_value * (0.8 + 0.4 * random.random())

        record = MindDataRecord(
            record_id=f"generative_{index:08d}",
            data_type=MindDataType.GENERATIVE,
            content=f"Generated content based on {base.record_id}",
            structured_data={
                "derived_from": base.record_id,
                "generation_method": "noise_injection",
                "noise_level": 0.2,
                "original_quality": base.quality_score,
            },
            quality_score=quality,
            quality_grade=self._quality_grade(quality),
            source_type=DataSourceType.MODEL_GENERATED,
            entropy_value=entropy,
            dimensionality=self.dimensions,
            tags=["generative"] + [f"derived_{base.record_id}"],
            categories=base.categories,
            parent_id=base.record_id,
            version="1.0.0",
        )
        record.add_vector(new_vector)
        return record

    def _generate_random_generative(self, index: int) -> MindDataRecord:
        values = self._rng.randn(self.dimensions)
        values = values / np.linalg.norm(values)

        vector = MindVector(
            vector_type=MindVectorType.SEMANTIC,
            dimensions=self.dimensions,
        )
        vector.from_numpy(values)

        quality = 0.3 + 0.5 * random.random()
        entropy = 0.2 + 0.7 * random.random()

        record = MindDataRecord(
            record_id=f"generative_{index:08d}",
            data_type=MindDataType.GENERATIVE,
            content=f"Randomly generated sample {index}",
            structured_data={
                "generation_method": "random",
                "distribution": "normal",
            },
            quality_score=quality,
            quality_grade=self._quality_grade(quality),
            source_type=DataSourceType.MODEL_GENERATED,
            entropy_value=entropy,
            dimensionality=self.dimensions,
            tags=["generative", "random"],
            categories=["random"],
            version="1.0.0",
        )
        record.add_vector(vector)
        return record

    def _quality_grade(self, score: float) -> QualityGrade:
        if score >= 0.9:
            return QualityGrade.GOLD
        elif score >= 0.7:
            return QualityGrade.SILVER
        elif score >= 0.5:
            return QualityGrade.BRONZE
        else:
            return QualityGrade.RAW


class SyntheticDataAugmentor:
    """合成数据增强器"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self._rng = np.random.RandomState(42)

    def augment(
        self,
        record: MindDataRecord,
        method: str = "noise",
        intensity: float = 0.1,
    ) -> MindDataRecord:
        vector = record.get_vector(list(record.vectors.keys())[0]) if record.vectors else None
        if not vector:
            return record

        if method == "noise":
            new_values = self._add_noise(vector.to_numpy(), intensity)
        elif method == "rotation":
            new_values = self._random_rotation(vector.to_numpy(), intensity)
        elif method == "interpolation":
            new_values = vector.to_numpy()
        elif method == "scaling":
            new_values = self._scaling(vector.to_numpy(), intensity)
        else:
            new_values = self._add_noise(vector.to_numpy(), intensity)

        new_vector = MindVector(
            vector_type=vector.vector_type,
            dimensions=self.dimensions,
        )
        new_vector.from_numpy(new_values)

        new_record = MindDataRecord(
            record_id=f"{record.record_id}_aug_{method}_{intensity:.2f}",
            data_type=record.data_type,
            content=record.content,
            structured_data={
                **record.structured_data,
                "augmented_from": record.record_id,
                "augmentation_method": method,
                "augmentation_intensity": intensity,
            },
            quality_score=max(0.0, record.quality_score - intensity * 0.5),
            quality_grade=record.quality_grade,
            source_type=DataSourceType.SYNTHETIC,
            entropy_value=record.entropy_value * (1 + intensity),
            dimensionality=record.dimensionality,
            tags=record.tags + ["augmented", method],
            categories=record.categories,
            parent_id=record.record_id,
            version=record.version,
        )
        new_record.add_vector(new_vector)
        return new_record

    def _add_noise(self, vector: np.ndarray, intensity: float) -> np.ndarray:
        noise = self._rng.randn(len(vector)) * intensity
        result = vector + noise
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm
        return result

    def _random_rotation(self, vector: np.ndarray, intensity: float) -> np.ndarray:
        n = len(vector)
        angle = intensity * np.pi
        i, j = self._rng.choice(n, 2, replace=False)
        result = vector.copy()
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        vi, vj = result[i], result[j]
        result[i] = cos_a * vi - sin_a * vj
        result[j] = sin_a * vi + cos_a * vj
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm
        return result

    def _scaling(self, vector: np.ndarray, intensity: float) -> np.ndarray:
        scale = 1.0 + (self._rng.randn() * intensity)
        result = vector * scale
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm
        return result

    def augment_batch(
        self,
        records: List[MindDataRecord],
        methods: Optional[List[str]] = None,
        augment_per_record: int = 3,
    ) -> List[MindDataRecord]:
        methods = methods or ["noise", "rotation", "scaling"]
        augmented = []
        for record in records:
            for _ in range(augment_per_record):
                method = random.choice(methods)
                intensity = 0.05 + 0.25 * random.random()
                new_record = self.augment(record, method, intensity)
                augmented.append(new_record)
        return augmented


class EntropyDrivenGenerator:
    """熵驱动数据集生成器"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self._rng = np.random.RandomState(42)
        self.logger = get_logger(f"{__name__}.EntropyDrivenGenerator")

    def generate_entropy_dataset(
        self,
        count: int = 1500,
        entropy_range: Tuple[float, float] = (0.1, 0.9),
    ) -> MindDataset:
        records = []
        for i in range(count):
            target_entropy = entropy_range[0] + (entropy_range[1] - entropy_range[0]) * (i / max(1, count - 1))
            record = self._generate_entropy_record(i, target_entropy)
            records.append(record)

        dataset = MindDataset(
            dataset_id=str(uuid.uuid4()),
            name=f"entropy_dataset_{len(records)}",
            description="Entropy-driven dataset with controlled entropy levels",
            data_type=MindDataType.ENTROPY,
            vector_type=MindVectorType.ENTROPY,
            dimensions=self.dimensions,
            source_type=DataSourceType.SYNTHETIC,
        )
        dataset.add_records(records)
        self.logger.info(f"Generated {len(records)} entropy records")
        return dataset

    def _generate_entropy_record(self, index: int, target_entropy: float) -> MindDataRecord:
        vector_values = self._generate_entropy_vector(target_entropy)
        vector = MindVector(
            vector_type=MindVectorType.ENTROPY,
            dimensions=self.dimensions,
        )
        vector.from_numpy(vector_values)

        quality = 0.5 + 0.4 * (1 - abs(target_entropy - 0.5) * 2)

        record = MindDataRecord(
            record_id=f"entropy_{index:08d}",
            data_type=MindDataType.ENTROPY,
            content=f"Entropy sample with target entropy {target_entropy:.3f}",
            structured_data={
                "target_entropy": target_entropy,
                "entropy_level": "low" if target_entropy < 0.3 else "medium" if target_entropy < 0.7 else "high",
                "complexity": target_entropy,
            },
            quality_score=quality,
            quality_grade=QualityGrade.SILVER,
            source_type=DataSourceType.SYNTHETIC,
            entropy_value=target_entropy,
            dimensionality=self.dimensions,
            tags=["entropy", f"level_{int(target_entropy * 10)}"],
            categories=["entropy"],
            version="1.0.0",
        )
        record.add_vector(vector)
        return record

    def _generate_entropy_vector(self, target_entropy: float) -> np.ndarray:
        if target_entropy < 0.3:
            n_peaks = max(1, int(self.dimensions * 0.05))
            vector = np.zeros(self.dimensions)
            peak_indices = self._rng.choice(self.dimensions, n_peaks, replace=False)
            vector[peak_indices] = self._rng.randn(n_peaks) * 2
        elif target_entropy < 0.7:
            vector = self._rng.randn(self.dimensions)
        else:
            vector = self._rng.randn(self.dimensions)
            mixing = int(self.dimensions * target_entropy * 0.5)
            for _ in range(mixing):
                i, j = self._rng.choice(self.dimensions, 2, replace=False)
                vector[i], vector[j] = vector[j], vector[i]

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector


class MindDatasetGenerator:
    """Mind数据集生成器 - 整合所有生成方法"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self.principle_gen = PrincipleDatasetGenerator(dimensions)
        self.generative_gen = GenerativeDatasetGenerator(dimensions)
        self.augmentor = SyntheticDataAugmentor(dimensions)
        self.entropy_gen = EntropyDrivenGenerator(dimensions)
        self.logger = get_logger(f"{__name__}.MindDatasetGenerator")

    def generate_complete_dataset(
        self,
        principle_count: int = 1000,
        generative_count: int = 2000,
        entropy_count: int = 1500,
        augment: bool = True,
        augment_count: int = 2,
    ) -> MindDataset:
        self.logger.info("Starting complete dataset generation...")

        principle_dataset = self.principle_gen.generate_principles(principle_count)
        generative_dataset = self.generative_gen.generate_generative_dataset(
            generative_count, principle_dataset
        )
        entropy_dataset = self.entropy_gen.generate_entropy_dataset(entropy_count)

        all_records = (
            principle_dataset.records
            + generative_dataset.records
            + entropy_dataset.records
        )

        if augment:
            augmented = self.augmentor.augment_batch(
                principle_dataset.records[:principle_count // 2],
                augment_per_record=augment_count,
            )
            all_records.extend(augmented)

        combined = MindDataset(
            dataset_id=str(uuid.uuid4()),
            name=f"mind_complete_dataset_{len(all_records)}",
            description="Complete mind dataset with principles, generative, and entropy samples",
            data_type=MindDataType.PRINCIPLE,
            vector_type=MindVectorType.SEMANTIC,
            dimensions=self.dimensions,
            source_type=DataSourceType.HYBRID,
        )
        combined.add_records(all_records)

        self.logger.info(
            f"Complete dataset generated: {len(all_records)} records total "
            f"({principle_count} principles, {generative_count} generative, "
            f"{entropy_count} entropy)"
        )
        return combined

    def generate_by_type(
        self,
        data_type: MindDataType,
        count: int = 1000,
        **kwargs: Any,
    ) -> MindDataset:
        if data_type == MindDataType.PRINCIPLE:
            return self.principle_gen.generate_principles(count, **kwargs)
        elif data_type == MindDataType.GENERATIVE:
            return self.generative_gen.generate_generative_dataset(count, **kwargs)
        elif data_type == MindDataType.ENTROPY:
            return self.entropy_gen.generate_entropy_dataset(count, **kwargs)
        else:
            return self.generative_gen.generate_generative_dataset(count, **kwargs)
