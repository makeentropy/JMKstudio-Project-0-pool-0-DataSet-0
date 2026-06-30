"""数学模块。

提供向量运算、空间运算等数学工具。
"""

from .vector import Vector, zeros, ones, random_vector
from .space import (
    SpacePoint,
    HyperPlane,
    SpaceHash,
    midpoint,
    scale_point,
    translate_point,
    point_on_side,
)

__all__ = [
    "Vector",
    "zeros",
    "ones",
    "random_vector",
    "SpacePoint",
    "HyperPlane",
    "SpaceHash",
    "midpoint",
    "scale_point",
    "translate_point",
    "point_on_side",
]
