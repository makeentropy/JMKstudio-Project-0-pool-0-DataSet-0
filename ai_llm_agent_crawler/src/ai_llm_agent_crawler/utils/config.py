"""
配置管理模块

使用 pydantic-settings 实现类型安全的配置管理，
支持从环境变量、.env 文件和配置文件加载配置。
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类
    
    配置优先级（从高到低）：
    1. 环境变量
    2. .env 文件
    3. 默认值
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # 应用基础配置
    app_name: str = Field(default="ai_llm_agent_crawler", description="应用名称")
    app_version: str = Field(default="0.1.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    environment: str = Field(default="development", description="运行环境")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="日志格式",
    )
    log_file: Optional[Path] = Field(default=None, description="日志文件路径")
    log_rotation: str = Field(default="100 MB", description="日志轮转大小")
    log_retention: str = Field(default="30 days", description="日志保留时间")
    log_compression: str = Field(default="zip", description="日志压缩格式")
    
    # 爬虫配置
    crawler_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="爬虫User-Agent",
    )
    crawler_timeout: int = Field(default=30, description="请求超时时间（秒）")
    crawler_max_retries: int = Field(default=3, description="最大重试次数")
    crawler_delay: float = Field(default=1.0, description="请求延迟（秒）")
    crawler_concurrent_requests: int = Field(default=10, description="并发请求数")
    crawler_download_delay: float = Field(default=0.5, description="下载延迟")
    crawler_auto_throttle: bool = Field(default=True, description="自动限流")
    
    # 数据库配置
    database_url: Optional[str] = Field(default=None, description="数据库连接URL")
    database_pool_size: int = Field(default=10, description="数据库连接池大小")
    database_max_overflow: int = Field(default=20, description="数据库最大溢出连接数")
    database_pool_timeout: int = Field(default=30, description="连接池超时时间")
    database_echo: bool = Field(default=False, description="是否打印SQL语句")
    
    # Redis配置
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis连接URL")
    redis_max_connections: int = Field(default=50, description="Redis最大连接数")
    redis_socket_timeout: int = Field(default=5, description="Redis socket超时")
    
    # MongoDB配置
    mongodb_url: Optional[str] = Field(default=None, description="MongoDB连接URL")
    mongodb_database: str = Field(default="ai_crawler", description="MongoDB数据库名")
    mongodb_max_pool_size: int = Field(default=100, description="MongoDB连接池大小")
    
    # Elasticsearch配置
    elasticsearch_url: Optional[str] = Field(default=None, description="Elasticsearch连接URL")
    elasticsearch_index_prefix: str = Field(default="crawler", description="索引前缀")
    
    # MinIO配置
    minio_endpoint: Optional[str] = Field(default=None, description="MinIO endpoint")
    minio_access_key: Optional[str] = Field(default=None, description="MinIO access key")
    minio_secret_key: Optional[str] = Field(default=None, description="MinIO secret key")
    minio_secure: bool = Field(default=False, description="是否使用HTTPS")
    minio_bucket: str = Field(default="ai-crawler", description="MinIO bucket名称")
    
    # AWS S3配置
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS Access Key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS Secret Access Key")
    aws_region: str = Field(default="us-east-1", description="AWS区域")
    aws_s3_bucket: Optional[str] = Field(default=None, description="S3 bucket名称")
    
    # 安全加密配置
    encryption_key: Optional[str] = Field(default=None, description="加密密钥")
    encryption_algorithm: str = Field(default="AES-256-GCM", description="加密算法")
    hash_algorithm: str = Field(default="SHA-256", description="哈希算法")
    password_salt: Optional[str] = Field(default=None, description="密码盐")
    
    # 数据集配置
    dataset_output_dir: Path = Field(default=Path("data/datasets"), description="数据集输出目录")
    dataset_format: str = Field(default="parquet", description="数据集格式")
    dataset_compression: str = Field(default="snappy", description="数据集压缩算法")
    dataset_chunk_size: int = Field(default=10000, description="数据集分块大小")
    
    # 维度空间配置
    dimension_max_dimensions: int = Field(default=1000, description="最大维度数")
    dimension_cache_size: int = Field(default=10000, description="维度缓存大小")
    
    # 版本管理配置
    version_storage_backend: str = Field(default="local", description="版本存储后端")
    version_max_versions: int = Field(default=100, description="最大版本数")
    
    # 存储配置
    storage_nas_path: Optional[Path] = Field(default=None, description="NAS存储路径")
    storage_max_size: Optional[int] = Field(default=None, description="最大存储大小（字节）")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """验证运行环境"""
        valid_envs = ["development", "testing", "staging", "production"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v_lower
    
    @field_validator("dataset_format")
    @classmethod
    def validate_dataset_format(cls, v: str) -> str:
        """验证数据集格式"""
        valid_formats = ["parquet", "json", "csv", "excel", "hdf5"]
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"Invalid dataset format: {v}. Must be one of {valid_formats}")
        return v_lower
    
    def get_database_url(self) -> str:
        """获取数据库URL"""
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.dataset_output_dir}/crawler.db"
    
    def get_log_file_path(self) -> Path:
        """获取日志文件路径"""
        if self.log_file:
            return Path(self.log_file)
        return Path("logs") / f"{self.app_name}.log"


@lru_cache
def get_settings() -> Settings:
    """
    获取配置实例（单例模式）
    
    使用 lru_cache 确保配置只加载一次。
    """
    return Settings()


def reload_settings() -> Settings:
    """
    重新加载配置
    
    清除缓存并重新加载配置。
    """
    get_settings.cache_clear()
    return get_settings()


# 导出配置实例
settings = get_settings()