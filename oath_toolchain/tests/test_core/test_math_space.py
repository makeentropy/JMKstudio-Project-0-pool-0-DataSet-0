"""空间运算库单元测试。"""
import pytest

from oath_toolchain.core.math.space import (
    SpacePoint,
    HyperPlane,
    SpaceHash,
    midpoint,
    scale_point,
    translate_point,
    point_on_side,
)
from oath_toolchain.core.math.vector import Vector


class TestSpacePoint:
    """测试SpacePoint类。"""

    def test_point_creation_from_list(self):
        """测试从列表创建点。"""
        p = SpacePoint([1, 2, 3])
        assert p.dim == 3
        assert p[0] == 1
        assert p[1] == 2
        assert p[2] == 3

    def test_point_creation_from_vector(self):
        """测试从向量创建点。"""
        v = Vector([1, 2, 3])
        p = SpacePoint(v)
        assert p.dim == 3
        assert p[0] == 1

    def test_point_creation_from_tuple(self):
        """测试从元组创建点。"""
        p = SpacePoint((1, 2, 3))
        assert p.dim == 3

    def test_point_coordinates(self):
        """测试坐标属性。"""
        p = SpacePoint([1, 2, 3])
        coords = p.coordinates
        assert isinstance(coords, Vector)
        assert coords == Vector([1, 2, 3])
        assert coords is not p._vector

    def test_point_distance_to(self):
        """测试两点间距离。"""
        p1 = SpacePoint([0, 0])
        p2 = SpacePoint([3, 4])
        assert abs(p1.distance_to(p2) - 5.0) < 1e-9

    def test_point_manhattan_distance_to(self):
        """测试曼哈顿距离。"""
        p1 = SpacePoint([0, 0])
        p2 = SpacePoint([3, 4])
        assert p1.manhattan_distance_to(p2) == 7

    def test_point_eq(self):
        """测试点相等。"""
        p1 = SpacePoint([1, 2, 3])
        p2 = SpacePoint([1, 2, 3])
        p3 = SpacePoint([1, 2, 4])
        assert p1 == p2
        assert p1 != p3

    def test_point_eq_non_point(self):
        """测试与非点比较。"""
        p = SpacePoint([1, 2, 3])
        assert p != "not a point"

    def test_point_repr(self):
        """测试repr表示。"""
        p = SpacePoint([1, 2, 3])
        r = repr(p)
        assert "SpacePoint" in r

    def test_point_str(self):
        """测试str表示。"""
        p = SpacePoint([1, 2, 3])
        s = str(p)
        assert "Point" in s


class TestHyperPlane:
    """测试HyperPlane类。"""

    def test_hyperplane_creation(self):
        """测试超平面创建。"""
        normal = Vector([1, 0, 0])
        plane = HyperPlane(normal, bias=5)
        assert plane.dim == 3
        assert plane.bias == 5

    def test_hyperplane_normal_normalized(self):
        """测试法向量已归一化。"""
        normal = Vector([3, 0, 0])
        plane = HyperPlane(normal)
        assert abs(plane.normal.norm() - 1.0) < 1e-9

    def test_hyperplane_zero_normal_raises(self):
        """测试零向量法向量抛出异常。"""
        with pytest.raises(ValueError):
            HyperPlane(Vector([0, 0, 0]))

    def test_hyperplane_evaluate(self):
        """测试超平面方程求值。"""
        plane = HyperPlane(Vector([1, 0, 0]), bias=-5)
        point = SpacePoint([10, 0, 0])
        assert abs(plane.evaluate(point) - 5.0) < 1e-9

    def test_hyperplane_side_positive(self):
        """测试正侧判断。"""
        plane = HyperPlane(Vector([1, 0, 0]), bias=0)
        point = SpacePoint([1, 0, 0])
        assert plane.side(point) == 1

    def test_hyperplane_side_negative(self):
        """测试负侧判断。"""
        plane = HyperPlane(Vector([1, 0, 0]), bias=0)
        point = SpacePoint([-1, 0, 0])
        assert plane.side(point) == -1

    def test_hyperplane_side_on_plane(self):
        """测试在超平面上。"""
        plane = HyperPlane(Vector([1, 0, 0]), bias=0)
        point = SpacePoint([0, 0, 0])
        assert plane.side(point) == 0

    def test_hyperplane_distance_to_point(self):
        """测试点到超平面距离。"""
        plane = HyperPlane(Vector([1, 0, 0]), bias=0)
        point = SpacePoint([5, 0, 0])
        assert abs(plane.distance_to_point(point) - 5.0) < 1e-9

    def test_hyperplane_project(self):
        """测试点投影。"""
        plane = HyperPlane(Vector([1, 0, 0]), bias=0)
        point = SpacePoint([5, 3, 4])
        projected = plane.project(point)
        assert projected[0] == 0
        assert projected[1] == 3
        assert projected[2] == 4

    def test_hyperplane_repr(self):
        """测试repr表示。"""
        plane = HyperPlane(Vector([1, 0, 0]))
        r = repr(plane)
        assert "HyperPlane" in r


