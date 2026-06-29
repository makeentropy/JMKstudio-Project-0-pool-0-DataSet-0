"""
维度空间地形 - 核心数据模型

定义地形、熵场、维度空间等核心数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field


class TerrainType(str, Enum):
    """地形类型枚举"""
    PLAIN = "plain"
    MOUNTAIN = "mountain"
    VALLEY = "valley"
    PLATEAU = "plateau"
    CANYON = "canyon"
    HILLS = "hills"
    BASIN = "basin"
    RIDGE = "ridge"
    CLIFF = "cliff"
    VOLCANO = "volcano"
    CRATER = "crater"
    ISLAND = "island"
    ARCHIPELAGO = "archipelago"
    ABYSS = "abyss"


class EntropyType(str, Enum):
    """熵类型枚举"""
    SHANNON = "shannon"
    RENYI = "renyi"
    TSALLIS = "tsallis"
    TOPOLOGICAL = "topological"
    SPECTRAL = "spectral"
    SAMPLE = "sample"
    KOLMOGOROV = "kolmogorov"
    PERMUTATION = "permutation"
    WAVELET = "wavelet"
    MULTISCALE = "multiscale"


class DimensionAxis(str, Enum):
    """维度轴枚举"""
    X = "x"
    Y = "y"
    Z = "z"
    TIME = "time"
    ENTROPY = "entropy"
    VALUE = "value"
    ENERGY = "energy"
    MASS = "mass"
    PHASE = "phase"
    FREQUENCY = "frequency"
    SCALE = "scale"
    DENSITY = "density"


class TerrainPoint(BaseModel):
    """地形点模型"""
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    height: float = Field(default=0.0)
    entropy: float = Field(default=0.0)
    gradient: float = Field(default=0.0)
    terrain_type: TerrainType = Field(default=TerrainType.PLAIN)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z, self.height, self.entropy, self.gradient])


class TerrainCell(BaseModel):
    """地形单元模型"""
    grid_x: int = Field(default=0, ge=0)
    grid_y: int = Field(default=0, ge=0)
    center: TerrainPoint = Field(default_factory=TerrainPoint)
    neighbors: List[Tuple[int, int]] = Field(default_factory=list)
    height_values: List[float] = Field(default_factory=list)
    entropy_values: List[float] = Field(default_factory=list)
    cell_type: TerrainType = Field(default=TerrainType.PLAIN)
    roughness: float = Field(default=0.0)
    slope: float = Field(default=0.0)
    aspect: float = Field(default=0.0)
    curvature: float = Field(default=0.0)
    is_critical: bool = Field(default=False)
    critical_type: str = Field(default="")

    @property
    def avg_height(self) -> float:
        return float(np.mean(self.height_values)) if self.height_values else 0.0

    @property
    def avg_entropy(self) -> float:
        return float(np.mean(self.entropy_values)) if self.entropy_values else 0.0

    @property
    def height_std(self) -> float:
        return float(np.std(self.height_values)) if self.height_values else 0.0


class TerrainMap(BaseModel):
    """地形图模型"""
    map_id: str = Field(default="")
    name: str = Field(default="")
    width: int = Field(default=128, ge=1)
    height: int = Field(default=128, ge=1)
    resolution: float = Field(default=1.0, gt=0.0)
    height_map: List[List[float]] = Field(default_factory=list)
    entropy_map: List[List[float]] = Field(default_factory=list)
    gradient_map: List[List[float]] = Field(default_factory=list)
    terrain_type_map: List[List[str]] = Field(default_factory=list)
    cells: List[List[TerrainCell]] = Field(default_factory=list)
    features: List["TerrainFeature"] = Field(default_factory=list)
    min_height: float = Field(default=0.0)
    max_height: float = Field(default=0.0)
    avg_height: float = Field(default=0.0)
    min_entropy: float = Field(default=0.0)
    max_entropy: float = Field(default=0.0)
    avg_entropy: float = Field(default=0.0)
    seed: int = Field(default=42)
    generation_method: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def get_height_at(self, x: int, y: int) -> float:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.height_map[y][x]
        return 0.0

    def get_entropy_at(self, x: int, y: int) -> float:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.entropy_map[y][x]
        return 0.0

    def to_numpy_height(self) -> np.ndarray:
        return np.array(self.height_map)

    def to_numpy_entropy(self) -> np.ndarray:
        return np.array(self.entropy_map)

    def calculate_statistics(self) -> None:
        if not self.height_map:
            return
        h = np.array(self.height_map)
        e = np.array(self.entropy_map) if self.entropy_map else np.zeros_like(h)
        self.min_height = float(h.min())
        self.max_height = float(h.max())
        self.avg_height = float(h.mean())
        self.min_entropy = float(e.min())
        self.max_entropy = float(e.max())
        self.avg_entropy = float(e.mean())


class EntropyField(BaseModel):
    """熵场模型"""
    field_id: str = Field(default="")
    name: str = Field(default="")
    dimensions: List[int] = Field(default_factory=lambda: [128, 128])
    data: List[float] = Field(default_factory=list)
    entropy_type: EntropyType = Field(default=EntropyType.SHANNON)
    min_value: float = Field(default=0.0)
    max_value: float = Field(default=0.0)
    mean_value: float = Field(default=0.0)
    std_value: float = Field(default=0.0)
    time_step: int = Field(default=0)
    evolution_rate: float = Field(default=0.01)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def to_numpy(self) -> np.ndarray:
        return np.array(self.data).reshape(self.dimensions)

    def from_numpy(self, arr: np.ndarray) -> None:
        self.dimensions = list(arr.shape)
        self.data = arr.flatten().tolist()
        self.min_value = float(arr.min())
        self.max_value = float(arr.max())
        self.mean_value = float(arr.mean())
        self.std_value = float(arr.std())


class DimensionSpace(BaseModel):
    """维度空间模型"""
    space_id: str = Field(default="")
    name: str = Field(default="")
    n_dimensions: int = Field(default=2, ge=1)
    axes: List[DimensionAxis] = Field(default_factory=lambda: [DimensionAxis.X, DimensionAxis.Y])
    dimension_names: List[str] = Field(default_factory=list)
    dimension_ranges: List[Tuple[float, float]] = Field(default_factory=list)
    points: List[List[float]] = Field(default_factory=list)
    point_values: List[float] = Field(default_factory=list)
    point_entropies: List[float] = Field(default_factory=list)
    manifolds: List[Dict[str, Any]] = Field(default_factory=list)
    metric: str = Field(default="euclidean")
    is_normalized: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def to_numpy_points(self) -> np.ndarray:
        return np.array(self.points)

    def get_point(self, index: int) -> Optional[List[float]]:
        if 0 <= index < len(self.points):
            return self.points[index]
        return None

    def add_point(self, point: List[float], value: float = 0.0, entropy: float = 0.0) -> int:
        self.points.append(point)
        self.point_values.append(value)
        self.point_entropies.append(entropy)
        return len(self.points) - 1

    def get_dimension_range(self, dim: int) -> Tuple[float, float]:
        if dim < len(self.dimension_ranges):
            return self.dimension_ranges[dim]
        return (0.0, 1.0)


class TerrainFeature(BaseModel):
    """地形特征模型"""
    feature_id: str = Field(default="")
    name: str = Field(default="")
    feature_type: str = Field(default="")
    center: Tuple[float, float] = Field(default=(0.0, 0.0))
    size: float = Field(default=0.0)
    height_range: Tuple[float, float] = Field(default=(0.0, 0.0))
    entropy_range: Tuple[float, float] = Field(default=(0.0, 0.0))
    boundary_points: List[Tuple[int, int]] = Field(default_factory=list)
    area: float = Field(default=0.0)
    volume: float = Field(default=0.0)
    prominence: float = Field(default=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TerrainConfig(BaseModel):
    """地形配置模型"""
    width: int = Field(default=128, ge=1)
    height: int = Field(default=128, ge=1)
    resolution: float = Field(default=1.0, gt=0.0)
    seed: int = Field(default=42)
    octaves: int = Field(default=6, ge=1)
    persistence: float = Field(default=0.5, gt=0.0)
    lacunarity: float = Field(default=2.0, gt=1.0)
    scale: float = Field(default=50.0, gt=0.0)
    height_multiplier: float = Field(default=100.0)
    base_height: float = Field(default=0.0)
    noise_type: str = Field(default="perlin")
    generation_method: str = Field(default="fractal")
    terrain_biomes: bool = Field(default=True)
    water_level: float = Field(default=0.3)
    mountain_level: float = Field(default=0.7)
    snow_level: float = Field(default=0.85)
    entropy_coupling: float = Field(default=0.3, ge=0.0, le=1.0)
    multi_scale: bool = Field(default=True)
    detail_levels: int = Field(default=4, ge=1)


class EntropyConfig(BaseModel):
    """熵配置模型"""
    entropy_type: EntropyType = Field(default=EntropyType.SHANNON)
    calculation_method: str = Field(default="histogram")
    bins: int = Field(default=50, ge=2)
    alpha: float = Field(default=2.0, gt=0.0)
    q: float = Field(default=1.0, gt=0.0)
    window_size: int = Field(default=16, ge=2)
    stride: int = Field(default=8, ge=1)
    normalize: bool = Field(default=True)
    base: float = Field(default=2.0, gt=1.0)
    kernel_size: int = Field(default=3, ge=1)
    multi_scale: bool = Field(default=True)
    scales: List[int] = Field(default_factory=lambda: [2, 4, 8, 16])
    evolution_rate: float = Field(default=0.01, ge=0.0)
    diffusion_rate: float = Field(default=0.1, ge=0.0)
    reaction_rate: float = Field(default=0.05, ge=0.0)
