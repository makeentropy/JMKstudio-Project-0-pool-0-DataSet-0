"""数据集CLI命令测试。"""
import os
import tempfile
import json

import pytest
from click.testing import CliRunner

from oath_toolchain.cli.main import cli


class TestCLIDataset:
    """数据集命令测试类。"""

    @pytest.fixture
    def runner(self):
        """创建CLI测试运行器。"""
        return CliRunner()

    @pytest.fixture
    def tmpdir(self):
        """创建临时目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_dataset_help(self, runner):
        """测试dataset帮助信息。"""
        result = runner.invoke(cli, ["dataset", "--help"])
        assert result.exit_code == 0
        assert "数据集" in result.output or "dataset" in result.output.lower()

    def test_dataset_create_help(self, runner):
        """测试dataset create帮助信息。"""
        result = runner.invoke(cli, ["dataset", "create", "--help"])
        assert result.exit_code == 0

    def test_dataset_list_help(self, runner):
        """测试dataset list帮助信息。"""
        result = runner.invoke(cli, ["dataset", "list", "--help"])
        assert result.exit_code == 0

    def test_dataset_get_help(self, runner):
        """测试dataset get帮助信息。"""
        result = runner.invoke(cli, ["dataset", "get", "--help"])
        assert result.exit_code == 0

    def test_dataset_delete_help(self, runner):
        """测试dataset delete帮助信息。"""
        result = runner.invoke(cli, ["dataset", "delete", "--help"])
        assert result.exit_code == 0

    def test_dataset_export_help(self, runner):
        """测试dataset export帮助信息。"""
        result = runner.invoke(cli, ["dataset", "export", "--help"])
        assert result.exit_code == 0

    def test_dataset_tag_help(self, runner):
        """测试dataset tag帮助信息。"""
        result = runner.invoke(cli, ["dataset", "tag", "--help"])
        assert result.exit_code == 0

    def test_dataset_version_help(self, runner):
        """测试dataset version帮助信息。"""
        result = runner.invoke(cli, ["dataset", "version", "--help"])
        assert result.exit_code == 0

    def test_dataset_create_list_json(self, runner, tmpdir):
        """测试创建和列出数据集。"""
        input_file = os.path.join(tmpdir, "data.json")
        data = {
            "items": [
                {"id": "1", "name": "test1"},
                {"id": "2", "name": "test2"},
            ]
        }
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = runner.invoke(cli, [
            "dataset", "create",
            "-n", "test_dataset",
            "-i", input_file,
        ])

        assert result.exit_code == 0

    def test_dataset_list(self, runner):
        """测试数据集列表。"""
        result = runner.invoke(cli, ["dataset", "list"])
        assert result.exit_code == 0

    def test_dataset_create_json(self, runner, tmpdir):
        """测试创建数据集（JSON输出）。"""
        input_file = os.path.join(tmpdir, "data.json")
        data = {
            "items": [
                {"id": "1", "name": "test1"},
                {"id": "2", "name": "test2"},
            ]
        }
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = runner.invoke(cli, [
            "-o", "json",
            "dataset", "create",
            "-n", "test_dataset",
            "-i", input_file,
        ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "success" in data

    def test_dataset_get_help(self, runner):
        """测试dataset get帮助信息。"""
        result = runner.invoke(cli, ["dataset", "get", "--help"])
        assert result.exit_code == 0

    def test_dataset_delete_help(self, runner):
        """测试dataset delete帮助信息。"""
        result = runner.invoke(cli, ["dataset", "delete", "--help"])
        assert result.exit_code == 0

    def test_dataset_export_help(self, runner):
        """测试dataset export帮助信息。"""
        result = runner.invoke(cli, ["dataset", "export", "--help"])
        assert result.exit_code == 0

    def test_dataset_tag_help(self, runner):
        """测试dataset tag帮助信息。"""
        result = runner.invoke(cli, ["dataset", "tag", "--help"])
        assert result.exit_code == 0

    def test_dataset_version_help(self, runner):
        """测试dataset version帮助信息。"""
        result = runner.invoke(cli, ["dataset", "version", "--help"])
        assert result.exit_code == 0

    def test_dataset_tag_add_help(self, runner):
        """测试dataset tag add帮助信息。"""
        result = runner.invoke(cli, ["dataset", "tag", "add", "--help"])
        assert result.exit_code == 0

    def test_dataset_version_commit_help(self, runner):
        """测试dataset version commit帮助信息。"""
        result = runner.invoke(cli, ["dataset", "version", "commit", "--help"])
        assert result.exit_code == 0

    def test_dataset_version_list_help(self, runner):
        """测试dataset version list帮助信息。"""
        result = runner.invoke(cli, ["dataset", "version", "list", "--help"])
        assert result.exit_code == 0

    def test_dataset_list_json(self, runner):
        """测试JSON格式的数据集列表。"""
        result = runner.invoke(cli, ["-o", "json", "dataset", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "success" in data

    def test_dataset_create_yaml(self, runner, tmpdir):
        """测试创建数据集（YAML输出）。"""
        input_file = os.path.join(tmpdir, "data.json")
        data = {
            "items": [
                {"id": "1", "name": "test1"},
            ]
        }
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = runner.invoke(cli, [
            "-o", "yaml",
            "dataset", "create",
            "-n", "test_dataset_yaml",
            "-i", input_file,
        ])

        assert result.exit_code == 0
        assert "success" in result.output
