import os
import json
from typing import Optional, Dict, Any, List
from .gpg_manager import GPGManager


class CAServer:
    def __init__(self, ca_name: str = "Superstring CA", data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(os.getcwd(), 'data', 'certificates')
        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir
        self.ca_name = ca_name
        self.gpg = GPGManager()
        self.ca_key: Optional[Dict[str, Any]] = None
        self.users_db = os.path.join(data_dir, 'users.json')
        self._init_db()

    def _init_db(self):
        if not os.path.exists(self.users_db):
            with open(self.users_db, 'w') as f:
                json.dump({'users': [], 'certificates': []}, f)

    def _load_db(self) -> Dict[str, Any]:
        with open(self.users_db, 'r') as f:
            return json.load(f)

    def _save_db(self, data: Dict[str, Any]):
        with open(self.users_db, 'w') as f:
            json.dump(data, f, indent=2)

    def initialize_ca(self, email: str, passphrase: str) -> Dict[str, Any]:
        result = self.gpg.generate_key(
            name_real=self.ca_name,
            name_email=email,
            passphrase=passphrase,
            key_length=4096
        )
        self.ca_key = result
        return result

    def register_user(self, username: str, email: str, passphrase: str) -> Dict[str, Any]:
        db = self._load_db()
        user_exists = any(u['username'] == username for u in db['users'])
        if user_exists:
            raise ValueError(f"User {username} already exists")

        key_result = self.gpg.generate_key(
            name_real=username,
            name_email=email,
            passphrase=passphrase
        )

        user = {
            'username': username,
            'email': email,
            'fingerprint': key_result['fingerprint'],
            'keyid': key_result['keyid'],
            'registered_at': os.path.getctime(self.gpg.gnupghome)
        }
        db['users'].append(user)
        self._save_db(db)

        return user

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        db = self._load_db()
        for user in db['users']:
            if user['username'] == username:
                return user
        return None

    def list_users(self) -> List[Dict[str, Any]]:
        db = self._load_db()
        return db['users']

    def issue_certificate(self, username: str, cert_data: Dict[str, Any]) -> Dict[str, Any]:
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User {username} not found")

        cert = {
            'id': f"CERT-{len(self._load_db()['certificates']) + 1:06d}",
            'username': username,
            'fingerprint': user['fingerprint'],
            'data': cert_data,
            'issued_at': os.path.getctime(__file__),
            'status': 'active'
        }

        db = self._load_db()
        db['certificates'].append(cert)
        self._save_db(db)

        return cert

    def list_certificates(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        db = self._load_db()
        certs = db['certificates']
        if username:
            certs = [c for c in certs if c['username'] == username]
        return certs

    def revoke_certificate(self, cert_id: str) -> bool:
        db = self._load_db()
        for cert in db['certificates']:
            if cert['id'] == cert_id:
                cert['status'] = 'revoked'
                cert['revoked_at'] = os.path.getctime(__file__)
                self._save_db(db)
                return True
        return False
