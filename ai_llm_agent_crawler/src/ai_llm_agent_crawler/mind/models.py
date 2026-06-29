"""
Mind数据集与数据池 - 核心数据模型

定义Mind向量、数据记录、数据集、数据池等核心数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field


class MindDataType(str, Enum):
    """Mind数据类型枚举"""
    PRINCIPLE = "principle"
    GENERATIVE = "generative"
    EXPERIENCE = "experience"
    STRATEGY = "strategy"
    OBSERVATION = "observation"
    REASONING = "reasoning"
    EMOTION = "emotion"
    MEMORY = "memory"
    INTENTION = "intention"
    PERCEPTION = "perception"
    ABSTRACTION = "abstraction"
    ANALOGY = "analogy"
    ENTROPY = "entropy"
    TERRAIN = "terrain"
    FINANCIAL = "financial"


class MindVectorType(str, Enum):
    """Mind向量类型枚举"""
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"
    SEMANTIC_STRUCTURAL = "semantic_structural"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    ENTROPY = "entropy"
    MULTIMODAL = "multimodal"
    ABSTRACT = "abstract"
    HIERARCHICAL = "hierarchical"
    DYNAMIC = "dynamic"


class DataSourceType(str, Enum):
    """数据源类型枚举"""
    SYNTHETIC = "synthetic"
    REAL_WORLD = "real_world"
    SIMULATION = "simulation"
    HUMAN_GENERATED = "human_generated"
    MODEL_GENERATED = "model_generated"
    CURATED = "curated"
    HYBRID = "hybrid"
    MINED = "mined"


class QualityGrade(str, Enum):
    """质量等级枚举"""
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    RAW = "raw"
    EXPERIMENTAL = "experimental"


class MindVector(BaseModel):
    """Mind向量模型"""
    vector_id: str = Field(default="")
    vector_type: MindVectorType = Field(default=MindVectorType.SEMANTIC)
    dimensions: int = Field(default=768, ge=1)
    values: List[float] = Field(default_factory=list)
    norm: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def to_numpy(self) -> np.ndarray:
        return np.array(self.values)

    def from_numpy(self, arr: np.ndarray) -> None:
        self.values = arr.tolist()
        self.dimensions = len(arr)
        self.norm = float(np.linalg.norm(arr))

    def normalize(self) -> None:
        if self.norm > 0:
            arr = self.to_numpy()
            normalized = arr / self.norm
            self.values = normalized.tolist()
            self.norm = 1.0

    def cosine_similarity(self, other: "MindVector") -> float:
        if self.dimensions != other.dimensions or self.norm == 0 or other.norm == 0:
            return 0.0
        a = self.to_numpy()
        b = other.to_numpy()
        return float(np.dot(a, b) / (self.norm * other.norm))

    def add(self, other: "MindVector") -> "MindVector":
        result = self.to_numpy() + other.to_numpy()
        new_vec = MindVector(
            vector_type=self.vector_type,
            dimensions=self.dimensions,
        )
        new_vec.from_numpy(result)
        return new_vec


class MindDataRecord(BaseModel):
    """Mind数据记录模型"""
    record_id: str = Field(default="")
    data_type: MindDataType = Field(default=MindDataType.PRINCIPLE)
    content: str = Field(default="")
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    vectors: Dict[str, MindVector] = Field(default_factory=dict)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_grade: QualityGrade = Field(default=QualityGrade.RAW)
    source_type: DataSourceType = Field(default=DataSourceType.SYNTHETIC)
    source_id: str = Field(default="")
    entropy_value: float = Field(default=0.0)
    dimensionality: int = Field(default=0)
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    access_count: int = Field(default=0)
    last_accessed: Optional[datetime] = None
    version: str = Field(default="1.0.0")
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_vector(self, vector_type: str) -> Optional[MindVector]:
        return self.vectors.get(vector_type)

    def add_vector(self, vector: MindVector) -> None:
        self.vectors[vector.vector_type.value] = vector

    def increment_access(self) -> None:
        self.access_count += 1
        self.last_accessed = datetime.now()


class MindDataset(BaseModel):
    """Mind数据集模型"""
    dataset_id: str = Field(default="")
    name: str = Field(default="")
    description: str = Field(default="")
    data_type: MindDataType = Field(default=MindDataType.PRINCIPLE)
    vector_type: MindVectorType = Field(default=MindVectorType.SEMANTIC)
    records: List[MindDataRecord] = Field(default_factory=list)
    record_count: int = Field(default=0)
    dimensions: int = Field(default=768)
    total_size_bytes: int = Field(default=0)
    avg_quality_score: float = Field(default=0.0)
    avg_entropy: float = Field(default=0.0)
    source_type: DataSourceType = Field(default=DataSourceType.SYNTHETIC)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_record(self, record: MindDataRecord) -> None:
        self.records.append(record)
        self.record_count = len(self.records)
        self._update_stats()

    def add_records(self, records: List[MindDataRecord]) -> None:
        self.records.extend(records)
        self.record_count = len(self.records)
        self._update_stats()

    def _update_stats(self) -> None:
        if not self.records:
            return
        self.avg_quality_score = float(np.mean([r.quality_score for r in self.records]))
        self.avg_entropy = float(np.mean([r.entropy_value for r in self.records]))
        self.updated_at = datetime.now()

    def get_records_by_type(self, data_type: MindDataType) -> List[MindDataRecord]:
        return [r for r in self.records if r.data_type == data_type]

    def get_top_quality(self, n: int = 10) -> List[MindDataRecord]:
        sorted_records = sorted(self.records, key=lambda r: r.quality_score, reverse=True)
        return sorted_records[:n]

    def sample(self, n: int = 10, seed: Optional[int] = None) -> List[MindDataRecord]:
        if len(self.records) <= n:
            return self.records.copy()
        rng = np.random.RandomState(seed)
        indices = rng.choice(len(self.records), n, replace=False)
        return [self.records[i] for i in indices]


class DataSource(BaseModel):
    """数据源模型"""
    source_id: str = Field(default="")
    name: str = Field(default="")
    source_type: DataSourceType = Field(default=DataSourceType.SYNTHETIC)
    description: str = Field(default="")
    url: str = Field(default="")
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    record_count: int = Field(default=0)
    last_updated: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PoolConfig(BaseModel):
    """数据池配置模型"""
    pool_id: str = Field(default="")
    name: str = Field(default="")
    max_records: int = Field(default=1000000)
    max_size_bytes: int = Field(default=10 * 1024 * 1024 * 1024)
    default_vector_dim: int = Field(default=768)
    supported_data_types: List[MindDataType] = Field(
        default_factory=lambda: list(MindDataType)
    )
    supported_vector_types: List[MindVectorType] = Field(
        default_factory=lambda: list(MindVectorType)
    )
    quality_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    eviction_policy: str = Field(default="lru")
    auto_prune: bool = Field(default=True)
    prune_interval_seconds: int = Field(default=3600)
    index_type: str = Field(default="hnsw")
    persistence_enabled: bool = Field(default=True)
    persistence_path: str = Field(default="data/mind_pool")


class DataPool(BaseModel):
    """数据池模型"""
    config: PoolConfig = Field(default_factory=PoolConfig)
    datasets: Dict[str, MindDataset] = Field(default_factory=dict)
    record_index: Dict[str, MindDataRecord] = Field(default_factory=dict)
    tag_index: Dict[str, List[str]] = Field(default_factory=dict)
    type_index: Dict[str, List[str]] = Field(default_factory=dict)
    total_records: int = Field(default=0)
    total_size_bytes: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    last_pruned: Optional[datetime] = None
    stats: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def add_dataset(self, dataset: MindDataset) -> None:
        self.datasets[dataset.dataset_id] = dataset
        for record in dataset.records:
            self._index_record(record)
        self.total_records = len(self.record_index)

    def add_record(self, record: MindDataRecord) -> bool:
        if self.total_records >= self.config.max_records:
            return False
        self._index_record(record)
        self.total_records = len(self.record_index)
        return True

    def _index_record(self, record: MindDataRecord) -> None:
        self.record_index[record.record_id] = record
        for tag in record.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(record.record_id)
        type_key = record.data_type.value
        if type_key not in self.type_index:
            self.type_index[type_key] = []
        self.type_index[type_key].append(record.record_id)

    def get_record(self, record_id: str) -> Optional[MindDataRecord]:
        record = self.record_index.get(record_id)
        if record:
            record.increment_access()
        return record

    def get_records_by_tag(self, tag: str) -> List[MindDataRecord]:
        ids = self.tag_index.get(tag, [])
        return [self.record_index[i] for i in ids if i in self.record_index]

    def get_records_by_type(self, data_type: MindDataType) -> List[MindDataRecord]:
        ids = self.type_index.get(data_type.value, [])
        return [self.record_index[i] for i in ids if i in self.record_index]

    def remove_record(self, record_id: str) -> bool:
        record = self.record_index.pop(record_id, None)
        if not record:
            return False
        for tag in record.tags:
            if tag in self.tag_index and record_id in self.tag_index[tag]:
                self.tag_index[tag].remove(record_id)
        type_key = record.data_type.value
        if type_key in self.type_index and record_id in self.type_index[type_key]:
            self.type_index[type_key].remove(record_id)
        self.total_records = len(self.record_index)
        return True


class MindDatasetMeta(BaseModel):
    """Mind数据集元数据模型"""
    dataset_id: str = Field(default="")
    name: str = Field(default="")
    data_type: MindDataType = Field(default=MindDataType.PRINCIPLE)
    vector_type: MindVectorType = Field(default=MindVectorType.SEMANTIC)
    record_count: int = Field(default=0)
    dimensions: int = Field(default=768)
    quality_score: float = Field(default=0.0)
    entropy_score: float = Field(default=0.0)
    diversity_score: float = Field(default=0.0)
    coverage_score: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    source: str = Field(default="")
    license: str = Field(default="")
    tags: List[str] = Field(default_factory=list)
    fields: List[str] = Field(default_factory=list)
    sample_records: List[Dict[str, Any]] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)


class EmbeddingConfig(BaseModel):
    """嵌入配置模型"""
    model_name: str = Field(default="default")
    dimensions: int = Field(default=768)
    pooling_strategy: str = Field(default="mean")
    normalize: bool = Field(default=True)
    batch_size: int = Field(default=32)
    max_length: int = Field(default=512)
    precision: str = Field(default="float32")
    device: str = Field(default="cpu")


class VectorIndexConfig(BaseModel):
    """向量索引配置模型"""
    index_type: str = Field(default="hnsw")
    dimensions: int = Field(default=768)
    metric: str = Field(default="cosine")
    ef_construction: int = Field(default=200)
    M: int = Field(default=16)
    ef_search: int = Field(default=50)
    nlist: int = Field(default=1024)
    nprobe: int = Field(default=10)
    use_pca: bool = Field(default=False)
    pca_dimensions: int = Field(default=256)
    use_quantization: bool = Field(default=False)
    quantization_bits: int = Field(default=8)
