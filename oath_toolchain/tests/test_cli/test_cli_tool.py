"""CLI工具管理测试模块。

测试工具管理命令。
"""
import pytest
from click.testing import CliRunner

from oath_toolchain.cli.main import cli


@pytest.fixture
def runner():
    """创建CliRunner实例。"""
    return CliRunner()


class TestCLITool:
    """工具管理命令测试类。"""

    def test_tool_list(self, runner):
        """测试列出工具。"""
        result = runner.invoke(cli, ["tool", "list"])
        assert result.exit_code == 0

    def test_tool_list_json(self, runner):
        """测试JSON格式列出工具。"""
        result = runner.invoke(cli, ["-o", "json", "tool", "list"])
        assert result.exit_code == 0
        import json
        output_data = json.loads(result.output)
        assert "success" in output_data
        assert "tools" in output_data
        assert "count" in output_data

    def test_tool_list_yaml(self, runner):
        """测试YAML格式列出工具。"""
        result = runner.invoke(cli, ["-o", "yaml", "tool", "list"])
        assert result.exit_code == 0

    def test_tool_list_has_tools(self, runner):
        """测试工具列表不为空。"""
        result = runner.invoke(cli, ["-o", "json", "tool", "list"])
        assert result.exit_code == 0
        import json
        output_data = json.loads(result.output)
        assert output_data["count"] > 0

    def test_tool_info_geometric_proof(self, runner):
        """测试查询几何证明工具信息。"""
        result = runner.invoke(cli, [
            "tool", "info",
            "-n", "geometric_proof",
        ])
        assert result.exit_code == 0

    def test_tool_info_ca_system(self, runner):
        """测试查询CA系统工具信息。"""
        result = runner.invoke(cli, [
            "tool", "info",
            "-n", "ca_system",
        ])
        assert result.exit_code == 0

    def test_tool_info_steganography(self, runner):
        """测试查询隐写工具信息。"""
        result = runner.invoke(cli, [
            "tool", "info",
            "-n", "steganography",
        ])
        assert result.exit_code == 0

    def test_tool_info_dataset_pool(self, runner):
        """测试查询数据集工具信息。"""
        result = runner.invoke(cli, [
            "tool", "info",
            "-n", "dataset_pool",
        ])
        assert result.exit_code == 0

    def test_tool_info_json_output(self, runner):
        """测试JSON格式查询工具信息。"""
        result = runner.invoke(cli, [
            "-o", "json",
            "tool", "info",
            "-n", "geometric_proof",
        ])
        assert result.exit_code == 0
        import json
        output_data = json.loads(result.output)
        assert "success" in output_data
        assert "tool" in output_data
        tool = output_data["tool"]
        assert "name" in tool
        assert "description" in tool
        assert "version" in tool

    def test_tool_execute_hash(self, runner):
        """测试执行工具操作（几何哈希）。"""
        import json
        params = json.dumps({"data": "test_data"})
        result = runner.invoke(cli, [
            "tool", "execute",
            "-n", "geometric_proof",
            "-a", "hash",
            "-p", params,
        ])
        assert result.exit_code == 0

    def test_tool_execute_nonexistent(self, runner):
        """测试执行不存在的工具。"""
        result = runner.invoke(cli, [
            "tool", "info",
            "-n", "nonexistent_tool",
        ])
        assert result.exit_code != 0

    def test_tool_help(self, runner):
        """测试tool命令帮助。"""
        result = runner.invoke(cli, ["tool", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "info" in result.output
        assert "execute" in result.output

    def test_tool_list_quiet(self, runner):
        """测试静默模式。"""
        result = runner.invoke(cli, ["--quiet", "tool", "list"])
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_tool_list_verbose(self, runner):
        """测试详细模式。"""
        result = runner.invoke(cli, ["--verbose", "tool", "list"])
        assert result.exit_code == 0
