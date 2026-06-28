"""
版本管理模块

提供数据版本控制、变更追踪和历史管理功能：
- 数据集版本管理
- 文件版本追踪
- 变更历史记录
- 版本回滚和恢复
- 版本比较和合并
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.config import get_settings
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class VersionType(str):
    """版本类型"""

    MAJOR = "major"  # 主版本
    MINOR = "minor"  # 次版本
    PATCH = "patch"  # 补丁版本
    SNAPSHOT = "snapshot"  # 快照版本
    RELEASE = "release"  # 发布版本
    BETA = "beta"  # 测试版本


class VersionStatus(str):
    """版本状态"""

    DRAFT = "draft"  # 草稿
    STABLE = "stable"  # 稳定
    DEPRECATED = "deprecated"  # 已弃用
    ARCHIVED = "archived"  # 已归档


class VersionInfo(BaseModel):
    """版本信息"""

    version: str = Field(..., description="版本号")
    version_type: str = Field(default=VersionType.RELEASE, description="版本类型")
    status: str = Field(default=VersionStatus.STABLE, description="版本状态")

    # 基本信息
    name: str = Field(default="", description="版本名称")
    description: str = Field(default="", description="版本描述")
    changes: List[str] = Field(default_factory=list, description="变更列表")
    notes: str = Field(default="", description="备注")

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")

    # 创建者信息
    created_by: str = Field(default="system", description="创建者")
    approved_by: Optional[str] = Field(default=None, description="审批者")

    # 关系信息
    parent_version: Optional[str] = Field(default=None, description="父版本")
    base_version: Optional[str] = Field(default=None, description="基准版本")
    dependencies: List[str] = Field(default_factory=list, description="依赖版本")

    # 文件信息
    file_path: Path = Field(default=Path(""), description="文件路径")
    checksum: str = Field(default="", description="校验和")
    size_bytes: int = Field(default=0, description="文件大小")

    # 统计信息
    record_count: int = Field(default=0, description="记录数")
    change_count: int = Field(default=0, description="变更数")

    # 标签
    tags: List[str] = Field(default_factory=list, description="标签")
    is_active: bool = Field(default=True, description="是否活跃")
    is_latest: bool = Field(default=False, description="是否最新")

    class Config:
        arbitrary_types_allowed = True


class VersionChange(BaseModel):
    """版本变更"""

    change_id: str = Field(..., description="变更ID")
    version: str = Field(..., description="版本号")
    change_type: str = Field(..., description="变更类型")

    # 变更内容
    description: str = Field(default="", description="变更描述")
    details: Dict[str, Any] = Field(default_factory=dict, description="变更详情")
    affected_files: List[str] = Field(default_factory=list, description="受影响文件")

    # 时间信息
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

    # 操作者
    operator: str = Field(default="system", description="操作者")


class VersionDiff(BaseModel):
    """版本差异"""

    version1: str = Field(..., description="版本1")
    version2: str = Field(..., description="版本2")
    diff_type: str = Field(default="content", description="差异类型")

    # 差异内容
    additions: List[str] = Field(default_factory=list, description="新增内容")
    deletions: List[str] = Field(default_factory=list, description="删除内容")
    modifications: List[str] = Field(default_factory=list, description="修改内容")

    # 统计
    addition_count: int = Field(default=0, description="新增数量")
    deletion_count: int = Field(default=0, description="删除数量")
    modification_count: int = Field(default=0, description="修改数量")

    # 相似度
    similarity: float = Field(default=0.0, description="相似度")


class VersionBranch(BaseModel):
    """版本分支"""

    branch_name: str = Field(..., description="分支名称")
    base_version: str = Field(..., description="基准版本")
    versions: List[str] = Field(default_factory=list, description="分支版本列表")

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 状态
    is_active: bool = Field(default=True, description="是否活跃")
    is_merged: bool = Field(default=False, description="是否已合并")
    merged_to: Optional[str] = Field(default=None, description="合并目标")


class VersionStorageBackend:
    """版本存储后端"""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        初始化存储后端

        Args:
            storage_path: 存储路径
        """
        self.storage_path = storage_path or get_settings().dataset_output_dir / "versions"
        self._ensure_storage_path()

    def _ensure_storage_path(self) -> None:
        """确保存储路径存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_version_file(
        self,
        source_path: Path,
        version_name: str,
        target_dir: Optional[Path] = None,
    ) -> Path:
        """
        保存版本文件

        Args:
            source_path: 源文件路径
            version_name: 版本名称
            target_dir: 目标目录

        Returns:
            保存的文件路径
        """
        target_dir = target_dir or self.storage_path / version_name
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / source_path.name
        shutil.copy2(source_path, target_path)

        return target_path

    def load_version_file(self, version_path: Path) -> bytes:
        """
        加载版本文件

        Args:
            version_path: 版本文件路径

        Returns:
            文件内容
        """
        with open(version_path, "rb") as f:
            return f.read()

    def delete_version(self, version_path: Path) -> bool:
        """
        删除版本

        Args:
            version_path: 版本路径

        Returns:
            是否成功
        """
        try:
            if version_path.is_dir():
                shutil.rmtree(version_path)
            elif version_path.is_file():
                version_path.unlink()
            return True
        except Exception as e:
            logger.error(f"删除版本失败: {e}")
            return False

    def calculate_checksum(self, file_path: Path) -> str:
        """
        计算文件校验和

        Args:
            file_path: 文件路径

        Returns:
            校验和
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_file_size(self, file_path: Path) -> int:
        """
        获取文件大小

        Args:
            file_path: 文件路径

        Returns:
            文件大小（字节）
        """
        return file_path.stat().st_size


