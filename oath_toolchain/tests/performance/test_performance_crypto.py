"""密码学性能测试。"""
from __future__ import annotations

import time
import statistics

import pytest

from oath_toolchain.core.crypto.primitives import AESCipher, RSACipher
from oath_toolchain.core.crypto.hash import Hash
from oath_toolchain.core.crypto.kdf import KDF


pytestmark = [pytest.mark.performance, pytest.mark.crypto]


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


class TestAESPerformance:
    """AES加密性能测试。"""

    @pytest.mark.parametrize(
        "data_size,name",
        [
            (1024, "1KB"),
            (10240, "10KB"),
            (102400, "100KB"),
            (1048576, "1MB"),
        ],
    )
    def test_aes_encrypt_performance(self, data_size, name):
        """测试AES加密性能（不同数据量）。"""
        import os

        key = AESCipher.generate_key(256)
        data = os.urandom(data_size)

        def encrypt():
            AESCipher.encrypt(data, key)

        avg, minimum, maximum, _ = measure_time(encrypt, iterations=50)
        throughput = data_size / avg / (1024 * 1024)

        print(f"\nAES-256-GCM 加密 ({name}):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  吞吐量: {throughput:.2f} MB/s")

        assert avg > 0
        assert throughput > 0

    @pytest.mark.parametrize(
        "data_size,name",
        [
            (1024, "1KB"),
            (10240, "10KB"),
            (102400, "100KB"),
            (1048576, "1MB"),
        ],
    )
    def test_aes_decrypt_performance(self, data_size, name):
        """测试AES解密性能（不同数据量）。"""
        import os

        key = AESCipher.generate_key(256)
        data = os.urandom(data_size)
        ciphertext, nonce, tag = AESCipher.encrypt(data, key)

        def decrypt():
            AESCipher.decrypt(ciphertext, key, nonce, tag)

        avg, minimum, maximum, _ = measure_time(decrypt, iterations=50)
        throughput = data_size / avg / (1024 * 1024)

        print(f"\nAES-256-GCM 解密 ({name}):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  吞吐量: {throughput:.2f} MB/s")

        assert avg > 0
        assert throughput > 0

    def test_aes_key_generation_performance(self):
        """测试AES密钥生成性能。"""
        def generate():
            AESCipher.generate_key(256)

        avg, minimum, maximum, _ = measure_time(generate, iterations=1000)

        print(f"\nAES-256 密钥生成:")
        print(f"  平均时间: {avg*1000000:.3f} µs")
        print(f"  最小时间: {minimum*1000000:.3f} µs")
        print(f"  最大时间: {maximum*1000000:.3f} µs")
        print(f"  每秒生成: {1/avg:.0f} 次")

        assert avg > 0


class TestRSAPerformance:
    """RSA签名性能测试。"""

    def test_rsa_keygen_2048_performance(self):
        """测试RSA-2048密钥生成性能。"""
        def generate():
            RSACipher.generate_keypair(key_size=2048)

        avg, minimum, maximum, _ = measure_time(generate, iterations=5)

        print(f"\nRSA-2048 密钥生成:")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")

        assert avg > 0

    def test_rsa_sign_performance(self, sample_data, rsa_keys):
        """测试RSA签名性能。"""
        private_key, _ = rsa_keys

        def sign():
            RSACipher.sign(sample_data, private_key)

        avg, minimum, maximum, _ = measure_time(sign, iterations=50)

        print(f"\nRSA-2048 签名 (数据大小: {len(sample_data)} bytes):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  每秒签名: {1/avg:.1f} 次")

        assert avg > 0

    def test_rsa_verify_performance(self, sample_data, rsa_keys):
        """测试RSA验证性能。"""
        private_key, public_key = rsa_keys
        signature = RSACipher.sign(sample_data, private_key)

        def verify():
            RSACipher.verify(sample_data, signature, public_key)

        avg, minimum, maximum, _ = measure_time(verify, iterations=100)

        print(f"\nRSA-2048 验证 (数据大小: {len(sample_data)} bytes):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  每秒验证: {1/avg:.1f} 次")

        assert avg > 0

    def test_rsa_encrypt_performance(self, sample_data, rsa_keys):
        """测试RSA加密性能。"""
        _, public_key = rsa_keys
        small_data = sample_data[:128]

        def encrypt():
            RSACipher.encrypt(small_data, public_key)

        avg, minimum, maximum, _ = measure_time(encrypt, iterations=100)

        print(f"\nRSA-2048 加密 (数据大小: {len(small_data)} bytes):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  每秒加密: {1/avg:.1f} 次")

        assert avg > 0


