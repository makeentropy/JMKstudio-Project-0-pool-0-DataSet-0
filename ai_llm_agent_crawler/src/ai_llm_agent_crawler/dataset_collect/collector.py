"""
数据收集器模块

支持多源数据收集: CherryTree知识库、ESP32硬件数据、Internet API等
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import hashlib
import json

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class DataSource(str, Enum):
    """数据源类型"""
    CHERRYTREE = "cherrytree"
    ESP32_SENSOR = "esp32_sensor"
    INTERNET_API = "internet_api"
    LOCAL_FILE = "local_file"
    WECHAT = "wechat"
    WEB_CRAWL = "web_crawl"


class CollectionConfig(BaseModel):
    """收集配置"""
    
    source_type: DataSource = Field(
        ...,
        description="数据源类型"
    )
    batch_size: int = Field(
        default=100,
        description="批量收集大小"
    )
    max_retries: int = Field(
        default=3,
        description="最大重试次数"
    )
    timeout: int = Field(
        default=30,
        description="超时时间(秒)"
    )
    enable_cache: bool = Field(
        default=True,
        description="是否启用缓存"
    )
    cache_dir: Optional[Path] = Field(
        default=None,
        description="缓存目录"
    )
    
    class Config:
        use_enum_values = True


@dataclass
class CollectedData:
    """收集的数据"""
    
    source: DataSource
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    data_id: str = field(default="")
    
    def __post_init__(self):
        if not self.data_id:
            # 生成唯一ID
            hash_input = f"{self.source}_{self.content[:100]}_{self.timestamp.isoformat()}"
            self.data_id = hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_id": self.data_id,
            "source": self.source.value if isinstance(self.source, DataSource) else self.source,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class DataCollector(ABC):
    """
    数据收集器基类
    
    所有数据收集器都应继承此类。
    """
    
    def __init__(self, config: CollectionConfig):
        self.config = config
        self._cache: Dict[str, CollectedData] = {}
    
    @abstractmethod
    def collect(self, **kwargs) -> List[CollectedData]:
        """
        收集数据
        
        Args:
            **kwargs: 收集参数
            
        Returns:
            收集到的数据列表
        """
        pass
    
    def _cache_data(self, data: CollectedData) -> None:
        """缓存数据"""
        if self.config.enable_cache:
            self._cache[data.data_id] = data
    
    def get_cached(self, data_id: str) -> Optional[CollectedData]:
        """获取缓存数据"""
        return self._cache.get(data_id)


class CherryTreeCollector(DataCollector):
    """
    CherryTree知识库数据收集器
    
    收集.ctd文件中的节点数据
    """
    
    def __init__(
        self,
        config: CollectionConfig,
        ctd_path: Optional[Path] = None
    ):
        super().__init__(config)
        self.ctd_path = ctd_path
    
    def collect(
        self,
        node_path: Optional[str] = None,
        include_children: bool = True,
        **kwargs
    ) -> List[CollectedData]:
        """
        收集CherryTree节点数据
        
        Args:
            node_path: 节点路径 (如: "量子物理/波函数")
            include_children: 是否包含子节点
            **kwargs: 额外参数
            
        Returns:
            收集到的数据列表
        """
        results = []
        
        # 如果指定了.ctd文件路径，解析XML结构
        if self.ctd_path and self.ctd_path.exists():
            results = self._parse_ctd_file(node_path, include_children)
        
        logger.info(f"从CherryTree收集了 {len(results)} 条数据")
        return results
    
    def _parse_ctd_file(
        self,
        node_path: Optional[str],
        include_children: bool
    ) -> List[CollectedData]:
        """解析.ctd文件 (SQLite数据库格式)"""
        import sqlite3
        
        results = []
        
        try:
            conn = sqlite3.connect(str(self.ctd_path))
            cursor = conn.cursor()
            
            # 查询节点
            if node_path:
                # 查询特定路径的节点
                cursor.execute(
                    "SELECT node_id, name, txt FROM node WHERE name LIKE ?",
                    (f"%{node_path}%",)
                )
            else:
                # 查询所有节点
                cursor.execute("SELECT node_id, name, txt FROM node")
            
            for row in cursor.fetchall():
                node_id, name, txt = row
                
                data = CollectedData(
                    source=DataSource.CHERRYTREE,
                    content=txt or "",
                    metadata={
                        "node_id": node_id,
                        "node_name": name,
                        "ctd_path": str(self.ctd_path),
                    }
                )
                self._cache_data(data)
                results.append(data)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"解析.ctd文件失败: {e}")
        
        return results


class ESP32DataCollector(DataCollector):
    """
    ESP32传感器数据收集器
    
    收集硬件数据: 声波、射频、地震波等
    """
    
    # 数据类型映射
    DATA_TYPES = {
        "audio_wave": "声波物质波",
        "rf_signal": "射频电磁波",
        "seismic": "地震振动波",
        "cw_morse": "摩尔斯CW波",
        "raw_bin": "原始bin数据",
    }
    
    def __init__(
        self,
        config: CollectionConfig,
        data_type: str = "raw_bin"
    ):
        super().__init__(config)
        self.data_type = data_type
    
    def collect(
        self,
        bin_file: Optional[Path] = None,
        port: Optional[int] = None,
        **kwargs
    ) -> List[CollectedData]:
        """
        收集ESP32数据
        
        Args:
            bin_file: Boost扫描bin文件路径
            port: 监听端口
            **kwargs: 额外参数
            
        Returns:
            收集到的数据列表
        """
        results = []
        
        if bin_file and bin_file.exists():
            results = self._parse_bin_file(bin_file)
        elif port:
            results = self._listen_port(port)
        
        logger.info(f"从ESP32收集了 {len(results)} 条数据")
        return results
    
    def _parse_bin_file(self, bin_file: Path) -> List[CollectedData]:
        """解析Boost裸盘扫描bin文件"""
        import struct
        
        results = []
        
        try:
            with open(bin_file, "rb") as f:
                # 读取bin文件头部
                header = f.read(64)
                
                # 解析数据块
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    
                    # 转换为十六进制表示
                    hex_data = chunk.hex()
                    
                    # BaseXOR隐写解码 (简化版)
                    decoded = self._base_xor_decode(hex_data)
                    
                    data = CollectedData(
                        source=DataSource.ESP32_SENSOR,
                        content=decoded,
                        metadata={
                            "data_type": self.DATA_TYPES.get(self.data_type, self.data_type),
                            "bin_file": str(bin_file),
                            "chunk_size": len(chunk),
                        }
                    )
                    self._cache_data(data)
                    results.append(data)
                    
        except Exception as e:
            logger.error(f"解析bin文件失败: {e}")
        
        return results
    
    def _listen_port(self, port: int) -> List[CollectedData]:
        """监听端口获取实时数据"""
        # 简化实现: 实际应用中需要实现socket监听
        logger.info(f"监听端口 {port} (未实现)")
        return []
    
    @staticmethod
    def _base_xor_decode(hex_data: str) -> str:
        """BaseXOR解码 (简化版)"""
        # 实际实现需要完整的隐写解码算法
        try:
            return bytes.fromhex(hex_data).decode("utf-8", errors="ignore")
        except:
            return hex_data


class InternetAPICollector(DataCollector):
    """
    Internet API数据收集器
    
    通过API搜索收集数据
    """
    
    def collect(
        self,
        query: str,
        max_results: int = 10,
        **kwargs
    ) -> List[CollectedData]:
        """
        通过API收集数据
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            **kwargs: 额外参数
            
        Returns:
            收集到的数据列表
        """
        results = []
        
        # 简化实现: 实际应用中调用真实API
        logger.info(f"通过API搜索: {query}")
        
        return results


class MultiSourceCollector:
    """
    多源数据收集器
    
    统一管理多个数据源
    """
    
    def __init__(self):
        self.collectors: Dict[DataSource, DataCollector] = {}
    
    def register(self, collector: DataCollector) -> None:
        """注册收集器"""
        self.collectors[collector.config.source_type] = collector
    
    def collect_all(self, **kwargs) -> Dict[DataSource, List[CollectedData]]:
        """
        从所有已注册的源收集数据
        
        Returns:
            按数据源分组的收集结果
        """
        results = {}
        
        for source_type, collector in self.collectors.items():
            try:
                data = collector.collect(**kwargs)
                results[source_type] = data
            except Exception as e:
                logger.error(f"从 {source_type} 收集失败: {e}")
                results[source_type] = []
        
        return results
    
    def collect_from(
        self,
        source: DataSource,
        **kwargs
    ) -> List[CollectedData]:
        """
        从指定源收集数据
        
        Args:
            source: 数据源类型
            **kwargs: 收集参数
            
        Returns:
            收集到的数据列表
        """
        collector = self.collectors.get(source)
        if not collector:
            logger.warning(f"未注册的收集器: {source}")
            return []
        
        return collector.collect(**kwargs)