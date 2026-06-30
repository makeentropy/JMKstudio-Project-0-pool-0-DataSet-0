"""乾坤程序引擎单元测试。"""
import pytest

from oath_toolchain.core.base import OathTool
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.orchestration import QiankunEngine
from oath_toolchain.core.exceptions import ValidationError


class MockTool(OathTool):
    """测试用模拟工具。"""

    __test__ = False

    name: str = "mock_tool"
    description: str = "模拟测试工具"
    _version: str = "0.1.0"
    _tags: list[str] = ["test", "mock"]
    _category: str = "test"

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0
        self.last_params = None

    def execute(self, params: dict) -> dict:
        self.call_count += 1
        self.last_params = params
        action = params.get("action", "default")
        return {
            "success": True,
            "action": action,
            "result": f"mock_result_{action}",
            "params_received": params,
        }


class MockTool2(OathTool):
    """第二个测试用模拟工具。"""

    __test__ = False

    name: str = "mock_tool_2"
    description: str = "第二个模拟测试工具"
    _version: str = "0.2.0"
    _tags: list[str] = ["test", "mock", "second"]
    _category: str = "test"

    def execute(self, params: dict) -> dict:
        action = params.get("action", "default")
        return {
            "success": True,
            "action": action,
            "result": f"mock2_result_{action}",
        }


