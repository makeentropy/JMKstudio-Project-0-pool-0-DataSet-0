"""标签索引与检索模块。

提供Karma标签的索引、搜索和统计功能，支持多种过滤条件和持久化存储。
"""
from __future__ import annotations

import json
import pickle
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .karma_tag import KarmaTag


class TagIndex:
    """标签索引类。

    提供Karma标签的内存索引和检索功能，支持多种过滤条件：
    - 按datafor过滤
    - 按datefor过滤
    - 按datatag标签过滤
    - 按tag标签过滤
    - 按签名者过滤
    - 按日期范围过滤
    - 支持分页和排序

    Attributes:
        _tags: 标签字典，键为tag_id，值为(标签, 数据集ID)元组
        _datafor_index: datafor字段倒排索引
        _datefor_index: datefor字段倒排索引
        _datatag_index: datatag字段倒排索引
        _tag_index: tag字段倒排索引
        _signer_index: 签名者倒排索引
    """

    def __init__(self) -> None:
        """初始化标签索引。"""
        self._tags: dict[str, Tuple[KarmaTag, Optional[str]]] = {}
        self._datafor_index: dict[str, set[str]] = defaultdict(set)
        self._datefor_index: dict[str, set[str]] = defaultdict(set)
        self._datatag_index: dict[str, set[str]] = defaultdict(set)
        self._tag_index: dict[str, set[str]] = defaultdict(set)
        self._signer_index: dict[str, set[str]] = defaultdict(set)

    def add_tag(self, tag: KarmaTag, dataset_id: Optional[str] = None) -> None:
        """添加标签到索引。

        Args:
            tag: 要添加的Karma标签
            dataset_id: 关联的数据集ID，可选
        """
        tag_id = tag.tag_id
        self._tags[tag_id] = (tag, dataset_id)

        if tag.datafor:
            self._datafor_index[tag.datafor].add(tag_id)

        if tag.datefor:
            self._datefor_index[tag.datefor].add(tag_id)

        for dt in tag.datatag:
            if dt:
                self._datatag_index[dt].add(tag_id)

        for t in tag.tag:
            if t:
                self._tag_index[t].add(tag_id)

        if tag.gpgca:
            self._signer_index["gpgca"].add(tag_id)

        if tag.jmkca:
            self._signer_index["jmkca"].add(tag_id)

        custom_sig = tag.get_custom_field("custom_signature")
        if custom_sig:
            self._signer_index["custom"].add(tag_id)

    def remove_tag(self, tag_id: str) -> bool:
        """从索引中移除标签。

        Args:
            tag_id: 要移除的标签ID

        Returns:
            移除成功返回True，标签不存在返回False
        """
        if tag_id not in self._tags:
            return False

        tag, _ = self._tags[tag_id]

        if tag.datafor and tag_id in self._datafor_index.get(tag.datafor, set()):
            self._datafor_index[tag.datafor].discard(tag_id)
            if not self._datafor_index[tag.datafor]:
                del self._datafor_index[tag.datafor]

        if tag.datefor and tag_id in self._datefor_index.get(tag.datefor, set()):
            self._datefor_index[tag.datefor].discard(tag_id)
            if not self._datefor_index[tag.datefor]:
                del self._datefor_index[tag.datefor]

        for dt in tag.datatag:
            if dt and tag_id in self._datatag_index.get(dt, set()):
                self._datatag_index[dt].discard(tag_id)
                if not self._datatag_index[dt]:
                    del self._datatag_index[dt]

        for t in tag.tag:
            if t and tag_id in self._tag_index.get(t, set()):
                self._tag_index[t].discard(tag_id)
                if not self._tag_index[t]:
                    del self._tag_index[t]

        if tag.gpgca and tag_id in self._signer_index.get("gpgca", set()):
            self._signer_index["gpgca"].discard(tag_id)
            if not self._signer_index["gpgca"]:
                del self._signer_index["gpgca"]

        if tag.jmkca and tag_id in self._signer_index.get("jmkca", set()):
            self._signer_index["jmkca"].discard(tag_id)
            if not self._signer_index["jmkca"]:
                del self._signer_index["jmkca"]

        custom_sig = tag.get_custom_field("custom_signature")
        if custom_sig and tag_id in self._signer_index.get("custom", set()):
            self._signer_index["custom"].discard(tag_id)
            if not self._signer_index["custom"]:
                del self._signer_index["custom"]

        del self._tags[tag_id]
        return True

    def search(self, filters: dict[str, Any]) -> List[Tuple[KarmaTag, Optional[str]]]:
        """搜索标签。

        支持的过滤条件：
        - datafor: str - 按数据用途精确匹配
        - datefor: str - 按数据日期精确匹配
        - datatag: str或List[str] - 按数据标签过滤（包含任一标签即可）
        - tag: str或List[str] - 按通用标签过滤（包含任一标签即可）
        - signer: str或List[str] - 按签名者过滤
        - date_range: Tuple[str, str] - 日期范围（起始日期, 结束日期），YYYYMMDD格式
        - dataset_id: str - 按数据集ID过滤

        Args:
            filters: 过滤条件字典

        Returns:
            匹配的标签列表，每项为(标签, 数据集ID)元组
        """
        if not filters:
            return list(self._tags.values())

        candidate_ids: Optional[set[str]] = None

        if "datafor" in filters:
            datafor = filters["datafor"]
            ids = self._datafor_index.get(datafor, set())
            candidate_ids = self._intersect(candidate_ids, ids)

        if "datefor" in filters:
            datefor = filters["datefor"]
            ids = self._datefor_index.get(datefor, set())
            candidate_ids = self._intersect(candidate_ids, ids)

        if "datatag" in filters:
            datatags = filters["datatag"]
            if isinstance(datatags, str):
                datatags = [datatags]
            ids: set[str] = set()
            for dt in datatags:
                ids.update(self._datatag_index.get(dt, set()))
            candidate_ids = self._intersect(candidate_ids, ids)

        if "tag" in filters:
            tags = filters["tag"]
            if isinstance(tags, str):
                tags = [tags]
            ids = set()
            for t in tags:
                ids.update(self._tag_index.get(t, set()))
            candidate_ids = self._intersect(candidate_ids, ids)

        if "signer" in filters:
            signers = filters["signer"]
            if isinstance(signers, str):
                signers = [signers]
            ids = set()
            for s in signers:
                ids.update(self._signer_index.get(s, set()))
            candidate_ids = self._intersect(candidate_ids, ids)

        if "date_range" in filters:
            start_date, end_date = filters["date_range"]
            ids = set()
            for datefor, tag_ids in self._datefor_index.items():
                if start_date <= datefor <= end_date:
                    ids.update(tag_ids)
            candidate_ids = self._intersect(candidate_ids, ids)

        if "dataset_id" in filters:
            dataset_id = filters["dataset_id"]
            ids = set()
            for tid, (_, did) in self._tags.items():
                if did == dataset_id:
                    ids.add(tid)
            candidate_ids = self._intersect(candidate_ids, ids)

        if candidate_ids is None:
            return list(self._tags.values())

        return [self._tags[tid] for tid in candidate_ids if tid in self._tags]

    def _intersect(
        self,
        a: Optional[set[str]],
        b: set[str],
    ) -> set[str]:
        """计算两个集合的交集。

        如果a为None，直接返回b。

        Args:
            a: 第一个集合，可为None
            b: 第二个集合

        Returns:
            交集结果
        """
        if a is None:
            return b
        return a & b

    def get_by_id(self, tag_id: str) -> Optional[Tuple[KarmaTag, Optional[str]]]:
        """按ID获取标签。

        Args:
            tag_id: 标签ID

        Returns:
            (标签, 数据集ID)元组，如果不存在则返回None
        """
        return self._tags.get(tag_id)

    def list_tags(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KarmaTag]:
        """列出标签（分页）。

        Args:
            limit: 每页数量，默认为100
            offset: 偏移量，默认为0

        Returns:
            标签列表
        """
        tag_list = list(self._tags.values())
        return [tag for tag, _ in tag_list[offset : offset + limit]]

    def get_tag_statistics(self) -> dict[str, Any]:
        """获取标签统计信息。

        Returns:
            统计信息字典，包含：
            - total_tags: 标签总数
            - unique_datafor: 不同datafor的数量
            - unique_datefor: 不同datefor的数量
            - unique_datatag: 不同datatag的数量
            - unique_tag: 不同tag的数量
            - signed_count: 已签名的标签数量
            - signer_distribution: 各签名者的标签数量
            - dataset_count: 不同数据集的数量
        """
        total_tags = len(self._tags)

        signed_count = 0
        signer_dist: dict[str, int] = {}
        for signer, ids in self._signer_index.items():
            signer_dist[signer] = len(ids)
            signed_count += len(ids)

        dataset_ids = set()
        for _, did in self._tags.values():
            if did:
                dataset_ids.add(did)

        return {
            "total_tags": total_tags,
            "unique_datafor": len(self._datafor_index),
            "unique_datefor": len(self._datefor_index),
            "unique_datatag": len(self._datatag_index),
            "unique_tag": len(self._tag_index),
            "signed_count": signed_count,
            "signer_distribution": signer_dist,
            "dataset_count": len(dataset_ids),
        }

    def build_index(self, tags: List[KarmaTag]) -> None:
        """批量构建索引。

        Args:
            tags: 标签列表
        """
        for tag in tags:
            self.add_tag(tag)

    def save_index(self, filepath: str) -> None:
        """保存索引到文件。

        使用pickle序列化索引数据。

        Args:
            filepath: 保存文件路径
        """
        data = {
            "tags": [(tag.to_dict(), dataset_id) for tag, dataset_id in self._tags.values()],
        }
        with open(filepath, "wb") as f:
            pickle.dump(data, f)

    def load_index(self, filepath: str) -> None:
        """从文件加载索引。

        Args:
            filepath: 加载文件路径
        """
        with open(filepath, "rb") as f:
            data = pickle.load(f)

        self._tags.clear()
        self._datafor_index.clear()
        self._datefor_index.clear()
        self._datatag_index.clear()
        self._tag_index.clear()
        self._signer_index.clear()

        for tag_dict, dataset_id in data["tags"]:
            tag = KarmaTag.from_dict(tag_dict)
            self.add_tag(tag, dataset_id)

    def save_json(self, filepath: str) -> None:
        """保存索引为JSON格式。

        Args:
            filepath: 保存文件路径
        """
        data = {
            "tags": [(tag.to_dict(), dataset_id) for tag, dataset_id in self._tags.values()],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_json(self, filepath: str) -> None:
        """从JSON文件加载索引。

        Args:
            filepath: 加载文件路径
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._tags.clear()
        self._datafor_index.clear()
        self._datefor_index.clear()
        self._datatag_index.clear()
        self._tag_index.clear()
        self._signer_index.clear()

        for tag_dict, dataset_id in data["tags"]:
            tag = KarmaTag.from_dict(tag_dict)
            self.add_tag(tag, dataset_id)

    def __len__(self) -> int:
        """返回索引中的标签数量。"""
        return len(self._tags)

    def __contains__(self, tag_id: str) -> bool:
        """检查标签是否存在（支持in运算符）。"""
        return tag_id in self._tags
