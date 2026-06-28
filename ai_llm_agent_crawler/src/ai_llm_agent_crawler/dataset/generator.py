"""
数据集生成器模块

提供数据集的生成和导出功能。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.config import get_settings
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class DatasetConfig(BaseModel):
    """数据集配置"""
    
    output_dir: Path = Field(
        default_factory=lambda: get_settings().dataset_output_dir,
        description="输出目录",
    )
    format: str = Field(
        default_factory=lambda: get_settings().dataset_format,
        description="数据集格式",
    )
    compression: str = Field(
        default_factory=lambda: get_settings().dataset_compression,
        description="压缩算法",
    )
    chunk_size: int = Field(
        default_factory=lambda: get_settings().dataset_chunk_size,
        description="分块大小",
    )


class DatasetGenerator(ABC):
    """
    数据集生成器基类
    
    所有数据集生成器都应继承此类。
    """
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """
        初始化数据集生成器
        
        Args:
            config: 数据集配置
        """
        self.config = config or DatasetConfig()
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        """确保输出目录存在"""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def generate(self, data: Any, **kwargs) -> pd.DataFrame:
        """
        生成数据集
        
        Args:
            data: 输入数据
            **kwargs: 额外参数
            
        Returns:
            生成的DataFrame
        """
        pass
    
    def save(
        self,
        df: pd.DataFrame,
        filename: str,
        format: Optional[str] = None,
        **kwargs,
    ) -> Path:
        """
        保存数据集到文件
        
        Args:
            df: 数据框
            filename: 文件名（不含扩展名）
            format: 文件格式，默认使用配置中的格式
            **kwargs: 额外参数
            
        Returns:
            保存的文件路径
        """
        format = format or self.config.format
        output_path = self.config.output_dir / f"{filename}.{format}"
        
        format_lower = format.lower()
        
        if format_lower == "parquet":
            df.to_parquet(
                output_path,
                compression=kwargs.get("compression", self.config.compression),
                index=kwargs.get("index", False),
            )
        elif format_lower == "csv":
            df.to_csv(
                output_path,
                index=kwargs.get("index", False),
                encoding=kwargs.get("encoding", "utf-8"),
            )
        elif format_lower == "json":
            df.to_json(
                output_path,
                orient=kwargs.get("orient", "records"),
                force_ascii=kwargs.get("force_ascii", False),
                indent=kwargs.get("indent", 2),
            )
        elif format_lower in ["excel", "xlsx"]:
            df.to_excel(
                output_path,
                index=kwargs.get("index", False),
                engine=kwargs.get("engine", "openpyxl"),
            )
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"数据集已保存: {output_path}")
        return output_path
    
    def load(self, filepath: Union[str, Path]) -> pd.DataFrame:
        """
        从文件加载数据集
        
        Args:
            filepath: 文件路径
            
        Returns:
            加载的DataFrame
        """
        filepath = Path(filepath)
        format = filepath.suffix.lower().lstrip(".")
        
        if format == "parquet":
            return pd.read_parquet(filepath)
        elif format == "csv":
            return pd.read_csv(filepath)
        elif format == "json":
            return pd.read_json(filepath)
        elif format in ["excel", "xlsx"]:
            return pd.read_excel(filepath, engine="openpyxl")
        else:
            raise ValueError(f"Unsupported format: {format}")


class JSONDatasetGenerator(DatasetGenerator):
    """JSON数据集生成器"""
    
    def generate(self, data: Union[List[Dict], Dict], **kwargs) -> pd.DataFrame:
        """
        从JSON数据生成数据集
        
        Args:
            data: JSON数据（字典或列表）
            **kwargs: 额外参数
            
        Returns:
            生成的DataFrame
        """
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame(data)
        
        logger.info(f"生成了 {len(df)} 条记录的数据集")
        return df


class CSVFlatDatasetGenerator(DatasetGenerator):
    """CSV扁平数据集生成器"""
    
    def generate(self, data: List[List[Any]], columns: Optional[List[str]] = None, **kwargs) -> pd.DataFrame:
        """
        从二维列表生成数据集
        
        Args:
            data: 二维数据列表
            columns: 列名
            **kwargs: 额外参数
            
        Returns:
            生成的DataFrame
        """
        df = pd.DataFrame(data, columns=columns)
        logger.info(f"生成了 {len(df)} 条记录的数据集")
        return df