"""KARMACA空间字典加密单元测试。"""
import base64

import pytest

from oath_toolchain.core.math.vector import Vector
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.tools.karmaca.space_dict import KarmaSpaceDict
from oath_toolchain.tools.karmaca.encryption import KarmacaEncryption


class TestKarmacaEncryption:
    """测试KarmacaEncryption类。"""

    def setup_method(self):
        """每个测试前重置注册表。"""
        ToolRegistry.reset_instance()
        self.encryption = KarmacaEncryption()

    def test_tool_name(self):
        """测试工具名称。"""
        assert self.encryption.name == "karmaca_encryption"

    def test_tool_description(self):
        """测试工具描述。"""
        assert self.encryption.description == "KARMACA空间字典加密工具"

    def test_tool_registration(self):
        """测试工具注册。"""
        from oath_toolchain.tools.karmaca.encryption import KarmacaEncryption as KE

        registry = ToolRegistry()
        registry.register(KE)
        assert registry.has_tool("karmaca_encryption")

    def test_encrypt_decrypt(self):
        """测试加密和解密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(10):
            sd.insert(
                Vector([float(i), float(i * 2), float(i * 3)]),
                bytes([i] * 32),
            )

        plaintext = b"Hello, KARMACA!"
        coordinate = Vector([5.0, 10.0, 15.0])

        ciphertext = self.encryption.encrypt(plaintext, coordinate, sd)
        assert isinstance(ciphertext, bytes)
        assert len(ciphertext) > len(plaintext)

        decrypted = self.encryption.decrypt(ciphertext, coordinate, sd)
        assert decrypted == plaintext

    def test_encrypt_decrypt_no_interpolation(self):
        """测试不使用插值的加密解密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        plaintext = b"Test message"
        coordinate = Vector([1.0, 2.0, 3.0])

        ciphertext = self.encryption.encrypt(
            plaintext, coordinate, sd, use_interpolation=False
        )
        decrypted = self.encryption.decrypt(
            ciphertext, coordinate, sd, use_interpolation=False
        )
        assert decrypted == plaintext

    def test_encrypt_invalid_data_type(self):
        """测试无效数据类型的加密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        with pytest.raises(ValueError):
            self.encryption.encrypt(
                "not bytes", Vector([1.0, 2.0, 3.0]), sd
            )

    def test_encrypt_dimension_mismatch(self):
        """测试维度不匹配的加密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        with pytest.raises(ValueError):
            self.encryption.encrypt(
                b"data", Vector([1.0, 2.0]), sd
            )

    def test_encrypt_empty_dict(self):
        """测试空字典加密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        with pytest.raises(ValueError):
            self.encryption.encrypt(
                b"data", Vector([1.0, 2.0, 3.0]), sd
            )

    def test_decrypt_invalid_ciphertext_length(self):
        """测试密文长度不足的解密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        with pytest.raises(ValueError):
            self.encryption.decrypt(
                b"short", Vector([1.0, 2.0, 3.0]), sd
            )

    def test_decrypt_wrong_coordinate(self):
        """测试使用错误坐标解密失败。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)
        sd.insert(Vector([10.0, 20.0, 30.0]), b"\xff" * 32)

        plaintext = b"Secret data"
        correct_coord = Vector([1.0, 2.0, 3.0])
        wrong_coord = Vector([10.0, 20.0, 30.0])

        ciphertext = self.encryption.encrypt(
            plaintext, correct_coord, sd, use_interpolation=False
        )

        from oath_toolchain.core.exceptions import EncryptionError

        with pytest.raises(EncryptionError):
            self.encryption.decrypt(
                ciphertext, wrong_coord, sd, use_interpolation=False
            )

    def test_decrypt_invalid_data_type(self):
        """测试无效数据类型的解密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        with pytest.raises(ValueError):
            self.encryption.decrypt(
                "not bytes", Vector([1.0, 2.0, 3.0]), sd
            )

    def test_execute_encrypt(self):
        """测试execute方法加密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        params = {
            "action": "encrypt",
            "data": base64.b64encode(b"test data").decode("utf-8"),
            "coordinate": [1.0, 2.0, 3.0],
            "space_dict": sd.to_dict(),
        }

        result = self.encryption.execute(params)
        assert result["success"] is True
        assert "result" in result
        assert isinstance(result["result"], str)

    def test_execute_decrypt(self):
        """测试execute方法解密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        plaintext = b"test data"
        coord = Vector([1.0, 2.0, 3.0])
        ciphertext = self.encryption.encrypt(plaintext, coord, sd, use_interpolation=False)

        params = {
            "action": "decrypt",
            "data": base64.b64encode(ciphertext).decode("utf-8"),
            "coordinate": [1.0, 2.0, 3.0],
            "space_dict": sd.to_dict(),
            "use_interpolation": False,
        }

        result = self.encryption.execute(params)
        assert result["success"] is True
        decrypted = base64.b64decode(result["result"])
        assert decrypted == plaintext

    def test_execute_invalid_action(self):
        """测试无效操作的execute。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        params = {
            "action": "invalid",
            "data": base64.b64encode(b"data").decode("utf-8"),
            "coordinate": [1.0, 2.0, 3.0],
            "space_dict": sd.to_dict(),
        }

        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.encryption.execute(params)

    def test_execute_missing_params(self):
        """测试缺少参数的execute。"""
        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.encryption.execute({"action": "encrypt"})

    def test_validate_params(self):
        """测试参数验证。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        params = {
            "action": "encrypt",
            "data": base64.b64encode(b"data").decode("utf-8"),
            "coordinate": [1.0, 2.0, 3.0],
            "space_dict": sd.to_dict(),
        }

        assert self.encryption.validate_params(params) is True

    def test_validate_params_invalid_data_type(self):
        """测试无效数据类型的参数验证。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        params = {
            "action": "encrypt",
            "data": 12345,
            "coordinate": [1.0, 2.0, 3.0],
            "space_dict": sd.to_dict(),
        }

        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.encryption.validate_params(params)

    def test_validate_params_invalid_coordinate_type(self):
        """测试无效坐标类型的参数验证。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        params = {
            "action": "encrypt",
            "data": "base64data",
            "coordinate": "not a list",
            "space_dict": sd.to_dict(),
        }

        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.encryption.validate_params(params)

    def test_validate_params_invalid_space_dict_type(self):
        """测试无效空间字典类型的参数验证。"""
        params = {
            "action": "encrypt",
            "data": "base64data",
            "coordinate": [1.0, 2.0, 3.0],
            "space_dict": "not a dict",
        }

        from oath_toolchain.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.encryption.validate_params(params)

    def test_large_data_encryption(self):
        """测试大数据加密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        for i in range(10):
            sd.insert(
                Vector([float(i), float(i), float(i)]),
                bytes([i] * 32),
            )

        plaintext = b"X" * 10000
        coordinate = Vector([5.0, 5.0, 5.0])

        ciphertext = self.encryption.encrypt(plaintext, coordinate, sd)
        decrypted = self.encryption.decrypt(ciphertext, coordinate, sd)
        assert decrypted == plaintext

    def test_empty_data_encryption(self):
        """测试空数据加密。"""
        sd = KarmaSpaceDict(dimensions=3, key_size=32)
        sd.insert(Vector([1.0, 2.0, 3.0]), b"\x00" * 32)

        plaintext = b""
        coordinate = Vector([1.0, 2.0, 3.0])

        ciphertext = self.encryption.encrypt(plaintext, coordinate, sd, use_interpolation=False)
        decrypted = self.encryption.decrypt(ciphertext, coordinate, sd, use_interpolation=False)
        assert decrypted == plaintext
