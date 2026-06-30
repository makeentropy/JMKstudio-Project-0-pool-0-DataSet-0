"""哈希链模块。

提供哈希链数据结构的实现，常用于一次性口令、时间戳认证等场景。
"""
from __future__ import annotations

from typing import Optional

from ..crypto.hash import Hash


class HashChain:
    """哈希链类。

    实现哈希链数据结构，从种子开始反复哈希生成链。
    链的顶端（锚点）是最后一次哈希的结果。

    Attributes:
        _seed: 初始种子
        _length: 链的长度
        _hash_alg: 哈希算法
        _chain: 存储的哈希链（可选，用于优化）
        _anchor: 链的顶端锚点
    """

    def __init__(
        self,
        seed: bytes,
        length: int,
        hash_alg: str = "sha256",
        precompute: bool = False,
    ) -> None:
        """初始化哈希链。

        Args:
            seed: 初始种子
            length: 链的长度（包含种子和锚点）
            hash_alg: 哈希算法名称，默认为sha256
            precompute: 是否预计算整个链，默认为False

        Raises:
            ValueError: 当长度小于2时
        """
        if length < 2:
            raise ValueError("哈希链长度至少为2")

        self._seed = seed
        self._length = length
        self._hash_alg = hash_alg
        self._chain: Optional[list[bytes]] = None
        self._anchor: bytes = b""

        if precompute:
            self._precompute_chain()
        else:
            self._anchor = self._compute_anchor()

    def _hash(self, data: bytes) -> bytes:
        """计算哈希值。

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

    def _compute_anchor(self) -> bytes:
        """计算链的顶端锚点。

        Returns:
            锚点哈希值
        """
        current = self._seed
        for _ in range(self._length - 1):
            current = self._hash(current)
        return current

    def _precompute_chain(self) -> None:
        """预计算整个哈希链。"""
        chain = [self._seed]
        current = self._seed
        for _ in range(self._length - 1):
            current = self._hash(current)
            chain.append(current)
        self._chain = chain
        self._anchor = chain[-1]

    @property
    def anchor(self) -> bytes:
        """获取链的顶端锚点。

        Returns:
            锚点哈希值
        """
        return self._anchor

    @property
    def length(self) -> int:
        """获取链的长度。

        Returns:
            链的长度
        """
        return self._length

    @property
    def seed(self) -> bytes:
        """获取初始种子。

        Returns:
            种子数据
        """
        return self._seed

    def get_value(self, index: int) -> bytes:
        """获取指定索引处的值。

        索引0是种子，索引length-1是锚点。

        Args:
            index: 索引值（0 <= index < length）

        Returns:
            指定索引处的哈希值

        Raises:
            IndexError: 当索引超出范围时
        """
        if index < 0 or index >= self._length:
            raise IndexError(
                f"索引超出范围: {index}, 链长度: {self._length}"
            )

        if self._chain is not None:
            return self._chain[index]

        current = self._seed
        for _ in range(index):
            current = self._hash(current)
        return current

    def verify_value(
        self,
        value: bytes,
        index: int,
        anchor: bytes,
    ) -> bool:
        """验证某个值是否属于哈希链。

        将value反复哈希，直到达到锚点位置，
        然后与给定的锚点比较。

        Args:
            value: 待验证的值
            index: 值在链中的索引
            anchor: 链的锚点（顶端）

        Returns:
            验证通过返回True，否则返回False
        """
        if index < 0 or index >= self._length:
            return False

        iterations = (self._length - 1) - index
        if iterations < 0:
            return False

        current = value
        for _ in range(iterations):
            current = self._hash(current)

        return current == anchor

    def __len__(self) -> int:
        """返回链的长度。

        Returns:
            链的长度
        """
        return self._length

    def __repr__(self) -> str:
        """返回哈希链的字符串表示。

        Returns:
            字符串表示
        """
        return (
            f"HashChain(length={self._length}, "
            f"anchor={self._anchor.hex()[:16]}...)"
        )
