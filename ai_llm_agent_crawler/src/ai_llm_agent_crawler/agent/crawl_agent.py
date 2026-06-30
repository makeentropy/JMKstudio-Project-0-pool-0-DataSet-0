"""
爬取Agent（LLM指导）

使用大语言模型指导爬虫的爬取策略，实现智能化的
爬取决策。LLM Agent 分析页面内容和爬取状态，
决定下一步爬取方向（拉注意力到最有价值的节点）。
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.agent.attention import AttentionConfig, AttentionScorer
from ai_llm_agent_crawler.graph.graph_store import CrawlGraph, CrawlNode, NodeStatus
from ai_llm_agent_crawler.seed.seed_manager import SeedPoint
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class AgentMode(str, Enum):
    """Agent运行模式"""

    AUTONOMOUS = "autonomous"
    SUPERVISED = "supervised"
    CONSERVATIVE = "conservative"
    EXPLORATORY = "exploratory"


class CrawlAction(str, Enum):
    """爬取动作"""

    CRAWL = "crawl"
    SKIP = "skip"
    PRIORITIZE = "prioritize"
    DEPTH_FIRST = "depth_first"
    BREADTH_FIRST = "breadth_first"
    EXPLORE_NEW = "explore_new"
    FOCUS_DEPTH = "focus_depth"


class CrawlDecision(BaseModel):
    """爬取决策"""

    action: CrawlAction = Field(description="决策动作")
    reason: str = Field(default="", description="决策原因")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度")
    priority: int = Field(default=5, ge=1, le=10, description="优先级")
    max_pages: Optional[int] = Field(default=None, description="最大页面数")
    max_depth: Optional[int] = Field(default=None, description="最大深度")
    focus_keywords: List[str] = Field(default_factory=list, description="关注关键词")
    suggestions: List[str] = Field(default_factory=list, description="建议")


class AgentConfig(BaseModel):
    """Agent配置"""

    mode: AgentMode = Field(default=AgentMode.AUTONOMOUS, description="运行模式")
    llm_provider: str = Field(default="openai", description="LLM提供商")
    llm_model: str = Field(default="gpt-3.5-turbo", description="LLM模型")
    llm_api_base: str = Field(default="", description="LLM API基地址")
    llm_api_key: str = Field(default="", description="LLM API密钥")
    max_decisions_per_cycle: int = Field(default=10, description="每周期最大决策数")
    decision_interval: int = Field(default=5, description="决策间隔（页面数）")
    enable_auto_adjust: bool = Field(default=True, description="启用自动调整")
    attention_config: AttentionConfig = Field(
        default_factory=AttentionConfig,
        description="注意力配置",
    )


class CrawlAgent:
    """
    爬取Agent

    使用LLM指导爬虫的爬取策略，实现智能化决策。
    Agent会分析爬取状态和内容，决定下一步爬取方向，
    实现"拉注意力"到最有价值的节点。
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        graph: Optional[CrawlGraph] = None,
    ):
        """
        初始化爬取Agent

        Args:
            config: Agent配置
            graph: 爬取图
        """
        self.config = config or AgentConfig()
        self.graph = graph or CrawlGraph()
        self.attention_scorer = AttentionScorer(self.config.attention_config)
        self._decision_history: List[CrawlDecision] = []
        self._pages_since_last_decision = 0
        self._is_running = False

        logger.info(
            f"爬取Agent已初始化，模式: {self.config.mode}, "
            f"策略: {self.config.attention_config.strategy}"
        )

    def set_graph(self, graph: CrawlGraph) -> None:
        """设置爬取图"""
        self.graph = graph

    def add_focus_keyword(self, keyword: str) -> None:
        """添加关注关键词"""
        self.attention_scorer.add_focus_keyword(keyword)

    def set_focus_keywords(self, keywords: List[str]) -> None:
        """设置关注关键词"""
        self.attention_scorer.set_focus_keywords(keywords)

    async def decide_next_targets(
        self,
        candidates: List[str],
        current_depth: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[tuple]:
        """
        决策下一批爬取目标

        Args:
            candidates: 候选URL列表
            current_depth: 当前深度
            context: 上下文信息

        Returns:
            (url, score, decision)列表，按优先级降序
        """
        if not candidates:
            return []

        scored = self.attention_scorer.rank_urls(
            candidates, self.graph, current_depth
        )

        results = []
        for url, attention_score in scored:
            if not self.attention_scorer.should_crawl(attention_score):
                continue

            decision = self._make_decision(url, attention_score, current_depth, context)
            if decision.action != CrawlAction.SKIP:
                results.append((url, attention_score, decision))

        results.sort(key=lambda x: (-x[2].priority, -x[1].total))
        return results

    def _make_decision(
        self,
        url: str,
        attention_score,
        depth: int,
        context: Optional[Dict[str, Any]],
    ) -> CrawlDecision:
        """
        生成爬取决策

        Args:
            url: URL
            attention_score: 注意力评分
            depth: 深度
            context: 上下文

        Returns:
            爬取决策
        """
        if depth > self.config.attention_config.max_depth:
            return CrawlDecision(
                action=CrawlAction.SKIP,
                reason="超过最大深度限制",
                confidence=0.9,
                priority=1,
            )

        if not self.attention_scorer.should_crawl(attention_score):
            return CrawlDecision(
                action=CrawlAction.SKIP,
                reason="注意力评分过低",
                confidence=0.8,
                priority=1,
            )

        is_high = self.attention_scorer.is_high_priority(attention_score)
        reasons = attention_score.reasons

        if is_high:
            action = CrawlAction.PRIORITIZE
            priority = min(10, int(attention_score.total * 10))
            reason = f"高优先级目标: {'; '.join(reasons[:2])}" if reasons else "高注意力评分"
        elif attention_score.total > 0.4:
            action = CrawlAction.CRAWL
            priority = int(attention_score.total * 7) + 3
            reason = f"常规爬取: {'; '.join(reasons[:2])}" if reasons else "正常注意力评分"
        else:
            action = CrawlAction.CRAWL
            priority = max(2, int(attention_score.total * 5))
            reason = "低优先级，资源充足时爬取"

        if self.config.mode == AgentMode.CONSERVATIVE:
            priority = max(1, priority - 2)
        elif self.config.mode == AgentMode.EXPLORATORY:
            priority = min(10, priority + 1)

        decision = CrawlDecision(
            action=action,
            reason=reason,
            confidence=attention_score.total,
            priority=priority,
        )

        self._decision_history.append(decision)
        return decision

    async def analyze_and_adjust(
        self,
        crawled_pages: int,
        current_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析爬取状态并调整策略

        Args:
            crawled_pages: 已爬取页面数
            current_stats: 当前统计

        Returns:
            调整建议
        """
        adjustments: Dict[str, Any] = {}

        if not self.config.enable_auto_adjust:
            return adjustments

        total_nodes = current_stats.get("total_nodes", 0)
        crawled = current_stats.get("status_counts", {}).get("crawled", 0)
        failed = current_stats.get("status_counts", {}).get("failed", 0)

        if total_nodes > 0:
            success_rate = crawled / (crawled + failed) if (crawled + failed) > 0 else 1.0
        else:
            success_rate = 1.0

        if failed > crawled * 0.3 and self.config.mode != AgentMode.CONSERVATIVE:
            adjustments["mode_suggestion"] = "建议切换到保守模式"
            adjustments["reason"] = f"失败率较高: {1 - success_rate:.1%}"

        high_attention_count = sum(
            1
            for node in self.graph._nodes.values()
            if node.attention_score >= self.config.attention_config.high_attention_threshold
        )

        if high_attention_count > 50:
            adjustments["attention_threshold"] = "建议提高高注意力阈值"
            adjustments["high_attention_count"] = high_attention_count

        domains = self.graph.get_domains()
        if len(domains) > 1 and len(domains) < 5:
            adjustments["diversity"] = "建议扩展更多域名"
            adjustments["domain_count"] = len(domains)

        adjustments["recommendations"] = self._generate_recommendations(current_stats)
        return adjustments

    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """生成爬取建议"""
        recommendations = []

        pending = stats.get("status_counts", {}).get("pending", 0)
        if pending < 10:
            recommendations.append("待爬取节点不足，建议从种子据点扩展更多链接")

        total = stats.get("total_nodes", 0)
        if total > 100:
            recommendations.append("节点数较多，建议启用PageRank计算优化爬取顺序")

        failed = stats.get("status_counts", {}).get("failed", 0)
        if failed > 20:
            recommendations.append("失败节点较多，建议检查网络连接或增加重试次数")

        if not recommendations:
            recommendations.append("爬取状态良好，继续保持当前策略")

        return recommendations

    def get_decision_history(self, limit: int = 20) -> List[CrawlDecision]:
        """获取决策历史"""
        return self._decision_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        decisions = self._decision_history
        action_counts: Dict[str, int] = {}
        for d in decisions:
            action = d.action
            action_counts[action] = action_counts.get(action, 0) + 1

        avg_confidence = (
            sum(d.confidence for d in decisions) / len(decisions) if decisions else 0
        )

        return {
            "mode": self.config.mode,
            "total_decisions": len(decisions),
            "action_counts": action_counts,
            "avg_confidence": avg_confidence,
            "focus_keywords": self.config.attention_config.focus_keywords,
            "attention_strategy": self.config.attention_config.strategy,
        }

    async def generate_crawl_plan(
        self,
        seed: SeedPoint,
        max_pages: int = 100,
    ) -> Dict[str, Any]:
        """
        生成爬取计划

        Args:
            seed: 种子据点
            max_pages: 最大页面数

        Returns:
            爬取计划
        """
        plan = {
            "seed_id": seed.seed_id,
            "seed_url": seed.url,
            "seed_name": seed.name,
            "max_pages": min(max_pages, seed.max_pages),
            "max_depth": seed.max_depth,
            "priority": seed.priority,
            "estimated_duration": f"{max_pages * 2 / 60:.1f} 分钟",
            "strategy": self.config.attention_config.strategy.value,
            "focus_keywords": self.config.attention_config.focus_keywords,
            "phases": [
                {
                    "phase": 1,
                    "name": "种子初始化",
                    "description": f"从种子据点 {seed.name} 开始爬取",
                    "pages": 1,
                },
                {
                    "phase": 2,
                    "name": "广度扩展",
                    "description": "广度优先探索，发现更多链接",
                    "pages": int(max_pages * 0.3),
                },
                {
                    "phase": 3,
                    "name": "注意力聚焦",
                    "description": "基于注意力评分，聚焦高价值内容",
                    "pages": int(max_pages * 0.5),
                },
                {
                    "phase": 4,
                    "name": "深度挖掘",
                    "description": "对高价值节点进行深度爬取",
                    "pages": int(max_pages * 0.2),
                },
            ],
            "created_at": datetime.now().isoformat(),
        }

        logger.info(f"生成爬取计划: {seed.name}, {max_pages}页")
        return plan

    def get_crawl_priority(self, node: CrawlNode) -> int:
        """
        获取节点的爬取优先级

        Args:
            node: 节点

        Returns:
            优先级（1-10）
        """
        score = self.attention_scorer.score_node(node, self.graph)
        return max(1, min(10, int(score.total * 10)))
