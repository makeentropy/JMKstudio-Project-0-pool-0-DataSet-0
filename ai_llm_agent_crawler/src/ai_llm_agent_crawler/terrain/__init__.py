"""
维度空间地形模块

提供多维空间地形生成、熵模型、地形分析、维度变换等功能。

主要组件:
- 地形模型 (models): 地形数据结构、维度空间、熵场定义
- 地形生成 (generator): 基于噪声、分形、熵驱动的地形生成
- 熵模型 (entropy): 地形熵计算、熵场演化、熵驱动动力学
- 地形分析 (analyzer): 地形特征提取、梯度分析、临界点检测
- 维度变换 (transform): 维度投影、降维、升维变换
"""

from ai_llm_agent_crawler.terrain.models import (
    TerrainType,
    EntropyType,
    DimensionAxis,
    TerrainPoint,
    TerrainCell,
    TerrainMap,
    EntropyField,
    DimensionSpace,
    TerrainFeature,
    TerrainConfig,
    EntropyConfig,
)

from ai_llm_agent_crawler.terrain.generator import (
    NoiseGenerator,
    FractalGenerator,
    EntropyDrivenGenerator,
    TerrainGenerator,
    MultiScaleTerrainGenerator,
)

from ai_llm_agent_crawler.terrain.entropy import (
    EntropyCalculator,
    EntropyFieldEvolver,
    InformationEntropy,
    TopologicalEntropy,
    SpectralEntropy,
    EntropyDynamics,
)

from ai_llm_agent_crawler.terrain.analyzer import (
    TerrainAnalyzer,
    FeatureExtractor,
    GradientAnalyzer,
    CriticalPointDetector,
    TerrainClassifier,
)

from ai_llm_agent_crawler.terrain.transform import (
    DimensionTransformer,
    ProjectionEngine,
    DimensionalityReducer,
    DimensionalityExpander,
    SpaceWarper,
)

__all__ = [
    # 模型
    "TerrainType",
    "EntropyType",
    "DimensionAxis",
    "TerrainPoint",
    "TerrainCell",
    "TerrainMap",
    "EntropyField",
    "DimensionSpace",
    "TerrainFeature",
    "TerrainConfig",
    "EntropyConfig",
    # 地形生成
    "NoiseGenerator",
    "FractalGenerator",
    "EntropyDrivenGenerator",
    "TerrainGenerator",
    "MultiScaleTerrainGenerator",
    # 熵模型
    "EntropyCalculator",
    "EntropyFieldEvolver",
    "InformationEntropy",
    "TopologicalEntropy",
    "SpectralEntropy",
    "EntropyDynamics",
    # 地形分析
    "TerrainAnalyzer",
    "FeatureExtractor",
    "GradientAnalyzer",
    "CriticalPointDetector",
    "TerrainClassifier",
    # 维度变换
    "DimensionTransformer",
    "ProjectionEngine",
    "DimensionalityReducer",
    "DimensionalityExpander",
    "SpaceWarper",
]
