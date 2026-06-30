"""KARMACA维度空间隐写单元测试。"""
import base64

import pytest

from oath_toolchain.core.math.vector import Vector
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.tools.karmaca.space_dict import KarmaSpaceDict
from oath_toolchain.tools.karmaca.steganography import DimensionSteganography


class TestDimensionSteganography:
    """测试DimensionSteganography类。"""

    def setup_method(self):
        """每个测试前重置注册表。"""
        ToolRegistry.reset_instance()
        self.stego = DimensionSteganography(precision=6)

    def test_tool_name(self):
        """测试工具名称。"""
        assert self.stego.name == "dimension_steganography"

    def test_tool_description(self):
        """测试工具描述。"""
        assert self.stego.description == "维度空间隐写工具"

    def test_tool_registration(self):
        """测试工具注册。"""
        from oath_toolchain.tools.karmaca.steganography import DimensionSteganography as DS

        registry = ToolRegistry()
        registry.register(DS)
        assert registry.has_tool("dimension_steganography")

    def test_precision_property(self):
        """测试precision属性。"""
        assert self.stego.precision == 6

    def test_embed_and_extract(self):
        """测试嵌入和提取数据。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(100):
            sd.insert(
                Vector([float(i), float(i * 2), float(i * 3)]),
                bytes([i % 256] * 32),
            )

        secret = b"Hello, Steganography!"
        modified_sd = self.stego.embed(secret, sd)
        assert modified_sd.size == sd.size

        extracted = self.stego.extract(modified_sd)
        assert extracted == secret

    def test_embed_empty_data(self):
        """测试嵌入空数据。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(50):
            sd.insert(
                Vector([float(i), float(i), float(i)]),
                bytes([i] * 32),
            )

        secret = b""
        modified_sd = self.stego.embed(secret, sd)
        extracted = self.stego.extract(modified_sd)
        assert extracted == secret

    def test_embed_data_too_long(self):
        """测试嵌入过长数据。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        with pytest.raises(ValueError):
            self.stego.embed(b"A" * 1000, sd)

    def test_embed_invalid_data_type(self):
        """测试无效数据类型的嵌入。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        with pytest.raises(ValueError):
            self.stego.embed("not bytes", sd)

    def test_embed_empty_dict(self):
        """测试空字典嵌入。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            self.stego.embed(b"data", sd)

    def test_extract_empty_dict(self):
        """测试空字典提取。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            self.stego.extract(sd)

    def test_extract_with_explicit_length(self):
        """测试指定长度提取。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(100):
            sd.insert(
                Vector([float(i), float(i), float(i)]),
                bytes([i % 256] * 32),
            )

        secret = b"Test message"
        modified_sd = self.stego.embed(secret, sd)
        extracted = self.stego.extract(modified_sd, data_length=len(secret))
        assert extracted == secret

    def test_get_capacity(self):
        """测试获取容量。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(10):
            sd.insert(
                Vector([float(i), float(i), float(i)]),
                bytes([i] * 32),
            )

        capacity = self.stego.get_capacity(sd)
        assert capacity > 0
        assert isinstance(capacity, int)

    def test_execute_embed(self):
        """测试execute方法嵌入。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(100):
            sd.insert(
                Vector([float(i), float(i), float(i)]),
                bytes([i % 256] * 32),
            )

        secret = b"Secret data"
        params = {
            "action": "embed",
            "secret_data": base64.b64encode(secret).decode("utf-8"),
            "space_dict": sd.to_dict(),
        }

        result = self.stego.execute(params)
        assert result["success"] is True
        assert "result" in result
        assert isinstance(result["result"], dict)

    def test_execute_extract(self):
        """测试execute方法提取。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(100):
            sd.insert(
                Vector([float(i), float(i), float(i)]),
                bytes([i % 256] * 32),
            )

        secret = b"Secret data"
        modified_sd = self.stego.embed(secret, sd)

        params = {
            "action": "extract",
            "space_dict": modified_sd.to_dict(),
        }

        result = self.stego.execute(params)
        assert result["success"] is True
        extracted = base64.b64decode(result["result"])
        assert extracted == secret

    def test_execute_invalid_action(self):
        """测试无效操作的execute。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        params = {
            "action": "invalid",
            "space_dict": sd.to_dict(),
        }

        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.stego.execute(params)

    def test_execute_missing_params(self):
        """测试缺少参数的execute。"""
        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.stego.execute({"action": "embed"})

    def test_execute_embed_missing_secret_data(self):
        """测试嵌入操作缺少secret_data。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.stego.execute({"action": "embed", "space_dict": sd.to_dict()})

    def test_validate_params(self):
        """测试参数验证。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        params = {
            "action": "embed",
            "secret_data": "base64data",
            "space_dict": sd.to_dict(),
        }

        assert self.stego.validate_params(params) is True

    def test_validate_params_invalid_space_dict(self):
        """测试无效空间字典的参数验证。"""
        params = {
            "action": "embed",
            "secret_data": "base64data",
            "space_dict": "not a dict",
        }

        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.stego.validate_params(params)

    def test_coordinates_preserved_after_embed(self):
        """测试嵌入后坐标基本保持不变（只有微小变化）。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        original_points = []
        for i in range(100):
            p = Vector([float(i), float(i * 2), float(i * 3)])
            original_points.append(p)
            sd.insert(p, bytes([i % 256] * 32))

        secret = b"Test data"
        modified_sd = self.stego.embed(secret, sd)

        for i in range(100):
            original = original_points[i]
            modified = modified_sd._points[i]
            for d in range(3):
                diff = abs(original[d] - modified[d])
                assert diff < 10 ** (-self.stego.precision + 1)

    def test_keys_preserved_after_embed(self):
        """测试嵌入后密钥保持不变。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        original_keys = []
        for i in range(100):
            key = bytes([i % 256] * 32)
            original_keys.append(key)
            sd.insert(Vector([float(i), float(i), float(i)]), key)

        secret = b"Test data"
        modified_sd = self.stego.embed(secret, sd)

        for i in range(100):
            assert modified_sd._keys[i] == original_keys[i]
