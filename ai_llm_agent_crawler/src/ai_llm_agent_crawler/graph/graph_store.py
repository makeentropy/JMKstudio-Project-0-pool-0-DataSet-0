"""
爬取图存储与遍历

管理爬虫节点（网页节点）和连线（链接关系），
实现连线载点图网络的存储、遍历和分析。
"""

import json
import math
from collections import deque
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin

from pydantic import BaseModel, ConfigDict, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class NodeStatus(str, Enum):
    """节点状态"""

    PENDING = "pending"
    CRAWLING = "crawling"
    CRAWLED = "crawled"
    FAILED = "failed"
    SKIPPED = "skipped"


class EdgeType(str, Enum):
    """连线类型"""

    LINK = "link"
    REDIRECT = "redirect"
    EMBED = "embed"
    API = "api"
    REFERENCE = "reference"


class CrawlNode(BaseModel):
    """爬取节点（载点）

    代表网络中的一个页面/资源节点（载点）。
    """

    node_id: str = Field(description="节点唯一标识")
    url: str = Field(description="节点URL")
    title: str = Field(default="", description="页面标题")
    status: NodeStatus = Field(default=NodeStatus.PENDING, description="爬取状态")
    depth: int = Field(default=0, description="爬取深度")
    domain: str = Field(default="", description="域名")
    content_type: str = Field(default="", description="内容类型")
    status_code: int = Field(default=0, description="HTTP状态码")
    content_length: int = Field(default=0, description="内容长度")

    # 图相关属性
    in_degree: int = Field(default=0, description="入度（指向该节点的连线数）")
    out_degree: int = Field(default=0, description="出度（从该节点出发的连线数）")

    # 重要度评分
    importance_score: float = Field(default=0.0, description="重要度评分")
    attention_score: float = Field(default=0.0, description="注意力评分")
    pagerank_score: float = Field(default=1.0, description="PageRank评分")

    # 时间信息
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间",
    )
    crawled_at: Optional[str] = Field(default=None, description="爬取时间")

    # 种子据点关联
    seed_id: Optional[str] = Field(default=None, description="关联的种子据点ID")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    model_config = ConfigDict(use_enum_values=True)


class CrawlEdge(BaseModel):
    """爬取连线（链接关系）

    代表两个节点之间的连线（链接关系）。
    """

    edge_id: str = Field(description="连线唯一标识")
    source_id: str = Field(description="源节点ID")
    target_id: str = Field(description="目标节点ID")
    edge_type: EdgeType = Field(default=EdgeType.LINK, description="连线类型")
    anchor_text: str = Field(default="", description="锚文本")
    weight: float = Field(default=1.0, description="连线权重")

    # 元数据
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    model_config = ConfigDict(use_enum_values=True)


