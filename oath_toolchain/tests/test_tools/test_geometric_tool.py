"""几何证据加密主工具单元测试。"""
import pytest

from oath_toolchain.tools.geometric_proof.tool import GeometricProofTool
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.core.exceptions import ValidationError


class TestGeometricProofTool:
    """测试GeometricProofTool类。"""

    def test_initialization(self):
        """测试初始化。"""
        tool = GeometricProofTool()
        assert tool.name == "geometric_proof"
        assert tool.description == "几何证据加密工具"
        assert tool.version == "0.1.0"
        assert tool.category == "crypto"
        assert "crypto" in tool.tags
        assert "geometric" in tool.tags

    def test_registry_integration(self):
        """测试工具注册集成。"""
        ToolRegistry.reset_instance()
        import importlib
        import oath_toolchain.tools.geometric_proof.tool as tool_module
        importlib.reload(tool_module)

        registry = ToolRegistry()
        assert "geometric_proof" in registry
        tool_class = registry.get_tool("geometric_proof")
        assert tool_class.__name__ == "GeometricProofTool"

    def test_create_tool_from_registry(self):
        """测试从注册表创建工具。"""
        ToolRegistry.reset_instance()
        import importlib
        import oath_toolchain.tools.geometric_proof.tool as tool_module
        importlib.reload(tool_module)

        registry = ToolRegistry()
        tool = registry.create_tool("geometric_proof")
        assert tool.name == "geometric_proof"
        assert tool.description == "几何证据加密工具"

    def test_execute_missing_action(self):
        """测试缺少action参数。"""
        tool = GeometricProofTool()
        with pytest.raises(ValidationError):
            tool.execute({})

    def test_execute_invalid_action(self):
        """测试无效的action参数。"""
        tool = GeometricProofTool()
        with pytest.raises(ValidationError):
            tool.execute({'action': 'invalid_action'})

    def test_action_hash(self):
        """测试hash操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'hash',
            'data': b'test data',
        })
        assert result['success'] is True
        assert result['action'] == 'hash'
        assert 'hash' in result
        assert len(result['hash']) == 64

    def test_action_hash_string_data(self):
        """测试字符串类型数据的hash。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'hash',
            'data': 'test data string',
        })
        assert result['success'] is True
        assert 'hash' in result

    def test_action_hash_to_point(self):
        """测试hash_to_point操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'hash_to_point',
            'data': b'test data',
        })
        assert result['success'] is True
        assert result['action'] == 'hash_to_point'
        assert 'point' in result
        assert isinstance(result['point'], list)
        assert len(result['point']) == 4

    def test_action_distance_hash(self):
        """测试distance_hash操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'distance_hash',
            'data1': b'data 1',
            'data2': b'data 2',
        })
        assert result['success'] is True
        assert 'euclidean_distance' in result
        assert 'cosine_similarity' in result
        assert result['euclidean_distance'] >= 0.0
        assert -1.0 <= result['cosine_similarity'] <= 1.0

    def test_action_geometric_roothash(self):
        """测试geometric_roothash操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'geometric_roothash',
            'data_blocks': [b'block 1', b'block 2', b'block 3'],
        })
        assert result['success'] is True
        assert 'root_hash' in result
        assert result['block_count'] == 3

    def test_action_prove(self):
        """测试prove操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'prove',
            'data': b'test data for proof',
        })
        assert result['success'] is True
        assert 'proof' in result
        assert 'data_hash' in result['proof']
        assert 'proof_points' in result['proof']

    def test_action_prove_with_secret(self):
        """测试带密钥的prove操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'prove',
            'data': b'test data',
            'secret': b'my secret',
        })
        assert result['success'] is True
        assert 'signature' in result['proof']

    def test_action_verify_valid(self):
        """测试verify操作（有效证明）。"""
        tool = GeometricProofTool()
        data = b'test data for verification'

        prove_result = tool.execute({
            'action': 'prove',
            'data': data,
        })
        proof = prove_result['proof']

        verify_result = tool.execute({
            'action': 'verify',
            'data': data,
            'proof': proof,
        })
        assert verify_result['success'] is True
        assert verify_result['valid'] is True

    def test_action_verify_tampered(self):
        """测试verify操作（被篡改的数据）。"""
        tool = GeometricProofTool()
        original_data = b'original data'
        tampered_data = b'tampered data'

        prove_result = tool.execute({
            'action': 'prove',
            'data': original_data,
        })
        proof = prove_result['proof']

        verify_result = tool.execute({
            'action': 'verify',
            'data': tampered_data,
            'proof': proof,
        })
        assert verify_result['success'] is True
        assert verify_result['valid'] is False

    def test_action_integrity_prove(self):
        """测试integrity_prove操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'integrity_prove',
            'data': b'integrity test data' * 10,
        })
        assert result['success'] is True
        assert 'proof' in result
        assert 'merkle_root' in result['proof']

    def test_action_integrity_verify_valid(self):
        """测试integrity_verify操作（有效证明）。"""
        tool = GeometricProofTool()
        data = b'integrity test data' * 10

        prove_result = tool.execute({
            'action': 'integrity_prove',
            'data': data,
        })
        proof = prove_result['proof']

        verify_result = tool.execute({
            'action': 'integrity_verify',
            'data': data,
            'proof': proof,
        })
        assert verify_result['success'] is True
        assert verify_result['valid'] is True

    def test_action_zk_prove(self):
        """测试zk_prove操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'zk_prove',
            'secret': b'my secret',
            'statement': b'public statement',
        })
        assert result['success'] is True
        assert 'proof' in result

    def test_action_zk_verify_valid(self):
        """测试zk_verify操作（有效证明）。"""
        tool = GeometricProofTool()
        secret = b'my secret'
        statement = b'public statement'

        prove_result = tool.execute({
            'action': 'zk_prove',
            'secret': secret,
            'statement': statement,
        })
        proof = prove_result['proof']

        verify_result = tool.execute({
            'action': 'zk_verify',
            'statement': statement,
            'proof': proof,
        })
        assert verify_result['success'] is True
        assert verify_result['valid'] is True

    def test_action_zk_commit(self):
        """测试zk_commit操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'zk_commit',
            'value': b'commit value',
        })
        assert result['success'] is True
        assert 'commitment' in result
        assert 'randomness' in result

    def test_action_zk_range_prove(self):
        """测试zk_range_prove操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'zk_range_prove',
            'value': 50,
            'min_val': 0,
            'max_val': 100,
        })
        assert result['success'] is True
        assert 'proof' in result

    def test_action_zk_range_verify_valid(self):
        """测试zk_range_verify操作（有效证明）。"""
        tool = GeometricProofTool()

        prove_result = tool.execute({
            'action': 'zk_range_prove',
            'value': 50,
            'min_val': 0,
            'max_val': 100,
        })
        proof = prove_result['proof']

        verify_result = tool.execute({
            'action': 'zk_range_verify',
            'proof': proof,
            'min_val': 0,
            'max_val': 100,
        })
        assert verify_result['success'] is True
        assert verify_result['valid'] is True

    def test_action_zk_membership_prove(self):
        """测试zk_membership_prove操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'zk_membership_prove',
            'element': b'elem2',
            'elements': [b'elem1', b'elem2', b'elem3'],
        })
        assert result['success'] is True
        assert 'proof' in result

    def test_action_vrf_gen(self):
        """测试vrf_gen操作。"""
        tool = GeometricProofTool()
        result = tool.execute({
            'action': 'vrf_gen',
        })
        assert result['success'] is True
        assert 'private_key' in result
        assert 'public_key' in result

    def test_action_vrf_compute(self):
        """测试vrf_compute操作。"""
        tool = GeometricProofTool()

        gen_result = tool.execute({'action': 'vrf_gen'})
        sk = gen_result['private_key']

        compute_result = tool.execute({
            'action': 'vrf_compute',
            'secret_key': sk,
            'input_data': b'test input',
        })
        assert compute_result['success'] is True
        assert 'output' in compute_result
        assert 'proof' in compute_result

    def test_action_vrf_verify_valid(self):
        """测试vrf_verify操作（有效证明）。"""
        tool = GeometricProofTool()

        gen_result = tool.execute({'action': 'vrf_gen'})
        sk = gen_result['private_key']
        pk = gen_result['public_key']
        input_data = b'test input'

        compute_result = tool.execute({
            'action': 'vrf_compute',
            'secret_key': sk,
            'input_data': input_data,
        })
        output = compute_result['output']
        proof = compute_result['proof']

        verify_result = tool.execute({
            'action': 'vrf_verify',
            'public_key': pk,
            'input_data': input_data,
            'output': output,
            'proof': proof,
        })
        assert verify_result['success'] is True
        assert verify_result['valid'] is True

    def test_action_vrf_random(self):
        """测试vrf_random操作。"""
        tool = GeometricProofTool()

        gen_result = tool.execute({'action': 'vrf_gen'})
        sk = gen_result['private_key']

        random_result = tool.execute({
            'action': 'vrf_random',
            'secret_key': sk,
            'seed': b'random seed',
        })
        assert random_result['success'] is True
        assert 'random_output' in random_result

    def test_validate_params_missing_action(self):
        """测试参数验证：缺少action。"""
        tool = GeometricProofTool()
        with pytest.raises(ValidationError):
            tool.validate_params({})

    def test_validate_params_invalid_action(self):
        """测试参数验证：无效action。"""
        tool = GeometricProofTool()
        with pytest.raises(ValidationError):
            tool.validate_params({'action': 'invalid'})

    def test_validate_params_valid_action(self):
        """测试参数验证：有效action。"""
        tool = GeometricProofTool()
        assert tool.validate_params({'action': 'hash'}) is True

    def test_metadata(self):
        """测试工具元数据。"""
        tool = GeometricProofTool()
        metadata = tool.metadata
        assert metadata['name'] == 'geometric_proof'
        assert metadata['description'] == '几何证据加密工具'
        assert metadata['version'] == '0.1.0'
        assert metadata['category'] == 'crypto'
        assert isinstance(metadata['tags'], list)

    def test_tool_repr(self):
        """测试工具的字符串表示。"""
        tool = GeometricProofTool()
        repr_str = repr(tool)
        assert 'GeometricProofTool' in repr_str
        assert 'geometric_proof' in repr_str

    def test_tool_str(self):
        """测试工具的可读字符串。"""
        tool = GeometricProofTool()
        str_repr = str(tool)
        assert 'geometric_proof' in str_repr
        assert '几何证据加密工具' in str_repr
