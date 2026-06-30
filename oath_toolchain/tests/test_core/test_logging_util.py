"""日志工具单元测试。"""
import logging
from pathlib import Path

import pytest

from oath_toolchain.core import logging_util
from oath_toolchain.core.logging_util import (
    get_logger,
    setup_logging,
    set_level,
    get_log_file,
)


class TestLoggingUtil:
    """测试日志工具。"""

    def setup_method(self):
        """每个测试前重置日志配置。"""
        logging_util._configured = False
        logging_util._default_level = logging.INFO
        logging_util._log_file = None

        root_logger = logging.getLogger("oath_toolchain")
        root_logger.handlers.clear()

    def test_get_logger_returns_logger(self):
        """测试获取日志记录器。"""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "oath_toolchain.test_module"

    def test_get_logger_with_prefix(self):
        """测试带前缀的日志记录器名称。"""
        logger = get_logger("oath_toolchain.my_module")
        assert logger.name == "oath_toolchain.my_module"

    def test_setup_logging_console(self):
        """测试设置控制台日志。"""
        setup_logging(level=logging.DEBUG, console=True)
        root_logger = logging.getLogger("oath_toolchain")
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) >= 1

    def test_setup_logging_no_console(self):
        """测试不输出到控制台。"""
        setup_logging(console=False)
        root_logger = logging.getLogger("oath_toolchain")
        console_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 0

    def test_setup_logging_with_file(self, tmp_path):
        """测试设置文件日志。"""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=str(log_file))

        assert get_log_file() == log_file

        logger = get_logger("file_test")
        logger.info("这是一条测试日志")

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "这是一条测试日志" in content

    def test_set_level(self):
        """测试设置日志级别。"""
        setup_logging(level=logging.INFO)
        set_level(logging.DEBUG)

        root_logger = logging.getLogger("oath_toolchain")
        assert root_logger.level == logging.DEBUG

        for handler in root_logger.handlers:
            assert handler.level == logging.DEBUG

    def test_get_log_file_none(self):
        """测试未配置日志文件时返回None。"""
        assert get_log_file() is None

    def test_logger_output(self, capsys):
        """测试日志输出到控制台。"""
        setup_logging(level=logging.INFO, console=True)
        logger = get_logger("output_test")
        logger.info("测试输出")

        captured = capsys.readouterr()
        assert "测试输出" in captured.out

    def test_multiple_loggers_same_config(self):
        """测试多个日志记录器共享同一配置。"""
        setup_logging(level=logging.WARNING)
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")

        assert logger1.parent.name == "oath_toolchain"
        assert logger2.parent.name == "oath_toolchain"
