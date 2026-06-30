"""加密管道单元测试。"""
import pytest

from oath_toolchain.core.base import OathTool
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.orchestration import QiankunEngine, Pipeline, PipelineStep
from oath_toolchain.core.exceptions import OathToolchainError


class MockTool(OathTool):
    """测试用模拟工具。"""

    __test__ = False

    name: str = "mock_tool"
    description: str = "模拟测试工具"

    def execute(self, params: dict) -> dict:
        action = params.get("action", "default")
        value = params.get("value", 0)
        return {
            "success": True,
            "action": action,
            "result": value * 2 if isinstance(value, int) else value,
            "params": params,
        }


class AddTool(OathTool):
    """加法测试工具。"""

    __test__ = False

    name: str = "add_tool"
    description: str = "加法测试工具"

    def execute(self, params: dict) -> dict:
        action = params.get("action", "add")
        a = params.get("a", 0)
        b = params.get("b", 0)
        return {
            "success": True,
            "action": action,
            "result": a + b,
            "sum": a + b,
        }


class TestPipelineStep:
    """测试管道步骤数据类。"""

    def test_create_step(self):
        """测试创建步骤。"""
        step = PipelineStep(
            name="test_step",
            tool="mock_tool",
            action="test_action",
        )
        assert step.name == "test_step"
        assert step.tool == "mock_tool"
        assert step.action == "test_action"
        assert step.params == {}
        assert step.input_mapping == {}
        assert step.output_key == ""

    def test_create_step_with_params(self):
        """测试带参数创建步骤。"""
        step = PipelineStep(
            name="step2",
            tool="add_tool",
            action="add",
            params={"a": 1, "b": 2},
            input_mapping={"a": "results.step1.result"},
            output_key="step2_output",
        )
        assert step.params == {"a": 1, "b": 2}
        assert step.input_mapping == {"a": "results.step1.result"}
        assert step.output_key == "step2_output"


