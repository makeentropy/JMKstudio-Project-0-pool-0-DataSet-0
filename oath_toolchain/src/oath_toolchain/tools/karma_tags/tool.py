"""Karma数据标签系统主工具模块。

提供Karma数据标签系统的统一入口，集成标签创建、验证、签名、编码、
索引和搜索等功能。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...core.base import OathTool
from ...core.exceptions import ValidationError
from ...core.registry import register_tool
from .karma_tag import KarmaTag, STANDARD_FIELDS
from .tag_index import TagIndex
from .tag_signature import TagSigner


@register_tool
class KarmaTagTool(OathTool):
    """Karma数据标签系统工具。

    提供完整的Karma数据标签管理功能，包括标签创建、验证、签名、
    编解码、索引和搜索等操作。

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
        _index: 标签索引实例
    """

    name: str = "karma_tags"
    description: str = "Karma数据标签系统"
    _version: str = "0.1.0"
    _tags: list[str] = ["data", "tags", "karma", "signature"]
    _category: str = "data"

    def __init__(self) -> None:
        """初始化Karma标签工具。"""
        super().__init__()
        self._index: TagIndex = TagIndex()

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具。

        根据action参数执行不同的Karma标签操作。

        Args:
            params: 输入参数字典，必须包含action字段
                支持的action:
                - create: 创建标签
                - validate: 验证标签
                - sign: 签名标签
                - verify: 验证签名
                - encode_base64: base64编码
                - decode_base64: base64解码
                - to_json: 转JSON
                - from_json: 从JSON加载
                - index_add: 添加到索引
                - index_search: 搜索索引
                - index_stats: 索引统计

        Returns:
            执行结果字典

        Raises:
            ValidationError: 当参数验证失败时
        """
        self.validate_params(params)

        action = params.get("action")

        try:
            if action == "create":
                return self._action_create(params)
            elif action == "validate":
                return self._action_validate(params)
            elif action == "sign":
                return self._action_sign(params)
            elif action == "verify":
                return self._action_verify(params)
            elif action == "encode_base64":
                return self._action_encode_base64(params)
            elif action == "decode_base64":
                return self._action_decode_base64(params)
            elif action == "to_json":
                return self._action_to_json(params)
            elif action == "from_json":
                return self._action_from_json(params)
            elif action == "index_add":
                return self._action_index_add(params)
            elif action == "index_search":
                return self._action_index_search(params)
            elif action == "index_stats":
                return self._action_index_stats(params)
            else:
                raise ValidationError(
                    field="action",
                    message=f"不支持的操作: {action}",
                )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                field="execution",
                message=f"执行失败: {str(e)}",
            ) from e

    def validate_params(self, params: dict[str, Any]) -> bool:
        """验证输入参数。

        Args:
            params: 输入参数字典

        Returns:
            验证通过返回True

        Raises:
            ValidationError: 当参数验证失败时
        """
        if "action" not in params:
            raise ValidationError(
                field="action",
                message="缺少必需的action参数",
            )

        action = params["action"]
        valid_actions = [
            "create",
            "validate",
            "sign",
            "verify",
            "encode_base64",
            "decode_base64",
            "to_json",
            "from_json",
            "index_add",
            "index_search",
            "index_stats",
        ]

        if action not in valid_actions:
            raise ValidationError(
                field="action",
                message=f"不支持的操作: {action}",
            )

        return True

    def _action_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行创建标签操作。"""
        tag_data = {k: v for k, v in params.items() if k != "action"}
        tag = KarmaTag(**tag_data)

        return {
            "success": True,
            "action": "create",
            "tag_id": tag.tag_id,
            "tag": tag.to_dict(),
        }

    def _action_validate(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行验证标签操作。"""
        tag = self._get_tag_from_params(params)
        valid, errors = tag.validate()

        return {
            "success": True,
            "action": "validate",
            "valid": valid,
            "errors": errors,
            "tag_id": tag.tag_id,
        }

    def _action_sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行签名标签操作。"""
        tag = self._get_tag_from_params(params)
        signer_type = params.get("signer", "gpgca")
        private_key_pem = params.get("private_key_pem")
        cert_pem = params.get("cert_pem")
        key_pem = params.get("key_pem")

        if cert_pem and key_pem:
            signer = TagSigner()
            tag = signer.sign_with_cert(tag, cert_pem.encode("utf-8") if isinstance(cert_pem, str) else cert_pem,
                                       key_pem.encode("utf-8") if isinstance(key_pem, str) else key_pem)
        elif private_key_pem:
            private_key_bytes = private_key_pem.encode("utf-8") if isinstance(private_key_pem, str) else private_key_pem
            signer = TagSigner(private_key_pem=private_key_bytes)
            tag = signer.sign_tag(tag, signer=signer_type)
        else:
            raise ValidationError(
                field="private_key_pem",
                message="签名需要private_key_pem参数，或cert_pem和key_pem参数",
            )

        return {
            "success": True,
            "action": "sign",
            "tag_id": tag.tag_id,
            "tag": tag.to_dict(),
            "signer": signer_type,
        }

    def _action_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行验证签名操作。"""
        tag = self._get_tag_from_params(params)
        signer_type = params.get("signer", "gpgca")
        public_key_pem = params.get("public_key_pem")
        cert_pem = params.get("cert_pem")

        if cert_pem:
            signer = TagSigner()
            cert_bytes = cert_pem.encode("utf-8") if isinstance(cert_pem, str) else cert_pem
            valid = signer.verify_with_cert(tag, cert_bytes)
        elif public_key_pem:
            public_key_bytes = public_key_pem.encode("utf-8") if isinstance(public_key_pem, str) else public_key_pem
            signer = TagSigner(public_key_pem=public_key_bytes)
            valid = signer.verify_tag(tag, signer=signer_type)
        else:
            raise ValidationError(
                field="public_key_pem",
                message="验证需要public_key_pem参数，或cert_pem参数",
            )

        return {
            "success": True,
            "action": "verify",
            "valid": valid,
            "tag_id": tag.tag_id,
            "signer": signer_type,
        }

    def _action_encode_base64(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行base64编码操作。"""
        tag = self._get_tag_from_params(params)
        b64_str = tag.to_base64()

        return {
            "success": True,
            "action": "encode_base64",
            "tag_id": tag.tag_id,
            "base64": b64_str,
        }

    def _action_decode_base64(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行base64解码操作。"""
        b64_str = params.get("base64")
        if not b64_str:
            raise ValidationError(
                field="base64",
                message="缺少必需的base64参数",
            )

        tag = KarmaTag.from_base64(b64_str)

        return {
            "success": True,
            "action": "decode_base64",
            "tag_id": tag.tag_id,
            "tag": tag.to_dict(),
        }

    def _action_to_json(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行转JSON操作。"""
        tag = self._get_tag_from_params(params)
        json_str = tag.to_json()

        return {
            "success": True,
            "action": "to_json",
            "tag_id": tag.tag_id,
            "json": json_str,
        }

    def _action_from_json(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行从JSON加载操作。"""
        json_str = params.get("json")
        if not json_str:
            raise ValidationError(
                field="json",
                message="缺少必需的json参数",
            )

        tag = KarmaTag.from_json(json_str)

        return {
            "success": True,
            "action": "from_json",
            "tag_id": tag.tag_id,
            "tag": tag.to_dict(),
        }

    def _action_index_add(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行添加到索引操作。"""
        tag = self._get_tag_from_params(params)
        dataset_id = params.get("dataset_id")

        self._index.add_tag(tag, dataset_id=dataset_id)

        return {
            "success": True,
            "action": "index_add",
            "tag_id": tag.tag_id,
            "index_size": len(self._index),
        }

    def _action_index_search(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行搜索索引操作。"""
        filters = params.get("filters", {})
        results = self._index.search(filters)

        tags_data = []
        for tag, dataset_id in results:
            tags_data.append({
                "tag": tag.to_dict(),
                "dataset_id": dataset_id,
            })

        return {
            "success": True,
            "action": "index_search",
            "count": len(results),
            "results": tags_data,
        }

    def _action_index_stats(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行索引统计操作。"""
        stats = self._index.get_tag_statistics()

        return {
            "success": True,
            "action": "index_stats",
            "statistics": stats,
        }

    def _get_tag_from_params(self, params: dict[str, Any]) -> KarmaTag:
        """从参数中获取标签对象。

        支持从tag字典、base64字符串或json字符串创建标签。

        Args:
            params: 参数字典

        Returns:
            KarmaTag实例

        Raises:
            ValidationError: 当无法创建标签时
        """
        if "tag" in params and isinstance(params["tag"], dict):
            return KarmaTag.from_dict(params["tag"])
        elif "base64" in params and "decode" not in params.get("action", ""):
            return KarmaTag.from_base64(params["base64"])
        elif "json" in params and "from_json" not in params.get("action", ""):
            return KarmaTag.from_json(params["json"])
        else:
            tag_data = {k: v for k, v in params.items() if k in STANDARD_FIELDS}
            return KarmaTag(**tag_data)
