"""OathSDK主类单元测试。"""
import pytest

from oath_toolchain.sdk import OathSDK
from oath_toolchain.sdk.crypto_api import CryptoAPI
from oath_toolchain.sdk.key_api import KeyAPI
from oath_toolchain.sdk.ca_api import CAAPI
from oath_toolchain.sdk.stego_api import StegoAPI
from oath_toolchain.sdk.dataset_api import DatasetAPI
from oath_toolchain.sdk.pipeline_api import PipelineAPI
from oath_toolchain.orchestration.qiankun_engine import QiankunEngine
from oath_toolchain.core.registry import ToolRegistry


class TestOathSDK:
    """测试OathSDK主类。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.sdk = OathSDK()

    def test_init_default(self):
        """测试默认初始化。"""
        sdk = OathSDK()
        assert sdk is not None
        assert sdk.engine is not None
        assert isinstance(sdk.engine, QiankunEngine)

    def test_init_with_config(self):
        """测试带配置初始化。"""
        config = {"auto_register_tools": False}
        sdk = OathSDK(config=config)
        assert sdk.config == config

    def test_crypto_property(self):
        """测试crypto属性。"""
        assert hasattr(self.sdk, 'crypto')
        assert isinstance(self.sdk.crypto, CryptoAPI)

    def test_keys_property(self):
        """测试keys属性。"""
        assert hasattr(self.sdk, 'keys')
        assert isinstance(self.sdk.keys, KeyAPI)

    def test_ca_property(self):
        """测试ca属性。"""
        assert hasattr(self.sdk, 'ca')
        assert isinstance(self.sdk.ca, CAAPI)

    def test_stego_property(self):
        """测试stego属性。"""
        assert hasattr(self.sdk, 'stego')
        assert isinstance(self.sdk.stego, StegoAPI)

    def test_datasets_property(self):
        """测试datasets属性。"""
        assert hasattr(self.sdk, 'datasets')
        assert isinstance(self.sdk.datasets, DatasetAPI)

    def test_pipelines_property(self):
        """测试pipelines属性。"""
        assert hasattr(self.sdk, 'pipelines')
        assert isinstance(self.sdk.pipelines, PipelineAPI)

    def test_list_tools(self):
        """测试list_tools方法。"""
        tools = self.sdk.list_tools()
        assert isinstance(tools, list)

    def test_list_tools_contains_registered(self):
        """测试list_tools包含已注册的工具。"""
        from oath_toolchain.core.base import OathTool

        class TestTool(OathTool):
            __test__ = False
            name = "test_sdk_tool"
            description = "测试工具"
            _version = "0.1.0"
            _tags = ["test"]
            _category = "test"

            def execute(self, params):
                return {"success": True}

        tool = TestTool()
        self.sdk.engine.register_tool(tool)

        tools = self.sdk.list_tools()
        tool_names = [t.get("name") for t in tools]
        assert "test_sdk_tool" in tool_names

    def test_execute_tool(self):
        """测试execute_tool方法。"""
        from oath_toolchain.core.base import OathTool

        class EchoTool(OathTool):
            __test__ = False
            name = "echo_tool"
            description = "回声工具"
            _version = "0.1.0"
            _tags = ["test"]
            _category = "test"

            def execute(self, params):
                return {
                    "success": True,
                    "action": params.get("action"),
                    "echo": params.get("message", ""),
                }

        tool = EchoTool()
        self.sdk.engine.register_tool(tool)

        result = self.sdk.execute_tool(
            "echo_tool",
            "say_hello",
            {"message": "hello world"},
        )
        assert result["success"] is True
        assert result["action"] == "say_hello"
        assert result["echo"] == "hello world"

    def test_execute_tool_not_found(self):
        """测试执行不存在的工具。"""
        with pytest.raises(Exception):
            self.sdk.execute_tool(
                "nonexistent_tool",
                "test",
                {},
            )

    def test_version(self):
        """测试version方法。"""
        version = self.sdk.version()
        assert isinstance(version, str)
        assert version == "0.1.0"

    def test_top_level_import(self):
        """测试从顶层包导入OathSDK。"""
        from oath_toolchain import OathSDK as TopOathSDK
        assert TopOathSDK is OathSDK

    def test_all_sub_apis_have_engine_reference(self):
        """测试所有子API都有引擎引用。"""
        assert self.sdk.crypto._engine is self.sdk.engine
        assert self.sdk.keys._engine is self.sdk.engine
        assert self.sdk.ca._engine is self.sdk.engine
        assert self.sdk.stego._engine is self.sdk.engine
        assert self.sdk.datasets._engine is self.sdk.engine
        assert self.sdk.pipelines._engine is self.sdk.engine
