import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..collector.models import AgentInteraction


def compute_content_hash(data: Dict[str, Any]) -> str:
    data_copy = data.copy()
    data_copy.pop("id", None)
    data_copy.pop("timestamp", None)
    data_copy.pop("metadata", None)
    sorted_data = json.dumps(data_copy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(sorted_data.encode("utf-8")).hexdigest()


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_interactions_to_jsonl(
    interactions: List[AgentInteraction],
    output_path: Path,
    filename: Optional[str] = None,
) -> Path:
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cleaned_interactions_{timestamp}.jsonl"
    file_path = output_path / filename
    with open(file_path, "w", encoding="utf-8") as f:
        for interaction in interactions:
            f.write(interaction.model_dump_json() + "\n")
    return file_path


def load_interactions_from_jsonl(input_path: Path) -> List[AgentInteraction]:
    interactions = []
    for file_path in input_path.glob("*.jsonl"):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    interaction = AgentInteraction(**data)
                    interactions.append(interaction)
    return interactions
