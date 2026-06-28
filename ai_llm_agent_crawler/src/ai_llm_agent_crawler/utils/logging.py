"""
日志系统模块

使用 loguru 提供强大的日志功能，支持：
- 彩色控制台输出
- 文件轮转
- 多日志处理器
- 结构化日志
- 异步日志
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from ai_llm_agent_crawler.utils.config import get_settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
) -> None:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别，默认从配置读取
        log_file: 日志文件路径，默认从配置读取
        log_format: 日志格式，默认从配置读取
        enable_file_logging: 是否启用文件日志
        enable_console_logging: 是否启用控制台日志
    """
    # 移除默认处理器
    logger.remove()
    
    # 获取配置
    settings = get_settings()
    
    # 使用传入参数或配置值
    level = log_level or settings.log_level
    file_path = log_file or settings.get_log_file_path()
    format_str = log_format or settings.log_format
    
    # 添加控制台处理器
    if enable_console_logging:
        logger.add(
            sys.stdout,
            level=level,
            format=format_str,
            colorize=True,
            enqueue=True,  # 异步写入
        )
    
    # 添加文件处理器
    if enable_file_logging:
        # 确保日志目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            str(file_path),
            level=level,
            format=format_str,
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression=settings.log_compression,
            enqueue=True,  # 异步写入
            serialize=False,  # 不序列化为JSON
        )
        
        # 添加错误日志文件
        error_log_path = file_path.parent / f"{file_path.stem}_error{file_path.suffix}"
        logger.add(
            str(error_log_path),
            level="ERROR",
            format=format_str,
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression=settings.log_compression,
            enqueue=True,
        )
    
    logger.info(f"日志系统初始化完成 - 级别: {level}")


def get_logger(name: Optional[str] = None):
    """
    获取日志记录器
        
    Args:
        name: 记录器名称，通常使用 __name__
        
    Returns:
        Logger: 配置好的日志记录器
    """
    if name:
        return logger.bind(name=name)
    return logger


class LogManager:
    """
    日志管理器
    
    提供日志配置和管理的便捷方法。
    """
    
    _initialized: bool = False
    
    @classmethod
    def initialize(
        cls,
        log_level: Optional[str] = None,
        log_file: Optional[Path] = None,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
    ) -> None:
        """
        初始化日志系统
        
        Args:
            log_level: 日志级别
            log_file: 日志文件路径
            enable_file_logging: 是否启用文件日志
            enable_console_logging: 是否启用控制台日志
        """
        if cls._initialized:
            logger.warning("日志系统已经初始化，跳过重复初始化")
            return
        
        setup_logging(
            log_level=log_level,
            log_file=log_file,
            enable_file_logging=enable_file_logging,
            enable_console_logging=enable_console_logging,
        )
        cls._initialized = True
    
    @classmethod
    def is_initialized(cls) -> bool:
        """检查日志系统是否已初始化"""
        return cls._initialized
    
    @classmethod
    def reset(cls) -> None:
        """重置日志系统"""
        logger.remove()
        cls._initialized = False


# 便捷函数
def configure_logging(**kwargs) -> None:
    """配置日志的便捷函数"""
    LogManager.initialize(**kwargs)


# 导出日志实例
__all__ = [
    "logger",
    "get_logger",
    "setup_logging",
    "LogManager",
    "configure_logging",
]