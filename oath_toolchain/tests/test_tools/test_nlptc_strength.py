"""NLPTC密钥强度评估单元测试。"""
import pytest

from oath_toolchain.tools.nlptcmodel.strength_evaluator import KeyStrengthEvaluator


class TestKeyStrengthEvaluator:
    """测试KeyStrengthEvaluator类。"""

    def setup_method(self):
        """每个测试前初始化评估器。"""
        self.evaluator = KeyStrengthEvaluator()

    def test_evaluate_strong_key(self):
        """测试强密钥评估。"""
        import os
        key = os.urandom(32)
        result = self.evaluator.evaluate(key)

        assert 'entropy' in result
        assert 'bit_size' in result
        assert 'char_diversity' in result
        assert 'pattern_detection' in result
        assert 'strength_score' in result
        assert 'strength_level' in result
        assert 'crack_time' in result
        assert 'recommendations' in result

        assert result['bit_size'] == 256
        assert result['strength_score'] > 0.5

    def test_evaluate_weak_key_all_zeros(self):
        """测试全零弱密钥评估。"""
        key = b'\x00' * 32
        result = self.evaluator.evaluate(key)

        assert result['strength_score'] < 0.5
        assert result['pattern_detection']['repeated_bytes']['found'] is True
        assert result['pattern_detection']['zero_padding']['found'] is True

    def test_evaluate_weak_key_all_ff(self):
        """测试全0xFF弱密钥评估。"""
        key = b'\xff' * 32
        result = self.evaluator.evaluate(key)

        assert result['strength_score'] < 0.5
        assert result['pattern_detection']['repeated_bytes']['found'] is True
        assert result['pattern_detection']['ff_padding']['found'] is True

    def test_evaluate_increasing_sequence(self):
        """测试递增序列弱密钥。"""
        key = bytes(range(32))
        result = self.evaluator.evaluate(key)

        assert result['pattern_detection']['increasing_sequence']['found'] is True

    def test_evaluate_decreasing_sequence(self):
        """测试递减序列弱密钥。"""
        key = bytes(range(31, -1, -1))
        result = self.evaluator.evaluate(key)

        assert result['pattern_detection']['decreasing_sequence']['found'] is True

    def test_evaluate_short_key(self):
        """测试短密钥评估。"""
        key = b'short'
        result = self.evaluator.evaluate(key)

        assert result['bit_size'] == 40
        assert result['strength_score'] < 0.5

    def test_calculate_entropy_random(self):
        """测试随机密钥熵值计算。"""
        import os
        key = os.urandom(32)
        entropy = self.evaluator.calculate_entropy(key)
        assert entropy > 4.0
        assert entropy <= 8.0

    def test_calculate_entropy_uniform(self):
        """测试均匀分布密钥熵值计算。"""
        key = bytes(range(256))
        entropy = self.evaluator.calculate_entropy(key)
        assert abs(entropy - 8.0) < 0.1

    def test_calculate_entropy_single_byte(self):
        """测试单字节密钥熵值计算。"""
        key = b'\x00' * 32
        entropy = self.evaluator.calculate_entropy(key)
        assert entropy == 0.0

    def test_calculate_entropy_empty(self):
        """测试空密钥熵值计算。"""
        entropy = self.evaluator.calculate_entropy(b'')
        assert entropy == 0.0

    def test_detect_patterns_strong_key(self):
        """测试强密钥模式检测。"""
        import os
        key = os.urandom(32)
        patterns = self.evaluator.detect_patterns(key)

        assert 'repeated_bytes' in patterns
        assert 'increasing_sequence' in patterns
        assert 'decreasing_sequence' in patterns
        assert 'common_patterns' in patterns
        assert 'weak_keywords' in patterns
        assert 'zero_padding' in patterns
        assert 'ff_padding' in patterns

    def test_detect_patterns_invalid_type(self):
        """测试无效类型模式检测。"""
        with pytest.raises(TypeError):
            self.evaluator.detect_patterns("not bytes")

    def test_detect_repeated_bytes(self):
        """测试重复字节检测。"""
        key = b'\x42' * 10
        result = self.evaluator._detect_repeated_bytes(key)
        assert result['found'] is True
        assert result['max_run_length'] == 10
        assert result['byte_value'] == 0x42

    def test_detect_repeated_bytes_short(self):
        """测试短密钥重复字节检测。"""
        key = b'\x00\x00\x00'
        result = self.evaluator._detect_repeated_bytes(key)
        assert result['found'] is False

    def test_detect_increasing_sequence(self):
        """测试递增序列检测。"""
        key = bytes(range(10))
        result = self.evaluator._detect_increasing_sequence(key)
        assert result['found'] is True
        assert result['max_run_length'] == 10

    def test_detect_decreasing_sequence(self):
        """测试递减序列检测。"""
        key = bytes(range(9, -1, -1))
        result = self.evaluator._detect_decreasing_sequence(key)
        assert result['found'] is True
        assert result['max_run_length'] == 10

    def test_detect_common_patterns(self):
        """测试常见模式检测。"""
        key = b'password12345678' + b'\x00' * 16
        result = self.evaluator._detect_common_patterns(key)
        assert result['found'] is True
        assert len(result['patterns']) > 0

    def test_detect_weak_keywords(self):
        """测试弱关键词检测。"""
        key = b'passwordadminroot' + b'\x00' * 16
        result = self.evaluator._detect_weak_keywords(key)
        assert result['found'] is True
        assert 'password' in result['keywords']

    def test_detect_zero_padding(self):
        """测试零填充检测。"""
        key = b'data' + b'\x00' * 28
        result = self.evaluator._detect_zero_padding(key)
        assert result['found'] is True
        assert result['zero_count'] == 28

    def test_detect_ff_padding(self):
        """测试0xFF填充检测。"""
        key = b'data' + b'\xff' * 28
        result = self.evaluator._detect_ff_padding(key)
        assert result['found'] is True
        assert result['ff_count'] == 28

    def test_estimate_crack_time_strong(self):
        """测试强密钥破解时间估算。"""
        import os
        key = os.urandom(32)
        result = self.evaluator.estimate_crack_time(key)

        assert 'online_attack' in result
        assert 'offline_fast' in result
        assert 'offline_slow' in result
        assert 'brute_force' in result
        assert 'total_entropy_bits' in result
        assert result['total_entropy_bits'] > 100

    def test_estimate_crack_time_weak(self):
        """测试弱密钥破解时间估算。"""
        key = b'12345678'
        result = self.evaluator.estimate_crack_time(key)

        assert 'online_attack' in result
        assert 'offline_fast' in result
        assert result['total_entropy_bits'] < 100

    def test_estimate_crack_time_empty(self):
        """测试空密钥破解时间估算。"""
        result = self.evaluator.estimate_crack_time(b'')
        assert result['online_attack'] == 'instant'

    def test_char_diversity(self):
        """测试字符多样性统计。"""
        import os
        key = os.urandom(32)
        result = self.evaluator._char_diversity(key)

        assert 'unique_bytes' in result
        assert 'total_bytes' in result
        assert 'diversity_ratio' in result
        assert 'byte_range_min' in result
        assert 'byte_range_max' in result
        assert result['total_bytes'] == 32
        assert result['unique_bytes'] > 0

    def test_char_diversity_empty(self):
        """测试空密钥字符多样性。"""
        result = self.evaluator._char_diversity(b'')
        assert result['unique_bytes'] == 0
        assert result['total_bytes'] == 0

    def test_strength_levels(self):
        """测试强度等级划分。"""
        assert self.evaluator._get_strength_level(0.9) == 'very_strong'
        assert self.evaluator._get_strength_level(0.7) == 'strong'
        assert self.evaluator._get_strength_level(0.4) == 'medium'
        assert self.evaluator._get_strength_level(0.1) == 'weak'

    def test_recommendations_strong_key(self):
        """测试强密钥建议。"""
        import os
        key = os.urandom(32)
        result = self.evaluator.evaluate(key)
        assert isinstance(result['recommendations'], list)
        assert len(result['recommendations']) > 0

    def test_recommendations_weak_key(self):
        """测试弱密钥建议。"""
        key = b'\x00' * 8
        result = self.evaluator.evaluate(key)
        assert len(result['recommendations']) > 1

    def test_format_time(self):
        """测试时间格式化。"""
        assert self.evaluator._format_time(0.0001) == 'instant'
        assert '毫秒' in self.evaluator._format_time(0.5)
        assert '秒' in self.evaluator._format_time(30)
        assert '分钟' in self.evaluator._format_time(120)
        assert '小时' in self.evaluator._format_time(7200)
        assert '天' in self.evaluator._format_time(172800)
        assert '年' in self.evaluator._format_time(63072000)
        assert '千年' in self.evaluator._format_time(31536000 * 5000)
        assert '百万年' in self.evaluator._format_time(31536000 * 2e6)
        assert '十亿年' in self.evaluator._format_time(31536000 * 2e9)

    def test_evaluate_invalid_type(self):
        """测试无效类型评估。"""
        with pytest.raises(TypeError):
            self.evaluator.evaluate("not bytes")

    def test_crack_time_calculation(self):
        """测试破解时间计算。"""
        time = self.evaluator._crack_time(10, 1000)
        assert time > 0
        assert time < 1

    def test_crack_time_zero_entropy(self):
        """测试零熵破解时间。"""
        time = self.evaluator._crack_time(0, 1000)
        assert time == 0.0
