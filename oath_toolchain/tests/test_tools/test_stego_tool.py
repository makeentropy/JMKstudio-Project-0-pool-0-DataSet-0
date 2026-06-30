"""隐写工具集主类单元测试。"""
import base64

import pytest

from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.tools.steganography.tool import SteganographyTool
from oath_toolchain.tools.steganography.cert_stego import CertificateSteganography


class TestSteganographyTool:
    """测试SteganographyTool类。"""

    def setup_method(self):
        """每个测试前重置注册表。"""
        ToolRegistry.reset_instance()
        self.tool = SteganographyTool()

    def test_tool_name(self):
        """测试工具名称。"""
        assert self.tool.name == "steganography"

    def test_tool_description(self):
        """测试工具描述。"""
        assert self.tool.description == "多载体隐写工具集"

    def test_tool_version(self):
        """测试工具版本。"""
        assert self.tool.version == "0.1.0"

    def test_tool_category(self):
        """测试工具分类。"""
        assert self.tool.category == "crypto"

    def test_tool_tags(self):
        """测试工具标签。"""
        assert "steganography" in self.tool.tags
        assert "crypto" in self.tool.tags

    def test_tool_registration(self):
        """测试工具注册。"""
        from oath_toolchain.tools.steganography.tool import SteganographyTool as ST
        registry = ToolRegistry()
        registry.register(ST)
        assert registry.has_tool("steganography")

    def test_validate_params_missing_action(self):
        """测试缺少action参数。"""
        from oath_toolchain.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            self.tool.validate_params({})

    def test_validate_params_invalid_action(self):
        """测试无效的action参数。"""
        from oath_toolchain.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            self.tool.validate_params({"action": "invalid"})

    def test_execute_xor_embed(self):
        """测试XOR隐写嵌入操作。"""
        secret = b"Hello, XOR Stego!"
        carrier = b"\x00" * 200
        params = {
            "action": "xor_embed",
            "secret_data": secret,
            "carrier_data": carrier,
        }
        result = self.tool.execute(params)
        assert result["success"] is True
        assert result["action"] == "xor_embed"
        assert "result" in result
        assert result["secret_size"] == len(secret)

    def test_execute_xor_embed_extract_roundtrip(self):
        """测试XOR隐写嵌入和提取往返。"""
        secret = b"Round trip test data"
        carrier = b"A" * 300
        params = {
            "action": "xor_embed",
            "secret_data": secret,
            "carrier_data": carrier,
        }
        embed_result = self.tool.execute(params)
        assert embed_result["success"] is True

        stego_b64 = embed_result["result"]
        stego_data = base64.b64decode(stego_b64)

        extract_params = {
            "action": "xor_extract",
            "stego_data": stego_data,
        }
        extract_result = self.tool.execute(extract_params)
        assert extract_result["success"] is True
        extracted = base64.b64decode(extract_result["result"])
        assert extracted == secret

    def test_execute_xor_embed_with_key(self):
        """测试带密钥的XOR隐写。"""
        secret = b"Encrypted secret"
        carrier = b"B" * 200
        key = b"mysecretkey"
        params = {
            "action": "xor_embed",
            "secret_data": secret,
            "carrier_data": carrier,
            "key": key,
        }
        result = self.tool.execute(params)
        assert result["success"] is True

        stego_b64 = result["result"]
        stego_data = base64.b64decode(stego_b64)

        extract_params = {
            "action": "xor_extract",
            "stego_data": stego_data,
            "key": key,
        }
        extract_result = self.tool.execute(extract_params)
        assert extract_result["success"] is True
        extracted = base64.b64decode(extract_result["result"])
        assert extracted == secret

    def test_execute_cert_embed_extract(self):
        """测试证书隐写嵌入和提取。"""
        cert = CertificateSteganography.generate_test_certificate()
        secret = b"Certificate hidden data"

        params = {
            "action": "cert_embed",
            "cert_pem": cert,
            "secret_data": secret,
        }
        embed_result = self.tool.execute(params)
        assert embed_result["success"] is True

        stego_cert = embed_result["result"].encode("utf-8")

        extract_params = {
            "action": "cert_extract",
            "cert_pem": stego_cert,
        }
        extract_result = self.tool.execute(extract_params)
        assert extract_result["success"] is True
        extracted = base64.b64decode(extract_result["result"])
        assert extracted == secret

    def test_execute_cert_serial_embed_extract(self):
        """测试证书序列号隐写。"""
        cert = CertificateSteganography.generate_test_certificate()
        secret_byte = 0x5A

        params = {
            "action": "cert_serial_embed",
            "cert_pem": cert,
            "secret_byte": secret_byte,
        }
        embed_result = self.tool.execute(params)
        assert embed_result["success"] is True
        assert embed_result["secret_byte"] == secret_byte

        stego_cert = embed_result["result"].encode("utf-8")

        extract_params = {
            "action": "cert_serial_extract",
            "cert_pem": stego_cert,
        }
        extract_result = self.tool.execute(extract_params)
        assert extract_result["success"] is True
        assert extract_result["result"] == secret_byte

    def test_execute_text_unicode_embed_extract(self):
        """测试文本Unicode隐写。"""
        text = "This is a test text with many spaces for hiding data. " * 50
        secret = b"Unicode hidden msg"

        params = {
            "action": "text_unicode_embed",
            "text": text,
            "secret_data": secret,
        }
        embed_result = self.tool.execute(params)
        assert embed_result["success"] is True

        stego_text = embed_result["result"]

        extract_params = {
            "action": "text_unicode_extract",
            "stego_text": stego_text,
        }
        extract_result = self.tool.execute(extract_params)
        assert extract_result["success"] is True
        extracted = base64.b64decode(extract_result["result"])
        assert extracted == secret

    def test_execute_text_case_embed_extract(self):
        """测试文本大小写隐写。"""
        text = "The quick brown fox jumps over the lazy dog. " * 10
        secret = b"Case stego test"

        params = {
            "action": "text_case_embed",
            "text": text,
            "secret_data": secret,
        }
        embed_result = self.tool.execute(params)
        assert embed_result["success"] is True

        stego_text = embed_result["result"]

        extract_params = {
            "action": "text_case_extract",
            "stego_text": stego_text,
        }
        extract_result = self.tool.execute(extract_params)
        assert extract_result["success"] is True
        extracted = base64.b64decode(extract_result["result"])
        assert extracted == secret

    def test_execute_text_whitespace_embed_extract(self):
        """测试文本空格隐写。"""
        lines = ["Line number " + str(i) for i in range(200)]
        text = "\n".join(lines)
        secret = b"Whitespace stego"

        params = {
            "action": "text_whitespace_embed",
            "text": text,
            "secret_data": secret,
        }
        embed_result = self.tool.execute(params)
        assert embed_result["success"] is True

        stego_text = embed_result["result"]

        extract_params = {
            "action": "text_whitespace_extract",
            "stego_text": stego_text,
        }
        extract_result = self.tool.execute(extract_params)
        assert extract_result["success"] is True
        extracted = base64.b64decode(extract_result["result"])
        assert extracted == secret

    def test_execute_analyze(self):
        """测试容量分析操作。"""
        carrier = bytes(range(256)) * 10
        params = {
            "action": "analyze",
            "carrier_data": carrier,
            "carrier_type": "binary",
        }
        result = self.tool.execute(params)
        assert result["success"] is True
        assert result["action"] == "analyze"
        assert "result" in result
        assert result["result"]["total_size"] == len(carrier)

    def test_execute_report(self):
        """测试分析报告操作。"""
        carrier = bytes(range(256)) * 10
        secret = b"Test secret"
        params = {
            "action": "report",
            "carrier_data": carrier,
            "secret_data": secret,
            "method": "xor",
        }
        result = self.tool.execute(params)
        assert result["success"] is True
        assert result["action"] == "report"
        assert "result" in result
        assert "overall_score" in result["result"]

    def test_execute_invalid_action(self):
        """测试无效操作的执行。"""
        params = {"action": "invalid_action"}
        from oath_toolchain.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            self.tool.execute(params)

    def test_execute_xor_extract_with_explicit_length(self):
        """测试指定长度的XOR提取。"""
        secret = b"Fixed length"
        carrier = b"X" * 100
        stego = self.tool._xor_stego.embed(secret, carrier)

        params = {
            "action": "xor_extract",
            "stego_data": stego,
            "with_length": False,
            "secret_length": len(secret),
        }
        result = self.tool.execute(params)
        assert result["success"] is True
        extracted = base64.b64decode(result["result"])
        assert extracted == secret

    def test_execute_xor_extract_missing_length(self):
        """测试缺少长度参数的XOR提取。"""
        from oath_toolchain.core.exceptions import ValidationError
        params = {
            "action": "xor_extract",
            "stego_data": b"test",
            "with_length": False,
        }
        with pytest.raises(ValidationError):
            self.tool.execute(params)

    def test_tool_metadata(self):
        """测试工具元数据。"""
        metadata = self.tool.metadata
        assert metadata["name"] == "steganography"
        assert metadata["description"] == "多载体隐写工具集"
        assert metadata["version"] == "0.1.0"

    def test_tool_repr(self):
        """测试工具字符串表示。"""
        repr_str = repr(self.tool)
        assert "SteganographyTool" in repr_str
        assert "steganography" in repr_str

    def test_tool_str(self):
        """测试工具可读字符串。"""
        str_val = str(self.tool)
        assert "steganography" in str_val
        assert "多载体隐写工具集" in str_val
