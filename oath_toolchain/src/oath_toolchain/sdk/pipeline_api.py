"""管道API模块。

提供加密管道和工作流的高层API，包括管道执行、工作流创建、
配置文件加密解密等功能。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..orchestration.pipeline import Pipeline, PipelineStep


class PipelineAPI:
    """管道API类。

    提供加密管道和工作流的统一高层接口，包括管道执行、
    工作流创建、配置文件加密解密等功能。

    Attributes:
        engine: 乾坤引擎实例
    """

    def __init__(self, engine: Any) -> None:
        """初始化管道API。

        Args:
            engine: 乾坤引擎实例
        """
        self._engine = engine
        self._profiles: Dict[str, Dict[str, Any]] = {}

    def list_pipelines(self) -> List[Dict[str, Any]]:
        """列出所有已注册的管道。

        Returns:
            管道信息列表
        """
        pipelines = []
        for name, pipeline in self._engine.pipelines.items():
            pipelines.append({
                "name": name,
                "step_count": len(pipeline.steps),
                "steps": [step.name for step in pipeline.steps],
            })
        return pipelines

    def run_pipeline(
        self,
        name: str,
        input_data: Any,
    ) -> Dict[str, Any]:
        """执行指定的管道。

        Args:
            name: 管道名称
            input_data: 输入数据

        Returns:
            管道执行结果字典

        Raises:
            ValidationError: 当管道不存在时
        """
        return self._engine.execute_pipeline(name, input_data)

    def create_pipeline(
        self,
        name: str,
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """创建新的加密管道。

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
            管道信息字典
        """
        pipeline = self._engine.create_pipeline(name, steps)
        return {
            "name": pipeline.name,
            "step_count": len(pipeline.steps),
            "steps": [step.name for step in pipeline.steps],
        }

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
            工作流信息字典
        """
        workflow = self._engine.create_workflow(name, definition)
        return workflow

    def run_workflow(
        self,
        name: str,
        input_data: Any,
    ) -> Dict[str, Any]:
        """执行工作流。

        Args:
            name: 工作流名称
            input_data: 输入数据

        Returns:
            工作流执行结果字典

        Raises:
            ValidationError: 当工作流不存在时
        """
        return self._engine.execute_workflow(name, input_data)

    def encrypt_with_profile(
        self,
        profile_name: str,
        data: bytes,
    ) -> Dict[str, Any]:
        """使用配置文件加密数据。

        Args:
            profile_name: 配置文件名称
            data: 待加密的数据

        Returns:
            加密结果字典

        Raises:
            ValueError: 当配置文件不存在时
        """
        if profile_name not in self._profiles:
            raise ValueError(f"配置文件不存在: {profile_name}")

        profile = self._profiles[profile_name]
        from .crypto_api import CryptoAPI
        crypto = CryptoAPI(self._engine)
        return crypto.encrypt_full(data, profile)

    def decrypt_with_profile(
        self,
        profile_name: str,
        data: Dict[str, Any],
    ) -> bytes:
        """使用配置文件解密数据。

        Args:
            profile_name: 配置文件名称
            data: 加密数据字典

        Returns:
            解密后的明文数据

        Raises:
            ValueError: 当配置文件不存在时
        """
        if profile_name not in self._profiles:
            raise ValueError(f"配置文件不存在: {profile_name}")

        profile = self._profiles[profile_name]
        from .crypto_api import CryptoAPI
        crypto = CryptoAPI(self._engine)
        return crypto.decrypt_full(data, profile)

    def register_profile(
        self,
        profile_name: str,
        config: Dict[str, Any],
    ) -> None:
        """注册加密配置文件。

        Args:
            profile_name: 配置文件名称
            config: 加密配置字典
        """
        self._profiles[profile_name] = config
