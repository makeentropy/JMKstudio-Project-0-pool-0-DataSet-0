"""证书隐写单元测试。"""
import pytest

from oath_toolchain.tools.steganography.cert_stego import CertificateSteganography


class TestCertificateSteganography:
    """测试CertificateSteganography类。"""

    def setup_method(self):
        """每个测试前初始化。"""
        self.stego = CertificateSteganography()
        self.test_cert = CertificateSteganography.generate_test_certificate()

    def test_init(self):
        """测试初始化。"""
        assert self.stego.DEFAULT_OID == "1.3.6.1.4.1.99999.1"

    def test_generate_test_certificate(self):
        """测试生成测试证书。"""
        cert_pem = CertificateSteganography.generate_test_certificate()
        assert b"BEGIN CERTIFICATE" in cert_pem
        assert b"END CERTIFICATE" in cert_pem

    def test_embed_in_extension(self):
        """测试在扩展字段嵌入数据。"""
        secret = b"Hello, Certificate Steganography!"
        stego_cert = self.stego.embed_in_extension(self.test_cert, secret)
        assert b"BEGIN CERTIFICATE" in stego_cert
        assert b"END CERTIFICATE" in stego_cert

    def test_extract_from_extension(self):
        """测试从扩展字段提取数据。"""
        secret = b"Secret data in extension"
        stego_cert = self.stego.embed_in_extension(self.test_cert, secret)
        extracted = self.stego.extract_from_extension(stego_cert)
        assert extracted == secret

    def test_embed_and_extract_custom_oid(self):
        """测试自定义OID的嵌入和提取。"""
        secret = b"Custom OID data"
        custom_oid = "1.3.6.1.4.1.12345.1"
        stego_cert = self.stego.embed_in_extension(self.test_cert, secret, custom_oid)
        extracted = self.stego.extract_from_extension(stego_cert, custom_oid)
        assert extracted == secret

    def test_extract_nonexistent_extension(self):
        """测试提取不存在的扩展。"""
        with pytest.raises(ValueError):
            self.stego.extract_from_extension(self.test_cert, "1.2.3.4.5.6.7")

    def test_embed_in_serial(self):
        """测试在序列号中嵌入数据。"""
        secret_byte = 0xAB
        stego_cert = self.stego.embed_in_serial(self.test_cert, secret_byte)
        assert b"BEGIN CERTIFICATE" in stego_cert

    def test_extract_from_serial(self):
        """测试从序列号提取数据。"""
        secret_byte = 0x42
        stego_cert = self.stego.embed_in_serial(self.test_cert, secret_byte)
        extracted = self.stego.extract_from_serial(stego_cert)
        assert extracted == secret_byte

    def test_extract_from_serial_zero(self):
        """测试提取值为0的情况。"""
        secret_byte = 0x00
        stego_cert = self.stego.embed_in_serial(self.test_cert, secret_byte)
        extracted = self.stego.extract_from_serial(stego_cert)
        assert extracted == 0

    def test_extract_from_serial_max(self):
        """测试提取值为255的情况。"""
        secret_byte = 0xFF
        stego_cert = self.stego.embed_in_serial(self.test_cert, secret_byte)
        extracted = self.stego.extract_from_serial(stego_cert)
        assert extracted == 255

    def test_embed_in_serial_invalid_byte_low(self):
        """测试嵌入无效字节值（小于0）。"""
        with pytest.raises(ValueError):
            self.stego.embed_in_serial(self.test_cert, -1)

    def test_embed_in_serial_invalid_byte_high(self):
        """测试嵌入无效字节值（大于255）。"""
        with pytest.raises(ValueError):
            self.stego.embed_in_serial(self.test_cert, 256)

    def test_embed_in_serial_invalid_type(self):
        """测试嵌入无效类型。"""
        with pytest.raises(ValueError):
            self.stego.embed_in_serial(self.test_cert, "not int")

    def test_get_capacity(self):
        """测试获取容量。"""
        capacity = self.stego.get_capacity(self.test_cert)
        assert "extension_bytes" in capacity
        assert "serial_bytes" in capacity
        assert "total_estimate" in capacity
        assert capacity["serial_bytes"] == 1
        assert capacity["extension_bytes"] == -1

    def test_embed_invalid_cert_format(self):
        """测试无效证书格式。"""
        with pytest.raises(ValueError):
            self.stego.embed_in_extension(b"not a cert", b"data")

    def test_extract_invalid_cert_format(self):
        """测试提取无效证书格式。"""
        with pytest.raises(ValueError):
            self.stego.extract_from_extension(b"not a cert")

    def test_embed_invalid_secret_type(self):
        """测试无效秘密数据类型。"""
        with pytest.raises(TypeError):
            self.stego.embed_in_extension(self.test_cert, "not bytes")

    def test_embed_invalid_cert_type(self):
        """测试无效证书类型。"""
        with pytest.raises(TypeError):
            self.stego.embed_in_extension("not bytes", b"data")

    def test_extract_invalid_cert_type(self):
        """测试提取无效证书类型。"""
        with pytest.raises(TypeError):
            self.stego.extract_from_extension("not bytes")

    def test_get_capacity_invalid_type(self):
        """测试容量分析无效类型。"""
        with pytest.raises(TypeError):
            self.stego.get_capacity("not bytes")

    def test_embed_empty_secret(self):
        """测试嵌入空数据。"""
        secret = b""
        stego_cert = self.stego.embed_in_extension(self.test_cert, secret)
        extracted = self.stego.extract_from_extension(stego_cert)
        assert extracted == secret
