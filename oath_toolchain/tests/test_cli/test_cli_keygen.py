"""CLI密钥生成测试模块。

测试密钥生成命令。
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


class TestCLIKeygen:
    """密钥生成命令测试类。"""

    def test_keygen_aes(self, runner, temp_dir):
        """测试AES密钥生成。"""
        output_file = os.path.join(temp_dir, "aes_key.bin")

        result = runner.invoke(cli, [
            "keygen", "aes",
            "-o", output_file,
            "--bits", "256",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) == 32

    def test_keygen_aes_128(self, runner, temp_dir):
        """测试128位AES密钥生成。"""
        output_file = os.path.join(temp_dir, "aes_128_key.bin")

        result = runner.invoke(cli, [
            "keygen", "aes",
            "-o", output_file,
            "--bits", "128",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) == 16

    def test_keygen_rsa(self, runner, temp_dir):
        """测试RSA密钥对生成。"""
        private_key_file = os.path.join(temp_dir, "rsa_private.key")
        public_key_file = os.path.join(temp_dir, "rsa_public.key")

        result = runner.invoke(cli, [
            "keygen", "rsa",
            "-o", private_key_file,
            "--pubout", public_key_file,
            "--bits", "2048",
        ])

        assert result.exit_code == 0
        assert os.path.exists(private_key_file)
        assert os.path.exists(public_key_file)

        with open(private_key_file, "r") as f:
            content = f.read()
            assert "PRIVATE KEY" in content

        with open(public_key_file, "r") as f:
            content = f.read()
            assert "PUBLIC KEY" in content

    def test_keygen_nlp(self, runner, temp_dir):
        """测试NLP密钥生成。"""
        output_file = os.path.join(temp_dir, "nlp_key.bin")
        text = "这是一段用于生成密钥的测试文本。"

        result = runner.invoke(cli, [
            "keygen", "nlp",
            "-o", output_file,
            "-t", text,
            "--mode", "hybrid",
            "--bits", "256",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) == 32

    def test_keygen_nlp_semantic(self, runner, temp_dir):
        """测试语义模式NLP密钥生成。"""
        output_file = os.path.join(temp_dir, "nlp_semantic_key.bin")
        text = "Semantic key generation test text."

        result = runner.invoke(cli, [
            "keygen", "nlp",
            "-o", output_file,
            "-t", text,
            "--mode", "semantic",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_keygen_nlp_entropy(self, runner, temp_dir):
        """测试熵模式NLP密钥生成。"""
        output_file = os.path.join(temp_dir, "nlp_entropy_key.bin")
        text = "Entropy mode test text for key generation."

        result = runner.invoke(cli, [
            "keygen", "nlp",
            "-o", output_file,
            "-t", text,
            "--mode", "entropy",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_keygen_karmaca(self, runner, temp_dir):
        """测试KARMACA空间字典生成。"""
        output_file = os.path.join(temp_dir, "space_dict.json")

        result = runner.invoke(cli, [
            "keygen", "karmaca",
            "-o", output_file,
            "-d", "3",
            "-s", "10",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

        import json
        with open(output_file, "r") as f:
            data = json.load(f)
        assert "dimensions" in data
        assert "points" in data

    def test_keygen_combined(self, runner, temp_dir):
        """测试组合密钥生成。"""
        output_file = os.path.join(temp_dir, "combined_key.bin")
        text = "Combined key generation test."

        result = runner.invoke(cli, [
            "keygen", "combined",
            "-o", output_file,
            "-t", text,
            "--bits", "256",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) == 32

    def test_keygen_aes_for_encryption(self, runner, temp_dir):
        """测试生成的AES密钥可用于加解密。"""
        key_file = os.path.join(temp_dir, "key.bin")
        input_file = os.path.join(temp_dir, "input.txt")
        encrypted_file = os.path.join(temp_dir, "encrypted.bin")
        decrypted_file = os.path.join(temp_dir, "decrypted.txt")

        original_data = b"Test data for keygen encryption test"

        with open(input_file, "wb") as f:
            f.write(original_data)

        result = runner.invoke(cli, [
            "keygen", "aes",
            "-o", key_file,
            "--bits", "256",
        ])
        assert result.exit_code == 0

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

    def test_keygen_json_output(self, runner, temp_dir):
        """测试JSON格式输出。"""
        output_file = os.path.join(temp_dir, "aes_key.bin")

        result = runner.invoke(cli, [
            "-o", "json",
            "keygen", "aes",
            "-o", output_file,
            "--bits", "256",
        ])

        assert result.exit_code == 0
        import json
        output_data = json.loads(result.output)
        assert "success" in output_data
        assert output_data["success"] is True

    def test_keygen_help(self, runner):
        """测试keygen帮助。"""
        result = runner.invoke(cli, ["keygen", "--help"])
        assert result.exit_code == 0
        assert "aes" in result.output
        assert "rsa" in result.output
        assert "nlp" in result.output
        assert "karmaca" in result.output
        assert "combined" in result.output

    def test_keygen_missing_output(self, runner):
        """测试缺少输出参数。"""
        result = runner.invoke(cli, ["keygen", "aes"])
        assert result.exit_code != 0