class TestHashPerformance:
    """哈希性能测试。"""

    @pytest.mark.parametrize(
        "data_size,name",
        [
            (1024, "1KB"),
            (10240, "10KB"),
            (102400, "100KB"),
            (1048576, "1MB"),
        ],
    )
    def test_sha256_performance(self, data_size, name):
        """测试SHA-256哈希性能。"""
        import os

        data = os.urandom(data_size)

        def hash_data():
            Hash.sha256(data)

        avg, minimum, maximum, _ = measure_time(hash_data, iterations=100)
        throughput = data_size / avg / (1024 * 1024)

        print(f"\nSHA-256 ({name}):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  吞吐量: {throughput:.2f} MB/s")

        assert avg > 0

    @pytest.mark.parametrize(
        "data_size,name",
        [
            (1024, "1KB"),
            (10240, "10KB"),
            (102400, "100KB"),
            (1048576, "1MB"),
        ],
    )
    def test_sha512_performance(self, data_size, name):
        """测试SHA-512哈希性能。"""
        import os

        data = os.urandom(data_size)

        def hash_data():
            Hash.sha512(data)

        avg, minimum, maximum, _ = measure_time(hash_data, iterations=100)
        throughput = data_size / avg / (1024 * 1024)

        print(f"\nSHA-512 ({name}):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  吞吐量: {throughput:.2f} MB/s")

        assert avg > 0

    def test_blake2b_performance(self, medium_sample_data):
        """测试BLAKE2b哈希性能。"""
        data = medium_sample_data

        def hash_data():
            Hash.blake2b(data)

        avg, minimum, maximum, _ = measure_time(hash_data, iterations=100)
        throughput = len(data) / avg / (1024 * 1024)

        print(f"\nBLAKE2b ({len(data)//1024}KB):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")
        print(f"  吞吐量: {throughput:.2f} MB/s")

        assert avg > 0

    def test_hmac_performance(self, sample_data):
        """测试HMAC性能。"""
        import os

        key = os.urandom(32)

        def hmac_data():
            Hash.hmac(key, sample_data, "sha256")

        avg, minimum, maximum, _ = measure_time(hmac_data, iterations=1000)

        print(f"\nHMAC-SHA256 (数据大小: {len(sample_data)} bytes):")
        print(f"  平均时间: {avg*1000000:.3f} µs")
        print(f"  最小时间: {minimum*1000000:.3f} µs")
        print(f"  最大时间: {maximum*1000000:.3f} µs")
        print(f"  每秒: {1/avg:.0f} 次")

        assert avg > 0


class TestKDFPerformance:
    """密钥派生函数性能测试。"""

    def test_hkdf_performance(self):
        """测试HKDF性能。"""
        import os

        key = os.urandom(32)
        salt = os.urandom(16)

        def hkdf():
            KDF.hkdf(key, salt=salt, info=b"test", length=32)

        avg, minimum, maximum, _ = measure_time(hkdf, iterations=1000)

        print(f"\nHKDF-SHA256:")
        print(f"  平均时间: {avg*1000000:.3f} µs")
        print(f"  最小时间: {minimum*1000000:.3f} µs")
        print(f"  最大时间: {maximum*1000000:.3f} µs")
        print(f"  每秒: {1/avg:.0f} 次")

        assert avg > 0

    def test_pbkdf2_performance(self):
        """测试PBKDF2性能。"""
        password = b"test_password"
        salt = b"test_salt"

        def pbkdf2():
            Hash.pbkdf2(password, salt, iterations=10000, dkLen=32)

        avg, minimum, maximum, _ = measure_time(pbkdf2, iterations=10)

        print(f"\nPBKDF2-SHA256 (10000 iterations):")
        print(f"  平均时间: {avg*1000:.3f} ms")
        print(f"  最小时间: {minimum*1000:.3f} ms")
        print(f"  最大时间: {maximum*1000:.3f} ms")

        assert avg > 0
