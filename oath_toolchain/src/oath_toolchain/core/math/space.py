"""空间运算库。

提供空间点、超平面、空间哈希等空间运算相关的类和工具函数。
"""
from __future__ import annotations

import hashlib
import math
from typing import List, Tuple, Union

from .vector import Vector


class SpacePoint:
    """空间点类。

    表示N维空间中的一个点，包装Vector类提供点相关的操作。

    Attributes:
        _vector: 内部存储的向量
    """

    def __init__(self, coordinates: Union[Vector, List[float], Tuple[float, ...]]) -> None:
        """初始化空间点。

        Args:
            coordinates: 点的坐标，可以是Vector、列表或元组
        """
        if isinstance(coordinates, Vector):
            self._vector = Vector(coordinates.to_list())
        else:
            self._vector = Vector(coordinates)

    @property
    def dim(self) -> int:
        """空间点的维度。

        Returns:
            空间维度数
        """
        return self._vector.dim

    @property
    def coordinates(self) -> Vector:
        """获取坐标向量。

        Returns:
            坐标向量的副本
        """
        return Vector(self._vector.to_list())

    def distance_to(self, other: SpacePoint) -> float:
        """计算到另一个点的欧几里得距离。

        Args:
            other: 另一个空间点

        Returns:
            欧几里得距离

        Raises:
            ValueError: 当维度不匹配时
        """
        return self._vector.distance(other._vector)

    def manhattan_distance_to(self, other: SpacePoint) -> float:
        """计算到另一个点的曼哈顿距离。

        Args:
            other: 另一个空间点

        Returns:
            曼哈顿距离

        Raises:
            ValueError: 当维度不匹配时
        """
        return self._vector.manhattan_distance(other._vector)

    def __getitem__(self, index: int) -> float:
        """获取指定维度的坐标。

        Args:
            index: 维度索引

        Returns:
            指定维度的坐标值
        """
        return self._vector[index]

    def __eq__(self, other: object) -> bool:
        """判断两个点是否相等。

        Args:
            other: 另一个点

        Returns:
            相等返回True，否则返回False
        """
        if not isinstance(other, SpacePoint):
            return NotImplemented
        return self._vector == other._vector

    def __repr__(self) -> str:
        """返回点的字符串表示。

        Returns:
            点的字符串表示
        """
        return f"SpacePoint({self._vector.to_list()})"

    def __str__(self) -> str:
        """返回点的可读字符串。

        Returns:
            点的可读字符串
        """
        return f"Point{str(self._vector)}"


class HyperPlane:
    """超平面类。

    表示N维空间中的超平面，用于空间划分。
    超平面方程: w · x + b = 0

    Attributes:
        _normal: 法向量
        _bias: 偏置项
    """

    def __init__(self, normal: Vector, bias: float = 0.0) -> None:
        """初始化超平面。

        Args:
            normal: 超平面的法向量
            bias: 偏置项
        """
        if normal.norm() == 0:
            raise ValueError("法向量不能是零向量")
        self._normal = normal.normalize()
        self._bias = bias

    @property
    def normal(self) -> Vector:
        """获取单位法向量。

        Returns:
            单位法向量的副本
        """
        return Vector(self._normal.to_list())

    @property
    def bias(self) -> float:
        """获取偏置项。

        Returns:
            偏置项值
        """
        return self._bias

    @property
    def dim(self) -> int:
        """超平面所在空间的维度。

        Returns:
            空间维度数
        """
        return self._normal.dim

    def evaluate(self, point: Union[SpacePoint, Vector]) -> float:
        """计算点代入超平面方程的值。

        Args:
            point: 空间点或向量

        Returns:
            w · x + b 的值
        """
        if isinstance(point, SpacePoint):
            vec = point.coordinates
        else:
            vec = point
        return self._normal.dot(vec) + self._bias

    def side(self, point: Union[SpacePoint, Vector]) -> int:
        """判断点在超平面的哪一侧。

        Args:
            point: 空间点或向量

        Returns:
            1表示在正侧，-1表示在负侧，0表示在超平面上
        """
        value = self.evaluate(point)
        if abs(value) < 1e-9:
            return 0
        return 1 if value > 0 else -1

    def distance_to_point(self, point: Union[SpacePoint, Vector]) -> float:
        """计算点到超平面的距离。

        Args:
            point: 空间点或向量

        Returns:
            点到超平面的距离（非负）
        """
        return abs(self.evaluate(point))

    def project(self, point: Union[SpacePoint, Vector]) -> SpacePoint:
        """计算点在超平面上的投影。

        Args:
            point: 空间点或向量

        Returns:
            投影点
        """
        if isinstance(point, SpacePoint):
            vec = point.coordinates
        else:
            vec = point
        distance = self.evaluate(point)
        projected = vec - distance * self._normal
        return SpacePoint(projected)

    def __repr__(self) -> str:
        """返回超平面的字符串表示。

        Returns:
            超平面的字符串表示
        """
        return f"HyperPlane(normal={self._normal.to_list()}, bias={self._bias})"


