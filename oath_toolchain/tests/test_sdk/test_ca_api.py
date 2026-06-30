"""CA证书API单元测试。"""
import pytest

from oath_toolchain.sdk import OathSDK
from oath_toolchain.core.registry import ToolRegistry


class TestCAAPI:
    """测试CAAPI类。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.sdk = OathSDK()

    def test_init_root_ca(self):
        """测试初始化根CA。"""
        result = self.sdk.ca.init_root_ca("Test Root CA")
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert "certificate" in result
        assert "private_key" in result
        assert "-----BEGIN CERTIFICATE-----" in result["certificate"]
        assert "-----BEGIN PRIVATE KEY-----" in result["private_key"]

    def test_init_root_ca_default_name(self):
        """测试使用默认名称初始化根CA。"""
        result = self.sdk.ca.init_root_ca()
        assert result.get("success") is True
        assert result.get("ca_name") == "JMKstudio Root CA"

    def test_create_intermediate_ca(self):
        """测试创建中间CA。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        result = self.sdk.ca.create_intermediate_ca(
            "Test Intermediate CA",
            ca_type="intermediate_ca",
        )
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert "certificate" in result
        assert "private_key" in result

    def test_issue_certificate(self):
        """测试签发证书。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        result = self.sdk.ca.issue_certificate(
            "test.example.com",
            cert_type="end_entity",
            issuer="root",
        )
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert "certificate" in result
        assert "private_key" in result
        assert result.get("subject") == "test.example.com"

    def test_verify_certificate(self):
        """测试验证证书。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        issue_result = self.sdk.ca.issue_certificate("test.example.com")
        cert_pem = issue_result["certificate"].encode("utf-8")

        result = self.sdk.ca.verify_certificate(cert_pem)
        assert isinstance(result, dict)
        assert result.get("success") is True

    def test_get_cert_info(self):
        """测试获取证书信息。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        issue_result = self.sdk.ca.issue_certificate("test.example.com")
        cert_pem = issue_result["certificate"].encode("utf-8")

        info = self.sdk.ca.get_cert_info(cert_pem)
        assert isinstance(info, dict)
        assert "serial_number" in info or "subject" in info

    def test_list_certificates(self):
        """测试列出证书。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        self.sdk.ca.issue_certificate("cert1.example.com")
        self.sdk.ca.issue_certificate("cert2.example.com")

        certs = self.sdk.ca.list_certificates()
        assert isinstance(certs, list)
        assert len(certs) >= 2

    def test_revoke_certificate(self):
        """测试吊销证书。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        issue_result = self.sdk.ca.issue_certificate("to_revoke.example.com")
        cert_pem = issue_result["certificate"].encode("utf-8")
        info = self.sdk.ca.get_cert_info(cert_pem)
        serial = info.get("serial_number")

        if serial:
            result = self.sdk.ca.revoke_certificate(serial, reason="key_compromise")
            assert isinstance(result, bool)

    def test_sign_with_cert(self):
        """测试使用证书签名。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        issue_result = self.sdk.ca.issue_certificate("sign.example.com")
        cert_pem = issue_result["certificate"].encode("utf-8")
        key_pem = issue_result["private_key"].encode("utf-8")

        data = b"Test data to sign"
        signature = self.sdk.ca.sign_with_cert(data, cert_pem, key_pem)
        assert isinstance(signature, bytes)
        assert len(signature) > 0

    def test_verify_with_cert(self):
        """测试使用证书验证签名。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        issue_result = self.sdk.ca.issue_certificate("verify.example.com")
        cert_pem = issue_result["certificate"].encode("utf-8")
        key_pem = issue_result["private_key"].encode("utf-8")

        data = b"Test data to verify"
        signature = self.sdk.ca.sign_with_cert(data, cert_pem, key_pem)

        valid = self.sdk.ca.verify_with_cert(data, signature, cert_pem)
        assert valid is True

    def test_verify_with_cert_invalid(self):
        """测试验证无效签名。"""
        self.sdk.ca.init_root_ca("Test Root CA")
        issue_result = self.sdk.ca.issue_certificate("verify2.example.com")
        cert_pem = issue_result["certificate"].encode("utf-8")
        key_pem = issue_result["private_key"].encode("utf-8")

        data = b"Original data"
        signature = self.sdk.ca.sign_with_cert(data, cert_pem, key_pem)

        modified_data = b"Modified data"
        valid = self.sdk.ca.verify_with_cert(modified_data, signature, cert_pem)
        assert valid is False
