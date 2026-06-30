"""数据集版本控制模块。

提供数据集的版本管理功能，包括版本提交、历史查询、版本回滚、
版本差异比较和版本标签等功能。
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional

from .dataset import Dataset
from .pool_manager import DatasetPoolManager


class DatasetVersionControl:
    """数据集版本控制器。

    管理数据集的版本历史，支持版本提交、查询、回滚、
    差异比较和版本标签等功能。

    Attributes:
        pool_manager: 数据集池管理器实例
        versions_dir: 版本存储目录
        _version_index: 版本索引缓存
    """

    def __init__(self, pool_manager: DatasetPoolManager) -> None:
        """初始化版本控制器。

        Args:
            pool_manager: 数据集池管理器实例
        """
        self.pool_manager: DatasetPoolManager = pool_manager
        self.versions_dir: str = os.path.join(pool_manager.data_dir, "versions")
        self._version_index: Dict[str, List[Dict[str, Any]]] = {}

        os.makedirs(self.versions_dir, exist_ok=True)

    def _get_versions_dir(self, dataset_id: str) -> str:
        """获取数据集的版本存储目录。

        Args:
            dataset_id: 数据集ID

        Returns:
            版本存储目录路径
        """
        return os.path.join(self.versions_dir, dataset_id)

    def _get_version_file(self, dataset_id: str, version: str) -> str:
        """获取版本文件路径。

        Args:
            dataset_id: 数据集ID
            version: 版本号

        Returns:
            版本文件路径
        """
        return os.path.join(self._get_versions_dir(dataset_id), f"{version}.json")

    def _get_index_file(self, dataset_id: str) -> str:
        """获取版本索引文件路径。

        Args:
            dataset_id: 数据集ID

        Returns:
            版本索引文件路径
        """
        return os.path.join(self._get_versions_dir(dataset_id), "index.json")

    def _load_version_index(self, dataset_id: str) -> List[Dict[str, Any]]:
        """加载版本索引。

        Args:
            dataset_id: 数据集ID

        Returns:
            版本索引列表
        """
        if dataset_id in self._version_index:
            return self._version_index[dataset_id]

        index_file = self._get_index_file(dataset_id)
        if os.path.exists(index_file):
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    self._version_index[dataset_id] = json.load(f)
            except json.JSONDecodeError:
                self._version_index[dataset_id] = []
        else:
            self._version_index[dataset_id] = []

        return self._version_index[dataset_id]

    def _save_version_index(self, dataset_id: str, index: List[Dict[str, Any]]) -> None:
        """保存版本索引。

        Args:
            dataset_id: 数据集ID
            index: 版本索引列表
        """
        self._version_index[dataset_id] = index
        index_file = self._get_index_file(dataset_id)
        os.makedirs(os.path.dirname(index_file), exist_ok=True)
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _generate_version_hash(self, dataset: Dataset) -> str:
        """生成版本哈希。

        Args:
            dataset: 数据集

        Returns:
            版本哈希字符串
        """
        data_str = json.dumps(dataset.data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()[:12]

    def commit_version(self, dataset_id: str, message: Optional[str] = None) -> str:
        """提交一个新版本。

        Args:
            dataset_id: 数据集ID
            message: 提交说明

        Returns:
            新版本号

        Raises:
            ValueError: 当数据集不存在时
        """
        dataset = self.pool_manager.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError(f"数据集不存在: {dataset_id}")

        index = self._load_version_index(dataset_id)
        version_num = len(index) + 1
        version_hash = self._generate_version_hash(dataset)
        version = f"v{version_num}.0.0"

        version_data = dataset.to_dict()
        version_data["version"] = version

        version_file = self._get_version_file(dataset_id, version)
        os.makedirs(os.path.dirname(version_file), exist_ok=True)
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(version_data, f, ensure_ascii=False, indent=2)

        index_entry = {
            "version": version,
            "version_hash": version_hash,
            "message": message or "",
            "created_at": time.time(),
            "size": dataset.size,
            "record_count": dataset.record_count,
            "tags": [],
        }
        index.append(index_entry)
        self._save_version_index(dataset_id, index)

        return version

    def list_versions(self, dataset_id: str) -> List[dict]:
        """列出数据集的所有版本历史。

        Args:
            dataset_id: 数据集ID

        Returns:
            版本信息列表，按时间倒序排列（最新在前）
        """
        index = self._load_version_index(dataset_id)
        return list(reversed(index))

    def get_version(self, dataset_id: str, version: str) -> Optional[Dataset]:
        """获取指定版本的数据集。

        Args:
            dataset_id: 数据集ID
            version: 版本号

        Returns:
            指定版本的Dataset实例，如果不存在则返回None
        """
        version_file = self._get_version_file(dataset_id, version)
        if not os.path.exists(version_file):
            return None

        try:
            with open(version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Dataset.from_dict(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def revert_to_version(self, dataset_id: str, version: str) -> Optional[Dataset]:
        """回滚到指定版本。

        Args:
            dataset_id: 数据集ID
            version: 要回滚到的版本号

        Returns:
            回滚后的Dataset实例，如果版本不存在则返回None
        """
        version_dataset = self.get_version(dataset_id, version)
        if version_dataset is None:
            return None

        dataset = self.pool_manager.get_dataset(dataset_id)
        if dataset is None:
            return None

        dataset.data = version_dataset.data
        dataset.metadata = dict(version_dataset.metadata)
        dataset.tags = list(version_dataset.tags)
        dataset.updated_at = time.time()

        dataset_path = self.pool_manager._get_dataset_path(dataset_id)
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset.to_dict(), f, ensure_ascii=False, indent=2)

        self.pool_manager._index[dataset_id].update({
            "updated_at": dataset.updated_at,
            "size": dataset.size,
            "record_count": dataset.record_count,
        })
        self.pool_manager._save_index()

        return dataset

    def diff_versions(
        self,
        dataset_id: str,
        version1: str,
        version2: str,
    ) -> dict:
        """比较两个版本的差异。

        Args:
            dataset_id: 数据集ID
            version1: 第一个版本号
            version2: 第二个版本号

        Returns:
            差异信息字典

        Raises:
            ValueError: 当任一版本不存在时
        """
        ds1 = self.get_version(dataset_id, version1)
        ds2 = self.get_version(dataset_id, version2)

        if ds1 is None:
            raise ValueError(f"版本不存在: {version1}")
        if ds2 is None:
            raise ValueError(f"版本不存在: {version2}")

        diff: Dict[str, Any] = {
            "version1": version1,
            "version2": version2,
            "metadata_changes": {},
            "data_changes": {},
            "tag_changes": {
                "added": [],
                "removed": [],
            },
        }

        for attr in ["name", "description", "format", "quality_score"]:
            v1 = getattr(ds1, attr)
            v2 = getattr(ds2, attr)
            if v1 != v2:
                diff["metadata_changes"][attr] = {"old": v1, "new": v2}

        if ds1.size != ds2.size:
            diff["metadata_changes"]["size"] = {"old": ds1.size, "new": ds2.size}

        if ds1.record_count != ds2.record_count:
            diff["metadata_changes"]["record_count"] = {
                "old": ds1.record_count,
                "new": ds2.record_count,
            }

        data1 = ds1.data
        data2 = ds2.data

        if isinstance(data1, dict) and isinstance(data2, dict):
            all_keys = set(data1.keys()) | set(data2.keys())
            for key in all_keys:
                v1 = data1.get(key)
                v2 = data2.get(key)
                if v1 != v2:
                    diff["data_changes"][key] = {"old": v1, "new": v2}

        tags1_ids = {t.tag_id for t in ds1.tags}
        tags2_ids = {t.tag_id for t in ds2.tags}

        for tag in ds2.tags:
            if tag.tag_id not in tags1_ids:
                diff["tag_changes"]["added"].append(tag.to_dict())

        for tag in ds1.tags:
            if tag.tag_id not in tags2_ids:
                diff["tag_changes"]["removed"].append(tag.to_dict())

        return diff

    def tag_version(self, dataset_id: str, version: str, tag: str) -> bool:
        """为指定版本打标签。

        Args:
            dataset_id: 数据集ID
            version: 版本号
            tag: 标签名称

        Returns:
            是否成功打标签
        """
        index = self._load_version_index(dataset_id)
        found = False

        for entry in index:
            if entry["version"] == version:
                if "tags" not in entry:
                    entry["tags"] = []
                if tag not in entry["tags"]:
                    entry["tags"].append(tag)
                found = True
                break

        if found:
            self._save_version_index(dataset_id, index)

        return found

    def get_version_by_tag(self, dataset_id: str, tag: str) -> Optional[Dataset]:
        """按标签获取版本。

        Args:
            dataset_id: 数据集ID
            tag: 版本标签

        Returns:
            匹配标签的Dataset实例，如果未找到则返回None
        """
        index = self._load_version_index(dataset_id)

        for entry in reversed(index):
            if "tags" in entry and tag in entry["tags"]:
                return self.get_version(dataset_id, entry["version"])

        return None
