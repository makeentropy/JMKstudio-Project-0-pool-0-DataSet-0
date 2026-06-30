"""Karma标签数据结构单元测试。"""
import base64
import json

import pytest

from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag


class TestKarmaTag:
    """测试KarmaTag类。"""

    def test_initialization_defaults(self):
        """测试默认初始化。"""
        tag = KarmaTag()
        assert tag.datafor == ""
        assert tag.datefor == ""
        assert tag.datatag == []
        assert tag.base64 == ""
        assert tag.tag == []
        assert tag.gpgca == ""
        assert tag.jmkca == ""
        assert tag.encrypt_xor is False
        assert tag.stego_dim == 0
        assert tag.dict_ca == ""
        assert tag.tag_id != ""

    def test_initialization_with_params(self):
        """测试带参数初始化。"""
        tag = KarmaTag(
            datafor="测试数据",
            datefor="20240101",
            datatag=["标签1", "标签2"],
            base64="dGVzdA==",
            tag=["通用标签"],
            gpgca="gpg签名",
            jmkca="jmk签名",
            encrypt_xor=True,
            stego_dim=3,
            dict_ca="dict-ca-1",
            tag_id="test-tag-123",
        )
        assert tag.datafor == "测试数据"
        assert tag.datefor == "20240101"
        assert tag.datatag == ["标签1", "标签2"]
        assert tag.base64 == "dGVzdA=="
        assert tag.tag == ["通用标签"]
        assert tag.gpgca == "gpg签名"
        assert tag.jmkca == "jmk签名"
        assert tag.encrypt_xor is True
        assert tag.stego_dim == 3
        assert tag.dict_ca == "dict-ca-1"
        assert tag.tag_id == "test-tag-123"

    def test_initialization_with_custom_fields(self):
        """测试自定义字段初始化。"""
        tag = KarmaTag(
            datafor="测试",
            datefor="20240101",
            custom_field_1="value1",
            custom_field_2=123,
        )
        assert tag.get_custom_field("custom_field_1") == "value1"
        assert tag.get_custom_field("custom_field_2") == 123
        assert tag.get_custom_field("nonexistent") is None

    def test_to_dict(self):
        """测试序列化为字典。"""
        tag = KarmaTag(
            datafor="测试",
            datefor="20240101",
            datatag=["tag1"],
            tag=["general"],
            custom_field="custom_value",
        )
        d = tag.to_dict()
        assert d["datafor"] == "测试"
        assert d["datefor"] == "20240101"
        assert d["datatag"] == ["tag1"]
        assert d["tag"] == ["general"]
        assert d["custom_field"] == "custom_value"
        assert "tag_id" in d

    def test_from_dict(self):
        """测试从字典创建。"""
        data = {
            "datafor": "测试数据",
            "datefor": "20240101",
            "datatag": ["tag1", "tag2"],
            "tag": ["general"],
            "custom_field": "custom_value",
        }
        tag = KarmaTag.from_dict(data)
        assert tag.datafor == "测试数据"
        assert tag.datefor == "20240101"
        assert tag.datatag == ["tag1", "tag2"]
        assert tag.tag == ["general"]
        assert tag.get_custom_field("custom_field") == "custom_value"

    def test_dict_roundtrip(self):
        """测试字典序列化往返。"""
        original = KarmaTag(
            datafor="往返测试",
            datefor="20240630",
            datatag=["a", "b"],
            tag=["x", "y"],
            encrypt_xor=True,
            stego_dim=5,
            custom_key="custom_val",
        )
        d = original.to_dict()
        restored = KarmaTag.from_dict(d)
        assert restored.datafor == original.datafor
        assert restored.datefor == original.datefor
        assert restored.datatag == original.datatag
        assert restored.tag == original.tag
        assert restored.encrypt_xor == original.encrypt_xor
        assert restored.stego_dim == original.stego_dim
        assert restored.get_custom_field("custom_key") == original.get_custom_field("custom_key")
        assert restored.tag_id == original.tag_id

    def test_to_json(self):
        """测试序列化为JSON。"""
        tag = KarmaTag(
            datafor="JSON测试",
            datefor="20240101",
            datatag=["标签1"],
        )
        json_str = tag.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["datafor"] == "JSON测试"
        assert parsed["datefor"] == "20240101"

    def test_from_json(self):
        """测试从JSON创建。"""
        json_str = json.dumps({
            "datafor": "JSON测试",
            "datefor": "20240101",
            "datatag": ["tag1"],
        })
        tag = KarmaTag.from_json(json_str)
        assert tag.datafor == "JSON测试"
        assert tag.datefor == "20240101"
        assert tag.datatag == ["tag1"]

    def test_json_roundtrip(self):
        """测试JSON序列化往返。"""
        original = KarmaTag(
            datafor="JSON往返",
            datefor="20240630",
            datatag=["a", "b"],
            tag=["x"],
            encrypt_xor=False,
            stego_dim=2,
        )
        json_str = original.to_json()
        restored = KarmaTag.from_json(json_str)
        assert restored.datafor == original.datafor
        assert restored.datefor == original.datefor
        assert restored.datatag == original.datatag
        assert restored.tag == original.tag
        assert restored.tag_id == original.tag_id

    def test_from_json_invalid(self):
        """测试无效JSON。"""
        with pytest.raises(ValueError, match="无效的JSON标签数据"):
            KarmaTag.from_json("不是有效的json")

    def test_to_base64(self):
        """测试序列化为base64。"""
        tag = KarmaTag(
            datafor="base64测试",
            datefor="20240101",
        )
        b64_str = tag.to_base64()
        assert isinstance(b64_str, str)
        decoded = base64.b64decode(b64_str)
        json_str = decoded.decode("utf-8")
        parsed = json.loads(json_str)
        assert parsed["datafor"] == "base64测试"

    def test_from_base64(self):
        """测试从base64创建。"""
        original = KarmaTag(
            datafor="base64测试",
            datefor="20240101",
            datatag=["t1"],
        )
        b64_str = original.to_base64()
        restored = KarmaTag.from_base64(b64_str)
        assert restored.datafor == "base64测试"
        assert restored.datefor == "20240101"
        assert restored.datatag == ["t1"]
        assert restored.tag_id == original.tag_id

    def test_base64_roundtrip(self):
        """测试base64序列化往返。"""
        original = KarmaTag(
            datafor="base64往返",
            datefor="20240630",
            datatag=["a", "b", "c"],
            tag=["general"],
            encrypt_xor=True,
            stego_dim=4,
            custom_field="custom",
        )
        b64_str = original.to_base64()
        restored = KarmaTag.from_base64(b64_str)
        assert restored.datafor == original.datafor
        assert restored.datefor == original.datefor
        assert restored.datatag == original.datatag
        assert restored.tag == original.tag
        assert restored.encrypt_xor == original.encrypt_xor
        assert restored.stego_dim == original.stego_dim
        assert restored.get_custom_field("custom_field") == original.get_custom_field("custom_field")
        assert restored.tag_id == original.tag_id

    def test_from_base64_invalid(self):
        """测试无效base64。"""
        with pytest.raises(ValueError):
            KarmaTag.from_base64("!!!invalid_base64!!!")

    def test_get_custom_field(self):
        """测试获取自定义字段。"""
        tag = KarmaTag(custom1="val1", custom2=123)
        assert tag.get_custom_field("custom1") == "val1"
        assert tag.get_custom_field("custom2") == 123
        assert tag.get_custom_field("nonexistent") is None

    def test_set_custom_field_new(self):
        """测试设置新的自定义字段。"""
        tag = KarmaTag()
        tag.set_custom_field("new_field", "new_value")
        assert tag.get_custom_field("new_field") == "new_value"

    def test_set_custom_field_existing(self):
        """测试设置已存在的自定义字段。"""
        tag = KarmaTag(existing="old_value")
        tag.set_custom_field("existing", "new_value")
        assert tag.get_custom_field("existing") == "new_value"

    def test_set_custom_field_standard(self):
        """测试设置标准字段。"""
        tag = KarmaTag()
        tag.set_custom_field("datafor", "新的用途")
        assert tag.datafor == "新的用途"

    def test_validate_valid_tag(self):
        """测试验证有效标签。"""
        tag = KarmaTag(
            datafor="有效测试",
            datefor="20240101",
            datatag=["tag1"],
            tag=["general"],
            base64="dGVzdA==",
        )
        valid, errors = tag.validate()
        assert valid is True
        assert errors == []

    def test_validate_missing_datafor(self):
        """测试验证缺少datafor。"""
        tag = KarmaTag(datefor="20240101")
        valid, errors = tag.validate()
        assert valid is False
        assert any("datafor字段不能为空" in e for e in errors)

    def test_validate_missing_datefor(self):
        """测试验证缺少datefor。"""
        tag = KarmaTag(datafor="测试")
        valid, errors = tag.validate()
        assert valid is False
        assert any("datefor字段不能为空" in e for e in errors)

    def test_validate_invalid_datefor_format(self):
        """测试验证datefor格式错误。"""
        tag = KarmaTag(datafor="测试", datefor="2024-01-01")
        valid, errors = tag.validate()
        assert valid is False
        assert any("YYYYMMDD格式" in e for e in errors)

    def test_validate_datefor_short(self):
        """测试验证datefor太短。"""
        tag = KarmaTag(datafor="测试", datefor="2024010")
        valid, errors = tag.validate()
        assert valid is False
        assert any("YYYYMMDD格式" in e for e in errors)

    def test_validate_datatag_not_list(self):
        """测试验证datatag不是列表。"""
        tag = KarmaTag(datafor="测试", datefor="20240101", datatag="notalist")
        valid, errors = tag.validate()
        assert valid is False
        assert any("datatag字段必须是列表类型" in e for e in errors)

    def test_validate_datatag_invalid_item(self):
        """测试验证datatag包含无效项。"""
        tag = KarmaTag(datafor="测试", datefor="20240101", datatag=["valid", 123])
        valid, errors = tag.validate()
        assert valid is False
        assert any("datatag" in e and "必须是字符串类型" in e for e in errors)

    def test_validate_tag_not_list(self):
        """测试验证tag不是列表。"""
        tag = KarmaTag(datafor="测试", datefor="20240101", tag="notalist")
        valid, errors = tag.validate()
        assert valid is False
        assert any("tag字段必须是列表类型" in e for e in errors)

    def test_validate_encrypt_xor_not_bool(self):
        """测试验证encrypt_xor不是布尔值。"""
        tag = KarmaTag(datafor="测试", datefor="20240101")
        tag.encrypt_xor = "notbool"
        valid, errors = tag.validate()
        assert valid is False
        assert any("encrypt_xor字段必须是布尔类型" in e for e in errors)

    def test_validate_stego_dim_not_int(self):
        """测试验证stego_dim不是整数。"""
        tag = KarmaTag(datafor="测试", datefor="20240101")
        tag.stego_dim = "notint"
        valid, errors = tag.validate()
        assert valid is False
        assert any("stego_dim字段必须是整数类型" in e for e in errors)

    def test_validate_stego_dim_negative(self):
        """测试验证stego_dim为负数。"""
        tag = KarmaTag(datafor="测试", datefor="20240101", stego_dim=-1)
        valid, errors = tag.validate()
        assert valid is False
        assert any("stego_dim字段不能为负数" in e for e in errors)

    def test_validate_invalid_base64(self):
        """测试验证无效base64。"""
        tag = KarmaTag(datafor="测试", datefor="20240101", base64="!!!invalid!!!")
        valid, errors = tag.validate()
        assert valid is False
        assert any("base64字段包含无效的base64数据" in e for e in errors)

    def test_validate_empty_tag_id(self):
        """测试验证空tag_id。"""
        tag = KarmaTag(datafor="测试", datefor="20240101", tag_id="")
        valid, errors = tag.validate()
        assert valid is False
        assert any("tag_id字段不能为空" in e for e in errors)

    def test_get_data_for_signing(self):
        """测试获取签名数据。"""
        tag = KarmaTag(
            datafor="签名测试",
            datefor="20240101",
            gpgca="gpg签名值",
            jmkca="jmk签名值",
            custom_field="custom",
        )
        data = tag.get_data_for_signing()
        assert isinstance(data, bytes)
        data_str = data.decode("utf-8")
        assert "签名测试" in data_str
        assert "20240101" in data_str
        assert "gpg签名值" not in data_str
        assert "jmk签名值" not in data_str
        assert "custom" in data_str

    def test_repr(self):
        """测试repr表示。"""
        tag = KarmaTag(datafor="测试", datefor="20240101", tag_id="test-123")
        r = repr(tag)
        assert "KarmaTag" in r
        assert "test-123" in r
        assert "测试" in r
        assert "20240101" in r

    def test_str(self):
        """测试str表示。"""
        tag = KarmaTag(datafor="测试数据", datefor="20240101", tag_id="test-456")
        s = str(tag)
        assert "KarmaTag" in s
        assert "test-456" in s
        assert "测试数据" in s
        assert "20240101" in s

    def test_equality_same_id(self):
        """测试相同tag_id的标签相等。"""
        tag1 = KarmaTag(datafor="a", datefor="20240101", tag_id="same-id")
        tag2 = KarmaTag(datafor="b", datefor="20240202", tag_id="same-id")
        assert tag1 == tag2

    def test_equality_different_id(self):
        """测试不同tag_id的标签不相等。"""
        tag1 = KarmaTag(datafor="a", datefor="20240101", tag_id="id-1")
        tag2 = KarmaTag(datafor="a", datefor="20240101", tag_id="id-2")
        assert tag1 != tag2

    def test_equality_not_tag(self):
        """测试与非标签对象比较。"""
        tag = KarmaTag()
        assert tag != "not a tag"
        assert tag != 123

    def test_hash_same_id(self):
        """测试相同tag_id的标签哈希相同。"""
        tag1 = KarmaTag(tag_id="hash-test-id")
        tag2 = KarmaTag(tag_id="hash-test-id")
        assert hash(tag1) == hash(tag2)

    def test_hash_in_set(self):
        """测试标签可以放入集合。"""
        tag1 = KarmaTag(tag_id="set-1")
        tag2 = KarmaTag(tag_id="set-2")
        tag3 = KarmaTag(tag_id="set-1")
        s = {tag1, tag2, tag3}
        assert len(s) == 2
