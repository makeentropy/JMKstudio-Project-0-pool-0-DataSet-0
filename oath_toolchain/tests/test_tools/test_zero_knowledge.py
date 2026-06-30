"""零知识证明基础框架单元测试。"""
import pytest

from oath_toolchain.tools.geometric_proof.zero_knowledge import ZeroKnowledgeProof
from oath_toolchain.core.math.vector import Vector


class TestZeroKnowledgeProof:
    """测试ZeroKnowledgeProof类。"""

    def test_initialization(self):
        """测试初始化。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        assert zkp.security_level == 128
        assert zkp.hash_alg == 'sha256'

    def test_initialization_high_security(self):
        """测试高安全级别初始化。"""
        zkp = ZeroKnowledgeProof(security_level=512)
        assert zkp.security_level == 512
        assert zkp.hash_alg == 'sha512'

    def test_initialization_min_security(self):
        """测试最低安全级别。"""
        zkp = ZeroKnowledgeProof(security_level=64)
        assert zkp.security_level == 64

    def test_initialization_invalid_security(self):
        """测试无效安全级别。"""
        with pytest.raises(ValueError):
            ZeroKnowledgeProof(security_level=32)

    def test_commit(self):
        """测试承诺生成。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        value = b"secret value"
        commitment = zkp.commit(value)

        assert 'commitment' in commitment
        assert 'randomness' in commitment
        assert isinstance(commitment['commitment'], bytes)
        assert isinstance(commitment['randomness'], bytes)
        assert len(commitment['commitment']) == 32

    def test_commit_deterministic_with_randomness(self):
        """测试使用指定随机数的承诺。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        value = b"secret value"
        randomness = b"\x01" * 16

        commitment1 = zkp.commit(value, randomness)
        commitment2 = zkp.commit(value, randomness)

        assert commitment1['commitment'] == commitment2['commitment']
        assert commitment1['randomness'] == commitment2['randomness']

    def test_verify_commitment_valid(self):
        """测试验证有效的承诺。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        value = b"secret value"
        commitment = zkp.commit(value)
        valid = zkp.verify_commitment(
            value,
            commitment['randomness'],
            commitment['commitment']
        )
        assert valid is True

    def test_verify_commitment_wrong_value(self):
        """测试验证错误值的承诺。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        value = b"secret value"
        wrong_value = b"wrong value"
        commitment = zkp.commit(value)
        valid = zkp.verify_commitment(
            wrong_value,
            commitment['randomness'],
            commitment['commitment']
        )
        assert valid is False

    def test_prove_knowledge(self):
        """测试生成知识证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        secret = b"my secret"
        statement = b"public statement"
        proof = zkp.prove_knowledge(secret, statement)

        assert 'statement' in proof
        assert 'secret_hash' in proof
        assert 'commitments_a' in proof
        assert 'commitments_b' in proof
        assert 'challenge' in proof
        assert 'responses' in proof
        assert 'num_rounds' in proof
        assert proof['num_rounds'] == 16

    def test_verify_knowledge_valid(self):
        """测试验证有效的知识证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        secret = b"my secret"
        statement = b"public statement"
        proof = zkp.prove_knowledge(secret, statement)
        valid = zkp.verify_knowledge(statement, proof)
        assert valid is True

    def test_verify_knowledge_wrong_statement(self):
        """测试验证错误声明的知识证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        secret = b"my secret"
        statement1 = b"statement 1"
        statement2 = b"statement 2"
        proof = zkp.prove_knowledge(secret, statement1)
        valid = zkp.verify_knowledge(statement2, proof)
        assert valid is False

    def test_verify_knowledge_invalid_proof(self):
        """测试验证无效的知识证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        statement = b"public statement"
        invalid_proof = {'invalid': 'proof'}
        valid = zkp.verify_knowledge(statement, invalid_proof)
        assert valid is False

    def test_prove_range(self):
        """测试生成范围证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        value = 50
        min_val = 0
        max_val = 100
        proof = zkp.prove_range(value, min_val, max_val)

        assert 'statement' in proof
        assert 'min_val' in proof
        assert 'max_val' in proof
        assert 'value_commitment' in proof
        assert 'value_randomness' in proof
        assert 'delta_min_commitment' in proof
        assert 'delta_max_commitment' in proof

    def test_prove_range_value_out_of_range(self):
        """测试值超出范围时生成范围证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        with pytest.raises(ValueError):
            zkp.prove_range(150, 0, 100)

    def test_verify_range_valid(self):
        """测试验证有效的范围证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        value = 50
        min_val = 0
        max_val = 100
        proof = zkp.prove_range(value, min_val, max_val)
        valid = zkp.verify_range(proof, min_val, max_val)
        assert valid is True

    def test_verify_range_wrong_bounds(self):
        """测试验证错误边界的范围证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        value = 50
        proof = zkp.prove_range(value, 0, 100)
        valid = zkp.verify_range(proof, 10, 90)
        assert valid is False

    def test_verify_range_invalid_proof(self):
        """测试验证无效的范围证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        invalid_proof = {'invalid': 'proof'}
        valid = zkp.verify_range(invalid_proof, 0, 100)
        assert valid is False

    def test_prove_membership(self):
        """测试生成成员证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        elements = [b"elem1", b"elem2", b"elem3", b"elem4"]
        element = b"elem2"
        proof = zkp.prove_membership(element, elements)

        assert 'element_hash' in proof
        assert 'element_index' in proof
        assert 'merkle_root' in proof
        assert 'merkle_path' in proof
        assert 'total_elements' in proof
        assert proof['element_index'] == 1
        assert proof['total_elements'] == 4

    def test_prove_membership_not_in_set(self):
        """测试元素不在集合中时生成成员证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        elements = [b"elem1", b"elem2", b"elem3"]
        element = b"elem_not_in_set"
        with pytest.raises(ValueError):
            zkp.prove_membership(element, elements)

    def test_verify_membership_valid(self):
        """测试验证有效的成员证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        elements = [b"elem1", b"elem2", b"elem3", b"elem4", b"elem5"]
        element = b"elem3"

        proof = zkp.prove_membership(element, elements)

        from oath_toolchain.core.data_structures.merkle import MerkleTree
        tree = MerkleTree(elements, 'sha256')
        set_root = tree.root

        valid = zkp.verify_membership(element, set_root, proof)
        assert valid is True

    def test_verify_membership_wrong_element(self):
        """测试验证错误元素的成员证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        elements = [b"elem1", b"elem2", b"elem3"]
        element = b"elem2"
        wrong_element = b"wrong_elem"

        proof = zkp.prove_membership(element, elements)

        from oath_toolchain.core.data_structures.merkle import MerkleTree
        tree = MerkleTree(elements, 'sha256')
        set_root = tree.root

        valid = zkp.verify_membership(wrong_element, set_root, proof)
        assert valid is False

    def test_verify_membership_invalid_proof(self):
        """测试验证无效的成员证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        element = b"elem1"
        set_root = b"\x00" * 32
        invalid_proof = {'invalid': 'proof'}
        valid = zkp.verify_membership(element, set_root, invalid_proof)
        assert valid is False

    def test_prove_equality(self):
        """测试生成等式证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        secret1 = b"same secret"
        secret2 = b"same secret"
        statement = b"equality statement"
        proof = zkp.prove_equality(secret1, secret2, statement)

        assert 'statement' in proof
        assert 'hash1' in proof
        assert 'hash2' in proof
        assert proof['hash1'] == proof['hash2']

    def test_prove_equality_different_secrets(self):
        """测试不同秘密生成等式证明时抛出异常。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        secret1 = b"secret 1"
        secret2 = b"secret 2"
        statement = b"equality statement"
        with pytest.raises(ValueError):
            zkp.prove_equality(secret1, secret2, statement)

    def test_verify_equality_valid(self):
        """测试验证有效的等式证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        secret = b"same secret"
        statement = b"equality statement"
        proof = zkp.prove_equality(secret, secret, statement)
        valid = zkp.verify_equality(statement, proof)
        assert valid is True

    def test_verify_equality_wrong_statement(self):
        """测试验证错误声明的等式证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        secret = b"same secret"
        statement1 = b"statement 1"
        statement2 = b"statement 2"
        proof = zkp.prove_equality(secret, secret, statement1)
        valid = zkp.verify_equality(statement2, proof)
        assert valid is False

    def test_geometric_prove(self):
        """测试几何零知识证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        secret_point = Vector([0.5, -0.3, 0.8, -0.1])
        statement = b"geometric proof statement"
        proof = zkp.geometric_prove(secret_point, statement)

        assert 'statement' in proof
        assert 'point_hash' in proof
        assert 'commitment' in proof
        assert 'proof_points' in proof
        assert 'dimensions' in proof
        assert proof['dimensions'] == 4

    def test_range_proof_edge_cases(self):
        """测试范围证明的边界情况。"""
        zkp = ZeroKnowledgeProof(security_level=128)

        proof_min = zkp.prove_range(0, 0, 10)
        assert zkp.verify_range(proof_min, 0, 10) is True

        proof_max = zkp.prove_range(10, 0, 10)
        assert zkp.verify_range(proof_max, 0, 10) is True

        proof_single = zkp.prove_range(5, 5, 5)
        assert zkp.verify_range(proof_single, 5, 5) is True

    def test_membership_single_element(self):
        """测试单元素集合的成员证明。"""
        zkp = ZeroKnowledgeProof(security_level=128)
        elements = [b"only_elem"]
        element = b"only_elem"
        proof = zkp.prove_membership(element, elements)

        from oath_toolchain.core.data_structures.merkle import MerkleTree
        tree = MerkleTree(elements, 'sha256')
        set_root = tree.root

        valid = zkp.verify_membership(element, set_root, proof)
        assert valid is True
