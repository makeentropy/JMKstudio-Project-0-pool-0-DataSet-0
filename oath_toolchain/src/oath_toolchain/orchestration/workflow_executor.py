"""工作流执行器模块。

提供支持条件分支、循环、并行执行的工作流引擎，
实现复杂加密业务流程的自动化编排。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..core.exceptions import ValidationError, OathToolchainError
from ..core.logging_util import get_logger

if TYPE_CHECKING:
    from .qiankun_engine import QiankunEngine

logger = get_logger("orchestration.workflow")


class WorkflowExecutor:
    """工作流执行器。

    支持条件分支、循环、并行执行等多种控制流结构，
    提供灵活的工作流定义和执行能力。

    Attributes:
        engine: 乾坤引擎实例
        _workflows: 工作流状态存储
    """

    def __init__(self, engine: "QiankunEngine") -> None:
        """初始化工作流执行器。

        Args:
            engine: 乾坤引擎实例
        """
        self.engine = engine
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._logger = get_logger("workflow_executor")

    def execute_workflow(
        self,
        definition: Dict[str, Any],
        input_data: Any,
    ) -> Dict[str, Any]:
        """执行工作流。

        根据工作流定义执行完整的工作流，支持条件分支、循环等控制流。

        Args:
            definition: 工作流定义字典
                - name: 工作流名称
                - nodes: 节点列表
                - start_node: 起始节点ID
            input_data: 输入数据

        Returns:
            执行结果字典，包含：
            - workflow_id: 工作流实例ID
            - success: 是否成功
            - output: 最终输出
            - context: 执行上下文

        Raises:
            ValidationError: 当工作流定义无效时
            OathToolchainError: 当执行失败时
        """
        workflow_id = str(uuid.uuid4())
        self._logger.info(f"开始执行工作流: {definition.get('name', 'unnamed')}")

        context: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "input": input_data,
            "initial_input": input_data,
            "results": {},
            "variables": {},
        }

        self._workflows[workflow_id] = {
            "definition": definition,
            "status": "running",
            "context": context,
            "current_node": None,
        }

        try:
            nodes = definition.get("nodes", [])
            if not nodes:
                raise ValidationError(
                    field="nodes",
                    message="工作流定义中没有节点",
                )

            node_map: Dict[str, Dict[str, Any]] = {}
            for node in nodes:
                node_id = node.get("id")
                if not node_id:
                    raise ValidationError(
                        field="nodes",
                        message="节点缺少id字段",
                    )
                node_map[node_id] = node

            edges = definition.get("edges", [])
            adjacency: Dict[str, List[str]] = {}
            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                if source and target:
                    if source not in adjacency:
                        adjacency[source] = []
                    adjacency[source].append(target)

            start_node_id = definition.get("start_node")
            if not start_node_id:
                start_node_id = nodes[0]["id"]

            if start_node_id not in node_map:
                raise ValidationError(
                    field="start_node",
                    message=f"起始节点不存在: {start_node_id}",
                )

            result = self._execute_node_recursive(
                start_node_id,
                node_map,
                adjacency,
                context,
            )

            self._workflows[workflow_id]["status"] = "completed"
            self._workflows[workflow_id]["output"] = result

            return {
                "workflow_id": workflow_id,
                "success": True,
                "output": result,
                "context": context,
            }

        except Exception as e:
            self._workflows[workflow_id]["status"] = "failed"
            self._workflows[workflow_id]["error"] = str(e)
            self._logger.error(f"工作流执行失败: {str(e)}")
            raise

    def execute_node(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行单个节点。

        根据节点类型执行不同的操作。

        Args:
            node: 节点定义
            context: 执行上下文

        Returns:
            节点执行结果

        Raises:
            ValidationError: 当节点类型不支持时
        """
        node_type = node.get("type", "tool")

        if node_type == "tool":
            return self._handle_tool_node(node, context)
        elif node_type == "condition":
            return self._handle_condition_node(node, context)
        elif node_type == "loop":
            return self._handle_loop_node(node, context)
        elif node_type == "parallel":
            return self._handle_parallel_node(node, context)
        elif node_type == "set_variable":
            return self._handle_set_variable_node(node, context)
        elif node_type == "end":
            return self._handle_end_node(node, context)
        else:
            raise ValidationError(
                field="type",
                message=f"不支持的节点类型: {node_type}",
            )

    def handle_branch(
        self,
        condition: str,
        context: Dict[str, Any],
    ) -> bool:
        """处理条件分支判断。

        评估条件表达式，支持简单的变量比较和逻辑运算。

        Args:
            condition: 条件表达式字符串
            context: 执行上下文

        Returns:
            条件是否成立
        """
        return self._evaluate_condition(condition, context)

    def handle_loop(
        self,
        loop_def: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理循环执行。

        Args:
            loop_def: 循环定义
            context: 执行上下文

        Returns:
            循环执行结果
        """
        loop_type = loop_def.get("loop_type", "count")
        results: List[Any] = []
        iterations = 0

        if loop_type == "count":
            count = loop_def.get("count", 0)
            body = loop_def.get("body", [])
            for i in range(count):
                context["variables"]["loop_index"] = i
                for node in body:
                    result = self.execute_node(node, context)
                    results.append(result)
                iterations += 1
        elif loop_type == "while":
            condition = loop_def.get("condition", "false")
            body = loop_def.get("body", [])
            max_iterations = loop_def.get("max_iterations", 1000)
            while self._evaluate_condition(condition, context):
                if iterations >= max_iterations:
                    break
                for node in body:
                    result = self.execute_node(node, context)
                    results.append(result)
                iterations += 1

        return {
            "success": True,
            "type": "loop",
            "iterations": iterations,
            "results": results,
        }

    def handle_parallel(
        self,
        parallel_def: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理并行执行。

        注意：当前实现为顺序模拟并行，保持结果一致性。

        Args:
            parallel_def: 并行定义
            context: 执行上下文

        Returns:
            并行执行结果
        """
        branches = parallel_def.get("branches", [])
        results: Dict[str, Any] = {}

        for i, branch in enumerate(branches):
            branch_name = branch.get("name", f"branch_{i}")
            branch_nodes = branch.get("nodes", [])
            branch_results = []
            for node in branch_nodes:
                result = self.execute_node(node, context)
                branch_results.append(result)
            results[branch_name] = branch_results

        return {
            "success": True,
            "type": "parallel",
            "branch_count": len(branches),
            "results": results,
        }

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流状态。

        Args:
            workflow_id: 工作流实例ID

        Returns:
            工作流状态信息

        Raises:
            ValidationError: 当工作流不存在时
        """
        if workflow_id not in self._workflows:
            raise ValidationError(
                field="workflow_id",
                message=f"工作流不存在: {workflow_id}",
            )

        workflow = self._workflows[workflow_id]
        return {
            "workflow_id": workflow_id,
            "status": workflow["status"],
            "definition": workflow["definition"],
            "current_node": workflow.get("current_node"),
            "error": workflow.get("error"),
        }

    def _execute_node_recursive(
        self,
        node_id: str,
        node_map: Dict[str, Dict[str, Any]],
        adjacency: Dict[str, List[str]],
        context: Dict[str, Any],
    ) -> Any:
        """递归执行节点及其后续节点。

        Args:
            node_id: 当前节点ID
            node_map: 节点映射表
            adjacency: 邻接表
            context: 执行上下文

        Returns:
            最终执行结果
        """
        if node_id not in node_map:
            return None

        node = node_map[node_id]
        context["current_node"] = node_id

        result = self.execute_node(node, context)

        context["results"][node_id] = result

        next_nodes = adjacency.get(node_id, [])

        if node.get("type") == "condition":
            condition_result = result.get("condition_result", False)
            if condition_result:
                next_node_id = node.get("true_branch")
            else:
                next_node_id = node.get("false_branch")
            if next_node_id:
                return self._execute_node_recursive(
                    next_node_id, node_map, adjacency, context
                )
            if not next_nodes:
                return result

        if not next_nodes:
            return result

        last_result = result
        for next_node_id in next_nodes:
            last_result = self._execute_node_recursive(
                next_node_id, node_map, adjacency, context
            )

        return last_result

    def _handle_tool_node(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理工具节点。

        Args:
            node: 节点定义
            context: 执行上下文

        Returns:
            工具执行结果
        """
        tool_name = node.get("tool")
        action = node.get("action")
        params = node.get("params", {})
        input_mapping = node.get("input_mapping", {})

        if not tool_name:
            raise ValidationError(
                field="tool",
                message="工具节点缺少tool字段",
            )

        execute_params: Dict[str, Any] = {"action": action} if action else {}
        execute_params.update(params)

        for param_name, context_key in input_mapping.items():
            value = self._get_from_context(context, context_key)
            if value is not None:
                execute_params[param_name] = value

        tool = self.engine.get_tool(tool_name)
        result = tool.execute(execute_params)

        output_key = node.get("output_key")
        if output_key:
            context["results"][output_key] = result
            context["variables"][output_key] = result

        return result

    def _handle_condition_node(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理条件节点。

        Args:
            node: 节点定义
            context: 执行上下文

        Returns:
            条件判断结果
        """
        condition = node.get("condition", "false")
        result = self._evaluate_condition(condition, context)

        return {
            "success": True,
            "type": "condition",
            "condition": condition,
            "condition_result": result,
        }

    def _handle_loop_node(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理循环节点。

        Args:
            node: 节点定义
            context: 执行上下文

        Returns:
            循环执行结果
        """
        return self.handle_loop(node, context)

    def _handle_parallel_node(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理并行节点。

        Args:
            node: 节点定义
            context: 执行上下文

        Returns:
            并行执行结果
        """
        return self.handle_parallel(node, context)

    def _handle_set_variable_node(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理设置变量节点。

        Args:
            node: 节点定义
            context: 执行上下文

        Returns:
            设置结果
        """
        variables = node.get("variables", {})
        for key, value in variables.items():
            context["variables"][key] = value

        return {
            "success": True,
            "type": "set_variable",
            "variables": dict(variables),
        }

    def _handle_end_node(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理结束节点。

        Args:
            node: 节点定义
            context: 执行上下文

        Returns:
            结束节点结果
        """
        output = node.get("output")
        if output:
            result = self._get_from_context(context, output)
        else:
            result = context.get("last_output")

        return {
            "success": True,
            "type": "end",
            "output": result,
        }

    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any],
    ) -> bool:
        """评估条件表达式。

        支持简单的条件表达式，例如：
        - "true" / "false"
        - "var == value"
        - "var != value"
        - "var > value"
        - "var < value"
        - "var >= value"
        - "var <= value"
        - "cond1 and cond2"
        - "cond1 or cond2"
        - "not cond"

        Args:
            condition: 条件表达式
            context: 执行上下文

        Returns:
            条件是否成立
        """
        condition = condition.strip()

        if condition.lower() == "true":
            return True
        if condition.lower() == "false":
            return False

        if condition.startswith("not "):
            return not self._evaluate_condition(condition[4:], context)

        or_parts = self._split_by_operator(condition, " or ")
        if len(or_parts) > 1:
            return any(self._evaluate_condition(part, context) for part in or_parts)

        and_parts = self._split_by_operator(condition, " and ")
        if len(and_parts) > 1:
            return all(self._evaluate_condition(part, context) for part in and_parts)

        operators = ["==", "!=", ">=", "<=", ">", "<"]
        for op in operators:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._resolve_value(left.strip(), context)
                right_val = self._resolve_value(right.strip(), context)
                return self._compare_values(left_val, right_val, op)

        val = self._resolve_value(condition, context)
        return bool(val)

    def _split_by_operator(self, expr: str, operator: str) -> List[str]:
        """按逻辑运算符分割表达式。

        Args:
            expr: 表达式字符串
            operator: 运算符

        Returns:
            分割后的部分列表
        """
        parts = []
        depth = 0
        current = ""
        i = 0
        while i < len(expr):
            if expr[i] == "(":
                depth += 1
                current += expr[i]
            elif expr[i] == ")":
                depth -= 1
                current += expr[i]
            elif depth == 0 and expr[i:i+len(operator)] == operator:
                parts.append(current.strip())
                current = ""
                i += len(operator) - 1
            else:
                current += expr[i]
            i += 1
        if current.strip():
            parts.append(current.strip())
        return parts

    def _resolve_value(self, expr: str, context: Dict[str, Any]) -> Any:
        """解析表达式的值。

        Args:
            expr: 表达式
            context: 上下文

        Returns:
            解析后的值
        """
        expr = expr.strip()

        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]
        if expr.startswith("'") and expr.endswith("'"):
            return expr[1:-1]

        try:
            return int(expr)
        except ValueError:
            pass

        try:
            return float(expr)
        except ValueError:
            pass

        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False
        if expr.lower() == "none" or expr.lower() == "null":
            return None

        val = self._get_from_context(context, expr)
        if val is not None:
            return val

        if "variables" in context:
            val = self._get_from_context(context["variables"], expr)
            if val is not None:
                return val

        return expr

    def _compare_values(self, left: Any, right: Any, op: str) -> bool:
        """比较两个值。

        Args:
            left: 左值
            right: 右值
            op: 比较运算符

        Returns:
            比较结果
        """
        try:
            if op == "==":
                return left == right
            elif op == "!=":
                return left != right
            elif op == ">":
                return left > right
            elif op == "<":
                return left < right
            elif op == ">=":
                return left >= right
            elif op == "<=":
                return left <= right
        except (TypeError, ValueError):
            return False
        return False

    def _get_from_context(self, context: Dict[str, Any], key: str) -> Any:
        """从上下文中获取值。

        支持点号表示法访问嵌套字典。

        Args:
            context: 上下文字典
            key: 键名

        Returns:
            找到的值，未找到返回None
        """
        parts = key.split(".")
        current: Any = context

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current
