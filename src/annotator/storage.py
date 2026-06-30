import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import AnnotatedData
from ..collector.models import AgentInteraction
from ..cleaner.utils import load_interactions_from_jsonl
from config.config import settings


class AnnotationStorage:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or settings.ANNOTATED_DATA_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, prefix: str = "annotated") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.jsonl"

    def save_single(
        self,
        annotated_data: AnnotatedData,
        filename: Optional[str] = None
    ) -> Path:
        if filename is None:
            filename = self._generate_filename("single")
        file_path = self.storage_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(annotated_data.model_dump_json() + "\n")
        
        return file_path

    def save_batch(
        self,
        annotated_data_list: List[AnnotatedData],
        filename: Optional[str] = None
    ) -> Path:
        if filename is None:
            filename = self._generate_filename("batch")
        file_path = self.storage_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            for annotated_data in annotated_data_list:
                f.write(annotated_data.model_dump_json() + "\n")
        
        return file_path

    def load_single(self, file_path: Path) -> Optional[AnnotatedData]:
        if not file_path.exists():
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            if line:
                return AnnotatedData.model_validate_json(line)
        return None

    def load_batch(self, file_path: Path) -> List[AnnotatedData]:
        annotated_data_list = []
        
        if not file_path.exists():
            return annotated_data_list
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    annotated_data = AnnotatedData.model_validate_json(line)
                    annotated_data_list.append(annotated_data)
        
        return annotated_data_list

    def load_all(self) -> List[AnnotatedData]:
        all_data = []
        for file_path in self.storage_dir.glob("*.jsonl"):
            all_data.extend(self.load_batch(file_path))
        return all_data

    def load_from_processed(
        self,
        processed_dir: Optional[Path] = None
    ) -> List[AgentInteraction]:
        processed_dir = processed_dir or settings.PROCESSED_DATA_DIR
        return load_interactions_from_jsonl(processed_dir)

    def get_statistics(self) -> Dict:
        all_data = self.load_all()
        
        total = len(all_data)
        verified = sum(1 for d in all_data if d.is_verified)
        has_annotations = sum(1 for d in all_data if d.annotations)
        
        label_counts: Dict[str, int] = {}
        for data in all_data:
            for ann in data.annotations:
                label_key = ann.label.value
                if ann.label.value == "custom" and ann.custom_label:
                    label_key = f"custom:{ann.custom_label}"
                label_counts[label_key] = label_counts.get(label_key, 0) + 1
        
        return {
            "total_annotated_items": total,
            "verified_count": verified,
            "with_annotations_count": has_annotations,
            "label_distribution": label_counts,
            "verification_rate": verified / max(1, total)
        }

    def export_to_json(
        self,
        annotated_data_list: List[AnnotatedData],
        output_path: Path
    ) -> None:
        export_data = []
        for data in annotated_data_list:
            item = {
                "id": data.id,
                "original_interaction": data.original_interaction.model_dump(),
                "annotations": [ann.model_dump() for ann in data.annotations],
                "is_verified": data.is_verified,
                "verified_by": data.verified_by,
                "verified_at": data.verified_at.isoformat() if data.verified_at else None,
                "quality_score": data.quality_score,
                "metadata": data.metadata,
                "created_at": data.created_at.isoformat(),
                "updated_at": data.updated_at.isoformat()
            }
            export_data.append(item)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def append_to_file(
        self,
        annotated_data: AnnotatedData,
        file_path: Path
    ) -> None:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(annotated_data.model_dump_json() + "\n")
