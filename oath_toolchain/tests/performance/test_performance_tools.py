"""工具性能测试。"""
from __future__ import annotations

import time
import statistics

import pytest

from oath_toolchain.core.math.vector import Vector
from oath_toolchain.tools.karmaca.space_dict import KarmaSpaceDict
from oath_toolchain.tools.karmaca.encryption import KarmacaEncryption
from oath_toolchain.tools.geometric_proof.geometric_hash import GeometricHash
from oath_toolchain.tools.nlptcmodel.key_generator import NLPTCKeyGenerator
from oath_toolchain.tools.nlptcmodel.text_features import TextFeatureExtractor
from oath_toolchain.tools.steganography.text_stego import TextSteganography


pytestmark = [pytest.mark.performance]


def measure_time(func, iterations=10):
    """测量函数执行时间。

    Args:
        func: 要测量的函数
        iterations: 迭代次数

    Returns:
        (平均时间, 最小时间, 最大时间, 时间列表) 元组
    """
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)

    avg = statistics.mean(times)
    minimum = min(times)
    maximum = max(times)
    return avg, minimum, maximum, times


class TestKarmaSpaceDictPerformance:
    """KARMACA空间字典性能测试。"""

    def _create_space_dict(self, dimensions=3, num_points=100):
        """创建空间字典。"""
        import os

        space_dict = KarmaSpaceDict(dimensions=dimensions, key_size=32)
        points = []
        keys = []
        for i in range(num_points):
            components = [(i * 0.1 + j * 0.05) % 1.0 for j in range(dimensions)]
            points.append(Vector(components))
            keys.append(os.urandom(32))
        space_dict.build(points, keys)
        return space_dict

    @pytest.mark.parametrize("num_points", [10, 50, 100, 500])
    def test_space_dict_build_performance(self, num_points):
        """测试空间字典构建性能。"""
        import os

        dimensions = 3
        points = []
        keys = []
        for i in range(num_points):
            components = [(i * 0.1 + j * 0.05) % 1.0 for j in range(dimensions)]
            points.append(Vector(components))
            keys.append(os.urandom(32))

        def build():
            sd = KarmaSpaceDict(dimensions=dimensions, key_size=32)
            sd.build(points, keys)

        avg, minimum, maximum, _ = measure_time(build, iterations=20)

        print(f"\n空间字典构建 ({num_points} points, {dimensions}D):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")

        assert avg > 0

    @pytest.mark.parametrize("dimensions", [2, 3, 4, 6])
    def test_space_dict_interpolation_performance(self, dimensions):
        """测试空间字典插值密钥性能。"""
        space_dict = self._create_space_dict(dimensions=dimensions, num_points=50)
        coordinate = Vector([0.5] * dimensions)

        def interpolate():
            space_dict.interpolate_key(coordinate)

        avg, minimum, maximum, _ = measure_time(interpolate, iterations=1000)

        print(f"\n空间字典插值密钥 ({dimensions}D, 50 points):")
        print(f"  平均时间: {avg*1000000:.3f} µs")
        print(f"  最小时间: {minimum*1000000:.3f} µs")
        print(f"  最大时间: {maximum*1000000:.3f} µs")
        print(f"  每秒: {1/avg:.0f} 次")

        assert avg > 0

    def test_space_dict_get_key_performance(self):
        """测试空间字典获取密钥性能。"""
        space_dict = self._create_space_dict(dimensions=3, num_points=100)
        coordinate = Vector([0.5, 0.5, 0.5])

        def get_key():
            space_dict.get_key(coordinate)

        avg, minimum, maximum, _ = measure_time(get_key, iterations=1000)

        print(f"\n空间字典获取密钥 (3D, 100 points):")
        print(f"  平均时间: {avg*1000000:.3f} µs")
        print(f"  最小时间: {minimum*1000000:.3f} µs")
        print(f"  最大时间: {maximum*1000000:.3f} µs")
        print(f"  每秒: {1/avg:.0f} 次")

        assert avg > 0


class TestGeometricHashPerformance:
    """几何哈希性能测试。"""

    @pytest.mark.parametrize(
        "data_size,name",
        [
            (1024, "1KB"),
            (10240, "10KB"),
            (102400, "100KB"),
        ],
    )
    @pytest.mark.parametrize("dimensions", [3, 4, 6])
    def test_geometric_hash_performance(self, data_size, name, dimensions):
        """测试几何哈希性能。"""
        import os

        data = os.urandom(data_size)
        gh = GeometricHash(dimensions=dimensions, hash_alg="sha256")

        def hash_data():
            gh.hash_data(data)

        avg, minimum, maximum, _ = measure_time(hash_data, iterations=50)
        throughput = data_size / avg / (1024 * 1024)

        print(f"\n几何哈希 ({name}, {dimensions}D):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  吞吐量: {throughput:.2f} MB/s")

        assert avg > 0

    def test_hash_to_point_performance(self, sample_data):
        """测试哈希映射到点性能。"""
        gh = GeometricHash(dimensions=4, hash_alg="sha256")

        def to_point():
            gh.hash_to_point(sample_data)

        avg, minimum, maximum, _ = measure_time(to_point, iterations=1000)

        print(f"\n几何哈希映射到点 (4D):")
        print(f"  平均时间: {avg*1000000:.3f} µs")
        print(f"  最小时间: {minimum*1000000:.3f} µs")
        print(f"  最大时间: {maximum*1000000:.3f} µs")
        print(f"  每秒: {1/avg:.0f} 次")

        assert avg > 0


