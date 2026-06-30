"""工作流执行器单元测试。"""
import pytest

from oath_toolchain.core.base import OathTool
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.orchestration import QiankunEngine, WorkflowExecutor
from oath_toolchain.core.exceptions import ValidationError


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
            "result": value,
            "doubled": value * 2 if isinstance(value, int) else value,
        }


class TestWorkflowExecutor:
    """测试工作流执行器。"""

    def setup_method(self):
        """每个测试前的准备工作。"""
        ToolRegistry.reset_instance()
        self.engine = QiankunEngine()
        self.mock_tool = MockTool()
        self.engine.register_tool(self.mock_tool)
        self.executor = WorkflowExecutor(self.engine)

    def test_init(self):
        """测试初始化。"""
        assert self.executor.engine is self.engine
        assert isinstance(self.executor._workflows, dict)

    def test_execute_workflow_simple(self):
        """测试执行简单工作流。"""
        definition = {
            "name": "simple_wf",
            "nodes": [
                {
                    "id": "node1",
                    "type": "tool",
                    "tool": "mock_tool",
                    "action": "test",
                    "params": {"value": 42},
                    "output_key": "out1",
                },
            ],
            "edges": [],
            "start_node": "node1",
        }
        result = self.executor.execute_workflow(definition, "input")
        assert result["success"] is True
        assert "workflow_id" in result

    def test_execute_workflow_no_nodes(self):
        """测试无节点工作流。"""
        definition = {
            "name": "empty_wf",
            "nodes": [],
            "edges": [],
        }
        with pytest.raises(ValidationError, match="没有节点"):
            self.executor.execute_workflow(definition, "input")

    def test_execute_workflow_node_no_id(self):
        """测试无ID节点。"""
        definition = {
            "name": "bad_wf",
            "nodes": [{"type": "tool", "tool": "mock_tool"}],
            "edges": [],
        }
        with pytest.raises(ValidationError, match="缺少id"):
            self.executor.execute_workflow(definition, "input")

    def test_execute_workflow_invalid_start_node(self):
        """测试无效起始节点。"""
        definition = {
            "name": "bad_start",
            "nodes": [{"id": "n1", "type": "tool", "tool": "mock_tool", "action": "a"}],
            "edges": [],
            "start_node": "nonexistent",
        }
        with pytest.raises(ValidationError, match="起始节点不存在"):
            self.executor.execute_workflow(definition, "input")

    def test_execute_node_tool_type(self):
        """测试执行工具类型节点。"""
        node = {
            "id": "t1",
            "type": "tool",
            "tool": "mock_tool",
            "action": "tool_action",
            "params": {"value": 10},
            "output_key": "tool_out",
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.execute_node(node, context)
        assert result["success"] is True
        assert result["action"] == "tool_action"
        assert context["variables"]["tool_out"]["result"] == 10

    def test_execute_node_set_variable(self):
        """测试设置变量节点。"""
        node = {
            "id": "sv1",
            "type": "set_variable",
            "variables": {"x": 100, "y": "hello"},
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.execute_node(node, context)
        assert result["success"] is True
        assert context["variables"]["x"] == 100
        assert context["variables"]["y"] == "hello"

    def test_execute_node_end(self):
        """测试结束节点。"""
        node = {"id": "end1", "type": "end"}
        context = {"results": {}, "variables": {}, "last_output": "final_result"}
        result = self.executor.execute_node(node, context)
        assert result["success"] is True
        assert result["type"] == "end"

    def test_execute_node_invalid_type(self):
        """测试无效节点类型。"""
        node = {"id": "bad", "type": "invalid_type"}
        context = {"results": {}, "variables": {}}
        with pytest.raises(ValidationError, match="不支持的节点类型"):
            self.executor.execute_node(node, context)

    def test_handle_branch_true(self):
        """测试条件分支为真。"""
        context = {"variables": {"x": 10}}
        result = self.executor.handle_branch("true", context)
        assert result is True

    def test_handle_branch_false(self):
        """测试条件分支为假。"""
        context = {"variables": {"x": 10}}
        result = self.executor.handle_branch("false", context)
        assert result is False

    def test_handle_branch_comparison(self):
        """测试比较条件。"""
        context = {"variables": {"x": 10}}
        assert self.executor.handle_branch("x == 10", context) is True
        assert self.executor.handle_branch("x > 5", context) is True
        assert self.executor.handle_branch("x < 5", context) is False
        assert self.executor.handle_branch("x != 5", context) is True

    def test_handle_branch_and_or(self):
        """测试逻辑与/或。"""
        context = {"variables": {"x": 10, "y": 20}}
        assert self.executor.handle_branch("x == 10 and y == 20", context) is True
        assert self.executor.handle_branch("x == 10 and y == 0", context) is False
        assert self.executor.handle_branch("x == 0 or y == 20", context) is True
        assert self.executor.handle_branch("x == 0 or y == 0", context) is False

    def test_handle_branch_not(self):
        """测试逻辑非。"""
        context = {"variables": {}}
        assert self.executor.handle_branch("not false", context) is True
        assert self.executor.handle_branch("not true", context) is False

    def test_handle_loop_count(self):
        """测试计数循环。"""
        loop_def = {
            "loop_type": "count",
            "count": 3,
            "body": [
                {"type": "set_variable", "variables": {"counter": "loop_index"}},
            ],
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.handle_loop(loop_def, context)
        assert result["success"] is True
        assert result["iterations"] == 3

    def test_handle_loop_while(self):
        """测试while循环。"""
        loop_def = {
            "loop_type": "while",
            "condition": "false",
            "body": [],
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.handle_loop(loop_def, context)
        assert result["success"] is True
        assert result["iterations"] == 0

    def test_handle_parallel(self):
        """测试并行执行。"""
        parallel_def = {
            "branches": [
                {"name": "b1", "nodes": [{"type": "set_variable", "variables": {"a": 1}}]},
                {"name": "b2", "nodes": [{"type": "set_variable", "variables": {"b": 2}}]},
            ],
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.handle_parallel(parallel_def, context)
        assert result["success"] is True
        assert result["branch_count"] == 2
        assert "b1" in result["results"]
        assert "b2" in result["results"]

    def test_get_workflow_status(self):
        """测试获取工作流状态。"""
        definition = {
            "name": "status_test",
            "nodes": [{"id": "n1", "type": "end"}],
            "edges": [],
        }
        result = self.executor.execute_workflow(definition, "in")
        wf_id = result["workflow_id"]

        status = self.executor.get_workflow_status(wf_id)
        assert status["workflow_id"] == wf_id
        assert status["status"] == "completed"

    def test_get_workflow_status_not_found(self):
        """测试获取不存在的工作流状态。"""
        with pytest.raises(ValidationError, match="不存在"):
            self.executor.get_workflow_status("nonexistent_id")

    def test_workflow_with_edges(self):
        """测试带边的工作流。"""
        definition = {
            "name": "edge_test",
            "nodes": [
                {"id": "n1", "type": "set_variable", "variables": {"x": 1}},
                {"id": "n2", "type": "set_variable", "variables": {"y": 2}},
                {"id": "n3", "type": "end"},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
            ],
            "start_node": "n1",
        }
        result = self.executor.execute_workflow(definition, "in")
        assert result["success"] is True

    def test_condition_node_evaluation(self):
        """测试条件节点评估。"""
        node = {
            "id": "cond1",
            "type": "condition",
            "condition": "true",
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.execute_node(node, context)
        assert result["condition_result"] is True

    def test_loop_node_execution(self):
        """测试循环节点执行。"""
        node = {
            "id": "loop1",
            "type": "loop",
            "loop_type": "count",
            "count": 2,
            "body": [],
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.execute_node(node, context)
        assert result["type"] == "loop"
        assert result["iterations"] == 2

    def test_parallel_node_execution(self):
        """测试并行节点执行。"""
        node = {
            "id": "par1",
            "type": "parallel",
            "branches": [
                {"name": "b1", "nodes": []},
            ],
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.execute_node(node, context)
        assert result["type"] == "parallel"
        assert result["branch_count"] == 1

    def test_workflow_with_condition_branch(self):
        """测试带条件分支的工作流。"""
        definition = {
            "name": "cond_wf",
            "nodes": [
                {"id": "start", "type": "set_variable", "variables": {"x": 10}},
                {"id": "cond", "type": "condition", "condition": "x == 10",
                 "true_branch": "true_node", "false_branch": "false_node"},
                {"id": "true_node", "type": "set_variable", "variables": {"result": "yes"}},
                {"id": "false_node", "type": "set_variable", "variables": {"result": "no"}},
            ],
            "edges": [
                {"source": "start", "target": "cond"},
            ],
            "start_node": "start",
        }
        result = self.executor.execute_workflow(definition, "input")
        assert result["success"] is True
        assert result["context"]["variables"]["x"] == 10
        assert result["context"]["results"]["cond"]["condition_result"] is True
        assert result["context"]["results"]["true_node"] is not None
        assert result["context"]["variables"]["result"] == "yes"

    def test_resolve_value_string_literal(self):
        """测试解析字符串字面量。"""
        context = {"results": {}, "variables": {}}
        val = self.executor._resolve_value('"hello world"', context)
        assert val == "hello world"

    def test_resolve_value_numeric(self):
        """测试解析数值。"""
        context = {"results": {}, "variables": {}}
        assert self.executor._resolve_value("42", context) == 42
        assert self.executor._resolve_value("3.14", context) == 3.14

    def test_resolve_value_boolean(self):
        """测试解析布尔值。"""
        context = {"results": {}, "variables": {}}
        assert self.executor._resolve_value("true", context) is True
        assert self.executor._resolve_value("false", context) is False
        assert self.executor._resolve_value("none", context) is None

    def test_compare_values(self):
        """测试值比较。"""
        assert self.executor._compare_values(10, 10, "==") is True
        assert self.executor._compare_values(10, 5, "!=") is True
        assert self.executor._compare_values(10, 5, ">") is True
        assert self.executor._compare_values(5, 10, "<") is True
        assert self.executor._compare_values(10, 10, ">=") is True
        assert self.executor._compare_values(5, 10, "<=") is True
        assert self.executor._compare_values("a", "b", ">") is False

    def test_while_loop_max_iterations(self):
        """测试while循环的最大迭代次数限制。"""
        loop_def = {
            "loop_type": "while",
            "condition": "true",
            "max_iterations": 5,
            "body": [],
        }
        context = {"results": {}, "variables": {}}
        result = self.executor.handle_loop(loop_def, context)
        assert result["iterations"] == 5

    def test_get_from_context_nested(self):
        """测试从嵌套上下文中获取值。"""
        context = {"a": {"b": {"c": "deep"}}}
        val = self.executor._get_from_context(context, "a.b.c")
        assert val == "deep"

    def test_get_from_context_missing(self):
        """测试获取不存在的值。"""
        val = self.executor._get_from_context({}, "a.b.c")
        assert val is None

    def test_tool_node_missing_tool(self):
        """测试工具节点缺少工具名称。"""
        node = {"id": "t1", "type": "tool", "action": "test"}
        context = {"results": {}, "variables": {}}
        with pytest.raises(ValidationError, match="缺少tool字段"):
            self.executor.execute_node(node, context)

    def test_end_node_with_output_key(self):
        """测试带输出键的结束节点。"""
        node = {"id": "end1", "type": "end", "output": "variables.x"}
        context = {"results": {}, "variables": {"x": "final_value"}, "last_output": "last"}
        result = self.executor.execute_node(node, context)
        assert result["output"] == "final_value"
