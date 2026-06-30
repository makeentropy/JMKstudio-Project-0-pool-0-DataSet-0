"""Merkle树模块。

提供Merkle树数据结构的实现，支持生成证明和验证证明。
"""
from __future__ import annotations

from typing import List, Optional

from ..crypto.hash import Hash


class MerkleTree:
    """Merkle树类。

    实现Merkle树数据结构，用于高效验证数据完整性。

    Attributes:
        _leaves: 叶子节点哈希列表
        _tree: 完整的树结构（各层节点）
        _hash_alg: 哈希算法名称
    """

    def __init__(
        self,
        data_blocks: List[bytes],
        hash_alg: str = "sha256",
    ) -> None:
        """初始化Merkle树。

        Args:
            data_blocks: 数据块列表
            hash_alg: 哈希算法名称，默认为sha256

        Raises:
            ValueError: 当数据块列表为空时
        """
        if len(data_blocks) == 0:
            raise ValueError("数据块列表不能为空")

        self._hash_alg = hash_alg
        self._leaves: List[bytes] = [
            self._hash_data(block) for block in data_blocks
        ]
        self._tree: List[List[bytes]] = []
        self._build_tree()

    def _hash_data(self, data: bytes) -> bytes:
        """计算数据的哈希值。

        Args:
            data: 输入数据

        Returns:
            哈希值
        """
        return Hash.sha256(data) if self._hash_alg == "sha256" else self._hash_with_alg(data)

    def _hash_with_alg(self, data: bytes) -> bytes:
        """使用指定算法计算哈希。

        Args:
            data: 输入数据

        Returns:
            哈希值
        """
        if self._hash_alg == "sha256":
            return Hash.sha256(data)
        elif self._hash_alg == "sha512":
            return Hash.sha512(data)
        elif self._hash_alg == "sha3_256":
            return Hash.sha3_256(data)
        elif self._hash_alg == "blake2b":
            return Hash.blake2b(data)
        else:
            return Hash.sha256(data)

    def _build_tree(self) -> None:
        """构建Merkle树。"""
        self._tree = [list(self._leaves)]
        current_level = list(self._leaves)

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = (
                    current_level[i + 1]
                    if i + 1 < len(current_level)
                    else left
                )
                combined = left + right
                next_level.append(self._hash_with_alg(combined))
            self._tree.append(next_level)
            current_level = next_level

    @property
    def root(self) -> bytes:
        """获取Merkle根哈希。

        Returns:
            根哈希值
        """
        return self._tree[-1][0]

    @property
    def leaf_count(self) -> int:
        """获取叶子节点数量。

        Returns:
            叶子节点数量
        """
        return len(self._leaves)

    @property
    def depth(self) -> int:
        """获取树的深度。

        Returns:
            树的深度（层数-1）
        """
        return len(self._tree) - 1

    def generate_proof(self, index: int) -> List[bytes]:
        """生成指定叶子节点的Merkle证明。

        Args:
            index: 叶子节点索引

        Returns:
            证明路径上的兄弟节点哈希列表

        Raises:
            IndexError: 当索引超出范围时
        """
        if index < 0 or index >= len(self._leaves):
            raise IndexError(
                f"索引超出范围: {index}, 叶子数: {len(self._leaves)}"
            )

        proof: List[bytes] = []
        current_index = index

        for level in range(len(self._tree) - 1):
            current_level = self._tree[level]
            if current_index % 2 == 0:
                sibling_index = current_index + 1
                if sibling_index >= len(current_level):
                    sibling_index = current_index
            else:
                sibling_index = current_index - 1

            proof.append(current_level[sibling_index])
            current_index = current_index // 2

        return proof

    def verify_proof(
        self,
        data_block: bytes,
        proof: List[bytes],
        root: bytes,
        index: int,
    ) -> bool:
        """验证Merkle证明。

        Args:
            data_block: 数据块
            proof: 证明路径
            root: 根哈希
            index: 叶子节点索引

        Returns:
            验证通过返回True，否则返回False
        """
        current_hash = self._hash_with_alg(data_block)
        current_index = index

        for sibling_hash in proof:
            if current_index % 2 == 0:
                combined = current_hash + sibling_hash
            else:
                combined = sibling_hash + current_hash

            current_hash = self._hash_with_alg(combined)
            current_index = current_index // 2

        return current_hash == root

    def add_leaf(self, data_block: bytes) -> None:
        """添加新的叶子节点。

        注意：添加叶子会重建整棵树。

        Args:
            data_block: 新的数据块
        """
        leaf_hash = self._hash_with_alg(data_block)
        self._leaves.append(leaf_hash)
        self._build_tree()

    def get_leaf(self, index: int) -> bytes:
        """获取指定索引的叶子哈希。

        Args:
            index: 叶子节点索引

        Returns:
            叶子节点的哈希值

        Raises:
            IndexError: 当索引超出范围时
        """
        if index < 0 or index >= len(self._leaves):
            raise IndexError(
                f"索引超出范围: {index}, 叶子数: {len(self._leaves)}"
            )
        return self._leaves[index]

    def __len__(self) -> int:
        """返回叶子节点数量。

        Returns:
            叶子节点数量
        """
        return len(self._leaves)

    def __repr__(self) -> str:
        """返回Merkle树的字符串表示。

        Returns:
            字符串表示
        """
        return f"MerkleTree(leaf_count={len(self._leaves)}, root={self.root.hex()[:16]}...)"