class VersionManager:
    """版本管理器"""

    def __init__(
        self,
        storage_backend: Optional[VersionStorageBackend] = None,
        max_versions: Optional[int] = None,
    ):
        """
        初始化版本管理器

        Args:
            storage_backend: 存储后端
            max_versions: 最大版本数
        """
        self.storage_backend = storage_backend or VersionStorageBackend()
        self.max_versions = max_versions or get_settings().version_max_versions

        # 版本索引
        self.version_index: Dict[str, List[VersionInfo]] = {}
        self.change_index: Dict[str, List[VersionChange]] = {}
        self.branch_index: Dict[str, VersionBranch] = {}

        # 加载已存储的版本
        self._load_versions()

    def _load_versions(self) -> None:
        """加载已存储的版本"""
        version_file = self.storage_backend.storage_path / "version_index.json"
        if version_file.exists():
            try:
                with open(version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, versions in data.items():
                    self.version_index[key] = [VersionInfo(**v) for v in versions]
                logger.info(f"加载了 {len(self.version_index)} 个版本索引")
            except Exception as e:
                logger.error(f"加载版本索引失败: {e}")

    def _save_version_index(self) -> None:
        """保存版本索引"""
        version_file = self.storage_backend.storage_path / "version_index.json"
        try:
            data = {}
            for key, versions in self.version_index.items():
                data[key] = [v.model_dump() for v in versions]
            with open(version_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存版本索引失败: {e}")

    def create_version(
        self,
        entity_id: str,
        source_path: Path,
        version_type: str = VersionType.MINOR,
        description: str = "",
        changes: Optional[List[str]] = None,
        created_by: str = "system",
    ) -> VersionInfo:
        """
        创建新版本

        Args:
            entity_id: 实体ID（数据集ID等）
            source_path: 源文件路径
            version_type: 版本类型
            description: 版本描述
            changes: 变更列表
            created_by: 创建者

        Returns:
            版本信息
        """
        # 获取当前最新版本
        versions = self.version_index.get(entity_id, [])
        if versions:
            base_version = versions[-1].version
            new_version = self._increment_version(base_version, version_type)
        else:
            base_version = None
            new_version = "1.0.0"

        # 保存版本文件
        version_dir = self.storage_backend.storage_path / entity_id / new_version
        saved_path = self.storage_backend.save_version_file(
            source_path, new_version, version_dir
        )

        # 计算校验和和大小
        checksum = self.storage_backend.calculate_checksum(saved_path)
        size_bytes = self.storage_backend.get_file_size(saved_path)

        # 创建版本信息
        version_info = VersionInfo(
            version=new_version,
            version_type=version_type,
            name=f"{entity_id}_v{new_version}",
            description=description,
            changes=changes or [],
            created_by=created_by,
            parent_version=base_version,
            file_path=saved_path,
            checksum=checksum,
            size_bytes=size_bytes,
        )

        # 添加到索引
        if entity_id not in self.version_index:
            self.version_index[entity_id] = []
        self.version_index[entity_id].append(version_info)

        # 标记最新版本
        for v in self.version_index[entity_id]:
            v.is_latest = False
        version_info.is_latest = True

        # 保存索引
        self._save_version_index()

        logger.info(f"创建版本: {entity_id} -> {new_version}")
        return version_info

    def get_version(self, entity_id: str, version: str) -> Optional[VersionInfo]:
        """
        获取指定版本

        Args:
            entity_id: 实体ID
            version: 版本号

        Returns:
            版本信息
        """
        versions = self.version_index.get(entity_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    def get_latest_version(self, entity_id: str) -> Optional[VersionInfo]:
        """
        获取最新版本

        Args:
            entity_id: 实体ID

        Returns:
            最新版本信息
        """
        versions = self.version_index.get(entity_id, [])
        if versions:
            for v in versions:
                if v.is_latest:
                    return v
            return versions[-1]
        return None

    def get_all_versions(self, entity_id: str) -> List[VersionInfo]:
        """
        获取所有版本

        Args:
            entity_id: 实体ID

        Returns:
            版本列表
        """
        return self.version_index.get(entity_id, [])

    def update_version(
        self,
        entity_id: str,
        version: str,
        updates: Dict[str, Any],
    ) -> Optional[VersionInfo]:
        """
        更新版本信息

        Args:
            entity_id: 实体ID
            version: 版本号
            updates: 更新内容

        Returns:
            更新后的版本信息
        """
        version_info = self.get_version(entity_id, version)
        if version_info is None:
            return None

        for key, value in updates.items():
            if hasattr(version_info, key):
                setattr(version_info, key, value)

        version_info.updated_at = datetime.now()
        self._save_version_index()

        return version_info

    def deprecate_version(
        self,
        entity_id: str,
        version: str,
        reason: str = "",
    ) -> Optional[VersionInfo]:
        """
        弃用版本

        Args:
            entity_id: 实体ID
            version: 版本号
            reason: 弃用原因

        Returns:
            更新后的版本信息
        """
        return self.update_version(
            entity_id,
            version,
            {
                "status": VersionStatus.DEPRECATED,
                "notes": f"弃用原因: {reason}",
            },
        )

    def archive_version(
        self,
        entity_id: str,
        version: str,
    ) -> Optional[VersionInfo]:
        """
        归档版本

        Args:
            entity_id: 实体ID
            version: 版本号

        Returns:
            更新后的版本信息
        """
        return self.update_version(
            entity_id,
            version,
            {"status": VersionStatus.ARCHIVED, "is_active": False},
        )

    def restore_version(
        self,
        entity_id: str,
        version: str,
    ) -> Optional[Path]:
        """
        恢复版本

        Args:
            entity_id: 实体ID
            version: 版本号

        Returns:
            恢复的文件路径
        """
        version_info = self.get_version(entity_id, version)
        if version_info is None:
            logger.error(f"版本 '{version}' 不存在")
            return None

        # 更新状态为活跃
        self.update_version(
            entity_id,
            version,
            {"status": VersionStatus.STABLE, "is_active": True},
        )

        return version_info.file_path

    def rollback(
        self,
        entity_id: str,
        target_version: str,
    ) -> Optional[VersionInfo]:
        """
        回滚到指定版本

        Args:
            entity_id: 实体ID
            target_version: 目标版本

        Returns:
            回滚后的版本信息
        """
        target_info = self.get_version(entity_id, target_version)
        if target_info is None:
            logger.error(f"目标版本 '{target_version}' 不存在")
            return None

        # 创建回滚版本
        rollback_version = self.create_version(
            entity_id,
            target_info.file_path,
            version_type=VersionType.PATCH,
            description=f"回滚到版本 {target_version}",
            changes=[f"回滚自版本 {target_version}"],
        )

        logger.info(f"回滚: {entity_id} -> {target_version}")
        return rollback_version

    def compare_versions(
        self,
        entity_id: str,
        version1: str,
        version2: str,
    ) -> VersionDiff:
        """
        比较两个版本

        Args:
            entity_id: 实体ID
            version1: 版本1
            version2: 版本2

        Returns:
            版本差异
        """
        v1 = self.get_version(entity_id, version1)
        v2 = self.get_version(entity_id, version2)

        if v1 is None or v2 is None:
            return VersionDiff(
                version1=version1,
                version2=version2,
            )

        diff = VersionDiff(
            version1=version1,
            version2=version2,
        )

        # 比较变更列表
        changes1 = set(v1.changes)
        changes2 = set(v2.changes)

        diff.additions = list(changes2 - changes1)
        diff.deletions = list(changes1 - changes2)
        diff.modifications = list(changes1 & changes2)

        # 计算数量
        diff.addition_count = len(diff.additions)
        diff.deletion_count = len(diff.deletions)
        diff.modification_count = len(diff.modifications)

        # 计算相似度（基于变更）
        total_changes = len(changes1) + len(changes2)
        if total_changes > 0:
            common = len(changes1 & changes2)
            diff.similarity = common / total_changes

        return diff

    def create_branch(
        self,
        entity_id: str,
        branch_name: str,
        base_version: str,
    ) -> VersionBranch:
        """
        创建版本分支

        Args:
            entity_id: 实体ID
            branch_name: 分支名称
            base_version: 基准版本

        Returns:
            版本分支
        """
        branch_key = f"{entity_id}_{branch_name}"

        branch = VersionBranch(
            branch_name=branch_name,
            base_version=base_version,
            versions=[base_version],
        )

        self.branch_index[branch_key] = branch
        logger.info(f"创建分支: {branch_key}")
        return branch

    def get_branch(self, entity_id: str, branch_name: str) -> Optional[VersionBranch]:
        """
        获取分支

        Args:
            entity_id: 实体ID
            branch_name: 分支名称

        Returns:
            版本分支
        """
        branch_key = f"{entity_id}_{branch_name}"
        return self.branch_index.get(branch_key)

    def merge_branch(
        self,
        entity_id: str,
        branch_name: str,
        target_version: str,
    ) -> Optional[VersionInfo]:
        """
        合并分支

        Args:
            entity_id: 实体ID
            branch_name: 分支名称
            target_version: 目标版本

        Returns:
            合合后的版本信息
        """
        branch = self.get_branch(entity_id, branch_name)
        if branch is None:
            logger.error(f"分支 '{branch_name}' 不存在")
            return None

        # 获取分支最新版本
        branch_version = branch.versions[-1] if branch.versions else None
        if branch_version is None:
            return None

        branch_info = self.get_version(entity_id, branch_version)
        if branch_info is None:
            return None

        # 创建合并版本
        merged_version = self.create_version(
            entity_id,
            branch_info.file_path,
            version_type=VersionType.MAJOR,
            description=f"合并分支 {branch_name}",
            changes=[f"合并分支 {branch_name} 到 {target_version}"],
        )

        # 标记分支已合并
        branch_key = f"{entity_id}_{branch_name}"
        self.branch_index[branch_key].is_merged = True
        self.branch_index[branch_key].merged_to = merged_version.version
        self.branch_index[branch_key].updated_at = datetime.now()

        return merged_version

    def record_change(
        self,
        entity_id: str,
        version: str,
        change_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        operator: str = "system",
    ) -> VersionChange:
        """
        记录变更

        Args:
            entity_id: 实体ID
            version: 版本号
            change_type: 变更类型
            description: 变更描述
            details: 变更详情
            operator: 操作者

        Returns:
            变更记录
        """
        change_id = hashlib.md5(
            f"{entity_id}_{version}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        change = VersionChange(
            change_id=change_id,
            version=version,
            change_type=change_type,
            description=description,
            details=details or {},
            operator=operator,
        )

        change_key = f"{entity_id}_{version}"
        if change_key not in self.change_index:
            self.change_index[change_key] = []
        self.change_index[change_key].append(change)

        logger.info(f"记录变更: {change_id}")
        return change

    def get_changes(
        self,
        entity_id: str,
        version: str,
    ) -> List[VersionChange]:
        """
        获取版本变更历史

        Args:
            entity_id: 实体ID
            version: 版本号

        Returns:
            变更记录列表
        """
        change_key = f"{entity_id}_{version}"
        return self.change_index.get(change_key, [])

    def get_version_history(self, entity_id: str) -> Dict[str, Any]:
        """
        获取版本历史

        Args:
            entity_id: 实体ID

        Returns:
            版本历史
        """
        versions = self.get_all_versions(entity_id)

        return {
            "entity_id": entity_id,
            "total_versions": len(versions),
            "versions": [v.model_dump() for v in versions],
            "latest_version": self.get_latest_version(entity_id).model_dump()
            if self.get_latest_version(entity_id)
            else None,
        }

    def cleanup_old_versions(
        self,
        entity_id: str,
        keep_count: Optional[int] = None,
    ) -> int:
        """
        清理旧版本

        Args:
            entity_id: 实体ID
            keep_count: 保留数量

        Returns:
            清理数量
        """
        keep_count = keep_count or self.max_versions
        versions = self.get_all_versions(entity_id)

        if len(versions) <= keep_count:
            return 0

        # 保留最新的版本，归档旧版本
        versions_to_archive = versions[:-keep_count]
        archived_count = 0

        for version in versions_to_archive:
            if version.status != VersionStatus.ARCHIVED:
                self.archive_version(entity_id, version.version)
                archived_count += 1

        logger.info(f"清理旧版本: {entity_id}, 归档了 {archived_count} 个版本")
        return archived_count

    def _increment_version(self, base_version: str, version_type: str) -> str:
        """
        增加版本号

        Args:
            base_version: 基础版本
            version_type: 版本类型

        Returns:
            新版本号
        """
        parts = base_version.split(".")
        if len(parts) != 3:
            return "1.0.0"

        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if version_type == VersionType.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif version_type == VersionType.MINOR:
            minor += 1
            patch = 0
        elif version_type == VersionType.PATCH:
            patch += 1
        elif version_type == VersionType.SNAPSHOT:
            patch += 1

        return f"{major}.{minor}.{patch}"


class VersionControlSystem:
    """版本控制系统"""

    def __init__(
        self,
        version_manager: Optional[VersionManager] = None,
    ):
        """
        初始化版本控制系统

        Args:
            version_manager: 版本管理器
        """
        self.version_manager = version_manager or VersionManager()

    def commit(
        self,
        entity_id: str,
        source_path: Path,
        message: str = "",
        version_type: str = VersionType.MINOR,
    ) -> VersionInfo:
        """
        提交版本

        Args:
            entity_id: 实体ID
            source_path: 源文件路径
            message: 提交消息
            version_type: 版本类型

        Returns:
            版本信息
        """
        return self.version_manager.create_version(
            entity_id,
            source_path,
            version_type,
            description=message,
        )

    def checkout(
        self,
        entity_id: str,
        version: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        检出版本

        Args:
            entity_id: 实体ID
            version: 版本号（None表示最新版本）
            output_path: 输出路径

        Returns:
            检出的文件路径
        """
        if version is None:
            version_info = self.version_manager.get_latest_version(entity_id)
        else:
            version_info = self.version_manager.get_version(entity_id, version)

        if version_info is None:
            return None

        if output_path is None:
            return version_info.file_path

        # 复制到输出路径
        shutil.copy2(version_info.file_path, output_path)
        return output_path

    def diff(
        self,
        entity_id: str,
        version1: str,
        version2: str,
    ) -> VersionDiff:
        """
        查看差异

        Args:
            entity_id: 实体ID
            version1: 版本1
            version2: 版本2

        Returns:
            版本差异
        """
        return self.version_manager.compare_versions(entity_id, version1, version2)

    def log(self, entity_id: str) -> Dict[str, Any]:
        """
        查看版本日志

        Args:
            entity_id: 实体ID

        Returns:
            版本历史
        """
        return self.version_manager.get_version_history(entity_id)

    def revert(
        self,
        entity_id: str,
        target_version: str,
    ) -> Optional[VersionInfo]:
        """
        回滚版本

        Args:
            entity_id: 实体ID
            target_version: 目标版本

        Returns:
            回滚后的版本信息
        """
        return self.version_manager.rollback(entity_id, target_version)

    def branch(
        self,
        entity_id: str,
        branch_name: str,
        base_version: Optional[str] = None,
    ) -> VersionBranch:
        """
        创建分支

        Args:
            entity_id: 实体ID
            branch_name: 分支名称
            base_version: 基准版本

        Returns:
            版本分支
        """
        if base_version is None:
            latest = self.version_manager.get_latest_version(entity_id)
            base_version = latest.version if latest else "1.0.0"

        return self.version_manager.create_branch(entity_id, branch_name, base_version)

    def merge(
        self,
        entity_id: str,
        branch_name: str,
        target_version: Optional[str] = None,
    ) -> Optional[VersionInfo]:
        """
        合并分支

        Args:
            entity_id: 实体ID
            branch_name: 分支名称
            target_version: 目标版本

        Returns:
            合并后的版本信息
        """
        if target_version is None:
            latest = self.version_manager.get_latest_version(entity_id)
            target_version = latest.version if latest else "1.0.0"

        return self.version_manager.merge_branch(entity_id, branch_name, target_version)

    def tag(
        self,
        entity_id: str,
        version: str,
        tag_name: str,
    ) -> Optional[VersionInfo]:
        """
        添加标签

        Args:
            entity_id: 实体ID
            version: 版本号
            tag_name: 标签名称

        Returns:
            更新后的版本信息
        """
        return self.version_manager.update_version(
            entity_id,
            version,
            {"tags": [tag_name]},
        )

    def status(self, entity_id: str) -> Dict[str, Any]:
        """
        查看状态

        Args:
            entity_id: 实体ID

        Returns:
            状态信息
        """
        latest = self.version_manager.get_latest_version(entity_id)
        versions = self.version_manager.get_all_versions(entity_id)

        return {
            "entity_id": entity_id,
            "latest_version": latest.version if latest else None,
            "latest_status": latest.status if latest else None,
            "total_versions": len(versions),
            "active_versions": len([v for v in versions if v.is_active]),
            "deprecated_versions": len([v for v in versions if v.status == VersionStatus.DEPRECATED]),
            "archived_versions": len([v for v in versions if v.status == VersionStatus.ARCHIVED]),
        }

    def publish(
        self,
        entity_id: str,
        version: str,
    ) -> Optional[VersionInfo]:
        """
        发布版本

        Args:
            entity_id: 实体ID
            version: 版本号

        Returns:
            更新后的版本信息
        """
        return self.version_manager.update_version(
            entity_id,
            version,
            {
                "status": VersionStatus.STABLE,
                "published_at": datetime.now(),
            },
        )

    def unpublish(
        self,
        entity_id: str,
        version: str,
        reason: str = "",
    ) -> Optional[VersionInfo]:
        """
        取消发布

        Args:
            entity_id: 实体ID
            version: 版本号
            reason: 原因

        Returns:
            更新后的版本信息
        """
        return self.version_manager.deprecate_version(entity_id, version, reason)


# 导出所有类
__all__ = [
    "VersionType",
    "VersionStatus",
    "VersionInfo",
    "VersionChange",
    "VersionDiff",
    "VersionBranch",
    "VersionStorageBackend",
    "VersionManager",
    "VersionControlSystem",
]