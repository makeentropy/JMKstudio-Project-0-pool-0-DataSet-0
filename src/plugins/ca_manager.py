from .base_plugin import BasePlugin
from typing import Optional, Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gpg_ca import GPGManager, CAServer


class CAManagerPlugin(BasePlugin):
    def __init__(self):
        super().__init__("CA Manager", "1.0.0")
        self.ca_server: Optional[CAServer] = None
        self.gpg_manager: Optional[GPGManager] = None

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        if config:
            self.config.update(config)
        
        self.gpg_manager = GPGManager()
        self.ca_server = CAServer()
        
        return True

    def execute(self, **kwargs) -> Any:
        action = kwargs.get('action')
        
        if action == 'init_ca':
            return self._init_ca(**kwargs)
        elif action == 'register_user':
            return self._register_user(**kwargs)
        elif action == 'issue_cert':
            return self._issue_cert(**kwargs)
        elif action == 'list_users':
            return self._list_users()
        elif action == 'list_certs':
            return self._list_certs(**kwargs)
        elif action == 'encrypt':
            return self._encrypt(**kwargs)
        elif action == 'decrypt':
            return self._decrypt(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

    def _init_ca(self, email: str, passphrase: str) -> Dict[str, Any]:
        result = self.ca_server.initialize_ca(email, passphrase)
        return {'status': 'success', 'result': result}

    def _register_user(self, username: str, email: str, 
                      passphrase: str) -> Dict[str, Any]:
        result = self.ca_server.register_user(username, email, passphrase)
        return {'status': 'success', 'result': result}

    def _issue_cert(self, username: str, cert_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.ca_server.issue_certificate(username, cert_data)
        return {'status': 'success', 'result': result}

    def _list_users(self) -> Dict[str, Any]:
        users = self.ca_server.list_users()
        return {'status': 'success', 'users': users}

    def _list_certs(self, username: Optional[str] = None) -> Dict[str, Any]:
        certs = self.ca_server.list_certificates(username)
        return {'status': 'success', 'certificates': certs}

    def _encrypt(self, data: str, recipients: List[str]) -> Dict[str, Any]:
        encrypted = self.gpg_manager.encrypt(data, recipients)
        return {'status': 'success', 'encrypted': encrypted}

    def _decrypt(self, encrypted_data: str, 
                passphrase: Optional[str] = None) -> Dict[str, Any]:
        decrypted = self.gpg_manager.decrypt(encrypted_data, passphrase)
        return {'status': 'success', 'decrypted': decrypted}

    def cleanup(self) -> bool:
        return True
