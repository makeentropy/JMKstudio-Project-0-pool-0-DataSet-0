"""数据集数据结构模块。

定义数据集的核心数据结构，支持标准字段和数据内容存储，
提供序列化、反序列化和标签管理功能。
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, List, Optional, Union

from ..karma_tags.karma_tag import KarmaTag


class Dataset:
    """数据集类。

    用于表示和管理一个数据集的完整信息，包括元数据、标签、
    数据内容和质量评分等。

    Attributes:
        dataset_id: 数据集唯一标识
        name: 数据集名称
        description: 数据集描述
        created_at: 创建时间戳
        updated_at: 更新时间戳
        version: 版本号
        size: 数据大小（字节）
        record_count: 记录数
        format: 数据格式（json/csv/yaml等）
        tags: Karma标签列表
        metadata: 元数据字典
        quality_score: 质量评分（0-100）
        _data: 数据内容（dict或bytes）
    """

    def __init__(
        self,
        dataset_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """初始化数据集。

        Args:
            dataset_id: 数据集ID，如未提供则自动生成
            name: 数据集名称
        """
        now = time.time()
        self.dataset_id: str = dataset_id or str(uuid.uuid4())
        self.name: str = name or ""
        self.description: str = ""
        self.created_at: float = now
        self.updated_at: float = now
        self.version: str = "1.0.0"
        self.size: int = 0
        self.record_count: int = 0
        self.format: str = "json"
        self.tags: List[KarmaTag] = []
        self.metadata: dict[str, Any] = {}
        self.quality_score: float = 0.0
        self._data: Union[dict[str, Any], bytes, None] = None

    @property
    def data(self) -> Union[dict[str, Any], bytes, None]:
        """获取数据内容。

        Returns:
            数据内容（dict或bytes）
        """
        return self._data

    @data.setter
    def data(self, value: Union[dict[str, Any], bytes, None]) -> None:
        """设置数据内容并更新大小和记录数。

        Args:
            value: 数据内容
        """
        self._data = value
        self._update_size_and_count()
        self.updated_at = time.time()

    def _update_size_and_count(self) -> None:
        """更新数据大小和记录数。"""
        if self._data is None:
            self.size = 0
            self.record_count = 0
        elif isinstance(self._data, bytes):
            self.size = len(self._data)
            self.record_count = 0
        elif isinstance(self._data, dict):
            try:
                json_str = json.dumps(self._data, ensure_ascii=False)
                self.size = len(json_str.encode("utf-8"))
            except (TypeError, ValueError):
                self.size = 0
            if "records" in self._data and isinstance(self._data["records"], list):
                self.record_count = len(self._data["records"])
            elif "items" in self._data and isinstance(self._data["items"], list):
                self.record_count = len(self._data["items"])
            else:
                self.record_count = 1
        else:
            self.size = 0
            self.record_count = 0

    def to_dict(self) -> dict[str, Any]:
        """将数据集序列化为字典。

        Returns:
            包含所有数据集信息的字典
        """
        result: dict[str, Any] = {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "size": self.size,
            "record_count": self.record_count,
            "format": self.format,
            "tags": [tag.to_dict() for tag in self.tags],
            "metadata": dict(self.metadata),
            "quality_score": self.quality_score,
        }

        if self._data is not None:
            if isinstance(self._data, bytes):
                import base64
                result["data"] = {
                    "type": "bytes",
                    "content": base64.b64encode(self._data).decode("utf-8"),
                }
            else:
                result["data"] = {
                    "type": "dict",
                    "content": self._data,
                }

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dataset":
        """从字典创建数据集实例。

        Args:
            data: 包含数据集信息的字典

        Returns:
            创建的Dataset实例
        """
        dataset = cls(
            dataset_id=data.get("dataset_id"),
            name=data.get("name"),
        )
        dataset.description = data.get("description", "")
        dataset.created_at = data.get("created_at", time.time())
        dataset.updated_at = data.get("updated_at", time.time())
        dataset.version = data.get("version", "1.0.0")
        dataset.size = data.get("size", 0)
        dataset.record_count = data.get("record_count", 0)
        dataset.format = data.get("format", "json")
        dataset.quality_score = data.get("quality_score", 0.0)
        dataset.metadata = dict(data.get("metadata", {}))

        tags_data = data.get("tags", [])
        dataset.tags = [KarmaTag.from_dict(tag_data) for tag_data in tags_data]

        if "data" in data and data["data"] is not None:
            data_info = data["data"]
            if data_info.get("type") == "bytes":
                import base64
                dataset._data = base64.b64decode(data_info["content"])
            else:
                dataset._data = data_info.get("content")

        return dataset

    def add_tag(self, tag: KarmaTag) -> None:
        """添加Karma标签。

        Args:
            tag: 要添加的Karma标签
        """
        existing_ids = {t.tag_id for t in self.tags}
        if tag.tag_id not in existing_ids:
            self.tags.append(tag)
            self.updated_at = time.time()

    def remove_tag(self, tag_id: str) -> bool:
        """移除指定ID的Karma标签。

        Args:
            tag_id: 要移除的标签ID

        Returns:
            是否成功移除
        """
        for i, tag in enumerate(self.tags):
            if tag.tag_id == tag_id:
                self.tags.pop(i)
                self.updated_at = time.time()
                return True
        return False

    def get_tags(self) -> List[KarmaTag]:
        """获取所有Karma标签。

        Returns:
            标签列表的副本
        """
        return list(self.tags)

    def __repr__(self) -> str:
        """返回数据集的字符串表示。"""
        return f"<Dataset id='{self.dataset_id}' name='{self.name}' version='{self.version}'>"

    def __str__(self) -> str:
        """返回数据集的可读字符串。"""
        return f"Dataset[{self.dataset_id}]: {self.name} (v{self.version}, {self.record_count} records)"

    def __eq__(self, other: object) -> bool:
        """判断两个数据集是否相等。

        基于dataset_id进行比较。
        """
        if not isinstance(other, Dataset):
            return NotImplemented
        return self.dataset_id == other.dataset_id

    def __hash__(self) -> int:
        """返回数据集的哈希值。

        基于dataset_id计算哈希。
        """
        return hash(self.dataset_id)
