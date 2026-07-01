"""
数据集池（Dataset Pool）增强管理模块

提供模型 Agent 专用的数据集池管理能力：
- 多数据集统一管理
- 数据集版本控制
- 数据集质量分级
- 模型训练数据池化
- 数据集动态分配
"""

import hashlib
import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dataset.schema import DatasetSchema, DatasetType
from ai_llm_agent_crawler.dataset.quality_validator import QualityValidator, ValidationReport
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class DatasetPoolLevel(str, Enum):
    """数据集池级别"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class DatasetPoolStatus(str, Enum):
    """数据集池状态"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    MAINTENANCE = "maintenance"
    DEPLETED = "depleted"


class PoolDatasetInfo(BaseModel):
    """池化数据集信息"""

    pool_dataset_id: str = Field(default_factory=lambda: f"pool_ds_{uuid.uuid4().hex[:8]}")
    dataset_id: str
    name: str
    version: str = "1.0.0"
    level: str = DatasetPoolLevel.BRONZE

    record_count: int = 0
    size_bytes: int = 0
    feature_count: int = 0
    label_count: int = 0

    quality_score: float = 0.0
    usage_count: int = 0
    last_used_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    dataset_type: str = DatasetType.TRAINING
    schema_ref: str = ""
    storage_path: str = ""

    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class DatasetPoolConfig(BaseModel):
    """数据集池配置"""

    pool_id: str = Field(default_factory=lambda: f"dataset_pool_{uuid.uuid4().hex[:8]}")
    name: str = "default_dataset_pool"
    description: str = "Default dataset pool for model agents"
    max_datasets: int = 100
    max_total_size_bytes: int = 10 * 1024 * 1024 * 1024

    auto_quality_check: bool = True
    auto_level_assignment: bool = True
    enable_versioning: bool = True

    bronze_quality_min: float = 0.0
    silver_quality_min: float = 0.5
    gold_quality_min: float = 0.7
    platinum_quality_min: float = 0.85
    diamond_quality_min: float = 0.95

    storage_base_dir: Path = Path("data/pool")

    class Config:
        arbitrary_types_allowed = True


