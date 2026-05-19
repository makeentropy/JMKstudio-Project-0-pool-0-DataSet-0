from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import json
import shutil
import hashlib
from .metadata import DatasetMetadata, DataSource, MetadataManager


class VersionChangeType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class VersionHistoryItem(BaseModel):
    version: str = Field(description="版本号")
    timestamp: datetime = Field(default_factory=datetime.now, description="创建时间")
    change_type: VersionChangeType = Field(description="变更类型")
    description: Optional[str] = Field(default=None, description="变更描述")
    author: Optional[str] = Field(default=None, description="作者")
    checksum: Optional[str] = Field(default=None, description="文件校验和")
    data_count: int = Field(default=0, description="数据条数")
    file_size: int = Field(default=0, description="文件大小")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DatasetVersion(BaseModel):
    dataset_id: str = Field(description="数据集ID")
    current_version: str = Field(default="1.0.0", description="当前版本号")
    versions: List[VersionHistoryItem] = Field(default_factory=list, description="版本历史")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VersionManager:
    def __init__(self, data_dir: Union[str, Path] = "/workspace/data"):
        self.data_dir = Path(data_dir)
        self.versions_dir = self.data_dir / ".versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_manager = MetadataManager(data_dir)

    def _increment_version(self, version: str, change_type: VersionChangeType) -> str:
        parts = version.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        if change_type == VersionChangeType.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif change_type == VersionChangeType.MINOR:
            minor += 1
            patch = 0
        elif change_type == VersionChangeType.PATCH:
            patch += 1

        return f"{major}.{minor}.{patch}"

    def _compute_checksum(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_file_size(self, path: Path) -> int:
        if path.is_file():
            return path.stat().st_size
        total_size = 0
        for file in path.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
        return total_size

    def _count_data_entries(self, path: Path) -> int:
        count = 0
        if path.is_file():
            if path.suffix == ".jsonl":
                with open(path, "r", encoding="utf-8") as f:
                    count = sum(1 for _ in f)
            elif path.suffix == ".json":
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            count = len(data)
                        else:
                            count = 1
                except Exception:
                    count = 1
        elif path.is_dir():
            for file in path.rglob("*.jsonl"):
                with open(file, "r", encoding="utf-8") as f:
                    count += sum(1 for _ in f)
            for file in path.rglob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            count += len(data)
                        else:
                            count += 1
                except Exception:
                    count += 1
        return count

    def _save_version_data(self, dataset_id: str, version: str, file_or_dir_path: Path) -> None:
        version_data_dir = self.versions_dir / dataset_id / version
        version_data_dir.mkdir(parents=True, exist_ok=True)

        if file_or_dir_path.is_file():
            shutil.copy2(file_or_dir_path, version_data_dir / file_or_dir_path.name)
        else:
            dest_dir = version_data_dir / file_or_dir_path.name
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(file_or_dir_path, dest_dir)

    def create_initial_version(
        self,
        dataset_id: str,
        file_or_dir_path: Union[str, Path],
        description: Optional[str] = None,
        author: Optional[str] = None
    ) -> DatasetVersion:
        path = Path(file_or_dir_path)
        if not path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")

        version = "1.0.0"
        checksum = self._compute_checksum(path) if path.is_file() else None
        data_count = self._count_data_entries(path)
        file_size = self._get_file_size(path)

        history_item = VersionHistoryItem(
            version=version,
            change_type=VersionChangeType.MAJOR,
            description=description or "Initial version",
            author=author,
            checksum=checksum,
            data_count=data_count,
            file_size=file_size
        )

        dataset_version = DatasetVersion(
            dataset_id=dataset_id,
            current_version=version,
            versions=[history_item]
        )

        self._save_version_data(dataset_id, version, path)
        self._save_dataset_version(dataset_version)
        return dataset_version

    def create_new_version(
        self,
        dataset_id: str,
        file_or_dir_path: Union[str, Path],
        change_type: VersionChangeType = VersionChangeType.PATCH,
        description: Optional[str] = None,
        author: Optional[str] = None
    ) -> DatasetVersion:
        path = Path(file_or_dir_path)
        if not path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")

        dataset_version = self.load_dataset_version(dataset_id)
        if not dataset_version:
            return self.create_initial_version(dataset_id, path, description, author)

        new_version = self._increment_version(dataset_version.current_version, change_type)
        checksum = self._compute_checksum(path) if path.is_file() else None
        data_count = self._count_data_entries(path)
        file_size = self._get_file_size(path)

        history_item = VersionHistoryItem(
            version=new_version,
            change_type=change_type,
            description=description,
            author=author,
            checksum=checksum,
            data_count=data_count,
            file_size=file_size
        )

        dataset_version.current_version = new_version
        dataset_version.versions.append(history_item)
        dataset_version.updated_at = datetime.now()

        self._save_version_data(dataset_id, new_version, path)
        self._save_dataset_version(dataset_version)
        return dataset_version

    def _save_dataset_version(self, dataset_version: DatasetVersion) -> None:
        version_file = self.versions_dir / f"{dataset_version.dataset_id}.json"
        dataset_version.updated_at = datetime.now()
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(dataset_version.model_dump_json(indent=2))

    def load_dataset_version(self, dataset_id: str) -> Optional[DatasetVersion]:
        version_file = self.versions_dir / f"{dataset_id}.json"
        if not version_file.exists():
            return None
        with open(version_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return DatasetVersion(**data)

    def list_versions(self, dataset_id: str) -> List[VersionHistoryItem]:
        dataset_version = self.load_dataset_version(dataset_id)
        if not dataset_version:
            return []
        return sorted(dataset_version.versions, key=lambda x: x.timestamp, reverse=True)

    def get_version(self, dataset_id: str, version: str) -> Optional[VersionHistoryItem]:
        dataset_version = self.load_dataset_version(dataset_id)
        if not dataset_version:
            return None
        for item in dataset_version.versions:
            if item.version == version:
                return item
        return None

    def restore_version(
        self,
        dataset_id: str,
        version: str,
        target_path: Union[str, Path]
    ) -> Optional[Path]:
        version_data_dir = self.versions_dir / dataset_id / version
        if not version_data_dir.exists():
            return None

        target = Path(target_path)
        if target.exists():
            if target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)

        items = list(version_data_dir.iterdir())
        if len(items) == 1:
            source = items[0]
            if source.is_file():
                shutil.copy2(source, target)
            else:
                shutil.copytree(source, target)
            return target
        return None

    def delete_version(self, dataset_id: str, version: str) -> bool:
        dataset_version = self.load_dataset_version(dataset_id)
        if not dataset_version:
            return False

        if dataset_version.current_version == version:
            return False

        dataset_version.versions = [v for v in dataset_version.versions if v.version != version]
        self._save_dataset_version(dataset_version)

        version_data_dir = self.versions_dir / dataset_id / version
        if version_data_dir.exists():
            shutil.rmtree(version_data_dir)
        return True

    def compare_versions(
        self,
        dataset_id: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        v1 = self.get_version(dataset_id, version1)
        v2 = self.get_version(dataset_id, version2)
        if not v1 or not v2:
            return {}

        return {
            "version1": v1.model_dump(),
            "version2": v2.model_dump(),
            "data_count_diff": v2.data_count - v1.data_count,
            "file_size_diff": v2.file_size - v1.file_size,
            "time_diff": v2.timestamp - v1.timestamp
        }
