"""
种子据点模块测试
"""

import pytest
from pathlib import Path

from ai_llm_agent_crawler.seed import SeedManager, SeedPoint, SeedCategory, SeedStatus


class TestSeedPoint:
    """SeedPoint 测试"""

    def test_create_seed(self):
        """测试创建种子据点"""
        seed = SeedPoint(
            seed_id="test_1",
            url="https://example.com",
            name="Test Site",
            category=SeedCategory.NEWS_PORTAL,
            priority=8,
        )
        assert seed.seed_id == "test_1"
        assert seed.url == "https://example.com"
        assert seed.name == "Test Site"
        assert seed.priority == 8
        assert seed.is_active()

    def test_get_domain(self):
        """测试获取域名"""
        seed = SeedPoint(seed_id="1", url="https://www.example.com/page")
        assert seed.get_domain() == "www.example.com"

    def test_record_success(self):
        """测试记录成功"""
        seed = SeedPoint(seed_id="1", url="https://example.com")
        initial = seed.pages_crawled
        seed.record_success()
        assert seed.pages_crawled == initial + 1
        assert seed.last_crawled_at is not None

    def test_record_failure(self):
        """测试记录失败"""
        seed = SeedPoint(seed_id="1", url="https://example.com")
        initial_health = seed.health_score
        seed.record_failure()
        assert seed.failure_count == 1
        assert seed.health_score < initial_health

    def test_seed_status_failed(self):
        """测试失败状态触发"""
        seed = SeedPoint(seed_id="1", url="https://example.com")
        for _ in range(10):
            seed.record_failure()
        assert seed.status == SeedStatus.FAILED


class TestSeedManager:
    """SeedManager 测试"""

    def test_create_manager(self):
        """测试创建管理器"""
        mgr = SeedManager()
        assert mgr.get_stats()["total"] == 0

    def test_add_seed_url(self):
        """测试添加种子URL"""
        mgr = SeedManager()
        seed_id = mgr.add_seed_url("https://example.com", name="Example")
        assert seed_id is not None
        assert mgr.get_stats()["total"] == 1

        seed = mgr.get_seed(seed_id)
        assert seed is not None
        assert seed.url == "https://example.com"

    def test_add_seed(self):
        """测试添加种子对象"""
        mgr = SeedManager()
        seed = SeedPoint(
            seed_id="custom_1",
            url="https://test.com",
            name="Test",
        )
        seed_id = mgr.add_seed(seed)
        assert seed_id == "custom_1"
        assert mgr.get_seed("custom_1") is not None

    def test_remove_seed(self):
        """测试移除种子"""
        mgr = SeedManager()
        seed_id = mgr.add_seed_url("https://example.com")
        assert mgr.remove_seed(seed_id) is True
        assert mgr.get_seed(seed_id) is None
        assert mgr.remove_seed("nonexistent") is False

    def test_get_active_seeds(self):
        """测试获取活跃种子"""
        mgr = SeedManager()
        mgr.add_seed_url("https://a.com")
        id2 = mgr.add_seed_url("https://b.com")
        mgr.pause_seed(id2)

        active = mgr.get_active_seeds()
        assert len(active) == 1
        assert active[0].url == "https://a.com"

    def test_get_seeds_by_category(self):
        """测试按分类获取种子"""
        mgr = SeedManager()
        mgr.add_seed_url("https://news.com", category=SeedCategory.NEWS_PORTAL)
        mgr.add_seed_url("https://blog.com", category=SeedCategory.BLOG)

        news = mgr.get_seeds_by_category(SeedCategory.NEWS_PORTAL)
        assert len(news) == 1
        assert news[0].url == "https://news.com"

    def test_get_seeds_by_tag(self):
        """测试按标签获取种子"""
        mgr = SeedManager()
        mgr.add_seed_url("https://a.com", tags=["tech", "news"])
        mgr.add_seed_url("https://b.com", tags=["tech"])

        tech_seeds = mgr.get_seeds_by_tag("tech")
        assert len(tech_seeds) == 2

        news_seeds = mgr.get_seeds_by_tag("news")
        assert len(news_seeds) == 1

    def test_pause_and_resume(self):
        """测试暂停和恢复"""
        mgr = SeedManager()
        seed_id = mgr.add_seed_url("https://example.com")

        assert mgr.pause_seed(seed_id)
        seed = mgr.get_seed(seed_id)
        assert seed.status == SeedStatus.PAUSED

        assert mgr.resume_seed(seed_id)
        seed = mgr.get_seed(seed_id)
        assert seed.status == SeedStatus.ACTIVE

    def test_get_next_seed(self):
        """测试获取下一个种子"""
        mgr = SeedManager()
        mgr.add_seed_url("https://low.com", priority=2)
        mgr.add_seed_url("https://high.com", priority=9)

        next_seed = mgr.get_next_seed()
        assert next_seed is not None
        assert next_seed.url == "https://high.com"

    def test_update_seed(self):
        """测试更新种子属性"""
        mgr = SeedManager()
        seed_id = mgr.add_seed_url("https://example.com", name="Old Name")

        assert mgr.update_seed(seed_id, name="New Name", priority=10)
        seed = mgr.get_seed(seed_id)
        assert seed.name == "New Name"
        assert seed.priority == 10

    def test_get_stats(self):
        """测试获取统计信息"""
        mgr = SeedManager()
        mgr.add_seed_url("https://a.com")
        mgr.add_seed_url("https://b.com")

        stats = mgr.get_stats()
        assert stats["total"] == 2
        assert stats["active"] == 2
        assert "categories" in stats

    def test_batch_import(self):
        """测试批量导入"""
        mgr = SeedManager()
        seeds_data = [
            {"seed_id": "b1", "url": "https://b1.com", "name": "B1"},
            {"seed_id": "b2", "url": "https://b2.com", "name": "B2"},
        ]
        count = mgr.batch_import(seeds_data)
        assert count == 2
        assert mgr.get_stats()["total"] == 2

    def test_export_seeds(self):
        """测试导出种子"""
        mgr = SeedManager()
        mgr.add_seed_url("https://example.com")

        data = mgr.export_seeds()
        assert len(data) == 1
        assert data[0]["url"] == "https://example.com"

    def test_persistence(self, tmp_path):
        """测试持久化存储"""
        storage_path = tmp_path / "seeds.json"

        mgr1 = SeedManager(storage_path)
        mgr1.add_seed_url("https://example.com", name="Test")
        mgr1.export_seeds(storage_path)

        mgr2 = SeedManager(storage_path)
        assert mgr2.get_stats()["total"] == 1
        seeds = mgr2.get_all_seeds()
        assert seeds[0].url == "https://example.com"
        assert seeds[0].name == "Test"
