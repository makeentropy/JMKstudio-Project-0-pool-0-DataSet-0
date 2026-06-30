"""
爬取图（连线载点）测试
"""

import pytest
from pathlib import Path

from ai_llm_agent_crawler.graph import (
    CrawlGraph,
    CrawlNode,
    CrawlEdge,
    NodeStatus,
    EdgeType,
)


class TestCrawlNode:
    """CrawlNode 测试"""

    def test_create_node(self):
        """测试创建节点"""
        node = CrawlNode(
            node_id="n1",
            url="https://example.com",
            title="Example",
            depth=0,
        )
        assert node.node_id == "n1"
        assert node.url == "https://example.com"
        assert node.depth == 0
        assert node.status == NodeStatus.PENDING


class TestCrawlGraph:
    """CrawlGraph 测试"""

    def test_create_graph(self):
        """测试创建图"""
        graph = CrawlGraph()
        assert graph.get_stats()["total_nodes"] == 0
        assert graph.get_stats()["total_edges"] == 0

    def test_add_node(self):
        """测试添加节点"""
        graph = CrawlGraph()
        node_id = graph.add_node("https://example.com", depth=0)
        assert node_id is not None
        assert graph.get_stats()["total_nodes"] == 1

        node = graph.get_node(node_id)
        assert node is not None
        assert node.url == "https://example.com"
        assert node.depth == 0

    def test_add_node_duplicate(self):
        """测试重复添加节点"""
        graph = CrawlGraph()
        id1 = graph.add_node("https://example.com")
        id2 = graph.add_node("https://example.com")
        assert id1 == id2
        assert graph.get_stats()["total_nodes"] == 1

    def test_get_node_by_url(self):
        """测试通过URL获取节点"""
        graph = CrawlGraph()
        graph.add_node("https://example.com/page")
        node = graph.get_node_by_url("https://example.com/page")
        assert node is not None
        assert node.domain == "example.com"

    def test_add_edge(self):
        """测试添加连线"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://a.com/page")

        edge_id = graph.add_edge("https://a.com", "https://a.com/page")
        assert edge_id is not None
        assert graph.get_stats()["total_edges"] == 1

    def test_add_edge_nonexistent(self):
        """测试添加不存在节点的连线"""
        graph = CrawlGraph()
        edge_id = graph.add_edge("https://a.com", "https://b.com")
        assert edge_id is None

    def test_outgoing_edges(self):
        """测试获取出边"""
        graph = CrawlGraph()
        src = graph.add_node("https://src.com")
        t1 = graph.add_node("https://t1.com")
        t2 = graph.add_node("https://t2.com")
        graph.add_edge("https://src.com", "https://t1.com")
        graph.add_edge("https://src.com", "https://t2.com")

        edges = graph.get_outgoing_edges(src)
        assert len(edges) == 2

    def test_incoming_edges(self):
        """测试获取入边"""
        graph = CrawlGraph()
        s1 = graph.add_node("https://s1.com")
        s2 = graph.add_node("https://s2.com")
        target = graph.add_node("https://target.com")
        graph.add_edge("https://s1.com", "https://target.com")
        graph.add_edge("https://s2.com", "https://target.com")

        edges = graph.get_incoming_edges(target)
        assert len(edges) == 2

    def test_neighbors(self):
        """测试获取邻居节点"""
        graph = CrawlGraph()
        graph.add_node("https://center.com")
        graph.add_node("https://a.com")
        graph.add_node("https://b.com")
        graph.add_edge("https://center.com", "https://a.com")
        graph.add_edge("https://b.com", "https://center.com")

        center = graph.get_node_by_url("https://center.com")
        neighbors = graph.get_neighbors(center.node_id)
        assert len(neighbors) == 2

    def test_remove_node(self):
        """测试移除节点"""
        graph = CrawlGraph()
        n1 = graph.add_node("https://a.com")
        n2 = graph.add_node("https://b.com")
        graph.add_edge("https://a.com", "https://b.com")

        assert graph.remove_node(n1)
        assert graph.get_stats()["total_nodes"] == 1
        assert graph.get_stats()["total_edges"] == 0

    def test_update_node(self):
        """测试更新节点"""
        graph = CrawlGraph()
        node_id = graph.add_node("https://example.com")

        assert graph.update_node(node_id, status=NodeStatus.CRAWLED, title="Example Page")
        node = graph.get_node(node_id)
        assert node.status == NodeStatus.CRAWLED
        assert node.title == "Example Page"

    def test_get_pending_nodes(self):
        """测试获取待爬取节点"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://b.com")
        n3 = graph.add_node("https://c.com")
        graph.update_node(n3, status=NodeStatus.CRAWLED)

        pending = graph.get_pending_nodes()
        assert len(pending) == 2

    def test_get_nodes_by_status(self):
        """测试按状态获取节点"""
        graph = CrawlGraph()
        n1 = graph.add_node("https://a.com")
        n2 = graph.add_node("https://b.com")
        graph.update_node(n1, status=NodeStatus.CRAWLED)

        crawled = graph.get_nodes_by_status(NodeStatus.CRAWLED)
        assert len(crawled) == 1
        assert crawled[0].node_id == n1

    def test_get_nodes_by_domain(self):
        """测试按域名获取节点"""
        graph = CrawlGraph()
        graph.add_node("https://example.com/a")
        graph.add_node("https://example.com/b")
        graph.add_node("https://other.com")

        nodes = graph.get_nodes_by_domain("example.com")
        assert len(nodes) == 2

    def test_get_nodes_by_depth(self):
        """测试按深度获取节点"""
        graph = CrawlGraph()
        graph.add_node("https://a.com", depth=0)
        graph.add_node("https://a.com/b", depth=1)
        graph.add_node("https://a.com/c", depth=1)
        graph.add_node("https://a.com/d", depth=2)

        depth1 = graph.get_nodes_by_depth(1)
        assert len(depth1) == 2

    def test_bfs(self):
        """测试广度优先遍历"""
        graph = CrawlGraph()
        graph.add_node("https://root.com", depth=0)
        graph.add_node("https://root.com/a", depth=1)
        graph.add_node("https://root.com/b", depth=1)
        graph.add_node("https://root.com/a/c", depth=2)
        graph.add_edge("https://root.com", "https://root.com/a")
        graph.add_edge("https://root.com", "https://root.com/b")
        graph.add_edge("https://root.com/a", "https://root.com/a/c")

        result = graph.bfs("https://root.com", max_depth=1)
        assert len(result) >= 2

    def test_compute_pagerank(self):
        """测试计算PageRank"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://b.com")
        graph.add_node("https://c.com")
        graph.add_edge("https://a.com", "https://b.com")
        graph.add_edge("https://b.com", "https://c.com")
        graph.add_edge("https://c.com", "https://a.com")

        graph.compute_pagerank()

        for node in graph._nodes.values():
            assert node.pagerank_score > 0

    def test_compute_importance(self):
        """测试计算重要度"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://b.com")
        graph.add_edge("https://a.com", "https://b.com")

        graph.compute_pagerank()
        graph.compute_importance()

        for node in graph._nodes.values():
            assert 0 <= node.importance_score <= 1

    def test_get_domains(self):
        """测试获取域名统计"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://a.com/page")
        graph.add_node("https://b.com")

        domains = graph.get_domains()
        assert len(domains) == 2
        assert "a.com" in domains
        assert domains["a.com"] == 2

    def test_get_top_nodes(self):
        """测试获取Top节点"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://b.com")
        graph.add_node("https://c.com")

        top = graph.get_top_nodes(by="in_degree", limit=2)
        assert len(top) <= 2

    def test_get_stats(self):
        """测试获取统计信息"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://b.com")

        stats = graph.get_stats()
        assert stats["total_nodes"] == 2
        assert "status_counts" in stats
        assert "domains" in stats

    def test_save_and_load(self, tmp_path):
        """测试保存和加载"""
        storage_path = tmp_path / "graph.json"

        g1 = CrawlGraph(storage_path)
        n1 = g1.add_node("https://example.com", title="Example")
        n2 = g1.add_node("https://example.com/page")
        g1.add_edge("https://example.com", "https://example.com/page")
        g1.save()

        g2 = CrawlGraph(storage_path)
        assert g2.get_stats()["total_nodes"] == 2
        assert g2.get_stats()["total_edges"] == 1

        node = g2.get_node_by_url("https://example.com")
        assert node is not None
        assert node.title == "Example"

    def test_export_graphviz(self, tmp_path):
        """测试导出Graphviz格式"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://b.com")
        graph.add_edge("https://a.com", "https://b.com")

        output = tmp_path / "test.dot"
        graph.export_graphviz(output)

        assert output.exists()
        content = output.read_text()
        assert "digraph" in content
