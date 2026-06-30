"""数据集池主工具模块。

提供Dataset Pool数据集池管理工具的统一入口，集成数据集管理、
版本控制、元数据管理等功能。
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional

from ...core.base import OathTool
from ...core.exceptions import ValidationError
from ...core.registry import register_tool
from .dataset import Dataset
from .pool_manager import DatasetPoolManager
from .version_control import DatasetVersionControl
from .metadata_manager import MetadataManager


@register_tool
class DatasetPoolTool(OathTool):
    """Dataset Pool数据集池管理工具。

    提供完整的数据集池管理功能，包括数据集的创建、删除、查询、
    更新、版本控制、元数据管理、导入导出等操作。

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
        _pool_manager: 数据集池管理器
        _version_control: 版本控制器
        _metadata_manager: 元数据管理器
    """

    name: str = "dataset_pool"
    description: str = "Dataset Pool数据集池管理工具"
    _version: str = "0.1.0"
    _tags: list[str] = ["data", "dataset", "pool", "versioning"]
    _category: str = "data"

    def __init__(self, pool_path: Optional[str] = None) -> None:
        """初始化数据集池工具。

        Args:
            pool_path: 数据集池存储路径
        """
        super().__init__()
        self._pool_manager: DatasetPoolManager = DatasetPoolManager(pool_path)
        self._version_control: DatasetVersionControl = DatasetVersionControl(self._pool_manager)
        self._metadata_manager: MetadataManager = MetadataManager(self._pool_manager)

    @property
    def pool_manager(self) -> DatasetPoolManager:
        """获取数据集池管理器。

        Returns:
            数据集池管理器实例
        """
        return self._pool_manager

    @property
    def version_control(self) -> DatasetVersionControl:
        """获取版本控制器。

        Returns:
            版本控制器实例
        """
        return self._version_control

    @property
    def metadata_manager(self) -> MetadataManager:
        """获取元数据管理器。

        Returns:
            元数据管理器实例
        """
        return self._metadata_manager

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具。

        根据action参数执行不同的数据集池操作。

        Args:
            params: 输入参数字典，必须包含action字段
                支持的action:
                - create: 创建数据集
                - delete: 删除数据集
                - get: 获取数据集
                - update: 更新数据集
                - list: 列出数据集
                - search_tags: 按标签搜索
                - import: 导入数据集
                - export: 导出数据集
                - stats: 池统计
                - commit: 提交版本
                - versions: 版本列表
                - revert: 版本回滚
                - set_meta: 设置元数据
                - get_meta: 获取元数据

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
            elif action == "delete":
                return self._action_delete(params)
            elif action == "get":
                return self._action_get(params)
            elif action == "update":
                return self._action_update(params)
            elif action == "list":
                return self._action_list(params)
            elif action == "search_tags":
                return self._action_search_tags(params)
            elif action == "import":
                return self._action_import(params)
            elif action == "export":
                return self._action_export(params)
            elif action == "stats":
                return self._action_stats(params)
            elif action == "commit":
                return self._action_commit(params)
            elif action == "versions":
                return self._action_versions(params)
            elif action == "revert":
                return self._action_revert(params)
            elif action == "set_meta":
                return self._action_set_meta(params)
            elif action == "get_meta":
                return self._action_get_meta(params)
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
            "delete",
            "get",
            "update",
            "list",
            "search_tags",
            "import",
            "export",
            "stats",
            "commit",
            "versions",
            "revert",
            "set_meta",
            "get_meta",
        ]

        if action not in valid_actions:
            raise ValidationError(
                field="action",
                message=f"不支持的操作: {action}",
            )

        return True

    def _action_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行创建数据集操作。"""
        name = params.get("name", "")
        data = params.get("data")
        format = params.get("format", "json")
        description = params.get("description")

        dataset = self._pool_manager.create_dataset(
            name=name,
            data=data,
            format=format,
            description=description,
        )

        return {
            "success": True,
            "action": "create",
            "dataset_id": dataset.dataset_id,
            "dataset": dataset.to_dict(),
        }

    def _action_delete(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行删除数据集操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        result = self._pool_manager.delete_dataset(dataset_id)

        return {
            "success": result,
            "action": "delete",
            "dataset_id": dataset_id,
        }

    def _action_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行获取数据集操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        dataset = self._pool_manager.get_dataset(dataset_id)
        if dataset is None:
            raise ValidationError(
                field="dataset_id",
                message=f"数据集不存在: {dataset_id}",
            )

        return {
            "success": True,
            "action": "get",
            "dataset_id": dataset_id,
            "dataset": dataset.to_dict(),
        }

    def _action_update(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行更新数据集操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        data = params.get("data")
        metadata = params.get("metadata")

        dataset = self._pool_manager.update_dataset(
            dataset_id=dataset_id,
            data=data,
            metadata=metadata,
        )

        if dataset is None:
            raise ValidationError(
                field="dataset_id",
                message=f"数据集不存在: {dataset_id}",
            )

        return {
            "success": True,
            "action": "update",
            "dataset_id": dataset_id,
            "dataset": dataset.to_dict(),
        }

    def _action_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行列出数据集操作。"""
        filters = params.get("filters")
        limit = params.get("limit", 100)
        offset = params.get("offset", 0)

        datasets = self._pool_manager.list_datasets(
            filters=filters,
            limit=limit,
            offset=offset,
        )

        datasets_data = [ds.to_dict() for ds in datasets]

        return {
            "success": True,
            "action": "list",
            "count": len(datasets_data),
            "datasets": datasets_data,
        }

    def _action_search_tags(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行按标签搜索操作。"""
        tag_filters = params.get("tag_filters", {})

        datasets = self._pool_manager.search_by_tags(tag_filters)
        datasets_data = [ds.to_dict() for ds in datasets]

        return {
            "success": True,
            "action": "search_tags",
            "count": len(datasets_data),
            "datasets": datasets_data,
        }

    def _action_import(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行导入数据集操作。"""
        filepath = params.get("filepath")
        if not filepath:
            raise ValidationError(
                field="filepath",
                message="缺少必需的filepath参数",
            )

        format = params.get("format")

        dataset = self._pool_manager.import_dataset(
            filepath=filepath,
            format=format,
        )

        return {
            "success": True,
            "action": "import",
            "dataset_id": dataset.dataset_id,
            "dataset": dataset.to_dict(),
        }

    def _action_export(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行导出数据集操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        filepath = params.get("filepath")
        if not filepath:
            raise ValidationError(
                field="filepath",
                message="缺少必需的filepath参数",
            )

        format = params.get("format")

        export_path = self._pool_manager.export_dataset(
            dataset_id=dataset_id,
            filepath=filepath,
            format=format,
        )

        return {
            "success": True,
            "action": "export",
            "dataset_id": dataset_id,
            "export_path": export_path,
        }

    def _action_stats(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行池统计操作。"""
        stats = self._pool_manager.get_pool_stats()
        storage = self._pool_manager.get_storage_usage()

        return {
            "success": True,
            "action": "stats",
            "pool_stats": stats,
            "storage_usage": storage,
        }

    def _action_commit(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行提交版本操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        message = params.get("message")

        version = self._version_control.commit_version(
            dataset_id=dataset_id,
            message=message,
        )

        return {
            "success": True,
            "action": "commit",
            "dataset_id": dataset_id,
            "version": version,
        }

    def _action_versions(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行版本列表操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        versions = self._version_control.list_versions(dataset_id)

        return {
            "success": True,
            "action": "versions",
            "dataset_id": dataset_id,
            "versions": versions,
            "count": len(versions),
        }

    def _action_revert(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行版本回滚操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        version = params.get("version")
        if not version:
            raise ValidationError(
                field="version",
                message="缺少必需的version参数",
            )

        dataset = self._version_control.revert_to_version(
            dataset_id=dataset_id,
            version=version,
        )

        if dataset is None:
            raise ValidationError(
                field="version",
                message=f"版本不存在: {version}",
            )

        return {
            "success": True,
            "action": "revert",
            "dataset_id": dataset_id,
            "version": version,
            "dataset": dataset.to_dict(),
        }

    def _action_set_meta(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行设置元数据操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        key = params.get("key")
        value = params.get("value")

        if key is None:
            raise ValidationError(
                field="key",
                message="缺少必需的key参数",
            )

        result = self._metadata_manager.set_metadata(
            dataset_id=dataset_id,
            key=key,
            value=value,
        )

        if not result:
            raise ValidationError(
                field="dataset_id",
                message=f"数据集不存在: {dataset_id}",
            )

        return {
            "success": True,
            "action": "set_meta",
            "dataset_id": dataset_id,
            "key": key,
            "value": value,
        }

    def _action_get_meta(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行获取元数据操作。"""
        dataset_id = params.get("dataset_id")
        if not dataset_id:
            raise ValidationError(
                field="dataset_id",
                message="缺少必需的dataset_id参数",
            )

        key = params.get("key")

        metadata = self._metadata_manager.get_metadata(
            dataset_id=dataset_id,
            key=key,
        )

        if metadata is None and key is not None:
            dataset = self._pool_manager.get_dataset(dataset_id)
            if dataset is None:
                raise ValidationError(
                    field="dataset_id",
                    message=f"数据集不存在: {dataset_id}",
                )

        return {
            "success": True,
            "action": "get_meta",
            "dataset_id": dataset_id,
            "key": key,
            "metadata": metadata,
        }
