"""
Probe - the core probe entity.

A probe:
1. Generates steganographically encoded data (with CA signature)
2. Decodes received stego data and validates it
3. Writes decoded data to the singularity memory matrix
4. Holds a certificate for its identity (the 'steganographic memory
   interface certificate with steganographic probe medium')
"""

import time
import threading
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from ..utils import generate_id, LogicLogger, CA, Certificate, hash_data
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from ..steganography import (
    StegoEncoder, StegoDecoder, AnchorPoint,
    StegoMedium, MediumType, CAStegoVerifier,
)
from ..memory_matrix import SingularityMatrix, MatrixCell


class ProbeState(Enum):
    IDLE = "idle"
    ENCODING = "encoding"
    DECODING = "decoding"
    WRITING = "writing"
    ERROR = "error"


@dataclass
class ProbeMetrics:
    probes_generated: int = 0
    probes_decoded: int = 0
    data_encoded_bytes: int = 0
    data_decoded_bytes: int = 0
    matrix_writes: int = 0
    validation_failures: int = 0


class ProbeCertificate(Certificate):
    """
    A probe's identity certificate - the 'steganographic memory interface
    certificate with steganographic probe medium'.

    Extends the base CA certificate with probe-specific attributes
    that describe the probe's medium and capabilities.
    """

    def __init__(self, probe_id: str, public_key, medium_type: MediumType,
                 ca: Optional[CA] = None, issuer: str = "CA_ROOT",
                 **kwargs):
        super().__init__(
            subject=f"probe:{probe_id}",
            public_key=public_key,
            issuer=issuer,
            **kwargs,
        )
        self.probe_id = probe_id
        self.medium_type = medium_type
        self.capabilities: List[str] = ["encode", "decode", "validate"]


