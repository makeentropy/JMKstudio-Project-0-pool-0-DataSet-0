"""
steganography - Stego encoding/decoding with CA verification & probe anchors.

Implements:
- Stego encoding: data hidden within a carrier medium (byte array / list)
- CA-based verification of encoded payloads
- Probe anchors: markers within the stego stream that allow probes
  to locate and extract hidden data segments
"""

from .encoder import StegoEncoder, StegoDecoder, AnchorPoint
from .medium import StegoMedium, MediumType
from .ca_stego import CAStegoVerifier

__all__ = [
    "StegoEncoder",
    "StegoDecoder",
    "AnchorPoint",
    "StegoMedium",
    "MediumType",
    "CAStegoVerifier",
]
