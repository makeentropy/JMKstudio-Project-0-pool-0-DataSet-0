"""奇点验证器主工具单元测试。"""
import pytest
import base64
import time

from oath_toolchain.tools.singularity.verifier import SingularityVerifier
from oath_toolchain.core.exceptions import ValidationError
from oath_toolchain.core.registry import ToolRegistry


class TestSingularityVerifier:
    """测试SingularityVerifier类。"""

    def setup_method(self):
        """每个测试前重置注册表并初始化验证器。"""
        ToolRegistry.reset_instance()
        from oath_toolchain.tools.singularity.verifier import SingularityVerifier as SV
        ToolRegistry.reset_instance()
        ToolRegistry().register(SV)
        self.verifier = SingularityVerifier()

    def test_tool_name(self):
        """测试工具名称。"""
        assert self.verifier.name == "singularity_verifier"

    def test_tool_description(self):
        """测试工具描述。"""
        assert self.verifier.description == "质能质量子奇点验证器"

    def test_tool_version(self):
        """测试工具版本。"""
        assert self.verifier.version == "0.1.0"

    def test_tool_category(self):
        """测试工具分类。"""
        assert self.verifier.category == "verification"

    def test_tool_tags(self):
        """测试工具标签。"""
        assert "verification" in self.verifier.tags
        assert "singularity" in self.verifier.tags

    def test_is_registered(self):
        """测试工具是否已注册。"""
        registry = ToolRegistry()
        assert registry.has_tool("singularity_verifier")

    def test_verify_key_strong(self):
        """测试强密钥验证。"""
        import os
        key = os.urandom(32)
        result = self.verifier.verify_key(key)
        assert 'valid' in result
        assert 'score' in result
        assert 'report' in result
        assert 'features' in result
        assert result['valid'] is True
        assert result['score'] > 0.5

    def test_verify_key_weak(self):
        """测试弱密钥验证。"""
        key = b'\x00' * 32
        result = self.verifier.verify_key(key)
        assert result['valid'] is False or result['score'] < 0.5

    def test_verify_key_invalid_type(self):
        """测试无效类型密钥验证。"""
        with pytest.raises(TypeError):
            self.verifier.verify_key("not bytes")

    def test_verify_data_random(self):
        """测试随机数据验证。"""
        import os
        data = os.urandom(64)
        result = self.verifier.verify_data(data)
        assert 'valid' in result
        assert 'score' in result
        assert 'report' in result
        assert 'features' in result

    def test_verify_data_weak(self):
        """测试弱数据验证。"""
        data = b'\x00' * 64
        result = self.verifier.verify_data(data)
        assert result['valid'] is False

    def test_verify_data_invalid_type(self):
        """测试无效类型数据验证。"""
        with pytest.raises(TypeError):
            self.verifier.verify_data("not bytes")

    def test_execute_verify_key_base64(self):
        """测试执行verify操作，密钥为base64编码。"""
        import os
        key = os.urandom(32)
        key_b64 = base64.b64encode(key).decode('ascii')
        result = self.verifier.execute({
            'action': 'verify',
            'key': key_b64,
            'mode': 'full',
        })
        assert 'valid' in result
        assert 'score' in result

    def test_execute_verify_data_string(self):
        """测试执行verify操作，数据为字符串。"""
        result = self.verifier.execute({
            'action': 'verify',
            'data': 'test data string',
            'mode': 'full',
        })
        assert 'valid' in result

    def test_execute_detect(self):
        """测试执行detect操作。"""
        result = self.verifier.execute({
            'action': 'detect',
            'data': b'\x00' * 32,
        })
        assert 'valid' in result
        assert 'report' in result

    def test_execute_features(self):
        """测试执行features操作。"""
        import os
        key = os.urandom(32)
        result = self.verifier.execute({
            'action': 'features',
            'key': key,
        })
        assert 'valid' in result
        assert 'features' in result
        assert 'detailed' in result['features']
        assert 'vector' in result['features']

    def test_execute_invalid_action(self):
        """测试执行无效操作。"""
        with pytest.raises(ValidationError):
            self.verifier.execute({
                'action': 'invalid_action',
                'data': b'test',
            })

    def test_execute_invalid_mode(self):
        """测试执行无效模式。"""
        with pytest.raises(ValidationError):
            self.verifier.execute({
                'action': 'verify',
                'data': b'test',
                'mode': 'invalid_mode',
            })

    def test_execute_invalid_sensitivity(self):
        """测试执行无效灵敏度。"""
        with pytest.raises(ValidationError):
            self.verifier.execute({
                'action': 'verify',
                'data': b'test',
                'sensitivity': 1.5,
            })

    def test_execute_no_data_or_key(self):
        """测试执行verify时没有data或key。"""
        with pytest.raises(ValidationError):
            self.verifier.execute({
                'action': 'verify',
            })

    def test_execute_detect_no_data(self):
        """测试执行detect时没有data。"""
        with pytest.raises(ValidationError):
            self.verifier.execute({
                'action': 'detect',
            })

    def test_execute_features_no_key(self):
        """测试执行features时没有key。"""
        with pytest.raises(ValidationError):
            self.verifier.execute({
                'action': 'features',
            })

    def test_fast_mode_faster_than_full(self):
        """测试快速模式比完整模式快。"""
        import os
        key = os.urandom(256)

        start = time.perf_counter()
        for _ in range(10):
            self.verifier.verify_key(key, mode='full')
        full_time = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(10):
            self.verifier.verify_key(key, mode='fast')
        fast_time = time.perf_counter() - start

        assert fast_time < full_time

    def test_generate_report_structure(self):
        """测试生成报告结构。"""
        import os
        from oath_toolchain.tools.singularity.singularity_detector import SingularityDetector
        data = os.urandom(64)
        detector = SingularityDetector()
        detection = detector.detect(data)
        report = self.verifier.generate_report(detection)

        assert 'is_singular' in report
        assert 'overall_score' in report
        assert 'total_singularities' in report
        assert 'critical_count' in report
        assert 'severity_breakdown' in report
        assert 'type_breakdown' in report
        assert 'singularities' in report
        assert 'verdict' in report
        assert 'recommendations' in report
        assert isinstance(report['recommendations'], list)

    def test_report_recommendations(self):
        """测试报告建议。"""
        data = b'\x00' * 64
        result = self.verifier.verify_data(data)
        assert len(result['report']['recommendations']) > 0

    def test_verify_key_fast_mode(self):
        """测试快速模式密钥验证。"""
        import os
        key = os.urandom(32)
        result = self.verifier.verify_key(key, mode='fast')
        assert 'valid' in result
        assert 'score' in result

    def test_verify_data_fast_mode(self):
        """测试快速模式数据验证。"""
        import os
        data = os.urandom(64)
        result = self.verifier.verify_data(data, mode='fast')
        assert 'valid' in result

    def test_metadata(self):
        """测试工具元数据。"""
        metadata = self.verifier.metadata
        assert metadata['name'] == 'singularity_verifier'
        assert metadata['description'] == '质能质量子奇点验证器'
        assert metadata['version'] == '0.1.0'
        assert 'tags' in metadata
        assert 'category' in metadata

    def test_validate_params_valid(self):
        """测试有效参数验证。"""
        assert self.verifier.validate_params({
            'action': 'verify',
            'data': b'test',
            'mode': 'full',
            'sensitivity': 0.8,
        }) is True

    def test_validate_params_invalid_params_type(self):
        """测试无效参数类型验证。"""
        with pytest.raises(ValidationError):
            self.verifier.validate_params("not a dict")

    def test_decode_input_bytes(self):
        """测试解码bytes输入。"""
        data = b'test data'
        assert self.verifier._decode_input(data) == data

    def test_decode_input_base64(self):
        """测试解码base64输入。"""
        data = b'test data'
        b64 = base64.b64encode(data).decode('ascii')
        assert self.verifier._decode_input(b64) == data

    def test_decode_input_string(self):
        """测试解码字符串输入。"""
        s = "test string"
        assert self.verifier._decode_input(s) == s.encode('utf-8')

    def test_decode_input_invalid(self):
        """测试解码无效输入。"""
        with pytest.raises(ValidationError):
            self.verifier._decode_input(12345)

    def test_empty_key_verification(self):
        """测试空密钥验证。"""
        result = self.verifier.verify_key(b"")
        assert result['valid'] is False

    def test_empty_data_verification(self):
        """测试空数据验证。"""
        result = self.verifier.verify_data(b"")
        assert result['valid'] is False

    def test_verdict_in_report(self):
        """测试报告中的结论。"""
        data = b'\x00' * 64
        result = self.verifier.verify_data(data)
        assert 'verdict' in result['report']
        assert isinstance(result['report']['verdict'], str)
