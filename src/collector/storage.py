import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from .models import AgentInteraction


class StorageManager:
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = Path.cwd() / "data" / "raw"
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, interactions: List[AgentInteraction], filename: Optional[str] = None) -> Path:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interactions_{timestamp}.jsonl"
        
        file_path = self.base_dir / filename
        
        with open(file_path, "a", encoding="utf-8") as f:
            for interaction in interactions:
                f.write(interaction.model_dump_json() + "\n")
        
        return file_path

    def save_single(self, interaction: AgentInteraction, filename: Optional[str] = None) -> Path:
        return self.save([interaction], filename)

    def load_all(self) -> List[AgentInteraction]:
        interactions = []
        for file_path in self.base_dir.glob("*.jsonl"):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        interaction = AgentInteraction(**data)
                        interactions.append(interaction)
        return interactions

    def get_all_files(self) -> List[Path]:
        return sorted(self.base_dir.glob("*.jsonl"))

    def clear_all(self) -> None:
        for file_path in self.base_dir.glob("*.jsonl"):
            file_path.unlink()
