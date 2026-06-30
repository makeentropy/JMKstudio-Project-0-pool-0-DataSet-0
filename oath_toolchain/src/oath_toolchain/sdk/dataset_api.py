"""数据集API模块。

提供数据集池管理的高层API，包括数据集的创建、删除、查询、
更新、版本控制、元数据管理、导入导出等功能。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..tools.dataset_pool.tool import DatasetPoolTool


class DatasetAPI:
    """数据集API类。

    提供完整的数据集池管理功能，包括数据集的创建、删除、查询、
    更新、版本控制、元数据管理、导入导出等操作。

    Attributes:
        engine: 乾坤引擎实例
    """

    def __init__(self, engine: Any) -> None:
        """初始化数据集API。

        Args:
            engine: 乾坤引擎实例
        """
        self._engine = engine
        self._dataset_tool = None
        self._ensure_tool()

    def _ensure_tool(self) -> None:
        """确保数据集工具已初始化。"""
        try:
            self._dataset_tool = self._engine.get_tool("dataset_pool")
        except Exception:
            self._dataset_tool = DatasetPoolTool()
            try:
                self._engine.register_tool(self._dataset_tool)
            except Exception:
                pass

    def create(
        self,
        name: str,
        data: Any = None,
        format: str = 'json',
    ) -> Dict[str, Any]:
        """创建数据集。

        Args:
            name: 数据集名称
            data: 数据集内容，可选
            format: 数据格式，默认为'json'

        Returns:
            数据集信息字典，包含：
                - success: 是否成功
                - dataset_id: 数据集ID
                - dataset: 数据集完整信息
        """
        result = self._dataset_tool.execute({
            "action": "create",
            "name": name,
            "data": data,
            "format": format,
        })
        return result

    def delete(self, dataset_id: str) -> bool:
        """删除数据集。

        Args:
            dataset_id: 数据集ID

        Returns:
            删除成功返回True，否则返回False
        """
        result = self._dataset_tool.execute({
            "action": "delete",
            "dataset_id": dataset_id,
        })
        return result.get("success", False)

    def get(self, dataset_id: str) -> Dict[str, Any]:
        """获取数据集信息。

        Args:
            dataset_id: 数据集ID

        Returns:
            数据集信息字典

        Raises:
            ValidationError: 当数据集不存在时
        """
        result = self._dataset_tool.execute({
            "action": "get",
            "dataset_id": dataset_id,
        })
        return result

    def update(
        self,
        dataset_id: str,
        data: Any = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """更新数据集。

        Args:
            dataset_id: 数据集ID
            data: 新的数据内容，可选
            metadata: 新的元数据，可选

        Returns:
            更新后的数据集信息字典
        """
        params = {
            "action": "update",
            "dataset_id": dataset_id,
        }
        if data is not None:
            params["data"] = data
        if metadata is not None:
            params["metadata"] = metadata

        result = self._dataset_tool.execute(params)
        return result

    def list_datasets(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """列出数据集。

        Args:
            filters: 过滤条件字典，可选

        Returns:
            数据集列表
        """
        params = {"action": "list"}
        if filters is not None:
            params["filters"] = filters

        result = self._dataset_tool.execute(params)
        return result.get("datasets", [])

    def search_by_tags(self, tag_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按标签搜索数据集。

        Args:
            tag_filters: 标签过滤条件字典

        Returns:
            匹配的数据集列表
        """
        result = self._dataset_tool.execute({
            "action": "search_tags",
            "tag_filters": tag_filters,
        })
        return result.get("datasets", [])

    def add_tag(self, dataset_id: str, tag: Dict[str, Any]) -> bool:
        """添加标签到数据集。

        Args:
            dataset_id: 数据集ID
            tag: 标签字典

        Returns:
            添加成功返回True，否则返回False
        """
        tags = self._get_dataset_tags(dataset_id)
        tag["tag_id"] = tag.get("tag_id", f"tag_{len(tags)}")
        tags.append(tag)
        return self._set_dataset_tags(dataset_id, tags)

    def remove_tag(self, dataset_id: str, tag_id: str) -> bool:
        """从数据集移除标签。

        Args:
            dataset_id: 数据集ID
            tag_id: 标签ID

        Returns:
            移除成功返回True，否则返回False
        """
        tags = self._get_dataset_tags(dataset_id)
        tags = [t for t in tags if t.get("tag_id") != tag_id]
        return self._set_dataset_tags(dataset_id, tags)

    def commit_version(
        self,
        dataset_id: str,
        message: str = None,
    ) -> str:
        """提交数据集版本。

        Args:
            dataset_id: 数据集ID
            message: 版本消息，可选

        Returns:
            版本号
        """
        result = self._dataset_tool.execute({
            "action": "commit",
            "dataset_id": dataset_id,
            "message": message,
        })
        return result.get("version", "")

    def list_versions(self, dataset_id: str) -> List[Dict[str, Any]]:
        """列出数据集的所有版本。

        Args:
            dataset_id: 数据集ID

        Returns:
            版本列表
        """
        result = self._dataset_tool.execute({
            "action": "versions",
            "dataset_id": dataset_id,
        })
        return result.get("versions", [])

    def revert_version(
        self,
        dataset_id: str,
        version: str,
    ) -> Dict[str, Any]:
        """回滚到指定版本。

        Args:
            dataset_id: 数据集ID
            version: 目标版本号

        Returns:
            回滚后的数据集信息字典
        """
        result = self._dataset_tool.execute({
            "action": "revert",
            "dataset_id": dataset_id,
            "version": version,
        })
        return result

    def export_dataset(
        self,
        dataset_id: str,
        filepath: str,
        format: str = None,
    ) -> str:
        """导出数据集。

        Args:
            dataset_id: 数据集ID
            filepath: 导出文件路径
            format: 导出格式，可选

        Returns:
            导出文件路径
        """
        result = self._dataset_tool.execute({
            "action": "export",
            "dataset_id": dataset_id,
            "filepath": filepath,
            "format": format,
        })
        return result.get("export_path", filepath)

    def _get_dataset_tags(self, dataset_id: str) -> List[Dict[str, Any]]:
        """获取数据集标签列表。

        Args:
            dataset_id: 数据集ID

        Returns:
            标签列表
        """
        result = self._dataset_tool.execute({
            "action": "get_meta",
            "dataset_id": dataset_id,
            "key": "tags",
        })
        return result.get("metadata", []) or []

    def _set_dataset_tags(
        self,
        dataset_id: str,
        tags: List[Dict[str, Any]],
    ) -> bool:
        """设置数据集标签。

        Args:
            dataset_id: 数据集ID
            tags: 标签列表

        Returns:
            设置成功返回True
        """
        result = self._dataset_tool.execute({
            "action": "set_meta",
            "dataset_id": dataset_id,
            "key": "tags",
            "value": tags,
        })
        return result.get("success", False)
