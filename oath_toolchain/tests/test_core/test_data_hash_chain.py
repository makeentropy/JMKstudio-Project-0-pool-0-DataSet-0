"""哈希链单元测试。"""
import pytest

from oath_toolchain.core.data_structures.hash_chain import HashChain
from oath_toolchain.core.crypto.hash import Hash


class TestHashChain:
    """测试HashChain类。"""

    def test_hash_chain_creation(self):
        """测试哈希链创建。"""
        seed = b"seed"
        chain = HashChain(seed, length=5)
        assert chain.length == 5
        assert chain.seed == seed
        assert chain.anchor is not None
        assert len(chain.anchor) == 32

    def test_hash_chain_min_length(self):
        """测试最小长度。"""
        chain = HashChain(b"seed", length=2)
        assert chain.length == 2

    def test_hash_chain_length_too_small(self):
        """测试长度过小。"""
        with pytest.raises(ValueError):
            HashChain(b"seed", length=1)

    def test_hash_chain_precompute(self):
        """测试预计算模式。"""
        seed = b"seed"
        chain = HashChain(seed, length=5, precompute=True)
        assert chain.length == 5
        assert chain.anchor is not None

    def test_get_value_seed(self):
        """测试获取种子值（索引0）。"""
        seed = b"my_seed"
        chain = HashChain(seed, length=5)
        assert chain.get_value(0) == seed

    def test_get_value_anchor(self):
        """测试获取锚点值。"""
        seed = b"seed"
        chain = HashChain(seed, length=5)
        assert chain.get_value(4) == chain.anchor

    def test_get_value(self):
        """测试获取中间值。"""
        seed = b"seed"
        chain = HashChain(seed, length=5)

        expected = seed
        for i in range(5):
            assert chain.get_value(i) == expected
            expected = Hash.sha256(expected)

    def test_get_value_invalid_index(self):
        """测试无效索引。"""
        chain = HashChain(b"seed", length=5)
        with pytest.raises(IndexError):
            chain.get_value(5)
        with pytest.raises(IndexError):
            chain.get_value(-1)

    def test_get_value_precompute(self):
        """测试预计算模式下获取值。"""
        seed = b"seed"
        chain = HashChain(seed, length=5, precompute=True)

        expected = seed
        for i in range(5):
            assert chain.get_value(i) == expected
            expected = Hash.sha256(expected)

    def test_verify_value_valid(self):
        """测试验证有效的值。"""
        seed = b"seed"
        chain = HashChain(seed, length=5)

        for i in range(5):
            value = chain.get_value(i)
            assert chain.verify_value(value, i, chain.anchor) is True

    def test_verify_value_invalid(self):
        """测试验证无效的值。"""
        seed = b"seed"
        chain = HashChain(seed, length=5)
        wrong_value = b"wrong_value"
        assert chain.verify_value(wrong_value, 0, chain.anchor) is False

    def test_verify_value_wrong_index(self):
        """测试验证错误索引。"""
        seed = b"seed"
        chain = HashChain(seed, length=5)
        value = chain.get_value(2)
        assert chain.verify_value(value, 1, chain.anchor) is False

    def test_verify_value_invalid_index(self):
        """测试验证无效索引。"""
        chain = HashChain(b"seed", length=5)
        assert chain.verify_value(b"test", 10, chain.anchor) is False
        assert chain.verify_value(b"test", -1, chain.anchor) is False

    def test_anchor_computation(self):
        """测试锚点计算。"""
        seed = b"test_seed"
        chain = HashChain(seed, length=4)

        expected = seed
        for _ in range(3):
            expected = Hash.sha256(expected)

        assert chain.anchor == expected

    def test_consistency_precompute_vs_no_precompute(self):
        """测试预计算和非预计算模式的一致性。"""
        seed = b"consistency_seed"
        chain1 = HashChain(seed, length=5, precompute=True)
        chain2 = HashChain(seed, length=5, precompute=False)

        assert chain1.anchor == chain2.anchor
        for i in range(5):
            assert chain1.get_value(i) == chain2.get_value(i)

    def test_len(self):
        """测试len()函数。"""
        chain = HashChain(b"seed", length=10)
        assert len(chain) == 10

    def test_repr(self):
        """测试repr表示。"""
        chain = HashChain(b"seed", length=5)
        r = repr(chain)
        assert "HashChain" in r
        assert "length=5" in r

    def test_sha512_algorithm(self):
        """测试使用SHA-512算法。"""
        chain = HashChain(b"seed", length=3, hash_alg="sha512")
        assert len(chain.anchor) == 64

    def test_sha3_256_algorithm(self):
        """测试使用SHA3-256算法。"""
        chain = HashChain(b"seed", length=3, hash_alg="sha3_256")
        assert len(chain.anchor) == 32

    def test_blake2b_algorithm(self):
        """测试使用BLAKE2b算法。"""
        chain = HashChain(b"seed", length=3, hash_alg="blake2b")
        assert len(chain.anchor) == 32

    def test_seed_property(self):
        """测试seed属性。"""
        seed = b"my_test_seed"
        chain = HashChain(seed, length=5)
        assert chain.seed == seed
