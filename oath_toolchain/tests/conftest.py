"""pytest 共享 fixtures 和 helper 函数。"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Tuple

import pytest

from oath_toolchain.core.crypto.primitives import AESCipher, RSACipher
from oath_toolchain.core.math.vector import Vector
from oath_toolchain.orchestration.qiankun_engine import QiankunEngine
from oath_toolchain.sdk.oath_sdk import OathSDK
from oath_toolchain.tools.ca_system.jmk_ca import JMKStudioCA
from oath_toolchain.tools.ca_system.certificate_types import CertificateType
from oath_toolchain.tools.dataset_pool.dataset import Dataset
from oath_toolchain.tools.karmaca.space_dict import KarmaSpaceDict


SAMPLE_TEXT = """这是一段测试文本。
用于测试各种加密和隐写功能。
包含多行内容，方便测试文本隐写。
Line 4: The quick brown fox jumps over the lazy dog.
Line 5: 中文测试内容。
Line 6: 1234567890!@#$%^&*()
Line 7: More sample text here.
Line 8: 神誓工具链测试。
Line 9: End of sample text.
Line 10: Final line."""

SAMPLE_DATA = b"Hello, World! This is a test message for encryption and steganography."

SAMPLE_DATASET_RECORDS = [
    {"id": 1, "name": "Alice", "score": 95},
    {"id": 2, "name": "Bob", "score": 87},
    {"id": 3, "name": "Charlie", "score": 92},
    {"id": 4, "name": "David", "score": 78},
    {"id": 5, "name": "Eve", "score": 88},
]


@pytest.fixture
def temp_dir():
    """临时目录 fixture。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_data():
    """样本数据 fixture。"""
    return SAMPLE_DATA


@pytest.fixture
def sample_text():
    """样本文本 fixture。"""
    return SAMPLE_TEXT


@pytest.fixture
def aes_key():
    """AES密钥 fixture (256位)。"""
    return AESCipher.generate_key(256)


@pytest.fixture
def aes_key_128():
    """AES密钥 fixture (128位)。"""
    return AESCipher.generate_key(128)


@pytest.fixture
def rsa_keys():
    """RSA密钥对 fixture (2048位，快速生成)。"""
    private_key, public_key = RSACipher.generate_keypair(key_size=2048)
    return private_key, public_key


@pytest.fixture
def rsa_keys_4096():
    """RSA密钥对 fixture (4096位，更安全)。"""
    private_key, public_key = RSACipher.generate_keypair(key_size=4096)
    return private_key, public_key


@pytest.fixture
def qiankun_engine():
    """QiankunEngine实例 fixture。"""
    engine = QiankunEngine()
    return engine


@pytest.fixture
def qiankun_engine_auto_register():
    """自动注册工具的QiankunEngine实例 fixture。"""
    engine = QiankunEngine(config={"auto_register_tools": True})
    return engine


@pytest.fixture
def oath_sdk():
    """OathSDK实例 fixture。"""
    sdk = OathSDK()
    return sdk


@pytest.fixture
def oath_sdk_auto():
    """自动注册工具的OathSDK实例 fixture。"""
    sdk = OathSDK(config={"auto_register_tools": True})
    return sdk


@pytest.fixture
def ca_root():
    """根CA实例 fixture。"""
    ca = JMKStudioCA(ca_name="Test Root CA")
    ca.initialize_root(key_size=2048, validity_days=365)
    return ca


@pytest.fixture
def ca_with_intermediate():
    """带有中间CA的根CA实例 fixture。"""
    ca = JMKStudioCA(ca_name="Test Root CA")
    ca.initialize_root(key_size=2048, validity_days=365)
    ca.create_intermediate_ca(
        "Test Intermediate CA",
        CertificateType.JMKSTUDIO_INTERMEDIATE,
        validity_days=180,
    )
    return ca


@pytest.fixture
def sample_dataset():
    """样本数据集 fixture。"""
    dataset = Dataset(name="test_dataset")
    dataset.description = "测试用数据集"
    dataset.data = {"records": SAMPLE_DATASET_RECORDS}
    dataset.metadata = {"source": "test", "category": "sample"}
    dataset.quality_score = 90.0
    return dataset


@pytest.fixture
def sample_space_dict():
    """样本空间字典 fixture (3维)。"""
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
    keys = [bytes([i] * 32) for i in range(len(points))]
    space_dict.build(points, keys)
    return space_dict


@pytest.fixture
def sample_space_dict_4d():
    """样本空间字典 fixture (4维)。"""
    space_dict = KarmaSpaceDict(dimensions=4, key_size=32)
    points = [
        Vector([0.0, 0.0, 0.0, 0.0]),
        Vector([1.0, 0.0, 0.0, 0.0]),
        Vector([0.0, 1.0, 0.0, 0.0]),
        Vector([0.0, 0.0, 1.0, 0.0]),
        Vector([0.0, 0.0, 0.0, 1.0]),
        Vector([1.0, 1.0, 0.0, 0.0]),
        Vector([1.0, 0.0, 1.0, 0.0]),
        Vector([1.0, 0.0, 0.0, 1.0]),
        Vector([0.0, 1.0, 1.0, 0.0]),
        Vector([0.0, 1.0, 0.0, 1.0]),
        Vector([0.0, 0.0, 1.0, 1.0]),
        Vector([1.0, 1.0, 1.0, 0.0]),
        Vector([1.0, 1.0, 0.0, 1.0]),
        Vector([1.0, 0.0, 1.0, 1.0]),
        Vector([0.0, 1.0, 1.0, 1.0]),
        Vector([1.0, 1.0, 1.0, 1.0]),
    ]
    keys = [bytes([i] * 32) for i in range(len(points))]
    space_dict.build(points, keys)
    return space_dict


@pytest.fixture
def sample_vector_3d():
    """3维样本向量 fixture。"""
    return Vector([0.5, 0.5, 0.5])


@pytest.fixture
def sample_vector_4d():
    """4维样本向量 fixture。"""
    return Vector([0.5, 0.5, 0.5, 0.5])


@pytest.fixture
def large_sample_data():
    """大样本数据 fixture (1MB)。"""
    return os.urandom(1024 * 1024)


@pytest.fixture
def medium_sample_data():
    """中等样本数据 fixture (100KB)。"""
    return os.urandom(100 * 1024)


@pytest.fixture
def small_sample_data():
    """小样本数据 fixture (1KB)。"""
    return os.urandom(1024)


def calculate_entropy(data: bytes) -> float:
    """计算数据的香农熵。

    Args:
        data: 输入数据

    Returns:
        熵值（0-8 bits/byte）
    """
    if not data:
        return 0.0

    freq = [0] * 256
    for byte in data:
        freq[byte] += 1

    length = len(data)
    entropy = 0.0
    for count in freq:
        if count > 0:
            p = count / length
            entropy -= p * (p.bit_length() - 1 if p > 0 else 0)
    import math

    entropy = 0.0
    for count in freq:
        if count > 0:
            p = count / length
            entropy -= p * math.log2(p)

    return entropy


def generate_carrier_text(num_lines: int = 100) -> str:
    """生成用于隐写测试的载体文本。

    Args:
        num_lines: 行数

    Returns:
        载体文本
    """
    lines = []
    for i in range(num_lines):
        lines.append(f"This is line number {i + 1} of the carrier text.")
    return "\n".join(lines)
