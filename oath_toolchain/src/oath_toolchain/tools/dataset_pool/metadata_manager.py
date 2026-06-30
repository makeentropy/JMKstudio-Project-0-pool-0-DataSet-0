"""数据集元数据管理模块。

提供数据集元数据的设置、获取、更新、删除和搜索功能，
支持按元数据搜索数据集，以及元数据schema定义。
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from .dataset import Dataset
from .pool_manager import DatasetPoolManager


class MetadataManager:
    """元数据管理器。

    管理数据集的元数据，支持增删改查和按元数据搜索功能。

    Attributes:
        pool_manager: 数据集池管理器实例
    """

    def __init__(self, pool_manager: DatasetPoolManager) -> None:
        """初始化元数据管理器。

        Args:
            pool_manager: 数据集池管理器实例
        """
        self.pool_manager: DatasetPoolManager = pool_manager

    def set_metadata(
        self,
        dataset_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """设置元数据。

        Args:
            dataset_id: 数据集ID
            key: 元数据键
            value: 元数据值

        Returns:
            是否成功设置
        """
        dataset = self.pool_manager.get_dataset(dataset_id)
        if dataset is None:
            return False

        dataset.metadata[key] = value
        dataset.updated_at = time.time()

        dataset_path = self.pool_manager._get_dataset_path(dataset_id)
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset.to_dict(), f, ensure_ascii=False, indent=2)

        self.pool_manager._index[dataset_id]["updated_at"] = dataset.updated_at
        self.pool_manager._save_index()

        return True

    def get_metadata(
        self,
        dataset_id: str,
        key: Optional[str] = None,
    ) -> Any:
        """获取元数据。

        Args:
            dataset_id: 数据集ID
            key: 元数据键，如为None则返回所有元数据

        Returns:
            元数据值或所有元数据字典，如果数据集不存在则返回None
        """
        dataset = self.pool_manager.get_dataset(dataset_id)
        if dataset is None:
            return None

        if key is None:
            return dict(dataset.metadata)

        return dataset.metadata.get(key)

    def update_metadata(
        self,
        dataset_id: str,
        metadata: dict,
    ) -> bool:
        """批量更新元数据。

        Args:
            dataset_id: 数据集ID
            metadata: 要更新的元数据字典

        Returns:
            是否成功更新
        """
        dataset = self.pool_manager.get_dataset(dataset_id)
        if dataset is None:
            return False

        dataset.metadata.update(metadata)
        dataset.updated_at = time.time()

        dataset_path = self.pool_manager._get_dataset_path(dataset_id)
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset.to_dict(), f, ensure_ascii=False, indent=2)

        self.pool_manager._index[dataset_id]["updated_at"] = dataset.updated_at
        self.pool_manager._save_index()

        return True

    def remove_metadata(
        self,
        dataset_id: str,
        key: str,
    ) -> bool:
        """删除元数据。

        Args:
            dataset_id: 数据集ID
            key: 要删除的元数据键

        Returns:
            是否成功删除
        """
        dataset = self.pool_manager.get_dataset(dataset_id)
        if dataset is None or key not in dataset.metadata:
            return False

        del dataset.metadata[key]
        dataset.updated_at = time.time()

        dataset_path = self.pool_manager._get_dataset_path(dataset_id)
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset.to_dict(), f, ensure_ascii=False, indent=2)

        self.pool_manager._index[dataset_id]["updated_at"] = dataset.updated_at
        self.pool_manager._save_index()

        return True

    def search_by_metadata(self, filters: dict) -> List[str]:
        """按元数据搜索数据集。

        Args:
            filters: 元数据过滤条件字典

        Returns:
            匹配的数据集ID列表
        """
        results = []

        for dataset_id in self.pool_manager._index:
            dataset = self.pool_manager.get_dataset(dataset_id)
            if dataset and self._match_metadata_filters(dataset, filters):
                results.append(dataset_id)

        return results

    def _match_metadata_filters(self, dataset: Dataset, filters: dict) -> bool:
        """检查数据集的元数据是否匹配过滤条件。

        Args:
            dataset: 数据集
            filters: 元数据过滤条件

        Returns:
            是否匹配
        """
        for key, value in filters.items():
            if key not in dataset.metadata:
                return False
            if isinstance(value, list):
                if dataset.metadata[key] not in value:
                    return False
            else:
                if dataset.metadata[key] != value:
                    return False
        return True

    def get_metadata_schema(self) -> dict:
        """获取元数据schema定义。

        Returns:
            元数据schema定义字典
        """
        return {
            "title": "Dataset Metadata Schema",
            "description": "数据集元数据schema定义",
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "数据来源",
                },
                "author": {
                    "type": "string",
                    "description": "数据作者",
                },
                "license": {
                    "type": "string",
                    "description": "数据许可证",
                },
                "category": {
                    "type": "string",
                    "description": "数据分类",
                },
                "domain": {
                    "type": "string",
                    "description": "数据领域",
                },
                "language": {
                    "type": "string",
                    "description": "数据语言",
                },
                "created_by": {
                    "type": "string",
                    "description": "创建者",
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型（结构化/半结构化/非结构化）",
                    "enum": ["structured", "semi-structured", "unstructured"],
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "自定义标签列表",
                },
                "custom_fields": {
                    "type": "object",
                    "description": "自定义字段",
                    "additionalProperties": True,
                },
            },
            "additionalProperties": True,
        }
