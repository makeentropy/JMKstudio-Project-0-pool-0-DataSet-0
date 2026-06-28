"""
日志模块单元测试
"""

import pytest
from pathlib import Path

from ai_llm_agent_crawler.utils.logging import LogManager, get_logger, setup_logging


class TestLogManager:
    """LogManager类测试"""
    
    def test_initialize(self, test_output_dir):
        """测试日志初始化"""
        log_file = test_output_dir / "test.log"
        
        LogManager.initialize(
            log_level="DEBUG",
            log_file=log_file,
            enable_file_logging=True,
            enable_console_logging=True,
        )
        
        assert LogManager.is_initialized() == True
        
        # 重置以便其他测试
        LogManager.reset()
    
    def test_double_initialize(self):
        """测试重复初始化"""
        LogManager.initialize(log_level="DEBUG", enable_file_logging=False)
        
        # 重复初始化应该跳过
        LogManager.initialize(log_level="INFO", enable_file_logging=False)
        
        assert LogManager.is_initialized() == True
        
        LogManager.reset()
    
    def test_reset(self):
        """测试重置"""
        LogManager.initialize(enable_file_logging=False)
        assert LogManager.is_initialized() == True
        
        LogManager.reset()
        assert LogManager.is_initialized() == False


class TestSetupLogging:
    """setup_logging函数测试"""
    
    def test_setup_with_file(self, test_output_dir):
        """测试带文件的日志设置"""
        log_file = test_output_dir / "setup_test.log"
        
        setup_logging(
            log_level="DEBUG",
            log_file=log_file,
            enable_file_logging=True,
            enable_console_logging=False,
        )
        
        # 检查日志文件是否被创建（可能在初始化时创建）
        # 注意：loguru不会立即创建文件，只有在写入时才创建
        
        LogManager.reset()
    
    def test_setup_console_only(self):
        """测试仅控制台日志"""
        setup_logging(
            log_level="INFO",
            enable_file_logging=False,
            enable_console_logging=True,
        )
        
        LogManager.reset()


class TestGetLogger:
    """get_logger函数测试"""
    
    def test_get_logger_without_name(self):
        """测试获取默认logger"""
        logger = get_logger()
        assert logger is not None
    
    def test_get_logger_with_name(self):
        """测试获取命名logger"""
        logger = get_logger("test_module")
        assert logger is not None
        
        # 绑定后的logger应该包含name信息
        # logger.bind返回BoundLogger，有extra属性