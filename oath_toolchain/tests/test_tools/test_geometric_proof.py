"""几何证明生成与验证单元测试。"""
import pytest

from oath_toolchain.tools.geometric_proof.proof_generator import GeometricProof


class TestGeometricProof:
    """测试GeometricProof类。"""

    def test_initialization(self):
        """测试初始化。"""
        gp = GeometricProof(dimensions=4, hash_alg='sha256', num_proof_points=8)
        assert gp.dimensions == 4
        assert gp.hash_alg == 'sha256'
        assert gp.num_proof_points == 8

    def test_initialization_invalid_num_points(self):
        """测试无效证明点数量。"""
        with pytest.raises(ValueError):
            GeometricProof(num_proof_points=0)

    def test_generate_proof(self):
        """测试生成几何证明。"""
        gp = GeometricProof(dimensions=4, num_proof_points=4)
        data = b"test data for proof"
        proof = gp.generate_proof(data)

        assert 'data_hash' in proof
        assert 'proof_points' in proof
        assert 'merkle_path' in proof
        assert 'merkle_root' in proof
        assert 'timestamp' in proof
        assert 'dimensions' in proof
        assert isinstance(proof['proof_points'], list)
        assert len(proof['proof_points']) == 4

    def test_generate_proof_with_secret(self):
        """测试带密钥的几何证明。"""
        gp = GeometricProof(dimensions=4, num_proof_points=4)
        data = b"test data"
        secret = b"my secret key"
        proof = gp.generate_proof(data, secret)

        assert 'signature' in proof
        assert proof['signature'] is not None

    def test_verify_proof_valid(self):
        """测试验证有效的几何证明。"""
        gp = GeometricProof(dimensions=4, num_proof_points=4)
        data = b"test data for verification"
        proof = gp.generate_proof(data)
        valid = gp.verify_proof(data, proof)
        assert valid is True

    def test_verify_proof_tampered_data(self):
        """测试验证被篡改的数据。"""
        gp = GeometricProof(dimensions=4, num_proof_points=4)
        original_data = b"original data"
        tampered_data = b"tampered data"
        proof = gp.generate_proof(original_data)
        valid = gp.verify_proof(tampered_data, proof)
        assert valid is False

    def test_verify_proof_tampered_proof(self):
        """测试验证被篡改的证明。"""
        gp = GeometricProof(dimensions=4, num_proof_points=4)
        data = b"test data"
        proof = gp.generate_proof(data)

        tampered_proof = dict(proof)
        tampered_proof['data_hash'] = '0' * 64

        valid = gp.verify_proof(data, tampered_proof)
        assert valid is False

    def test_verify_proof_invalid_format(self):
        """测试验证格式无效的证明。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data"
        invalid_proof = {'invalid': 'proof'}
        valid = gp.verify_proof(data, invalid_proof)
        assert valid is False

    def test_verify_signature_valid(self):
        """测试验证有效的签名。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data"
        secret = b"secret key"
        proof = gp.generate_proof(data, secret)
        valid = gp.verify_signature(proof, secret)
        assert valid is True

    def test_verify_signature_wrong_secret(self):
        """测试用错误密钥验证签名。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data"
        secret1 = b"secret key 1"
        secret2 = b"secret key 2"
        proof = gp.generate_proof(data, secret1)
        valid = gp.verify_signature(proof, secret2)
        assert valid is False

    def test_verify_signature_no_signature(self):
        """测试验证没有签名的证明。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data"
        proof = gp.generate_proof(data)
        valid = gp.verify_signature(proof, b"any secret")
        assert valid is False

    def test_generate_integrity_proof(self):
        """测试生成完整性证明。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data for integrity proof" * 10
        proof = gp.generate_integrity_proof(data)

        assert 'data_size' in proof
        assert 'block_size' in proof
        assert 'block_count' in proof
        assert 'merkle_root' in proof
        assert 'block_hashes' in proof
        assert proof['data_size'] == len(data)

    def test_verify_integrity_proof_valid(self):
        """测试验证有效的完整性证明。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data for integrity verification" * 20
        proof = gp.generate_integrity_proof(data)
        valid = gp.verify_integrity_proof(data, proof)
        assert valid is True

    def test_verify_integrity_proof_tampered(self):
        """测试验证被篡改的完整性证明。"""
        gp = GeometricProof(dimensions=4)
        original_data = b"original data" * 20
        tampered_data = b"tampered data" * 20
        proof = gp.generate_integrity_proof(original_data)
        valid = gp.verify_integrity_proof(tampered_data, proof)
        assert valid is False

    def test_verify_integrity_proof_size_mismatch(self):
        """测试验证大小不匹配的完整性证明。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data" * 10
        proof = gp.generate_integrity_proof(data)
        shorter_data = data[:-1]
        valid = gp.verify_integrity_proof(shorter_data, proof)
        assert valid is False

    def test_generate_block_proof(self):
        """测试生成块证明。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data for block proof" * 10
        block_proof = gp.generate_block_proof(data, 0)

        assert 'block_index' in block_proof
        assert block_proof['block_index'] == 0
        assert 'block_data' in block_proof
        assert 'block_hash' in block_proof
        assert 'merkle_path' in block_proof
        assert 'merkle_root' in block_proof

    def test_generate_block_proof_invalid_index(self):
        """测试生成块证明时的无效索引。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data"
        with pytest.raises(IndexError):
            gp.generate_block_proof(data, 999)

    def test_generate_block_proof_negative_index(self):
        """测试生成块证明时的负索引。"""
        gp = GeometricProof(dimensions=4)
        data = b"test data"
        with pytest.raises(IndexError):
            gp.generate_block_proof(data, -1)

    def test_different_dimensions(self):
        """测试不同维度的证明。"""
        gp3 = GeometricProof(dimensions=3, num_proof_points=4)
        gp6 = GeometricProof(dimensions=6, num_proof_points=4)

        data = b"test data"
        proof3 = gp3.generate_proof(data)
        proof6 = gp6.generate_proof(data)

        assert proof3['dimensions'] == 3
        assert proof6['dimensions'] == 6

        assert len(proof3['proof_points'][0]) == 3
        assert len(proof6['proof_points'][0]) == 6

    def test_different_num_proof_points(self):
        """测试不同数量的证明点。"""
        gp4 = GeometricProof(num_proof_points=4)
        gp8 = GeometricProof(num_proof_points=8)

        data = b"test data"
        proof4 = gp4.generate_proof(data)
        proof8 = gp8.generate_proof(data)

        assert len(proof4['proof_points']) == 4
        assert len(proof8['proof_points']) == 8

    def test_empty_data(self):
        """测试空数据的证明。"""
        gp = GeometricProof(dimensions=4)
        data = b""
        proof = gp.generate_proof(data)
        valid = gp.verify_proof(data, proof)
        assert valid is True

    def test_large_data(self):
        """测试大数据的证明。"""
        gp = GeometricProof(dimensions=4)
        data = b"x" * 10000
        proof = gp.generate_proof(data)
        valid = gp.verify_proof(data, proof)
        assert valid is True

    def test_integrity_proof_empty_data(self):
        """测试空数据的完整性证明。"""
        gp = GeometricProof(dimensions=4)
        data = b""
        proof = gp.generate_integrity_proof(data)
        assert proof['data_size'] == 0
        valid = gp.verify_integrity_proof(data, proof)
        assert valid is True
