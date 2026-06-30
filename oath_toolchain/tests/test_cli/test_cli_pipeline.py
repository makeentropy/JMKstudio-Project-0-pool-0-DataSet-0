"""管道CLI命令测试。"""
import os
import tempfile
import json

import pytest
from click.testing import CliRunner

from oath_toolchain.cli.main import cli


class TestCLIPipeline:
    """管道命令测试类。"""

    @pytest.fixture
    def runner(self):
        """创建CLI测试运行器。"""
        return CliRunner()

    @pytest.fixture
    def tmpdir(self):
        """创建临时目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_pipeline_help(self, runner):
        """测试pipeline帮助信息。"""
        result = runner.invoke(cli, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "管道" in result.output or "pipeline" in result.output.lower()

    def test_pipeline_list_help(self, runner):
        """测试pipeline list帮助信息。"""
        result = runner.invoke(cli, ["pipeline", "list", "--help"])
        assert result.exit_code == 0

    def test_pipeline_run_help(self, runner):
        """测试pipeline run帮助信息。"""
        result = runner.invoke(cli, ["pipeline", "run", "--help"])
        assert result.exit_code == 0

    def test_pipeline_create_help(self, runner):
        """测试pipeline create帮助信息。"""
        result = runner.invoke(cli, ["pipeline", "create", "--help"])
        assert result.exit_code == 0

    def test_pipeline_list(self, runner):
        """测试列出管道。"""
        result = runner.invoke(cli, ["pipeline", "list"])
        assert result.exit_code == 0
        assert "full_encryption" in result.output

    def test_pipeline_list_json(self, runner):
        """测试JSON格式的管道列表。"""
        result = runner.invoke(cli, ["-o", "json", "pipeline", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data.get("success") is True
        assert "pipelines" in data

    def test_pipeline_run_full_encryption(self, runner, tmpdir):
        """测试运行完整加密管道。"""
        input_file = os.path.join(tmpdir, "input.txt")
        output_file = os.path.join(tmpdir, "output.enc")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Hello, Pipeline!")

        result = runner.invoke(cli, [
            "pipeline", "run",
            "-n", "full_encryption",
            "-i", input_file,
            "-o", output_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) > 0

    def test_pipeline_run_stego_encrypt(self, runner, tmpdir):
        """测试运行隐写加密管道。"""
        input_file = os.path.join(tmpdir, "input.txt")
        output_file = os.path.join(tmpdir, "output.enc")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Secret data")

        result = runner.invoke(cli, [
            "pipeline", "run",
            "-n", "stego_encrypt",
            "-i", input_file,
            "-o", output_file,
        ])

        assert result.exit_code == 0

    def test_pipeline_run_nonexistent(self, runner, tmpdir):
        """测试运行不存在的管道。"""
        input_file = os.path.join(tmpdir, "input.txt")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write("test")

        result = runner.invoke(cli, [
            "pipeline", "run",
            "-n", "nonexistent_pipeline",
            "-i", input_file,
            "-o", "/tmp/out.bin",
        ])

        assert result.exit_code != 0
