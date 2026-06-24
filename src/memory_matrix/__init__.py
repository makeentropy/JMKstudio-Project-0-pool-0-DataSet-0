"""
memory_matrix - Singularity matrix memory space interface.

The 'quantum singularity space matrix' is the steganographic memory space
where decoded probe data is organized. It provides a multi-dimensional
key-value store with tag-based addressing, versioning, and event hooks.
"""

from .matrix import SingularityMatrix, MatrixCell, MatrixDimension
from .space import StegoMemorySpace, MemoryPool

__all__ = [
    "SingularityMatrix",
    "MatrixCell",
    "MatrixDimension",
    "StegoMemorySpace",
    "MemoryPool",
]
