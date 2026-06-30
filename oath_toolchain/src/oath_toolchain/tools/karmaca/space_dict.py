"""KARMACA空间字典模块。

提供基于多维空间坐标映射到加密密钥的空间字典实现，
支持动态维度扩展、压缩、范围查询和k近邻搜索等功能。
"""
from __future__ import annotations

import pickle
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ...core.math.vector import Vector


class KarmaSpaceDict:
    """KARMACA空间字典类。

    将N维空间坐标映射到加密密钥的字典结构，支持多维空间插值、
    动态维度扩展、压缩和快速近邻搜索。

    Attributes:
        _dimensions: 空间维度数
        _key_size: 密钥字节数
        _points: 存储的坐标点列表
        _keys: 对应的密钥列表
        _space_hash: 空间哈希用于快速查找
    """

    def __init__(self, dimensions: int = 3, key_size: int = 32) -> None:
        """初始化空间字典。

        Args:
            dimensions: 空间维度数，默认为3
            key_size: 密钥字节数，默认为32（256位）

        Raises:
            ValueError: 当参数无效时
        """
        if dimensions < 1:
            raise ValueError("维度数必须大于0")
        if key_size < 1:
            raise ValueError("密钥大小必须大于0")

        self._dimensions = dimensions
        self._key_size = key_size
        self._points: List[Vector] = []
        self._keys: List[bytes] = []

    @property
    def dimensions(self) -> int:
        """获取空间维度数。

        Returns:
            维度数
        """
        return self._dimensions

    @property
    def key_size(self) -> int:
        """获取密钥字节数。

        Returns:
            密钥字节数
        """
        return self._key_size

    @property
    def size(self) -> int:
        """获取字典条目数。

        Returns:
            条目数量
        """
        return len(self._points)

    def build(self, data_points: List[Vector], keys: List[bytes]) -> None:
        """批量构建空间字典。

        Args:
            data_points: 坐标点列表
            keys: 对应的密钥列表

        Raises:
            ValueError: 当参数无效时
        """
        if len(data_points) != len(keys):
            raise ValueError("坐标点数量与密钥数量不匹配")

        for point in data_points:
            if point.dim != self._dimensions:
                raise ValueError(
                    f"坐标维度不匹配: 期望{self._dimensions}维，实际{point.dim}维"
                )

        for key in keys:
            if len(key) != self._key_size:
                raise ValueError(
                    f"密钥长度不匹配: 期望{self._key_size}字节，实际{len(key)}字节"
                )

        self._points = list(data_points)
        self._keys = list(keys)

    def insert(self, coordinate: Vector, key: bytes) -> None:
        """插入单个条目。

        Args:
            coordinate: 空间坐标
            key: 对应的密钥

        Raises:
            ValueError: 当参数无效时
        """
        if coordinate.dim != self._dimensions:
            raise ValueError(
                f"坐标维度不匹配: 期望{self._dimensions}维，实际{coordinate.dim}维"
            )
        if len(key) != self._key_size:
            raise ValueError(
                f"密钥长度不匹配: 期望{self._key_size}字节，实际{len(key)}字节"
            )

        self._points.append(Vector(coordinate.to_list()))
        self._keys.append(key)

    def get_key(self, coordinate: Vector) -> bytes:
        """根据坐标获取密钥（最近邻）。

        Args:
            coordinate: 查询坐标

        Returns:
            最近邻点对应的密钥

        Raises:
            ValueError: 当坐标维度不匹配或字典为空时
        """
        if coordinate.dim != self._dimensions:
            raise ValueError(
                f"坐标维度不匹配: 期望{self._dimensions}维，实际{coordinate.dim}维"
            )
        if self.size == 0:
            raise ValueError("空间字典为空")

        nearest_idx = self._find_nearest_neighbor(coordinate)
        return self._keys[nearest_idx]

    def remove(self, coordinate: Vector) -> bool:
        """删除条目。

        Args:
            coordinate: 要删除的坐标

        Returns:
            删除成功返回True，未找到返回False

        Raises:
            ValueError: 当坐标维度不匹配时
        """
        if coordinate.dim != self._dimensions:
            raise ValueError(
                f"坐标维度不匹配: 期望{self._dimensions}维，实际{coordinate.dim}维"
            )

        for i, point in enumerate(self._points):
            if point == coordinate:
                del self._points[i]
                del self._keys[i]
                return True
        return False

    def expand_dimensions(self, new_dimensions: int) -> None:
        """动态扩展维度。

        Args:
            new_dimensions: 新的维度数，必须大于当前维度

        Raises:
            ValueError: 当新维度数小于等于当前维度时
        """
        if new_dimensions <= self._dimensions:
            raise ValueError(
                f"新维度数必须大于当前维度: {new_dimensions} <= {self._dimensions}"
            )

        extra_dims = new_dimensions - self._dimensions
        expanded_points = []
        for point in self._points:
            new_components = point.to_list() + [0.0] * extra_dims
            expanded_points.append(Vector(new_components))

        self._points = expanded_points
        self._dimensions = new_dimensions

    def compress(self, threshold: float) -> int:
        """压缩字典（合并相近点）。

        合并距离小于阈值的点，保留第一个点的密钥。

        Args:
            threshold: 合并阈值（欧几里得距离）

        Returns:
            被合并的条目数量

        Raises:
            ValueError: 当阈值无效时
        """
        if threshold <= 0:
            raise ValueError("阈值必须大于0")

        if self.size == 0:
            return 0

        kept_points: List[Vector] = []
        kept_keys: List[bytes] = []
        merged_count = 0

        for i, point in enumerate(self._points):
            should_keep = True
            for kept_point in kept_points:
                if point.distance(kept_point) < threshold:
                    should_keep = False
                    merged_count += 1
                    break
            if should_keep:
                kept_points.append(point)
                kept_keys.append(self._keys[i])

        self._points = kept_points
        self._keys = kept_keys
        return merged_count

    def query_range(
        self, min_coord: Vector, max_coord: Vector
    ) -> List[Tuple[Vector, bytes]]:
        """范围查询。

        Args:
            min_coord: 最小坐标
            max_coord: 最大坐标

        Returns:
            范围内的(坐标, 密钥)元组列表

        Raises:
            ValueError: 当坐标维度不匹配时
        """
        if min_coord.dim != self._dimensions:
            raise ValueError(
                f"最小坐标维度不匹配: 期望{self._dimensions}维，实际{min_coord.dim}维"
            )
        if max_coord.dim != self._dimensions:
            raise ValueError(
                f"最大坐标维度不匹配: 期望{self._dimensions}维，实际{max_coord.dim}维"
            )

        result = []
        for i, point in enumerate(self._points):
            in_range = True
            for d in range(self._dimensions):
                if point[d] < min_coord[d] or point[d] > max_coord[d]:
                    in_range = False
                    break
            if in_range:
                result.append((Vector(point.to_list()), self._keys[i]))
        return result

    def get_nearest_neighbors(
        self, coordinate: Vector, k: int = 5
    ) -> List[Tuple[Vector, bytes, float]]:
        """k近邻搜索。

        Args:
            coordinate: 查询坐标
            k: 返回的近邻数量

        Returns:
            近邻列表，每个元素为(坐标, 密钥, 距离)元组，按距离升序排列

        Raises:
            ValueError: 当参数无效时
        """
        if coordinate.dim != self._dimensions:
            raise ValueError(
                f"坐标维度不匹配: 期望{self._dimensions}维，实际{coordinate.dim}维"
            )
        if k < 1:
            raise ValueError("k必须大于0")
        if self.size == 0:
            raise ValueError("空间字典为空")

        distances = []
        for i, point in enumerate(self._points):
            dist = coordinate.distance(point)
            distances.append((i, dist))

        distances.sort(key=lambda x: x[1])

        k = min(k, self.size)
        result = []
        for i in range(k):
            idx, dist = distances[i]
            result.append((Vector(self._points[idx].to_list()), self._keys[idx], dist))
        return result

    def save(self, filepath: str) -> None:
        """持久化保存到文件。

        Args:
            filepath: 文件路径
        """
        data = self.to_dict()
        with open(filepath, "wb") as f:
            pickle.dump(data, f)

    def load(self, filepath: str) -> None:
        """从文件加载。

        Args:
            filepath: 文件路径

        Raises:
            FileNotFoundError: 当文件不存在时
            ValueError: 当文件格式无效时
        """
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)
            self.from_dict(data)
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"加载空间字典失败: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。

        Returns:
            序列化后的字典
        """
        return {
            "dimensions": self._dimensions,
            "key_size": self._key_size,
            "points": [p.to_list() for p in self._points],
            "keys": [k.hex() for k in self._keys],
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """从字典反序列化。

        Args:
            data: 序列化字典

        Raises:
            ValueError: 当数据格式无效时
        """
        required_fields = ["dimensions", "key_size", "points", "keys"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必要字段: {field}")

        dimensions = data["dimensions"]
        key_size = data["key_size"]
        points_data = data["points"]
        keys_data = data["keys"]

        if not isinstance(dimensions, int) or dimensions < 1:
            raise ValueError("维度数无效")
        if not isinstance(key_size, int) or key_size < 1:
            raise ValueError("密钥大小无效")
        if len(points_data) != len(keys_data):
            raise ValueError("坐标点数量与密钥数量不匹配")

        points = []
        for p in points_data:
            if len(p) != dimensions:
                raise ValueError(f"坐标维度不匹配: 期望{dimensions}维")
            points.append(Vector(p))

        keys = []
        for k in keys_data:
            key_bytes = bytes.fromhex(k)
            if len(key_bytes) != key_size:
                raise ValueError(f"密钥长度不匹配: 期望{key_size}字节")
            keys.append(key_bytes)

        self._dimensions = dimensions
        self._key_size = key_size
        self._points = points
        self._keys = keys

    def _find_nearest_neighbor(self, coordinate: Vector) -> int:
        """查找最近邻点的索引。

        Args:
            coordinate: 查询坐标

        Returns:
            最近邻点的索引
        """
        min_dist = float("inf")
        min_idx = 0
        for i, point in enumerate(self._points):
            dist = coordinate.distance(point)
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        return min_idx

    def interpolate_key(self, coordinate: Vector, k: int = 4) -> bytes:
        """基于k近邻插值生成密钥。

        使用反距离加权插值（IDW）对k个最近邻的密钥进行插值，
        生成查询位置的密钥。

        Args:
            coordinate: 查询坐标
            k: 用于插值的近邻数量

        Returns:
            插值生成的密钥

        Raises:
            ValueError: 当参数无效时
        """
        if coordinate.dim != self._dimensions:
            raise ValueError(
                f"坐标维度不匹配: 期望{self._dimensions}维，实际{coordinate.dim}维"
            )
        if k < 1:
            raise ValueError("k必须大于0")
        if self.size == 0:
            raise ValueError("空间字典为空")

        neighbors = self.get_nearest_neighbors(coordinate, k)

        if len(neighbors) == 1 or neighbors[0][2] < 1e-10:
            return neighbors[0][1]

        weights = []
        for _, _, dist in neighbors:
            if dist < 1e-10:
                return neighbors[0][1]
            weights.append(1.0 / (dist ** 2))

        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        key_arrays = []
        for _, key, _ in neighbors:
            key_arrays.append(np.frombuffer(key, dtype=np.uint8))

        interpolated = np.zeros(self._key_size, dtype=np.float64)
        for i, key_arr in enumerate(key_arrays):
            interpolated += normalized_weights[i] * key_arr.astype(np.float64)

        interpolated = np.clip(interpolated, 0, 255).astype(np.uint8)
        return interpolated.tobytes()
