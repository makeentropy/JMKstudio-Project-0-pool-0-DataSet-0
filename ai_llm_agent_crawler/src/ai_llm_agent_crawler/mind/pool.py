"""
数据池管理模块

提供数据池存储、索引、检索、更新等功能。
"""

import heapq
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.mind.models import (
    DataPool,
    MindDataRecord,
    MindDataset,
    MindDataType,
    PoolConfig,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class PoolIndex:
    """数据池索引"""

    def __init__(self):
        self._record_index: Dict[str, MindDataRecord] = {}
        self._tag_index: Dict[str, set] = {}
        self._type_index: Dict[str, set] = {}
        self._quality_heap: List[Tuple[float, str]] = []
        self._access_order: OrderedDict = OrderedDict()

    def add(self, record: MindDataRecord) -> None:
        rid = record.record_id
        self._record_index[rid] = record

        for tag in record.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(rid)

        type_key = record.data_type.value
        if type_key not in self._type_index:
            self._type_index[type_key] = set()
        self._type_index[type_key].add(rid)

        heapq.heappush(self._quality_heap, (-record.quality_score, rid))
        self._access_order[rid] = time.time()

    def remove(self, record_id: str) -> bool:
        if record_id not in self._record_index:
            return False

        record = self._record_index[record_id]

        for tag in record.tags:
            if tag in self._tag_index and record_id in self._tag_index[tag]:
                self._tag_index[tag].remove(record_id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        type_key = record.data_type.value
        if type_key in self._type_index and record_id in self._type_index[type_key]:
            self._type_index[type_key].remove(record_id)
            if not self._type_index[type_key]:
                del self._type_index[type_key]

        del self._record_index[record_id]
        if record_id in self._access_order:
            del self._access_order[record_id]

        return True

    def get(self, record_id: str) -> Optional[MindDataRecord]:
        if record_id in self._record_index:
            self._access_order[record_id] = time.time()
            self._access_order.move_to_end(record_id)
            return self._record_index[record_id]
        return None

    def get_by_tag(self, tag: str) -> List[MindDataRecord]:
        ids = self._tag_index.get(tag, set())
        return [self._record_index[i] for i in ids if i in self._record_index]

    def get_by_type(self, data_type: MindDataType) -> List[MindDataRecord]:
        ids = self._type_index.get(data_type.value, set())
        return [self._record_index[i] for i in ids if i in self._record_index]

    def get_top_quality(self, n: int = 10) -> List[MindDataRecord]:
        results = []
        seen = set()
        temp_heap = self._quality_heap.copy()

        while temp_heap and len(results) < n:
            neg_score, rid = heapq.heappop(temp_heap)
            if rid in self._record_index and rid not in seen:
                seen.add(rid)
                results.append(self._record_index[rid])

        return results

    def get_least_recently_used(self, n: int = 10) -> List[MindDataRecord]:
        sorted_ids = sorted(self._access_order.keys(), key=lambda k: self._access_order[k])
        results = []
        for rid in sorted_ids[:n]:
            if rid in self._record_index:
                results.append(self._record_index[rid])
        return results

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        data_type: Optional[MindDataType] = None,
        min_quality: float = 0.0,
        limit: int = 50,
    ) -> List[MindDataRecord]:
        candidate_ids: Optional[set] = None

        if tags:
            candidate_ids = set()
            for tag in tags:
                candidate_ids |= self._tag_index.get(tag, set())

        if data_type:
            type_ids = self._type_index.get(data_type.value, set())
            if candidate_ids is None:
                candidate_ids = type_ids
            else:
                candidate_ids &= type_ids

        if candidate_ids is None:
            candidate_ids = set(self._record_index.keys())

        results = []
        for rid in candidate_ids:
            record = self._record_index.get(rid)
            if not record:
                continue
            if record.quality_score < min_quality:
                continue
            if query and query.lower() not in record.content.lower():
                continue
            results.append(record)

        results.sort(key=lambda r: r.quality_score, reverse=True)
        return results[:limit]

    def size(self) -> int:
        return len(self._record_index)

    def all_records(self) -> List[MindDataRecord]:
        return list(self._record_index.values())

    def get_all_tags(self) -> List[str]:
        return list(self._tag_index.keys())

    def get_type_counts(self) -> Dict[str, int]:
        return {k: len(v) for k, v in self._type_index.items()}


class PoolRetriever:
    """数据池检索器"""

    def __init__(self, index: PoolIndex):
        self.index = index
        self.logger = get_logger(f"{__name__}.PoolRetriever")

    def retrieve_by_similarity(
        self,
        query_vector: np.ndarray,
        vector_type: str = "semantic",
        top_k: int = 10,
        data_type: Optional[MindDataType] = None,
        min_quality: float = 0.0,
    ) -> List[Tuple[MindDataRecord, float]]:
        candidates = self.index.get_by_type(data_type) if data_type else self.index.all_records()

        scored = []
        for record in candidates:
            if record.quality_score < min_quality:
                continue
            record_vec = record.get_vector(vector_type)
            if not record_vec:
                continue
            sim = self._cosine_similarity(query_vector, record_vec.to_numpy())
            scored.append((record, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def retrieve_by_keywords(
        self,
        keywords: List[str],
        top_k: int = 20,
    ) -> List[MindDataRecord]:
        results = set()
        for kw in keywords:
            tag_results = self.index.get_by_tag(kw)
            results.update(tag_results)

        text_results = self.index.search(query=" ".join(keywords), limit=top_k)
        results.update(text_results)

        sorted_results = sorted(results, key=lambda r: r.quality_score, reverse=True)
        return sorted_results[:top_k]

    def retrieve_by_quality(
        self,
        data_type: Optional[MindDataType] = None,
        min_quality: float = 0.7,
        top_k: int = 20,
    ) -> List[MindDataRecord]:
        return self.index.search(
            query="",
            data_type=data_type,
            min_quality=min_quality,
            limit=top_k,
        )

    def retrieve_diverse(
        self,
        query_vector: np.ndarray,
        vector_type: str = "semantic",
        top_k: int = 10,
        diversity: float = 0.5,
    ) -> List[MindDataRecord]:
        initial = self.retrieve_by_similarity(query_vector, vector_type, top_k * 3)

        if len(initial) <= top_k:
            return [r[0] for r in initial]

        selected = [initial[0][0]]
        for record, sim in initial[1:]:
            if len(selected) >= top_k:
                break

            max_sim_to_selected = max(
                self._cosine_similarity(
                    record.get_vector(vector_type).to_numpy() if record.get_vector(vector_type) else np.zeros(1),
                    s.get_vector(vector_type).to_numpy() if s.get_vector(vector_type) else np.zeros(1),
                )
                for s in selected
            )

            diversity_score = (1 - diversity) * sim + diversity * (1 - max_sim_to_selected)
            if diversity_score > 0.5:
                selected.append(record)

        return selected[:top_k]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        if a.shape != b.shape:
            return 0.0
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


class PoolUpdater:
    """数据池更新器"""

    def __init__(self, index: PoolIndex, config: PoolConfig):
        self.index = index
        self.config = config
        self._last_prune_time: float = 0
        self.logger = get_logger(f"{__name__}.PoolUpdater")

    def add_record(self, record: MindDataRecord) -> bool:
        if self.index.size() >= self.config.max_records:
            if self.config.auto_prune:
                self._prune()
            else:
                self.logger.warning("Pool is full, cannot add record")
                return False

        if record.quality_score < self.config.quality_threshold:
            return False

        self.index.add(record)
        return True

    def add_dataset(self, dataset: MindDataset) -> int:
        count = 0
        for record in dataset.records:
            if self.add_record(record):
                count += 1
        self.logger.info(f"Added {count}/{len(dataset.records)} records from dataset")
        return count

    def update_record(self, record_id: str, updates: Dict[str, Any]) -> bool:
        record = self.index.get(record_id)
        if not record:
            return False

        for key, value in updates.items():
            if hasattr(record, key):
                setattr(record, key, value)

        return True

    def remove_record(self, record_id: str) -> bool:
        return self.index.remove(record_id)

    def _prune(self) -> int:
        if not self.config.auto_prune:
            return 0

        current_time = time.time()
        if current_time - self._last_prune_time < self.config.prune_interval_seconds:
            return 0

        target_size = int(self.config.max_records * 0.8)
        records_to_remove = self.index.size() - target_size
        if records_to_remove <= 0:
            return 0

        lru_records = self.index.get_least_recently_used(records_to_remove)
        removed = 0
        for record in lru_records:
            if self.index.remove(record.record_id):
                removed += 1

        self._last_prune_time = current_time
        self.logger.info(f"Pruned {removed} records from pool")
        return removed

    def refresh_quality_scores(self, scorer: Callable[[MindDataRecord], float]) -> int:
        updated = 0
        for record in self.index.all_records():
            new_score = scorer(record)
            if abs(new_score - record.quality_score) > 0.01:
                record.quality_score = new_score
                updated += 1
        self.logger.info(f"Updated quality scores for {updated} records")
        return updated


class MultiPoolRouter:
    """多池路由器"""

    def __init__(self):
        self._pools: Dict[str, DataPoolManager] = {}
        self._routing_rules: List[Dict[str, Any]] = []
        self.logger = get_logger(f"{__name__}.MultiPoolRouter")

    def add_pool(self, pool: "DataPoolManager", name: str) -> None:
        self._pools[name] = pool

    def remove_pool(self, name: str) -> bool:
        if name in self._pools:
            del self._pools[name]
            return True
        return False

    def get_pool(self, name: str) -> Optional["DataPoolManager"]:
        return self._pools.get(name)

    def add_routing_rule(
        self,
        condition: Callable[[MindDataRecord], bool],
        pool_name: str,
        priority: int = 0,
    ) -> None:
        self._routing_rules.append({
            "condition": condition,
            "pool_name": pool_name,
            "priority": priority,
        })
        self._routing_rules.sort(key=lambda r: r["priority"], reverse=True)

    def route_record(self, record: MindDataRecord) -> Optional[str]:
        for rule in self._routing_rules:
            if rule["condition"](record):
                return rule["pool_name"]
        return None

    def add_record(self, record: MindDataRecord) -> bool:
        pool_name = self.route_record(record)
        if pool_name and pool_name in self._pools:
            return self._pools[pool_name].add_record(record)
        return False

    def search_all(
        self,
        query_vector: np.ndarray,
        vector_type: str = "semantic",
        top_k: int = 10,
    ) -> List[Tuple[MindDataRecord, float, str]]:
        all_results = []
        for name, pool in self._pools.items():
            results = pool.search_by_vector(query_vector, vector_type, top_k)
            for record, score in results:
                all_results.append((record, score, name))

        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:top_k]


class DataPoolManager:
    """数据池管理器 - 整合索引、检索和更新"""

    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig()
        self.index = PoolIndex()
        self.retriever = PoolRetriever(self.index)
        self.updater = PoolUpdater(self.index, self.config)
        self.pool = DataPool(config=self.config)
        self.logger = get_logger(f"{__name__}.DataPoolManager")

    def add_record(self, record: MindDataRecord) -> bool:
        return self.updater.add_record(record)

    def add_dataset(self, dataset: MindDataset) -> int:
        return self.updater.add_dataset(dataset)

    def get_record(self, record_id: str) -> Optional[MindDataRecord]:
        return self.index.get(record_id)

    def search_by_vector(
        self,
        query_vector: np.ndarray,
        vector_type: str = "semantic",
        top_k: int = 10,
        data_type: Optional[MindDataType] = None,
        min_quality: float = 0.0,
    ) -> List[Tuple[MindDataRecord, float]]:
        return self.retriever.retrieve_by_similarity(
            query_vector, vector_type, top_k, data_type, min_quality
        )

    def search_by_keywords(
        self,
        keywords: List[str],
        top_k: int = 20,
    ) -> List[MindDataRecord]:
        return self.retriever.retrieve_by_keywords(keywords, top_k)

    def get_by_type(self, data_type: MindDataType) -> List[MindDataRecord]:
        return self.index.get_by_type(data_type)

    def get_by_tag(self, tag: str) -> List[MindDataRecord]:
        return self.index.get_by_tag(tag)

    def get_top_quality(self, n: int = 10) -> List[MindDataRecord]:
        return self.index.get_top_quality(n)

    def get_diverse(
        self,
        query_vector: np.ndarray,
        vector_type: str = "semantic",
        top_k: int = 10,
        diversity: float = 0.5,
    ) -> List[MindDataRecord]:
        return self.retriever.retrieve_diverse(query_vector, vector_type, top_k, diversity)

    def remove_record(self, record_id: str) -> bool:
        return self.updater.remove_record(record_id)

    def size(self) -> int:
        return self.index.size()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_records": self.index.size(),
            "type_counts": self.index.get_type_counts(),
            "total_tags": len(self.index.get_all_tags()),
            "max_records": self.config.max_records,
            "quality_threshold": self.config.quality_threshold,
        }

    def get_all_records(self) -> List[MindDataRecord]:
        return self.index.all_records()
