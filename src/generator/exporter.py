from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import json

from ..annotator.models import AnnotatedData
from .formatter import FormatType, DataFormatter


class ExportFormat(str, Enum):
    HUGGINGFACE = "huggingface"
    JSONL = "jsonl"
    PARQUET = "parquet"
    LLAMA = "llama"
    ALPACA = "alpaca"


class DataExporter:
    def __init__(self, export_format: ExportFormat = ExportFormat.HUGGINGFACE):
        self.export_format = export_format

    def export(
        self,
        data_list: List[AnnotatedData],
        output_dir: Union[str, Path],
        filename: Optional[str] = None,
    ) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.export_format in [ExportFormat.HUGGINGFACE, ExportFormat.JSONL, ExportFormat.PARQUET]:
            format_type = FormatType(self.export_format.value)
            formatter = DataFormatter(format_type)
            return formatter.save(data_list, output_dir, filename)
        elif self.export_format == ExportFormat.LLAMA:
            return self._export_llama(data_list, output_dir, filename)
        elif self.export_format == ExportFormat.ALPACA:
            return self._export_alpaca(data_list, output_dir, filename)
        else:
            raise ValueError(f"Unsupported export format: {self.export_format}")

    def export_split(
        self,
        train_data: List[AnnotatedData],
        val_data: List[AnnotatedData],
        test_data: List[AnnotatedData],
        output_dir: Union[str, Path],
    ) -> Dict[str, Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        for split_name, data in [("train", train_data), ("val", val_data), ("test", test_data)]:
            if data:
                split_dir = output_dir / split_name
                split_filename = f"{split_name}.jsonl" if self.export_format in [ExportFormat.JSONL, ExportFormat.LLAMA, ExportFormat.ALPACA] else None
                results[split_name] = self.export(data, split_dir, split_filename)

        return results

    def _export_llama(
        self,
        data_list: List[AnnotatedData],
        output_dir: Path,
        filename: Optional[str] = None,
    ) -> Path:
        if filename:
            save_path = output_dir / filename
        else:
            save_path = output_dir / "llama_dataset.jsonl"

        with open(save_path, "w", encoding="utf-8") as f:
            for data in data_list:
                prompt = f"<s>[INST] {data.original_interaction.user_input} [/INST] {data.original_interaction.agent_response}"
                f.write(json.dumps({"text": prompt}, ensure_ascii=False) + "\n")

        return save_path

    def _export_alpaca(
        self,
        data_list: List[AnnotatedData],
        output_dir: Path,
        filename: Optional[str] = None,
    ) -> Path:
        if filename:
            save_path = output_dir / filename
        else:
            save_path = output_dir / "alpaca_dataset.jsonl"

        with open(save_path, "w", encoding="utf-8") as f:
            for data in data_list:
                sample = {
                    "instruction": data.original_interaction.user_input,
                    "input": "",
                    "output": data.original_interaction.agent_response,
                }
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        return save_path
