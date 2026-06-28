"""
数据集元数据管理系统模块

实现数据集元数据的追踪和管理：
- 数据集版本追踪
- 变更历史记录
- 元数据查询和搜索
- 数据集生命周期管理
- 元数据导出和导入
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dataset.schema import (
    DatasetMetadata,
    DatasetVersion,
    DataQuality,
    DatasetFormat,
    DatasetType,
    DataType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ChangeType(str):
    """变更类型"""

    CREATE = "create"  # 创建
    UPDATE = "update"  # 更新
    DELETE = "delete"  # 删除
    VERSION = "version"  # 版本变更
    QUALITY = "quality"  # 质量变更
    SCHEMA = "schema"  # 模式变更
    MERGE = "merge"  # 合并
    SPLIT = "split"  # 分割


class ChangeRecord(BaseModel):
    """变更记录"""

    change_id: str = Field(..., description="变更ID")
    dataset_id: str = Field(..., description="数据集ID")
    change_type: str = Field(..., description="变更类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

    # 变更详情
    description: str = Field(default="", description="变更描述")
    changes: Dict[str, Any] = Field(default_factory=dict, description="变更内容")
    before_state: Dict[str, Any] = Field(default_factory=dict, description="变更前状态")
    after_state: Dict[str, Any] = Field(default_factory=dict, description="变更后状态")

    # 版本信息
    version_before: Optional[str] = Field(default=None, description="变更前版本")
    version_after: Optional[str] = Field(default=None, description="变更后版本")

    # 操作者信息
    operator: str = Field(default="system", description="操作者")
    operation_source: str = Field(default="manual", description="操作来源")

    # 相关信息
    related_changes: List[str] = Field(default_factory=list, description="相关变更ID")
    notes: str = Field(default="", description="备注")


class MetadataSearchQuery(BaseModel):
    """元数据搜索查询"""

    query_text: Optional[str] = Field(default=None, description="搜索文本")
    dataset_ids: Optional[List[str]] = Field(default=None, description="数据集ID列表")
    names: Optional[List[str]] = Field(default=None, description="名称列表")
    types: Optional[List[str]] = Field(default=None, description="类型列表")
    data_types: Optional[List[str]] = Field(default=None, description="数据类型列表")
    formats: Optional[List[str]] = Field(default=None, description="格式列表")
    quality_levels: Optional[List[str]] = Field(default=None, description="质量等级列表")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    sources: Optional[List[str]] = Field(default=None, description="来源列表")
    owners: Optional[List[str]] = Field(default=None, description="所有者列表")
    created_after: Optional[datetime] = Field(default=None, description="创建时间之后")
    created_before: Optional[datetime] = Field(default=None, description="创建时间之前")
    updated_after: Optional[datetime] = Field(default=None, description="更新时间之后")
    updated_before: Optional[datetime] = Field(default=None, description="更新时间之前")
    min_records: Optional[int] = Field(default=None, description="最小记录数")
    max_records: Optional[int] = Field(default=None, description="最大记录数")
    is_public: Optional[bool] = Field(default=None, description="是否公开")
    has_expired: Optional[bool] = Field(default=None, description="是否已过期")
    sort_by: Optional[str] = Field(default="updated_at", description="排序字段")
    sort_order: Optional[str] = Field(default="desc", description="排序方向")
    limit: Optional[int] = Field(default=100, description="结果数量限制")
    offset: Optional[int] = Field(default=0, description="偏移量")


class MetadataSearchResult(BaseModel):
    """元数据搜索结果"""

    query: MetadataSearchQuery = Field(..., description="查询")
    results: List[DatasetMetadata] = Field(default_factory=list, description="结果列表")
    total_count: int = Field(default=0, description="总数")
    page_size: int = Field(default=100, description="页面大小")
    page_number: int = Field(default=1, description="页码")
    execution_time: float = Field(default=0.0, description="执行时间")


class MetadataStore:
    """元数据存储"""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        初始化元数据存储

        Args:
            storage_path: 存储路径
        """
        self.storage_path = storage_path or Path("data/metadata")
        self.metadata_index: Dict[str, DatasetMetadata] = {}
        self.version_index: Dict[str, List[DatasetVersion]] = {}
        self.change_history: Dict[str, List[ChangeRecord]] = {}

        self._ensure_storage_path()
        self._load_from_storage()

    def _ensure_storage_path(self) -> None:
        """确保存储路径存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _load_from_storage(self) -> None:
        """从存储加载数据"""
        # 加载元数据索引
        metadata_file = self.storage_path / "metadata_index.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    self.metadata_index[item["id"]] = DatasetMetadata(**item)
                logger.info(f"加载了 {len(self.metadata_index)} 条元数据")
            except Exception as e:
                logger.error(f"加载元数据失败: {e}")

        # 加载版本索引
        version_file = self.storage_path / "version_index.json"
        if version_file.exists():
            try:
                with open(version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for dataset_id, versions in data.items():
                    self.version_index[dataset_id] = [DatasetVersion(**v) for v in versions]
            except Exception as e:
                logger.error(f"加载版本索引失败: {e}")

        # 加载变更历史
        history_file = self.storage_path / "change_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for dataset_id, changes in data.items():
                    self.change_history[dataset_id] = [ChangeRecord(**c) for c in changes]
            except Exception as e:
                logger.error(f"加载变更历史失败: {e}")

    def _save_to_storage(self) -> None:
        """保存数据到存储"""
        # 保存元数据索引
        metadata_file = self.storage_path / "metadata_index.json"
        try:
            data = [m.model_dump() for m in self.metadata_index.values()]
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")

        # 保存版本索引
        version_file = self.storage_path / "version_index.json"
        try:
            data = {}
            for dataset_id, versions in self.version_index.items():
                data[dataset_id] = [v.model_dump() for v in versions]
            with open(version_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存版本索引失败: {e}")

        # 保存变更历史
        history_file = self.storage_path / "change_history.json"
        try:
            data = {}
            for dataset_id, changes in self.change_history.items():
                data[dataset_id] = [c.model_dump() for c in changes]
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存变更历史失败: {e}")

    def save_metadata(self, metadata: DatasetMetadata) -> None:
        """
        保存元数据

        Args:
            metadata: 数据集元数据
        """
        self.metadata_index[metadata.id] = metadata
        self._save_to_storage()
        logger.info(f"保存元数据: {metadata.id}")

    def get_metadata(self, dataset_id: str) -> Optional[DatasetMetadata]:
        """
        获取元数据

        Args:
            dataset_id: 数据集ID

        Returns:
            数据集元数据
        """
        return self.metadata_index.get(dataset_id)

    def delete_metadata(self, dataset_id: str) -> bool:
        """
        删除元数据

        Args:
            dataset_id: 数据集ID

        Returns:
            是否成功删除
        """
        if dataset_id in self.metadata_index:
            del self.metadata_index[dataset_id]
            self._save_to_storage()
            logger.info(f"删除元数据: {dataset_id}")
            return True
        return False

    def list_metadata(self) -> List[DatasetMetadata]:
        """列出所有元数据"""
        return list(self.metadata_index.values())

    def add_version(self, dataset_id: str, version: DatasetVersion) -> None:
        """
        添加版本

        Args:
            dataset_id: 数据集ID
            version: 版本信息
        """
        if dataset_id not in self.version_index:
            self.version_index[dataset_id] = []
        self.version_index[dataset_id].append(version)
        self._save_to_storage()
        logger.info(f"添加版本: {dataset_id} -> {version.version}")

    def get_versions(self, dataset_id: str) -> List[DatasetVersion]:
        """
        获取版本列表

        Args:
            dataset_id: 数据集ID

        Returns:
            版本列表
        """
        return self.version_index.get(dataset_id, [])

    def get_version(self, dataset_id: str, version: str) -> Optional[DatasetVersion]:
        """
        获取指定版本

        Args:
            dataset_id: 数据集ID
            version: 版本号

        Returns:
            版本信息
        """
        versions = self.get_versions(dataset_id)
        for v in versions:
            if v.version == version:
                return v
        return None

    def record_change(self, change: ChangeRecord) -> None:
        """
        记录变更

        Args:
            change: 变更记录
        """
        if change.dataset_id not in self.change_history:
            self.change_history[change.dataset_id] = []
        self.change_history[change.dataset_id].append(change)
        self._save_to_storage()
        logger.info(f"记录变更: {change.change_id}")

    def get_changes(self, dataset_id: str) -> List[ChangeRecord]:
        """
        获取变更历史

        Args:
            dataset_id: 数据集ID

        Returns:
            变更记录列表
        """
        return self.change_history.get(dataset_id, [])

    def search(self, query: MetadataSearchQuery) -> MetadataSearchResult:
        """
        搜索元数据

        Args:
            query: 搜索查询

        Returns:
            搜索结果
        """
        start_time = datetime.now()

        # 筛选结果
        results = []
        for metadata in self.metadata_index.values():
            if self._matches_query(metadata, query):
                results.append(metadata)

        # 排序
        if query.sort_by:
            reverse = query.sort_order == "desc"
            sort_key = lambda m: getattr(m, query.sort_by, datetime.min)
            results.sort(key=sort_key, reverse=reverse)

        # 分页
        total_count = len(results)
        offset = query.offset or 0
        limit = query.limit or 100
        results = results[offset:offset + limit]

        execution_time = (datetime.now() - start_time).total_seconds()

        return MetadataSearchResult(
            query=query,
            results=results,
            total_count=total_count,
            page_size=limit,
            page_number=(offset // limit) + 1,
            execution_time=execution_time,
        )

    def _matches_query(self, metadata: DatasetMetadata, query: MetadataSearchQuery) -> bool:
        """检查元数据是否匹配查询"""
        # 文本搜索
        if query.query_text:
            search_text = query.query_text.lower()
            if not (
                search_text in metadata.name.lower() or
                search_text in metadata.description.lower() or
                any(search_text in tag.lower() for tag in metadata.tags)
            ):
                return False

        # ID筛选
        if query.dataset_ids and metadata.id not in query.dataset_ids:
            return False

        # 名称筛选
        if query.names and metadata.name not in query.names:
            return False

        # 类型筛选
        if query.types and metadata.dataset_type not in query.types:
            return False

        # 数据类型筛选
        if query.data_types and metadata.data_type not in query.data_types:
            return False

        # 格式筛选
        if query.formats and metadata.format not in query.formats:
            return False

        # 质量等级筛选
        if query.quality_levels and metadata.quality not in query.quality_levels:
            return False

        # 标签筛选
        if query.tags and not any(tag in metadata.tags for tag in query.tags):
            return False

        # 来源筛选
        if query.sources and metadata.source not in query.sources:
            return False

        # 所有者筛选
        if query.owners and metadata.owner not in query.owners:
            return False

        # 时间筛选
        if query.created_after and metadata.created_at < query.created_after:
            return False
        if query.created_before and metadata.created_at > query.created_before:
            return False
        if query.updated_after and metadata.updated_at < query.updated_after:
            return False
        if query.updated_before and metadata.updated_at > query.updated_before:
            return False

        # 记录数筛选
        if query.min_records and metadata.total_records < query.min_records:
            return False
        if query.max_records and metadata.total_records > query.max_records:
            return False

        # 公开状态筛选
        if query.is_public is not None and metadata.is_public != query.is_public:
            return False

        # 过期状态筛选
        if query.has_expired is not None:
            if query.has_expired:
                if metadata.expires_at is None or metadata.expires_at > datetime.now():
                    return False
            else:
                if metadata.expires_at is not None and metadata.expires_at <= datetime.now():
                    return False

        return True


class MetadataManager:
    """元数据管理器"""

    def __init__(self, store: Optional[MetadataStore] = None):
        """
        初始化元数据管理器

        Args:
            store: 元数据存储
        """
        self.store = store or MetadataStore()

    def register_dataset(
        self,
        name: str,
        description: str = "",
        dataset_type: str = DatasetType.TRAINING,
        data_type: str = DataType.TEXT,
        format: str = DatasetFormat.PARQUET,
        source: str = "",
        tags: Optional[List[str]] = None,
        owner: str = "system",
        **kwargs,
    ) -> DatasetMetadata:
        """
        注册数据集

        Args:
            name: 数据集名称
            description: 描述
            dataset_type: 数据集类型
            data_type: 数据类型
            format: 数据格式
            source: 来源
            tags: 标签
            owner: 所有者
            **kwargs: 其他参数

        Returns:
            数据集元数据
        """
        # 生成ID
        dataset_id = self._generate_dataset_id(name)

        # 创建元数据
        metadata = DatasetMetadata(
            id=dataset_id,
            name=name,
            description=description,
            version="1.0.0",
            dataset_type=dataset_type,
            data_type=data_type,
            format=format,
            quality=DataQuality.RAW,
            source=source,
            tags=tags or [],
            owner=owner,
            **kwargs,
        )

        # 保存元数据
        self.store.save_metadata(metadata)

        # 记录变更
        change = ChangeRecord(
            change_id=self._generate_change_id(dataset_id),
            dataset_id=dataset_id,
            change_type=ChangeType.CREATE,
            description=f"创建数据集 {name}",
            after_state=metadata.model_dump(),
            version_after=metadata.version,
        )
        self.store.record_change(change)

        logger.info(f"注册数据集: {dataset_id}")
        return metadata

    def update_metadata(
        self,
        dataset_id: str,
        updates: Dict[str, Any],
        operator: str = "system",
        description: str = "",
    ) -> Optional[DatasetMetadata]:
        """
        更新元数据

        Args:
            dataset_id: 数据集ID
            updates: 更新内容
            operator: 操作者
            description: 更新描述

        Returns:
            更新后的元数据
        """
        metadata = self.store.get_metadata(dataset_id)
        if metadata is None:
            logger.error(f"数据集 '{dataset_id}' 不存在")
            return None

        # 记录变更前状态
        before_state = metadata.model_dump()

        # 应用更新
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

        metadata.updated_at = datetime.now()

        # 保存更新
        self.store.save_metadata(metadata)

        # 记录变更
        change = ChangeRecord(
            change_id=self._generate_change_id(dataset_id),
            dataset_id=dataset_id,
            change_type=ChangeType.UPDATE,
            description=description or f"更新数据集 {dataset_id}",
            before_state=before_state,
            after_state=metadata.model_dump(),
            changes=updates,
            operator=operator,
        )
        self.store.record_change(change)

        logger.info(f"更新数据集元数据: {dataset_id}")
        return metadata

    def create_version(
        self,
        dataset_id: str,
        description: str = "",
        changes: Optional[List[str]] = None,
        file_path: Optional[Path] = None,
        checksum: str = "",
        operator: str = "system",
    ) -> Optional[DatasetVersion]:
        """
        创建新版本

        Args:
            dataset_id: 数据集ID
            description: 版本描述
            changes: 变更列表
            file_path: 文件路径
            checksum: 校验和
            operator: 操作者

        Returns:
            版本信息
        """
        metadata = self.store.get_metadata(dataset_id)
        if metadata is None:
            logger.error(f"数据集 '{dataset_id}' 不存在")
            return None

        # 生成新版本号
        versions = self.store.get_versions(dataset_id)
        if versions:
            last_version = versions[-1].version
            new_version = self._increment_version(last_version)
        else:
            new_version = "1.0.0"

        # 创建版本记录
        version = DatasetVersion(
            version=new_version,
            description=description,
            changes=changes or [],
            parent_version=metadata.version,
            checksum=checksum,
            file_path=file_path or Path(""),
            created_by=operator,
        )

        # 保存版本
        self.store.add_version(dataset_id, version)

        # 更新元数据版本
        metadata.version = new_version
        metadata.updated_at = datetime.now()
        self.store.save_metadata(metadata)

        # 记录变更
        change = ChangeRecord(
            change_id=self._generate_change_id(dataset_id),
            dataset_id=dataset_id,
            change_type=ChangeType.VERSION,
            description=f"创建版本 {new_version}",
            version_before=metadata.version,
            version_after=new_version,
            operator=operator,
        )
        self.store.record_change(change)

        logger.info(f"创建数据集版本: {dataset_id} -> {new_version}")
        return version

    def update_quality(
        self,
        dataset_id: str,
        quality: str,
        reason: str = "",
        operator: str = "system",
    ) -> Optional[DatasetMetadata]:
        """
        更新质量等级

        Args:
            dataset_id: 数据集ID
            quality: 新质量等级
            reason: 变更原因
            operator: 操作者

        Returns:
            更新后的元数据
        """
        return self.update_metadata(
            dataset_id,
            {"quality": quality},
            operator,
            f"质量等级变更: {reason}",
        )

    def get_dataset_info(self, dataset_id: str) -> Dict[str, Any]:
        """
        获取数据集完整信息

        Args:
            dataset_id: 数据集ID

        Returns:
            数据集信息
        """
        metadata = self.store.get_metadata(dataset_id)
        versions = self.store.get_versions(dataset_id)
        changes = self.store.get_changes(dataset_id)

        return {
            "metadata": metadata,
            "versions": versions,
            "changes": changes,
            "version_count": len(versions),
            "change_count": len(changes),
        }

    def search_datasets(self, query: Union[str, MetadataSearchQuery]) -> MetadataSearchResult:
        """
        搜索数据集

        Args:
            query: 搜索查询

        Returns:
            搜索结果
        """
        if isinstance(query, str):
            query = MetadataSearchQuery(query_text=query)

        return self.store.search(query)

    def get_dataset_history(self, dataset_id: str) -> List[ChangeRecord]:
        """
        获取数据集变更历史

        Args:
            dataset_id: 数据集ID

        Returns:
            变更记录列表
        """
        return self.store.get_changes(dataset_id)

    def get_version_history(self, dataset_id: str) -> List[DatasetVersion]:
        """
        获取版本历史

        Args:
            dataset_id: 数据集ID

        Returns:
            版本列表
        """
        return self.store.get_versions(dataset_id)

    def compare_versions(
        self,
        dataset_id: str,
        version1: str,
        version2: str,
    ) -> Dict[str, Any]:
        """
        比较两个版本

        Args:
            dataset_id: 数据集ID
            version1: 版本1
            version2: 版本2

        Returns:
            比较结果
        """
        v1 = self.store.get_version(dataset_id, version1)
        v2 = self.store.get_version(dataset_id, version2)

        if v1 is None or v2 is None:
            return {"error": "版本不存在"}

        return {
            "version1": v1.model_dump(),
            "version2": v2.model_dump(),
            "changes_between": v2.changes if v2.changes else [],
            "time_diff": (v2.created_at - v1.created_at).total_seconds(),
        }

    def delete_dataset(self, dataset_id: str) -> bool:
        """
        删除数据集

        Args:
            dataset_id: 数据集ID

        Returns:
            是否成功
        """
        metadata = self.store.get_metadata(dataset_id)
        if metadata is None:
            return False

        # 记录删除变更
        change = ChangeRecord(
            change_id=self._generate_change_id(dataset_id),
            dataset_id=dataset_id,
            change_type=ChangeType.DELETE,
            description=f"删除数据集 {metadata.name}",
            before_state=metadata.model_dump(),
        )
        self.store.record_change(change)

        # 删除元数据
        return self.store.delete_metadata(dataset_id)

    def export_metadata(
        self,
        dataset_ids: Optional[List[str]] = None,
        output_path: Optional[Path] = None,
        format: str = "json",
    ) -> Path:
        """
        导出元数据

        Args:
            dataset_ids: 数据集ID列表（None表示全部）
            output_path: 输出路径
            format: 导出格式

        Returns:
            导出文件路径
        """
        output_path = output_path or self.store.storage_path / "export"

        if dataset_ids:
            metadata_list = [
                self.store.get_metadata(id)
                for id in dataset_ids
                if self.store.get_metadata(id)
            ]
        else:
            metadata_list = self.store.list_metadata()

        output_path.mkdir(parents=True, exist_ok=True)

        if format == "json":
            file_path = output_path / "metadata_export.json"
            data = [m.model_dump() for m in metadata_list]
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        elif format == "csv":
            file_path = output_path / "metadata_export.csv"
            records = []
            for m in metadata_list:
                records.append({
                    "id": m.id,
                    "name": m.name,
                    "version": m.version,
                    "type": m.dataset_type,
                    "data_type": m.data_type,
                    "format": m.format,
                    "quality": m.quality,
                    "total_records": m.total_records,
                    "source": m.source,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                })
            df = pd.DataFrame(records)
            df.to_csv(file_path, index=False, encoding="utf-8")

        logger.info(f"导出元数据到: {file_path}")
        return file_path

    def import_metadata(
        self,
        input_path: Path,
        format: str = "json",
    ) -> int:
        """
        导入元数据

        Args:
            input_path: 输入路径
            format: 导入格式

        Returns:
            导入数量
        """
        if format == "json":
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            count = 0
            for item in data:
                metadata = DatasetMetadata(**item)
                self.store.save_metadata(metadata)
                count += 1

            return count

        elif format == "csv":
            df = pd.read_csv(input_path)
            count = 0

            for _, row in df.iterrows():
                metadata = DatasetMetadata(
                    id=row["id"],
                    name=row["name"],
                    version=row["version"],
                    dataset_type=row["type"],
                    data_type=row["data_type"],
                    format=row["format"],
                    quality=row["quality"],
                    total_records=row["total_records"],
                    source=row["source"],
                )
                self.store.save_metadata(metadata)
                count += 1

            return count

        return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息
        """
        metadata_list = self.store.list_metadata()

        stats = {
            "total_datasets": len(metadata_list),
            "by_type": {},
            "by_data_type": {},
            "by_format": {},
            "by_quality": {},
            "total_records": 0,
            "total_size": 0,
        }

        for metadata in metadata_list:
            # 按类型统计
            type_key = metadata.dataset_type
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

            # 按数据类型统计
            data_type_key = metadata.data_type
            stats["by_data_type"][data_type_key] = stats["by_data_type"].get(data_type_key, 0) + 1

            # 按格式统计
            format_key = metadata.format
            stats["by_format"][format_key] = stats["by_format"].get(format_key, 0) + 1

            # 按质量统计
            quality_key = metadata.quality
            stats["by_quality"][quality_key] = stats["by_quality"].get(quality_key, 0) + 1

            # 总记录数和大小
            stats["total_records"] += metadata.total_records
            stats["total_size"] += metadata.file_size

        return stats

    def _generate_dataset_id(self, name: str) -> str:
        """生成数据集ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_input = f"{name}_{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{name}_{hash_value}"

    def _generate_change_id(self, dataset_id: str) -> str:
        """生成变更ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"change_{dataset_id}_{timestamp}"

    def _increment_version(self, version: str) -> str:
        """增加版本号"""
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            return ".".join(parts)
        return version


