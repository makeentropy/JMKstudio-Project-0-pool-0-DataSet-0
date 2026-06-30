"""配置管理单元测试。"""
import json
import os
from pathlib import Path

import pytest
import yaml

from oath_toolchain.core.config import ConfigManager, ConfigSchema
from oath_toolchain.core.exceptions import ConfigError


class TestConfigManager:
    """测试配置管理器。"""

    def setup_method(self):
        """每个测试前创建配置管理器。"""
        self.config = ConfigManager()

    def test_default_values(self):
        """测试默认值配置。"""
        defaults = {"key1": "value1", "nested": {"key2": "value2"}}
        config = ConfigManager(defaults=defaults)
        assert config.get("key1") == "value1"
        assert config.get("nested.key2") == "value2"

    def test_get_nonexistent_key_default(self):
        """测试获取不存在的键时返回默认值。"""
        assert self.config.get("nonexistent") is None
        assert self.config.get("nonexistent", "default_val") == "default_val"

    def test_runtime_set(self):
        """测试运行时设置配置。"""
        self.config.set("app.name", "TestApp")
        self.config.set("app.version", "1.0.0")
        assert self.config.get("app.name") == "TestApp"
        assert self.config.get("app.version") == "1.0.0"

    def test_config_priority(self):
        """测试配置优先级。

        运行时设置 > 环境变量 > 配置文件 > 默认值
        """
        defaults = {"level": "default"}
        config = ConfigManager(defaults=defaults, env_prefix="TEST_PRIORITY_")

        assert config.get("level") == "default"

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"level": "file"}, f)
            config_path = f.name

        try:
            config.load_from_file(config_path)
            assert config.get("level") == "file"

            os.environ["TEST_PRIORITY_LEVEL"] = "env"
            config.load_from_env()
            assert config.get("level") == "env"

            config.set("level", "runtime")
            assert config.get("level") == "runtime"
        finally:
            os.unlink(config_path)
            if "TEST_PRIORITY_LEVEL" in os.environ:
                del os.environ["TEST_PRIORITY_LEVEL"]

    def test_load_from_yaml_file(self, tmp_path):
        """测试从YAML文件加载配置。"""
        config_file = tmp_path / "config.yaml"
        yaml_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "test_db",
            },
            "log_level": "DEBUG",
        }
        with open(config_file, "w") as f:
            yaml.dump(yaml_data, f)

        self.config.load_from_file(config_file)
        assert self.config.get("database.host") == "localhost"
        assert self.config.get("database.port") == 5432
        assert self.config.get("log_level") == "DEBUG"

    def test_load_from_json_file(self, tmp_path):
        """测试从JSON文件加载配置。"""
        config_file = tmp_path / "config.json"
        json_data = {
            "app": {"name": "TestApp", "debug": True},
            "items": [1, 2, 3],
        }
        with open(config_file, "w") as f:
            json.dump(json_data, f)

        self.config.load_from_file(config_file)
        assert self.config.get("app.name") == "TestApp"
        assert self.config.get("app.debug") is True
        assert self.config.get("items") == [1, 2, 3]

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件。"""
        with pytest.raises(ConfigError, match="配置文件不存在"):
            self.config.load_from_file("/nonexistent/path/config.yaml")

    def test_load_unsupported_format(self, tmp_path):
        """测试加载不支持的格式。"""
        config_file = tmp_path / "config.txt"
        config_file.write_text("invalid")

        with pytest.raises(ConfigError, match="不支持的配置文件格式"):
            self.config.load_from_file(config_file)

    def test_load_from_env(self):
        """测试从环境变量加载配置。"""
        os.environ["OATH_TEST_HOST"] = "testhost"
        os.environ["OATH_TEST_PORT"] = "8080"
        os.environ["OATH_TEST_DB__HOST"] = "dbhost"
        os.environ["OATH_TEST_DB__PORT"] = "3306"
        os.environ["OATH_TEST_ENABLED"] = "true"
        os.environ["OATH_TEST_DISABLED"] = "false"

        try:
            config = ConfigManager(env_prefix="OATH_TEST_")
            config.load_from_env()

            assert config.get("host") == "testhost"
            assert config.get("port") == 8080
            assert config.get("db.host") == "dbhost"
            assert config.get("db.port") == 3306
            assert config.get("enabled") is True
            assert config.get("disabled") is False
        finally:
            for key in [
                "OATH_TEST_HOST",
                "OATH_TEST_PORT",
                "OATH_TEST_DB__HOST",
                "OATH_TEST_DB__PORT",
                "OATH_TEST_ENABLED",
                "OATH_TEST_DISABLED",
            ]:
                if key in os.environ:
                    del os.environ[key]

    def test_get_all(self):
        """测试获取所有配置。"""
        defaults = {"a": 1, "b": {"c": 2}}
        config = ConfigManager(defaults=defaults)
        config.set("b.d", 3)

        all_config = config.get_all()
        assert all_config["a"] == 1
        assert all_config["b"]["c"] == 2
        assert all_config["b"]["d"] == 3

    def test_reset(self):
        """测试重置配置。"""
        defaults = {"key": "default"}
        config = ConfigManager(defaults=defaults)
        config.set("key", "runtime")

        assert config.get("key") == "runtime"
        config.reset()
        assert config.get("key") == "default"

    def test_validate_without_schema(self):
        """测试没有schema时验证通过。"""
        assert self.config.validate() is True

    def test_validate_with_valid_schema(self):
        """测试使用有效schema验证。"""

        class AppSchema(ConfigSchema):
            app_name: str
            debug: bool = False
            port: int = 8000

        self.config.set_schema(AppSchema)
        self.config.set("app_name", "TestApp")
        self.config.set("debug", True)
        self.config.set("port", 9000)

        assert self.config.validate() is True

    def test_validate_with_invalid_schema(self):
        """测试使用无效schema验证失败。"""

        class AppSchema(ConfigSchema):
            app_name: str
            port: int

        self.config.set_schema(AppSchema)
        self.config.set("app_name", 123)
        self.config.set("port", "not_a_number")

        with pytest.raises(ConfigError, match="配置验证失败"):
            self.config.validate()

    def test_env_value_parsing(self):
        """测试环境变量值解析。"""
        os.environ["OATH_PARSE_INT"] = "42"
        os.environ["OATH_PARSE_FLOAT"] = "3.14"
        os.environ["OATH_PARSE_BOOL_TRUE"] = "true"
        os.environ["OATH_PARSE_BOOL_FALSE"] = "false"
        os.environ["OATH_PARSE_STRING"] = "hello"

        try:
            config = ConfigManager(env_prefix="OATH_PARSE_")
            config.load_from_env()

            assert config.get("int") == 42
            assert isinstance(config.get("int"), int)
            assert config.get("float") == 3.14
            assert isinstance(config.get("float"), float)
            assert config.get("bool_true") is True
            assert config.get("bool_false") is False
            assert config.get("string") == "hello"
        finally:
            for key in [
                "OATH_PARSE_INT",
                "OATH_PARSE_FLOAT",
                "OATH_PARSE_BOOL_TRUE",
                "OATH_PARSE_BOOL_FALSE",
                "OATH_PARSE_STRING",
            ]:
                if key in os.environ:
                    del os.environ[key]
