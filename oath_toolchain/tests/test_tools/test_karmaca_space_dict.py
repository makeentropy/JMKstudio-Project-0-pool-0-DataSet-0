"""KARMACA空间字典单元测试。"""
import os
import tempfile

import pytest

from oath_toolchain.core.math.vector import Vector
from oath_toolchain.tools.karmaca.space_dict import KarmaSpaceDict


class TestKarmaSpaceDict:
    """测试KarmaSpaceDict类。"""

    def test_initialization(self):
        """测试初始化。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        assert sd.dimensions == 3
        assert sd.key_size == 32
        assert sd.size == 0

    def test_initialization_invalid_dimensions(self):
        """测试无效维度初始化。"""
        with pytest.raises(ValueError):
            KarmaSpaceDict(dimensions=0)

    def test_initialization_invalid_key_size(self):
        """测试无效密钥大小初始化。"""
        with pytest.raises(ValueError):
            KarmaSpaceDict(key_size=0)

    def test_insert(self):
        """测试插入条目。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        coord = Vector([1.0, 2.0, 3.0])
        key = b"\x00" * 32
        sd.insert(coord, key)
        assert sd.size == 1

    def test_insert_dimension_mismatch(self):
        """测试维度不匹配的插入。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        coord = Vector([1.0, 2.0])
        key = b"\x00" * 32
        with pytest.raises(ValueError):
            sd.insert(coord, key)

    def test_insert_key_size_mismatch(self):
        """测试密钥长度不匹配的插入。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        coord = Vector([1.0, 2.0, 3.0])
        key = b"\x00" * 16
        with pytest.raises(ValueError):
            sd.insert(coord, key)

    def test_build(self):
        """测试批量构建。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        points = [Vector([i, i + 1, i + 2]) for i in range(10)]
        keys = [bytes([i] * 32) for i in range(10)]
        sd.build(points, keys)
        assert sd.size == 10

    def test_build_mismatched_lengths(self):
        """测试数量不匹配的构建。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        points = [Vector([i, i, i]) for i in range(5)]
        keys = [bytes([i] * 32) for i in range(10)]
        with pytest.raises(ValueError):
            sd.build(points, keys)

    def test_get_key(self):
        """测试获取密钥。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        coord = Vector([1.0, 2.0, 3.0])
        key = b"\x01" * 32
        sd.insert(coord, key)
        result = sd.get_key(Vector([1.0, 2.0, 3.0]))
        assert result == key

    def test_get_key_nearest_neighbor(self):
        """测试最近邻获取密钥。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        coord1 = Vector([0.0, 0.0, 0.0])
        key1 = b"\x01" * 32
        coord2 = Vector([10.0, 10.0, 10.0])
        key2 = b"\x02" * 32
        sd.insert(coord1, key1)
        sd.insert(coord2, key2)

        query = Vector([1.0, 1.0, 1.0])
        result = sd.get_key(query)
        assert result == key1

    def test_get_key_empty_dict(self):
        """测试空字典获取密钥。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            sd.get_key(Vector([1.0, 2.0, 3.0]))

    def test_get_key_dimension_mismatch(self):
        """测试维度不匹配的获取密钥。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)
        with pytest.raises(ValueError):
            sd.get_key(Vector([1.0, 2.0]))

    def test_remove(self):
        """测试删除条目。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        coord = Vector([1.0, 2.0, 3.0])
        key = b"\x00" * 32
        sd.insert(coord, key)
        assert sd.size == 1
        result = sd.remove(coord)
        assert result is True
        assert sd.size == 0

    def test_remove_nonexistent(self):
        """测试删除不存在的条目。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        coord = Vector([1.0, 2.0, 3.0])
        result = sd.remove(coord)
        assert result is False

    def test_remove_dimension_mismatch(self):
        """测试维度不匹配的删除。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            sd.remove(Vector([1.0, 2.0]))

    def test_expand_dimensions(self):
        """测试动态扩展维度。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)
        sd.expand_dimensions(5)
        assert sd.dimensions == 5
        assert sd.size == 1
        key = sd.get_key(Vector([1.0, 2.0, 3.0, 0.0, 0.0]))
        assert key == b"\x00" * 32

    def test_expand_dimensions_invalid(self):
        """测试无效的维度扩展。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            sd.expand_dimensions(3)
        with pytest.raises(ValueError):
            sd.expand_dimensions(2)

    def test_compress(self):
        """测试压缩字典。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([0.0, 0.0, 0.0]), b"\x01" * 32)
        sd.insert(Vector([0.01, 0.01, 0.01]), b"\x02" * 32)
        sd.insert(Vector([10.0, 10.0, 10.0]), b"\x03" * 32)

        merged = sd.compress(threshold=0.1)
        assert merged == 1
        assert sd.size == 2

    def test_compress_zero_threshold(self):
        """测试阈值为0的压缩。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            sd.compress(threshold=0)

    def test_compress_empty_dict(self):
        """测试空字典压缩。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        merged = sd.compress(threshold=1.0)
        assert merged == 0

    def test_query_range(self):
        """测试范围查询。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 1.0, 1.0]), b"\x01" * 32)
        sd.insert(Vector([5.0, 5.0, 5.0]), b"\x02" * 32)
        sd.insert(Vector([10.0, 10.0, 10.0]), b"\x03" * 32)

        min_coord = Vector([0.0, 0.0, 0.0])
        max_coord = Vector([6.0, 6.0, 6.0])
        results = sd.query_range(min_coord, max_coord)
        assert len(results) == 2

    def test_query_range_dimension_mismatch(self):
        """测试维度不匹配的范围查询。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)
        with pytest.raises(ValueError):
            sd.query_range(Vector([0.0, 0.0]), Vector([1.0, 1.0]))

    def test_get_nearest_neighbors(self):
        """测试k近邻搜索。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(10):
            sd.insert(Vector([float(i), float(i), float(i)]), bytes([i]) * 32)

        query = Vector([5.0, 5.0, 5.0])
        neighbors = sd.get_nearest_neighbors(query, k=3)
        assert len(neighbors) == 3
        assert neighbors[0][2] <= neighbors[1][2] <= neighbors[2][2]

    def test_get_nearest_neighbors_k_too_large(self):
        """测试k大于字典大小的情况。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)
        neighbors = sd.get_nearest_neighbors(Vector([1.0, 2.0, 3.0]), k=5)
        assert len(neighbors) == 1

    def test_get_nearest_neighbors_empty(self):
        """测试空字典的近邻搜索。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            sd.get_nearest_neighbors(Vector([1.0, 2.0, 3.0]))

    def test_get_nearest_neighbors_invalid_k(self):
        """测试无效k值。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)
        with pytest.raises(ValueError):
            sd.get_nearest_neighbors(Vector([1.0, 2.0, 3.0]), k=0)

    def test_get_nearest_neighbors_dimension_mismatch(self):
        """测试维度不匹配的近邻搜索。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)
        with pytest.raises(ValueError):
            sd.get_nearest_neighbors(Vector([1.0, 2.0]))

    def test_save_and_load(self):
        """测试保存和加载。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(5):
            sd.insert(Vector([float(i), float(i), float(i)]), bytes([i]) * 32)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            filepath = f.name

        try:
            sd.save(filepath)
            assert os.path.exists(filepath)

            sd2 = KarmaSpaceDict()
            sd2.load(filepath)
            assert sd2.dimensions == sd.dimensions
            assert sd2.key_size == sd.key_size
            assert sd2.size == sd.size
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件。"""
        sd = KarmaSpaceDict()
        with pytest.raises(FileNotFoundError):
            sd.load("/nonexistent/file.pkl")

    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(5):
            sd.insert(Vector([float(i), float(i + 1), float(i + 2)]), bytes([i]) * 32)

        data = sd.to_dict()
        assert "dimensions" in data
        assert "key_size" in data
        assert "points" in data
        assert "keys" in data

        sd2 = KarmaSpaceDict()
        sd2.from_dict(data)
        assert sd2.dimensions == sd.dimensions
        assert sd2.key_size == sd.key_size
        assert sd2.size == sd.size

    def test_from_dict_missing_fields(self):
        """测试缺少字段的反序列化。"""
        sd = KarmaSpaceDict()
        with pytest.raises(ValueError):
            sd.from_dict({"dimensions": 3})

    def test_from_dict_invalid_data(self):
        """测试无效数据的反序列化。"""
        sd = KarmaSpaceDict()
        with pytest.raises(ValueError):
            sd.from_dict(
                {
                    "dimensions": 3,
                    "key_size": 32,
                    "points": [[1.0, 2.0]],
                    "keys": ["00" * 32],
                }
            )

    def test_interpolate_key(self):
        """测试插值密钥生成。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([0.0, 0.0, 0.0]), b"\x00" * 32)
        sd.insert(Vector([10.0, 10.0, 10.0]), b"\xff" * 32)

        query = Vector([5.0, 5.0, 5.0])
        key = sd.interpolate_key(query, k=2)
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_interpolate_key_single_point(self):
        """测试单点插值。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        key_orig = b"\x55" * 32
        sd.insert(Vector([5.0, 5.0, 5.0]), key_orig)

        query = Vector([5.0, 5.0, 5.0])
        key = sd.interpolate_key(query, k=4)
        assert key == key_orig

    def test_interpolate_key_empty(self):
        """测试空字典插值。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            sd.interpolate_key(Vector([1.0, 2.0, 3.0]))

    def test_large_scale_10000_entries(self):
        """测试10000个条目的性能。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        points = []
        keys = []
        for i in range(100):
            for j in range(100):
                x = float(i)
                y = float(j)
                z = float(i + j)
                points.append(Vector([x, y, z]))
                keys.append(bytes([i % 256, j % 256] + [0] * 30))

        sd.build(points, keys)
        assert sd.size == 10000

        query = Vector([50.0, 50.0, 100.0])
        key = sd.get_key(query)
        assert len(key) == 32

    def test_deterministic_key_mapping(self):
        """测试相同坐标始终映射到相同密钥。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\xaa" * 32)
        sd.insert(Vector([4.0, 5.0, 6.0]), b"\xbb" * 32)

        key1 = sd.get_key(Vector([1.0, 2.0, 3.0]))
        key2 = sd.get_key(Vector([1.0, 2.0, 3.0]))
        assert key1 == key2

        key3 = sd.get_key(Vector([4.0, 5.0, 6.0]))
        assert key3 != key1
