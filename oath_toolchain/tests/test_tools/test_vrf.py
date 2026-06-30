"""可验证随机函数单元测试。"""
import pytest

from oath_toolchain.tools.geometric_proof.vrf import VerifiableRandomFunction
from oath_toolchain.core.math.vector import Vector


class TestVerifiableRandomFunction:
    """测试VerifiableRandomFunction类。"""

    def test_initialization(self):
        """测试初始化。"""
        vrf = VerifiableRandomFunction()
        assert vrf.hash_alg == 'sha256'

    def test_generate_keypair(self):
        """测试生成密钥对。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()

        assert isinstance(private_key, bytes)
        assert isinstance(public_key, bytes)
        assert len(private_key) > 0
        assert len(public_key) > 0
        assert private_key != public_key

    def test_generate_keypair_unique(self):
        """测试密钥对的唯一性。"""
        vrf = VerifiableRandomFunction()
        sk1, pk1 = vrf.generate_keypair()
        sk2, pk2 = vrf.generate_keypair()

        assert sk1 != sk2
        assert pk1 != pk2

    def test_compute(self):
        """测试计算VRF。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output, proof = vrf.compute(private_key, input_data)

        assert isinstance(output, bytes)
        assert isinstance(proof, bytes)
        assert len(output) == 32
        assert len(proof) > 0

    def test_compute_deterministic(self):
        """测试VRF计算的确定性。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output1, proof1 = vrf.compute(private_key, input_data)
        output2, proof2 = vrf.compute(private_key, input_data)

        assert output1 == output2
        assert proof1 == proof2

    def test_compute_different_inputs(self):
        """测试不同输入产生不同输出。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()

        output1, _ = vrf.compute(private_key, b"input 1")
        output2, _ = vrf.compute(private_key, b"input 2")

        assert output1 != output2

    def test_compute_different_keys(self):
        """测试不同密钥产生不同输出。"""
        vrf = VerifiableRandomFunction()
        sk1, pk1 = vrf.generate_keypair()
        sk2, pk2 = vrf.generate_keypair()
        input_data = b"test input"

        output1, _ = vrf.compute(sk1, input_data)
        output2, _ = vrf.compute(sk2, input_data)

        assert output1 != output2

    def test_verify_valid(self):
        """测试验证有效的VRF。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output, proof = vrf.compute(private_key, input_data)
        valid = vrf.verify(public_key, input_data, output, proof)

        assert valid is True

    def test_verify_wrong_output(self):
        """测试验证错误输出的VRF。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output, proof = vrf.compute(private_key, input_data)
        wrong_output = b"\x00" * 32
        valid = vrf.verify(public_key, input_data, wrong_output, proof)

        assert valid is False

    def test_verify_wrong_input(self):
        """测试验证错误输入的VRF。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()

        output, proof = vrf.compute(private_key, b"input 1")
        valid = vrf.verify(public_key, b"input 2", output, proof)

        assert valid is False

    def test_verify_wrong_public_key(self):
        """测试验证错误公钥的VRF。"""
        vrf = VerifiableRandomFunction()
        sk1, pk1 = vrf.generate_keypair()
        sk2, pk2 = vrf.generate_keypair()
        input_data = b"test input"

        output, proof = vrf.compute(sk1, input_data)
        valid = vrf.verify(pk2, input_data, output, proof)

        assert valid is False

    def test_verify_invalid_public_key(self):
        """测试验证无效公钥的VRF。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output, proof = vrf.compute(private_key, input_data)
        invalid_pk = b"invalid_key"
        valid = vrf.verify(invalid_pk, input_data, output, proof)

        assert valid is False

    def test_verify_invalid_proof(self):
        """测试验证无效证明的VRF。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output, _ = vrf.compute(private_key, input_data)
        invalid_proof = b"invalid_proof"
        valid = vrf.verify(public_key, input_data, output, invalid_proof)

        assert valid is False

    def test_random_output(self):
        """测试生成可验证随机数。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        seed = b"random seed"

        random_out = vrf.random_output(private_key, seed)

        assert isinstance(random_out, bytes)
        assert len(random_out) == 32

    def test_random_output_deterministic(self):
        """测试可验证随机数的确定性。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        seed = b"random seed"

        out1 = vrf.random_output(private_key, seed)
        out2 = vrf.random_output(private_key, seed)

        assert out1 == out2

    def test_random_output_verify(self):
        """测试可验证随机数的验证。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        seed = b"random seed"

        output, proof = vrf.compute(private_key, seed)
        random_out = vrf.random_output(private_key, seed)

        assert output == random_out
        assert vrf.verify(public_key, seed, random_out, proof) is True

    def test_geometric_vrf(self):
        """测试几何VRF。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output, proof, point = vrf.geometric_vrf(private_key, input_data)

        assert isinstance(output, bytes)
        assert isinstance(proof, bytes)
        assert isinstance(point, Vector)
        assert point.dim == 4
        assert len(output) == 32

    def test_verify_geometric_vrf(self):
        """测试验证几何VRF。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output, proof, point = vrf.geometric_vrf(private_key, input_data)
        valid = vrf.verify_geometric_vrf(public_key, input_data, output, proof)

        assert valid is True

    def test_compute_invalid_private_key(self):
        """测试使用无效私钥计算VRF。"""
        vrf = VerifiableRandomFunction()
        with pytest.raises(ValueError):
            vrf.compute(b"invalid_key", b"test input")

    def test_empty_input(self):
        """测试空输入。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b""

        output, proof = vrf.compute(private_key, input_data)
        valid = vrf.verify(public_key, input_data, output, proof)

        assert valid is True

    def test_large_input(self):
        """测试大输入。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"x" * 10000

        output, proof = vrf.compute(private_key, input_data)
        valid = vrf.verify(public_key, input_data, output, proof)

        assert valid is True

    def test_multiple_inputs_consistency(self):
        """测试多个输入的一致性。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()

        for i in range(10):
            input_data = f"input_{i}".encode()
            output, proof = vrf.compute(private_key, input_data)
            assert vrf.verify(public_key, input_data, output, proof) is True

    def test_verify_proof_too_short(self):
        """测试验证过短的证明。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()
        input_data = b"test input"

        output, _ = vrf.compute(private_key, input_data)
        short_proof = b"short"
        valid = vrf.verify(public_key, input_data, output, short_proof)

        assert valid is False
