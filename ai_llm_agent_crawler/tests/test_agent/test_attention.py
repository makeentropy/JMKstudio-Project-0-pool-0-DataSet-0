"""
注意力评分机制（拉注意力）测试
"""

import pytest

from ai_llm_agent_crawler.agent.attention import (
    AttentionScorer,
    AttentionConfig,
    ScoringStrategy,
)
from ai_llm_agent_crawler.graph import CrawlGraph, CrawlNode


class TestAttentionConfig:
    """AttentionConfig 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = AttentionConfig()
        assert config.strategy == ScoringStrategy.COMBINED
        assert config.min_attention_score == 0.1
        assert config.high_attention_threshold == 0.7
        assert config.max_depth == 5


class TestAttentionScorer:
    """AttentionScorer 测试"""

    def test_create_scorer(self):
        """测试创建评分器"""
        scorer = AttentionScorer()
        assert scorer is not None

    def test_set_focus_keywords(self):
        """测试设置关注关键词"""
        scorer = AttentionScorer()
        scorer.set_focus_keywords(["ai", "ml", "data"])
        assert len(scorer.config.focus_keywords) == 3

    def test_add_focus_keyword(self):
        """测试添加关注关键词"""
        scorer = AttentionScorer()
        scorer.add_focus_keyword("test")
        assert "test" in scorer.config.focus_keywords

    def test_score_node_no_keywords(self):
        """测试无关键词时的评分"""
        scorer = AttentionScorer()
        node = CrawlNode(
            node_id="n1",
            url="https://example.com",
            title="Example Page",
        )
        score = scorer.score_node(node)
        assert 0 <= score.total <= 1
        assert score.keyword_score == 0.0

    def test_score_node_with_keywords(self):
        """测试有关键词时的评分"""
        scorer = AttentionScorer()
        scorer.set_focus_keywords(["example", "test"])

        node = CrawlNode(
            node_id="n1",
            url="https://example.com/test-page",
            title="Example Test Page",
        )
        score = scorer.score_node(node)
        assert score.keyword_score > 0

    def test_score_with_graph(self):
        """测试带图的评分"""
        graph = CrawlGraph()
        n1 = graph.add_node("https://a.com", depth=0)
        n2 = graph.add_node("https://a.com/page1", depth=1)
        n3 = graph.add_node("https://a.com/page2", depth=1)
        graph.add_edge("https://a.com", "https://a.com/page1")
        graph.add_edge("https://a.com", "https://a.com/page2")

        graph.compute_pagerank()
        graph.compute_importance()

        scorer = AttentionScorer()
        node = graph.get_node(n1)
        score = scorer.score_node(node, graph)

        assert 0 <= score.total <= 1
        assert score.link_score >= 0

    def test_should_crawl(self):
        """测试是否应该爬取"""
        scorer = AttentionScorer()

        high_config = AttentionConfig(min_attention_score=0.9)
        high_scorer = AttentionScorer(high_config)

        node = CrawlNode(node_id="n1", url="https://example.com")
        score = scorer.score_node(node)

        assert scorer.should_crawl(score) is True
        assert high_scorer.should_crawl(score) is False

    def test_is_high_priority(self):
        """测试是否为高优先级"""
        config = AttentionConfig(high_attention_threshold=0.5)
        scorer = AttentionScorer(config)
        scorer.set_focus_keywords(["example", "test", "page", "content", "data"])

        node = CrawlNode(
            node_id="n1",
            url="https://example.com/test-page-content-data",
            title="Example Test Page Content Data",
        )
        score = scorer.score_node(node)
        assert scorer.is_high_priority(score) is True or scorer.is_high_priority(score) is False

    def test_rank_urls(self):
        """测试URL排名"""
        scorer = AttentionScorer()
        scorer.set_focus_keywords(["important"])

        urls = [
            "https://example.com/important-page",
            "https://example.com/normal-page",
            "https://other.com/trivial",
        ]

        ranked = scorer.rank_urls(urls)
        assert len(ranked) == 3
        assert ranked[0][1].total >= ranked[-1][1].total

    def test_filter_crawlable(self):
        """测试过滤可爬取URL"""
        config = AttentionConfig(min_attention_score=0.9)
        scorer = AttentionScorer(config)

        urls = [
            "https://a.com/page",
            "https://b.com/page",
            "https://c.com/page",
        ]

        result = scorer.filter_crawlable(urls)
        assert isinstance(result, list)

    def test_update_graph_attention(self):
        """测试更新图的注意力评分"""
        graph = CrawlGraph()
        graph.add_node("https://a.com")
        graph.add_node("https://b.com")
        graph.add_node("https://c.com")

        scorer = AttentionScorer()
        scorer.set_focus_keywords(["a.com"])
        scorer.update_graph_attention(graph)

        for node in graph._nodes.values():
            assert hasattr(node, "attention_score")
            assert 0 <= node.attention_score <= 1

    def test_keyword_strategy(self):
        """测试关键词策略"""
        config = AttentionConfig(strategy=ScoringStrategy.KEYWORD)
        scorer = AttentionScorer(config)
        scorer.set_focus_keywords(["test"])

        node = CrawlNode(node_id="n1", url="https://test.com")
        score = scorer.score_node(node)
        assert score.total == score.keyword_score

    def test_depth_penalty(self):
        """测试深度惩罚"""
        scorer = AttentionScorer()

        shallow = CrawlNode(node_id="n1", url="https://a.com", depth=0)
        deep = CrawlNode(node_id="n2", url="https://a.com/deep", depth=5)

        shallow_score = scorer.score_node(shallow)
        deep_score = scorer.score_node(deep)

        assert shallow_score.freshness_score >= deep_score.freshness_score

    def test_domain_authority(self):
        """测试域名权威评分"""
        scorer = AttentionScorer()

        gov_node = CrawlNode(
            node_id="n1",
            url="https://example.gov/page",
            domain="example.gov",
        )
        com_node = CrawlNode(
            node_id="n2",
            url="https://example.com/page",
            domain="example.com",
        )

        gov_score = scorer.score_node(gov_node)
        com_score = scorer.score_node(com_node)

        assert gov_score.domain_score >= com_score.domain_score

    def test_preferred_domains(self):
        """测试偏好域名"""
        config = AttentionConfig(preferred_domains=["preferred.com"])
        scorer = AttentionScorer(config)

        pref_node = CrawlNode(
            node_id="n1",
            url="https://preferred.com/page",
            domain="preferred.com",
        )
        other_node = CrawlNode(
            node_id="n2",
            url="https://other.com/page",
            domain="other.com",
        )

        pref_score = scorer.score_node(pref_node)
        other_score = scorer.score_node(other_node)

        assert pref_score.domain_score > other_score.domain_score
