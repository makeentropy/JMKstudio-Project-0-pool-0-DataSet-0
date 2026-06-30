"""隐写容量与安全性分析单元测试。"""
import pytest

from oath_toolchain.tools.steganography.capacity_analyzer import StegoCapacityAnalyzer


class TestStegoCapacityAnalyzer:
    """测试StegoCapacityAnalyzer类。"""

    def setup_method(self):
        """每个测试前初始化。"""
        self.analyzer = StegoCapacityAnalyzer()

    def test_init(self):
        """测试初始化。"""
        assert "binary" in self.analyzer.SUPPORTED_TYPES
        assert "text" in self.analyzer.SUPPORTED_TYPES

    def test_analyze_carrier_binary(self):
        """测试二进制载体分析。"""
        carrier = b"A" * 1000
        result = self.analyzer.analyze_carrier(carrier, "binary")
        assert result["carrier_type"] == "binary"
        assert result["total_size"] == 1000
        assert result["estimated_capacity"] > 0
        assert 0 <= result["entropy"] <= 8
        assert "recommendation" in result

    def test_analyze_carrier_text(self):
        """测试文本载体分析。"""
        carrier = b"Hello World! " * 100
        result = self.analyzer.analyze_carrier(carrier, "text")
        assert result["carrier_type"] == "text"
        assert result["total_size"] == len(carrier)

    def test_analyze_carrier_image(self):
        """测试图像载体分析。"""
        carrier = bytes(range(256)) * 10
        result = self.analyzer.analyze_carrier(carrier, "image")
        assert result["carrier_type"] == "image"

    def test_analyze_carrier_audio(self):
        """测试音频载体分析。"""
        carrier = bytes([i % 256 for i in range(1000)])
        result = self.analyzer.analyze_carrier(carrier, "audio")
        assert result["carrier_type"] == "audio"

    def test_analyze_carrier_certificate(self):
        """测试证书载体分析。"""
        from oath_toolchain.tools.steganography.cert_stego import CertificateSteganography
        cert = CertificateSteganography.generate_test_certificate()
        result = self.analyzer.analyze_carrier(cert, "certificate")
        assert result["carrier_type"] == "certificate"

    def test_analyze_carrier_invalid_type(self):
        """测试无效载体类型。"""
        with pytest.raises(ValueError):
            self.analyzer.analyze_carrier(b"data", "invalid")

    def test_analyze_carrier_invalid_data_type(self):
        """测试无效数据类型。"""
        with pytest.raises(TypeError):
            self.analyzer.analyze_carrier("not bytes")

    def test_estimate_security(self):
        """测试安全性评估。"""
        original = bytes([i % 256 for i in range(1000)])
        stego = bytearray(original)
        stego[0] ^= 0xFF
        result = self.analyzer.estimate_security(bytes(stego), original)
        assert "changed_bytes" in result
        assert "change_ratio" in result
        assert "original_entropy" in result
        assert "stego_entropy" in result
        assert "entropy_diff" in result
        assert "psnr" in result
        assert "detectability" in result
        assert "security_score" in result
        assert result["changed_bytes"] >= 1

    def test_estimate_security_identical(self):
        """测试完全相同数据的安全性评估。"""
        data = b"test data" * 100
        result = self.analyzer.estimate_security(data, data)
        assert result["changed_bytes"] == 0
        assert result["change_ratio"] == 0
        assert result["entropy_diff"] == 0
        assert result["psnr"] == float("inf")

    def test_estimate_security_different_lengths(self):
        """测试不同长度数据的安全性评估。"""
        with pytest.raises(ValueError):
            self.analyzer.estimate_security(b"short", b"longer data")

    def test_estimate_security_invalid_type(self):
        """测试无效类型的安全性评估。"""
        with pytest.raises(TypeError):
            self.analyzer.estimate_security("not bytes", b"data")

    def test_compare_statistics(self):
        """测试统计特性比较。"""
        data1 = bytes([i for i in range(256)] * 4)
        data2 = bytes([(i + 1) % 256 for i in range(256)] * 4)
        result = self.analyzer.compare_statistics(data1, data2)
        assert "size1" in result
        assert "size2" in result
        assert "entropy1" in result
        assert "entropy2" in result
        assert "mean1" in result
        assert "mean2" in result
        assert "std1" in result
        assert "std2" in result
        assert "correlation" in result
        assert "chi_square" in result

    def test_compare_statistics_identical(self):
        """测试相同数据的统计比较。"""
        data = b"same data" * 100
        result = self.analyzer.compare_statistics(data, data)
        assert result["size_diff"] == 0
        assert result["entropy_diff"] == 0
        assert result["mean_diff"] == 0
        assert result["correlation"] > 0.9

    def test_compare_statistics_invalid_type(self):
        """测试无效类型的统计比较。"""
        with pytest.raises(TypeError):
            self.analyzer.compare_statistics("not bytes", b"data")

    def test_generate_report(self):
        """测试生成分析报告。"""
        carrier = bytes([i % 256 for i in range(1000)])
        secret = b"Secret message"
        result = self.analyzer.generate_report(carrier, secret, "xor")
        assert "method" in result
        assert "carrier_analysis" in result
        assert "secret_size" in result
        assert "capacity_sufficient" in result
        assert "security_estimation" in result
        assert "overall_score" in result
        assert "recommendations" in result
        assert result["method"] == "xor"
        assert result["secret_size"] == len(secret)

    def test_generate_report_insufficient_capacity(self):
        """测试容量不足时的报告。"""
        carrier = b"tiny"
        secret = b"A" * 1000
        result = self.analyzer.generate_report(carrier, secret)
        assert result["capacity_sufficient"] is False
        assert len(result["recommendations"]) > 0

    def test_generate_report_invalid_carrier_type(self):
        """测试无效载体类型的报告。"""
        with pytest.raises(TypeError):
            self.analyzer.generate_report("not bytes", b"secret")

    def test_generate_report_invalid_secret_type(self):
        """测试无效秘密类型的报告。"""
        with pytest.raises(TypeError):
            self.analyzer.generate_report(b"carrier", "not bytes")

    def test_calculate_entropy_uniform(self):
        """测试均匀分布数据的熵值。"""
        data = bytes(range(256))
        entropy = self.analyzer._calculate_entropy(data)
        assert entropy > 7

    def test_calculate_entropy_constant(self):
        """测试常量数据的熵值。"""
        data = b"\x00" * 1000
        entropy = self.analyzer._calculate_entropy(data)
        assert entropy == 0

    def test_calculate_entropy_empty(self):
        """测试空数据的熵值。"""
        entropy = self.analyzer._calculate_entropy(b"")
        assert entropy == 0

    def test_byte_distribution(self):
        """测试字节分布统计。"""
        data = bytes(range(100))
        dist = self.analyzer._byte_distribution(data)
        assert "min" in dist
        assert "max" in dist
        assert "mean" in dist
        assert "median" in dist
        assert dist["min"] == 0
        assert dist["max"] == 99

    def test_byte_distribution_empty(self):
        """测试空数据的字节分布。"""
        dist = self.analyzer._byte_distribution(b"")
        assert dist["min"] == 0
