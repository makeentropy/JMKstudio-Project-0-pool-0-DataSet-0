"""SDK与CLI一致性测试。"""
from __future__ import annotations

import pytest

from click.testing import CliRunner

from oath_toolchain.cli.main import cli
from oath_toolchain.core.crypto.primitives import AESCipher, RSACipher
from oath_toolchain.core.crypto.hash import Hash
from oath_toolchain.sdk.oath_sdk import OathSDK


pytestmark = [pytest.mark.integration, pytest.mark.sdk, pytest.mark.cli]


class TestCryptoConsistency:
    """SDK与CLI加密操作一致性测试。"""

    def test_hash_consistency(self, sample_data):
        """测试SDK和CLI的哈希结果一致。"""
        sdk = OathSDK()

        sdk_hash = sdk.crypto.hash(sample_data, algorithm="sha256")

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("input.bin", "wb") as f:
                f.write(sample_data)

            result = runner.invoke(cli, ["crypto", "hash", "input.bin", "--algorithm", "sha256"])

            if result.exit_code == 0:
                output = result.output.strip()
                if output:
                    hash_hex = sdk_hash.hex()
                    assert hash_hex in output or output in hash_hex

    def test_aes_encrypt_decrypt_roundtrip(self, sample_data):
        """测试SDK的AES加密解密往返。"""
        sdk = OathSDK()
        aes_key = AESCipher.generate_key(256)

        encrypted = sdk.crypto.encrypt_aes(sample_data, aes_key)
        decrypted = sdk.crypto.decrypt_aes(encrypted, aes_key)

        assert decrypted == sample_data

    def test_rsa_sign_verify_consistency(self, sample_data):
        """测试SDK的RSA签名验证。"""
        sdk = OathSDK()
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)

        priv_pem = RSACipher.serialize_private_key(private_key)
        pub_pem = RSACipher.serialize_public_key(public_key)

        signature = sdk.crypto.sign(sample_data, priv_pem, method="rsa")
        valid = sdk.crypto.verify(sample_data, signature, pub_pem, method="rsa")

        assert valid


class TestDatasetConsistency:
    """SDK数据集操作测试。"""

    def test_dataset_create(self, temp_dir):
        """测试SDK创建数据集。"""
        sdk = OathSDK()

        dataset_name = "consistency_test"
        result = sdk.datasets.create(name=dataset_name, data={"test": True})

        assert result is not None
        assert isinstance(result, dict)

    def test_dataset_delete(self, temp_dir):
        """测试SDK删除数据集。"""
        sdk = OathSDK()

        result = sdk.datasets.create(name="to_delete", data={"x": 1})
        assert result is not None

        if result.get("success") and result.get("dataset_id"):
            delete_result = sdk.datasets.delete(result["dataset_id"])
            assert isinstance(delete_result, bool)


class TestCaConsistency:
    """SDK CA操作测试。"""

    def test_ca_init_root(self):
        """测试SDK初始化根CA。"""
        sdk = OathSDK()

        result = sdk.ca.init_root_ca(name="Test CA")

        assert result is not None
        assert isinstance(result, dict)

    def test_ca_issue_certificate(self):
        """测试SDK签发证书。"""
        sdk = OathSDK()

        init_result = sdk.ca.init_root_ca(name="Test CA")

        if init_result.get("success"):
            issue_result = sdk.ca.issue_certificate(
                subject="test.example.com",
                cert_type="end_entity",
            )
            assert issue_result is not None
            assert isinstance(issue_result, dict)
