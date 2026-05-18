import gnupg
import os
from typing import Optional, Dict, Any


class GPGManager:
    def __init__(self, gnupghome: Optional[str] = None):
        if gnupghome is None:
            gnupghome = os.path.join(os.getcwd(), 'data', 'gnupg')
        os.makedirs(gnupghome, exist_ok=True)
        self.gpg = gnupg.GPG(gnupghome=gnupghome)
        self.gnupghome = gnupghome

    def generate_key(self, name_real: str, name_email: str, passphrase: str,
                    key_length: int = 2048, key_type: str = 'RSA') -> Dict[str, Any]:
        input_data = self.gpg.gen_key_input(
            name_real=name_real,
            name_email=name_email,
            passphrase=passphrase,
            key_type=key_type,
            key_length=key_length
        )
        key = self.gpg.gen_key(input_data)
        return {
            'fingerprint': key.fingerprint,
            'keyid': key.keyid
        }

    def encrypt(self, data: str, recipients: list, armor: bool = True) -> str:
        encrypted = self.gpg.encrypt(data, recipients, armor=armor)
        return str(encrypted)

    def decrypt(self, encrypted_data: str, passphrase: Optional[str] = None) -> str:
        decrypted = self.gpg.decrypt(encrypted_data, passphrase=passphrase)
        return str(decrypted)

    def sign(self, data: str, keyid: Optional[str] = None, passphrase: Optional[str] = None) -> str:
        signed = self.gpg.sign(data, keyid=keyid, passphrase=passphrase)
        return str(signed)

    def verify(self, signed_data: str) -> Dict[str, Any]:
        verified = self.gpg.verify(signed_data)
        return {
            'valid': verified.valid,
            'fingerprint': verified.fingerprint,
            'keyid': verified.key_id
        }

    def list_keys(self, secret: bool = False) -> list:
        return self.gpg.list_keys(secret=secret)

    def export_key(self, keyid: str, secret: bool = False,
                  passphrase: Optional[str] = None) -> str:
        return str(self.gpg.export_keys(keyid, secret=secret, passphrase=passphrase))

    def import_key(self, key_data: str) -> Dict[str, Any]:
        result = self.gpg.import_keys(key_data)
        return {
            'count': result.count,
            'fingerprints': result.fingerprints,
            'results': result.results
        }

    def delete_key(self, keyid: str, secret: bool = False, passphrase: Optional[str] = None):
        self.gpg.delete_keys(keyid, secret=secret, passphrase=passphrase)
