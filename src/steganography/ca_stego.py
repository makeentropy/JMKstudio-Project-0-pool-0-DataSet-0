"""
CA-based Steganography Verification.

Signs stego payloads with CA-issued certificates so that probes and
nodes can verify both the integrity and the authenticity of hidden data.
"""

from typing import Optional, Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from .encoder import StegoEncoder, StegoDecoder, AnchorPoint
from .medium import StegoMedium
from ..utils import CA, Certificate, hash_data


class CAStegoVerifier:
    """
    Adds CA-based signature verification to steganographic operations.

    Flow:
    1. Encoder signs the stego payload with its private key
    2. Signature is embedded as an anchor attribute
    3. Decoder / node verifies the signature against the CA certificate
       before accepting the data
    """

    def __init__(self, ca: CA, cert: Certificate, private_key=None):
        self.ca = ca
        self.cert = cert
        self._private_key = private_key

    def sign_anchor(self, anchor: AnchorPoint, payload: bytes) -> AnchorPoint:
        if self._private_key is None:
            raise ValueError("No private key available for signing")
        signature = self._private_key.sign(
            payload + anchor.tag.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        anchor.signature = signature
        return anchor

    def verify_anchor(self, anchor: AnchorPoint, payload: bytes) -> bool:
        if anchor.signature is None:
            return False
        try:
            self.cert.public_key.verify(
                anchor.signature,
                payload + anchor.tag.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    def encode_verified(self, encoder: StegoEncoder, data: bytes,
                        tag: str = "default") -> Tuple[StegoMedium, AnchorPoint]:
        medium, anchor = encoder.encode(data, tag=tag)
        self.sign_anchor(anchor, data)
        return medium, anchor

    def decode_verified(self, decoder: StegoDecoder,
                        anchor: AnchorPoint) -> Optional[bytes]:
        data = decoder.extract_by_anchor(anchor)
        if data is None:
            return None
        if not self.verify_anchor(anchor, data):
            return None
        return data

    def verify_certificate_chain(self, cert: Certificate) -> bool:
        return self.ca.verify_certificate(cert)