class SpaceHash:
    """空间哈希函数类。

    基于空间坐标生成哈希值，支持局部敏感哈希(LSH)的简化实现。
    """

    def __init__(self, dimensions: int, bucket_size: float = 1.0, num_hashes: int = 4) -> None:
        """初始化空间哈希。

        Args:
            dimensions: 空间维度
            bucket_size: 哈希桶大小
            num_hashes: 哈希函数数量

        Raises:
            ValueError: 当参数无效时
        """
        if dimensions < 1:
            raise ValueError("维度必须大于0")
        if bucket_size <= 0:
            raise ValueError("桶大小必须大于0")
        if num_hashes < 1:
            raise ValueError("哈希函数数量必须大于0")

        self._dimensions = dimensions
        self._bucket_size = bucket_size
        self._num_hashes = num_hashes
        self._hash_planes: List[HyperPlane] = []
        self._init_hash_planes()

    def _init_hash_planes(self) -> None:
        """初始化哈希超平面。"""
        import random

        random.seed(42)
        for i in range(self._num_hashes):
            components = []
            for _ in range(self._dimensions):
                components.append(random.uniform(-1.0, 1.0))
            normal = Vector(components)
            bias = random.uniform(-self._bucket_size, self._bucket_size)
            self._hash_planes.append(HyperPlane(normal, bias))

    def hash(self, point: Union[SpacePoint, Vector]) -> str:
        """计算点的空间哈希值。

        Args:
            point: 空间点或向量

        Returns:
            哈希值字符串
        """
        if isinstance(point, SpacePoint):
            vec = point.coordinates
        else:
            vec = point

        bucket_coords = []
        for i in range(self._dimensions):
            bucket = int(math.floor(vec[i] / self._bucket_size))
            bucket_coords.append(str(bucket))

        hash_input = "_".join(bucket_coords)
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def lsh_signature(self, point: Union[SpacePoint, Vector]) -> Tuple[int, ...]:
        """计算点的局部敏感哈希签名。

        Args:
            point: 空间点或向量

        Returns:
            LSH签名元组
        """
        if isinstance(point, SpacePoint):
            vec = point.coordinates
        else:
            vec = point

        signature = []
        for plane in self._hash_planes:
            side = plane.side(vec)
            signature.append(1 if side >= 0 else 0)
        return tuple(signature)

    def are_similar(
        self,
        point1: Union[SpacePoint, Vector],
        point2: Union[SpacePoint, Vector],
        threshold: int = 1,
    ) -> bool:
        """判断两个点是否相似（基于LSH）。

        Args:
            point1: 第一个点
            point2: 第二个点
            threshold: 允许的汉明距离阈值

        Returns:
            相似返回True，否则返回False
        """
        sig1 = self.lsh_signature(point1)
        sig2 = self.lsh_signature(point2)
        hamming_distance = sum(a != b for a, b in zip(sig1, sig2))
        return hamming_distance <= threshold

    @property
    def dimensions(self) -> int:
        """空间维度。

        Returns:
            空间维度数
        """
        return self._dimensions

    @property
    def bucket_size(self) -> float:
        """哈希桶大小。

        Returns:
            桶大小
        """
        return self._bucket_size

    @property
    def num_hashes(self) -> int:
        """哈希函数数量。

        Returns:
            哈希函数数量
        """
        return self._num_hashes


def midpoint(point1: SpacePoint, point2: SpacePoint) -> SpacePoint:
    """计算两点之间的中点。

    Args:
        point1: 第一个点
        point2: 第二个点

    Returns:
        中点

    Raises:
        ValueError: 当维度不匹配时
    """
    if point1.dim != point2.dim:
        raise ValueError(
            f"点维度不匹配: {point1.dim} vs {point2.dim}"
        )
    mid = (point1.coordinates + point2.coordinates) / 2.0
    return SpacePoint(mid)


def scale_point(point: SpacePoint, scale: float) -> SpacePoint:
    """缩放空间点坐标。

    Args:
        point: 空间点
        scale: 缩放因子

    Returns:
        缩放后的点
    """
    return SpacePoint(point.coordinates * scale)


def translate_point(point: SpacePoint, offset: Union[Vector, SpacePoint]) -> SpacePoint:
    """平移空间点。

    Args:
        point: 空间点
        offset: 平移向量

    Returns:
        平移后的点

    Raises:
        ValueError: 当维度不匹配时
    """
    if isinstance(offset, SpacePoint):
        offset_vec = offset.coordinates
    else:
        offset_vec = offset
    return SpacePoint(point.coordinates + offset_vec)


def point_on_side(
    plane: HyperPlane, point: Union[SpacePoint, Vector]
) -> int:
    """判断点在超平面的哪一侧（工具函数）。

    Args:
        plane: 超平面
        point: 空间点或向量

    Returns:
        1表示正侧，-1表示负侧，0表示在超平面上
    """
    return plane.side(point)
