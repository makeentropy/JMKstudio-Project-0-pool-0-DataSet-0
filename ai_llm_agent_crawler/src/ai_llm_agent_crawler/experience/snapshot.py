"""
经验池快照管理模块

提供经验数据池的快照创建、查询、对比、回滚和删除功能。
"""

import hashlib
import json
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.experience.models import ExperienceRecord
from ai_llm_agent_crawler.experience.pool import ExperienceDataPool
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


def _generate_snapshot_id() -> str:
    """生成快照唯一ID

    Returns:
        快照ID，格式为 snap_ + 时间戳 + 8位hash
    """
    timestamp = str(int(time.time() * 1000))
    random_hash = hashlib.md5(uuid.uuid4().hex.encode()).hexdigest()[:8]
    return f"snap_{timestamp}_{random_hash}"


class ExperiencePoolSnapshot(BaseModel):
    """经验池快照元数据模型"""

    snapshot_id: str = Field(..., description="快照唯一ID")
    version: str = Field(..., description="语义化版本号")
    name: str = Field(default="", description="快照名称")
    description: str = Field(default="", description="快照描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    record_count: int = Field(default=0, description="记录数量")
    total_size_bytes: int = Field(default=0, description="总字节数")
    checksum: str = Field(default="", description="数据校验和(sha256)")
    snapshot_type: str = Field(default="full", description="快照类型(full/incremental)")
    status: str = Field(default="completed", description="快照状态(creating/completed/failed)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        use_enum_values = True


class ExperienceSnapshotManager:
    """经验池快照管理器"""

    def __init__(
        self,
        pool: ExperienceDataPool,
        storage_dir: str = "./experience_snapshots",
        auto_create_dir: bool = True,
    ):
        """
        初始化快照管理器

        Args:
            pool: 关联的经验数据池
            storage_dir: 快照存储目录
            auto_create_dir: 是否自动创建目录
        """
        self._pool = pool
        self._storage_dir = Path(storage_dir)
        self._auto_create_dir = auto_create_dir
        self._logger = get_logger(f"{__name__}.ExperienceSnapshotManager")

        if self._auto_create_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)

        self._index_file = self._storage_dir / "snapshots.json"
        self._snapshots: Dict[str, ExperiencePoolSnapshot] = {}

        self._load_index()

    def _load_index(self) -> None:
        """加载快照索引文件"""
        if not self._index_file.exists():
            return

        try:
            with open(self._index_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for snapshot_data in data:
                if "created_at" in snapshot_data and isinstance(snapshot_data["created_at"], str):
                    snapshot_data["created_at"] = datetime.fromisoformat(snapshot_data["created_at"])
                snapshot = ExperiencePoolSnapshot(**snapshot_data)
                self._snapshots[snapshot.snapshot_id] = snapshot

            self._logger.info(f"加载快照索引，共 {len(self._snapshots)} 个快照")
        except Exception as e:
            self._logger.error(f"加载快照索引失败: {e}")

    def _save_index(self) -> None:
        """保存快照索引文件"""
        try:
            snapshots_list = []
            for snapshot in self._snapshots.values():
                data = snapshot.model_dump()
                data["created_at"] = snapshot.created_at.isoformat()
                snapshots_list.append(data)

            self._storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(snapshots_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._logger.error(f"保存快照索引失败: {e}")

    def _get_snapshot_dir(self, snapshot_id: str) -> Path:
        """获取快照目录路径

        Args:
            snapshot_id: 快照ID

        Returns:
            快照目录路径
        """
        return self._storage_dir / snapshot_id

    def _compute_checksum(self, data_json: str) -> str:
        """计算数据的sha256校验和

        Args:
            data_json: JSON字符串数据

        Returns:
            sha256校验和
        """
        return hashlib.sha256(data_json.encode("utf-8")).hexdigest()

    @staticmethod
    def _increment_version(current_version: str) -> str:
        """递增语义化版本号的patch部分

        Args:
            current_version: 当前版本号，如 1.0.0

        Returns:
            递增后的版本号，如 1.0.1
        """
        parts = current_version.split(".")
        if len(parts) != 3:
            return "0.1.0"

        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
            return f"{major}.{minor}.{patch + 1}"
        except ValueError:
            return "0.1.0"

    def _get_next_version(self) -> str:
        """获取下一个版本号

        Returns:
            下一个版本号
        """
        if not self._snapshots:
            return "0.1.0"

        latest = self.get_latest_snapshot()
        if latest is None:
            return "0.1.0"

        return self._increment_version(latest.version)

    def create_snapshot(
        self,
        name: str = "",
        description: str = "",
        version: Optional[str] = None,
    ) -> ExperiencePoolSnapshot:
        """
        创建当前经验池的完整快照

        Args:
            name: 快照名称
            description: 快照描述
            version: 版本号，未指定则自动递增

        Returns:
            快照元数据
        """
        snapshot_id = _generate_snapshot_id()
        snapshot_dir = self._get_snapshot_dir(snapshot_id)
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        records_list = [record.to_dict() for record in self._pool._records.values()]
        data_json = json.dumps(records_list, ensure_ascii=False, indent=2)

        checksum = self._compute_checksum(data_json)
        total_size_bytes = len(data_json.encode("utf-8"))

        data_file = snapshot_dir / "data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            f.write(data_json)

        if version is None:
            version = self._get_next_version()

        snapshot = ExperiencePoolSnapshot(
            snapshot_id=snapshot_id,
            version=version,
            name=name,
            description=description,
            record_count=len(records_list),
            total_size_bytes=total_size_bytes,
            checksum=checksum,
            snapshot_type="full",
            status="completed",
        )

        metadata_file = snapshot_dir / "metadata.json"
        metadata_data = snapshot.model_dump()
        metadata_data["created_at"] = snapshot.created_at.isoformat()
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata_data, f, ensure_ascii=False, indent=2)

        self._snapshots[snapshot_id] = snapshot
        self._save_index()

        self._logger.info(
            f"创建快照: {snapshot_id}, 版本: {version}, 记录数: {len(records_list)}"
        )

        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[ExperiencePoolSnapshot]:
        """
        按ID查询快照元数据

        Args:
            snapshot_id: 快照ID

        Returns:
            快照元数据，不存在则返回None
        """
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self) -> List[ExperiencePoolSnapshot]:
        """
        列出所有快照，按创建时间倒序排列

        Returns:
            快照列表
        """
        snapshots = list(self._snapshots.values())
        snapshots.sort(key=lambda s: s.created_at, reverse=True)
        return snapshots

    def _load_snapshot_data(self, snapshot_id: str) -> List[ExperienceRecord]:
        """加载快照数据

        Args:
            snapshot_id: 快照ID

        Returns:
            经验记录列表
        """
        snapshot_dir = self._get_snapshot_dir(snapshot_id)
        data_file = snapshot_dir / "data.json"

        if not data_file.exists():
            return []

        try:
            with open(data_file, "r", encoding="utf-8") as f:
                records_data = json.load(f)

            records = []
            for data in records_data:
                record = ExperienceRecord.from_dict(data)
                records.append(record)
            return records
        except Exception as e:
            self._logger.error(f"加载快照数据失败: {e}")
            return []

    def compare_snapshots(
        self,
        snapshot_id_1: str,
        snapshot_id_2: str,
    ) -> Dict[str, Any]:
        """
        对比两个快照的差异

        Args:
            snapshot_id_1: 第一个快照ID
            snapshot_id_2: 第二个快照ID

        Returns:
            对比结果，包含 added、removed、modified 和 summary
        """
        records_1 = self._load_snapshot_data(snapshot_id_1)
        records_2 = self._load_snapshot_data(snapshot_id_2)

        if not records_1 or not records_2:
            return {
                "added": [],
                "removed": [],
                "modified": [],
                "summary": {
                    "total_1": len(records_1),
                    "total_2": len(records_2),
                    "added_count": 0,
                    "removed_count": 0,
                    "modified_count": 0,
                },
            }

        records_1_dict = {r.experience_id: r for r in records_1}
        records_2_dict = {r.experience_id: r for r in records_2}

        ids_1 = set(records_1_dict.keys())
        ids_2 = set(records_2_dict.keys())

        added_ids = ids_2 - ids_1
        removed_ids = ids_1 - ids_2
        common_ids = ids_1 & ids_2

        added = [records_2_dict[rid].to_dict() for rid in added_ids]
        removed = [records_1_dict[rid].to_dict() for rid in removed_ids]

        modified = []
        for rid in common_ids:
            r1_dict = records_1_dict[rid].to_dict()
            r2_dict = records_2_dict[rid].to_dict()
            if r1_dict != r2_dict:
                modified.append(r2_dict)

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "summary": {
                "total_1": len(records_1),
                "total_2": len(records_2),
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
            },
        }

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        将经验池回滚到指定快照版本

        Args:
            snapshot_id: 快照ID

        Returns:
            是否成功
        """
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot is None:
            self._logger.error(f"快照不存在: {snapshot_id}")
            return False

        records = self._load_snapshot_data(snapshot_id)
        if not records and snapshot.record_count > 0:
            self._logger.error(f"快照数据加载失败: {snapshot_id}")
            return False

        self._pool._records.clear()
        for record in records:
            self._pool._records[record.experience_id] = record

        self._pool._update_dataframe()

        self._logger.info(f"回滚快照: {snapshot_id}, 记录数: {len(records)}")
        return True

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        删除指定快照（包括数据文件和元数据）

        Args:
            snapshot_id: 快照ID

        Returns:
            是否成功
        """
        if snapshot_id not in self._snapshots:
            self._logger.warning(f"快照不存在: {snapshot_id}")
            return False

        snapshot_dir = self._get_snapshot_dir(snapshot_id)
        try:
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir)

            del self._snapshots[snapshot_id]
            self._save_index()

            self._logger.info(f"删除快照: {snapshot_id}")
            return True
        except Exception as e:
            self._logger.error(f"删除快照失败: {e}")
            return False

    def get_latest_snapshot(self) -> Optional[ExperiencePoolSnapshot]:
        """
        获取最新的快照

        Returns:
            最新快照元数据，没有快照则返回None
        """
        if not self._snapshots:
            return None

        snapshots = list(self._snapshots.values())
        snapshots.sort(key=lambda s: s.created_at, reverse=True)
        return snapshots[0]
