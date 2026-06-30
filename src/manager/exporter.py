from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import json
import csv
import shutil
import zipfile
from pydantic import BaseModel, Field
from .metadata import DatasetMetadata, DataSource, MetadataManager
from .version_manager import VersionManager
from .stats import StatsManager


class ExportFormat(str, Enum):
    JSONL = "jsonl"
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    ZIP = "zip"


class ImportResult(BaseModel):
    success: bool = Field(default=False, description="是否成功")
    imported_count: int = Field(default=0, description="导入条数")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")


class Exporter:
    def __init__(self, data_dir: Union[str, Path] = "/workspace/data"):
        self.data_dir = Path(data_dir)
        self.metadata_manager = MetadataManager(data_dir)
        self.version_manager = VersionManager(data_dir)
        self.stats_manager = StatsManager(data_dir)

    def export_dataset(
        self,
        dataset_id: str,
        output_path: Union[str, Path],
        format: ExportFormat = ExportFormat.JSONL,
        include_metadata: bool = True,
        version: Optional[str] = None
    ) -> Path:
        dataset = self.metadata_manager.load_metadata(dataset_id)
        if not dataset or not dataset.file_path:
            raise ValueError(f"Dataset not found: {dataset_id}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        source_path = dataset.file_path

        if version:
            temp_path = Path("/tmp/restored_version")
            if temp_path.exists():
                shutil.rmtree(temp_path)
            restored = self.version_manager.restore_version(dataset_id, version, temp_path)
            if restored:
                source_path = restored
            else:
                raise ValueError(f"Version {version} not found for dataset {dataset_id}")

        if format == ExportFormat.JSONL:
            return self._export_jsonl(source_path, output_path, include_metadata, dataset)
        elif format == ExportFormat.JSON:
            return self._export_json(source_path, output_path, include_metadata, dataset)
        elif format == ExportFormat.CSV:
            return self._export_csv(source_path, output_path, include_metadata, dataset)
        elif format == ExportFormat.ZIP:
            return self._export_zip(source_path, output_path, include_metadata, dataset)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_jsonl(
        self,
        source_path: Path,
        output_path: Path,
        include_metadata: bool,
        dataset: DatasetMetadata
    ) -> Path:
        data = self._collect_data(source_path)

        if output_path.is_dir():
            output_path = output_path / f"{dataset.name}.jsonl"

        with open(output_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        if include_metadata:
            meta_path = output_path.parent / f"{output_path.stem}_metadata.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(dataset.model_dump_json(indent=2))

        return output_path

    def _export_json(
        self,
        source_path: Path,
        output_path: Path,
        include_metadata: bool,
        dataset: DatasetMetadata
    ) -> Path:
        data = self._collect_data(source_path)

        if output_path.is_dir():
            output_path = output_path / f"{dataset.name}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if include_metadata:
            meta_path = output_path.parent / f"{output_path.stem}_metadata.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(dataset.model_dump_json(indent=2))

        return output_path

    def _export_csv(
        self,
        source_path: Path,
        output_path: Path,
        include_metadata: bool,
        dataset: DatasetMetadata
    ) -> Path:
        data = self._collect_data(source_path)

        if output_path.is_dir():
            output_path = output_path / f"{dataset.name}.csv"

        if not data:
            with open(output_path, "w", encoding="utf-8") as f:
                pass
            return output_path

        sample = data[0]
        flattened = self._flatten_dict(sample)
        fieldnames = list(flattened.keys())

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in data:
                flat_item = self._flatten_dict(item)
                row = {}
                for field in fieldnames:
                    row[field] = flat_item.get(field, "")
                writer.writerow(row)

        if include_metadata:
            meta_path = output_path.parent / f"{output_path.stem}_metadata.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(dataset.model_dump_json(indent=2))

        return output_path

    def _export_zip(
        self,
        source_path: Path,
        output_path: Path,
        include_metadata: bool,
        dataset: DatasetMetadata
    ) -> Path:
        if output_path.is_dir():
            output_path = output_path / f"{dataset.name}.zip"

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if source_path.is_file():
                zf.write(source_path, source_path.name)
            else:
                for file in source_path.rglob("*"):
                    if file.is_file():
                        arcname = str(file.relative_to(source_path.parent))
                        zf.write(file, arcname)

            if include_metadata:
                meta_content = dataset.model_dump_json(indent=2)
                zf.writestr(f"{dataset.name}_metadata.json", meta_content)

        return output_path

    def _collect_data(self, path: Path) -> List[Dict[str, Any]]:
        data = []

        if path.is_file():
            self._read_file_into_list(path, data)
        else:
            for file in path.rglob("*"):
                if file.is_file():
                    self._read_file_into_list(file, data)

        return data

    def _read_file_into_list(self, file: Path, data: List[Dict[str, Any]]):
        try:
            if file.suffix == ".jsonl":
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data.append(json.loads(line))
            elif file.suffix == ".json":
                with open(file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        data.extend(content)
                    else:
                        data.append(content)
        except Exception:
            pass

    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v, ensure_ascii=False)))
            else:
                items.append((new_key, v))
        return dict(items)

    def import_data(
        self,
        input_path: Union[str, Path],
        dataset_name: Optional[str] = None,
        source: DataSource = DataSource.RAW,
        auto_scan: bool = True
    ) -> ImportResult:
        input_path = Path(input_path)
        result = ImportResult()

        if not input_path.exists():
            result.errors.append(f"Input path not found: {input_path}")
            return result

        dest_dir = self.data_dir / source.value
        dest_dir.mkdir(parents=True, exist_ok=True)

        if input_path.is_file() and input_path.suffix == ".zip":
            return self._import_zip(input_path, dest_dir, dataset_name, source, auto_scan)

        if dataset_name is None:
            dataset_name = input_path.stem

        if input_path.is_file():
            dest_path = dest_dir / input_path.name
            shutil.copy2(input_path, dest_path)
        else:
            dest_path = dest_dir / input_path.name
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(input_path, dest_path)

        result.imported_count = self._count_entries(dest_path)
        result.success = True

        if auto_scan:
            dataset = self.metadata_manager.create_metadata(
                dest_path,
                name=dataset_name,
                source=source,
                tags=[source.value]
            )
            self.version_manager.create_initial_version(
                dataset.dataset_id,
                dest_path,
                "Initial import"
            )

        return result

    def _import_zip(
        self,
        zip_path: Path,
        dest_dir: Path,
        dataset_name: Optional[str],
        source: DataSource,
        auto_scan: bool
    ) -> ImportResult:
        result = ImportResult()

        extract_dir = dest_dir / zip_path.stem
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            extracted_items = list(extract_dir.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                single_dir = extracted_items[0]
                for item in single_dir.iterdir():
                    shutil.move(str(item), str(extract_dir / item.name))
                single_dir.rmdir()

            name = dataset_name or zip_path.stem
            result.imported_count = self._count_entries(extract_dir)
            result.success = True

            if auto_scan:
                dataset = self.metadata_manager.create_metadata(
                    extract_dir,
                    name=name,
                    source=source,
                    tags=[source.value, "imported"]
                )
                self.version_manager.create_initial_version(
                    dataset.dataset_id,
                    extract_dir,
                    "Imported from ZIP"
                )

        except Exception as e:
            result.errors.append(f"Failed to extract ZIP: {str(e)}")
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

        return result

    def _count_entries(self, path: Path) -> int:
        count = 0
        if path.is_file():
            if path.suffix == ".jsonl":
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        count = sum(1 for _ in f)
                except Exception:
                    pass
            elif path.suffix == ".json":
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            count = len(data)
                        else:
                            count = 1
                except Exception:
                    pass
        else:
            for file in path.rglob("*.jsonl"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        count += sum(1 for _ in f)
                except Exception:
                    pass
            for file in path.rglob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            count += len(data)
                        else:
                            count += 1
                except Exception:
                    pass
        return count
