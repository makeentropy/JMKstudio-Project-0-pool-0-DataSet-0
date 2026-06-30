"""加密管道模块。

提供基于步骤的加密管道执行机制，支持顺序执行多工具操作，
实现复杂加密流程的自动化编排。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..core.exceptions import ValidationError, OathToolchainError
from ..core.logging_util import get_logger

if TYPE_CHECKING:
    from .qiankun_engine import QiankunEngine

logger = get_logger("orchestration.pipeline")


@dataclass
class PipelineStep:
    """管道步骤数据类。

    定义管道中的单个执行步骤，包括工具名称、操作类型、参数映射等。

    Attributes:
        name: 步骤名称，用于标识和引用
        tool: 要调用的工具名称
        action: 工具的操作类型（action参数）
        params: 步骤的固定参数字典
        input_mapping: 输入映射，将上下文/上一步输出映射到本步输入
        output_key: 输出存储键名，用于保存到上下文中
    """

    name: str
    tool: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_key: str = ""


class Pipeline:
    """加密管道类。

    管理一系列按顺序执行的步骤，支持上下文传递和错误处理。
    每个步骤调用指定工具的指定操作，并将结果保存到上下文中。

    Attributes:
        name: 管道名称
        steps: 管道步骤列表
    """

    def __init__(self, name: str, steps: List[PipelineStep]) -> None:
        """初始化加密管道。

        Args:
            name: 管道名称
            steps: 管道步骤列表

        Raises:
            ValidationError: 当步骤配置无效时
        """
        self.name = name
        self.steps = steps
        self._logger = get_logger(f"pipeline.{name}")

    def execute(
        self,
        engine: "QiankunEngine",
        initial_input: Any,
    ) -> Dict[str, Any]:
        """执行管道。

        按顺序执行每一步，将初始输入和各步输出保存到上下文中，
        支持通过input_mapping进行数据传递。

        Args:
            engine: 乾坤引擎实例，用于获取和调用工具
            initial_input: 初始输入数据

        Returns:
            执行结果字典，包含：
            - success: 是否成功
            - pipeline: 管道名称
            - context: 完整的执行上下文
            - output: 最后一步的输出
            - steps_executed: 已执行的步骤数

        Raises:
            OathToolchainError: 当执行过程中出现错误时
        """
        context: Dict[str, Any] = {
            "initial_input": initial_input,
            "input": initial_input,
            "results": {},
        }

        steps_executed = 0
        last_output: Any = None

        try:
            for step in self.steps:
                self._logger.info(f"执行步骤: {step.name}")

                step_params = self._build_step_params(step, context)

                tool = engine.get_tool(step.tool)
                result = tool.execute(step_params)

                if step.output_key:
                    context["results"][step.output_key] = result
                    context[step.output_key] = result

                last_output = result
                context["last_output"] = result
                steps_executed += 1

                self._logger.debug(f"步骤 {step.name} 完成")

            return {
                "success": True,
                "pipeline": self.name,
                "context": context,
                "output": last_output,
                "steps_executed": steps_executed,
            }

        except Exception as e:
            self._logger.error(f"管道执行失败，步骤 {step.name}: {str(e)}")
            raise OathToolchainError(
                message=f"管道 '{self.name}' 执行失败，步骤 '{step.name}': {str(e)}",
                details={
                    "pipeline": self.name,
                    "failed_step": step.name,
                    "steps_executed": steps_executed,
                    "context": context,
                },
            ) from e

    def validate(self) -> Tuple[bool, List[str]]:
        """验证管道配置。

        检查管道配置的有效性，包括：
        - 步骤名称唯一性
        - 必填字段完整性
        - 输入映射引用有效性

        Returns:
            元组 (是否有效, 错误信息列表)
        """
        errors: List[str] = []
        step_names: set[str] = set()

        for i, step in enumerate(self.steps):
            if not step.name:
                errors.append(f"步骤 {i}: 缺少名称")
            elif step.name in step_names:
                errors.append(f"步骤 {i}: 名称重复 '{step.name}'")
            else:
                step_names.add(step.name)

            if not step.tool:
                errors.append(f"步骤 '{step.name}': 缺少工具名称")

            if not step.action:
                errors.append(f"步骤 '{step.name}': 缺少操作类型")

        return len(errors) == 0, errors

    def _build_step_params(
        self,
        step: PipelineStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建步骤参数字典。

        合并固定参数和从上下文中映射的输入参数。

        Args:
            step: 管道步骤
            context: 执行上下文

        Returns:
            构建完成的参数字典
        """
        params: Dict[str, Any] = {"action": step.action}
        params.update(step.params)

        for param_name, context_key in step.input_mapping.items():
            value = self._get_from_context(context, context_key)
            if value is not None:
                params[param_name] = value

        return params

    def _get_from_context(
        self,
        context: Dict[str, Any],
        key: str,
    ) -> Any:
        """从上下文中获取值。

        支持点号表示法访问嵌套字典，例如 "results.step1.output"。

        Args:
            context: 上下文字典
            key: 键名，支持点号嵌套

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

    def __repr__(self) -> str:
        """返回管道的字符串表示。"""
        return f"<Pipeline name='{self.name}' steps={len(self.steps)}>"
