"""CLI CA证书测试模块。

测试CA证书管理命令。
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


class TestCLICA:
    """CA证书命令测试类。"""

    def test_ca_init_root(self, runner, temp_dir):
        """测试根CA初始化。"""
        cert_file = os.path.join(temp_dir, "root_ca.crt")
        key_file = os.path.join(temp_dir, "root_ca.key")

        result = runner.invoke(cli, [
            "ca", "init-root",
            "--name", "Test Root CA",
            "--key-size", "2048",
            "--validity-days", "365",
            "--cert-out", cert_file,
            "--key-out", key_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(cert_file)
        assert os.path.exists(key_file)

        with open(cert_file, "r") as f:
            content = f.read()
            assert "CERTIFICATE" in content

        with open(key_file, "r") as f:
            content = f.read()
            assert "PRIVATE KEY" in content

    def test_ca_info(self, runner, temp_dir):
        """测试证书信息查询。"""
        cert_file = os.path.join(temp_dir, "root_ca.crt")
        key_file = os.path.join(temp_dir, "root_ca.key")

        runner.invoke(cli, [
            "ca", "init-root",
            "--name", "Test CA",
            "--key-size", "2048",
            "--cert-out", cert_file,
            "--key-out", key_file,
        ])

        result = runner.invoke(cli, [
            "ca", "info",
            "-c", cert_file,
        ])

        assert result.exit_code == 0

    def test_ca_verify(self, runner, temp_dir):
        """测试证书验证。"""
        cert_file = os.path.join(temp_dir, "root_ca.crt")
        key_file = os.path.join(temp_dir, "root_ca.key")

        runner.invoke(cli, [
            "ca", "init-root",
            "--name", "Test CA",
            "--key-size", "2048",
            "--cert-out", cert_file,
            "--key-out", key_file,
        ])

        result = runner.invoke(cli, [
            "ca", "verify",
            "-c", cert_file,
        ])

        assert result.exit_code == 0

    def test_ca_issue(self, runner, temp_dir):
        """测试签发证书。"""
        ca_cert_file = os.path.join(temp_dir, "root_ca.crt")
        ca_key_file = os.path.join(temp_dir, "root_ca.key")
        cert_file = os.path.join(temp_dir, "user.crt")
        key_file = os.path.join(temp_dir, "user.key")

        runner.invoke(cli, [
            "ca", "init-root",
            "--name", "Test Root CA",
            "--key-size", "2048",
            "--cert-out", ca_cert_file,
            "--key-out", ca_key_file,
        ])

        result = runner.invoke(cli, [
            "ca", "issue",
            "-s", "test@example.com",
            "-t", "end_entity",
            "--validity-days", "365",
            "--key-size", "2048",
            "--ca-cert", ca_cert_file,
            "--ca-key", ca_key_file,
            "--cert-out", cert_file,
            "--key-out", key_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(cert_file)
        assert os.path.exists(key_file)

    def test_ca_init_root_json_output(self, runner, temp_dir):
        """测试JSON格式输出。"""
        cert_file = os.path.join(temp_dir, "root_ca.crt")
        key_file = os.path.join(temp_dir, "root_ca.key")

        result = runner.invoke(cli, [
            "-o", "json",
            "ca", "init-root",
            "--name", "Test Root CA",
            "--key-size", "2048",
            "--cert-out", cert_file,
            "--key-out", key_file,
        ])

        assert result.exit_code == 0
        import json
        output_data = json.loads(result.output)
        assert "success" in output_data
        assert output_data["success"] is True

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

    def test_ca_create_intermediate(self, runner, temp_dir):
        """测试创建中间CA。"""
        root_cert_file = os.path.join(temp_dir, "root_ca.crt")
        root_key_file = os.path.join(temp_dir, "root_ca.key")
        int_cert_file = os.path.join(temp_dir, "int_ca.crt")
        int_key_file = os.path.join(temp_dir, "int_ca.key")

        runner.invoke(cli, [
            "ca", "init-root",
            "--name", "Test Root CA",
            "--key-size", "2048",
            "--cert-out", root_cert_file,
            "--key-out", root_key_file,
        ])

        result = runner.invoke(cli, [
            "ca", "create-intermediate",
            "--name", "Test Intermediate CA",
            "--type", "intermediate_ca",
            "--root-cert", root_cert_file,
            "--root-key", root_key_file,
            "--cert-out", int_cert_file,
            "--key-out", int_key_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(int_cert_file)
        assert os.path.exists(int_key_file)

    def test_ca_revoke(self, runner, temp_dir):
        """测试吊销证书。"""
        ca_cert_file = os.path.join(temp_dir, "root_ca.crt")
        ca_key_file = os.path.join(temp_dir, "root_ca.key")
        cert_file = os.path.join(temp_dir, "user.crt")
        key_file = os.path.join(temp_dir, "user.key")

        runner.invoke(cli, [
            "ca", "init-root",
            "--name", "Test Root CA",
            "--key-size", "2048",
            "--cert-out", ca_cert_file,
            "--key-out", ca_key_file,
        ])

        runner.invoke(cli, [
            "ca", "issue",
            "-s", "test@example.com",
            "-t", "end_entity",
            "--ca-cert", ca_cert_file,
            "--ca-key", ca_key_file,
            "--cert-out", cert_file,
            "--key-out", key_file,
        ])

        from cryptography import x509
        with open(cert_file, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        serial = str(cert.serial_number)

        result = runner.invoke(cli, [
            "ca", "revoke",
            "-s", serial,
            "-r", "key_compromise",
            "--ca-cert", ca_cert_file,
            "--ca-key", ca_key_file,
        ])

        assert result.exit_code == 0

    def test_ca_list(self, runner, temp_dir):
        """测试列出证书。"""
        ca_cert_file = os.path.join(temp_dir, "root_ca.crt")
        ca_key_file = os.path.join(temp_dir, "root_ca.key")

        runner.invoke(cli, [
            "ca", "init-root",
            "--name", "Test Root CA",
            "--key-size", "2048",
            "--cert-out", ca_cert_file,
            "--key-out", ca_key_file,
        ])

        result = runner.invoke(cli, [
            "ca", "list",
            "--ca-cert", ca_cert_file,
            "--ca-key", ca_key_file,
        ])

        assert result.exit_code == 0

    def test_ca_verify_with_ca(self, runner, temp_dir):
        """测试带CA证书的验证。"""
        ca_cert_file = os.path.join(temp_dir, "root_ca.crt")
        ca_key_file = os.path.join(temp_dir, "root_ca.key")
        cert_file = os.path.join(temp_dir, "user.crt")
        key_file = os.path.join(temp_dir, "user.key")

        runner.invoke(cli, [
            "ca", "init-root",
            "--name", "Test Root CA",
            "--key-size", "2048",
            "--cert-out", ca_cert_file,
            "--key-out", ca_key_file,
        ])

        runner.invoke(cli, [
            "ca", "issue",
            "-s", "test@example.com",
            "-t", "end_entity",
            "--ca-cert", ca_cert_file,
            "--ca-key", ca_key_file,
            "--cert-out", cert_file,
            "--key-out", key_file,
        ])

        result = runner.invoke(cli, [
            "ca", "verify",
            "-c", cert_file,
            "--ca-cert", ca_cert_file,
        ])

        assert result.exit_code == 0

    def test_ca_init_root_yaml_output(self, runner, temp_dir):
        """测试YAML格式输出。"""
        cert_file = os.path.join(temp_dir, "root_ca.crt")
        key_file = os.path.join(temp_dir, "root_ca.key")

        result = runner.invoke(cli, [
            "-o", "yaml",
            "ca", "init-root",
            "--name", "Test Root CA",
            "--key-size", "2048",
            "--cert-out", cert_file,
            "--key-out", key_file,
        ])

        assert result.exit_code == 0
        assert "success" in result.output