class ModelDatasetPool:
    """
    模型数据集池

    专为模型 Agent 设计的数据集池管理系统，
    支持多级别、多版本、质量分级的数据集管理。
    """

    def __init__(self, config: Optional[DatasetPoolConfig] = None):
        """
        初始化数据集池

        Args:
            config: 数据集池配置
        """
        self.config = config or DatasetPoolConfig()
        self._datasets: Dict[str, PoolDatasetInfo] = {}
        self._data_cache: Dict[str, pd.DataFrame] = {}
        self._schemas: Dict[str, DatasetSchema] = {}
        self._status: DatasetPoolStatus = DatasetPoolStatus.ACTIVE
        self._quality_validator = QualityValidator()

        self.config.storage_base_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"{__name__}.{self.config.name}")

    @property
    def status(self) -> DatasetPoolStatus:
        """池状态"""
        return self._status

    def add_dataset(
        self,
        dataset: pd.DataFrame,
        schema: DatasetSchema,
        dataset_id: Optional[str] = None,
        level: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[PoolDatasetInfo]:
        """
        添加数据集到池中

        Args:
            dataset: 数据集 DataFrame
            schema: 数据集模式
            dataset_id: 数据集 ID（可选，自动生成）
            level: 数据集级别（可选，自动分配）
            tags: 标签列表
            metadata: 元数据

        Returns:
            池化数据集信息
        """
        if len(self._datasets) >= self.config.max_datasets:
            self.logger.error("数据集池已满")
            return None

        ds_id = dataset_id or schema.name
        if ds_id in self._datasets:
            self.logger.warning(f"数据集已存在，将更新: {ds_id}")

        quality_score = 0.0
        if self.config.auto_quality_check:
            try:
                report = self._quality_validator.validate(dataset)
                quality_score = report.quality_score
            except Exception as e:
                self.logger.warning(f"质量检查失败: {e}")

        if level is None and self.config.auto_level_assignment:
            level = self._calculate_level(quality_score)

        record_count = len(dataset)
        size_bytes = dataset.memory_usage(deep=True).sum()

        info = PoolDatasetInfo(
            dataset_id=ds_id,
            name=schema.name,
            version=schema.version,
            level=level or DatasetPoolLevel.BRONZE,
            record_count=record_count,
            size_bytes=int(size_bytes),
            feature_count=len([f for f in schema.fields]),
            label_count=len(schema.labels),
            quality_score=quality_score,
            dataset_type=schema.dataset_type,
            schema_ref=schema.name,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._datasets[info.pool_dataset_id] = info
        self._data_cache[ds_id] = dataset
        self._schemas[ds_id] = schema

        self.logger.info(
            f"数据集已添加到池: {info.name} ({level}), "
            f"记录数={record_count}, 质量={quality_score:.2f}"
        )
        return info

    def remove_dataset(self, pool_dataset_id: str) -> bool:
        """
        从池中移除数据集

        Args:
            pool_dataset_id: 池数据集 ID

        Returns:
            是否移除成功
        """
        if pool_dataset_id not in self._datasets:
            return False

        info = self._datasets[pool_dataset_id]
        ds_id = info.dataset_id

        del self._datasets[pool_dataset_id]
        if ds_id in self._data_cache:
            del self._data_cache[ds_id]
        if ds_id in self._schemas:
            del self._schemas[ds_id]

        self.logger.info(f"数据集已从池中移除: {info.name}")
        return True

    def get_dataset(self, pool_dataset_id: str) -> Optional[Tuple[pd.DataFrame, DatasetSchema, PoolDatasetInfo]]:
        """
        获取数据集

        Args:
            pool_dataset_id: 池数据集 ID

        Returns:
            (DataFrame, Schema, PoolInfo) 元组
        """
        info = self._datasets.get(pool_dataset_id)
        if not info:
            return None

        dataset = self._data_cache.get(info.dataset_id)
        schema = self._schemas.get(info.dataset_id)

        if dataset is not None:
            info.usage_count += 1
            info.last_used_time = datetime.now()

        return (dataset, schema, info) if dataset is not None and schema is not None else None

    def get_dataset_by_name(self, name: str) -> Optional[Tuple[pd.DataFrame, DatasetSchema, PoolDatasetInfo]]:
        """
        按名称获取数据集

        Args:
            name: 数据集名称

        Returns:
            (DataFrame, Schema, PoolInfo) 元组
        """
        for info in self._datasets.values():
            if info.name == name:
                return self.get_dataset(info.pool_dataset_id)
        return None

    def list_datasets(
        self,
        level: Optional[str] = None,
        dataset_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_quality: Optional[float] = None,
    ) -> List[PoolDatasetInfo]:
        """
        列出数据集

        Args:
            level: 按级别过滤
            dataset_type: 按类型过滤
            tags: 按标签过滤
            min_quality: 最低质量分数

        Returns:
            数据集信息列表
        """
        datasets = list(self._datasets.values())

        if level:
            datasets = [d for d in datasets if d.level == level]

        if dataset_type:
            datasets = [d for d in datasets if d.dataset_type == dataset_type]

        if tags:
            datasets = [d for d in datasets if all(t in d.tags for t in tags)]

        if min_quality is not None:
            datasets = [d for d in datasets if d.quality_score >= min_quality]

        return datasets

    def search_datasets(self, query: str) -> List[PoolDatasetInfo]:
        """
        搜索数据集

        Args:
            query: 搜索关键词

        Returns:
            匹配的数据集列表
        """
        query_lower = query.lower()
        results = []

        for info in self._datasets.values():
            if (
                query_lower in info.name.lower()
                or query_lower in info.dataset_id.lower()
                or any(query_lower in tag.lower() for tag in info.tags)
            ):
                results.append(info)

        return results

    def update_dataset_level(self, pool_dataset_id: str, new_level: str) -> bool:
        """
        更新数据集级别

        Args:
            pool_dataset_id: 池数据集 ID
            new_level: 新级别

        Returns:
            是否更新成功
        """
        info = self._datasets.get(pool_dataset_id)
        if not info:
            return False

        old_level = info.level
        info.level = new_level
        info.updated_at = datetime.now()

        self.logger.info(f"数据集级别更新: {info.name} {old_level} -> {new_level}")
        return True

    def reevaluate_quality(self, pool_dataset_id: str) -> Optional[float]:
        """
        重新评估数据集质量

        Args:
            pool_dataset_id: 池数据集 ID

        Returns:
            新的质量分数
        """
        result = self.get_dataset(pool_dataset_id)
        if not result:
            return None

        dataset, schema, info = result

        try:
            report = self._quality_validator.validate(dataset)
            info.quality_score = report.quality_score
            info.updated_at = datetime.now()

            if self.config.auto_level_assignment:
                info.level = self._calculate_level(report.quality_score)

            self.logger.info(f"质量重评估完成: {info.name}, 分数={report.quality_score:.2f}")
            return report.quality_score
        except Exception as e:
            self.logger.error(f"质量评估失败: {e}")
            return None

    def get_datasets_by_level(self, level: str) -> List[PoolDatasetInfo]:
        """按级别获取数据集"""
        return [d for d in self._datasets.values() if d.level == level]

    def get_best_datasets(
        self,
        count: int = 5,
        dataset_type: Optional[str] = None,
    ) -> List[PoolDatasetInfo]:
        """
        获取质量最高的数据集

        Args:
            count: 返回数量
            dataset_type: 按类型过滤

        Returns:
            数据集信息列表
        """
        datasets = self.list_datasets(dataset_type=dataset_type)
        datasets.sort(key=lambda d: d.quality_score, reverse=True)
        return datasets[:count]

    def allocate_for_training(
        self,
        agent_id: str,
        min_quality: float = 0.0,
        min_records: int = 0,
        dataset_type: Optional[str] = None,
    ) -> Optional[PoolDatasetInfo]:
        """
        为模型训练分配数据集

        Args:
            agent_id: Agent ID
            min_quality: 最低质量要求
            min_records: 最少记录数要求
            dataset_type: 数据集类型

        Returns:
            分配的数据集信息
        """
        candidates = self.list_datasets(
            dataset_type=dataset_type,
            min_quality=min_quality,
        )

        candidates = [c for c in candidates if c.record_count >= min_records]

        if not candidates:
            self.logger.warning(f"没有符合条件的数据集: agent={agent_id}")
            return None

        candidates.sort(key=lambda d: (d.quality_score, d.usage_count), reverse=True)
        selected = candidates[0]

        selected.usage_count += 1
        selected.last_used_time = datetime.now()

        self.logger.info(
            f"数据集分配: {selected.name} -> {agent_id}, "
            f"质量={selected.quality_score:.2f}, 记录数={selected.record_count}"
        )
        return selected

    def get_pool_stats(self) -> Dict[str, Any]:
        """
        获取数据集池统计信息

        Returns:
            统计字典
        """
        total_datasets = len(self._datasets)
        total_records = sum(d.record_count for d in self._datasets.values())
        total_size = sum(d.size_bytes for d in self._datasets.values())
        avg_quality = (
            sum(d.quality_score for d in self._datasets.values()) / total_datasets
            if total_datasets > 0 else 0.0
        )

        level_counts = {}
        for level in DatasetPoolLevel:
            level_counts[level.value] = len(
                [d for d in self._datasets.values() if d.level == level.value]
            )

        type_counts = {}
        for d in self._datasets.values():
            type_counts[d.dataset_type] = type_counts.get(d.dataset_type, 0) + 1

        return {
            "pool_id": self.config.pool_id,
            "name": self.config.name,
            "status": self._status.value,
            "total_datasets": total_datasets,
            "max_datasets": self.config.max_datasets,
            "total_records": total_records,
            "total_size_bytes": total_size,
            "avg_quality_score": avg_quality,
            "level_distribution": level_counts,
            "type_distribution": type_counts,
        }

    def _calculate_level(self, quality_score: float) -> str:
        """
        根据质量分数计算数据集级别

        Args:
            quality_score: 质量分数

        Returns:
            数据集级别
        """
        if quality_score >= self.config.diamond_quality_min:
            return DatasetPoolLevel.DIAMOND
        elif quality_score >= self.config.platinum_quality_min:
            return DatasetPoolLevel.PLATINUM
        elif quality_score >= self.config.gold_quality_min:
            return DatasetPoolLevel.GOLD
        elif quality_score >= self.config.silver_quality_min:
            return DatasetPoolLevel.SILVER
        else:
            return DatasetPoolLevel.BRONZE

    def export_pool_summary(self, output_path: Optional[Path] = None) -> Path:
        """
        导出数据集池摘要

        Args:
            output_path: 输出路径

        Returns:
            输出文件路径
        """
        output_path = output_path or self.config.storage_base_dir / "pool_summary.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        summary = {
            "stats": self.get_pool_stats(),
            "datasets": [
                {
                    "pool_dataset_id": d.pool_dataset_id,
                    "name": d.name,
                    "level": d.level,
                    "quality_score": d.quality_score,
                    "record_count": d.record_count,
                    "version": d.version,
                    "tags": d.tags,
                }
                for d in self._datasets.values()
            ],
            "exported_at": datetime.now().isoformat(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        self.logger.info(f"数据集池摘要已导出: {output_path}")
        return output_path
