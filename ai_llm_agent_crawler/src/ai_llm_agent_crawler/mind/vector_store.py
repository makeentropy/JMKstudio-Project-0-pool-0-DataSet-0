"""
向量存储模块

提供向量索引、相似度搜索等功能，支持Flat、HNSW、IVF等索引类型。
"""

import heapq
import math
import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.mind.models import (
    VectorIndexConfig,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class VectorSearchResult:
    """向量搜索结果"""

    def __init__(self, id: str, vector: np.ndarray, score: float, metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.vector = vector
        self.score = score
        self.metadata = metadata or {}


class VectorIndex:
    """向量索引基类"""

    def __init__(self, config: VectorIndexConfig):
        self.config = config
        self.dimensions = config.dimensions
        self.metric = config.metric
        self._vectors: Dict[str, np.ndarray] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._is_built = False

    def add(self, id: str, vector: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if len(vector) != self.dimensions:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimensions}, got {len(vector)}")
        self._vectors[id] = vector.copy()
        if metadata:
            self._metadata[id] = metadata
        self._is_built = False
        return True

    def add_batch(
        self,
        ids: List[str],
        vectors: List[np.ndarray],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        count = 0
        for i, (id, vec) in enumerate(zip(ids, vectors)):
            meta = metadatas[i] if metadatas and i < len(metadatas) else None
            if self.add(id, vec, meta):
                count += 1
        return count

    def remove(self, id: str) -> bool:
        if id in self._vectors:
            del self._vectors[id]
            if id in self._metadata:
                del self._metadata[id]
            self._is_built = False
            return True
        return False

    def get(self, id: str) -> Optional[np.ndarray]:
        return self._vectors.get(id)

    def build(self) -> None:
        self._is_built = True

    def search(
        self,
        query: np.ndarray,
        top_k: int = 10,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[VectorSearchResult]:
        raise NotImplementedError

    def size(self) -> int:
        return len(self._vectors)

    def _distance(self, a: np.ndarray, b: np.ndarray) -> float:
        if self.metric == "cosine":
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 1.0
            return 1.0 - float(np.dot(a, b) / (norm_a * norm_b))
        elif self.metric == "euclidean":
            return float(np.linalg.norm(a - b))
        elif self.metric == "dot_product":
            return -float(np.dot(a, b))
        else:
            return float(np.linalg.norm(a - b))

    def _similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return 1.0 - self._distance(a, b)


class FlatIndex(VectorIndex):
    """Flat索引 - 暴力搜索"""

    def __init__(self, config: VectorIndexConfig):
        super().__init__(config)

    def search(
        self,
        query: np.ndarray,
        top_k: int = 10,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[VectorSearchResult]:
        if len(query) != self.dimensions:
            raise ValueError(f"Query dimension mismatch")

        results = []
        for id, vec in self._vectors.items():
            if filter_fn and id in self._metadata:
                if not filter_fn(self._metadata[id]):
                    continue
            score = self._similarity(query, vec)
            results.append(VectorSearchResult(id, vec, score, self._metadata.get(id)))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


class HNSWNode:
    """HNSW节点"""

    def __init__(self, id: str, vector: np.ndarray, max_level: int = 0):
        self.id = id
        self.vector = vector
        self.max_level = max_level
        self.connections: List[List[str]] = [[] for _ in range(max_level + 1)]


class HNSWIndex(VectorIndex):
    """HNSW索引 - 分层导航小世界图"""

    def __init__(self, config: VectorIndexConfig):
        super().__init__(config)
        self.M = config.M
        self.ef_construction = config.ef_construction
        self.ef_search = config.ef_search
        self._nodes: Dict[str, HNSWNode] = {}
        self._entry_point: Optional[str] = None
        self._max_level = 0
        self._level_multiplier = 1.0 / math.log(self.M)

    def add(self, id: str, vector: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if len(vector) != self.dimensions:
            raise ValueError(f"Vector dimension mismatch")

        super().add(id, vector, metadata)

        level = self._select_level()
        node = HNSWNode(id, vector, max(level, 0))
        self._nodes[id] = node

        if self._entry_point is None:
            self._entry_point = id
            self._max_level = level
            return True

        current = self._entry_point
        for l in range(self._max_level, level, -1):
            current = self._search_layer(vector, current, 1, l)[0]

        for l in range(min(level, self._max_level), -1, -1):
            neighbors = self._search_layer(vector, current, self.ef_construction, l)
            selected = self._select_neighbors(vector, neighbors, self.M, l)
            node.connections[l] = selected

            for neighbor_id in selected:
                if neighbor_id in self._nodes:
                    neighbor_node = self._nodes[neighbor_id]
                    neighbor_node.connections[l].append(id)
                    if len(neighbor_node.connections[l]) > self.M * 2:
                        neighbor_node.connections[l] = self._select_neighbors(
                            self._nodes[neighbor_id].vector,
                            neighbor_node.connections[l],
                            self.M,
                            l,
                        )

            if neighbors:
                current = neighbors[0]

        if level > self._max_level:
            self._entry_point = id
            self._max_level = level

        self._is_built = True
        return True

    def _select_level(self) -> int:
        r = random.random()
        if r == 0:
            return 0
        level = int(-math.log(r) * self._level_multiplier)
        return min(level, 16)

    def _search_layer(
        self,
        query: np.ndarray,
        entry: str,
        ef: int,
        level: int,
    ) -> List[str]:
        if entry not in self._nodes:
            return []

        visited = set([entry])
        candidates = [(self._distance(query, self._nodes[entry].vector), entry)]
        results = [(self._distance(query, self._nodes[entry].vector), entry)]

        while candidates:
            current_dist, current = heapq.heappop(candidates)
            if results and current_dist > results[0][0]:
                break

            if current in self._nodes:
                node = self._nodes[current]
                if level < len(node.connections):
                    for neighbor in node.connections[level]:
                        if neighbor not in visited and neighbor in self._nodes:
                            visited.add(neighbor)
                            dist = self._distance(query, self._nodes[neighbor].vector)
                            heapq.heappush(candidates, (dist, neighbor))
                            if len(results) < ef:
                                heapq.heappush(results, (dist, neighbor))
                            elif dist < results[0][0]:
                                heapq.heapreplace(results, (dist, neighbor))

        return [r[1] for r in sorted(results, key=lambda x: x[0])]

    def _select_neighbors(
        self,
        query: np.ndarray,
        candidates: List[str],
        M: int,
        level: int,
    ) -> List[str]:
        scored = []
        for c in candidates:
            if c in self._nodes:
                dist = self._distance(query, self._nodes[c].vector)
                scored.append((dist, c))
        scored.sort(key=lambda x: x[0])
        return [s[1] for s in scored[:M]]

    def search(
        self,
        query: np.ndarray,
        top_k: int = 10,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[VectorSearchResult]:
        if len(query) != self.dimensions or self._entry_point is None:
            return []

        current = self._entry_point
        for l in range(self._max_level, 0, -1):
            layer_result = self._search_layer(query, current, 1, l)
            if layer_result:
                current = layer_result[0]

        ef = max(self.ef_search, top_k)
        candidates = self._search_layer(query, current, ef, 0)

        results = []
        for c in candidates:
            if c in self._nodes:
                if filter_fn and c in self._metadata:
                    if not filter_fn(self._metadata[c]):
                        continue
                score = self._similarity(query, self._nodes[c].vector)
                results.append(VectorSearchResult(c, self._nodes[c].vector, score, self._metadata.get(c)))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def build(self) -> None:
        self._is_built = True


class IVFIndex(VectorIndex):
    """IVF索引 - 倒排文件"""

    def __init__(self, config: VectorIndexConfig):
        super().__init__(config)
        self.nlist = config.nlist
        self.nprobe = config.nprobe
        self._centroids: Optional[np.ndarray] = None
        self._inverted_lists: List[List[str]] = []
        self._is_trained = False

    def train(self, vectors: np.ndarray) -> None:
        n = len(vectors)
        if n < self.nlist:
            self.nlist = max(1, n)

        indices = np.random.choice(n, self.nlist, replace=False)
        self._centroids = vectors[indices].copy()

        for _ in range(10):
            assignments = [[] for _ in range(self.nlist)]
            for i, v in enumerate(vectors):
                dists = np.linalg.norm(self._centroids - v, axis=1)
                cluster = np.argmin(dists)
                assignments[cluster].append(i)

            for j in range(self.nlist):
                if assignments[j]:
                    cluster_vectors = vectors[assignments[j]]
                    self._centroids[j] = np.mean(cluster_vectors, axis=0)

        self._is_trained = True

    def add(self, id: str, vector: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not self._is_trained:
            return super().add(id, vector, metadata)

        if len(vector) != self.dimensions:
            raise ValueError(f"Vector dimension mismatch")

        super().add(id, vector, metadata)

        if not self._inverted_lists:
            self._inverted_lists = [[] for _ in range(self.nlist)]

        dists = np.linalg.norm(self._centroids - vector, axis=1)
        cluster = np.argmin(dists)
        self._inverted_lists[cluster].append(id)

        self._is_built = True
        return True

    def build(self) -> None:
        if self._centroids is None and self._vectors:
            all_vecs = np.array(list(self._vectors.values()))
            self.train(all_vecs)

            self._inverted_lists = [[] for _ in range(self.nlist)]
            for id, vec in self._vectors.items():
                dists = np.linalg.norm(self._centroids - vec, axis=1)
                cluster = np.argmin(dists)
                self._inverted_lists[cluster].append(id)

        self._is_built = True

    def search(
        self,
        query: np.ndarray,
        top_k: int = 10,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[VectorSearchResult]:
        if len(query) != self.dimensions:
            return []

        if not self._is_built:
            self.build()

        if self._centroids is None:
            return []

        dists = np.linalg.norm(self._centroids - query, axis=1)
        closest_clusters = np.argsort(dists)[:self.nprobe]

        candidate_ids = set()
        for cluster in closest_clusters:
            if cluster < len(self._inverted_lists):
                candidate_ids.update(self._inverted_lists[cluster])

        results = []
        for id in candidate_ids:
            if id in self._vectors:
                if filter_fn and id in self._metadata:
                    if not filter_fn(self._metadata[id]):
                        continue
                score = self._similarity(query, self._vectors[id])
                results.append(VectorSearchResult(id, self._vectors[id], score, self._metadata.get(id)))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


class VectorStore:
    """向量存储 - 整合多种索引"""

    def __init__(self, config: Optional[VectorIndexConfig] = None):
        self.config = config or VectorIndexConfig()
        self._index: Optional[VectorIndex] = None
        self._create_index()
        self.logger = get_logger(f"{__name__}.VectorStore")

    def _create_index(self) -> None:
        index_type = self.config.index_type.lower()
        if index_type == "hnsw":
            self._index = HNSWIndex(self.config)
        elif index_type == "ivf":
            self._index = IVFIndex(self.config)
        else:
            self._index = FlatIndex(self.config)

    def add(self, id: str, vector: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> bool:
        return self._index.add(id, vector, metadata) if self._index else False

    def add_batch(
        self,
        ids: List[str],
        vectors: List[np.ndarray],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        return self._index.add_batch(ids, vectors, metadatas) if self._index else 0

    def remove(self, id: str) -> bool:
        return self._index.remove(id) if self._index else False

    def get(self, id: str) -> Optional[np.ndarray]:
        return self._index.get(id) if self._index else None

    def search(
        self,
        query: np.ndarray,
        top_k: int = 10,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[VectorSearchResult]:
        return self._index.search(query, top_k, filter_fn) if self._index else []

    def build(self) -> None:
        if self._index:
            self._index.build()

    def size(self) -> int:
        return self._index.size() if self._index else 0
