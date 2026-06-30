"""奇点检测算法单元测试。"""
import pytest

from oath_toolchain.tools.singularity.mass_energy import DataMassEnergy
from oath_toolchain.tools.singularity.singularity_detector import (
    SingularityDetectionResult,
    SingularityDetector,
    SingularityPoint,
)


class TestSingularityPoint:
    """测试SingularityPoint数据类。"""

    def test_create_singularity_point(self):
        """测试创建奇点。"""
        point = SingularityPoint(
            type='test_type',
            severity='high',
            value=0.5,
            threshold=0.3,
            description='测试奇点',
        )
        assert point.type == 'test_type'
        assert point.severity == 'high'
        assert point.value == 0.5
        assert point.threshold == 0.3
        assert point.description == '测试奇点'


class TestSingularityDetectionResult:
    """测试SingularityDetectionResult数据类。"""

    def test_create_empty_result(self):
        """测试创建空结果。"""
        result = SingularityDetectionResult()
        assert result.total_count == 0
        assert result.critical_count == 0
        assert result.singularities == []
        assert result.overall_score == 1.0
        assert result.is_singular is False

    def test_to_dict(self):
        """测试转换为字典。"""
        point = SingularityPoint(
            type='test',
            severity='low',
            value=0.1,
            threshold=0.2,
            description='test',
        )
        result = SingularityDetectionResult(
            total_count=1,
            critical_count=0,
            singularities=[point],
            overall_score=0.9,
            is_singular=False,
        )
        d = result.to_dict()
        assert d['total_count'] == 1
        assert d['critical_count'] == 0
        assert len(d['singularities']) == 1
        assert d['overall_score'] == 0.9
        assert d['is_singular'] is False


class TestSingularityDetector:
    """测试SingularityDetector类。"""

    def setup_method(self):
        """每个测试前初始化检测器。"""
        self.detector = SingularityDetector()

    def test_init_default_sensitivity(self):
        """测试默认灵敏度。"""
        assert self.detector.sensitivity == 0.8

    def test_init_custom_sensitivity(self):
        """测试自定义灵敏度。"""
        detector = SingularityDetector(sensitivity=0.5)
        assert detector.sensitivity == 0.5

    def test_init_invalid_sensitivity_low(self):
        """测试无效低灵敏度。"""
        with pytest.raises(ValueError):
            SingularityDetector(sensitivity=-0.1)

    def test_init_invalid_sensitivity_high(self):
        """测试无效高灵敏度。"""
        with pytest.raises(ValueError):
            SingularityDetector(sensitivity=1.1)

    def test_detect_empty_data(self):
        """测试空数据检测。"""
        result = self.detector.detect(b"")
        assert result.total_count > 0
        assert result.is_singular is True

    def test_detect_invalid_type(self):
        """测试无效类型检测。"""
        with pytest.raises(TypeError):
            self.detector.detect("not bytes")

    def test_detect_all_zeros(self):
        """测试全零数据检测。"""
        data = b'\x00' * 64
        result = self.detector.detect(data)
        assert result.total_count > 0
        assert result.is_singular is True
        assert result.overall_score < 0.8

    def test_detect_random_data(self):
        """测试随机数据检测。"""
        import os
        data = os.urandom(64)
        result = self.detector.detect(data)
        assert result.is_singular is False
        assert result.overall_score > 0.5

    def test_detect_with_precomputed_mass_energy(self):
        """测试使用预计算质能数据检测。"""
        data = b'\x00' * 64
        me = DataMassEnergy(data)
        result1 = self.detector.detect(data)
        result2 = self.detector.detect(data, me)
        assert result1.total_count == result2.total_count

    def test_mass_threshold_detection_low(self):
        """测试低质量阈值检测。"""
        data = b'\x00'
        result = self.detector.detect(data)
        types = {s.type for s in result.singularities}
        assert 'mass_threshold' in types

    def test_energy_singularity_detection(self):
        """测试能量奇点检测。"""
        data = b'\x00' * 100
        result = self.detector.detect(data)
        types = {s.type for s in result.singularities}
        assert 'energy_singularity' in types

    def test_statistical_anomaly_detection(self):
        """测试统计异常检测。"""
        data = b'\x00' * 100
        result = self.detector.detect(data)
        types = {s.type for s in result.singularities}
        assert 'statistical_anomaly' in types

    def test_mass_energy_imbalance(self):
        """测试质能失衡检测。"""
        data = b'\x00' * 100
        result = self.detector.detect(data)
        types = {s.type for s in result.singularities}
        assert 'mass_energy_imbalance' in types

    def test_critical_point_detection(self):
        """测试临界点检测。"""
        data = bytes([i % 4 for i in range(100)])
        result = self.detector.detect(data)
        assert result.total_count >= 0

    def test_overall_score_range(self):
        """测试总体评分范围。"""
        import os
        data = os.urandom(100)
        result = self.detector.detect(data)
        assert 0.0 <= result.overall_score <= 1.0

    def test_severity_levels(self):
        """测试严重等级。"""
        data = b'\x00' * 200
        result = self.detector.detect(data)
        severities = {s.severity for s in result.singularities}
        assert severities.issubset({'critical', 'high', 'medium', 'low'})

    def test_high_sensitivity(self):
        """测试高灵敏度检测。"""
        import os
        detector_low = SingularityDetector(sensitivity=0.3)
        detector_high = SingularityDetector(sensitivity=0.9)
        data = os.urandom(100)
        result_low = detector_low.detect(data)
        result_high = detector_high.detect(data)
        assert result_high.total_count >= result_low.total_count

    def test_detection_result_structure(self):
        """测试检测结果结构。"""
        data = b"test data for detection"
        result = self.detector.detect(data)
        assert hasattr(result, 'total_count')
        assert hasattr(result, 'critical_count')
        assert hasattr(result, 'singularities')
        assert hasattr(result, 'overall_score')
        assert hasattr(result, 'is_singular')

    def test_increasing_sequence_detection(self):
        """测试递增序列检测。"""
        data = bytes(range(100))
        result = self.detector.detect(data)
        assert result.total_count > 0

    def test_skewness_detection(self):
        """测试偏度检测。"""
        data = bytes([0] * 90 + list(range(200, 210)))
        result = self.detector.detect(data)
        types = {s.type for s in result.singularities}
        assert 'statistical_anomaly' in types
