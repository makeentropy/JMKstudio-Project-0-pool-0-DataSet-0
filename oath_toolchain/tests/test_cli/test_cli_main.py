"""CLI主入口测试模块。

测试CLI主命令和全局选项。
"""
import pytest
from click.testing import CliRunner

from oath_toolchain.cli.main import cli


@pytest.fixture
def runner():
    """创建CliRunner实例。"""
    return CliRunner()


class TestCLIMain:
    """CLI主入口测试类。"""

    def test_help_command(self, runner):
        """测试帮助命令。"""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "神誓工具链" in result.output
        assert "encrypt" in result.output
        assert "decrypt" in result.output
        assert "keygen" in result.output
        assert "sign" in result.output
        assert "verify" in result.output
        assert "ca" in result.output
        assert "stego" in result.output
        assert "dataset" in result.output
        assert "pipeline" in result.output
        assert "tool" in result.output

    def test_output_json(self, runner):
        """测试--output选项。"""
        result = runner.invoke(cli, ["--output", "json", "tool", "list"])
        assert result.exit_code == 0

    def test_output_yaml(self, runner):
        """测试--output选项(yaml格式。"""
        result = runner.invoke(cli, ["--output", "yaml", "tool", "list"])
        assert result.exit_code == 0

    def test_quiet_mode(self, runner):
        """测试静默模式。"""
        result = runner.invoke(cli, ["--quiet", "tool", "list"])
        assert result.exit_code == 0

    def test_verbose_mode(self, runner):
        """测试详细输出模式。"""
        result = runner.invoke(cli, ["--verbose", "tool", "list"])
        assert result.exit_code == 0

    def test_invalid_command(self, runner):
        """测试无效命令。"""
        result = runner.invoke(cli, ["invalid_command"])
        assert result.exit_code != 0

    def test_encrypt_help(self, runner):
        """测试加密命令帮助。"""
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert result.exit_code == 0
        assert "aes" in result.output
        assert "rsa" in result.output
        assert "karmaca" in result.output

    def test_decrypt_help(self, runner):
        """测试解密命令帮助。"""
        result = runner.invoke(cli, ["decrypt", "--help"])
        assert result.exit_code == 0
        assert "aes" in result.output
        assert "rsa" in result.output

    def test_keygen_help(self, runner):
        """测试密钥生成命令帮助。"""
        result = runner.invoke(cli, ["keygen", "--help"])
        assert result.exit_code == 0
        assert "aes" in result.output
        assert "rsa" in result.output
        assert "nlp" in result.output

    def test_sign_help(self, runner):
        """测试签名命令帮助。"""
        result = runner.invoke(cli, ["sign", "--help"])
        assert result.exit_code == 0
        assert "rsa" in result.output
        assert "hmac" in result.output

    def test_verify_help(self, runner):
        """测试验证命令帮助。"""
        result = runner.invoke(cli, ["verify", "--help"])
        assert result.exit_code == 0
        assert "rsa" in result.output
        assert "hmac" in result.output
        assert "cert" in result.output

    def test_ca_help(self, runner):
        """测试CA命令帮助。"""
        result = runner.invoke(cli, ["ca", "--help"])
        assert result.exit_code == 0
        assert "init-root" in result.output
        assert "create-intermediate" in result.output
        assert "issue" in result.output
        assert "verify" in result.output
        assert "revoke" in result.output
        assert "list" in result.output
        assert "info" in result.output

    def test_stego_help(self, runner):
        """测试隐写命令帮助。"""
        result = runner.invoke(cli, ["stego", "--help"])
        assert result.exit_code == 0
        assert "embed" in result.output
        assert "extract" in result.output
        assert "analyze" in result.output

    def test_dataset_help(self, runner):
        """测试数据集命令帮助。"""
        result = runner.invoke(cli, ["dataset", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "get" in result.output
        assert "delete" in result.output

    def test_pipeline_help(self, runner):
        """测试管道命令帮助。"""
        result = runner.invoke(cli, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "run" in result.output
        assert "create" in result.output

    def test_tool_help(self, runner):
        """测试工具命令帮助。"""
        result = runner.invoke(cli, ["tool", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "info" in result.output
        assert "execute" in result.output

    def test_config_json_file(self, runner, tmp_path):
        """测试JSON配置文件加载。"""
        config_file = tmp_path / "config.json"
        import json
        config_file.write_text(json.dumps({"setting": "value"}))

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "tool", "list",
        ])
        assert result.exit_code == 0

    def test_config_yaml_file(self, runner, tmp_path):
        """测试YAML配置文件加载。"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("setting: value\n")

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "tool", "list",
        ])
        assert result.exit_code == 0

    def test_config_invalid_file(self, runner, tmp_path):
        """测试无效配置文件。"""
        config_file = tmp_path / "config.json"
        config_file.write_text("invalid json content")

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "tool", "list",
        ])
        assert result.exit_code != 0

    def test_output_text_format(self, runner):
        """测试text输出格式。"""
        result = runner.invoke(cli, ["--output", "text", "tool", "list"])
        assert result.exit_code == 0

    def test_verbose_encrypt(self, runner, tmp_path):
        """测试verbose模式下的加密。"""
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "output.enc"
        key_file = tmp_path / "key.bin"

        input_file.write_text("test")

        from oath_toolchain.core.crypto.primitives import AESCipher
        key = AESCipher.generate_key(256)
        key_file.write_bytes(key)

        result = runner.invoke(cli, [
            "--verbose",
            "encrypt", "aes",
            "-i", str(input_file),
            "-o", str(output_file),
            "-k", str(key_file),
        ])
        assert result.exit_code == 0

    def test_short_options(self, runner):
        """测试短选项（-v, -q, -o）。"""
        result = runner.invoke(cli, ["-v", "-o", "json", "tool", "list"])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["-q", "tool", "list"])
        assert result.exit_code == 0
