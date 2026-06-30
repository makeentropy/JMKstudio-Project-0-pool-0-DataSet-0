from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json

from ..annotator.models import AnnotatedData
from .formatter import FormatType, DataFormatter
from .splitter import DataSplitter, DatasetSplit
from .augmenter import TextAugmenter
from .exporter import ExportFormat, DataExporter
from config.config import settings


class DatasetGenerationPipeline:
    def __init__(
        self,
        input_dir: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
        enable_augmentation: bool = False,
        export_format: ExportFormat = ExportFormat.JSONL,
        random_seed: int = 42,
    ):
        self.input_dir = Path(input_dir) if input_dir else settings.ANNOTATED_DATA_DIR
        self.output_dir = Path(output_dir) if output_dir else settings.FINAL_DATA_DIR

        self.splitter = DataSplitter(
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            random_seed=random_seed,
        )
        self.augmenter = TextAugmenter(random_seed=random_seed)
        self.exporter = DataExporter(export_format=export_format)
        self.enable_augmentation = enable_augmentation

    def run(self) -> Dict[str, Any]:
        data_list = self._load_annotated_data()
        if not data_list:
            raise ValueError("No annotated data found")

        if self.enable_augmentation:
            data_list = self.augmenter.augment(data_list)

        split = self.splitter.split(data_list)
        split_info = self.splitter.get_split_info(split)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_output_dir = self.output_dir / f"dataset_{timestamp}"

        export_paths = self.exporter.export_split(
            train_data=split.train,
            val_data=split.val,
            test_data=split.test,
            output_dir=run_output_dir,
        )

        self._save_metadata(run_output_dir, split_info, export_paths)

        return {
            "output_dir": str(run_output_dir),
            "split_info": split_info,
            "export_paths": {k: str(v) for k, v in export_paths.items()},
        }

    def _load_annotated_data(self) -> List[AnnotatedData]:
        data_list = []

        if not self.input_dir.exists():
            return data_list

        for file_path in self.input_dir.glob("*.jsonl"):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        annotated_data = AnnotatedData.model_validate(data)
                        data_list.append(annotated_data)

        return data_list

    def _save_metadata(
        self,
        output_dir: Path,
        split_info: Dict[str, Any],
        export_paths: Dict[str, Path],
    ):
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "split_info": split_info,
            "export_paths": {k: str(v) for k, v in export_paths.items()},
            "enable_augmentation": self.enable_augmentation,
        }

        with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
