"""Dataset数据集数据结构单元测试。"""
import pytest
import time

from oath_toolchain.tools.dataset_pool.dataset import Dataset
from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag


class TestDataset:
    """测试Dataset类。"""

    def test_initialization_default(self):
        """测试默认初始化。"""
        dataset = Dataset()
        assert dataset.dataset_id is not None
        assert dataset.name == ""
        assert dataset.description == ""
        assert dataset.created_at > 0
        assert dataset.updated_at >= dataset.created_at
        assert dataset.version == "1.0.0"
        assert dataset.size == 0
        assert dataset.record_count == 0
        assert dataset.format == "json"
        assert dataset.tags == []
        assert dataset.metadata == {}
        assert dataset.quality_score == 0.0
        assert dataset.data is None

    def test_initialization_with_params(self):
        """测试带参数初始化。"""
        dataset = Dataset(dataset_id="test-id", name="测试数据集")
        assert dataset.dataset_id == "test-id"
        assert dataset.name == "测试数据集"

    def test_data_setter_dict(self):
        """测试设置dict类型数据。"""
        dataset = Dataset()
        data = {"key": "value", "records": [1, 2, 3]}
        dataset.data = data
        assert dataset.data == data
        assert dataset.size > 0
        assert dataset.record_count == 3

    def test_data_setter_bytes(self):
        """测试设置bytes类型数据。"""
        dataset = Dataset()
        data = b"hello world"
        dataset.data = data
        assert dataset.data == data
        assert dataset.size == len(data)
        assert dataset.record_count == 0

    def test_data_setter_none(self):
        """测试设置None数据。"""
        dataset = Dataset()
        dataset.data = {"key": "value"}
        assert dataset.size > 0
        dataset.data = None
        assert dataset.data is None
        assert dataset.size == 0
        assert dataset.record_count == 0

    def test_to_dict(self):
        """测试序列化为字典。"""
        dataset = Dataset(name="测试")
        dataset.data = {"records": [1, 2, 3]}
        dataset.metadata = {"author": "test"}

        result = dataset.to_dict()
        assert result["name"] == "测试"
        assert result["dataset_id"] == dataset.dataset_id
        assert result["metadata"] == {"author": "test"}
        assert "data" in result
        assert result["data"]["type"] == "dict"

    def test_to_dict_with_bytes_data(self):
        """测试bytes数据的序列化。"""
        dataset = Dataset()
        dataset.data = b"binary data"

        result = dataset.to_dict()
        assert result["data"]["type"] == "bytes"
        assert "content" in result["data"]

    def test_to_dict_without_data(self):
        """测试无数据时的序列化。"""
        dataset = Dataset()
        result = dataset.to_dict()
        assert "data" not in result

    def test_from_dict(self):
        """测试从字典反序列化。"""
        data = {
            "dataset_id": "test-123",
            "name": "测试数据集",
            "description": "这是一个测试",
            "version": "2.0.0",
            "format": "csv",
            "quality_score": 95.5,
            "metadata": {"source": "test"},
            "tags": [],
            "data": {
                "type": "dict",
                "content": {"key": "value"},
            },
        }

        dataset = Dataset.from_dict(data)
        assert dataset.dataset_id == "test-123"
        assert dataset.name == "测试数据集"
        assert dataset.description == "这是一个测试"
        assert dataset.version == "2.0.0"
        assert dataset.format == "csv"
        assert dataset.quality_score == 95.5
        assert dataset.metadata == {"source": "test"}
        assert dataset.data == {"key": "value"}

    def test_from_dict_with_bytes_data(self):
        """测试从带bytes数据的字典反序列化。"""
        import base64
        original_data = b"binary data"
        data = {
            "dataset_id": "test-bytes",
            "name": "二进制测试",
            "data": {
                "type": "bytes",
                "content": base64.b64encode(original_data).decode("utf-8"),
            },
        }

        dataset = Dataset.from_dict(data)
        assert dataset.data == original_data

    def test_from_dict_minimal(self):
        """测试最小数据反序列化。"""
        dataset = Dataset.from_dict({})
        assert dataset.dataset_id is not None
        assert dataset.name == ""

    def test_add_tag(self):
        """测试添加标签。"""
        dataset = Dataset()
        tag = KarmaTag(datafor="测试", datefor="20240101")

        dataset.add_tag(tag)
        assert len(dataset.tags) == 1
        assert dataset.tags[0].tag_id == tag.tag_id

    def test_add_tag_duplicate(self):
        """测试添加重复标签。"""
        dataset = Dataset()
        tag = KarmaTag(datafor="测试", datefor="20240101")

        dataset.add_tag(tag)
        dataset.add_tag(tag)
        assert len(dataset.tags) == 1

    def test_remove_tag(self):
        """测试移除标签。"""
        dataset = Dataset()
        tag = KarmaTag(datafor="测试", datefor="20240101", tag_id="tag-1")

        dataset.add_tag(tag)
        result = dataset.remove_tag("tag-1")
        assert result is True
        assert len(dataset.tags) == 0

    def test_remove_tag_not_found(self):
        """测试移除不存在的标签。"""
        dataset = Dataset()
        result = dataset.remove_tag("nonexistent")
        assert result is False

    def test_get_tags(self):
        """测试获取标签列表。"""
        dataset = Dataset()
        tag1 = KarmaTag(datafor="测试1", datefor="20240101", tag_id="tag-1")
        tag2 = KarmaTag(datafor="测试2", datefor="20240102", tag_id="tag-2")

        dataset.add_tag(tag1)
        dataset.add_tag(tag2)

        tags = dataset.get_tags()
        assert len(tags) == 2
        tags.append(KarmaTag())
        assert len(dataset.tags) == 2

    def test_repr(self):
        """测试repr表示。"""
        dataset = Dataset(dataset_id="test-id", name="测试")
        repr_str = repr(dataset)
        assert "Dataset" in repr_str
        assert "test-id" in repr_str
        assert "测试" in repr_str

    def test_str(self):
        """测试str表示。"""
        dataset = Dataset(dataset_id="test-id", name="测试")
        str_repr = str(dataset)
        assert "test-id" in str_repr
        assert "测试" in str_repr

    def test_eq(self):
        """测试相等性比较。"""
        ds1 = Dataset(dataset_id="same-id")
        ds2 = Dataset(dataset_id="same-id")
        ds3 = Dataset(dataset_id="different-id")

        assert ds1 == ds2
        assert ds1 != ds3
        assert ds1 != "not a dataset"

    def test_hash(self):
        """测试哈希。"""
        ds1 = Dataset(dataset_id="same-id")
        ds2 = Dataset(dataset_id="same-id")

        assert hash(ds1) == hash(ds2)
        assert {ds1, ds2} == {ds1}

    def test_data_updates_timestamp(self):
        """测试设置数据更新时间戳。"""
        dataset = Dataset()
        old_updated = dataset.updated_at
        time.sleep(0.01)
        dataset.data = {"key": "value"}
        assert dataset.updated_at > old_updated

    def test_add_tag_updates_timestamp(self):
        """测试添加标签更新时间戳。"""
        dataset = Dataset()
        old_updated = dataset.updated_at
        time.sleep(0.01)
        dataset.add_tag(KarmaTag(datafor="test", datefor="20240101"))
        assert dataset.updated_at > old_updated

    def test_remove_tag_updates_timestamp(self):
        """测试移除标签更新时间戳。"""
        dataset = Dataset()
        tag = KarmaTag(datafor="test", datefor="20240101", tag_id="tag-1")
        dataset.add_tag(tag)
        old_updated = dataset.updated_at
        time.sleep(0.01)
        dataset.remove_tag("tag-1")
        assert dataset.updated_at > old_updated

    def test_record_count_with_items(self):
        """测试items键的记录数统计。"""
        dataset = Dataset()
        dataset.data = {"items": [1, 2, 3, 4, 5]}
        assert dataset.record_count == 5

    def test_record_count_single_dict(self):
        """测试单个字典的记录数统计。"""
        dataset = Dataset()
        dataset.data = {"key": "value"}
        assert dataset.record_count == 1
