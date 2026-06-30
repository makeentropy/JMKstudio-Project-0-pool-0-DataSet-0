"""
种子据点管理器

管理爬虫的起始据点（Seed URLs / 据点），支持：
- 多分类种子管理
- 优先级排序
- 启用/禁用控制
- 批量导入导出
- 健康度检测
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class SeedCategory(str, Enum):
    """种子据点分类"""

    NEWS_PORTAL = "news_portal"
    SOCIAL_MEDIA = "social_media"
    FORUM = "forum"
    BLOG = "blog"
    E_COMMERCE = "e_commerce"
    DOCUMENTATION = "documentation"
    SEARCH_ENGINE = "search_engine"
    ACADEMIC = "academic"
    CUSTOM = "custom"


class SeedStatus(str, Enum):
    """种子状态"""

    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class SeedPoint(BaseModel):
    """种子据点

    代表一个爬虫的起始据点（Base Point / 据点）。
    """

    seed_id: str = Field(description="据点唯一标识")
    url: str = Field(description="据点URL")
    name: str = Field(default="", description="据点名称")
    category: SeedCategory = Field(default=SeedCategory.CUSTOM, description="分类")
    priority: int = Field(default=5, ge=1, le=10, description="优先级（1-10）")
    status: SeedStatus = Field(default=SeedStatus.ACTIVE, description="状态")
    description: str = Field(default="", description="描述")
    tags: List[str] = Field(default_factory=list, description="标签")
    max_depth: int = Field(default=3, ge=0, description="最大爬取深度")
    max_pages: int = Field(default=1000, ge=1, description="最大页面数")
    allowed_domains: List[str] = Field(default_factory=list, description="允许的域名列表")
    denied_domains: List[str] = Field(default_factory=list, description="禁止的域名列表")

    # 统计信息
    pages_crawled: int = Field(default=0, description="已爬取页面数")
    last_crawled_at: Optional[str] = Field(default=None, description="上次爬取时间")
    health_score: float = Field(default=1.0, ge=0.0, le=1.0, description="健康度分数")
    failure_count: int = Field(default=0, description="失败次数")

    # 元数据
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    model_config = ConfigDict(use_enum_values=True)

    def get_domain(self) -> str:
        """获取据点域名"""
        parsed = urlparse(self.url)
        return parsed.netloc

    def is_active(self) -> bool:
        """检查据点是否活跃"""
        return self.status == SeedStatus.ACTIVE

    def record_success(self) -> None:
        """记录成功爬取"""
        self.pages_crawled += 1
        self.last_crawled_at = datetime.now().isoformat()
        self.failure_count = max(0, self.failure_count - 1)
        self.health_score = min(1.0, self.health_score + 0.01)

    def record_failure(self) -> None:
        """记录失败"""
        self.failure_count += 1
        self.health_score = max(0.0, self.health_score - 0.1)
        if self.failure_count >= 10:
            self.status = SeedStatus.FAILED


class SeedManager:
    """种子据点管理器

    管理所有爬虫起始据点，支持增删改查、分类、优先级和健康度管理。
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        初始化种子管理器

        Args:
            storage_path: 持久化存储路径
        """
        self._seeds: Dict[str, SeedPoint] = {}
        self._storage_path = storage_path
        if storage_path and storage_path.exists():
            self._load()

    def add_seed(self, seed: SeedPoint) -> str:
        """
        添加种子据点

        Args:
            seed: 种子据点

        Returns:
            据点ID
        """
        if not seed.seed_id:
            seed.seed_id = f"seed_{len(self._seeds) + 1}"

        self._seeds[seed.seed_id] = seed
        logger.info(f"添加种子据点: {seed.seed_id} ({seed.url})")
        self._save()
        return seed.seed_id

    def add_seed_url(
        self,
        url: str,
        name: str = "",
        category: SeedCategory = SeedCategory.CUSTOM,
        priority: int = 5,
        **kwargs,
    ) -> str:
        """
        通过URL快速添加种子据点

        Args:
            url: 据点URL
            name: 名称
            category: 分类
            priority: 优先级
            **kwargs: 其他参数

        Returns:
            据点ID
        """
        seed_id = f"seed_{len(self._seeds) + 1}_{abs(hash(url)) % 10000}"
        seed = SeedPoint(
            seed_id=seed_id,
            url=url,
            name=name or url,
            category=category,
            priority=priority,
            **kwargs,
        )
        return self.add_seed(seed)

    def remove_seed(self, seed_id: str) -> bool:
        """
        移除种子据点

        Args:
            seed_id: 据点ID

        Returns:
            是否成功
        """
        if seed_id in self._seeds:
            del self._seeds[seed_id]
            logger.info(f"移除种子据点: {seed_id}")
            self._save()
            return True
        return False

    def get_seed(self, seed_id: str) -> Optional[SeedPoint]:
        """
        获取种子据点

        Args:
            seed_id: 据点ID

        Returns:
            种子据点，不存在返回None
        """
        return self._seeds.get(seed_id)

    def get_all_seeds(self) -> List[SeedPoint]:
        """
        获取所有种子据点

        Returns:
            种子据点列表（按优先级降序）
        """
        return sorted(
            self._seeds.values(),
            key=lambda s: (-s.priority, -s.health_score),
        )

    def get_active_seeds(self) -> List[SeedPoint]:
        """
        获取所有活跃的种子据点

        Returns:
            活跃种子列表
        """
        return [s for s in self.get_all_seeds() if s.is_active()]

    def get_seeds_by_category(self, category: SeedCategory) -> List[SeedPoint]:
        """
        按分类获取种子据点

        Args:
            category: 分类

        Returns:
            该分类的种子列表
        """
        return [s for s in self.get_all_seeds() if s.category == category]

    def get_seeds_by_tag(self, tag: str) -> List[SeedPoint]:
        """
        按标签获取种子据点

        Args:
            tag: 标签

        Returns:
            包含该标签的种子列表
        """
        return [s for s in self.get_all_seeds() if tag in s.tags]

    def update_seed(self, seed_id: str, **kwargs) -> bool:
        """
        更新种子据点属性

        Args:
            seed_id: 据点ID
            **kwargs: 要更新的属性

        Returns:
            是否成功
        """
        seed = self._seeds.get(seed_id)
        if not seed:
            return False

        for key, value in kwargs.items():
            if hasattr(seed, key):
                setattr(seed, key, value)

        self._save()
        return True

    def pause_seed(self, seed_id: str) -> bool:
        """
        暂停种子据点

        Args:
            seed_id: 据点ID

        Returns:
            是否成功
        """
        return self.update_seed(seed_id, status=SeedStatus.PAUSED)

    def resume_seed(self, seed_id: str) -> bool:
        """
        恢复种子据点

        Args:
            seed_id: 据点ID

        Returns:
            是否成功
        """
        return self.update_seed(seed_id, status=SeedStatus.ACTIVE)

    def get_next_seed(self) -> Optional[SeedPoint]:
        """
        获取下一个要爬取的种子据点（优先级最高的活跃种子）

        Returns:
            种子据点
        """
        active = self.get_active_seeds()
        if active:
            return active[0]
        return None

    def batch_import(self, seeds: List[Dict[str, Any]]) -> int:
        """
        批量导入种子据点

        Args:
            seeds: 种子数据列表

        Returns:
            成功导入数量
        """
        count = 0
        for seed_data in seeds:
            try:
                seed = SeedPoint(**seed_data)
                self.add_seed(seed)
                count += 1
            except Exception as e:
                logger.warning(f"导入种子失败: {seed_data.get('url', 'unknown')}, 错误: {e}")
        logger.info(f"批量导入完成: 成功{count}个，失败{len(seeds) - count}个")
        return count

    def export_seeds(self, output_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        导出所有种子据点

        Args:
            output_path: 输出文件路径（JSON格式）

        Returns:
            种子数据列表
        """
        seeds_data = [seed.model_dump() for seed in self.get_all_seeds()]
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(seeds_data, f, indent=2, ensure_ascii=False)
            logger.info(f"种子已导出到: {output_path}")
        return seeds_data

    def get_stats(self) -> Dict[str, Any]:
        """
        获取种子统计信息

        Returns:
            统计字典
        """
        all_seeds = self.get_all_seeds()
        categories = {}
        for seed in all_seeds:
            cat = seed.category
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total": len(all_seeds),
            "active": len(self.get_active_seeds()),
            "paused": sum(1 for s in all_seeds if s.status == SeedStatus.PAUSED),
            "failed": sum(1 for s in all_seeds if s.status == SeedStatus.FAILED),
            "total_pages_crawled": sum(s.pages_crawled for s in all_seeds),
            "categories": categories,
            "avg_health": (
                sum(s.health_score for s in all_seeds) / len(all_seeds)
                if all_seeds
                else 0.0
            ),
        }

    def _load(self) -> None:
        """从文件加载种子数据"""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for seed_data in data:
                try:
                    seed = SeedPoint(**seed_data)
                    self._seeds[seed.seed_id] = seed
                except Exception as e:
                    logger.warning(f"加载种子失败: {e}")

            logger.info(f"已加载 {len(self._seeds)} 个种子据点")
        except Exception as e:
            logger.error(f"加载种子文件失败: {e}")

    def _save(self) -> None:
        """保存种子数据到文件"""
        if not self._storage_path:
            return

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            seeds_data = [seed.model_dump() for seed in self._seeds.values()]
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(seeds_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存种子文件失败: {e}")