class TestSpaceHash:
    """测试SpaceHash类。"""

    def test_spacehash_creation(self):
        """测试空间哈希创建。"""
        sh = SpaceHash(dimensions=3, bucket_size=1.0, num_hashes=4)
        assert sh.dimensions == 3
        assert sh.bucket_size == 1.0
        assert sh.num_hashes == 4

    def test_spacehash_invalid_dimensions(self):
        """测试无效维度。"""
        with pytest.raises(ValueError):
            SpaceHash(dimensions=0)

    def test_spacehash_invalid_bucket_size(self):
        """测试无效桶大小。"""
        with pytest.raises(ValueError):
            SpaceHash(dimensions=3, bucket_size=0)

    def test_spacehash_invalid_num_hashes(self):
        """测试无效哈希函数数量。"""
        with pytest.raises(ValueError):
            SpaceHash(dimensions=3, num_hashes=0)

    def test_spacehash_hash(self):
        """测试空间哈希。"""
        sh = SpaceHash(dimensions=3, bucket_size=1.0)
        p1 = SpacePoint([0.1, 0.2, 0.3])
        p2 = SpacePoint([0.5, 0.6, 0.7])
        h1 = sh.hash(p1)
        h2 = sh.hash(p2)
        assert isinstance(h1, str)
        assert len(h1) == 64  # SHA-256 hex
        assert h1 == h2  # 同一桶

    def test_spacehash_hash_different_buckets(self):
        """测试不同桶的哈希。"""
        sh = SpaceHash(dimensions=3, bucket_size=1.0)
        p1 = SpacePoint([0.5, 0.5, 0.5])
        p2 = SpacePoint([1.5, 0.5, 0.5])
        h1 = sh.hash(p1)
        h2 = sh.hash(p2)
        assert h1 != h2

    def test_spacehash_lsh_signature(self):
        """测试LSH签名。"""
        sh = SpaceHash(dimensions=3, bucket_size=1.0, num_hashes=4)
        p = SpacePoint([1, 2, 3])
        sig = sh.lsh_signature(p)
        assert len(sig) == 4
        assert all(s in (0, 1) for s in sig)

    def test_spacehash_are_similar_close_points(self):
        """测试相近点的相似性。"""
        sh = SpaceHash(dimensions=3, bucket_size=1.0, num_hashes=4)
        p1 = SpacePoint([0.1, 0.1, 0.1])
        p2 = SpacePoint([0.2, 0.2, 0.2])
        assert sh.are_similar(p1, p2, threshold=1) is True

    def test_spacehash_with_vector_input(self):
        """测试向量输入。"""
        sh = SpaceHash(dimensions=2)
        v = Vector([1.0, 2.0])
        h = sh.hash(v)
        assert isinstance(h, str)


class TestSpaceUtilityFunctions:
    """测试空间工具函数。"""

    def test_midpoint(self):
        """测试中点计算。"""
        p1 = SpacePoint([0, 0, 0])
        p2 = SpacePoint([2, 4, 6])
        mid = midpoint(p1, p2)
        assert mid == SpacePoint([1, 2, 3])

    def test_midpoint_dim_mismatch(self):
        """测试维度不匹配的中点。"""
        p1 = SpacePoint([0, 0])
        p2 = SpacePoint([2, 4, 6])
        with pytest.raises(ValueError):
            midpoint(p1, p2)

    def test_scale_point(self):
        """测试点缩放。"""
        p = SpacePoint([1, 2, 3])
        scaled = scale_point(p, 2)
        assert scaled == SpacePoint([2, 4, 6])

    def test_translate_point(self):
        """测试点平移。"""
        p = SpacePoint([1, 2, 3])
        offset = Vector([4, 5, 6])
        translated = translate_point(p, offset)
        assert translated == SpacePoint([5, 7, 9])

    def test_translate_point_with_spacepoint(self):
        """测试用SpacePoint平移。"""
        p = SpacePoint([1, 2, 3])
        offset = SpacePoint([4, 5, 6])
        translated = translate_point(p, offset)
        assert translated == SpacePoint([5, 7, 9])

    def test_point_on_side(self):
        """测试点在超平面哪一侧。"""
        plane = HyperPlane(Vector([1, 0, 0]), bias=0)
        point = SpacePoint([1, 0, 0])
        assert point_on_side(plane, point) == 1
