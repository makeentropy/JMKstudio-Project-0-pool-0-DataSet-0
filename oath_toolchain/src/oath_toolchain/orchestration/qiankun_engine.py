"""乾坤程序引擎主模块。

乾坤程序统一加密引擎的核心入口，整合工具注册、管道执行、
工作流编排和安全编排等功能，提供统一的加密操作接口。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..core.base import OathTool
from ..core.registry import ToolRegistry
from ..core.exceptions import ValidationError, OathToolchainError
from ..core.logging_util import get_logger

from .pipeline import Pipeline, PipelineStep
from .workflow_executor import WorkflowExecutor
from .security_orchestrator import SecurityOrchestrator

if TYPE_CHECKING:
    pass

logger = get_logger("orchestration.qiankun")


class QiankunEngine:
    """乾坤程序引擎主类。

    乾坤程序统一加密引擎的核心，提供工具管理、管道执行、
    工作流编排和安全编排等功能，是整个加密编排层的入口。

    Attributes:
        tool_registry: 工具注册表实例
        pipelines: 已注册的管道字典
        workflows: 已注册的工作流字典
        security_context: 安全上下文
        workflow_executor: 工作流执行器实例
        security_orchestrator: 安全编排器实例
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """初始化乾坤引擎。

        Args:
            config: 配置字典，可选
                - auto_register_tools: 是否自动注册已发现的工具
                - default_security_profile: 默认安全配置文件
        """
        self.config = config or {}
        self.tool_registry = ToolRegistry()
        self.pipelines: Dict[str, Pipeline] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.security_context: Dict[str, Any] = {}
        self.workflow_executor = WorkflowExecutor(self)
        self.security_orchestrator = SecurityOrchestrator(self)
        self._tool_instances: Dict[str, OathTool] = {}
        self._logger = get_logger("qiankun_engine")

        self._register_default_pipelines()

        if self.config.get("auto_register_tools", False):
            self._auto_register_tools()

        self._logger.info("乾坤程序引擎初始化完成")

    def register_tool(self, tool: OathTool) -> None:
        """注册工具实例。

        Args:
            tool: 工具实例，必须是OathTool的子类实例

        Raises:
            TypeError: 当tool不是OathTool实例时
            ValueError: 当工具名称已存在时
        """
        if not isinstance(tool, OathTool):
            raise TypeError(f"工具必须是OathTool的实例，收到: {type(tool)}")

        tool_name = tool.name
        if tool_name in self._tool_instances:
            raise ValueError(f"工具名称 '{tool_name}' 已存在")

        self._tool_instances[tool_name] = tool
        self._logger.info(f"工具已注册: {tool_name}")

    def get_tool(self, tool_name: str) -> OathTool:
        """获取工具实例。

        优先返回已注册的实例，不存在则尝试从注册表创建。

        Args:
            tool_name: 工具名称

        Returns:
            工具实例

        Raises:
            ToolNotFoundError: 当工具不存在时
        """
        if tool_name in self._tool_instances:
            return self._tool_instances[tool_name]

        if self.tool_registry.has_tool(tool_name):
            tool = self.tool_registry.create_tool(tool_name)
            self._tool_instances[tool_name] = tool
            return tool

        from ..core.exceptions import ToolNotFoundError
        raise ToolNotFoundError(tool_name=tool_name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有已注册的工具。

        Returns:
            工具元数据列表
        """
        result: List[Dict[str, Any]] = []

        for tool_name, tool in self._tool_instances.items():
            result.append(tool.metadata)

        for tool_name in self.tool_registry.list_tools():
            if tool_name not in self._tool_instances:
                try:
                    tool_class = self.tool_registry.get_tool(tool_name)
                    temp_instance = tool_class.__new__(tool_class)
                    from ..core.logging_util import get_logger
                    temp_instance._logger = get_logger(f"tools.{tool_name}")
                    result.append({
                        "name": temp_instance.name,
                        "description": temp_instance.description,
                        "version": temp_instance.version,
                        "author": temp_instance.author,
                        "tags": temp_instance.tags,
                        "category": temp_instance.category,
                    })
                except Exception:
                    result.append({"name": tool_name, "error": "无法获取元数据"})

        return result

    def create_pipeline(
        self,
        name: str,
        steps: List[Dict[str, Any]],
    ) -> Pipeline:
        """创建加密管道。

        Args:
            name: 管道名称
            steps: 步骤定义列表，每个步骤包含：
                - name: 步骤名称
                - tool: 工具名称
                - action: 操作类型
                - params: 参数字典（可选）
                - input_mapping: 输入映射（可选）
                - output_key: 输出键名（可选）

        Returns:
            创建的管道实例

        Raises:
            ValidationError: 当管道配置无效时
        """
        if not name:
            raise ValidationError(
                field="name",
                message="管道名称不能为空",
            )

        if not steps:
            raise ValidationError(
                field="steps",
                message="管道步骤不能为空",
            )

        pipeline_steps: List[PipelineStep] = []
        for step_def in steps:
            step = PipelineStep(
                name=step_def.get("name", ""),
                tool=step_def.get("tool", ""),
                action=step_def.get("action", ""),
                params=step_def.get("params", {}),
                input_mapping=step_def.get("input_mapping", {}),
                output_key=step_def.get("output_key", ""),
            )
            pipeline_steps.append(step)

        pipeline = Pipeline(name, pipeline_steps)

        valid, errors = pipeline.validate()
        if not valid:
            raise ValidationError(
                field="steps",
                message=f"管道配置无效: {'; '.join(errors)}",
                details={"errors": errors},
            )

        self.pipelines[name] = pipeline
        self._logger.info(f"创建管道: {name} ({len(steps)}步)")

        return pipeline

    def execute_pipeline(
        self,
        pipeline_name: str,
        input_data: Any,
    ) -> Dict[str, Any]:
        """执行管道。

        Args:
            pipeline_name: 管道名称
            input_data: 输入数据

        Returns:
            执行结果字典

        Raises:
            ValidationError: 当管道不存在时
        """
        if pipeline_name not in self.pipelines:
            raise ValidationError(
                field="pipeline_name",
                message=f"管道不存在: {pipeline_name}",
            )

        pipeline = self.pipelines[pipeline_name]
        self._logger.info(f"执行管道: {pipeline_name}")

        return pipeline.execute(self, input_data)

    def create_workflow(
        self,
        name: str,
        definition: Dict[str, Any],
    ) -> Dict[str, Any]:
        """创建工作流。

        Args:
            name: 工作流名称
            definition: 工作流定义

        Returns:
            创建的工作流信息

        Raises:
            ValidationError: 当工作流定义无效时
        """
        if not name:
            raise ValidationError(
                field="name",
                message="工作流名称不能为空",
            )

        if not definition:
            raise ValidationError(
                field="definition",
                message="工作流定义不能为空",
            )

        workflow = {
            "name": name,
            "definition": definition,
        }

        self.workflows[name] = workflow
        self._logger.info(f"创建工作流: {name}")

        return workflow

    def execute_workflow(
        self,
        workflow_name: str,
        input_data: Any,
    ) -> Dict[str, Any]:
        """执行工作流。

        Args:
            workflow_name: 工作流名称
            input_data: 输入数据

        Returns:
            执行结果字典

        Raises:
            ValidationError: 当工作流不存在时
        """
        if workflow_name not in self.workflows:
            raise ValidationError(
                field="workflow_name",
                message=f"工作流不存在: {workflow_name}",
            )

        workflow = self.workflows[workflow_name]
        self._logger.info(f"执行工作流: {workflow_name}")

        return self.workflow_executor.execute_workflow(
            workflow["definition"],
            input_data,
        )

    def get_security_report(self) -> Dict[str, Any]:
        """获取安全报告。

        Returns:
            安全报告字典，包含：
            - pipelines: 已注册的管道列表
            - workflows: 已注册的工作流列表
            - tools: 已注册的工具列表
            - security_profiles: 安全配置文件列表
            - security_context: 安全上下文摘要
        """
        security_report = self.security_orchestrator.get_security_report()

        return {
            "engine": "qiankun",
            "version": "1.0.0",
            "pipelines": list(self.pipelines.keys()),
            "pipeline_count": len(self.pipelines),
            "workflows": list(self.workflows.keys()),
            "workflow_count": len(self.workflows),
            "tools": [t.get("name", "") for t in self.list_tools()],
            "tool_count": len(self.list_tools()),
            "security_profiles": security_report.get("profiles", []),
            "supported_layers": security_report.get("supported_layers", []),
            "security_context_keys": list(self.security_context.keys()),
        }

    def _register_default_pipelines(self) -> None:
        """注册预置管道。"""
        self._register_full_encryption_pipeline()
        self._register_stego_encrypt_pipeline()
        self._register_secure_dataset_pipeline()

    def _register_full_encryption_pipeline(self) -> None:
        """注册完整加密管道。

        管道流程: NLP密钥生成 → KARMACA空间加密 → AES加密 → 几何证明 → 证书签名
        """
        try:
            self.pipelines["full_encryption"] = Pipeline(
                name="full_encryption",
                steps=[
                    PipelineStep(
                        name="generate_key",
                        tool="geometric_proof",
                        action="hash",
                        params={"dimensions": 4, "hash_alg": "sha256"},
                        input_mapping={"data": "input"},
                        output_key="key_hash",
                    ),
                    PipelineStep(
                        name="geometric_prove",
                        tool="geometric_proof",
                        action="prove",
                        params={"dimensions": 4, "num_proof_points": 8},
                        input_mapping={"data": "input"},
                        output_key="proof",
                    ),
                ],
            )
            self._logger.debug("预置管道已注册: full_encryption")
        except Exception as e:
            self._logger.warning(f"预置管道注册失败 (full_encryption): {e}")

    def _register_stego_encrypt_pipeline(self) -> None:
        """注册隐写加密管道。

        管道流程: 加密 → XOR隐写 → 文本隐写
        """
        try:
            self.pipelines["stego_encrypt"] = Pipeline(
                name="stego_encrypt",
                steps=[
                    PipelineStep(
                        name="xor_embed",
                        tool="steganography",
                        action="xor_embed",
                        input_mapping={
                            "secret_data": "input.secret_data",
                            "carrier_data": "input.carrier_data",
                        },
                        output_key="xor_stego",
                    ),
                ],
            )
            self._logger.debug("预置管道已注册: stego_encrypt")
        except Exception as e:
            self._logger.warning(f"预置管道注册失败 (stego_encrypt): {e}")

    def _register_secure_dataset_pipeline(self) -> None:
        """注册安全数据集管道。

        管道流程: 数据集创建 → Karma标签 → CA签名 → 版本提交
        """
        try:
            self.pipelines["secure_dataset"] = Pipeline(
                name="secure_dataset",
                steps=[
                    PipelineStep(
                        name="create_dataset",
                        tool="dataset_pool",
                        action="create",
                        input_mapping={"name": "input.name"},
                        output_key="dataset",
                    ),
                ],
            )
            self._logger.debug("预置管道已注册: secure_dataset")
        except Exception as e:
            self._logger.warning(f"预置管道注册失败 (secure_dataset): {e}")

    def _auto_register_tools(self) -> None:
        """自动注册已发现的工具。"""
        try:
            tool_names = self.tool_registry.list_tools()
            for tool_name in tool_names:
                if tool_name not in self._tool_instances:
                    try:
                        tool = self.tool_registry.create_tool(tool_name)
                        self._tool_instances[tool_name] = tool
                        self._logger.debug(f"自动注册工具: {tool_name}")
                    except Exception as e:
                        self._logger.warning(f"工具自动注册失败 ({tool_name}): {e}")
        except Exception as e:
            self._logger.warning(f"自动注册工具失败: {e}")

    def __repr__(self) -> str:
        """返回引擎的字符串表示。"""
        return (
            f"<QiankunEngine "
            f"tools={len(self._tool_instances)} "
            f"pipelines={len(self.pipelines)} "
            f"workflows={len(self.workflows)}>"
        )