class DatasetLifecycleManager:
    """数据集生命周期管理器"""

    def __init__(self, metadata_manager: Optional[MetadataManager] = None):
        """
        初始化生命周期管理器

        Args:
            metadata_manager: 元数据管理器
        """
        self.metadata_manager = metadata_manager or MetadataManager()

    def archive_dataset(self, dataset_id: str) -> bool:
        """
        归档数据集

        Args:
            dataset_id: 数据集ID

        Returns:
            是否成功
        """
        updates = {
            "is_public": False,
            "extra": {"archived": True, "archived_at": datetime.now().isoformat()},
        }
        metadata = self.metadata_manager.update_metadata(
            dataset_id, updates, description="归档数据集"
        )
        return metadata is not None

    def restore_dataset(self, dataset_id: str) -> bool:
        """
        恢复数据集

        Args:
            dataset_id: 数据集ID

        Returns:
            是否成功
        """
        metadata = self.metadata_manager.store.get_metadata(dataset_id)
        if metadata is None:
            return False

        updates = {
            "is_public": True,
            "extra": {"archived": False, "restored_at": datetime.now().isoformat()},
        }
        result = self.metadata_manager.update_metadata(
            dataset_id, updates, description="恢复数据集"
        )
        return result is not None

    def set_expiration(
        self,
        dataset_id: str,
        expires_at: datetime,
    ) -> Optional[DatasetMetadata]:
        """
        设置过期时间

        Args:
            dataset_id: 数据集ID
            expires_at: 过期时间

        Returns:
            更新后的元数据
        """
        return self.metadata_manager.update_metadata(
            dataset_id,
            {"expires_at": expires_at},
            description=f"设置过期时间: {expires_at}",
        )

    def check_expiration(self) -> List[DatasetMetadata]:
        """
        检查已过期的数据集

        Returns:
            过期数据集列表
        """
        query = MetadataSearchQuery(has_expired=True)
        result = self.metadata_manager.search_datasets(query)
        return result.results

    def transfer_ownership(
        self,
        dataset_id: str,
        new_owner: str,
    ) -> Optional[DatasetMetadata]:
        """
        转移所有权

        Args:
            dataset_id: 数据集ID
            new_owner: 新所有者

        Returns:
            更新后的元数据
        """
        return self.metadata_manager.update_metadata(
            dataset_id,
            {"owner": new_owner},
            description=f"转移所有权给 {new_owner}",
        )