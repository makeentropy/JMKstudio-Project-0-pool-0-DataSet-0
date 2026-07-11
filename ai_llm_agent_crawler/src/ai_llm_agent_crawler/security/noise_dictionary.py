"""维度空间噪音字典。

生成可重现的「噪音字典」，作为 XOR 编码的密钥流来源。
字典按维度（dimension）+ 时钟种子（clock_seed）派生，确保同维度同时钟下可重现解码。
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class NoiseDictionary:
    """维度空间噪音字典。

    通过 ``dimension`` 与 ``clock_seed`` 派生确定性字节流，作为 XOR 密钥流。
    """

    dimension: str
    clock_seed: int
    salt: bytes = b"trae-noise-v1"
    _buffer: bytearray = field(default_factory=bytearray, repr=False)

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError("dimension 不能为空")
        if self.clock_seed < 0:
            raise ValueError("clock_seed 不能为负")

    # ------------------------------------------------------------------ derive
    def _derive_block(self, counter: int) -> bytes:
        """派生第 counter 块（32 字节）噪音。"""
        material = b"|".join(
            [
                self.dimension.encode("utf-8"),
                struct.pack(">q", self.clock_seed),
                struct.pack(">q", counter),
                self.salt,
            ]
        )
        return hashlib.sha256(material).digest()

    # ------------------------------------------------------------------ stream
    def keystream(self, length: int) -> bytes:
        """生成长度为 ``length`` 的密钥流。"""
        if length <= 0:
            return b""
        out = bytearray(length)
        counter = 0
        produced = 0
        while produced < length:
            block = self._derive_block(counter)
            n = min(len(block), length - produced)
            out[produced:produced + n] = block[:n]
            produced += n
            counter += 1
        return bytes(out)

    def iter_blocks(self, block_size: int = 32) -> Iterator[bytes]:
        """按块迭代噪音流。"""
        if block_size <= 0:
            raise ValueError("block_size 必须为正")
        counter = 0
        while True:
            block = self._derive_block(counter)
            yield block[:block_size]
            counter += 1

    # ------------------------------------------------------------------ fingerprint
    def fingerprint(self) -> str:
        """字典指纹（用于校验两端字典一致性）。"""
        return hashlib.sha256(
            b"|".join(
                [
                    self.dimension.encode("utf-8"),
                    struct.pack(">q", self.clock_seed),
                    self.salt,
                ]
            )
        ).hexdigest()

    def __len__(self) -> int:
        return 1 << 64  # 概念上无限长


def build_noise_dictionary(dimension: str, clock_seed: int, salt: bytes = b"trae-noise-v1") -> NoiseDictionary:
    """便捷构造噪音字典。"""
    return NoiseDictionary(dimension=dimension, clock_seed=clock_seed, salt=salt)
