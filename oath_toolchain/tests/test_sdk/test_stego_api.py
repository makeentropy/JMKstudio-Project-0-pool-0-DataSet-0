"""隐写API单元测试。"""
import pytest

from oath_toolchain.sdk import OathSDK
from oath_toolchain.core.registry import ToolRegistry


class TestStegoAPI:
    """测试StegoAPI类。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.sdk = OathSDK()
        self.secret_data = b"Secret message for steganography!"
        self.test_text = "This is a test text for steganography. " * 40
        self.test_text_multiline = "\n".join([
            f"Line {i}: This is a test line with enough content."
            for i in range(200)
        ])

    def test_embed_extract_xor(self):
        """测试XOR隐写的嵌入和提取。"""
        carrier = b"A" * 1000
        stego = self.sdk.stego.embed_xor(self.secret_data, carrier)
        assert isinstance(stego, bytes)
        assert len(stego) == len(carrier)

        extracted = self.sdk.stego.extract_xor(stego)
        assert extracted == self.secret_data

    def test_embed_xor_with_key(self):
        """测试带密钥的XOR隐写。"""
        carrier = b"B" * 1000
        key = b"test_key_12345"
        stego = self.sdk.stego.embed_xor(self.secret_data, carrier, key)
        assert isinstance(stego, bytes)

        extracted = self.sdk.stego.extract_xor(stego, key=key)
        assert extracted == self.secret_data

    def test_embed_text_unicode(self):
        """测试Unicode文本隐写。"""
        secret = b"Hello Unicode!"
        stego_text = self.sdk.stego.embed_text_unicode(secret, self.test_text)
        assert isinstance(stego_text, str)
        assert len(stego_text) >= len(self.test_text)

    def test_extract_text_unicode(self):
        """测试提取Unicode文本隐写。"""
        secret = b"Secret in Unicode"
        stego_text = self.sdk.stego.embed_text_unicode(secret, self.test_text)
        extracted = self.sdk.stego.extract_text_unicode(stego_text)
        assert extracted == secret

    def test_embed_text_whitespace(self):
        """测试空格文本隐写。"""
        secret = b"Whitespace stego"
        stego_text = self.sdk.stego.embed_text_whitespace(secret, self.test_text_multiline)
        assert isinstance(stego_text, str)

    def test_extract_text_whitespace(self):
        """测试提取空格文本隐写。"""
        secret = b"Hidden in spaces"
        stego_text = self.sdk.stego.embed_text_whitespace(secret, self.test_text_multiline)
        extracted = self.sdk.stego.extract_text_whitespace(stego_text)
        assert extracted == secret

    def test_embed_in_cert(self):
        """测试证书隐写嵌入。"""
        self.sdk.ca.init_root_ca("Test CA for Stego")
        result = self.sdk.ca.issue_certificate("stego.example.com")
        cert_pem = result["certificate"].encode("utf-8")

        secret = b"Secret in certificate"
        stego_cert = self.sdk.stego.embed_in_cert(secret, cert_pem)
        assert isinstance(stego_cert, bytes)
        assert b"-----BEGIN CERTIFICATE-----" in stego_cert

    def test_extract_from_cert(self):
        """测试从证书提取隐写数据。"""
        self.sdk.ca.init_root_ca("Test CA for Stego Extract")
        result = self.sdk.ca.issue_certificate("stego2.example.com")
        cert_pem = result["certificate"].encode("utf-8")

        secret = b"Certificate stego test"
        stego_cert = self.sdk.stego.embed_in_cert(secret, cert_pem)
        extracted = self.sdk.stego.extract_from_cert(stego_cert)
        assert extracted == secret

    def test_analyze_carrier(self):
        """测试载体分析。"""
        carrier = b"X" * 1024
        result = self.sdk.stego.analyze_carrier(carrier, "binary")
        assert isinstance(result, dict)

    def test_estimate_security(self):
        """测试隐写安全性评估。"""
        original = b"O" * 1000
        secret = b"test"
        stego = self.sdk.stego.embed_xor(secret, original)
        result = self.sdk.stego.estimate_security(original, stego)
        assert isinstance(result, dict)
