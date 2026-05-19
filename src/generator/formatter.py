from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import json
import pyarrow as pa
import pyarrow.parquet as pq

from ..annotator.models import AnnotatedData


class FormatType(str, Enum):
    HUGGINGFACE = "huggingface"
    JSONL = "jsonl"
    PARQUET = "parquet"


class DataFormatter:
    def __init__(self, format_type: FormatType = FormatType.HUGGINGFACE):
        self.format_type = format_type

    def format_sample(self, data: AnnotatedData) -> Dict[str, Any]:
        sample = {
            "id": data.id,
            "user_input": data.original_interaction.user_input,
            "agent_response": data.original_interaction.agent_response,
            "timestamp": data.original_interaction.timestamp.isoformat() if data.original_interaction.timestamp else None,
            "tool_calls": data.original_interaction.tool_calls,
            "annotations": [
                {
                    "label": ann.label.value if hasattr(ann.label, "value") else ann.label,
                    "confidence": ann.confidence,
                    "annotator_type": ann.annotator_type,
                }
                for ann in data.annotations
            ],
            "quality_score": data.quality_score,
            "is_verified": data.is_verified,
        }
        return sample

    def format_batch(self, data_list: List[AnnotatedData]) -> List[Dict[str, Any]]:
        return [self.format_sample(data) for data in data_list]

    def save(
        self,
        data_list: List[AnnotatedData],
        output_path: Union[str, Path],
        filename: Optional[str] = None,
    ) -> Path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        if self.format_type == FormatType.HUGGINGFACE:
            return self._save_huggingface(data_list, output_path, filename)
        elif self.format_type == FormatType.JSONL:
            return self._save_jsonl(data_list, output_path, filename)
        elif self.format_type == FormatType.PARQUET:
            return self._save_parquet(data_list, output_path, filename)
        else:
            raise ValueError(f"Unsupported format: {self.format_type}")

    def _save_huggingface(
        self,
        data_list: List[AnnotatedData],
        output_path: Path,
        filename: Optional[str] = None,
    ) -> Path:
        from datasets import Dataset, DatasetDict

        formatted_data = self.format_batch(data_list)
        dataset = Dataset.from_list(formatted_data)

        if filename:
            save_path = output_path / filename
        else:
            save_path = output_path / "huggingface_dataset"

        dataset.save_to_disk(str(save_path))
        return save_path

    def _save_jsonl(
        self,
        data_list: List[AnnotatedData],
        output_path: Path,
        filename: Optional[str] = None,
    ) -> Path:
        if filename:
            save_path = output_path / filename
        else:
            save_path = output_path / "dataset.jsonl"

        formatted_data = self.format_batch(data_list)

        with open(save_path, "w", encoding="utf-8") as f:
            for sample in formatted_data:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        return save_path

    def _save_parquet(
        self,
        data_list: List[AnnotatedData],
        output_path: Path,
        filename: Optional[str] = None,
    ) -> Path:
        if filename:
            save_path = output_path / filename
        else:
            save_path = output_path / "dataset.parquet"

        formatted_data = self.format_batch(data_list)

        if not formatted_data:
            return save_path

        df = pa.Table.from_pylist(formatted_data)
        pq.write_table(df, save_path)

        return save_path