class TestQiankunEngine:
    """测试乾坤程序引擎。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.engine = QiankunEngine()

    def test_init_default(self):
        """测试默认初始化。"""
        engine = QiankunEngine()
        assert engine is not None
        assert isinstance(engine.pipelines, dict)
        assert isinstance(engine.workflows, dict)
        assert isinstance(engine.security_context, dict)

    def test_init_with_config(self):
        """测试带配置的初始化。"""
        config = {"auto_register_tools": False}
        engine = QiankunEngine(config=config)
        assert engine.config == config

    def test_register_tool(self):
        """测试注册工具。"""
        tool = MockTool()
        self.engine.register_tool(tool)
        assert "mock_tool" in self.engine._tool_instances

    def test_register_tool_invalid_type(self):
        """测试注册非工具类型。"""
        with pytest.raises(TypeError):
            self.engine.register_tool("not a tool")

    def test_register_tool_duplicate(self):
        """测试重复注册工具。"""
        tool1 = MockTool()
        tool2 = MockTool()
        self.engine.register_tool(tool1)
        with pytest.raises(ValueError, match="mock_tool"):
            self.engine.register_tool(tool2)

    def test_get_tool_registered(self):
        """测试获取已注册的工具。"""
        tool = MockTool()
        self.engine.register_tool(tool)
        result = self.engine.get_tool("mock_tool")
        assert result is tool

    def test_get_tool_from_registry(self):
        """测试从注册表获取工具。"""
        registry = ToolRegistry()
        registry.register(MockTool)
        result = self.engine.get_tool("mock_tool")
        assert isinstance(result, MockTool)

    def test_get_tool_not_found(self):
        """测试获取不存在的工具。"""
        from oath_toolchain.core.exceptions import ToolNotFoundError
        with pytest.raises(ToolNotFoundError):
            self.engine.get_tool("nonexistent_tool")

    def test_list_tools_empty(self):
        """测试空工具列表。"""
        tools = self.engine.list_tools()
        assert isinstance(tools, list)

    def test_list_tools_with_registered(self):
        """测试列出已注册工具。"""
        tool = MockTool()
        self.engine.register_tool(tool)
        tools = self.engine.list_tools()
        assert len(tools) >= 1
        names = [t["name"] for t in tools]
        assert "mock_tool" in names

    def test_create_pipeline_simple(self):
        """测试创建简单管道。"""
        steps = [
            {
                "name": "step1",
                "tool": "mock_tool",
                "action": "test_action",
                "output_key": "step1_output",
            },
        ]
        pipeline = self.engine.create_pipeline("test_pipeline", steps)
        assert pipeline is not None
        assert pipeline.name == "test_pipeline"
        assert "test_pipeline" in self.engine.pipelines

    def test_create_pipeline_empty_name(self):
        """测试创建空名称的管道。"""
        with pytest.raises(ValidationError, match="名称"):
            self.engine.create_pipeline("", [{"name": "step1", "tool": "t", "action": "a"}])

    def test_create_pipeline_empty_steps(self):
        """测试创建空步骤的管道。"""
        with pytest.raises(ValidationError, match="步骤"):
            self.engine.create_pipeline("test", [])

    def test_create_pipeline_invalid_steps(self):
        """测试创建无效步骤的管道。"""
        invalid_steps = [{"name": "", "tool": "", "action": ""}]
        with pytest.raises(ValidationError):
            self.engine.create_pipeline("invalid", invalid_steps)

    def test_execute_pipeline(self):
        """测试执行管道。"""
        tool = MockTool()
        self.engine.register_tool(tool)

        steps = [
            {
                "name": "step1",
                "tool": "mock_tool",
                "action": "test_action",
                "output_key": "step1_output",
            },
        ]
        self.engine.create_pipeline("test_pipe", steps)
        result = self.engine.execute_pipeline("test_pipe", "test_input")

        assert result["success"] is True
        assert result["pipeline"] == "test_pipe"
        assert result["steps_executed"] == 1
        assert tool.call_count == 1

    def test_execute_pipeline_not_found(self):
        """测试执行不存在的管道。"""
        with pytest.raises(ValidationError, match="不存在"):
            self.engine.execute_pipeline("nonexistent", "input")

    def test_create_workflow(self):
        """测试创建工作流。"""
        definition = {
            "name": "test_workflow",
            "nodes": [
                {"id": "node1", "type": "set_variable", "variables": {"x": 1}},
            ],
            "edges": [],
        }
        workflow = self.engine.create_workflow("test_wf", definition)
        assert workflow is not None
        assert "test_wf" in self.engine.workflows

    def test_create_workflow_empty_name(self):
        """测试创建空名称的工作流。"""
        with pytest.raises(ValidationError, match="名称"):
            self.engine.create_workflow("", {"nodes": []})

    def test_create_workflow_empty_definition(self):
        """测试创建空定义的工作流。"""
        with pytest.raises(ValidationError, match="定义"):
            self.engine.create_workflow("test", {})

    def test_execute_workflow(self):
        """测试执行工作流。"""
        tool = MockTool()
        self.engine.register_tool(tool)

        definition = {
            "name": "test_wf",
            "nodes": [
                {"id": "start", "type": "tool", "tool": "mock_tool", "action": "wf_test", "output_key": "out"},
            ],
            "edges": [],
            "start_node": "start",
        }
        self.engine.create_workflow("test_wf", definition)
        result = self.engine.execute_workflow("test_wf", "input_data")

        assert result["success"] is True
        assert "workflow_id" in result

    def test_execute_workflow_not_found(self):
        """测试执行不存在的工作流。"""
        with pytest.raises(ValidationError, match="不存在"):
            self.engine.execute_workflow("nonexistent", "input")

    def test_get_security_report(self):
        """测试获取安全报告。"""
        report = self.engine.get_security_report()
        assert report is not None
        assert "pipelines" in report
        assert "workflows" in report
        assert "tools" in report
        assert report["engine"] == "qiankun"

    def test_default_pipelines_exist(self):
        """测试预置管道是否存在。"""
        assert "full_encryption" in self.engine.pipelines
        assert "stego_encrypt" in self.engine.pipelines
        assert "secure_dataset" in self.engine.pipelines

    def test_repr(self):
        """测试字符串表示。"""
        repr_str = repr(self.engine)
        assert "QiankunEngine" in repr_str

    def test_auto_register_tools(self):
        """测试自动注册工具。"""
        ToolRegistry.reset_instance()
        registry = ToolRegistry()
        registry.register(MockTool)

        engine = QiankunEngine(config={"auto_register_tools": True})
        tool_names = [t["name"] for t in engine.list_tools()]
        assert "mock_tool" in tool_names

    def test_get_tool_creates_instance(self):
        """测试获取工具时创建实例并缓存。"""
        ToolRegistry.reset_instance()
        registry = ToolRegistry()
        registry.register(MockTool)

        engine = QiankunEngine()
        tool1 = engine.get_tool("mock_tool")
        tool2 = engine.get_tool("mock_tool")
        assert tool1 is tool2

    def test_security_context_exists(self):
        """测试安全上下文存在。"""
        assert isinstance(self.engine.security_context, dict)
        assert len(self.engine.security_context) == 0

    def test_workflow_executor_exists(self):
        """测试工作流执行器存在。"""
        assert self.engine.workflow_executor is not None
        assert self.engine.workflow_executor.engine is self.engine

    def test_security_orchestrator_exists(self):
        """测试安全编排器存在。"""
        assert self.engine.security_orchestrator is not None
        assert self.engine.security_orchestrator.engine is self.engine
