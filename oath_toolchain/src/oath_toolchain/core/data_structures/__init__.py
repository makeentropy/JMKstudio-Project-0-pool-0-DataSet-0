"""数据结构模块。

提供Merkle树、哈希链等高级数据结构。
"""

from .merkle import MerkleTree
from .hash_chain import HashChain

__all__ = [
    "MerkleTree",
    "HashChain",
]
