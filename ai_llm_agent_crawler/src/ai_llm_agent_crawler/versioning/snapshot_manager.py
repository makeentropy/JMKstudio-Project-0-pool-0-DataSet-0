"""
快照备份管理模块

提供数据快照备份、存储和恢复功能：
- 完整快照 (Full Snapshot)
- 增量快照 (Incremental Snapshot)
- 压缩快照 (Compressed Snapshot)
- 快照元数据管理
- 快照存储结构设计
- 数据一致性保护
"""

import gzip
import hashlib
import json
import os
import shutil
import tarfile
import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.config import get_settings
from ai_llm_agent_crawler.utils.logging import get_logger
from ai_llm_agent_crawler.versioning.version_manager import (
    VersionInfo,
    VersionManager,
    VersionType,
    VersionStatus,
)

logger = get_logger(__name__)


class SnapshotType(str, Enum):
    """快照类型"""
    FULL = "full"  # 完整快照
    INCREMENTAL = "incremental"  # 增量快照
    COMPRESSED = "compressed"  # 压缩快照
    DIFF = "diff"  # 差异快照


class SnapshotStatus(str, Enum):
    """快照状态"""
    CREATING = "creating"  # 创建中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    VERIFYING = "verifying"  # 验证中
    VERIFIED = "verified"  # 已验证
    CORRUPTED = "corrupted"  # 已损坏
    DELETED = "deleted"  # 已删除


class CompressionType(str, Enum):
    """压缩类型"""
    NONE = "none"  # 无压缩
    GZIP = "gzip"  # GZIP压缩
    TAR_GZ = "tar.gz"  # TAR.GZ压缩
    ZIP = "zip"  # ZIP压缩
    LZMA = "lzma"  # LZMA压缩


class SnapshotMetadata(BaseModel):
    """快照元数据"""
    snapshot_id: str = Field(..., description="快照ID")
    snapshot_type: SnapshotType = Field(..., description="快照类型")
    status: SnapshotStatus = Field(default=SnapshotStatus.COMPLETED, description="快照状态")
    
    # 基本信息
    name: str = Field(default="", description="快照名称")
    description: str = Field(default="", description="快照描述")
    
    # 关联信息
    entity_id: str = Field(..., description="实体ID")
    base_version: str = Field(..., description="基础版本")
    parent_snapshot: Optional[str] = Field(default=None, description="父快照ID")
    
    # 存储信息
    storage_path: Path = Field(default=Path(""), description="存储路径")
    compression_type: CompressionType = Field(default=CompressionType.NONE, description="压缩类型")
    original_size: int = Field(default=0, description="原始大小(字节)")
    compressed_size: int = Field(default=0, description="压缩后大小(字节)")
    compression_ratio: float = Field(default=0.0, description="压缩比率")
    
    # 文件信息
    file_count: int = Field(default=0, description="文件数量")
    checksum: str = Field(default="", description="校验和")
    checksum_algorithm: str = Field(default="sha256", description="校验算法")
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    
    # 增量快照信息
    changed_files: List[str] = Field(default_factory=list, description="变更文件列表")
    added_files: List[str] = Field(default_factory=list, description="新增文件列表")
    deleted_files: List[str] = Field(default_factory=list, description="删除文件列表")
    delta_size: int = Field(default=0, description="增量大小(字节)")
    
    # 验证信息
    is_verified: bool = Field(default=False, description="是否已验证")
    verified_at: Optional[datetime] = Field(default=None, description="验证时间")
    verification_errors: List[str] = Field(default_factory=list, description="验证错误")
    
    # 标签和备注
    tags: List[str] = Field(default_factory=list, description="标签")
    notes: str = Field(default="", description="备注")
    
    # 操作者
    created_by: str = Field(default="system", description="创建者")
    
    class Config:
        arbitrary_types_allowed = True


