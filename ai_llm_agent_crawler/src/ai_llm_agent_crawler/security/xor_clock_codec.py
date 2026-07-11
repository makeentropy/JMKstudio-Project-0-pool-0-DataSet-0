"""XOR 时钟级校验编解码。

使用 :class:`NoiseDictionary` 提供的噪音流对数据进行 XOR 编码，
并附「时钟级校验码」（基于时钟种子的 HMAC 风格摘要）用于校验式解码。

编码容器结构（全部 bytes）：
    [version:1][dimension_len:2][dimension:N][clock_seed:8][payload_len:4]
    [xor_payload:M][clock_check:32]

``clock_check`` = sha256(version || dimension || clock_seed || payload_len || xor_payload || salt)
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import Any

from ai_llm_agent_crawler.security.noise_dictionary import NoiseDictionary

_VERSION = 1
_HEADER = struct.Struct(">B H q I")  # version, dim_len, clock_seed, payload_len
_CLOCK_CHECK_LEN = 32


@dataclass
class XorClockPayload:
    """XOR 时钟编码结果。"""

    dimension: str
    clock_seed: int
    ciphertext: bytes
    clock_check: bytes
    fingerprint: str

    def to_bytes(self) -> bytes:
        dim_b = self.dimension.encode("utf-8")
        header = _HEADER.pack(_VERSION, len(dim_b), self.clock_seed, len(self.ciphertext))
        return header + dim_b + self.ciphertext + self.clock_check

    @classmethod
    def from_bytes(cls, data: bytes) -> XorClockPayload:
        if len(data) < _HEADER.size + _CLOCK_CHECK_LEN:
            raise ValueError("数据过短，无法解析 XOR 时钟容器")
        version, dim_len, clock_seed, payload_len = _HEADER.unpack(data[: _HEADER.size])
        if version != _VERSION:
            raise ValueError(f"不支持的版本: {version}")
        offset = _HEADER.size
        dimension = data[offset:offset + dim_len].decode("utf-8")
        offset += dim_len
        if len(data) < offset + payload_len + _CLOCK_CHECK_LEN:
            raise ValueError("数据长度与头部声明不一致")
        ciphertext = data[offset:offset + payload_len]
        offset += payload_len
        clock_check = data[offset:offset + _CLOCK_CHECK_LEN]
        nd = NoiseDictionary(dimension=dimension, clock_seed=clock_seed)
        return cls(
            dimension=dimension,
            clock_seed=clock_seed,
            ciphertext=ciphertext,
            clock_check=clock_check,
            fingerprint=nd.fingerprint(),
        )


class XorClockCodec:
    """XOR 时钟级校验编解码器。"""

    def __init__(self, salt: bytes = b"trae-xor-clock-v1") -> None:
        self.salt: bytes = salt

    # ------------------------------------------------------------------ encode
    def encode(self, plaintext: bytes, dimension: str, clock_seed: int) -> XorClockPayload:
        if not isinstance(plaintext, (bytes, bytearray)):
            raise TypeError("plaintext 必须为 bytes")
        nd = NoiseDictionary(dimension=dimension, clock_seed=clock_seed, salt=self.salt)
        keystream = nd.keystream(len(plaintext))
        cipher = _xor(plaintext, keystream)
        check = self._clock_check(dimension, clock_seed, cipher)
        return XorClockPayload(
            dimension=dimension,
            clock_seed=clock_seed,
            ciphertext=cipher,
            clock_check=check,
            fingerprint=nd.fingerprint(),
        )

    # ------------------------------------------------------------------ decode
    def decode(self, payload: XorClockPayload, verify: bool = True) -> bytes:
        if verify:
            expected = self._clock_check(
                payload.dimension, payload.clock_seed, payload.ciphertext
            )
            if not _consteq(expected, payload.clock_check):
                raise ValueError("时钟级校验失败：数据可能被篡改或字典不匹配")
        nd = NoiseDictionary(
            dimension=payload.dimension, clock_seed=payload.clock_seed, salt=self.salt
        )
        keystream = nd.keystream(len(payload.ciphertext))
        return _xor(payload.ciphertext, keystream)

    # ------------------------------------------------------------------ helpers
    def _clock_check(self, dimension: str, clock_seed: int, ciphertext: bytes) -> bytes:
        material = b"|".join(
            [
                b"xor-clock",
                struct.pack(">B", _VERSION),
                dimension.encode("utf-8"),
                struct.pack(">q", clock_seed),
                struct.pack(">I", len(ciphertext)),
                ciphertext,
                self.salt,
            ]
        )
        return hashlib.sha256(material).digest()


def _xor(a: bytes, b: bytes) -> bytes:
    n = min(len(a), len(b))
    return bytes(x ^ y for x, y in zip(a[:n], b[:n]))


def _consteq(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0
