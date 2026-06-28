"""
GPG加密模块测试
"""

import pytest
from ai_llm_agent_crawler.security.gpg_encryption import (
    EncryptionMode,
    GPGKeyManager,
    GPGDictionaryEncryptor,
    SecureDictionaryStorage,
)


class TestGPGKeyManager:
    """测试GPG密钥管理器"""

    def test_generate_key_pair(self):
        """测试生成密钥对"""
        manager = GPGKeyManager()
        private_key, public_key = manager.generate_key_pair("test_key")

        assert private_key.key_id == "test_key"
        assert public_key.key_id == "test_key"
        assert private_key.key_type == "private"
        assert public_key.key_type == "public"
        assert private_key.fingerprint == public_key.fingerprint

    def test_get_key(self):
        """测试获取密钥"""
        manager = GPGKeyManager()
        manager.generate_key_pair("test_key")

        private_key = manager.get_key("test_key", "private")
        public_key = manager.get_key("test_key", "public")

        assert private_key is not None
        assert public_key is not None
        assert private_key.key_type == "private"
        assert public_key.key_type == "public"

    def test_import_key(self):
        """测试导入密钥"""
        manager = GPGKeyManager()

        # 先生成一个密钥对
        _, public_key = manager.generate_key_pair("original")

        # 导入公钥数据作为新密钥
        imported_key = manager.import_key(public_key.key_data, "public", "imported")

        assert imported_key.key_id == "imported"
        assert imported_key.key_type == "public"

    def test_export_key(self):
        """测试导出密钥"""
        manager = GPGKeyManager()
        manager.generate_key_pair("test_key")

        exported_private = manager.export_key("test_key", "private")
        exported_public = manager.export_key("test_key", "public")

        assert exported_private is not None
        assert exported_public is not None
        assert len(exported_private) > 0
        assert len(exported_public) > 0

    def test_delete_key(self):
        """测试删除密钥"""
        manager = GPGKeyManager()
        manager.generate_key_pair("test_key")

        assert manager.delete_key("test_key", "private")
        assert manager.get_key("test_key", "private") is None

    def test_list_keys(self):
        """测试列出密钥"""
        manager = GPGKeyManager()
        manager.generate_key_pair("key1")
        manager.generate_key_pair("key2")

        keys = manager.list_keys()

        assert len(keys) == 4  # 2 pairs = 4 keys


class TestGPGDictionaryEncryptor:
    """测试GPG字典加密器"""

    def setup_method(self):
        """设置测试方法"""
        self.key_manager = GPGKeyManager()
        self.private_key, self.public_key = self.key_manager.generate_key_pair("test_key")
        self.encryptor = GPGDictionaryEncryptor(self.key_manager)

    def test_encrypt_dict_hybrid(self):
        """测试混合加密"""
        data = {"key": "value", "number": 42}

        encrypted_data = self.encryptor.encrypt_dict(
            data,
            "test_key",
            EncryptionMode.HYBRID
        )

        assert encrypted_data.mode == "hybrid"
        assert encrypted_data.key_id == "test_key"
        assert encrypted_data.encrypted_key is not None
        assert len(encrypted_data.ciphertext) > 0

    def test_encrypt_decrypt_dict_hybrid(self):
        """测试混合加密和解密"""
        data = {"key": "value", "number": 42}

        encrypted_data = self.encryptor.encrypt_dict(
            data,
            "test_key",
            EncryptionMode.HYBRID
        )

        decrypted_data = self.encryptor.decrypt_dict(
            encrypted_data,
            "test_key"
        )

        assert decrypted_data == data

    def test_encrypt_decrypt_dict_with_signature(self):
        """测试带签名的加密和解密"""
        # 生成签名密钥对
        sign_private, _ = self.key_manager.generate_key_pair("sign_key")

        data = {"key": "value", "number": 42}

        encrypted_data = self.encryptor.encrypt_dict(
            data,
            "test_key",
            EncryptionMode.HYBRID,
            sign_with_key_id="sign_key"
        )

        assert encrypted_data.signature is not None

        decrypted_data = self.encryptor.decrypt_dict(
            encrypted_data,
            "test_key",
            verify_with_key_id="sign_key"
        )

        assert decrypted_data == data

    def test_encrypt_dict_to_json(self):
        """测试加密为JSON"""
        data = {"key": "value"}

        json_str = self.encryptor.encrypt_dict_to_json(
            data,
            "test_key",
            EncryptionMode.HYBRID
        )

        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_decrypt_dict_from_json(self):
        """测试从JSON解密"""
        data = {"key": "value"}

        json_str = self.encryptor.encrypt_dict_to_json(
            data,
            "test_key",
            EncryptionMode.HYBRID
        )

        decrypted_data = self.encryptor.decrypt_dict_from_json(
            json_str,
            "test_key"
        )

        assert decrypted_data == data

    def test_encrypt_complex_dict(self):
        """测试复杂字典加密"""
        data = {
            "name": "test",
            "nested": {"a": 1, "b": 2},
            "list": [1, 2, 3],
            "boolean": True,
            "null": None,
        }

        encrypted_data = self.encryptor.encrypt_dict(
            data,
            "test_key",
            EncryptionMode.HYBRID
        )

        decrypted_data = self.encryptor.decrypt_dict(
            encrypted_data,
            "test_key"
        )

        assert decrypted_data == data


class TestSecureDictionaryStorage:
    """测试安全字典存储"""

    def setup_method(self):
        """设置测试方法"""
        self.key_manager = GPGKeyManager()
        self.private_key, self.public_key = self.key_manager.generate_key_pair("test_key")
        self.encryptor = GPGDictionaryEncryptor(self.key_manager)
        self.storage = SecureDictionaryStorage(self.encryptor)

    def test_store_and_retrieve(self):
        """测试存储和检索"""
        data = {"key": "value"}

        self.storage.store("test_data", data, "test_key")

        retrieved_data = self.storage.retrieve("test_data", "test_key")

        assert retrieved_data == data

    def test_delete(self):
        """测试删除"""
        data = {"key": "value"}
        self.storage.store("test_data", data, "test_key")

        assert self.storage.delete("test_data")
        assert self.storage.retrieve("test_data", "test_key") is None

    def test_list_keys(self):
        """测试列出存储键"""
        self.storage.store("data1", {"a": 1}, "test_key")
        self.storage.store("data2", {"b": 2}, "test_key")

        keys = self.storage.list_keys()

        assert len(keys) == 2
        assert "data1" in keys
        assert "data2" in keys

    def test_export_import_storage(self):
        """测试导出和导入存储"""
        self.storage.store("data1", {"a": 1}, "test_key")
        self.storage.store("data2", {"b": 2}, "test_key")

        exported = self.storage.export_storage()

        # 创建新存储并导入
        new_storage = SecureDictionaryStorage()
        new_storage.import_storage(exported)

        assert len(new_storage.list_keys()) == 2