"""CLI加密解密测试模块。

测试加密和解密命令。
"""
import os
import tempfile

import pytest
from click.testing import CliRunner

from oath_toolchain.cli.main import cli


@pytest.fixture
def runner():
    """创建CliRunner实例。"""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """创建临时目录。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestCLIEncrypt:
    """加密命令测试类。"""

    def test_encrypt_aes(self, runner, temp_dir):
        """测试AES加密。"""
        input_file = os.path.join(temp_dir, "input.txt")
        output_file = os.path.join(temp_dir, "output.enc")
        key_file = os.path.join(temp_dir, "key.bin")

        with open(input_file, "w") as f:
            f.write("Hello, World!")

        from oath_toolchain.core.crypto.primitives import AESCipher
        key = AESCipher.generate_key(256)
        with open(key_file, "wb") as f:
            f.write(key)

        result = runner.invoke(cli, [
            "encrypt", "aes",
            "-i", input_file,
            "-o", output_file,
            "-k", key_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) > 0

    def test_decrypt_aes(self, runner, temp_dir):
        """测试AES解密往返。"""
        input_file = os.path.join(temp_dir, "input.txt")
        encrypted_file = os.path.join(temp_dir, "output.enc")
        decrypted_file = os.path.join(temp_dir, "decrypted.txt")
        key_file = os.path.join(temp_dir, "key.bin")

        original_data = b"Hello, World! Test AES encryption."
        with open(input_file, "wb") as f:
            f.write(original_data)

        from oath_toolchain.core.crypto.primitives import AESCipher
        key = AESCipher.generate_key(256)
        with open(key_file, "wb") as f:
            f.write(key)

        result = runner.invoke(cli, [
            "encrypt", "aes",
            "-i", input_file,
            "-o", encrypted_file,
            "-k", key_file,
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "decrypt", "aes",
            "-i", encrypted_file,
            "-o", decrypted_file,
            "-k", key_file,
        ])

        assert result.exit_code == 0
        with open(decrypted_file, "rb") as f:
            decrypted_data = f.read()
        assert decrypted_data == original_data

    def test_encrypt_rsa(self, runner, temp_dir):
        """测试RSA加密。"""
        input_file = os.path.join(temp_dir, "input.txt")
        output_file = os.path.join(temp_dir, "output.enc")
        private_key_file = os.path.join(temp_dir, "private.key")
        public_key_file = os.path.join(temp_dir, "public.key")

        small_data = b"Short msg"
        with open(input_file, "wb") as f:
            f.write(small_data)

        from oath_toolchain.core.crypto.primitives import RSACipher
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        with open(private_key_file, "wb") as f:
            f.write(RSACipher.serialize_private_key(private_key))
        with open(public_key_file, "wb") as f:
            f.write(RSACipher.serialize_public_key(public_key))

        result = runner.invoke(cli, [
            "encrypt", "rsa",
            "-i", input_file,
            "-o", output_file,
            "-k", public_key_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_decrypt_rsa(self, runner, temp_dir):
        """测试RSA解密往返。"""
        input_file = os.path.join(temp_dir, "input.txt")
        encrypted_file = os.path.join(temp_dir, "output.enc")
        decrypted_file = os.path.join(temp_dir, "decrypted.txt")
        private_key_file = os.path.join(temp_dir, "private.key")
        public_key_file = os.path.join(temp_dir, "public.key")

        original_data = b"Test RSA"
        with open(input_file, "wb") as f:
            f.write(original_data)

        from oath_toolchain.core.crypto.primitives import RSACipher
        private_key, public_key = RSACipher.generate_keypair(key_size=2048)
        with open(private_key_file, "wb") as f:
            f.write(RSACipher.serialize_private_key(private_key))
        with open(public_key_file, "wb") as f:
            f.write(RSACipher.serialize_public_key(public_key))

        result = runner.invoke(cli, [
            "encrypt", "rsa",
            "-i", input_file,
            "-o", encrypted_file,
            "-k", public_key_file,
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "decrypt", "rsa",
            "-i", encrypted_file,
            "-o", decrypted_file,
            "-k", private_key_file,
        ])

        assert result.exit_code == 0
        with open(decrypted_file, "rb") as f:
            decrypted_data = f.read()
        assert decrypted_data == original_data

    def test_encrypt_geometric(self, runner, temp_dir):
        """测试几何加密。"""
        input_file = os.path.join(temp_dir, "input.txt")
        output_file = os.path.join(temp_dir, "output.enc")

        with open(input_file, "w") as f:
            f.write("Test geometric encryption")

        result = runner.invoke(cli, [
            "encrypt", "geometric",
            "-i", input_file,
            "-o", output_file,
            "-k", "test_secret_key",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_decrypt_geometric(self, runner, temp_dir):
        """测试几何解密往返。"""
        input_file = os.path.join(temp_dir, "input.txt")
        encrypted_file = os.path.join(temp_dir, "output.enc")
        decrypted_file = os.path.join(temp_dir, "decrypted.txt")

        original_data = b"Test geometric encryption round trip"
        with open(input_file, "wb") as f:
            f.write(original_data)

        key = "my_secret_key"

        result = runner.invoke(cli, [
            "encrypt", "geometric",
            "-i", input_file,
            "-o", encrypted_file,
            "-k", key,
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "decrypt", "geometric",
            "-i", encrypted_file,
            "-o", decrypted_file,
            "-k", key,
        ])

        assert result.exit_code == 0
        with open(decrypted_file, "rb") as f:
            decrypted_data = f.read()
        assert decrypted_data == original_data

    def test_encrypt_full(self, runner, temp_dir):
        """测试完整加密管道。"""
        input_file = os.path.join(temp_dir, "input.txt")
        output_file = os.path.join(temp_dir, "output.enc")

        with open(input_file, "w") as f:
            f.write("Full encryption pipeline test")

        result = runner.invoke(cli, [
            "encrypt", "full",
            "-i", input_file,
            "-o", output_file,
            "-k", "full_encryption_key",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_decrypt_full(self, runner, temp_dir):
        """测试完整解密管道往返。"""
        input_file = os.path.join(temp_dir, "input.txt")
        encrypted_file = os.path.join(temp_dir, "output.enc")
        decrypted_file = os.path.join(temp_dir, "decrypted.txt")

        original_data = b"Full encryption pipeline round trip test"
        with open(input_file, "wb") as f:
            f.write(original_data)

        key = "full_pipeline_key"

        result = runner.invoke(cli, [
            "encrypt", "full",
            "-i", input_file,
            "-o", encrypted_file,
            "-k", key,
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "decrypt", "full",
            "-i", encrypted_file,
            "-o", decrypted_file,
            "-k", key,
        ])

        assert result.exit_code == 0
        with open(decrypted_file, "rb") as f:
            decrypted_data = f.read()
        assert decrypted_data == original_data

    def test_encrypt_missing_input(self, runner, temp_dir):
        """测试缺少输入文件。"""
        key_file = os.path.join(temp_dir, "key.bin")
        output_file = os.path.join(temp_dir, "output.enc")

        result = runner.invoke(cli, [
            "encrypt", "aes",
            "-i", "/nonexistent/file.txt",
            "-o", output_file,
            "-k", key_file,
        ])

        assert result.exit_code != 0

    def test_encrypt_json_output(self, runner, temp_dir):
        """测试JSON格式输出。"""
        input_file = os.path.join(temp_dir, "input.txt")
        output_file = os.path.join(temp_dir, "output.enc")
        key_file = os.path.join(temp_dir, "key.bin")

        with open(input_file, "w") as f:
            f.write("Test")

        from oath_toolchain.core.crypto.primitives import AESCipher
        key = AESCipher.generate_key(256)
        with open(key_file, "wb") as f:
            f.write(key)

        result = runner.invoke(cli, [
            "-o", "json",
            "encrypt", "aes",
            "-i", input_file,
            "-o", output_file,
            "-k", key_file,
        ])

        assert result.exit_code == 0
        import json
        output_data = json.loads(result.output)
        assert "success" in output_data

    def test_encrypt_karmaca(self, runner, temp_dir):
        """测试KARMACA加密。"""
        input_file = os.path.join(temp_dir, "input.txt")
        output_file = os.path.join(temp_dir, "output.enc")
        key_file = os.path.join(temp_dir, "space_dict.json")

        with open(input_file, "w") as f:
            f.write("Test KARMACA encryption")

        result = runner.invoke(cli, [
            "keygen", "karmaca",
            "-o", key_file,
            "-d", "3",
            "-s", "50",
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "encrypt", "karmaca",
            "-i", input_file,
            "-o", output_file,
            "-k", key_file,
            "-c", "1.0,2.0,3.0",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_decrypt_karmaca(self, runner, temp_dir):
        """测试KARMACA解密往返。"""
        input_file = os.path.join(temp_dir, "input.txt")
        encrypted_file = os.path.join(temp_dir, "output.enc")
        decrypted_file = os.path.join(temp_dir, "decrypted.txt")
        key_file = os.path.join(temp_dir, "space_dict.json")

        original_data = b"Test KARMACA encryption round trip"
        with open(input_file, "wb") as f:
            f.write(original_data)

        result = runner.invoke(cli, [
            "keygen", "karmaca",
            "-o", key_file,
            "-d", "3",
            "-s", "50",
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "encrypt", "karmaca",
            "-i", input_file,
            "-o", encrypted_file,
            "-k", key_file,
            "-c", "1.0,2.0,3.0",
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "decrypt", "karmaca",
            "-i", encrypted_file,
            "-o", decrypted_file,
            "-k", key_file,
            "-c", "1.0,2.0,3.0",
        ])

        assert result.exit_code == 0
        with open(decrypted_file, "rb") as f:
            decrypted_data = f.read()
        assert decrypted_data == original_data

    def test_encrypt_help(self, runner):
        """测试encrypt帮助信息。"""
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert result.exit_code == 0
        assert "加密" in result.output or "encrypt" in result.output.lower()

    def test_decrypt_help(self, runner):
        """测试decrypt帮助信息。"""
        result = runner.invoke(cli, ["decrypt", "--help"])
        assert result.exit_code == 0
        assert "解密" in result.output or "decrypt" in result.output.lower()

    def test_encrypt_aes_help(self, runner):
        """测试encrypt aes帮助信息。"""
        result = runner.invoke(cli, ["encrypt", "aes", "--help"])
        assert result.exit_code == 0

    def test_decrypt_aes_help(self, runner):
        """测试decrypt aes帮助信息。"""
        result = runner.invoke(cli, ["decrypt", "aes", "--help"])
        assert result.exit_code == 0

    def test_encrypt_rsa_help(self, runner):
        """测试encrypt rsa帮助信息。"""
        result = runner.invoke(cli, ["encrypt", "rsa", "--help"])
        assert result.exit_code == 0

    def test_decrypt_rsa_help(self, runner):
        """测试decrypt rsa帮助信息。"""
        result = runner.invoke(cli, ["decrypt", "rsa", "--help"])
        assert result.exit_code == 0

    def test_encrypt_karmaca_help(self, runner):
        """测试encrypt karmaca帮助信息。"""
        result = runner.invoke(cli, ["encrypt", "karmaca", "--help"])
        assert result.exit_code == 0

    def test_decrypt_karmaca_help(self, runner):
        """测试decrypt karmaca帮助信息。"""
        result = runner.invoke(cli, ["decrypt", "karmaca", "--help"])
        assert result.exit_code == 0

    def test_encrypt_geometric_help(self, runner):
        """测试encrypt geometric帮助信息。"""
        result = runner.invoke(cli, ["encrypt", "geometric", "--help"])
        assert result.exit_code == 0

    def test_decrypt_geometric_help(self, runner):
        """测试decrypt geometric帮助信息。"""
        result = runner.invoke(cli, ["decrypt", "geometric", "--help"])
        assert result.exit_code == 0

    def test_encrypt_full_help(self, runner):
        """测试encrypt full帮助信息。"""
        result = runner.invoke(cli, ["encrypt", "full", "--help"])
        assert result.exit_code == 0

    def test_decrypt_full_help(self, runner):
        """测试decrypt full帮助信息。"""
        result = runner.invoke(cli, ["decrypt", "full", "--help"])
        assert result.exit_code == 0

    def test_encrypt_yaml_output(self, runner, temp_dir):
        """测试YAML格式输出。"""
        input_file = os.path.join(temp_dir, "input.txt")
        output_file = os.path.join(temp_dir, "output.enc")
        key_file = os.path.join(temp_dir, "key.bin")

        with open(input_file, "w") as f:
            f.write("Test")

        from oath_toolchain.core.crypto.primitives import AESCipher
        key = AESCipher.generate_key(256)
        with open(key_file, "wb") as f:
            f.write(key)

        result = runner.invoke(cli, [
            "-o", "yaml",
            "encrypt", "aes",
            "-i", input_file,
            "-o", output_file,
            "-k", key_file,
        ])

        assert result.exit_code == 0
        assert "success" in result.output
