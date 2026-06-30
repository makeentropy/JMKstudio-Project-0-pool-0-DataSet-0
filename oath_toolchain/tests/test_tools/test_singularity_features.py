"""密钥奇点特征提取单元测试。"""
import pytest
import math

from oath_toolchain.tools.singularity.key_features import KeySingularityFeatures


class TestKeySingularityFeatures:
    """测试KeySingularityFeatures类。"""

    def setup_method(self):
        """每个测试前初始化特征提取器。"""
        self.extractor = KeySingularityFeatures()

    def test_extract_invalid_type(self):
        """测试无效类型提取。"""
        with pytest.raises(TypeError):
            self.extractor.extract("not bytes")

    def test_extract_empty_key(self):
        """测试空密钥提取。"""
        result = self.extractor.extract(b"")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_extract_random_key(self):
        """测试随机密钥提取。"""
        import os
        key = os.urandom(32)
        result = self.extractor.extract(key)
        assert isinstance(result, dict)
        assert 'dist_entropy' in result
        assert 'seq_autocorr_1' in result
        assert 'struct_repeat_max' in result
        assert 'spec_low_ratio' in result
        assert 'geo_distance_mean' in result

    def test_extract_distribution_features(self):
        """测试分布特征提取。"""
        key = bytes(range(256))
        result = self.extractor.extract(key)
        assert result['dist_entropy'] > 7.0
        assert result['dist_unique_ratio'] == 1.0

    def test_extract_uniform_key(self):
        """测试均匀密钥分布特征。"""
        key = b'\x00' * 64
        result = self.extractor.extract(key)
        assert result['dist_entropy'] == 0.0
        assert result['dist_unique_ratio'] == 1.0 / 256.0

    def test_feature_vector_default_size(self):
        """测试默认大小的特征向量。"""
        import os
        key = os.urandom(32)
        vector = self.extractor.feature_vector(key)
        assert len(vector) == 64
        assert all(isinstance(v, float) for v in vector)

    def test_feature_vector_custom_size(self):
        """测试自定义大小的特征向量。"""
        import os
        key = os.urandom(32)
        vector = self.extractor.feature_vector(key, size=32)
        assert len(vector) == 32

    def test_feature_vector_invalid_key_type(self):
        """测试无效密钥类型的特征向量。"""
        with pytest.raises(TypeError):
            self.extractor.feature_vector("not bytes")

    def test_feature_vector_invalid_size(self):
        """测试无效大小的特征向量。"""
        with pytest.raises(ValueError):
            self.extractor.feature_vector(b"test", size=0)

    def test_feature_vector_normalized(self):
        """测试特征向量已归一化。"""
        import os
        key = os.urandom(32)
        vector = self.extractor.feature_vector(key)
        norm = math.sqrt(sum(v * v for v in vector))
        assert abs(norm - 1.0) < 0.001

    def test_similarity_identical_keys(self):
        """测试相同密钥的相似度。"""
        import os
        key = os.urandom(32)
        sim = self.extractor.similarity(key, key)
        assert abs(sim - 1.0) < 0.001

    def test_similarity_different_keys(self):
        """测试不同密钥的相似度。"""
        import os
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        sim = self.extractor.similarity(key1, key2)
        assert 0.0 <= sim <= 1.0

    def test_similarity_invalid_type(self):
        """测试无效类型相似度。"""
        with pytest.raises(TypeError):
            self.extractor.similarity("not bytes", b"test")
        with pytest.raises(TypeError):
            self.extractor.similarity(b"test", "not bytes")

    def test_sequence_features_short_key(self):
        """测试短密钥序列特征。"""
        key = b'\x00\x01\x02'
        result = self.extractor.extract(key)
        assert 'seq_autocorr_1' in result

    def test_structure_features_repeated(self):
        """测试重复字节结构特征。"""
        key = b'\x42' * 64
        result = self.extractor.extract(key)
        assert result['struct_repeat_max'] == 64
        assert result['struct_repeat_ratio'] == 1.0

    def test_structure_features_increasing(self):
        """测试递增序列结构特征。"""
        key = bytes(range(64))
        result = self.extractor.extract(key)
        assert result['struct_increasing_max'] >= 4

    def test_spectral_features(self):
        """测试频谱特征。"""
        key = bytes(range(256))
        result = self.extractor.extract(key)
        assert 0.0 <= result['spec_low_ratio'] <= 1.0
        assert 0.0 <= result['spec_mid_ratio'] <= 1.0
        assert 0.0 <= result['spec_high_ratio'] <= 1.0
        assert abs(
            result['spec_low_ratio'] + result['spec_mid_ratio'] + result['spec_high_ratio'] - 1.0
        ) < 0.001

    def test_geometric_features(self):
        """测试几何特征。"""
        import os
        key = os.urandom(32)
        result = self.extractor.extract(key)
        assert 'geo_distance_mean' in result
        assert 'geo_centroid_x' in result
        assert 'geo_span' in result
        assert 0.0 <= result['geo_span'] <= 1.0

    def test_feature_count(self):
        """测试特征数量。"""
        import os
        key = os.urandom(64)
        result = self.extractor.extract(key)
        assert len(result) >= 20

    def test_all_features_are_floats(self):
        """测试所有特征值都是浮点数。"""
        import os
        key = os.urandom(32)
        result = self.extractor.extract(key)
        for value in result.values():
            assert isinstance(value, float)

    def test_zero_key_features(self):
        """测试全零密钥特征。"""
        key = b'\x00' * 32
        result = self.extractor.extract(key)
        assert result['dist_entropy'] == 0.0
        assert result['struct_zero_ratio'] == 1.0
        assert result['spec_low_ratio'] == 1.0

    def test_ff_key_features(self):
        """测试全0xFF密钥特征。"""
        key = b'\xff' * 32
        result = self.extractor.extract(key)
        assert result['struct_ff_ratio'] == 1.0
        assert result['spec_high_ratio'] == 1.0
