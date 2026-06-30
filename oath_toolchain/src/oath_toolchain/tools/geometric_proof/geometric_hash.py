"""几何哈希函数族模块。

提供基于高维空间几何特性的哈希函数，将数据映射到高维空间点，
利用空间距离、角度等几何特性计算哈希，提供基于几何的抗碰撞特性。
"""
from __future__ import annotations

import math
import struct
from typing import List, Tuple

from ...core.crypto.hash import Hash
from ...core.math.vector import Vector


class GeometricHash:
    """几何哈希函数类。

    将数据映射到高维空间点，利用空间几何特性（距离、角度、体积）
    计算哈希，提供基于几何的抗碰撞特性。

    Attributes:
        _dimensions: 空间维度数
        _hash_alg: 基础哈希算法名称
    """

    def __init__(self, dimensions: int = 4, hash_alg: str = 'sha256') -> None:
        """初始化几何哈希。

        Args:
            dimensions: 空间维度数，默认为4
            hash_alg: 基础哈希算法名称，默认为'sha256'

        Raises:
            ValueError: 当维度数小于2时
        """
        if dimensions < 2:
            raise ValueError("维度数必须大于等于2")

        self._dimensions = dimensions
        self._hash_alg = hash_alg

    @property
    def dimensions(self) -> int:
        """获取空间维度数。

        Returns:
            维度数
        """
        return self._dimensions

    @property
    def hash_alg(self) -> str:
        """获取基础哈希算法名称。

        Returns:
            哈希算法名称
        """
        return self._hash_alg

    def hash_data(self, data: bytes) -> bytes:
        """计算几何哈希。

        将数据映射到高维空间点，然后基于空间几何特性计算最终哈希值。

        Args:
            data: 输入数据

        Returns:
            几何哈希值
        """
        point = self.hash_to_point(data)
        components = point.to_list()

        hash_input = bytearray()
        for comp in components:
            hash_input.extend(struct.pack('>d', comp))

        hash_input.extend(data)
        return self._compute_hash(bytes(hash_input))

    def hash_to_point(self, data: bytes) -> Vector:
        """将数据哈希映射到空间点。

        使用多次哈希生成足够的随机数来构造高维空间点的坐标。

        Args:
            data: 输入数据

        Returns:
            映射后的空间点（向量）
        """
        components: List[float] = []
        counter = 0

        while len(components) < self._dimensions:
            hash_input = data + struct.pack('>I', counter)
            hash_bytes = self._compute_hash(hash_input)

            for i in range(0, len(hash_bytes) - 7, 8):
                if len(components) >= self._dimensions:
                    break
                chunk = hash_bytes[i:i + 8]
                value = struct.unpack('>Q', chunk)[0]
                normalized = value / (2 ** 64)
                components.append(normalized * 2.0 - 1.0)

            counter += 1

        return Vector(components[:self._dimensions])

    def distance_hash(self, data1: bytes, data2: bytes) -> float:
        """基于空间距离的哈希相似度。

        将两个数据点映射到空间中，计算它们之间的欧几里得距离。
        距离越小表示数据越相似。

        Args:
            data1: 第一个数据
            data2: 第二个数据

        Returns:
            两点之间的欧几里得距离，范围[0, 2*sqrt(dimensions)]
        """
        point1 = self.hash_to_point(data1)
        point2 = self.hash_to_point(data2)
        return point1.distance(point2)

    def geometric_roothash(self, data_blocks: List[bytes]) -> bytes:
        """基于几何排列的根哈希。

        将多个数据块映射到空间点，计算几何中心和各点到中心的距离，
        然后结合这些几何信息计算根哈希。

        Args:
            data_blocks: 数据块列表

        Returns:
            根哈希值

        Raises:
            ValueError: 当数据块列表为空时
        """
        if len(data_blocks) == 0:
            raise ValueError("数据块列表不能为空")

        points = [self.hash_to_point(block) for block in data_blocks]

        centroid = self._compute_centroid(points)

        distances = [point.distance(centroid) for point in points]

        sorted_points = sorted(
            points,
            key=lambda p: tuple(round(c, 10) for c in p.to_list())
        )

        angles = []
        if len(sorted_points) >= 2:
            ref_vec = sorted_points[0] - centroid
            for i in range(1, len(sorted_points)):
                vec = sorted_points[i] - centroid
                if ref_vec.norm() > 1e-10 and vec.norm() > 1e-10:
                    cos_theta = ref_vec.dot(vec) / (ref_vec.norm() * vec.norm())
                    cos_theta = max(-1.0, min(1.0, cos_theta))
                    angles.append(math.acos(cos_theta))
                else:
                    angles.append(0.0)

        block_hashes = [self._compute_hash(block) for block in data_blocks]
        sorted_block_hashes = sorted(block_hashes)

        hash_input = bytearray()
        for comp in centroid.to_list():
            hash_input.extend(struct.pack('>d', comp))
        for dist in sorted(distances):
            hash_input.extend(struct.pack('>d', dist))
        for angle in sorted(angles):
            hash_input.extend(struct.pack('>d', angle))

        for bh in sorted_block_hashes:
            hash_input.extend(bh)

        return self._compute_hash(bytes(hash_input))

    def _compute_hash(self, data: bytes) -> bytes:
        """使用指定算法计算哈希。

        Args:
            data: 输入数据

        Returns:
            哈希值
        """
        if self._hash_alg == 'sha256':
            return Hash.sha256(data)
        elif self._hash_alg == 'sha512':
            return Hash.sha512(data)
        elif self._hash_alg == 'sha3_256':
            return Hash.sha3_256(data)
        elif self._hash_alg == 'sha3_512':
            return Hash.sha3_512(data)
        elif self._hash_alg == 'blake2b':
            return Hash.blake2b(data)
        else:
            return Hash.sha256(data)

    def _compute_centroid(self, points: List[Vector]) -> Vector:
        """计算点集的几何中心（质心）。

        Args:
            points: 空间点列表

        Returns:
            质心点
        """
        if len(points) == 0:
            raise ValueError("点列表不能为空")

        dim = points[0].dim
        centroid_comps = [0.0] * dim

        for point in points:
            for i in range(dim):
                centroid_comps[i] += point[i]

        for i in range(dim):
            centroid_comps[i] /= len(points)

        return Vector(centroid_comps)

    def cosine_similarity_hash(self, data1: bytes, data2: bytes) -> float:
        """基于余弦相似度的哈希比较。

        将两个数据映射到空间点，计算它们之间的余弦相似度。

        Args:
            data1: 第一个数据
            data2: 第二个数据

        Returns:
            余弦相似度值，范围[-1, 1]
        """
        point1 = self.hash_to_point(data1)
        point2 = self.hash_to_point(data2)

        norm1 = point1.norm()
        norm2 = point2.norm()

        if norm1 < 1e-10 or norm2 < 1e-10:
            return 0.0

        return point1.dot(point2) / (norm1 * norm2)

    def hyperplane_hash(
        self,
        data: bytes,
        num_planes: int = 8,
        seed: bytes = b'geometric_hash_seed'
    ) -> Tuple[int, ...]:
        """基于超平面的哈希签名（LSH简化版）。

        生成一组随机超平面，根据数据点在各超平面的哪一侧生成签名。

        Args:
            data: 输入数据
            num_planes: 超平面数量
            seed: 随机种子

        Returns:
            超平面哈希签名元组
        """
        point = self.hash_to_point(data)
        planes = self._generate_planes(num_planes, seed)

        signature = []
        for normal, bias in planes:
            value = point.dot(normal) + bias
            signature.append(1 if value >= 0 else 0)

        return tuple(signature)

    def _generate_planes(
        self,
        num_planes: int,
        seed: bytes
    ) -> List[Tuple[Vector, float]]:
        """生成随机超平面。

        Args:
            num_planes: 超平面数量
            seed: 随机种子

        Returns:
            (法向量, 偏置)元组列表
        """
        planes: List[Tuple[Vector, float]] = []
        counter = 0

        while len(planes) < num_planes:
            hash_input = seed + struct.pack('>I', counter)
            hash_bytes = self._compute_hash(hash_input)

            normal_comps = []
            bias_bytes = b''
            byte_idx = 0

            for _ in range(self._dimensions):
                if byte_idx + 8 > len(hash_bytes):
                    counter += 1
                    hash_input = seed + struct.pack('>I', counter)
                    hash_bytes = self._compute_hash(hash_input)
                    byte_idx = 0

                chunk = hash_bytes[byte_idx:byte_idx + 8]
                value = struct.unpack('>q', chunk)[0]
                normalized = value / (2 ** 63)
                normal_comps.append(normalized)
                byte_idx += 8

            if byte_idx + 8 > len(hash_bytes):
                counter += 1
                hash_input = seed + struct.pack('>I', counter)
                hash_bytes = self._compute_hash(hash_input)
                byte_idx = 0

            bias_chunk = hash_bytes[byte_idx:byte_idx + 8]
            bias = struct.unpack('>q', bias_chunk)[0] / (2 ** 63)

            normal = Vector(normal_comps)
            if normal.norm() > 1e-10:
                normal = normal.normalize()
                planes.append((normal, bias))

            counter += 1

        return planes[:num_planes]
