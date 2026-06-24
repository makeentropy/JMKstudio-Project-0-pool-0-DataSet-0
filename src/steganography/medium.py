"""
Stego Medium - the carrier data that hides information.

Medium types:
- BYTES: raw byte array (LSB steganography)
- LIST: generic list-based carrier (value modulation)
- TEXT: text with zero-width character steganography
"""

from enum import Enum
from typing import Union, List, Optional
import struct


class MediumType(Enum):
    BYTES = "bytes"
    LIST = "list"
    TEXT = "text"


class StegoMedium:
    """
    Wraps a carrier medium and provides uniform read/write access
    for steganographic bit operations.
    """

    def __init__(self, carrier, medium_type: Optional[MediumType] = None):
        self._carrier = carrier
        if medium_type is None:
            medium_type = self._detect_type(carrier)
        self.type = medium_type
        self._bits_available = self._compute_capacity()

    def _detect_type(self, carrier) -> MediumType:
        if isinstance(carrier, (bytes, bytearray)):
            return MediumType.BYTES
        if isinstance(carrier, str):
            return MediumType.TEXT
        if isinstance(carrier, list):
            return MediumType.LIST
        raise ValueError(f"Unsupported carrier type: {type(carrier)}")

    def _compute_capacity(self) -> int:
        if self.type == MediumType.BYTES:
            return len(self._carrier)
        elif self.type == MediumType.LIST:
            return len(self._carrier)
        elif self.type == MediumType.TEXT:
            return len(self._carrier) * 8
        return 0

    @property
    def capacity_bytes(self) -> int:
        return self._bits_available // 8

    @property
    def carrier(self):
        return self._carrier

    def set_lsb(self, index: int, bit: int) -> None:
        bit = 1 if bit else 0
        if self.type == MediumType.BYTES:
            if not isinstance(self._carrier, bytearray):
                self._carrier = bytearray(self._carrier)
            self._carrier[index] = (self._carrier[index] & 0xFE) | bit
        elif self.type == MediumType.LIST:
            val = self._carrier[index]
            if isinstance(val, int):
                self._carrier[index] = (val & 0xFFFFFFFE) | bit
            else:
                self._carrier[index] = bit
        elif self.type == MediumType.TEXT:
            char_idx = index // 8
            bit_idx = index % 8
            char_code = ord(self._carrier[char_idx])
            char_code = (char_code & ~(1 << bit_idx)) | (bit << bit_idx)
            chars = list(self._carrier)
            chars[char_idx] = chr(char_code)
            self._carrier = "".join(chars)

    def get_lsb(self, index: int) -> int:
        if self.type == MediumType.BYTES:
            return self._carrier[index] & 1
        elif self.type == MediumType.LIST:
            val = self._carrier[index]
            if isinstance(val, int):
                return val & 1
            return 1 if val else 0
        elif self.type == MediumType.TEXT:
            char_idx = index // 8
            bit_idx = index % 8
            return (ord(self._carrier[char_idx]) >> bit_idx) & 1
        return 0

    def __len__(self) -> int:
        if self.type == MediumType.BYTES:
            return len(self._carrier)
        elif self.type == MediumType.LIST:
            return len(self._carrier)
        elif self.type == MediumType.TEXT:
            return len(self._carrier) * 8
        return 0

    def __repr__(self) -> str:
        return f"<StegoMedium type={self.type.value} capacity={self.capacity_bytes}B>"
