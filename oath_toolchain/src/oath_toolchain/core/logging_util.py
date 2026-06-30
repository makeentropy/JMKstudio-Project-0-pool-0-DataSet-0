"""神誓工具链日志工具模块。

提供统一的日志配置和获取接口，支持控制台和文件输出。
"""
import logging
import sys
from pathlib import Path
from typing import Optional

_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False
_default_level = logging.INFO
_log_file: Optional[Path] = None


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str | Path] = None,
    console: bool = True,
    format_string: Optional[str] = None,
) -> None:
    """配置全局日志设置。

    Args:
        level: 日志级别，默认为INFO
        log_file: 日志文件路径，如提供则同时输出到文件
        console: 是否输出到控制台，默认为True
        format_string: 自定义日志格式字符串
    """
    global _configured, _default_level, _log_file

    _default_level = level
    fmt = format_string or _LOG_FORMAT
    formatter = logging.Formatter(fmt, datefmt=_DATE_FORMAT)

    root_logger = logging.getLogger("oath_toolchain")
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)
        _log_file = log_path

    root_logger.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器。

    Args:
        name: 日志记录器名称，通常使用模块名

    Returns:
        配置好的日志记录器实例
    """
    if not _configured:
        setup_logging()

    if name.startswith("oath_toolchain."):
        full_name = name
    else:
        full_name = f"oath_toolchain.{name}"

    logger = logging.getLogger(full_name)
    return logger


def set_level(level: int) -> None:
    """设置全局日志级别。

    Args:
        level: 新的日志级别
    """
    global _default_level
    _default_level = level
    root_logger = logging.getLogger("oath_toolchain")
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)


def get_log_file() -> Optional[Path]:
    """获取当前配置的日志文件路径。

    Returns:
        日志文件路径，如果未配置则返回None
    """
    return _log_file
