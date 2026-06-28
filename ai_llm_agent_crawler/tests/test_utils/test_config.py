"""
配置模块单元测试
"""

from pathlib import Path

import pytest

from ai_llm_agent_crawler.utils.config import Settings, get_settings, reload_settings


class TestSettings:
    """Settings类测试"""
    
    def test_default_settings(self):
        """测试默认配置"""
        settings = Settings()
        
        assert settings.app_name == "ai_llm_agent_crawler"
        assert settings.app_version == "0.1.0"
        assert settings.debug == False
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
    
    def test_custom_settings(self):
        """测试自定义配置"""
        settings = Settings(
            debug=True,
            environment="testing",
            log_level="DEBUG",
        )
        
        assert settings.debug == True
        assert settings.environment == "testing"
        assert settings.log_level == "DEBUG"
    
    def test_log_level_validation(self):
        """测试日志级别验证"""
        # 有效级别
        settings = Settings(log_level="DEBUG")
        assert settings.log_level == "DEBUG"
        
        # 无效级别应该抛出异常
        with pytest.raises(ValueError):
            Settings(log_level="INVALID")
    
    def test_environment_validation(self):
        """测试运行环境验证"""
        # 有效环境
        settings = Settings(environment="production")
        assert settings.environment == "production"
        
        # 无效环境应该抛出异常
        with pytest.raises(ValueError):
            Settings(environment="invalid_env")
    
    def test_dataset_format_validation(self):
        """测试数据集格式验证"""
        # 有效格式
        settings = Settings(dataset_format="csv")
        assert settings.dataset_format == "csv"
        
        # 无效格式应该抛出异常
        with pytest.raises(ValueError):
            Settings(dataset_format="invalid_format")
    
    def test_get_database_url(self):
        """测试获取数据库URL"""
        # 自定义URL
        settings = Settings(database_url="postgresql://localhost/test")
        assert settings.get_database_url() == "postgresql://localhost/test"
        
        # 默认URL（SQLite）
        settings = Settings()
        url = settings.get_database_url()
        assert "sqlite:///" in url
    
    def test_get_log_file_path(self):
        """测试获取日志文件路径"""
        # 自定义路径
        settings = Settings(log_file=Path("/custom/path.log"))
        assert settings.get_log_file_path() == Path("/custom/path.log")
        
        # 默认路径
        settings = Settings()
        path = settings.get_log_file_path()
        assert path == Path("logs") / "ai_llm_agent_crawler.log"


class TestGetSettings:
    """get_settings函数测试"""
    
    def test_singleton(self):
        """测试单例模式"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_reload_settings(self):
        """测试重新加载配置"""
        settings1 = get_settings()
        settings2 = reload_settings()
        
        # 重新加载后应该是不同的对象
        assert settings1 is not settings2
        
        # 但再次调用get_settings应该返回新对象
        settings3 = get_settings()
        assert settings2 is settings3