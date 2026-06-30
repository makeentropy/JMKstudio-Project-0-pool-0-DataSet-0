"""数据集池管理器模块。

提供数据集的创建、删除、查询、更新、导入导出等核心管理功能，
使用本地文件系统作为存储后端，JSON作为索引格式。
"""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional

from .dataset import Dataset
from ..karma_tags.karma_tag import KarmaTag


class DatasetPoolManager:
    """数据集池管理器。

    管理数据集的生命周期，包括创建、删除、查询、更新、导入导出等操作。
    使用本地文件系统作为存储后端，JSON文件作为索引。

    Attributes:
        pool_path: 数据集池存储路径
        index_path: 索引文件路径
        data_dir: 数据文件存储目录
        _index: 内存中的索引数据
    """

    def __init__(self, pool_path: Optional[str] = None) -> None:
        """初始化数据集池管理器。

        Args:
            pool_path: 数据集池存储路径，如未提供则使用临时目录
        """
        if pool_path is None:
            pool_path = os.path.join(tempfile.gettempdir(), "oath_dataset_pool")

        self.pool_path: str = os.path.abspath(pool_path)
        self.index_path: str = os.path.join(self.pool_path, "index.json")
        self.data_dir: str = os.path.join(self.pool_path, "datasets")
        self._index: Dict[str, Dict[str, Any]] = {}

        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """初始化存储目录和索引文件。"""
        os.makedirs(self.pool_path, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        if os.path.exists(self.index_path):
            self._load_index()
        else:
            self._save_index()

    def _load_index(self) -> None:
        """从文件加载索引。"""
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                self._index = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._index = {}

    def _save_index(self) -> None:
        """保存索引到文件。"""
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    def _get_dataset_path(self, dataset_id: str) -> str:
        """获取数据集文件路径。

        Args:
            dataset_id: 数据集ID

        Returns:
            数据集文件的完整路径
        """
        return os.path.join(self.data_dir, f"{dataset_id}.json")

    def create_dataset(
        self,
        name: str,
        data: Any = None,
        format: str = "json",
        description: Optional[str] = None,
    ) -> Dataset:
        """创建新数据集。

        Args:
            name: 数据集名称
            data: 初始数据内容
            format: 数据格式（json/csv/yaml等）
            description: 数据集描述

        Returns:
            创建的Dataset实例
        """
        dataset = Dataset(name=name)
        dataset.format = format
        if description:
            dataset.description = description
        if data is not None:
            dataset.data = data

        dataset_path = self._get_dataset_path(dataset.dataset_id)
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset.to_dict(), f, ensure_ascii=False, indent=2)

        self._index[dataset.dataset_id] = {
            "name": dataset.name,
            "format": dataset.format,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
            "size": dataset.size,
            "record_count": dataset.record_count,
            "version": dataset.version,
            "quality_score": dataset.quality_score,
        }
        self._save_index()

        return dataset

    def delete_dataset(self, dataset_id: str) -> bool:
        """删除数据集。

        Args:
            dataset_id: 数据集ID

        Returns:
            是否成功删除
        """
        if dataset_id not in self._index:
            return False

        dataset_path = self._get_dataset_path(dataset_id)
        if os.path.exists(dataset_path):
            os.remove(dataset_path)

        versions_dir = os.path.join(self.data_dir, f"{dataset_id}_versions")
        if os.path.exists(versions_dir):
            shutil.rmtree(versions_dir)

        del self._index[dataset_id]
        self._save_index()

        return True

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """获取数据集。

        Args:
            dataset_id: 数据集ID

        Returns:
            Dataset实例，如果不存在则返回None
        """
        if dataset_id not in self._index:
            return None

        dataset_path = self._get_dataset_path(dataset_id)
        if not os.path.exists(dataset_path):
            return None

        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Dataset.from_dict(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def save_dataset(self, dataset: Dataset) -> None:
        """保存数据集到文件并更新索引。

        Args:
            dataset: 要保存的数据集
        """
        dataset_path = self._get_dataset_path(dataset.dataset_id)
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset.to_dict(), f, ensure_ascii=False, indent=2)

        self._index[dataset.dataset_id] = {
            "name": dataset.name,
            "format": dataset.format,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
            "size": dataset.size,
            "record_count": dataset.record_count,
            "version": dataset.version,
            "quality_score": dataset.quality_score,
        }
        self._save_index()

    def update_dataset(
        self,
        dataset_id: str,
        data: Any = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Dataset]:
        """更新数据集。

        Args:
            dataset_id: 数据集ID
            data: 新的数据内容（None表示不更新）
            metadata: 新的元数据（None表示不更新）

        Returns:
            更新后的Dataset实例，如果不存在则返回None
        """
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            return None

        if data is not None:
            dataset.data = data

        if metadata is not None:
            dataset.metadata.update(metadata)
            dataset.updated_at = time.time()

        self.save_dataset(dataset)

        return dataset

    def list_datasets(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dataset]:
        """列出数据集。

        Args:
            filters: 过滤条件字典
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            数据集列表
        """
        dataset_ids = list(self._index.keys())

        if filters:
            filtered_ids = []
            for dataset_id in dataset_ids:
                dataset = self.get_dataset(dataset_id)
                if dataset and self._match_filters(dataset, filters):
                    filtered_ids.append(dataset_id)
            dataset_ids = filtered_ids

        dataset_ids = dataset_ids[offset:offset + limit]

        datasets = []
        for dataset_id in dataset_ids:
            dataset = self.get_dataset(dataset_id)
            if dataset:
                datasets.append(dataset)

        return datasets

    def _match_filters(self, dataset: Dataset, filters: dict) -> bool:
        """检查数据集是否匹配过滤条件。

        Args:
            dataset: 数据集
            filters: 过滤条件

        Returns:
            是否匹配
        """
        for key, value in filters.items():
            if hasattr(dataset, key):
                attr_value = getattr(dataset, key)
                if isinstance(value, list):
                    if attr_value not in value:
                        return False
                else:
                    if attr_value != value:
                        return False
            elif key in dataset.metadata:
                if dataset.metadata[key] != value:
                    return False
            else:
                return False
        return True

    def search_by_tags(self, tag_filters: dict) -> List[Dataset]:
        """按标签搜索数据集。

        Args:
            tag_filters: 标签过滤条件字典

        Returns:
            匹配的数据集列表
        """
        results = []
        for dataset_id in self._index:
            dataset = self.get_dataset(dataset_id)
            if dataset and self._match_tag_filters(dataset, tag_filters):
                results.append(dataset)
        return results

    def _match_tag_filters(self, dataset: Dataset, tag_filters: dict) -> bool:
        """检查数据集的标签是否匹配过滤条件。

        Args:
            dataset: 数据集
            tag_filters: 标签过滤条件

        Returns:
            是否匹配
        """
        for tag in dataset.tags:
            match = True
            for key, value in tag_filters.items():
                if hasattr(tag, key):
                    attr_value = getattr(tag, key)
                    if isinstance(value, list):
                        if attr_value not in value:
                            match = False
                            break
                    else:
                        if attr_value != value:
                            match = False
                            break
            if match:
                return True
        return False

    def import_dataset(
        self,
        filepath: str,
        format: Optional[str] = None,
    ) -> Dataset:
        """从文件导入数据集。

        Args:
            filepath: 导入文件路径
            format: 数据格式，如未提供则根据文件扩展名推断

        Returns:
            导入的Dataset实例

        Raises:
            FileNotFoundError: 当文件不存在时
            ValueError: 当文件格式不支持时
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        if format is None:
            _, ext = os.path.splitext(filepath)
            format = ext.lstrip(".").lower()

        name = os.path.basename(filepath)

        if format == "json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            dataset = self.create_dataset(name=name, data=data, format=format)
        elif format == "csv":
            records = []
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)
            data = {"records": records}
            dataset = self.create_dataset(name=name, data=data, format=format)
        else:
            with open(filepath, "rb") as f:
                data = f.read()
            dataset = self.create_dataset(name=name, data=data, format=format)

        return dataset

    def export_dataset(
        self,
        dataset_id: str,
        filepath: str,
        format: Optional[str] = None,
    ) -> str:
        """导出数据集到文件。

        Args:
            dataset_id: 数据集ID
            filepath: 导出文件路径
            format: 导出格式，如未提供则使用数据集原格式

        Returns:
            导出文件的完整路径

        Raises:
            ValueError: 当数据集不存在或格式不支持时
        """
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError(f"数据集不存在: {dataset_id}")

        if format is None:
            format = dataset.format

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        if format == "json":
            data = dataset.data if dataset.data else {}
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        elif format == "csv":
            data = dataset.data
            records = []
            if isinstance(data, dict):
                if "records" in data and isinstance(data["records"], list):
                    records = data["records"]
                elif "items" in data and isinstance(data["items"], list):
                    records = data["items"]
            if records:
                fieldnames = list(records[0].keys())
                with open(filepath, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("")
        else:
            if isinstance(dataset.data, bytes):
                with open(filepath, "wb") as f:
                    f.write(dataset.data)
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(dataset.data if dataset.data else {}, f, ensure_ascii=False, indent=2)

        return os.path.abspath(filepath)

    def get_pool_stats(self) -> dict:
        """获取池统计信息。

        Returns:
            统计信息字典
        """
        total_datasets = len(self._index)
        total_size = sum(info.get("size", 0) for info in self._index.values())
        total_records = sum(info.get("record_count", 0) for info in self._index.values())

        format_counts: Dict[str, int] = {}
        for info in self._index.values():
            fmt = info.get("format", "unknown")
            format_counts[fmt] = format_counts.get(fmt, 0) + 1

        return {
            "total_datasets": total_datasets,
            "total_size": total_size,
            "total_records": total_records,
            "format_distribution": format_counts,
            "pool_path": self.pool_path,
        }

    def get_storage_usage(self) -> dict:
        """获取存储使用情况。

        Returns:
            存储使用信息字典
        """
        total_used = 0
        if os.path.exists(self.pool_path):
            for dirpath, _, filenames in os.walk(self.pool_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_used += os.path.getsize(filepath)

        total, used, free = shutil.disk_usage(self.pool_path)

        return {
            "pool_used_bytes": total_used,
            "pool_used_mb": total_used / (1024 * 1024),
            "disk_total_bytes": total,
            "disk_used_bytes": used,
            "disk_free_bytes": free,
            "disk_total_gb": total / (1024 * 1024 * 1024),
            "disk_free_gb": free / (1024 * 1024 * 1024),
        }
