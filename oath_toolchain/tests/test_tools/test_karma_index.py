"""标签索引与检索单元测试。"""
import json
import os
import tempfile

import pytest

from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag
from oath_toolchain.tools.karma_tags.tag_index import TagIndex


class TestTagIndex:
    """测试TagIndex类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.index = TagIndex()
        self.tag1 = KarmaTag(
            tag_id="tag-1",
            datafor="用途1",
            datefor="20240101",
            datatag=["标签a", "标签b"],
            tag=["通用1"],
        )
        self.tag2 = KarmaTag(
            tag_id="tag-2",
            datafor="用途2",
            datefor="20240201",
            datatag=["标签b", "标签c"],
            tag=["通用2"],
        )
        self.tag3 = KarmaTag(
            tag_id="tag-3",
            datafor="用途1",
            datefor="20240301",
            datatag=["标签a"],
            tag=["通用1", "通用2"],
        )

    def test_initialization(self):
        """测试初始化。"""
        assert len(self.index) == 0

    def test_add_tag(self):
        """测试添加标签。"""
        self.index.add_tag(self.tag1)
        assert len(self.index) == 1
        assert "tag-1" in self.index

    def test_add_tag_with_dataset(self):
        """测试带数据集ID添加标签。"""
        self.index.add_tag(self.tag1, dataset_id="dataset-1")
        tag, did = self.index.get_by_id("tag-1")
        assert did == "dataset-1"

    def test_add_multiple_tags(self):
        """测试添加多个标签。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        assert len(self.index) == 3

    def test_remove_tag_exists(self):
        """测试移除存在的标签。"""
        self.index.add_tag(self.tag1)
        assert len(self.index) == 1
        result = self.index.remove_tag("tag-1")
        assert result is True
        assert len(self.index) == 0
        assert "tag-1" not in self.index

    def test_remove_tag_not_exists(self):
        """测试移除不存在的标签。"""
        result = self.index.remove_tag("nonexistent")
        assert result is False

    def test_remove_updates_indexes(self):
        """测试移除标签后索引更新。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        results_before = self.index.search({"datafor": "用途1"})
        assert len(results_before) == 2

        self.index.remove_tag("tag-1")
        results_after = self.index.search({"datafor": "用途1"})
        assert len(results_after) == 1
        assert results_after[0][0].tag_id == "tag-3"

    def test_search_empty_filters(self):
        """测试空过滤条件搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        results = self.index.search({})
        assert len(results) == 2

    def test_search_by_datafor(self):
        """测试按datafor搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        results = self.index.search({"datafor": "用途1"})
        assert len(results) == 2
        tag_ids = [t.tag_id for t, _ in results]
        assert "tag-1" in tag_ids
        assert "tag-3" in tag_ids

    def test_search_by_datefor(self):
        """测试按datefor搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        results = self.index.search({"datefor": "20240101"})
        assert len(results) == 1
        assert results[0][0].tag_id == "tag-1"

    def test_search_by_datatag_single(self):
        """测试按单个datatag搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        results = self.index.search({"datatag": "标签b"})
        assert len(results) == 2
        tag_ids = [t.tag_id for t, _ in results]
        assert "tag-1" in tag_ids
        assert "tag-2" in tag_ids

    def test_search_by_datatag_multiple(self):
        """测试按多个datatag搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        results = self.index.search({"datatag": ["标签a", "标签c"]})
        assert len(results) == 3

    def test_search_by_tag_single(self):
        """测试按单个tag搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        results = self.index.search({"tag": "通用1"})
        assert len(results) == 2
        tag_ids = [t.tag_id for t, _ in results]
        assert "tag-1" in tag_ids
        assert "tag-3" in tag_ids

    def test_search_by_tag_multiple(self):
        """测试按多个tag搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        results = self.index.search({"tag": ["通用1", "通用2"]})
        assert len(results) == 3

    def test_search_by_date_range(self):
        """测试按日期范围搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        results = self.index.search({"date_range": ("20240101", "20240215")})
        assert len(results) == 2
        tag_ids = [t.tag_id for t, _ in results]
        assert "tag-1" in tag_ids
        assert "tag-2" in tag_ids

    def test_search_by_dataset_id(self):
        """测试按数据集ID搜索。"""
        self.index.add_tag(self.tag1, dataset_id="ds1")
        self.index.add_tag(self.tag2, dataset_id="ds2")
        self.index.add_tag(self.tag3, dataset_id="ds1")
        results = self.index.search({"dataset_id": "ds1"})
        assert len(results) == 2
        tag_ids = [t.tag_id for t, _ in results]
        assert "tag-1" in tag_ids
        assert "tag-3" in tag_ids

    def test_search_combined_filters(self):
        """测试组合过滤条件搜索。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        results = self.index.search({
            "datafor": "用途1",
            "datatag": "标签a",
        })
        assert len(results) == 2

    def test_search_no_results(self):
        """测试搜索无结果。"""
        self.index.add_tag(self.tag1)
        results = self.index.search({"datafor": "不存在的用途"})
        assert len(results) == 0

    def test_get_by_id_exists(self):
        """测试按ID获取存在的标签。"""
        self.index.add_tag(self.tag1, dataset_id="ds1")
        result = self.index.get_by_id("tag-1")
        assert result is not None
        tag, did = result
        assert tag.tag_id == "tag-1"
        assert did == "ds1"

    def test_get_by_id_not_exists(self):
        """测试按ID获取不存在的标签。"""
        result = self.index.get_by_id("nonexistent")
        assert result is None

    def test_list_tags(self):
        """测试列出标签。"""
        self.index.add_tag(self.tag1)
        self.index.add_tag(self.tag2)
        self.index.add_tag(self.tag3)
        tags = self.index.list_tags()
        assert len(tags) == 3

    def test_list_tags_pagination(self):
        """测试分页列出标签。"""
        for i in range(10):
            tag = KarmaTag(
                tag_id=f"paginate-{i}",
                datafor=f"用途{i}",
                datefor="20240101",
            )
            self.index.add_tag(tag)

        page1 = self.index.list_tags(limit=3, offset=0)
        assert len(page1) == 3

        page2 = self.index.list_tags(limit=3, offset=3)
        assert len(page2) == 3

        last = self.index.list_tags(limit=3, offset=9)
        assert len(last) == 1

    def test_get_tag_statistics_empty(self):
        """测试空索引统计。"""
        stats = self.index.get_tag_statistics()
        assert stats["total_tags"] == 0
        assert stats["unique_datafor"] == 0
        assert stats["unique_datefor"] == 0
        assert stats["unique_datatag"] == 0
        assert stats["unique_tag"] == 0
        assert stats["signed_count"] == 0
        assert stats["dataset_count"] == 0

    def test_get_tag_statistics(self):
        """测试索引统计。"""
        self.index.add_tag(self.tag1, dataset_id="ds1")
        self.index.add_tag(self.tag2, dataset_id="ds1")
        self.index.add_tag(self.tag3, dataset_id="ds2")

        stats = self.index.get_tag_statistics()
        assert stats["total_tags"] == 3
        assert stats["unique_datafor"] == 2
        assert stats["unique_datefor"] == 3
        assert stats["unique_datatag"] == 3
        assert stats["unique_tag"] == 2
        assert stats["dataset_count"] == 2

    def test_get_tag_statistics_with_signers(self):
        """测试带签名的统计。"""
        tag_signed = KarmaTag(
            tag_id="signed-1",
            datafor="test",
            datefor="20240101",
            gpgca="fake-signature",
        )
        self.index.add_tag(tag_signed)
        stats = self.index.get_tag_statistics()
        assert stats["signed_count"] >= 1
        assert "gpgca" in stats["signer_distribution"]

    def test_build_index(self):
        """测试批量构建索引。"""
        tags = [self.tag1, self.tag2, self.tag3]
        self.index.build_index(tags)
        assert len(self.index) == 3
        assert "tag-1" in self.index
        assert "tag-2" in self.index
        assert "tag-3" in self.index

    def test_save_and_load_index_pickle(self):
        """测试保存和加载索引（pickle格式）。"""
        self.index.add_tag(self.tag1, dataset_id="ds1")
        self.index.add_tag(self.tag2, dataset_id="ds2")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            filepath = f.name

        try:
            self.index.save_index(filepath)
            assert os.path.exists(filepath)

            new_index = TagIndex()
            new_index.load_index(filepath)
            assert len(new_index) == 2

            tag1, did1 = new_index.get_by_id("tag-1")
            assert tag1.datafor == "用途1"
            assert did1 == "ds1"

            tag2, did2 = new_index.get_by_id("tag-2")
            assert tag2.datafor == "用途2"
            assert did2 == "ds2"
        finally:
            os.unlink(filepath)

    def test_save_and_load_index_json(self):
        """测试保存和加载索引（JSON格式）。"""
        self.index.add_tag(self.tag1, dataset_id="ds1")
        self.index.add_tag(self.tag2, dataset_id="ds2")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
            filepath = f.name

        try:
            self.index.save_json(filepath)
            assert os.path.exists(filepath)

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert "tags" in data
            assert len(data["tags"]) == 2

            new_index = TagIndex()
            new_index.load_json(filepath)
            assert len(new_index) == 2

            tag1, did1 = new_index.get_by_id("tag-1")
            assert tag1.datafor == "用途1"
            assert did1 == "ds1"
        finally:
            os.unlink(filepath)

    def test_contains(self):
        """测试in运算符。"""
        assert "tag-1" not in self.index
        self.index.add_tag(self.tag1)
        assert "tag-1" in self.index

    def test_len(self):
        """测试len函数。"""
        assert len(self.index) == 0
        self.index.add_tag(self.tag1)
        assert len(self.index) == 1
        self.index.add_tag(self.tag2)
        assert len(self.index) == 2
        self.index.remove_tag("tag-1")
        assert len(self.index) == 1

    def test_search_by_signer(self):
        """测试按签名者搜索。"""
        tag_gpg = KarmaTag(
            tag_id="gpg-tag",
            datafor="test",
            datefor="20240101",
            gpgca="gpg-sig",
        )
        tag_jmk = KarmaTag(
            tag_id="jmk-tag",
            datafor="test",
            datefor="20240101",
            jmkca="jmk-sig",
        )
        tag_both = KarmaTag(
            tag_id="both-tag",
            datafor="test",
            datefor="20240101",
            gpgca="gpg-sig",
            jmkca="jmk-sig",
        )
        self.index.add_tag(tag_gpg)
        self.index.add_tag(tag_jmk)
        self.index.add_tag(tag_both)

        results = self.index.search({"signer": "gpgca"})
        assert len(results) == 2

        results = self.index.search({"signer": ["gpgca", "jmkca"]})
        assert len(results) == 3

    def test_full_search_flow(self):
        """测试完整的搜索流程。"""
        for i in range(20):
            tag = KarmaTag(
                tag_id=f"full-tag-{i}",
                datafor=f"用途{i % 3}",
                datefor=f"2024{str(i % 12 + 1).zfill(2)}01",
                datatag=[f"标签{i % 5}"],
                tag=[f"通用{i % 4}"],
            )
            self.index.add_tag(tag, dataset_id=f"ds-{i % 2}")

        assert len(self.index) == 20

        results = self.index.search({"datafor": "用途0"})
        assert len(results) == 7

        results = self.index.search({"date_range": ("20240101", "20240630")})
        assert len(results) == 12

        results = self.index.search({
            "datafor": "用途1",
            "tag": "通用2",
        })
        assert len(results) >= 1

        stats = self.index.get_tag_statistics()
        assert stats["total_tags"] == 20
        assert stats["dataset_count"] == 2
