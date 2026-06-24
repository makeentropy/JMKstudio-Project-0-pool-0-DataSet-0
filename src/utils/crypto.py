"""
Cryptographic utilities - CA, certificates, hashing, ID generation.
"""

import hashlib
import uuid
import time
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature


def generate_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}_{int(time.time() * 1000)}"


def hash_data(data: bytes, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    h.update(data)
    return h.hexdigest()


class Certificate:
    def __init__(self, subject: str, public_key, issuer: str = "CA_ROOT",
                 serial: Optional[str] = None, valid_from: float = None,
                 valid_to: float = None, signature: Optional[bytes] = None):
        self.subject = subject
        self.public_key = public_key
        self.issuer = issuer
        self.serial = serial or generate_id("cert")
        self.valid_from = valid_from or time.time()
        self.valid_to = valid_to or (time.time() + 365 * 24 * 3600)
        self.signature = signature

    def to_bytes(self) -> bytes:
        pub_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        payload = f"{self.subject}|{self.issuer}|{self.serial}|{self.valid_from}|{self.valid_to}|".encode()
        return payload + pub_pem

    def verify(self, ca_public_key) -> bool:
        if self.signature is None:
            return False
        try:
            ca_public_key.verify(
                self.signature,
                self.to_bytes(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "issuer": self.issuer,
            "serial": self.serial,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "has_signature": self.signature is not None,
        }


class CA:
    def __init__(self, name: str = "CA_ROOT"):
        self.name = name
        self.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        self._issued: Dict[str, Certificate] = {}

    def issue_certificate(self, subject: str, subject_public_key) -> Certificate:
        cert = Certificate(
            subject=subject,
            public_key=subject_public_key,
            issuer=self.name,
        )
        cert.signature = self.private_key.sign(
            cert.to_bytes(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        self._issued[cert.serial] = cert
        return cert

    def verify_certificate(self, cert: Certificate) -> bool:
        if cert.serial in self._issued:
            stored = self._issued[cert.serial]
            if stored.subject != cert.subject:
                return False
        return cert.verify(self.public_key)

    def revoke(self, serial: str) -> bool:
        if serial in self._issued:
            del self._issued[serial]
            return True
        return False