class TestPipeline:
    """测试加密管道。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.engine = QiankunEngine()
        self.mock_tool = MockTool()
        self.add_tool = AddTool()
        self.engine.register_tool(self.mock_tool)
        self.engine.register_tool(self.add_tool)

    def test_create_pipeline(self):
        """测试创建管道。"""
        steps = [
            PipelineStep(name="step1", tool="mock_tool", action="act1"),
            PipelineStep(name="step2", tool="mock_tool", action="act2"),
        ]
        pipeline = Pipeline("test_pipeline", steps)
        assert pipeline.name == "test_pipeline"
        assert len(pipeline.steps) == 2

    def test_validate_valid_pipeline(self):
        """测试验证有效管道。"""
        steps = [
            PipelineStep(name="step1", tool="mock_tool", action="act1"),
            PipelineStep(name="step2", tool="mock_tool", action="act2"),
        ]
        pipeline = Pipeline("test", steps)
        valid, errors = pipeline.validate()
        assert valid is True
        assert len(errors) == 0

    def test_validate_duplicate_names(self):
        """测试验证重复步骤名称。"""
        steps = [
            PipelineStep(name="step1", tool="mock_tool", action="act1"),
            PipelineStep(name="step1", tool="mock_tool", action="act2"),
        ]
        pipeline = Pipeline("test", steps)
        valid, errors = pipeline.validate()
        assert valid is False
        assert any("重复" in e for e in errors)

    def test_validate_missing_name(self):
        """测试验证缺少名称。"""
        steps = [
            PipelineStep(name="", tool="mock_tool", action="act1"),
        ]
        pipeline = Pipeline("test", steps)
        valid, errors = pipeline.validate()
        assert valid is False
        assert any("缺少名称" in e for e in errors)

    def test_validate_missing_tool(self):
        """测试验证缺少工具。"""
        steps = [
            PipelineStep(name="step1", tool="", action="act1"),
        ]
        pipeline = Pipeline("test", steps)
        valid, errors = pipeline.validate()
        assert valid is False
        assert any("缺少工具名称" in e for e in errors)

    def test_validate_missing_action(self):
        """测试验证缺少操作。"""
        steps = [
            PipelineStep(name="step1", tool="mock_tool", action=""),
        ]
        pipeline = Pipeline("test", steps)
        valid, errors = pipeline.validate()
        assert valid is False
        assert any("缺少操作类型" in e for e in errors)

    def test_execute_single_step(self):
        """测试执行单步管道。"""
        steps = [
            PipelineStep(
                name="step1",
                tool="mock_tool",
                action="test_action",
                params={"value": 5},
                output_key="step1_out",
            ),
        ]
        pipeline = Pipeline("single_step", steps)
        result = pipeline.execute(self.engine, "initial_input")

        assert result["success"] is True
        assert result["steps_executed"] == 1
        assert "step1_out" in result["context"]["results"]
        assert result["context"]["results"]["step1_out"]["result"] == 10

    def test_execute_multiple_steps(self):
        """测试执行多步管道。"""
        steps = [
            PipelineStep(
                name="step1",
                tool="mock_tool",
                action="first",
                params={"value": 3},
                output_key="s1",
            ),
            PipelineStep(
                name="step2",
                tool="mock_tool",
                action="second",
                params={"value": 7},
                output_key="s2",
            ),
        ]
        pipeline = Pipeline("multi_step", steps)
        result = pipeline.execute(self.engine, "input")

        assert result["success"] is True
        assert result["steps_executed"] == 2
        assert "s1" in result["context"]["results"]
        assert "s2" in result["context"]["results"]

    def test_execute_with_input_mapping(self):
        """测试带输入映射的管道执行。"""
        steps = [
            PipelineStep(
                name="step1",
                tool="add_tool",
                action="add",
                params={"a": 10, "b": 20},
                output_key="first_sum",
            ),
            PipelineStep(
                name="step2",
                tool="add_tool",
                action="add",
                params={"b": 5},
                input_mapping={"a": "results.first_sum.sum"},
                output_key="second_sum",
            ),
        ]
        pipeline = Pipeline("mapping_test", steps)
        result = pipeline.execute(self.engine, "start")

        assert result["success"] is True
        assert result["context"]["results"]["first_sum"]["sum"] == 30
        assert result["context"]["results"]["second_sum"]["sum"] == 35

    def test_execute_with_initial_input(self):
        """测试使用初始输入。"""
        steps = [
            PipelineStep(
                name="step1",
                tool="mock_tool",
                action="echo",
                input_mapping={"value": "initial_input"},
                output_key="out",
            ),
        ]
        pipeline = Pipeline("init_input", steps)
        result = pipeline.execute(self.engine, 42)

        assert result["success"] is True
        assert result["context"]["results"]["out"]["result"] == 84

    def test_execute_error_handling(self):
        """测试错误处理。"""

        class FailingTool(OathTool):
            __test__ = False
            name: str = "fail_tool"
            description: str = "失败工具"

            def execute(self, params: dict) -> dict:
                raise RuntimeError("故意失败")

        self.engine.register_tool(FailingTool())

        steps = [
            PipelineStep(name="good", tool="mock_tool", action="ok", output_key="g"),
            PipelineStep(name="bad", tool="fail_tool", action="fail", output_key="b"),
        ]
        pipeline = Pipeline("error_test", steps)

        with pytest.raises(OathToolchainError):
            pipeline.execute(self.engine, "input")

    def test_execute_last_output(self):
        """测试last_output设置。"""
        steps = [
            PipelineStep(name="s1", tool="mock_tool", action="a", params={"value": 1}),
            PipelineStep(name="s2", tool="mock_tool", action="b", params={"value": 2}),
        ]
        pipeline = Pipeline("last_out", steps)
        result = pipeline.execute(self.engine, "in")

        assert result["output"] is not None
        assert result["output"]["action"] == "b"

    def test_repr(self):
        """测试字符串表示。"""
        steps = [PipelineStep(name="s1", tool="t", action="a")]
        pipeline = Pipeline("test_repr", steps)
        repr_str = repr(pipeline)
        assert "Pipeline" in repr_str
        assert "test_repr" in repr_str

    def test_get_from_context_nested(self):
        """测试从嵌套上下文中获取值。"""
        steps = [
            PipelineStep(name="s1", tool="mock_tool", action="a", output_key="out"),
        ]
        pipeline = Pipeline("nested_test", steps)

        context = {
            "a": {"b": {"c": "deep_value"}},
            "results": {},
        }
        value = pipeline._get_from_context(context, "a.b.c")
        assert value == "deep_value"

    def test_get_from_context_missing(self):
        """测试获取不存在的键。"""
        pipeline = Pipeline("test", [])
        value = pipeline._get_from_context({}, "nonexistent.key")
        assert value is None
