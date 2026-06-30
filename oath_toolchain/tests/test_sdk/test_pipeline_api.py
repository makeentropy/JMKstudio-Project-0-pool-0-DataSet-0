"""管道API单元测试。"""
import pytest

from oath_toolchain.sdk import OathSDK
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.core.base import OathTool


class MockTool(OathTool):
    """测试用模拟工具。"""

    __test__ = False

    name: str = "mock_pipeline_tool"
    description: str = "管道测试模拟工具"
    _version: str = "0.1.0"
    _tags: list = ["test", "mock"]
    _category: str = "test"

    def execute(self, params: dict) -> dict:
        action = params.get("action", "default")
        input_data = params.get("data", "")
        return {
            "success": True,
            "action": action,
            "result": f"processed_{action}_{input_data}",
            "input": input_data,
        }


class TestPipelineAPI:
    """测试PipelineAPI类。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.sdk = OathSDK()
        self.mock_tool = MockTool()
        self.sdk.engine.register_tool(self.mock_tool)

    def test_list_pipelines(self):
        """测试列出管道。"""
        pipelines = self.sdk.pipelines.list_pipelines()
        assert isinstance(pipelines, list)

    def test_list_pipelines_default(self):
        """测试默认管道已注册。"""
        pipelines = self.sdk.pipelines.list_pipelines()
        pipeline_names = [p["name"] for p in pipelines]
        assert "full_encryption" in pipeline_names
        assert "stego_encrypt" in pipeline_names
        assert "secure_dataset" in pipeline_names

    def test_create_pipeline(self):
        """测试创建管道。"""
        steps = [
            {
                "name": "step1",
                "tool": "mock_pipeline_tool",
                "action": "process",
                "params": {},
                "input_mapping": {"data": "input"},
                "output_key": "step1_result",
            },
        ]

        result = self.sdk.pipelines.create_pipeline("test_pipeline", steps)
        assert isinstance(result, dict)
        assert result["name"] == "test_pipeline"
        assert result["step_count"] == 1

        pipelines = self.sdk.pipelines.list_pipelines()
        pipeline_names = [p["name"] for p in pipelines]
        assert "test_pipeline" in pipeline_names

    def test_run_pipeline(self):
        """测试执行管道。"""
        steps = [
            {
                "name": "step1",
                "tool": "mock_pipeline_tool",
                "action": "test_action",
                "params": {},
                "input_mapping": {"data": "input"},
                "output_key": "output",
            },
        ]

        self.sdk.pipelines.create_pipeline("run_test_pipeline", steps)

        result = self.sdk.pipelines.run_pipeline("run_test_pipeline", "hello")
        assert isinstance(result, dict)

    def test_run_pipeline_nonexistent(self):
        """测试执行不存在的管道。"""
        with pytest.raises(Exception):
            self.sdk.pipelines.run_pipeline("nonexistent_pipeline", "data")

    def test_create_workflow(self):
        """测试创建工作流。"""
        definition = {
            "steps": [
                {"id": "step1", "type": "action", "name": "test"},
            ]
        }

        result = self.sdk.pipelines.create_workflow("test_workflow", definition)
        assert isinstance(result, dict)
        assert result["name"] == "test_workflow"
        assert result["definition"] == definition

    def test_run_workflow_nonexistent(self):
        """测试执行不存在的工作流。"""
        with pytest.raises(Exception):
            self.sdk.pipelines.run_workflow("nonexistent_workflow", "data")

    def test_register_profile(self):
        """测试注册配置文件。"""
        from oath_toolchain.core.crypto.primitives import AESCipher
        aes_key = AESCipher.generate_key(256)

        config = {
            "aes_key": aes_key,
            "use_geometric_proof": False,
        }

        self.sdk.pipelines.register_profile("test_profile", config)
        assert "test_profile" in self.sdk.pipelines._profiles

    def test_encrypt_decrypt_with_profile(self):
        """测试使用配置文件加密解密。"""
        from oath_toolchain.core.crypto.primitives import AESCipher
        aes_key = AESCipher.generate_key(256)
        test_data = b"Profile encryption test"

        config = {
            "aes_key": aes_key,
        }

        self.sdk.pipelines.register_profile("crypto_profile", config)

        encrypted = self.sdk.pipelines.encrypt_with_profile(
            "crypto_profile", test_data
        )
        assert isinstance(encrypted, dict)
        assert "final_data" in encrypted

        decrypted = self.sdk.pipelines.decrypt_with_profile(
            "crypto_profile", encrypted
        )
        assert decrypted == test_data

    def test_encrypt_with_profile_not_found(self):
        """测试使用不存在的配置文件加密。"""
        with pytest.raises(ValueError, match="配置文件不存在"):
            self.sdk.pipelines.encrypt_with_profile("no_such_profile", b"data")

    def test_decrypt_with_profile_not_found(self):
        """测试使用不存在的配置文件解密。"""
        with pytest.raises(ValueError, match="配置文件不存在"):
            self.sdk.pipelines.decrypt_with_profile("no_such_profile", {})
