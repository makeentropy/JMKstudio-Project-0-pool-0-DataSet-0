"""隐写CLI命令测试。"""
import os
import tempfile

import pytest
from click.testing import CliRunner

from oath_toolchain.cli.main import cli


class TestCLIStego:
    """隐写命令测试类。"""

    @pytest.fixture
    def runner(self):
        """创建CLI测试运行器。"""
        return CliRunner()

    @pytest.fixture
    def tmpdir(self):
        """创建临时目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_stego_embed_xor(self, runner, tmpdir):
        """测试XOR隐写嵌入。"""
        secret_file = os.path.join(tmpdir, "secret.txt")
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        output_file = os.path.join(tmpdir, "output.txt")

        with open(secret_file, "w", encoding="utf-8") as f:
            f.write("Secret message")

        with open(carrier_file, "w", encoding="utf-8") as f:
            f.write("This is a carrier text with enough length to hide the secret message inside it. " * 10)

        result = runner.invoke(cli, [
            "stego", "embed", "xor",
            "-s", secret_file,
            "-c", carrier_file,
            "-o", output_file,
            "-k", "testkey",
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_stego_embed_unicode(self, runner, tmpdir):
        """测试Unicode隐写嵌入。"""
        secret_file = os.path.join(tmpdir, "secret.txt")
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        output_file = os.path.join(tmpdir, "output.txt")

        with open(secret_file, "w", encoding="utf-8") as f:
            f.write("Hi")

        with open(carrier_file, "w", encoding="utf-8") as f:
            f.write("Hello World " * 100)

        result = runner.invoke(cli, [
            "stego", "embed", "unicode",
            "-s", secret_file,
            "-c", carrier_file,
            "-o", output_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_stego_embed_case(self, runner, tmpdir):
        """测试大小写隐写嵌入。"""
        secret_file = os.path.join(tmpdir, "secret.txt")
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        output_file = os.path.join(tmpdir, "output.txt")

        with open(secret_file, "wb") as f:
            f.write(b"\x00")

        with open(carrier_file, "w", encoding="utf-8") as f:
            f.write("abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz")

        result = runner.invoke(cli, [
            "stego", "embed", "case",
            "-s", secret_file,
            "-c", carrier_file,
            "-o", output_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_stego_embed_whitespace(self, runner, tmpdir):
        """测试空格隐写嵌入。"""
        secret_file = os.path.join(tmpdir, "secret.txt")
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        output_file = os.path.join(tmpdir, "output.txt")

        with open(secret_file, "wb") as f:
            f.write(b"\x00")

        with open(carrier_file, "w", encoding="utf-8") as f:
            for i in range(50):
                f.write(f"line {i}\n")

        result = runner.invoke(cli, [
            "stego", "embed", "whitespace",
            "-s", secret_file,
            "-c", carrier_file,
            "-o", output_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

    def test_stego_help(self, runner):
        """测试stego帮助信息。"""
        result = runner.invoke(cli, ["stego", "--help"])
        assert result.exit_code == 0
        assert "隐写" in result.output or "stego" in result.output.lower()

    def test_stego_embed_help(self, runner):
        """测试stego embed帮助信息。"""
        result = runner.invoke(cli, ["stego", "embed", "--help"])
        assert result.exit_code == 0

    def test_stego_extract_help(self, runner):
        """测试stego extract帮助信息。"""
        result = runner.invoke(cli, ["stego", "extract", "--help"])
        assert result.exit_code == 0

    def test_stego_analyze_help(self, runner):
        """测试stego analyze帮助信息。"""
        result = runner.invoke(cli, ["stego", "analyze", "--help"])
        assert result.exit_code == 0

    def test_stego_analyze(self, runner, tmpdir):
        """测试载体分析。"""
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        with open(carrier_file, "w", encoding="utf-8") as f:
            f.write("Hello World! This is a test carrier file.")

        result = runner.invoke(cli, [
            "stego", "analyze",
            "-i", carrier_file,
        ])

        assert result.exit_code == 0

    def test_stego_extract_xor_help(self, runner):
        """测试stego extract xor帮助信息。"""
        result = runner.invoke(cli, ["stego", "extract", "xor", "--help"])
        assert result.exit_code == 0

    def test_stego_extract_unicode_help(self, runner):
        """测试stego extract unicode帮助信息。"""
        result = runner.invoke(cli, ["stego", "extract", "unicode", "--help"])
        assert result.exit_code == 0

    def test_stego_extract_whitespace_help(self, runner):
        """测试stego extract whitespace帮助信息。"""
        result = runner.invoke(cli, ["stego", "extract", "whitespace", "--help"])
        assert result.exit_code == 0

    def test_stego_extract_case_help(self, runner):
        """测试stego extract case帮助信息。"""
        result = runner.invoke(cli, ["stego", "extract", "case", "--help"])
        assert result.exit_code == 0

    def test_stego_embed_cert_help(self, runner):
        """测试stego embed cert帮助信息。"""
        result = runner.invoke(cli, ["stego", "embed", "cert", "--help"])
        assert result.exit_code == 0

    def test_stego_extract_cert_help(self, runner):
        """测试stego extract cert帮助信息。"""
        result = runner.invoke(cli, ["stego", "extract", "cert", "--help"])
        assert result.exit_code == 0

    def test_stego_extract_xor(self, runner, tmpdir):
        """测试XOR隐写提取。"""
        secret_file = os.path.join(tmpdir, "secret.txt")
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        output_file = os.path.join(tmpdir, "output.txt")
        extract_file = os.path.join(tmpdir, "extracted.txt")

        secret_data = "Secret message"
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(secret_data)

        with open(carrier_file, "w", encoding="utf-8") as f:
            f.write("This is a carrier text with enough length to hide the secret message inside it. " * 10)

        runner.invoke(cli, [
            "stego", "embed", "xor",
            "-s", secret_file,
            "-c", carrier_file,
            "-o", output_file,
            "-k", "testkey",
        ])

        result = runner.invoke(cli, [
            "stego", "extract", "xor",
            "-i", output_file,
            "-o", extract_file,
            "-k", "testkey",
        ])

        assert result.exit_code == 0
        assert os.path.exists(extract_file)

    def test_stego_extract_unicode(self, runner, tmpdir):
        """测试Unicode隐写提取。"""
        secret_file = os.path.join(tmpdir, "secret.txt")
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        output_file = os.path.join(tmpdir, "output.txt")
        extract_file = os.path.join(tmpdir, "extracted.txt")

        with open(secret_file, "w", encoding="utf-8") as f:
            f.write("Hi")

        with open(carrier_file, "w", encoding="utf-8") as f:
            f.write("Hello World " * 100)

        runner.invoke(cli, [
            "stego", "embed", "unicode",
            "-s", secret_file,
            "-c", carrier_file,
            "-o", output_file,
        ])

        result = runner.invoke(cli, [
            "stego", "extract", "unicode",
            "-i", output_file,
            "-o", extract_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(extract_file)

    def test_stego_extract_whitespace(self, runner, tmpdir):
        """测试空格隐写提取。"""
        secret_file = os.path.join(tmpdir, "secret.txt")
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        output_file = os.path.join(tmpdir, "output.txt")
        extract_file = os.path.join(tmpdir, "extracted.txt")

        with open(secret_file, "wb") as f:
            f.write(b"\x00")

        with open(carrier_file, "w", encoding="utf-8") as f:
            for i in range(50):
                f.write(f"line {i}\n")

        runner.invoke(cli, [
            "stego", "embed", "whitespace",
            "-s", secret_file,
            "-c", carrier_file,
            "-o", output_file,
        ])

        result = runner.invoke(cli, [
            "stego", "extract", "whitespace",
            "-i", output_file,
            "-o", extract_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(extract_file)

    def test_stego_extract_case(self, runner, tmpdir):
        """测试大小写隐写提取。"""
        secret_file = os.path.join(tmpdir, "secret.txt")
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        output_file = os.path.join(tmpdir, "output.txt")
        extract_file = os.path.join(tmpdir, "extracted.txt")

        with open(secret_file, "wb") as f:
            f.write(b"\x00")

        with open(carrier_file, "w", encoding="utf-8") as f:
            f.write("abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz")

        runner.invoke(cli, [
            "stego", "embed", "case",
            "-s", secret_file,
            "-c", carrier_file,
            "-o", output_file,
        ])

        result = runner.invoke(cli, [
            "stego", "extract", "case",
            "-i", output_file,
            "-o", extract_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(extract_file)

    def test_stego_analyze_json(self, runner, tmpdir):
        """测试JSON格式的载体分析。"""
        carrier_file = os.path.join(tmpdir, "carrier.txt")
        with open(carrier_file, "w", encoding="utf-8") as f:
            f.write("Hello World! This is a test carrier file.")

        result = runner.invoke(cli, [
            "-o", "json",
            "stego", "analyze",
            "-i", carrier_file,
        ])

        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data.get("success") is True