class CrawlGraph:
    """爬取图（连线载点网络）

    管理爬虫的节点和连线，构成完整的爬取网络图。
    支持图遍历、节点分析和连接可视化。
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        初始化爬取图

        Args:
            storage_path: 持久化存储路径
        """
        self._nodes: Dict[str, CrawlNode] = {}
        self._edges: Dict[str, CrawlEdge] = {}
        self._out_edges: Dict[str, Set[str]] = {}
        self._in_edges: Dict[str, Set[str]] = {}
        self._url_to_node: Dict[str, str] = {}
        self._storage_path = storage_path

        if storage_path and storage_path.exists():
            self._load()

    def add_node(
        self,
        url: str,
        depth: int = 0,
        seed_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        添加节点

        Args:
            url: 节点URL
            depth: 深度
            seed_id: 关联的种子据点ID
            **kwargs: 其他属性

        Returns:
            节点ID
        """
        normalized_url = self._normalize_url(url)

        if normalized_url in self._url_to_node:
            return self._url_to_node[normalized_url]

        node_id = f"node_{len(self._nodes) + 1}_{abs(hash(normalized_url)) % 100000}"
        domain = urlparse(normalized_url).netloc

        node = CrawlNode(
            node_id=node_id,
            url=normalized_url,
            depth=depth,
            domain=domain,
            seed_id=seed_id,
            **kwargs,
        )

        self._nodes[node_id] = node
        self._url_to_node[normalized_url] = node_id
        self._out_edges[node_id] = set()
        self._in_edges[node_id] = set()

        logger.debug(f"添加节点: {node_id} ({normalized_url})")
        return node_id

    def add_edge(
        self,
        source_url: str,
        target_url: str,
        edge_type: EdgeType = EdgeType.LINK,
        anchor_text: str = "",
        weight: float = 1.0,
    ) -> Optional[str]:
        """
        添加连线

        Args:
            source_url: 源URL
            target_url: 目标URL
            edge_type: 连线类型
            anchor_text: 锚文本
            weight: 权重

        Returns:
            连线ID，如果源或目标不存在则返回None
        """
        source_id = self._url_to_node.get(self._normalize_url(source_url))
        target_id = self._url_to_node.get(self._normalize_url(target_url))

        if not source_id or not target_id:
            return None

        edge_id = f"edge_{source_id}_{target_id}"

        if edge_id in self._edges:
            return edge_id

        edge = CrawlEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            anchor_text=anchor_text,
            weight=weight,
        )

        self._edges[edge_id] = edge
        self._out_edges[source_id].add(edge_id)
        self._in_edges[target_id].add(edge_id)

        source_node = self._nodes.get(source_id)
        target_node = self._nodes.get(target_id)
        if source_node:
            source_node.out_degree += 1
        if target_node:
            target_node.in_degree += 1

        logger.debug(f"添加连线: {edge_id}")
        return edge_id

    def remove_node(self, node_id: str) -> bool:
        """
        移除节点及其所有连线

        Args:
            node_id: 节点ID

        Returns:
            是否成功
        """
        if node_id not in self._nodes:
            return False

        node = self._nodes[node_id]
        self._url_to_node.pop(node.url, None)

        edges_to_remove = set()
        edges_to_remove.update(self._out_edges.get(node_id, set()))
        edges_to_remove.update(self._in_edges.get(node_id, set()))

        for edge_id in edges_to_remove:
            edge = self._edges.pop(edge_id, None)
            if edge:
                self._out_edges.get(edge.source_id, set()).discard(edge_id)
                self._in_edges.get(edge.target_id, set()).discard(edge_id)

        self._out_edges.pop(node_id, None)
        self._in_edges.pop(node_id, None)
        self._nodes.pop(node_id, None)

        logger.info(f"移除节点: {node_id}")
        return True

    def get_node(self, node_id: str) -> Optional[CrawlNode]:
        """获取节点"""
        return self._nodes.get(node_id)

    def get_node_by_url(self, url: str) -> Optional[CrawlNode]:
        """通过URL获取节点"""
        node_id = self._url_to_node.get(self._normalize_url(url))
        if node_id:
            return self._nodes.get(node_id)
        return None

    def get_edge(self, edge_id: str) -> Optional[CrawlEdge]:
        """获取连线"""
        return self._edges.get(edge_id)

    def get_outgoing_edges(self, node_id: str) -> List[CrawlEdge]:
        """获取节点的出边"""
        edge_ids = self._out_edges.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_incoming_edges(self, node_id: str) -> List[CrawlEdge]:
        """获取节点的入边"""
        edge_ids = self._in_edges.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_neighbors(self, node_id: str) -> List[CrawlNode]:
        """获取节点的所有邻居节点"""
        neighbors = set()
        for edge in self.get_outgoing_edges(node_id):
            neighbors.add(edge.target_id)
        for edge in self.get_incoming_edges(node_id):
            neighbors.add(edge.source_id)
        return [self._nodes[nid] for nid in neighbors if nid in self._nodes]

    def update_node(self, node_id: str, **kwargs) -> bool:
        """更新节点属性"""
        node = self._nodes.get(node_id)
        if not node:
            return False

        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)

        return True

    def get_pending_nodes(self, limit: int = 100) -> List[CrawlNode]:
        """获取待爬取的节点"""
        pending = [
            n
            for n in self._nodes.values()
            if n.status == NodeStatus.PENDING
        ]
        pending.sort(key=lambda n: (-n.attention_score, -n.importance_score, n.depth))
        return pending[:limit]

    def get_nodes_by_status(self, status: NodeStatus) -> List[CrawlNode]:
        """按状态获取节点"""
        return [n for n in self._nodes.values() if n.status == status]

    def get_nodes_by_domain(self, domain: str) -> List[CrawlNode]:
        """按域名获取节点"""
        return [n for n in self._nodes.values() if n.domain == domain]

    def get_nodes_by_depth(self, depth: int) -> List[CrawlNode]:
        """按深度获取节点"""
        return [n for n in self._nodes.values() if n.depth == depth]

    def bfs(self, start_url: str, max_depth: int = 3) -> List[CrawlNode]:
        """
        广度优先遍历

        Args:
            start_url: 起始URL
            max_depth: 最大深度

        Returns:
            遍历到的节点列表
        """
        start_node = self.get_node_by_url(start_url)
        if not start_node:
            return []

        visited = set()
        result = []
        queue = deque([(start_node.node_id, 0)])

        while queue:
            node_id, depth = queue.popleft()
            if node_id in visited or depth > max_depth:
                continue

            visited.add(node_id)
            node = self._nodes.get(node_id)
            if node:
                result.append(node)

            for edge in self.get_outgoing_edges(node_id):
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))

        return result

    def compute_pagerank(self, damping: float = 0.85, iterations: int = 20) -> None:
        """
        计算PageRank评分

        Args:
            damping: 阻尼系数
            iterations: 迭代次数
        """
        if not self._nodes:
            return

        n = len(self._nodes)
        for node in self._nodes.values():
            node.pagerank_score = 1.0 / n

        for _ in range(iterations):
            new_scores: Dict[str, float] = {}
            for node_id, node in self._nodes.items():
                rank_sum = 0.0
                for edge in self.get_incoming_edges(node_id):
                    source = self._nodes.get(edge.source_id)
                    if source and source.out_degree > 0:
                        rank_sum += source.pagerank_score / source.out_degree
                new_scores[node_id] = (1 - damping) / n + damping * rank_sum

            for node_id, score in new_scores.items():
                if node_id in self._nodes:
                    self._nodes[node_id].pagerank_score = score

        logger.info(f"PageRank计算完成，节点数: {n}")

    def compute_importance(self) -> None:
        """计算节点重要度（综合评分）"""
        if not self._nodes:
            return

        max_in = max((n.in_degree for n in self._nodes.values()), default=1)
        max_out = max((n.out_degree for n in self._nodes.values()), default=1)
        max_pr = max((n.pagerank_score for n in self._nodes.values()), default=1.0)

        for node in self._nodes.values():
            in_norm = node.in_degree / max_in if max_in > 0 else 0
            out_norm = node.out_degree / max_out if max_out > 0 else 0
            pr_norm = node.pagerank_score / max_pr if max_pr > 0 else 0

            node.importance_score = (
                0.4 * in_norm + 0.2 * out_norm + 0.4 * pr_norm
            )

    def get_domains(self) -> Dict[str, int]:
        """获取所有域名及节点数"""
        domains: Dict[str, int] = {}
        for node in self._nodes.values():
            domains[node.domain] = domains.get(node.domain, 0) + 1
        return dict(sorted(domains.items(), key=lambda x: -x[1]))

    def get_stats(self) -> Dict[str, Any]:
        """获取图统计信息"""
        nodes = list(self._nodes.values())
        edges = list(self._edges.values())

        status_counts = {}
        for node in nodes:
            status = node.status
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "status_counts": status_counts,
            "domains": len(self.get_domains()),
            "max_depth": max((n.depth for n in nodes), default=0),
            "avg_in_degree": (
                sum(n.in_degree for n in nodes) / len(nodes) if nodes else 0
            ),
            "avg_out_degree": (
                sum(n.out_degree for n in nodes) / len(nodes) if nodes else 0
            ),
            "avg_importance": (
                sum(n.importance_score for n in nodes) / len(nodes) if nodes else 0
            ),
        }

    def get_top_nodes(
        self,
        by: str = "importance",
        limit: int = 10,
    ) -> List[CrawlNode]:
        """
        获取排名前N的节点

        Args:
            by: 排序依据（importance/attention/pagerank/in_degree/out_degree）
            limit: 返回数量

        Returns:
            节点列表
        """
        nodes = list(self._nodes.values())

        if by == "importance":
            nodes.sort(key=lambda n: -n.importance_score)
        elif by == "attention":
            nodes.sort(key=lambda n: -n.attention_score)
        elif by == "pagerank":
            nodes.sort(key=lambda n: -n.pagerank_score)
        elif by == "in_degree":
            nodes.sort(key=lambda n: -n.in_degree)
        elif by == "out_degree":
            nodes.sort(key=lambda n: -n.out_degree)

        return nodes[:limit]

    def export_graphviz(self, output_path: Path, max_nodes: int = 100) -> None:
        """
        导出为Graphviz DOT格式

        Args:
            output_path: 输出文件路径
            max_nodes: 最大节点数
        """
        top_nodes = self.get_top_nodes(by="importance", limit=max_nodes)
        node_ids = {n.node_id for n in top_nodes}

        lines = ["digraph CrawlGraph {"]
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, style=filled];')

        for node in top_nodes:
            color = self._get_status_color(node.status)
            safe_title = node.title.replace('"', '\\"')[:50]
            lines.append(
                f'  "{node.node_id}" [label="{safe_title}\\n{node.domain}", '
                f'fillcolor="{color}"];'
            )

        for edge in self._edges.values():
            if edge.source_id in node_ids and edge.target_id in node_ids:
                lines.append(f'  "{edge.source_id}" -> "{edge.target_id}";')

        lines.append("}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"图已导出到: {output_path}")

    def save(self, output_path: Optional[Path] = None) -> None:
        """保存图数据"""
        path = output_path or self._storage_path
        if not path:
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [n.model_dump() for n in self._nodes.values()],
            "edges": [e.model_dump() for e in self._edges.values()],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """从文件加载图数据"""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for node_data in data.get("nodes", []):
                try:
                    node = CrawlNode(**node_data)
                    self._nodes[node.node_id] = node
                    self._url_to_node[node.url] = node.node_id
                    self._out_edges[node.node_id] = set()
                    self._in_edges[node.node_id] = set()
                except Exception as e:
                    logger.warning(f"加载节点失败: {e}")

            for edge_data in data.get("edges", []):
                try:
                    edge = CrawlEdge(**edge_data)
                    self._edges[edge.edge_id] = edge
                    self._out_edges.setdefault(edge.source_id, set()).add(edge.edge_id)
                    self._in_edges.setdefault(edge.target_id, set()).add(edge.edge_id)
                except Exception as e:
                    logger.warning(f"加载连线失败: {e}")

            logger.info(
                f"已加载图数据: {len(self._nodes)} 个节点, {len(self._edges)} 条连线"
            )
        except Exception as e:
            logger.error(f"加载图数据失败: {e}")

    @staticmethod
    def _normalize_url(url: str) -> str:
        """标准化URL"""
        url = url.strip()
        if not url:
            return url
        parsed = urlparse(url)
        normalized = parsed._replace(fragment="")
        result = normalized.geturl()
        if result.endswith("/") and len(result) > 8:
            result = result.rstrip("/")
        return result

    @staticmethod
    def _get_status_color(status: str) -> str:
        """获取状态对应的颜色"""
        colors = {
            "pending": "#lightblue",
            "crawling": "#yellow",
            "crawled": "#lightgreen",
            "failed": "#lightcoral",
            "skipped": "#lightgray",
        }
        return colors.get(status, "white")
