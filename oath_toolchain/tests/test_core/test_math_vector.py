"""N维向量运算库单元测试。"""
import math
import pytest

from oath_toolchain.core.math.vector import Vector, zeros, ones, random_vector


class TestVector:
    """测试Vector类。"""

    def test_vector_creation(self):
        """测试向量创建。"""
        v = Vector([1, 2, 3])
        assert v.dim == 3
        assert v[0] == 1
        assert v[1] == 2
        assert v[2] == 3

    def test_vector_creation_empty_raises(self):
        """测试空向量创建抛出异常。"""
        with pytest.raises(ValueError):
            Vector([])

    def test_vector_len(self):
        """测试len()函数。"""
        v = Vector([1, 2, 3])
        assert len(v) == 3

    def test_vector_iter(self):
        """测试向量迭代。"""
        v = Vector([1, 2, 3])
        components = list(v)
        assert components == [1, 2, 3]

    def test_vector_eq(self):
        """测试向量相等。"""
        v1 = Vector([1, 2, 3])
        v2 = Vector([1, 2, 3])
        v3 = Vector([1, 2, 4])
        assert v1 == v2
        assert v1 != v3

    def test_vector_eq_different_dim(self):
        """测试不同维度向量不相等。"""
        v1 = Vector([1, 2])
        v2 = Vector([1, 2, 3])
        assert v1 != v2

    def test_vector_eq_non_vector(self):
        """测试与非向量比较。"""
        v = Vector([1, 2, 3])
        assert v != "not a vector"

    def test_vector_add_vector(self):
        """测试向量加法。"""
        v1 = Vector([1, 2, 3])
        v2 = Vector([4, 5, 6])
        result = v1 + v2
        assert result == Vector([5, 7, 9])

    def test_vector_add_scalar(self):
        """测试向量加标量。"""
        v = Vector([1, 2, 3])
        result = v + 2
        assert result == Vector([3, 4, 5])

    def test_vector_radd_scalar(self):
        """测试右加标量。"""
        v = Vector([1, 2, 3])
        result = 2 + v
        assert result == Vector([3, 4, 5])

    def test_vector_add_dim_mismatch(self):
        """测试维度不匹配的向量加法。"""
        v1 = Vector([1, 2])
        v2 = Vector([1, 2, 3])
        with pytest.raises(ValueError):
            v1 + v2

    def test_vector_sub_vector(self):
        """测试向量减法。"""
        v1 = Vector([4, 5, 6])
        v2 = Vector([1, 2, 3])
        result = v1 - v2
        assert result == Vector([3, 3, 3])

    def test_vector_sub_scalar(self):
        """测试向量减标量。"""
        v = Vector([4, 5, 6])
        result = v - 1
        assert result == Vector([3, 4, 5])

    def test_vector_rsub_scalar(self):
        """测试右减标量。"""
        v = Vector([1, 2, 3])
        result = 10 - v
        assert result == Vector([9, 8, 7])

    def test_vector_mul_vector(self):
        """测试向量逐元素相乘。"""
        v1 = Vector([1, 2, 3])
        v2 = Vector([4, 5, 6])
        result = v1 * v2
        assert result == Vector([4, 10, 18])

    def test_vector_mul_scalar(self):
        """测试向量乘标量。"""
        v = Vector([1, 2, 3])
        result = v * 2
        assert result == Vector([2, 4, 6])

    def test_vector_rmul_scalar(self):
        """测试右乘标量。"""
        v = Vector([1, 2, 3])
        result = 2 * v
        assert result == Vector([2, 4, 6])

    def test_vector_truediv_vector(self):
        """测试向量逐元素相除。"""
        v1 = Vector([4, 6, 8])
        v2 = Vector([2, 3, 4])
        result = v1 / v2
        assert result == Vector([2, 2, 2])

    def test_vector_truediv_scalar(self):
        """测试向量除以标量。"""
        v = Vector([2, 4, 6])
        result = v / 2
        assert result == Vector([1, 2, 3])

    def test_vector_truediv_by_zero_scalar(self):
        """测试除以零标量。"""
        v = Vector([1, 2, 3])
        with pytest.raises(ZeroDivisionError):
            v / 0

    def test_vector_neg(self):
        """测试向量取反。"""
        v = Vector([1, -2, 3])
        result = -v
        assert result == Vector([-1, 2, -3])

    def test_vector_dot(self):
        """测试点积。"""
        v1 = Vector([1, 2, 3])
        v2 = Vector([4, 5, 6])
        result = v1.dot(v2)
        assert result == 32  # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32

    def test_vector_dot_dim_mismatch(self):
        """测试维度不匹配的点积。"""
        v1 = Vector([1, 2])
        v2 = Vector([1, 2, 3])
        with pytest.raises(ValueError):
            v1.dot(v2)

    def test_vector_cross(self):
        """测试叉积。"""
        v1 = Vector([1, 0, 0])
        v2 = Vector([0, 1, 0])
        result = v1.cross(v2)
        assert result == Vector([0, 0, 1])

    def test_vector_cross_not_3d(self):
        """测试非3维向量的叉积。"""
        v1 = Vector([1, 2])
        v2 = Vector([3, 4])
        with pytest.raises(ValueError):
            v1.cross(v2)

    def test_vector_norm(self):
        """测试向量范数。"""
        v = Vector([3, 4])
        assert abs(v.norm() - 5.0) < 1e-9

    def test_vector_normalize(self):
        """测试向量归一化。"""
        v = Vector([3, 4])
        normalized = v.normalize()
        assert abs(normalized.norm() - 1.0) < 1e-9

    def test_vector_normalize_zero_vector(self):
        """测试零向量归一化。"""
        v = Vector([0, 0, 0])
        with pytest.raises(ZeroDivisionError):
            v.normalize()

    def test_vector_distance(self):
        """测试欧几里得距离。"""
        v1 = Vector([0, 0])
        v2 = Vector([3, 4])
        assert abs(v1.distance(v2) - 5.0) < 1e-9

    def test_vector_manhattan_distance(self):
        """测试曼哈顿距离。"""
        v1 = Vector([0, 0])
        v2 = Vector([3, 4])
        assert v1.manhattan_distance(v2) == 7

    def test_vector_cosine_similarity(self):
        """测试余弦相似度。"""
        v1 = Vector([1, 0])
        v2 = Vector([0, 1])
        assert abs(v1.cosine_similarity(v2)) < 1e-9

    def test_vector_cosine_similarity_same_direction(self):
        """测试同向向量的余弦相似度。"""
        v1 = Vector([1, 2, 3])
        v2 = Vector([2, 4, 6])
        assert abs(v1.cosine_similarity(v2) - 1.0) < 1e-9

    def test_vector_angle(self):
        """测试夹角计算。"""
        v1 = Vector([1, 0])
        v2 = Vector([0, 1])
        assert abs(v1.angle(v2) - math.pi / 2) < 1e-9

    def test_vector_to_list(self):
        """测试转换为列表。"""
        v = Vector([1, 2, 3])
        lst = v.to_list()
        assert lst == [1, 2, 3]
        lst.append(4)
        assert v.dim == 3

    def test_vector_repr(self):
        """测试repr表示。"""
        v = Vector([1, 2, 3])
        r = repr(v)
        assert "Vector" in r
        assert "1, 2, 3" in r

    def test_vector_str(self):
        """测试str表示。"""
        v = Vector([1, 2, 3])
        s = str(v)
        assert "1, 2, 3" in s


class TestVectorFactoryFunctions:
    """测试向量工厂函数。"""

    def test_zeros(self):
        """测试全零向量。"""
        v = zeros(3)
        assert v == Vector([0, 0, 0])

    def test_zeros_invalid_dim(self):
        """测试无效维度的zeros。"""
        with pytest.raises(ValueError):
            zeros(0)

    def test_ones(self):
        """测试全一向量。"""
        v = ones(3)
        assert v == Vector([1, 1, 1])

    def test_ones_invalid_dim(self):
        """测试无效维度的ones。"""
        with pytest.raises(ValueError):
            ones(0)

    def test_random_vector(self):
        """测试随机向量。"""
        v = random_vector(5)
        assert v.dim == 5
        for x in v:
            assert 0 <= x < 1

    def test_random_vector_range(self):
        """测试指定范围的随机向量。"""
        v = random_vector(5, min_val=10, max_val=20)
        assert v.dim == 5
        for x in v:
            assert 10 <= x < 20

    def test_random_vector_invalid_dim(self):
        """测试无效维度的随机向量。"""
        with pytest.raises(ValueError):
            random_vector(0)