class Probe:
    """
    A steganographic probe - generates and decodes hidden data,
    and organizes results into the singularity memory matrix.
    """

    def __init__(self, name: str, ca: CA,
                 matrix: Optional[SingularityMatrix] = None,
                 medium_type: MediumType = MediumType.BYTES,
                 logger: Optional[LogicLogger] = None):
        self.probe_id = generate_id("probe")
        self.name = name
        self.state = ProbeState.IDLE
        self.ca = ca
        self.matrix = matrix
        self.medium_type = medium_type
        self.logger = logger or LogicLogger(f"probe_{name}")

        self._private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        self._public_key = self._private_key.public_key()

        self.certificate = ProbeCertificate(
            probe_id=self.probe_id,
            public_key=self._public_key,
            medium_type=medium_type,
            ca=ca,
        )
        issued = ca.issue_certificate(self.certificate.subject, self._public_key)
        self.certificate.signature = issued.signature

        self._verifier = CAStegoVerifier(ca, self.certificate, self._private_key)
        self._encoder = StegoEncoder()
        self._decoder = StegoDecoder()
        self.metrics = ProbeMetrics()
        self._active_anchors: Dict[str, AnchorPoint] = {}
        self._lock = threading.RLock()

        self.logger.log("probe", "created", probe_id=self.probe_id, name=name)

    def attach_matrix(self, matrix: SingularityMatrix) -> None:
        self.matrix = matrix
        self.logger.log("probe", "matrix_attached", matrix_id=matrix.matrix_id)

    @property
    def anchors(self) -> List[AnchorPoint]:
        return list(self._active_anchors.values())

    def generate_carrier(self, size: int = 4096) -> StegoMedium:
        import os
        if self.medium_type == MediumType.BYTES:
            data = bytearray(os.urandom(size))
            return StegoMedium(data, MediumType.BYTES)
        elif self.medium_type == MediumType.LIST:
            data = list(os.urandom(size))
            return StegoMedium(data, MediumType.LIST)
        else:
            chars = "".join(chr(c % 95 + 32) for c in os.urandom(size))
            return StegoMedium(chars, MediumType.TEXT)

    def encode_to_medium(self, data: bytes, tag: str = "default",
                         medium: Optional[StegoMedium] = None) -> Tuple[StegoMedium, AnchorPoint]:
        with self._lock:
            self.state = ProbeState.ENCODING
            try:
                if medium is None:
                    medium = self.generate_carrier()
                self._encoder.set_medium(medium)
                medium, anchor = self._verifier.encode_verified(
                    self._encoder, data, tag=tag
                )
                self._active_anchors[anchor.anchor_id] = anchor
                self.metrics.probes_generated += 1
                self.metrics.data_encoded_bytes += len(data)
                self.logger.log("probe", "encoded",
                                anchor_id=anchor.anchor_id,
                                tag=tag, size=len(data))
                return medium, anchor
            except Exception as e:
                self.state = ProbeState.ERROR
                self.logger.log("probe", "encode_error", error=str(e))
                raise
            finally:
                if self.state != ProbeState.ERROR:
                    self.state = ProbeState.IDLE

    def decode_from_medium(self, medium: StegoMedium,
                           anchor: AnchorPoint) -> Optional[bytes]:
        with self._lock:
            self.state = ProbeState.DECODING
            try:
                self._decoder.set_medium(medium)
                data = self._verifier.decode_verified(self._decoder, anchor)
                if data is None:
                    self.metrics.validation_failures += 1
                    self.logger.log("probe", "decode_failed",
                                    anchor_id=anchor.anchor_id,
                                    reason="verification_failed")
                    return None
                self.metrics.probes_decoded += 1
                self.metrics.data_decoded_bytes += len(data)
                self.logger.log("probe", "decoded",
                                anchor_id=anchor.anchor_id,
                                size=len(data))

                if self.matrix is not None:
                    self._write_to_matrix(data, anchor)
                return data
            except Exception as e:
                self.state = ProbeState.ERROR
                self.logger.log("probe", "decode_error", error=str(e))
                return None
            finally:
                if self.state != ProbeState.ERROR:
                    self.state = ProbeState.IDLE

    def _write_to_matrix(self, data: bytes, anchor: AnchorPoint) -> Optional[MatrixCell]:
        if self.matrix is None:
            return None
        self.state = ProbeState.WRITING
        try:
            cell = self.matrix.write(
                anchor=anchor.anchor_id,
                data=data,
                source=f"probe:{self.probe_id}",
                tag=anchor.tag,
                metadata={
                    "anchor_tag": anchor.tag,
                    "anchor_offset": anchor.offset,
                    "payload_hash": anchor.payload_hash,
                },
            )
            self.metrics.matrix_writes += 1
            self.logger.log("probe", "matrix_write",
                            cell_id=cell.cell_id, anchor=anchor.anchor_id)
            return cell
        finally:
            self.state = ProbeState.IDLE

    def build_probe_request(self, data: bytes, tag: str = "default",
                            medium: Optional[StegoMedium] = None) -> Dict[str, Any]:
        medium, anchor = self.encode_to_medium(data, tag=tag, medium=medium)
        return {
            "probe_id": self.probe_id,
            "payload_hash": anchor.payload_hash,
            "certificate": self.certificate,
            "signature": anchor.signature,
            "anchor": anchor.anchor_id,
            "anchor_tag": anchor.tag,
            "payload": medium.carrier,
            "medium_type": self.medium_type.value,
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "name": self.name,
            "state": self.state.value,
            "medium_type": self.medium_type.value,
            "active_anchors": len(self._active_anchors),
            "metrics": {
                "probes_generated": self.metrics.probes_generated,
                "probes_decoded": self.metrics.probes_decoded,
                "data_encoded_bytes": self.metrics.data_encoded_bytes,
                "data_decoded_bytes": self.metrics.data_decoded_bytes,
                "matrix_writes": self.metrics.matrix_writes,
                "validation_failures": self.metrics.validation_failures,
            },
            "has_matrix": self.matrix is not None,
        }

    def __repr__(self) -> str:
        return f"<Probe id={self.probe_id} name={self.name} state={self.state.value}>"
