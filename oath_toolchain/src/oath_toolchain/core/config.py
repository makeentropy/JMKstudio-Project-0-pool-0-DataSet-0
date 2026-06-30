"""神誓工具链配置管理模块。

提供统一的配置管理功能，支持多种配置源和层级覆盖。
"""
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .exceptions import ConfigError


class ConfigSchema(BaseModel):
    """配置Schema基类。

    用于配置项的验证和类型转换。
    """

    model_config = ConfigDict(extra="allow")


class ConfigManager:
    """配置管理器。

    支持层级配置：默认值 -> 配置文件 -> 环境变量 -> 运行时设置。
    支持YAML和JSON格式的配置文件。

    Attributes:
        _defaults: 默认配置值
        _file_config: 从配置文件加载的配置
        _env_config: 从环境变量加载的配置
        _runtime_config: 运行时设置的配置
    """

    def __init__(
        self,
        defaults: Optional[dict[str, Any]] = None,
        env_prefix: str = "OATH_",
    ) -> None:
        """初始化配置管理器。

        Args:
            defaults: 默认配置值
            env_prefix: 环境变量前缀，默认为"OATH_"
        """
        self._defaults: dict[str, Any] = defaults or {}
        self._file_config: dict[str, Any] = {}
        self._env_config: dict[str, Any] = {}
        self._runtime_config: dict[str, Any] = {}
        self._env_prefix = env_prefix
        self._schema: Optional[type[ConfigSchema]] = None

    def set_schema(self, schema: type[ConfigSchema]) -> None:
        """设置配置验证Schema。

        Args:
            schema: Pydantic模型类，用于验证配置
        """
        self._schema = schema

    def load_from_file(self, config_path: str | Path) -> None:
        """从配置文件加载配置。

        支持YAML和JSON格式，根据文件扩展名自动判断。

        Args:
            config_path: 配置文件路径

        Raises:
            ConfigError: 当文件不存在或格式错误时
        """
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(
                message=f"配置文件不存在: {path}",
                details={"config_path": str(path)},
            )

        try:
            suffix = path.suffix.lower()
            if suffix in (".yaml", ".yml"):
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            elif suffix == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                raise ConfigError(
                    message=f"不支持的配置文件格式: {suffix}",
                    details={"supported_formats": [".yaml", ".yml", ".json"]},
                )

            if not isinstance(data, dict):
                raise ConfigError(message="配置文件内容必须是键值对格式")

            self._file_config = data
        except ConfigError:
            raise
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ConfigError(
                message=f"配置文件解析失败: {e}",
                details={"config_path": str(path)},
            ) from e
        except Exception as e:
            raise ConfigError(
                message=f"读取配置文件失败: {e}",
                details={"config_path": str(path)},
            ) from e

    def load_from_env(self) -> None:
        """从环境变量加载配置。

        环境变量名格式: {prefix}{KEY}，例如 OATH_LOG_LEVEL
        支持嵌套配置，使用双下划线分隔，例如 OATH_DATABASE__HOST
        """
        env_config: dict[str, Any] = {}

        for key, value in os.environ.items():
            if not key.startswith(self._env_prefix):
                continue

            config_key = key[len(self._env_prefix) :].lower()
            self._set_nested_value(env_config, config_key, value)

        self._env_config = env_config

    def _set_nested_value(
        self, config: dict[str, Any], key: str, value: str
    ) -> None:
        """设置嵌套配置值。

        Args:
            config: 配置字典
            key: 配置键，双下划线表示层级分隔
            value: 配置值
        """
        keys = key.split("__")
        current = config

        for i, k in enumerate(keys[:-1]):
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = self._parse_env_value(value)

    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值为合适的Python类型。

        Args:
            value: 环境变量字符串值

        Returns:
            解析后的值
        """
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        try:
            return int(value)
        except ValueError:
            pass

        try:
            return float(value)
        except ValueError:
            pass

        if value.startswith("[") and value.endswith("]"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        return value

    def set(self, key: str, value: Any) -> None:
        """运行时设置配置值。

        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split(".")
        current = self._runtime_config

        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。

        配置优先级：运行时设置 > 环境变量 > 配置文件 > 默认值

        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 当键不存在时的默认值

        Returns:
            配置值
        """
        keys = key.split(".")

        sources = [
            self._runtime_config,
            self._env_config,
            self._file_config,
            self._defaults,
        ]

        for source in sources:
            value = self._get_nested_value(source, keys)
            if value is not None:
                return value

        return default

    def _get_nested_value(
        self, config: dict[str, Any], keys: list[str]
    ) -> Optional[Any]:
        """获取嵌套配置值。

        Args:
            config: 配置字典
            keys: 键列表

        Returns:
            配置值，如果不存在则返回None
        """
        current = config
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def get_all(self) -> dict[str, Any]:
        """获取所有配置的合并结果。

        Returns:
            合并后的完整配置字典
        """
        result = deepcopy(self._defaults)
        self._deep_update(result, self._file_config)
        self._deep_update(result, self._env_config)
        self._deep_update(result, self._runtime_config)
        return result

    def _deep_update(
        self, base: dict[str, Any], update: dict[str, Any]
    ) -> None:
        """深度更新字典。

        Args:
            base: 基础字典，将被原地修改
            update: 用于更新的字典
        """
        for key, value in update.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_update(base[key], value)
            else:
                base[key] = deepcopy(value)

    def validate(self) -> bool:
        """验证当前配置是否符合Schema。

        Returns:
            如果验证通过返回True

        Raises:
            ConfigError: 当验证失败时
        """
        if self._schema is None:
            return True

        try:
            self._schema(**self.get_all())
            return True
        except ValidationError as e:
            errors = []
            for error in e.errors():
                loc = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{loc}: {error['msg']}")

            raise ConfigError(
                message="配置验证失败",
                details={"errors": errors},
            ) from e

    def reset(self) -> None:
        """重置所有配置。"""
        self._file_config = {}
        self._env_config = {}
        self._runtime_config = {}
