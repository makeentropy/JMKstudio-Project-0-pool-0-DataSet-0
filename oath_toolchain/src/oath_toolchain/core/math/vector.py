"""N维向量运算库。

提供通用的N维向量运算，包括基本算术运算、距离计算、相似度计算等。
"""
from __future__ import annotations

import math
import random
from typing import Any, Iterable, Iterator, List, Union


class Vector:
    """N维向量类。

    支持基本的向量运算，包括加减乘除、点积、叉积、距离计算等。

    Attributes:
        _components: 向量分量列表
    """

    def __init__(self, components: Iterable[float]) -> None:
        """初始化向量。

        Args:
            components: 向量分量的可迭代对象

        Raises:
            ValueError: 当分量为空时
        """
        self._components: List[float] = list(components)
        if len(self._components) == 0:
            raise ValueError("向量至少需要一个分量")

    @property
    def dim(self) -> int:
        """向量维度。

        Returns:
            向量的维度数
        """
        return len(self._components)

    def __len__(self) -> int:
        """返回向量维度。

        Returns:
            向量的维度数
        """
        return len(self._components)

    def __getitem__(self, index: int) -> float:
        """获取指定索引的分量。

        Args:
            index: 分量索引

        Returns:
            指定索引的分量值

        Raises:
            IndexError: 当索引超出范围时
        """
        return self._components[index]

    def __iter__(self) -> Iterator[float]:
        """返回向量分量的迭代器。

        Returns:
            分量迭代器
        """
        return iter(self._components)

    def __eq__(self, other: object) -> bool:
        """判断两个向量是否相等。

        Args:
            other: 另一个向量

        Returns:
            相等返回True，否则返回False
        """
        if not isinstance(other, Vector):
            return NotImplemented
        if self.dim != other.dim:
            return False
        return all(
            abs(a - b) < 1e-9 for a, b in zip(self._components, other._components)
        )

    def __add__(self, other: Union[Vector, float]) -> Vector:
        """向量加法。

        Args:
            other: 另一个向量或标量

        Returns:
            相加后的新向量

        Raises:
            ValueError: 当向量维度不匹配时
        """
        if isinstance(other, Vector):
            if self.dim != other.dim:
                raise ValueError(
                    f"向量维度不匹配: {self.dim} vs {other.dim}"
                )
            return Vector(
                [a + b for a, b in zip(self._components, other._components)]
            )
        elif isinstance(other, (int, float)):
            return Vector([x + other for x in self._components])
        return NotImplemented

    def __radd__(self, other: Union[Vector, float]) -> Vector:
        """右加法。

        Args:
            other: 另一个向量或标量

        Returns:
            相加后的新向量
        """
        return self.__add__(other)

    def __sub__(self, other: Union[Vector, float]) -> Vector:
        """向量减法。

        Args:
            other: 另一个向量或标量

        Returns:
            相减后的新向量

        Raises:
            ValueError: 当向量维度不匹配时
        """
        if isinstance(other, Vector):
            if self.dim != other.dim:
                raise ValueError(
                    f"向量维度不匹配: {self.dim} vs {other.dim}"
                )
            return Vector(
                [a - b for a, b in zip(self._components, other._components)]
            )
        elif isinstance(other, (int, float)):
            return Vector([x - other for x in self._components])
        return NotImplemented

    def __rsub__(self, other: Union[Vector, float]) -> Vector:
        """右减法。

        Args:
            other: 另一个向量或标量

        Returns:
            相减后的新向量
        """
        if isinstance(other, (int, float)):
            return Vector([other - x for x in self._components])
        return NotImplemented

    def __mul__(self, other: Union[Vector, float]) -> Vector:
        """向量乘法（逐元素相乘或标量乘法）。

        Args:
            other: 另一个向量或标量

        Returns:
            相乘后的新向量

        Raises:
            ValueError: 当向量维度不匹配时
        """
        if isinstance(other, Vector):
            if self.dim != other.dim:
                raise ValueError(
                    f"向量维度不匹配: {self.dim} vs {other.dim}"
                )
            return Vector(
                [a * b for a, b in zip(self._components, other._components)]
            )
        elif isinstance(other, (int, float)):
            return Vector([x * other for x in self._components])
        return NotImplemented

    def __rmul__(self, other: Union[Vector, float]) -> Vector:
        """右乘法。

        Args:
            other: 另一个向量或标量

        Returns:
            相乘后的新向量
        """
        return self.__mul__(other)

    def __truediv__(self, other: Union[Vector, float]) -> Vector:
        """向量除法（逐元素相除或标量除法）。

        Args:
            other: 另一个向量或标量

        Returns:
            相除后的新向量

        Raises:
            ValueError: 当向量维度不匹配时
            ZeroDivisionError: 当除以零时
        """
        if isinstance(other, Vector):
            if self.dim != other.dim:
                raise ValueError(
                    f"向量维度不匹配: {self.dim} vs {other.dim}"
                )
            if any(b == 0 for b in other._components):
                raise ZeroDivisionError("向量除法中存在零分量")
            return Vector(
                [a / b for a, b in zip(self._components, other._components)]
            )
        elif isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("不能除以零")
            return Vector([x / other for x in self._components])
        return NotImplemented

    def __neg__(self) -> Vector:
        """向量取反。

        Returns:
            取反后的新向量
        """
        return Vector([-x for x in self._components])

    def __repr__(self) -> str:
        """返回向量的字符串表示。

        Returns:
            向量的字符串表示
        """
        return f"Vector({self._components})"

    def __str__(self) -> str:
        """返回向量的可读字符串。

        Returns:
            向量的可读字符串
        """
        return f"({', '.join(str(x) for x in self._components)})"

    def dot(self, other: Vector) -> float:
        """计算点积。

        Args:
            other: 另一个向量

        Returns:
            点积结果

        Raises:
            ValueError: 当向量维度不匹配时
        """
        if self.dim != other.dim:
            raise ValueError(
                f"向量维度不匹配: {self.dim} vs {other.dim}"
            )
        return sum(
            a * b for a, b in zip(self._components, other._components)
        )

    def cross(self, other: Vector) -> Vector:
        """计算叉积（仅支持3维向量）。

        Args:
            other: 另一个3维向量

        Returns:
            叉积结果向量

        Raises:
            ValueError: 当向量不是3维时
        """
        if self.dim != 3 or other.dim != 3:
            raise ValueError("叉积仅支持3维向量")
        x1, y1, z1 = self._components
        x2, y2, z2 = other._components
        return Vector([
            y1 * z2 - z1 * y2,
            z1 * x2 - x1 * z2,
            x1 * y2 - y1 * x2,
        ])

    def norm(self) -> float:
        """计算向量的欧几里得范数（长度/模）。

        Returns:
            向量的模长
        """
        return math.sqrt(sum(x * x for x in self._components))

    def normalize(self) -> Vector:
        """归一化向量（单位向量）。

        Returns:
            归一化后的单位向量

        Raises:
            ZeroDivisionError: 当向量是零向量时
        """
        length = self.norm()
        if length == 0:
            raise ZeroDivisionError("零向量无法归一化")
        return Vector([x / length for x in self._components])

    def distance(self, other: Vector) -> float:
        """计算与另一个向量的欧几里得距离。

        Args:
            other: 另一个向量

        Returns:
            欧几里得距离

        Raises:
            ValueError: 当向量维度不匹配时
        """
        if self.dim != other.dim:
            raise ValueError(
                f"向量维度不匹配: {self.dim} vs {other.dim}"
            )
        return math.sqrt(
            sum(
                (a - b) ** 2
                for a, b in zip(self._components, other._components)
            )
        )

    def manhattan_distance(self, other: Vector) -> float:
        """计算与另一个向量的曼哈顿距离。

        Args:
            other: 另一个向量

        Returns:
            曼哈顿距离

        Raises:
            ValueError: 当向量维度不匹配时
        """
        if self.dim != other.dim:
            raise ValueError(
                f"向量维度不匹配: {self.dim} vs {other.dim}"
            )
        return sum(
            abs(a - b) for a, b in zip(self._components, other._components)
        )

    def cosine_similarity(self, other: Vector) -> float:
        """计算与另一个向量的余弦相似度。

        Args:
            other: 另一个向量

        Returns:
            余弦相似度值，范围[-1, 1]

        Raises:
            ValueError: 当向量维度不匹配时
            ZeroDivisionError: 当任一向量是零向量时
        """
        if self.dim != other.dim:
            raise ValueError(
                f"向量维度不匹配: {self.dim} vs {other.dim}"
            )
        norm_self = self.norm()
        norm_other = other.norm()
        if norm_self == 0 or norm_other == 0:
            raise ZeroDivisionError("零向量无法计算余弦相似度")
        return self.dot(other) / (norm_self * norm_other)

    def angle(self, other: Vector) -> float:
        """计算与另一个向量的夹角（弧度）。

        Args:
            other: 另一个向量

        Returns:
            夹角的弧度值，范围[0, π]

        Raises:
            ValueError: 当向量维度不匹配时
            ZeroDivisionError: 当任一向量是零向量时
        """
        cos_theta = self.cosine_similarity(other)
        cos_theta = max(-1.0, min(1.0, cos_theta))
        return math.acos(cos_theta)

    def to_list(self) -> List[float]:
        """转换为列表。

        Returns:
            向量分量的列表副本
        """
        return list(self._components)


def zeros(n: int) -> Vector:
    """创建全零向量。

    Args:
        n: 向量维度

    Returns:
        n维全零向量

    Raises:
        ValueError: 当n小于1时
    """
    if n < 1:
        raise ValueError("向量维度必须大于0")
    return Vector([0.0] * n)


def ones(n: int) -> Vector:
    """创建全一向量。

    Args:
        n: 向量维度

    Returns:
        n维全一向量

    Raises:
        ValueError: 当n小于1时
    """
    if n < 1:
        raise ValueError("向量维度必须大于0")
    return Vector([1.0] * n)


def random_vector(n: int, min_val: float = 0.0, max_val: float = 1.0) -> Vector:
    """创建随机向量。

    Args:
        n: 向量维度
        min_val: 随机最小值（含）
        max_val: 随机最大值（不含）

    Returns:
        n维随机向量

    Raises:
        ValueError: 当n小于1时
    """
    if n < 1:
        raise ValueError("向量维度必须大于0")
    return Vector(
        [random.uniform(min_val, max_val) for _ in range(n)]
    )
