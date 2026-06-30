"""Karma标签数据结构模块。

定义Karma数据标签的核心数据结构，支持标准字段和自定义字段的存储、
序列化、反序列化和验证功能。
"""
from __future__ import annotations

import base64
import json
import re
import uuid
from typing import Any, List, Tuple


STANDARD_FIELDS = [
    "datafor",
    "datefor",
    "datatag",
    "base64",
    "tag",
    "gpgca",
    "jmkca",
    "encrypt_xor",
    "stego_dim",
    "dict_ca",
    "tag_id",
]


class KarmaTag:
    """Karma数据标签类。

    用于描述和标记数据的元数据标签，支持多种标准字段和自定义字段扩展。
    标签可以序列化为字典、JSON或base64格式，也可以从这些格式反序列化。

    Attributes:
        datafor: 数据用途描述
        datefor: 数据日期（YYYYMMDD格式）
        datatag: 数据标签列表
        base64: base64编码的数据内容
        tag: 通用标签列表
        gpgca: GPG CA签名
        jmkca: JMK CA签名
        encrypt_xor: 是否使用XOR加密
        stego_dim: 隐写维度
        dict_ca: 字典CA标识
        tag_id: 标签唯一标识
        _custom_fields: 自定义字段字典
    """

    def __init__(self, **kwargs: Any) -> None:
        """初始化Karma标签。

        Args:
            **kwargs: 标签字段键值对。支持标准字段和自定义字段。
        """
        self.datafor: str = kwargs.get("datafor", "")
        self.datefor: str = kwargs.get("datefor", "")
        self.datatag: List[str] = kwargs.get("datatag", [])
        self.base64: str = kwargs.get("base64", "")
        self.tag: List[str] = kwargs.get("tag", [])
        self.gpgca: str = kwargs.get("gpgca", "")
        self.jmkca: str = kwargs.get("jmkca", "")
        self.encrypt_xor: bool = kwargs.get("encrypt_xor", False)
        self.stego_dim: int = kwargs.get("stego_dim", 0)
        self.dict_ca: str = kwargs.get("dict_ca", "")
        self.tag_id: str = kwargs.get("tag_id", str(uuid.uuid4()))

        self._custom_fields: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key not in STANDARD_FIELDS:
                self._custom_fields[key] = value

    def to_dict(self) -> dict[str, Any]:
        """将标签序列化为字典。

        Returns:
            包含所有标签字段的字典，包括标准字段和自定义字段。
        """
        result: dict[str, Any] = {
            "datafor": self.datafor,
            "datefor": self.datefor,
            "datatag": list(self.datatag),
            "base64": self.base64,
            "tag": list(self.tag),
            "gpgca": self.gpgca,
            "jmkca": self.jmkca,
            "encrypt_xor": self.encrypt_xor,
            "stego_dim": self.stego_dim,
            "dict_ca": self.dict_ca,
            "tag_id": self.tag_id,
        }
        result.update(self._custom_fields)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KarmaTag":
        """从字典创建Karma标签。

        Args:
            data: 包含标签字段的字典

        Returns:
            创建的KarmaTag实例
        """
        return cls(**data)

    def to_base64(self) -> str:
        """将标签序列化为base64字符串。

        先将标签转换为JSON，然后进行base64编码。

        Returns:
            base64编码的标签字符串
        """
        json_str = self.to_json()
        json_bytes = json_str.encode("utf-8")
        return base64.b64encode(json_bytes).decode("utf-8")

    @classmethod
    def from_base64(cls, b64_str: str) -> "KarmaTag":
        """从base64字符串创建Karma标签。

        Args:
            b64_str: base64编码的标签字符串

        Returns:
            创建的KarmaTag实例

        Raises:
            ValueError: 当base64字符串无效或JSON解析失败时
        """
        try:
            json_bytes = base64.b64decode(b64_str)
            json_str = json_bytes.decode("utf-8")
            return cls.from_json(json_str)
        except (base64.binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"无效的base64标签数据: {e}") from e

    def to_json(self) -> str:
        """将标签序列化为JSON字符串。

        Returns:
            JSON格式的标签字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "KarmaTag":
        """从JSON字符串创建Karma标签。

        Args:
            json_str: JSON格式的标签字符串

        Returns:
            创建的KarmaTag实例

        Raises:
            ValueError: 当JSON解析失败时
        """
        try:
            data = json.loads(json_str)
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON标签数据: {e}") from e

    def get_custom_field(self, key: str) -> Any:
        """获取自定义字段的值。

        Args:
            key: 自定义字段名

        Returns:
            字段值，如果字段不存在则返回None
        """
        return self._custom_fields.get(key)

    def set_custom_field(self, key: str, value: Any) -> None:
        """设置自定义字段的值。

        Args:
            key: 自定义字段名
            value: 字段值
        """
        if key in STANDARD_FIELDS:
            setattr(self, key, value)
        else:
            self._custom_fields[key] = value

    def validate(self) -> Tuple[bool, List[str]]:
        """验证标签的完整性和有效性。

        检查标准字段的格式和必填项。

        Returns:
            (验证是否通过, 错误信息列表) 元组
        """
        errors: List[str] = []

        if not self.datafor:
            errors.append("datafor字段不能为空")

        if self.datefor:
            if not re.match(r"^\d{8}$", self.datefor):
                errors.append("datefor字段必须是YYYYMMDD格式的8位数字")
        else:
            errors.append("datefor字段不能为空")

        if not isinstance(self.datatag, list):
            errors.append("datatag字段必须是列表类型")
        else:
            for i, item in enumerate(self.datatag):
                if not isinstance(item, str):
                    errors.append(f"datatag[{i}]必须是字符串类型")

        if not isinstance(self.tag, list):
            errors.append("tag字段必须是列表类型")
        else:
            for i, item in enumerate(self.tag):
                if not isinstance(item, str):
                    errors.append(f"tag[{i}]必须是字符串类型")

        if not isinstance(self.encrypt_xor, bool):
            errors.append("encrypt_xor字段必须是布尔类型")

        if not isinstance(self.stego_dim, int):
            errors.append("stego_dim字段必须是整数类型")
        elif self.stego_dim < 0:
            errors.append("stego_dim字段不能为负数")

        if self.base64:
            try:
                base64.b64decode(self.base64)
            except Exception:
                errors.append("base64字段包含无效的base64数据")

        if not self.tag_id:
            errors.append("tag_id字段不能为空")

        return len(errors) == 0, errors

    def get_data_for_signing(self) -> bytes:
        """获取用于签名的数据（排除签名字段）。

        将标签数据（排除所有签名字段）序列化为JSON并编码为字节。

        Returns:
            用于签名的字节数据
        """
        data = self.to_dict()
        data.pop("gpgca", None)
        data.pop("jmkca", None)
        data.pop("custom_signature", None)
        data.pop("signer_cert", None)
        return json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")

    def __repr__(self) -> str:
        """返回标签的字符串表示。"""
        return f"<KarmaTag id='{self.tag_id}' datafor='{self.datafor}' datefor='{self.datefor}'>"

    def __str__(self) -> str:
        """返回标签的可读字符串。"""
        return f"KarmaTag[{self.tag_id}]: {self.datafor} ({self.datefor})"

    def __eq__(self, other: object) -> bool:
        """判断两个标签是否相等。

        基于tag_id进行比较。
        """
        if not isinstance(other, KarmaTag):
            return NotImplemented
        return self.tag_id == other.tag_id

    def __hash__(self) -> int:
        """返回标签的哈希值。

        基于tag_id计算哈希。
        """
        return hash(self.tag_id)