class TestNLPKeyGenerationPerformance:
    """NLP密钥生成性能测试。"""

    def test_text_feature_extraction_performance(self, sample_text):
        """测试文本特征提取性能。"""
        extractor = TextFeatureExtractor()

        def extract():
            extractor.extract_features(sample_text)

        avg, minimum, maximum, _ = measure_time(extract, iterations=100)

        print(f"\nNLP文本特征提取:")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  每秒: {1/avg:.1f} 次")

        assert avg > 0

    def test_key_generation_performance(self, sample_text):
        """测试NLP密钥生成性能。"""
        keygen = NLPTCKeyGenerator()

        def generate():
            keygen.generate_key(sample_text, key_size=32)

        avg, minimum, maximum, _ = measure_time(generate, iterations=50)

        print(f"\nNLP密钥生成 (256位):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  每秒: {1/avg:.1f} 次")

        assert avg > 0


class TestSteganographyPerformance:
    """隐写性能测试。"""

    def _generate_carrier_lines(self, num_lines=1000):
        """生成载体文本（按行）。"""
        lines = []
        for i in range(num_lines):
            lines.append(f"Line {i + 1}: This is sample carrier text line.")
        return "\n".join(lines)

    def _generate_carrier_spaces(self, num_spaces=1000):
        """生成载体文本（按空格）。"""
        words = []
        for i in range(num_spaces):
            words.append(f"word{i}")
        return " ".join(words)

    def test_whitespace_embed_performance(self):
        """测试空格隐写嵌入性能。"""
        test_data = b"TestSecretData123"
        carrier = self._generate_carrier_lines(1000)
        stego = TextSteganography()

        def embed():
            stego.embed_whitespace(carrier, test_data)

        avg, minimum, maximum, _ = measure_time(embed, iterations=100)

        print(f"\n空格隐写嵌入 (数据: {len(test_data)} bytes):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  每秒: {1/avg:.1f} 次")

        assert avg > 0

    def test_whitespace_extract_performance(self):
        """测试空格隐写提取性能。"""
        test_data = b"TestSecretData123"
        carrier = self._generate_carrier_lines(1000)
        stego = TextSteganography()
        stego_text = stego.embed_whitespace(carrier, test_data)

        def extract():
            stego.extract_whitespace(stego_text)

        avg, minimum, maximum, _ = measure_time(extract, iterations=100)

        print(f"\n空格隐写提取 (数据: {len(test_data)} bytes):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  每秒: {1/avg:.1f} 次")

        assert avg > 0

    def test_unicode_embed_performance(self):
        """测试Unicode零宽字符隐写嵌入性能。"""
        test_data = b"TestSecretData123"
        carrier = self._generate_carrier_spaces(1000)
        stego = TextSteganography()

        def embed():
            stego.embed_unicode(carrier, test_data)

        avg, minimum, maximum, _ = measure_time(embed, iterations=50)

        print(f"\nUnicode隐写嵌入 (数据: {len(test_data)} bytes):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  每秒: {1/avg:.1f} 次")

        assert avg > 0


class TestKarmacaEncryptionPerformance:
    """KARMACA加密性能测试。"""

    def test_karmaca_encrypt_performance(self, sample_data):
        """测试KARMACA加密性能。"""
        import os

        space_dict = KarmaSpaceDict(dimensions=3, key_size=32)
        points = [
            Vector([0.0, 0.0, 0.0]),
            Vector([1.0, 0.0, 0.0]),
            Vector([0.0, 1.0, 0.0]),
            Vector([0.0, 0.0, 1.0]),
            Vector([1.0, 1.0, 0.0]),
            Vector([1.0, 0.0, 1.0]),
            Vector([0.0, 1.0, 1.0]),
            Vector([1.0, 1.0, 1.0]),
        ]
        keys = [os.urandom(32) for _ in points]
        space_dict.build(points, keys)

        karmaca = KarmacaEncryption()
        coordinate = Vector([0.5, 0.5, 0.5])

        def encrypt():
            karmaca.encrypt(sample_data, coordinate, space_dict)

        avg, minimum, maximum, _ = measure_time(encrypt, iterations=100)
        throughput = len(sample_data) / avg / 1024

        print(f"\nKARMACA加密 (3D, 8 points, {len(sample_data)} bytes):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  吞吐量: {throughput:.2f} KB/s")

        assert avg > 0

    def test_karmaca_decrypt_performance(self, sample_data):
        """测试KARMACA解密性能。"""
        import os

        space_dict = KarmaSpaceDict(dimensions=3, key_size=32)
        points = [
            Vector([0.0, 0.0, 0.0]),
            Vector([1.0, 0.0, 0.0]),
            Vector([0.0, 1.0, 0.0]),
            Vector([0.0, 0.0, 1.0]),
            Vector([1.0, 1.0, 0.0]),
            Vector([1.0, 0.0, 1.0]),
            Vector([0.0, 1.0, 1.0]),
            Vector([1.0, 1.0, 1.0]),
        ]
        keys = [os.urandom(32) for _ in points]
        space_dict.build(points, keys)

        karmaca = KarmacaEncryption()
        coordinate = Vector([0.5, 0.5, 0.5])
        encrypted = karmaca.encrypt(sample_data, coordinate, space_dict)

        def decrypt():
            karmaca.decrypt(encrypted, coordinate, space_dict)

        avg, minimum, maximum, _ = measure_time(decrypt, iterations=100)
        throughput = len(sample_data) / avg / 1024

        print(f"\nKARMACA解密 (3D, 8 points, {len(sample_data)} bytes):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  吞吐量: {throughput:.2f} KB/s")

        assert avg > 0
