from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import json
import shutil
import hashlib


class DataSource(str, Enum):
    RAW = "raw"
    ANNOTATED = "annotated"
    FINAL = "final"


class DatasetMetadata(BaseModel):
    dataset_id: str = Field(description="数据集唯一标识符")
    name: str = Field(description="数据集名称")
    description: Optional[str] = Field(default=None, description="数据集描述")
    source: DataSource = Field(description="数据来源类型")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    data_count: int = Field(default=0, description="数据条数")
    file_size: int = Field(default=0, description="文件总大小(字节)")
    file_path: Optional[Path] = Field(default=None, description="文件或目录路径")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    version: str = Field(default="1.0.0", description="版本号")
    checksum: Optional[str] = Field(default=None, description="文件校验和")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="自定义字段")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v)
        }


class MetadataManager:
    def __init__(self, data_dir: Union[str, Path] = "/workspace/data"):
        self.data_dir = Path(data_dir)
        self.metadata_dir = self.data_dir / ".metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

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

    def create_metadata(
        self,
        file_or_dir_path: Union[str, Path],
        name: Optional[str] = None,
        description: Optional[str] = None,
        source: DataSource = DataSource.RAW,
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> DatasetMetadata:
        path = Path(file_or_dir_path)
        if not path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")

        if name is None:
            name = path.stem

        dataset_id = f"{source.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        checksum = None
        if path.is_file():
            checksum = self._compute_checksum(path)

        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            name=name,
            description=description,
            source=source,
            file_path=path,
            file_size=self._get_file_size(path),
            data_count=self._count_data_entries(path),
            tags=tags or [],
            version=version,
            checksum=checksum,
            custom_fields=custom_fields or {}
        )

        self.save_metadata(metadata)
        return metadata

    def save_metadata(self, metadata: DatasetMetadata) -> None:
        metadata_file = self.metadata_dir / f"{metadata.dataset_id}.json"
        metadata.updated_at = datetime.now()
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

    def load_metadata(self, dataset_id: str) -> Optional[DatasetMetadata]:
        metadata_file = self.metadata_dir / f"{dataset_id}.json"
        if not metadata_file.exists():
            return None
        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("file_path"):
                data["file_path"] = Path(data["file_path"])
            return DatasetMetadata(**data)

    def list_datasets(self, source: Optional[DataSource] = None) -> List[DatasetMetadata]:
        datasets = []
        for metadata_file in self.metadata_dir.glob("*.json"):
            metadata = self.load_metadata(metadata_file.stem)
            if metadata:
                if source is None or metadata.source == source:
                    datasets.append(metadata)
        return sorted(datasets, key=lambda x: x.created_at, reverse=True)

    def delete_metadata(self, dataset_id: str) -> bool:
        metadata_file = self.metadata_dir / f"{dataset_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()
            return True
        return False

    def update_metadata(
        self,
        dataset_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Optional[DatasetMetadata]:
        metadata = self.load_metadata(dataset_id)
        if not metadata:
            return None

        if name is not None:
            metadata.name = name
        if description is not None:
            metadata.description = description
        if tags is not None:
            metadata.tags = tags
        if version is not None:
            metadata.version = version
        if custom_fields is not None:
            metadata.custom_fields = custom_fields

        self.save_metadata(metadata)
        return metadata

    def scan_data_directory(self) -> List[DatasetMetadata]:
        existing_ids = {m.dataset_id for m in self.list_datasets()}
        new_datasets = []

        for source in DataSource:
            source_dir = self.data_dir / source.value
            if source_dir.exists():
                for item in source_dir.iterdir():
                    if item.name.startswith("."):
                        continue
                    dataset = self.create_metadata(
                        item,
                        source=source,
                        tags=[source.value]
                    )
                    if dataset.dataset_id not in existing_ids:
                        new_datasets.append(dataset)

        return new_datasets
