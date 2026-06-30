"""几何哈希函数单元测试。"""
import pytest

from oath_toolchain.tools.geometric_proof.geometric_hash import GeometricHash
from oath_toolchain.core.math.vector import Vector


class TestGeometricHash:
    """测试GeometricHash类。"""

    def test_initialization(self):
        """测试初始化。"""
        gh = GeometricHash(dimensions=4, hash_alg='sha256')
        assert gh.dimensions == 4
        assert gh.hash_alg == 'sha256'

    def test_initialization_min_dimensions(self):
        """测试最小维度初始化。"""
        gh = GeometricHash(dimensions=2)
        assert gh.dimensions == 2

    def test_initialization_invalid_dimensions(self):
        """测试无效维度初始化。"""
        with pytest.raises(ValueError):
            GeometricHash(dimensions=1)

    def test_initialization_zero_dimensions(self):
        """测试零维度初始化。"""
        with pytest.raises(ValueError):
            GeometricHash(dimensions=0)

    def test_hash_data_deterministic(self):
        """测试哈希的确定性。"""
        gh = GeometricHash(dimensions=4)
        data = b"test data"
        hash1 = gh.hash_data(data)
        hash2 = gh.hash_data(data)
        assert hash1 == hash2
        assert isinstance(hash1, bytes)
        assert len(hash1) == 32

    def test_hash_data_different_inputs(self):
        """测试不同输入产生不同哈希。"""
        gh = GeometricHash(dimensions=4)
        data1 = b"test data 1"
        data2 = b"test data 2"
        hash1 = gh.hash_data(data1)
        hash2 = gh.hash_data(data2)
        assert hash1 != hash2

    def test_hash_to_point(self):
        """测试哈希到空间点。"""
        gh = GeometricHash(dimensions=4)
        data = b"test data"
        point = gh.hash_to_point(data)
        assert isinstance(point, Vector)
        assert point.dim == 4
        for comp in point.to_list():
            assert -1.0 <= comp <= 1.0

    def test_hash_to_point_deterministic(self):
        """测试哈希到点的确定性。"""
        gh = GeometricHash(dimensions=4)
        data = b"test data"
        point1 = gh.hash_to_point(data)
        point2 = gh.hash_to_point(data)
        assert point1 == point2

    def test_hash_to_point_different_dimensions(self):
        """测试不同维度的哈希到点。"""
        gh3 = GeometricHash(dimensions=3)
        gh6 = GeometricHash(dimensions=6)
        data = b"test data"
        point3 = gh3.hash_to_point(data)
        point6 = gh6.hash_to_point(data)
        assert point3.dim == 3
        assert point6.dim == 6

    def test_distance_hash(self):
        """测试距离哈希。"""
        gh = GeometricHash(dimensions=4)
        data1 = b"test data 1"
        data2 = b"test data 2"
        distance = gh.distance_hash(data1, data2)
        assert isinstance(distance, float)
        assert distance >= 0.0

    def test_distance_hash_same_data(self):
        """测试相同数据的距离哈希为0。"""
        gh = GeometricHash(dimensions=4)
        data = b"test data"
        distance = gh.distance_hash(data, data)
        assert distance == pytest.approx(0.0, abs=1e-9)

    def test_cosine_similarity_hash(self):
        """测试余弦相似度哈希。"""
        gh = GeometricHash(dimensions=4)
        data1 = b"test data 1"
        data2 = b"test data 2"
        similarity = gh.cosine_similarity_hash(data1, data2)
        assert isinstance(similarity, float)
        assert -1.0 <= similarity <= 1.0

    def test_cosine_similarity_same_data(self):
        """测试相同数据的余弦相似度为1。"""
        gh = GeometricHash(dimensions=4)
        data = b"test data"
        similarity = gh.cosine_similarity_hash(data, data)
        assert similarity == pytest.approx(1.0, abs=1e-9)

    def test_geometric_roothash(self):
        """测试几何根哈希。"""
        gh = GeometricHash(dimensions=4)
        blocks = [
            b"block 1",
            b"block 2",
            b"block 3",
            b"block 4",
        ]
        root = gh.geometric_roothash(blocks)
        assert isinstance(root, bytes)
        assert len(root) == 32

    def test_geometric_roothash_deterministic(self):
        """测试几何根哈希的确定性。"""
        gh = GeometricHash(dimensions=4)
        blocks = [b"block 1", b"block 2", b"block 3"]
        root1 = gh.geometric_roothash(blocks)
        root2 = gh.geometric_roothash(blocks)
        assert root1 == root2

    def test_geometric_roothash_empty(self):
        """测试空数据块列表的几何根哈希。"""
        gh = GeometricHash(dimensions=4)
        with pytest.raises(ValueError):
            gh.geometric_roothash([])

    def test_geometric_roothash_single_block(self):
        """测试单个数据块的几何根哈希。"""
        gh = GeometricHash(dimensions=4)
        blocks = [b"single block"]
        root = gh.geometric_roothash(blocks)
        assert isinstance(root, bytes)
        assert len(root) == 32

    def test_geometric_roothash_order_independence(self):
        """测试几何根哈希是否与顺序无关（几何特性）。"""
        gh = GeometricHash(dimensions=4)
        blocks1 = [b"block 1", b"block 2", b"block 3"]
        blocks2 = [b"block 3", b"block 1", b"block 2"]
        root1 = gh.geometric_roothash(blocks1)
        root2 = gh.geometric_roothash(blocks2)
        assert root1 == root2

    def test_hyperplane_hash(self):
        """测试超平面哈希。"""
        gh = GeometricHash(dimensions=4)
        data = b"test data"
        signature = gh.hyperplane_hash(data, num_planes=8)
        assert isinstance(signature, tuple)
        assert len(signature) == 8
        for bit in signature:
            assert bit in (0, 1)

    def test_hyperplane_hash_deterministic(self):
        """测试超平面哈希的确定性。"""
        gh = GeometricHash(dimensions=4)
        data = b"test data"
        sig1 = gh.hyperplane_hash(data, num_planes=8)
        sig2 = gh.hyperplane_hash(data, num_planes=8)
        assert sig1 == sig2

    def test_hyperplane_hash_different_data(self):
        """测试不同数据的超平面哈希。"""
        gh = GeometricHash(dimensions=4)
        data1 = b"test data 1"
        data2 = b"test data 2"
        sig1 = gh.hyperplane_hash(data1, num_planes=8)
        sig2 = gh.hyperplane_hash(data2, num_planes=8)
        assert isinstance(sig1, tuple)
        assert isinstance(sig2, tuple)
        assert len(sig1) == 8
        assert len(sig2) == 8

    def test_hyperplane_hash_different_seed(self):
        """测试不同种子的超平面哈希。"""
        gh = GeometricHash(dimensions=4)
        data = b"test data"
        sig1 = gh.hyperplane_hash(data, num_planes=8, seed=b"seed1")
        sig2 = gh.hyperplane_hash(data, num_planes=8, seed=b"seed2")
        assert isinstance(sig1, tuple)
        assert isinstance(sig2, tuple)

    def test_different_hash_algorithms(self):
        """测试不同哈希算法。"""
        data = b"test data"
        gh_sha256 = GeometricHash(dimensions=4, hash_alg='sha256')
        gh_sha512 = GeometricHash(dimensions=4, hash_alg='sha512')

        hash_sha256 = gh_sha256.hash_data(data)
        hash_sha512 = gh_sha512.hash_data(data)

        assert len(hash_sha256) == 32
        assert len(hash_sha512) == 64

    def test_high_dimensions(self):
        """测试高维度。"""
        gh = GeometricHash(dimensions=16)
        data = b"test data"
        point = gh.hash_to_point(data)
        assert point.dim == 16

    def test_hash_to_point_range(self):
        """测试哈希到点的坐标范围。"""
        gh = GeometricHash(dimensions=8)
        for i in range(100):
            data = f"test data {i}".encode()
            point = gh.hash_to_point(data)
            for comp in point.to_list():
                assert -1.0 <= comp <= 1.0
