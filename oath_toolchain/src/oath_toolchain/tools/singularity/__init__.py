"""质能质量子奇点验证器工具模块。

提供基于数据质能模型的奇点检测和验证功能，包括数据质能计算、
奇点检测、密钥特征提取和综合验证。
"""

from .key_features import KeySingularityFeatures
from .mass_energy import DataMassEnergy
from .singularity_detector import (
    SingularityDetectionResult,
    SingularityDetector,
    SingularityPoint,
)
from .verifier import SingularityVerifier

__all__ = [
    "DataMassEnergy",
    "SingularityDetector",
    "SingularityPoint",
    "SingularityDetectionResult",
    "KeySingularityFeatures",
    "SingularityVerifier",
]
