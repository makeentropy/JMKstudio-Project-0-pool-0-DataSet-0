"""
Stego Encoder / Decoder with Anchor Points.

Anchor points (探针锚点) are special markers embedded in the stego stream
that allow probes to locate and decode hidden data segments. Each anchor
contains a tag and an offset pointer to the data segment.
"""

import struct
import zlib
import hashlib
from typing import Optional, List, Tuple
from dataclasses import dataclass

from .medium import StegoMedium, MediumType
from ..utils import generate_id, hash_data


MAGIC_HEADER = b"STG0"
ANCHOR_MAGIC = b"ANC"


@dataclass
class AnchorPoint:
    """
    Probe anchor point - a marker in the stego stream that points to
    a hidden data segment. Probes use anchors to locate and extract data.
    """
    anchor_id: str
    tag: str
    offset: int
    length: int
    payload_hash: str
    signature: Optional[bytes] = None

    def to_bytes(self) -> bytes:
        tag_bytes = self.tag.encode("utf-8")
        data = (
            ANCHOR_MAGIC
            + struct.pack(">H", len(self.anchor_id))
            + self.anchor_id.encode("utf-8")
            + struct.pack(">H", len(tag_bytes))
            + tag_bytes
            + struct.pack(">II", self.offset, self.length)
            + bytes.fromhex(self.payload_hash)
        )
        return data

    @classmethod
    def from_bytes(cls, data: bytes) -> "AnchorPoint":
        idx = 0
        if data[idx:idx+3] != ANCHOR_MAGIC:
            raise ValueError("Invalid anchor magic")
        idx += 3
        aid_len = struct.unpack(">H", data[idx:idx+2])[0]
        idx += 2
        anchor_id = data[idx:idx+aid_len].decode("utf-8")
        idx += aid_len
        tag_len = struct.unpack(">H", data[idx:idx+2])[0]
        idx += 2
        tag = data[idx:idx+tag_len].decode("utf-8")
        idx += tag_len
        offset, length = struct.unpack(">II", data[idx:idx+8])
        idx += 8
        payload_hash = data[idx:idx+32].hex()
        return cls(
            anchor_id=anchor_id,
            tag=tag,
            offset=offset,
            length=length,
            payload_hash=payload_hash,
        )


class StegoEncoder:
    """
    Encodes data into a carrier medium using LSB (Least Significant Bit)
    steganography, with anchor points for probe-based extraction.
    """

    def __init__(self, medium: Optional[StegoMedium] = None):
        self.medium = medium
        self.anchors: List[AnchorPoint] = []

    def set_medium(self, medium: StegoMedium) -> None:
        self.medium = medium
        self.anchors = []

    def encode(self, data: bytes, tag: str = "default",
               offset: Optional[int] = None) -> Tuple[StegoMedium, AnchorPoint]:
        if self.medium is None:
            raise ValueError("No medium set")

        compressed = zlib.compress(data, 9)
        payload = (
            MAGIC_HEADER
            + struct.pack(">I", len(data))
            + compressed
        )

        capacity_bits = len(self.medium)
        needed_bits = len(payload) * 8
        if needed_bits > capacity_bits:
            raise ValueError(
                f"Payload too large: need {needed_bits} bits, "
                f"medium has {capacity_bits} bits"
            )

        start_offset = offset or 32
        bit_idx = start_offset
        for byte in payload:
            for bit_pos in range(8):
                bit = (byte >> (7 - bit_pos)) & 1
                self.medium.set_lsb(bit_idx, bit)
                bit_idx += 1

        payload_hash = hash_data(data)
        anchor = AnchorPoint(
            anchor_id=generate_id("anc"),
            tag=tag,
            offset=start_offset,
            length=len(data),
            payload_hash=payload_hash,
        )
        self.anchors.append(anchor)
        return self.medium, anchor

    def encode_multiple(self, segments: List[Tuple[bytes, str]]) -> StegoMedium:
        if self.medium is None:
            raise ValueError("No medium set")

        current_offset = 32
        for data, tag in segments:
            try:
                _, anchor = self.encode(data, tag, offset=current_offset)
                compressed_len = len(zlib.compress(data, 9))
                header_len = len(MAGIC_HEADER) + 4
                total_bits = (compressed_len + header_len) * 8
                current_offset += total_bits + 64
            except ValueError:
                break
        return self.medium


class StegoDecoder:
    """
    Decodes steganographic data from a medium.
    Can locate data by anchor, by tag, or extract all hidden segments.
    """

    def __init__(self, medium: Optional[StegoMedium] = None):
        self.medium = medium

    def set_medium(self, medium: StegoMedium) -> None:
        self.medium = medium

    def decode(self, payload_input) -> Optional[bytes]:
        if self.medium is None and payload_input is None:
            return None
        if isinstance(payload_input, (bytes, bytearray)):
            return self._decode_raw(payload_input)
        return None

    def _decode_raw(self, data: bytes) -> Optional[bytes]:
        try:
            if data[:4] == MAGIC_HEADER:
                orig_len = struct.unpack(">I", data[4:8])[0]
                compressed = data[8:]
                decompressed = zlib.decompress(compressed)
                if len(decompressed) == orig_len:
                    return decompressed
        except Exception:
            pass
        return data

    def extract_at(self, offset: int, length: int) -> Optional[bytes]:
        if self.medium is None:
            return None

        bits = []
        for i in range(length * 8 + 64 * 8):
            if offset + i >= len(self.medium):
                break
            bits.append(self.medium.get_lsb(offset + i))

        byte_data = bytearray()
        for i in range(0, len(bits) - 7, 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bits[i + j]
            byte_data.append(byte)

        return self._decode_raw(bytes(byte_data))

    def extract_by_anchor(self, anchor: AnchorPoint) -> Optional[bytes]:
        data = self.extract_at(anchor.offset, anchor.length)
        if data is None:
            return None
        if hash_data(data) != anchor.payload_hash:
            return None
        return data

    def find_anchors_by_tag(self, tag: str, anchors: List[AnchorPoint]) -> List[AnchorPoint]:
        return [a for a in anchors if a.tag == tag]