class SnapshotIndex(BaseModel):
    """快照索引"""
    entity_id: str = Field(..., description="实体ID")
    snapshots: List[SnapshotMetadata] = Field(default_factory=list, description="快照列表")
    latest_snapshot_id: Optional[str] = Field(default=None, description="最新快照ID")
    latest_full_snapshot_id: Optional[str] = Field(default=None, description="最新完整快照ID")
    total_size: int = Field(default=0, description="总大小(字节)")
    snapshot_count: int = Field(default=0, description="快照数量")
    
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class SnapshotStorage:
    """快照存储后端"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        初始化存储后端
        
        Args:
            storage_path: 存储路径
        """
        self.storage_path = storage_path or get_settings().dataset_output_dir / "snapshots"
        self._ensure_storage_path()
    
    def _ensure_storage_path(self) -> None:
        """确保存储路径存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def get_entity_snapshot_dir(self, entity_id: str) -> Path:
        """获取实体快照目录"""
        return self.storage_path / entity_id
    
    def get_snapshot_path(self, entity_id: str, snapshot_id: str) -> Path:
        """获取快照路径"""
        return self.get_entity_snapshot_dir(entity_id) / snapshot_id
    
    def create_snapshot_directory(self, entity_id: str, snapshot_id: str) -> Path:
        """创建快照目录"""
        snapshot_path = self.get_snapshot_path(entity_id, snapshot_id)
        snapshot_path.mkdir(parents=True, exist_ok=True)
        return snapshot_path
    
    def save_snapshot_metadata(self, entity_id: str, metadata: SnapshotMetadata) -> Path:
        """保存快照元数据"""
        metadata_path = self.get_snapshot_path(entity_id, metadata.snapshot_id) / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        return metadata_path
    
    def load_snapshot_metadata(self, entity_id: str, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """加载快照元数据"""
        metadata_path = self.get_snapshot_path(entity_id, snapshot_id) / "metadata.json"
        if not metadata_path.exists():
            return None
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SnapshotMetadata(**data)
        except Exception as e:
            logger.error(f"加载快照元数据失败: {e}")
            return None
    
    def calculate_checksum(self, path: Path, algorithm: str = "sha256") -> str:
        """计算文件或目录校验和"""
        if path.is_file():
            return self._calculate_file_checksum(path, algorithm)
        elif path.is_dir():
            return self._calculate_dir_checksum(path, algorithm)
        return ""
    
    def _calculate_file_checksum(self, file_path: Path, algorithm: str = "sha256") -> str:
        """计算文件校验和"""
        hash_func = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    
    def _calculate_dir_checksum(self, dir_path: Path, algorithm: str = "sha256") -> str:
        """计算目录校验和"""
        hash_func = hashlib.new(algorithm)
        for root, dirs, files in sorted(os.walk(dir_path)):
            for file in sorted(files):
                if file == "metadata.json":
                    continue  # 排除元数据文件
                file_path = Path(root) / file
                relative_path = file_path.relative_to(dir_path)
                hash_func.update(str(relative_path).encode())
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_func.update(chunk)
        return hash_func.hexdigest()
    
    def get_size(self, path: Path) -> int:
        """获取文件或目录大小"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total_size = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size
            return total_size
        return 0
    
    def compress_directory(
        self,
        source_dir: Path,
        compression_type: CompressionType,
    ) -> Path:
        """压缩目录"""
        compressed_name = source_dir.name
        
        if compression_type == CompressionType.GZIP:
            # 对于单个文件，使用gzip
            compressed_path = source_dir.parent / f"{compressed_name}.tar.gz"
            with tarfile.open(compressed_path, "w:gz") as tar:
                tar.add(source_dir, arcname=compressed_name)
            return compressed_path
        
        elif compression_type == CompressionType.TAR_GZ:
            compressed_path = source_dir.parent / f"{compressed_name}.tar.gz"
            with tarfile.open(compressed_path, "w:gz") as tar:
                tar.add(source_dir, arcname=compressed_name)
            return compressed_path
        
        elif compression_type == CompressionType.ZIP:
            compressed_path = source_dir.parent / f"{compressed_name}.zip"
            with zipfile.ZipFile(compressed_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(source_dir.parent)
                        zf.write(file_path, arcname)
            return compressed_path
        
        elif compression_type == CompressionType.LZMA:
            compressed_path = source_dir.parent / f"{compressed_name}.tar.xz"
            with tarfile.open(compressed_path, "w:xz") as tar:
                tar.add(source_dir, arcname=compressed_name)
            return compressed_path
        
        return source_dir
    
    def decompress_archive(self, archive_path: Path, target_dir: Path) -> Path:
        """解压归档"""
        if archive_path.suffix == ".gz" or archive_path.suffixes == [".tar", ".gz"]:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(target_dir)
            return target_dir
        
        elif archive_path.suffix == ".xz" or archive_path.suffixes == [".tar", ".xz"]:
            with tarfile.open(archive_path, "r:xz") as tar:
                tar.extractall(target_dir)
            return target_dir
        
        elif archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(target_dir)
            return target_dir
        
        return archive_path
    
    def delete_snapshot(self, entity_id: str, snapshot_id: str) -> bool:
        """删除快照"""
        snapshot_path = self.get_snapshot_path(entity_id, snapshot_id)
        try:
            if snapshot_path.exists():
                shutil.rmtree(snapshot_path)
            return True
        except Exception as e:
            logger.error(f"删除快照失败: {e}")
            return False


class SnapshotManager:
    """快照管理器"""
    
    def __init__(
        self,
        storage: Optional[SnapshotStorage] = None,
        version_manager: Optional[VersionManager] = None,
        max_snapshots: int = 100,
    ):
        """
        初始化快照管理器
        
        Args:
            storage: 存储后端
            version_manager: 版本管理器
            max_snapshots: 最大快照数
        """
        self.storage = storage or SnapshotStorage()
        self.version_manager = version_manager or VersionManager()
        self.max_snapshots = max_snapshots
        
        # 快照索引
        self.snapshot_indexes: Dict[str, SnapshotIndex] = {}
        
        # 加载已存储的快照索引
        self._load_indexes()
    
    def _load_indexes(self) -> None:
        """加载快照索引"""
        index_file = self.storage.storage_path / "snapshot_index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, index_data in data.items():
                    snapshots = [SnapshotMetadata(**s) for s in index_data.get("snapshots", [])]
                    self.snapshot_indexes[key] = SnapshotIndex(
                        entity_id=index_data["entity_id"],
                        snapshots=snapshots,
                        latest_snapshot_id=index_data.get("latest_snapshot_id"),
                        latest_full_snapshot_id=index_data.get("latest_full_snapshot_id"),
                        total_size=index_data.get("total_size", 0),
                        snapshot_count=index_data.get("snapshot_count", 0),
                    )
                logger.info(f"加载了 {len(self.snapshot_indexes)} 个快照索引")
            except Exception as e:
                logger.error(f"加载快照索引失败: {e}")
    
    def _save_indexes(self) -> None:
        """保存快照索引"""
        index_file = self.storage.storage_path / "snapshot_index.json"
        try:
            data = {}
            for key, index in self.snapshot_indexes.items():
                data[key] = index.model_dump()
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存快照索引失败: {e}")
    
    def create_full_snapshot(
        self,
        entity_id: str,
        source_path: Path,
        name: Optional[str] = None,
        description: str = "",
        compression_type: CompressionType = CompressionType.NONE,
        created_by: str = "system",
    ) -> SnapshotMetadata:
        """
        创建完整快照
        
        Args:
            entity_id: 实体ID
            source_path: 源路径
            name: 快照名称
            description: 快照描述
            compression_type: 压缩类型
            created_by: 创建者
            
        Returns:
            快照元数据
        """
        # 生成快照ID
        snapshot_id = self._generate_snapshot_id(entity_id)
        
        # 创建快照目录
        snapshot_dir = self.storage.create_snapshot_directory(entity_id, snapshot_id)
        
        # 记录原始大小
        original_size = self.storage.get_size(source_path)
        
        # 复制文件
        if source_path.is_file():
            target_file = snapshot_dir / source_path.name
            shutil.copy2(source_path, target_file)
        elif source_path.is_dir():
            target_subdir = snapshot_dir / "data"
            shutil.copytree(source_path, target_subdir)
        
        # 计算校验和
        checksum = self.storage.calculate_checksum(snapshot_dir)
        
        # 压缩（如果需要）
        final_path = snapshot_dir
        compressed_size = original_size
        
        if compression_type != CompressionType.NONE:
            compressed_archive = self.storage.compress_directory(snapshot_dir, compression_type)
            final_path = compressed_archive
            compressed_size = self.storage.get_size(compressed_archive)
            # 删除原始目录
            shutil.rmtree(snapshot_dir)
        
        # 获取基础版本
        latest_version = self.version_manager.get_latest_version(entity_id)
        base_version = latest_version.version if latest_version else "1.0.0"
        
        # 创建元数据
        metadata = SnapshotMetadata(
            snapshot_id=snapshot_id,
            snapshot_type=SnapshotType.FULL,
            name=name or f"full_snapshot_{snapshot_id}",
            description=description,
            entity_id=entity_id,
            base_version=base_version,
            storage_path=final_path,
            compression_type=compression_type,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size if original_size > 0 else 0,
            checksum=checksum,
            created_by=created_by,
            status=SnapshotStatus.COMPLETED,
            completed_at=datetime.now(),
        )
        
        # 统计文件数量
        if source_path.is_dir():
            metadata.file_count = sum(1 for _ in os.walk(source_path))
        else:
            metadata.file_count = 1
        
        # 保存元数据
        if compression_type == CompressionType.NONE:
            self.storage.save_snapshot_metadata(entity_id, metadata)
        else:
            # 对于压缩快照，将元数据存储在归档外
            metadata_dir = self.storage.get_entity_snapshot_dir(entity_id)
            metadata_file = metadata_dir / f"{snapshot_id}_metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        
        # 更新索引
        self._update_index(entity_id, metadata)
        
        logger.info(f"创建完整快照: {entity_id} -> {snapshot_id}")
        return metadata
    
    def create_incremental_snapshot(
        self,
        entity_id: str,
        source_path: Path,
        parent_snapshot_id: Optional[str] = None,
        name: Optional[str] = None,
        description: str = "",
        compression_type: CompressionType = CompressionType.NONE,
        created_by: str = "system",
    ) -> SnapshotMetadata:
        """
        创建增量快照
        
        Args:
            entity_id: 实体ID
            source_path: 源路径
            parent_snapshot_id: 父快照ID
            name: 快照名称
            description: 快照描述
            compression_type: 均缩类型
            created_by: 创建者
            
        Returns:
            快照元数据
        """
        # 获取父快照
        if parent_snapshot_id is None:
            # 使用最新的完整快照作为父快照
            parent_snapshot = self._get_latest_full_snapshot(entity_id)
            if parent_snapshot is None:
                # 如果没有完整快照，创建完整快照
                logger.warning(f"没有找到完整快照，将创建完整快照")
                return self.create_full_snapshot(
                    entity_id, source_path, name, description,
                    compression_type, created_by
                )
            parent_snapshot_id = parent_snapshot.snapshot_id
        else:
            parent_snapshot = self.get_snapshot(entity_id, parent_snapshot_id)
        
        # 生成快照ID
        snapshot_id = self._generate_snapshot_id(entity_id)
        
        # 创建快照目录
        snapshot_dir = self.storage.create_snapshot_directory(entity_id, snapshot_id)
        
        # 计算差异
        parent_path = parent_snapshot.storage_path
        if parent_snapshot.compression_type != CompressionType.NONE:
            # 解压父快照
            temp_dir = Path(str(parent_path) + "_temp")
            parent_path = self.storage.decompress_archive(parent_path, temp_dir)
        
        # 计算变更文件
        changed_files, added_files, deleted_files = self._calculate_diff(
            source_path, parent_path
        )
        
        # 只保存变更的文件
        delta_dir = snapshot_dir / "delta"
        delta_dir.mkdir(exist_ok=True)
        
        for file in added_files + changed_files:
            source_file = source_path / file
            if source_file.exists():
                target_file = delta_dir / file
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
        
        # 计算增量大小
        delta_size = self.storage.get_size(delta_dir)
        
        # 记录删除的文件
        deleted_file = snapshot_dir / "deleted.json"
        with open(deleted_file, "w", encoding="utf-8") as f:
            json.dump(deleted_files, f)
        
        # 计算校验和
        checksum = self.storage.calculate_checksum(snapshot_dir)
        
        # 压缩（如果需要）
        final_path = snapshot_dir
        compressed_size = delta_size
        
        if compression_type != CompressionType.NONE:
            compressed_archive = self.storage.compress_directory(snapshot_dir, compression_type)
            final_path = compressed_archive
            compressed_size = self.storage.get_size(compressed_archive)
            shutil.rmtree(snapshot_dir)
        
        # 获取基础版本
        latest_version = self.version_manager.get_latest_version(entity_id)
        base_version = latest_version.version if latest_version else parent_snapshot.base_version
        
        # 创建元数据
        metadata = SnapshotMetadata(
            snapshot_id=snapshot_id,
            snapshot_type=SnapshotType.INCREMENTAL,
            name=name or f"incremental_snapshot_{snapshot_id}",
            description=description,
            entity_id=entity_id,
            base_version=base_version,
            parent_snapshot=parent_snapshot_id,
            storage_path=final_path,
            compression_type=compression_type,
            original_size=self.storage.get_size(source_path),
            compressed_size=compressed_size,
            compression_ratio=compressed_size / delta_size if delta_size > 0 else 0,
            checksum=checksum,
            delta_size=delta_size,
            changed_files=changed_files,
            added_files=added_files,
            deleted_files=deleted_files,
            created_by=created_by,
            status=SnapshotStatus.COMPLETED,
            completed_at=datetime.now(),
        )
        
        # 统计文件数量
        metadata.file_count = len(added_files) + len(changed_files)
        
        # 保存元数据
        if compression_type == CompressionType.NONE:
            self.storage.save_snapshot_metadata(entity_id, metadata)
        else:
            metadata_dir = self.storage.get_entity_snapshot_dir(entity_id)
            metadata_file = metadata_dir / f"{snapshot_id}_metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        
        # 更新索引
        self._update_index(entity_id, metadata)
        
        logger.info(f"创建增量快照: {entity_id} -> {snapshot_id}")
        return metadata
    
    def create_compressed_snapshot(
        self,
        entity_id: str,
        source_path: Path,
        name: Optional[str] = None,
        description: str = "",
        compression_type: CompressionType = CompressionType.TAR_GZ,
        created_by: str = "system",
    ) -> SnapshotMetadata:
        """
        创建压缩快照
        
        Args:
            entity_id: 实体ID
            source_path: 源路径
            name: 快照名称
            description: 快照描述
            compression_type: 均缩类型
            created_by: 创建者
            
        Returns:
            快照元数据
        """
        return self.create_full_snapshot(
            entity_id, source_path, name, description,
            compression_type, created_by
        )
    
    def create_diff_snapshot(
        self,
        entity_id: str,
        source_path: Path,
        base_snapshot_id: str,
        name: Optional[str] = None,
        description: str = "",
        created_by: str = "system",
    ) -> SnapshotMetadata:
        """
        创建差异快照
        
        Args:
            entity_id: 实体ID
            source_path: 源路径
            base_snapshot_id: 基准快照ID
            name: 快照名称
            description: 快照描述
            created_by: 创建者
            
        Returns:
            快照元数据
        """
        return self.create_incremental_snapshot(
            entity_id, source_path, base_snapshot_id,
            name, description, CompressionType.NONE, created_by
        )
    
    def get_snapshot(self, entity_id: str, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """
        获取快照
        
        Args:
            entity_id: 实体ID
            snapshot_id: 快照ID
            
        Returns:
            快照元数据
        """
        # 先从索引查找
        index = self.snapshot_indexes.get(entity_id)
        if index:
            for snapshot in index.snapshots:
                if snapshot.snapshot_id == snapshot_id:
                    return snapshot
        
        # 从存储加载
        return self.storage.load_snapshot_metadata(entity_id, snapshot_id)
    
    def get_latest_snapshot(self, entity_id: str) -> Optional[SnapshotMetadata]:
        """
        获取最新快照
        
        Args:
            entity_id: 实体ID
            
        Returns:
            最新快照元数据
        """
        index = self.snapshot_indexes.get(entity_id)
        if index and index.latest_snapshot_id:
            return self.get_snapshot(entity_id, index.latest_snapshot_id)
        return None
    
    def get_latest_full_snapshot(self, entity_id: str) -> Optional[SnapshotMetadata]:
        """
        获取最新完整快照
        
        Args:
            entity_id: 实体ID
            
        Returns:
            最新完整快照元数据
        """
        index = self.snapshot_indexes.get(entity_id)
        if index and index.latest_full_snapshot_id:
            return self.get_snapshot(entity_id, index.latest_full_snapshot_id)
        
        # 手动查找
        if index:
            for snapshot in reversed(index.snapshots):
                if snapshot.snapshot_type == SnapshotType.FULL:
                    return snapshot
        return None
    
    def _get_latest_full_snapshot(self, entity_id: str) -> Optional[SnapshotMetadata]:
        """内部方法：获取最新完整快照"""
        return self.get_latest_full_snapshot(entity_id)
    
    def list_snapshots(
        self,
        entity_id: str,
        snapshot_type: Optional[SnapshotType] = None,
        status: Optional[SnapshotStatus] = None,
    ) -> List[SnapshotMetadata]:
        """
        列出快照
        
        Args:
            entity_id: 实体ID
            snapshot_type: 快照类型筛选
            status: 快照状态筛选
            
        Returns:
            快照列表
        """
        index = self.snapshot_indexes.get(entity_id)
        if not index:
            return []
        
        snapshots = index.snapshots
        
        # 筛选
        if snapshot_type:
            snapshots = [s for s in snapshots if s.snapshot_type == snapshot_type]
        if status:
            snapshots = [s for s in snapshots if s.status == status]
        
        return snapshots
    
    def restore_snapshot(
        self,
        entity_id: str,
        snapshot_id: str,
        output_path: Path,
        verify_integrity: bool = True,
    ) -> bool:
        """
        恢复快照
        
        Args:
            entity_id: 实体ID
            snapshot_id: 快照ID
            output_path: 输出路径
            verify_integrity: 是否验证完整性
            
        Returns:
            是否成功
        """
        snapshot = self.get_snapshot(entity_id, snapshot_id)
        if snapshot is None:
            logger.error(f"快照 '{snapshot_id}' 不存在")
            return False
        
        # 验证完整性
        if verify_integrity:
            if not self.verify_snapshot(entity_id, snapshot_id):
                logger.error(f"快照完整性验证失败")
                return False
        
        # 根据快照类型恢复
        if snapshot.snapshot_type == SnapshotType.FULL:
            return self._restore_full_snapshot(snapshot, output_path)
        elif snapshot.snapshot_type == SnapshotType.INCREMENTAL:
            return self._restore_incremental_snapshot(entity_id, snapshot, output_path)
        else:
            return self._restore_full_snapshot(snapshot, output_path)
    
    def _restore_full_snapshot(self, snapshot: SnapshotMetadata, output_path: Path) -> bool:
        """恢复完整快照"""
        snapshot_path = snapshot.storage_path
        
        try:
            # 如果是压缩的，先解压
            if snapshot.compression_type != CompressionType.NONE:
                temp_dir = output_path.parent / f"temp_{snapshot.snapshot_id}"
                self.storage.decompress_archive(snapshot_path, temp_dir)
                
                # 复制内容
                if temp_dir.is_dir():
                    data_dir = temp_dir / "data"
                    if data_dir.exists():
                        shutil.copytree(data_dir, output_path, dirs_exist_ok=True)
                    else:
                        shutil.copytree(temp_dir, output_path, dirs_exist_ok=True)
                
                # 清理临时目录
                shutil.rmtree(temp_dir)
            else:
                # 直接复制
                data_dir = snapshot_path / "data"
                if data_dir.exists():
                    shutil.copytree(data_dir, output_path, dirs_exist_ok=True)
                else:
                    # 单文件快照
                    for file in snapshot_path.iterdir():
                        if file.name != "metadata.json":
                            if output_path.is_dir():
                                shutil.copy2(file, output_path / file.name)
                            else:
                                shutil.copy2(file, output_path)
            
            logger.info(f"恢复完整快照: {snapshot.snapshot_id} -> {output_path}")
            return True
        except Exception as e:
            logger.error(f"恢复快照失败: {e}")
            return False
    
    def _restore_incremental_snapshot(
        self,
        entity_id: str,
        snapshot: SnapshotMetadata,
        output_path: Path,
    ) -> bool:
        """恢复增量快照"""
        # 首先恢复父快照（完整快照）
        parent_chain = self._get_snapshot_chain(entity_id, snapshot.snapshot_id)
        
        if not parent_chain:
            logger.error(f"无法获取快照链")
            return False
        
        # 找到完整快照作为基础
        base_full_snapshot = None
        for s in parent_chain:
            if s.snapshot_type == SnapshotType.FULL:
                base_full_snapshot = s
                break
        
        if base_full_snapshot is None:
            logger.error(f"找不到基础完整快照")
            return False
        
        # 恢复基础完整快照
        if not self._restore_full_snapshot(base_full_snapshot, output_path):
            return False
        
        # 按顺序应用增量快照
        incremental_snapshots = [s for s in parent_chain if s.snapshot_type == SnapshotType.INCREMENTAL]
        
        for inc_snapshot in incremental_snapshots:
            if not self._apply_incremental_snapshot(inc_snapshot, output_path):
                logger.error(f"应用增量快照失败: {inc_snapshot.snapshot_id}")
                return False
        
        logger.info(f"恢复增量快照链: {snapshot.snapshot_id} -> {output_path}")
        return True
    
    def _apply_incremental_snapshot(self, snapshot: SnapshotMetadata, output_path: Path) -> bool:
        """应用增量快照"""
        snapshot_path = snapshot.storage_path
        
        try:
            # 如果是压缩的，先解压
            if snapshot.compression_type != CompressionType.NONE:
                temp_dir = output_path.parent / f"temp_{snapshot.snapshot_id}"
                self.storage.decompress_archive(snapshot_path, temp_dir)
                delta_dir = temp_dir / "delta"
            else:
                delta_dir = snapshot_path / "delta"
            
            # 应用新增和修改的文件
            if delta_dir.exists():
                for root, dirs, files in os.walk(delta_dir):
                    for file in files:
                        source_file = Path(root) / file
                        relative_path = source_file.relative_to(delta_dir)
                        target_file = output_path / relative_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, target_file)
            
            # 处理删除的文件
            deleted_file_path = snapshot_path / "deleted.json" if snapshot.compression_type == CompressionType.NONE else temp_dir / "deleted.json"
            if deleted_file_path.exists():
                with open(deleted_file_path, "r", encoding="utf-8") as f:
                    deleted_files = json.load(f)
                for file in deleted_files:
                    file_to_delete = output_path / file
                    if file_to_delete.exists():
                        if file_to_delete.is_dir():
                            shutil.rmtree(file_to_delete)
                        else:
                            file_to_delete.unlink()
            
            # 清理临时目录
            if snapshot.compression_type != CompressionType.NONE and temp_dir.exists():
                shutil.rmtree(temp_dir)
            
            return True
        except Exception as e:
            logger.error(f"应用增量快照失败: {e}")
            return False
    
    def _get_snapshot_chain(self, entity_id: str, snapshot_id: str) -> List[SnapshotMetadata]:
        """获取快照链（从当前快照到完整快照）"""
        chain = []
        current = self.get_snapshot(entity_id, snapshot_id)
        
        while current:
            chain.append(current)
            if current.snapshot_type == SnapshotType.FULL:
                break
            if current.parent_snapshot:
                current = self.get_snapshot(entity_id, current.parent_snapshot)
            else:
                break
        
        return chain
    
    def verify_snapshot(self, entity_id: str, snapshot_id: str) -> bool:
        """
        验证快照完整性
        
        Args:
            entity_id: 实体ID
            snapshot_id: 快照ID
            
        Returns:
            是否验证通过
        """
        snapshot = self.get_snapshot(entity_id, snapshot_id)
        if snapshot is None:
            return False
        
        snapshot_path = snapshot.storage_path
        
        try:
            # 计算当前校验和
            if snapshot.compression_type != CompressionType.NONE:
                # 对于压缩快照，只验证归档完整性
                if snapshot_path.exists():
                    # 尝试解压验证
                    temp_dir = snapshot_path.parent / f"verify_temp_{snapshot_id}"
                    self.storage.decompress_archive(snapshot_path, temp_dir)
                    current_checksum = self.storage.calculate_checksum(temp_dir)
                    shutil.rmtree(temp_dir)
                else:
                    return False
            else:
                current_checksum = self.storage.calculate_checksum(snapshot_path)
            
            # 比较校验和
            is_valid = current_checksum == snapshot.checksum
            
            # 更新元数据
            snapshot.is_verified = is_valid
            snapshot.verified_at = datetime.now()
            if not is_valid:
                snapshot.verification_errors.append("校验和不匹配")
                snapshot.status = SnapshotStatus.CORRUPTED
            
            self._update_snapshot_metadata(entity_id, snapshot)
            
            return is_valid
        except Exception as e:
            logger.error(f"验证快照失败: {e}")
            snapshot.verification_errors.append(str(e))
            snapshot.status = SnapshotStatus.CORRUPTED
            self._update_snapshot_metadata(entity_id, snapshot)
            return False
    
    def _update_snapshot_metadata(self, entity_id: str, metadata: SnapshotMetadata) -> None:
        """更新快照元数据"""
        index = self.snapshot_indexes.get(entity_id)
        if index:
            for i, snapshot in enumerate(index.snapshots):
                if snapshot.snapshot_id == metadata.snapshot_id:
                    index.snapshots[i] = metadata
                    break
        self._save_indexes()
    
    def delete_snapshot(self, entity_id: str, snapshot_id: str, force: bool = False) -> bool:
        """
        删除快照
        
        Args:
            entity_id: 实体ID
            snapshot_id: 快照ID
            force: 是否强制删除（包括依赖的增量快照）
            
        Returns:
            是否成功
        """
        snapshot = self.get_snapshot(entity_id, snapshot_id)
        if snapshot is None:
            logger.error(f"快照 '{snapshot_id}' 不存在")
            return False
        
        # 检查是否有增量快照依赖此快照
        if snapshot.snapshot_type == SnapshotType.FULL and not force:
            dependent_snapshots = self._find_dependent_snapshots(entity_id, snapshot_id)
            if dependent_snapshots:
                logger.error(f"有 {len(dependent_snapshots)} 个增量快照依赖此快照")
                return False
        
        # 删除存储
        if not self.storage.delete_snapshot(entity_id, snapshot_id):
            return False
        
        # 更新索引
        index = self.snapshot_indexes.get(entity_id)
        if index:
            index.snapshots = [s for s in index.snapshots if s.snapshot_id != snapshot_id]
            index.snapshot_count = len(index.snapshots)
            
            # 更新最新快照ID
            if index.latest_snapshot_id == snapshot_id:
                if index.snapshots:
                    index.latest_snapshot_id = index.snapshots[-1].snapshot_id
                else:
                    index.latest_snapshot_id = None
            
            if index.latest_full_snapshot_id == snapshot_id:
                for s in reversed(index.snapshots):
                    if s.snapshot_type == SnapshotType.FULL:
                        index.latest_full_snapshot_id = s.snapshot_id
                        break
                else:
                    index.latest_full_snapshot_id = None
        
        self._save_indexes()
        
        logger.info(f"删除快照: {entity_id} -> {snapshot_id}")
        return True
    
    def _find_dependent_snapshots(self, entity_id: str, snapshot_id: str) -> List[SnapshotMetadata]:
        """查找依赖指定快照的增量快照"""
        index = self.snapshot_indexes.get(entity_id)
        if not index:
            return []
        
        dependent = []
        for snapshot in index.snapshots:
            if snapshot.parent_snapshot == snapshot_id:
                dependent.append(snapshot)
                # 递归查找
                dependent.extend(self._find_dependent_snapshots(entity_id, snapshot.snapshot_id))
        
        return dependent
    
    def cleanup_old_snapshots(
        self,
        entity_id: str,
        keep_count: Optional[int] = None,
        keep_full_snapshots: bool = True,
    ) -> int:
        """
        清理旧快照
        
        Args:
            entity_id: 实体ID
            keep_count: 保留数量
            keep_full_snapshots: 是否保留完整快照
            
        Returns:
            清理数量
        """
        keep_count = keep_count or self.max_snapshots
        snapshots = self.list_snapshots(entity_id)
        
        if len(snapshots) <= keep_count:
            return 0
        
        # 保留最新快照和完整快照
        to_keep = set()
        
        # 始终保留最新快照
        latest = self.get_latest_snapshot(entity_id)
        if latest:
            to_keep.add(latest.snapshot_id)
            # 保留快照链
            chain = self._get_snapshot_chain(entity_id, latest.snapshot_id)
            for s in chain:
                to_keep.add(s.snapshot_id)
        
        # 如果需要保留完整快照
        if keep_full_snapshots:
            full_snapshots = self.list_snapshots(entity_id, SnapshotType.FULL)
            for s in full_snapshots:
                to_keep.add(s.snapshot_id)
        
        # 按时间排序，删除最旧的
        snapshots_to_delete = [s for s in snapshots if s.snapshot_id not in to_keep]
        snapshots_to_delete.sort(key=lambda x: x.created_at)
        
        delete_count = max(0, len(snapshots_to_delete) - (keep_count - len(to_keep)))
        deleted = 0
        
        for snapshot in snapshots_to_delete[:delete_count]:
            if self.delete_snapshot(entity_id, snapshot.snapshot_id, force=True):
                deleted += 1
        
        logger.info(f"清理旧快照: {entity_id}, 删除了 {deleted} 个快照")
        return deleted
    
    def _generate_snapshot_id(self, entity_id: str) -> str:
        """生成快照ID（微秒级时间戳 + 随机盐避免冲突）"""
        import random
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
        salt = random.randint(0, 0xFFFF)
        hash_part = hashlib.md5(f"{entity_id}_{timestamp}_{salt}".encode()).hexdigest()[:8]
        return f"snap_{timestamp}_{hash_part}"
    
    def _calculate_diff(
        self,
        source_path: Path,
        base_path: Path,
    ) -> tuple:
        """
        计算差异
        
        Args:
            source_path: 源路径
            base_path: 基准路径
            
        Returns:
            (changed_files, added_files, deleted_files)
        """
        source_files = set()
        base_files = set()
        
        # 收集源文件
        if source_path.is_file():
            source_files.add(source_path.name)
        elif source_path.is_dir():
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    relative = Path(root) / file
                    source_files.add(str(relative.relative_to(source_path)))
        
        # 收集基准文件
        if base_path.is_file():
            base_files.add(base_path.name)
        elif base_path.is_dir():
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    relative = Path(root) / file
                    base_files.add(str(relative.relative_to(base_path)))
        
        # 计算差异
        added_files = sorted(list(source_files - base_files))
        deleted_files = sorted(list(base_files - source_files))
        common_files = source_files & base_files
        
        # 检查修改的文件
        changed_files = []
        for file in common_files:
            source_file = source_path / file
            base_file = base_path / file
            
            if source_file.is_file() and base_file.is_file():
                # 比较文件内容
                if self._files_different(source_file, base_file):
                    changed_files.append(file)
        
        return sorted(changed_files), added_files, deleted_files
    
    def _files_different(self, file1: Path, file2: Path) -> bool:
        """比较两个文件是否不同"""
        # 比较大小
        if file1.stat().st_size != file2.stat().st_size:
            return True
        
        # 比较校验和
        checksum1 = self.storage._calculate_file_checksum(file1)
        checksum2 = self.storage._calculate_file_checksum(file2)
        
        return checksum1 != checksum2
    
    def _update_index(self, entity_id: str, metadata: SnapshotMetadata) -> None:
        """更新快照索引"""
        if entity_id not in self.snapshot_indexes:
            self.snapshot_indexes[entity_id] = SnapshotIndex(entity_id=entity_id)
        
        index = self.snapshot_indexes[entity_id]
        index.snapshots.append(metadata)
        index.snapshot_count = len(index.snapshots)
        index.latest_snapshot_id = metadata.snapshot_id
        
        if metadata.snapshot_type == SnapshotType.FULL:
            index.latest_full_snapshot_id = metadata.snapshot_id
        
        # 更新总大小
        index.total_size = sum(s.compressed_size for s in index.snapshots)
        index.updated_at = datetime.now()
        
        self._save_indexes()
    
    def get_snapshot_statistics(self, entity_id: str) -> Dict[str, Any]:
        """
        获取快照统计信息
        
        Args:
            entity_id: 实体ID
            
        Returns:
            统计信息
        """
        snapshots = self.list_snapshots(entity_id)
        
        full_count = len([s for s in snapshots if s.snapshot_type == SnapshotType.FULL])
        incremental_count = len([s for s in snapshots if s.snapshot_type == SnapshotType.INCREMENTAL])
        compressed_count = len([s for s in snapshots if s.compression_type != CompressionType.NONE])
        
        total_size = sum(s.compressed_size for s in snapshots)
        total_original_size = sum(s.original_size for s in snapshots)
        
        avg_compression_ratio = 0
        if total_original_size > 0:
            avg_compression_ratio = total_size / total_original_size
        
        verified_count = len([s for s in snapshots if s.is_verified])
        
        return {
            "entity_id": entity_id,
            "total_snapshots": len(snapshots),
            "full_snapshots": full_count,
            "incremental_snapshots": incremental_count,
            "compressed_snapshots": compressed_count,
            "total_size": total_size,
            "total_original_size": total_original_size,
            "avg_compression_ratio": avg_compression_ratio,
            "verified_snapshots": verified_count,
            "latest_snapshot_id": self.snapshot_indexes.get(entity_id, SnapshotIndex(entity_id=entity_id)).latest_snapshot_id,
        }


# 导出所有类
__all__ = [
    "SnapshotType",
    "SnapshotStatus",
    "CompressionType",
    "SnapshotMetadata",
    "SnapshotIndex",
    "SnapshotStorage",
    "SnapshotManager",
]