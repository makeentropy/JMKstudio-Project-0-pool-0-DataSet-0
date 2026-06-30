"""Merkle树单元测试。"""
import pytest

from oath_toolchain.core.data_structures.merkle import MerkleTree


class TestMerkleTree:
    """测试MerkleTree类。"""

    def test_merkle_tree_creation(self):
        """测试Merkle树创建。"""
        data_blocks = [b"block1", b"block2", b"block3", b"block4"]
        tree = MerkleTree(data_blocks)
        assert tree.leaf_count == 4
        assert tree.root is not None
        assert len(tree.root) == 32

    def test_merkle_tree_empty_raises(self):
        """测试空数据块列表。"""
        with pytest.raises(ValueError):
            MerkleTree([])

    def test_merkle_tree_single_leaf(self):
        """测试单个叶子节点的Merkle树。"""
        tree = MerkleTree([b"single"])
        assert tree.leaf_count == 1
        assert tree.depth == 0

    def test_merkle_tree_root_deterministic(self):
        """测试Merkle树根的确定性。"""
        data_blocks = [b"a", b"b", b"c", b"d"]
        tree1 = MerkleTree(data_blocks)
        tree2 = MerkleTree(data_blocks)
        assert tree1.root == tree2.root

    def test_merkle_tree_different_data_different_root(self):
        """测试不同数据有不同的根。"""
        tree1 = MerkleTree([b"a", b"b"])
        tree2 = MerkleTree([b"c", b"d"])
        assert tree1.root != tree2.root

    def test_generate_proof(self):
        """测试生成Merkle证明。"""
        data_blocks = [b"block0", b"block1", b"block2", b"block3"]
        tree = MerkleTree(data_blocks)

        for i in range(4):
            proof = tree.generate_proof(i)
            assert isinstance(proof, list)
            assert len(proof) == tree.depth

    def test_generate_proof_invalid_index(self):
        """测试无效索引的证明生成。"""
        tree = MerkleTree([b"a", b"b"])
        with pytest.raises(IndexError):
            tree.generate_proof(5)

    def test_verify_proof_valid(self):
        """测试验证有效的Merkle证明。"""
        data_blocks = [b"block0", b"block1", b"block2", b"block3"]
        tree = MerkleTree(data_blocks)

        for i in range(4):
            proof = tree.generate_proof(i)
            assert tree.verify_proof(data_blocks[i], proof, tree.root, i) is True

    def test_verify_proof_invalid_data(self):
        """测试验证无效数据。"""
        data_blocks = [b"block0", b"block1", b"block2", b"block3"]
        tree = MerkleTree(data_blocks)
        proof = tree.generate_proof(0)
        assert tree.verify_proof(b"wrong_data", proof, tree.root, 0) is False

    def test_verify_proof_wrong_index(self):
        """测试验证错误索引。"""
        data_blocks = [b"block0", b"block1", b"block2", b"block3"]
        tree = MerkleTree(data_blocks)
        proof = tree.generate_proof(0)
        assert tree.verify_proof(data_blocks[1], proof, tree.root, 0) is False

    def test_add_leaf(self):
        """测试添加叶子节点。"""
        tree = MerkleTree([b"a", b"b"])
        old_root = tree.root
        tree.add_leaf(b"c")
        assert tree.leaf_count == 3
        assert tree.root != old_root

    def test_add_leaf_verify(self):
        """测试添加叶子后验证证明。"""
        tree = MerkleTree([b"a", b"b"])
        tree.add_leaf(b"c")
        tree.add_leaf(b"d")

        for i in range(4):
            data = [b"a", b"b", b"c", b"d"][i]
            proof = tree.generate_proof(i)
            assert tree.verify_proof(data, proof, tree.root, i) is True

    def test_get_leaf(self):
        """测试获取叶子节点。"""
        data_blocks = [b"a", b"b", b"c"]
        tree = MerkleTree(data_blocks)
        leaf = tree.get_leaf(1)
        assert isinstance(leaf, bytes)
        assert len(leaf) == 32

    def test_get_leaf_invalid_index(self):
        """测试获取无效索引的叶子。"""
        tree = MerkleTree([b"a", b"b"])
        with pytest.raises(IndexError):
            tree.get_leaf(5)

    def test_len(self):
        """测试len()函数。"""
        tree = MerkleTree([b"a", b"b", b"c"])
        assert len(tree) == 3

    def test_depth(self):
        """测试树深度。"""
        tree = MerkleTree([b"a", b"b", b"c", b"d"])
        assert tree.depth == 2

    def test_odd_number_of_leaves(self):
        """测试奇数个叶子节点。"""
        data_blocks = [b"a", b"b", b"c"]
        tree = MerkleTree(data_blocks)
        assert tree.leaf_count == 3
        assert tree.root is not None

        for i in range(3):
            proof = tree.generate_proof(i)
            assert tree.verify_proof(data_blocks[i], proof, tree.root, i) is True

    def test_repr(self):
        """测试repr表示。"""
        tree = MerkleTree([b"a", b"b"])
        r = repr(tree)
        assert "MerkleTree" in r
        assert "leaf_count=2" in r

    def test_sha512_algorithm(self):
        """测试使用SHA-512算法。"""
        tree = MerkleTree([b"a", b"b"], hash_alg="sha512")
        assert len(tree.root) == 64

    def test_sha3_256_algorithm(self):
        """测试使用SHA3-256算法。"""
        tree = MerkleTree([b"a", b"b"], hash_alg="sha3_256")
        assert len(tree.root) == 32

    def test_blake2b_algorithm(self):
        """测试使用BLAKE2b算法。"""
        tree = MerkleTree([b"a", b"b"], hash_alg="blake2b")
        assert len(tree.root) == 32
