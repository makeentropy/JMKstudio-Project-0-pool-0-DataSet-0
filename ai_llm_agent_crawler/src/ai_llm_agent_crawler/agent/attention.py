"""
注意力评分机制（拉注意力）

实现多维度的页面注意力评分系统，用于智能判断
哪些页面/节点值得优先爬取（拉注意力到重要节点）。

支持多种评分策略：
- 基于关键词的注意力
- 基于链接结构的注意力
- 基于内容质量的注意力
- 基于LLM语义的注意力
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.graph.graph_store import CrawlNode, CrawlGraph
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ScoringStrategy(str, Enum):
    """评分策略"""

    KEYWORD = "keyword"
    LINK_STRUCTURE = "link_structure"
    CONTENT_QUALITY = "content_quality"
    DOMAIN_AUTHORITY = "domain_authority"
    FRESHNESS = "freshness"
    COMBINED = "combined"


class AttentionConfig(BaseModel):
    """注意力配置"""

    strategy: ScoringStrategy = Field(
        default=ScoringStrategy.COMBINED,
        description="评分策略",
    )

    # 关键词配置
    focus_keywords: List[str] = Field(
        default_factory=list,
        description="关注的关键词列表",
    )
    keyword_weight: float = Field(default=0.3, description="关键词权重")

    # 链接结构配置
    link_structure_weight: float = Field(default=0.25, description="链接结构权重")
    pagerank_weight: float = Field(default=0.15, description="PageRank权重")
    in_degree_weight: float = Field(default=0.1, description="入度权重")

    # 内容质量配置
    content_quality_weight: float = Field(default=0.15, description="内容质量权重")

    # 域名权威配置
    domain_authority_weight: float = Field(default=0.15, description="域名权威权重")
    preferred_domains: List[str] = Field(
        default_factory=list,
        description="偏好的域名列表",
    )
    domain_boost: float = Field(default=1.5, description="偏好域名的提升倍数")

    # 新鲜度配置
    freshness_weight: float = Field(default=0.15, description="新鲜度权重")
    depth_penalty: float = Field(default=0.9, description="深度惩罚因子")

    # 阈值配置
    min_attention_score: float = Field(
        default=0.1,
        description="最低注意力分数（低于此值跳过）",
    )
    high_attention_threshold: float = Field(
        default=0.7,
        description="高注意力阈值（优先爬取）",
    )

    # 最大深度
    max_depth: int = Field(default=5, description="最大爬取深度")


@dataclass
class AttentionScore:
    """注意力评分结果"""

    total: float = 0.0
    keyword_score: float = 0.0
    link_score: float = 0.0
    content_score: float = 0.0
    domain_score: float = 0.0
    freshness_score: float = 0.0
    reasons: List[str] = None

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


class AttentionScorer:
    """
    注意力评分器

    实现"拉注意力"机制——多维度评估页面重要性，
    将注意力聚焦到最有价值的节点。
    """

    def __init__(self, config: Optional[AttentionConfig] = None):
        """
        初始化注意力评分器

        Args:
            config: 注意力配置
        """
        self.config = config or AttentionConfig()
        self._keyword_patterns: List[re.Pattern] = []
        self._compile_keywords()

    def set_focus_keywords(self, keywords: List[str]) -> None:
        """
        设置关注关键词

        Args:
            keywords: 关键词列表
        """
        self.config.focus_keywords = keywords
        self._compile_keywords()

    def add_focus_keyword(self, keyword: str) -> None:
        """
        添加关注关键词

        Args:
            keyword: 关键词
        """
        if keyword not in self.config.focus_keywords:
            self.config.focus_keywords.append(keyword)
            self._compile_keywords()

    def _compile_keywords(self) -> None:
        """编译关键词正则表达式"""
        self._keyword_patterns = []
        for kw in self.config.focus_keywords:
            try:
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                self._keyword_patterns.append(pattern)
            except re.error:
                continue

    def score_node(
        self,
        node: CrawlNode,
        graph: Optional[CrawlGraph] = None,
        content: str = "",
    ) -> AttentionScore:
        """
        计算节点的注意力评分

        Args:
            node: 爬取节点
            graph: 爬取图（用于链接结构分析）
            content: 页面内容（可选）

        Returns:
            注意力评分结果
        """
        score = AttentionScore()

        if self.config.strategy in [ScoringStrategy.KEYWORD, ScoringStrategy.COMBINED]:
            score.keyword_score = self._score_keywords(node, content)
            if score.keyword_score > 0.3:
                score.reasons.append(f"关键词匹配度高 ({score.keyword_score:.2f})")

        if self.config.strategy in [ScoringStrategy.LINK_STRUCTURE, ScoringStrategy.COMBINED]:
            score.link_score = self._score_link_structure(node, graph)
            if score.link_score > 0.5:
                score.reasons.append(f"链接结构重要 ({score.link_score:.2f})")

        if self.config.strategy in [ScoringStrategy.CONTENT_QUALITY, ScoringStrategy.COMBINED]:
            score.content_score = self._score_content_quality(node, content)
            if score.content_score > 0.5:
                score.reasons.append(f"内容质量高 ({score.content_score:.2f})")

        if self.config.strategy in [ScoringStrategy.DOMAIN_AUTHORITY, ScoringStrategy.COMBINED]:
            score.domain_score = self._score_domain_authority(node)
            if score.domain_score > 0.5:
                score.reasons.append(f"域名权威 ({score.domain_score:.2f})")

        if self.config.strategy in [ScoringStrategy.FRESHNESS, ScoringStrategy.COMBINED]:
            score.freshness_score = self._score_freshness(node)
            if score.freshness_score > 0.5:
                score.reasons.append(f"新鲜度高 ({score.freshness_score:.2f})")

        score.total = self._combine_scores(score)
        return score

    def _score_keywords(self, node: CrawlNode, content: str) -> float:
        """
        基于关键词的评分

        Args:
            node: 节点
            content: 内容

        Returns:
            关键词评分（0-1）
        """
        if not self._keyword_patterns:
            return 0.0

        text = f"{node.title} {node.url} {content}"
        if not text.strip():
            return 0.0

        match_count = 0
        for pattern in self._keyword_patterns:
            matches = pattern.findall(text)
            match_count += len(matches)

        max_matches = max(len(self._keyword_patterns) * 3, 1)
        score = min(match_count / max_matches, 1.0)
        return score

    def _score_link_structure(
        self,
        node: CrawlNode,
        graph: Optional[CrawlGraph],
    ) -> float:
        """
        基于链接结构的评分

        Args:
            node: 节点
            graph: 爬取图

        Returns:
            链接结构评分（0-1）
        """
        if not graph:
            return 0.0

        pr_score = node.pagerank_score
        in_score = min(node.in_degree / 20.0, 1.0) if node.in_degree > 0 else 0.0
        out_score = min(node.out_degree / 50.0, 1.0) if node.out_degree > 0 else 0.0

        score = (
            self.config.pagerank_weight * pr_score
            + self.config.in_degree_weight * in_score
            + 0.1 * out_score
        )
        return min(score, 1.0)

    def _score_content_quality(self, node: CrawlNode, content: str) -> float:
        """
        基于内容质量的评分

        Args:
            node: 节点
            content: 内容

        Returns:
            内容质量评分（0-1）
        """
        if not content:
            return 0.5

        content_length = len(content)

        length_score = min(content_length / 5000.0, 1.0)

        text_chars = len(re.findall(r"[\w\u4e00-\u9fff]", content))
        content_ratio = text_chars / max(content_length, 1)
        quality_score = min(content_ratio * 2, 1.0)

        has_title = 1.0 if node.title else 0.0

        score = 0.4 * length_score + 0.4 * quality_score + 0.2 * has_title
        return score

    def _score_domain_authority(self, node: CrawlNode) -> float:
        """
        基于域名权威的评分

        Args:
            node: 节点

        Returns:
            域名权威评分（0-1）
        """
        domain = node.domain
        if not domain:
            return 0.0

        score = 0.3

        tld_scores = {
            ".gov": 1.0,
            ".edu": 0.9,
            ".org": 0.7,
            ".com": 0.6,
            ".net": 0.5,
            ".io": 0.5,
            ".cn": 0.5,
        }

        for tld, tld_score in tld_scores.items():
            if domain.endswith(tld):
                score = max(score, tld_score)
                break

        if self.config.preferred_domains:
            for pref_domain in self.config.preferred_domains:
                if pref_domain in domain:
                    score *= self.config.domain_boost
                    break

        return min(score, 1.0)

    def _score_freshness(self, node: CrawlNode) -> float:
        """
        基于新鲜度的评分

        Args:
            node: 节点

        Returns:
            新鲜度评分（0-1）
        """
        depth = node.depth
        if depth > self.config.max_depth:
            return 0.0

        depth_score = self.config.depth_penalty**depth

        status_score = 1.0
        if node.status == "failed":
            status_score = 0.2
        elif node.status == "skipped":
            status_score = 0.3

        return depth_score * status_score

    def _combine_scores(self, score: AttentionScore) -> float:
        """
        综合评分

        Args:
            score: 各维度评分

        Returns:
            综合评分
        """
        if self.config.strategy == ScoringStrategy.KEYWORD:
            return score.keyword_score
        if self.config.strategy == ScoringStrategy.LINK_STRUCTURE:
            return score.link_score
        if self.config.strategy == ScoringStrategy.CONTENT_QUALITY:
            return score.content_score
        if self.config.strategy == ScoringStrategy.DOMAIN_AUTHORITY:
            return score.domain_score
        if self.config.strategy == ScoringStrategy.FRESHNESS:
            return score.freshness_score

        total = (
            self.config.keyword_weight * score.keyword_score
            + self.config.link_structure_weight * score.link_score
            + self.config.content_quality_weight * score.content_score
            + self.config.domain_authority_weight * score.domain_score
            + self.config.freshness_weight * score.freshness_score
        )
        return min(max(total, 0.0), 1.0)

    def should_crawl(self, score: AttentionScore) -> bool:
        """
        判断是否应该爬取

        Args:
            score: 注意力评分

        Returns:
            是否应该爬取
        """
        return score.total >= self.config.min_attention_score

    def is_high_priority(self, score: AttentionScore) -> bool:
        """
        判断是否为高优先级

        Args:
            score: 注意力评分

        Returns:
            是否为高优先级
        """
        return score.total >= self.config.high_attention_threshold

    def rank_urls(
        self,
        urls: List[str],
        graph: Optional[CrawlGraph] = None,
        depth: int = 0,
    ) -> List[tuple]:
        """
        对URL列表进行注意力排名

        Args:
            urls: URL列表
            graph: 爬取图
            depth: 当前深度

        Returns:
            (url, score)列表，按分数降序排列
        """
        scored = []
        for url in urls:
            node = CrawlNode(
                node_id=f"temp_{abs(hash(url))}",
                url=url,
                depth=depth,
                domain=urlparse(url).netloc,
            )
            score = self.score_node(node, graph)
            scored.append((url, score))

        scored.sort(key=lambda x: -x[1].total)
        return scored

    def filter_crawlable(
        self,
        urls: List[str],
        graph: Optional[CrawlGraph] = None,
        depth: int = 0,
    ) -> List[str]:
        """
        过滤出值得爬取的URL

        Args:
            urls: URL列表
            graph: 爬取图
            depth: 当前深度

        Returns:
            值得爬取的URL列表
        """
        ranked = self.rank_urls(urls, graph, depth)
        return [url for url, score in ranked if self.should_crawl(score)]

    def update_graph_attention(self, graph: CrawlGraph) -> None:
        """
        更新图中所有节点的注意力评分

        Args:
            graph: 爬取图
        """
        count = 0
        for node in graph._nodes.values():
            score = self.score_node(node, graph)
            node.attention_score = score.total
            count += 1
        logger.info(f"已更新 {count} 个节点的注意力评分")
