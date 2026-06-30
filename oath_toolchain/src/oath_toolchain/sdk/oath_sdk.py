"""神誓工具链SDK主入口模块。

提供OathSDK类，是整个SDK的统一入口，整合所有子API模块。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..orchestration.qiankun_engine import QiankunEngine
from .crypto_api import CryptoAPI
from .key_api import KeyAPI
from .ca_api import CAAPI
from .stego_api import StegoAPI
from .dataset_api import DatasetAPI
from .pipeline_api import PipelineAPI


class OathSDK:
    """神誓工具链SDK主类。

    是整个SDK的统一入口，提供简洁易用的高层API，
    整合加密、密钥、CA证书、隐写、数据集、管道等功能模块。

    Attributes:
        engine: 乾坤引擎实例
        crypto: 加密API实例
        keys: 密钥API实例
        ca: CA证书API实例
        stego: 隐写API实例
        datasets: 数据集API实例
        pipelines: 管道API实例

    Examples:
        >>> sdk = OathSDK()
        >>> key = sdk.keys.generate_aes_key()
        >>> encrypted = sdk.crypto.encrypt_aes(b"hello", key)
        >>> decrypted = sdk.crypto.decrypt_aes(encrypted, key)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """初始化SDK。

        Args:
            config: 配置字典，可选，传递给乾坤引擎。
                支持的配置项：
                - auto_register_tools: 是否自动注册工具，默认False
                - default_security_profile: 默认安全配置文件
        """
        self.config = config or {}
        self.engine = QiankunEngine(config=self.config)

        self.crypto = CryptoAPI(self.engine)
        self.keys = KeyAPI(self.engine)
        self.ca = CAAPI(self.engine)
        self.stego = StegoAPI(self.engine)
        self.datasets = DatasetAPI(self.engine)
        self.pipelines = PipelineAPI(self.engine)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有已注册的工具。

        Returns:
            工具元数据列表，每个元素包含工具的名称、描述、版本等信息
        """
        return self.engine.list_tools()

    def execute_tool(
        self,
        tool_name: str,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行指定工具的指定操作。

        Args:
            tool_name: 工具名称
            action: 操作名称
            params: 参数字典

        Returns:
            执行结果字典

        Raises:
            ToolNotFoundError: 当工具不存在时
            ValidationError: 当参数验证失败时
        """
        tool = self.engine.get_tool(tool_name)
        execute_params = dict(params)
        execute_params["action"] = action
        return tool.execute(execute_params)

    def version(self) -> str:
        """获取SDK版本号。

        Returns:
            版本号字符串
        """
        from .. import __version__
        return __version__
