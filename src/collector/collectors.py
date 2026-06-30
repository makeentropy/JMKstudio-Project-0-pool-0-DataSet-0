import json
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
from abc import ABC, abstractmethod
from .models import AgentInteraction, ToolCall


class BaseCollector(ABC):
    @abstractmethod
    def collect(self) -> List[AgentInteraction]:
        pass


class FileCollector(BaseCollector):
    def __init__(self, file_path: str, format_type: str = "json"):
        self.file_path = Path(file_path)
        self.format_type = format_type.lower()

    def collect(self) -> List[AgentInteraction]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        if self.format_type == "json":
            return self._collect_json()
        elif self.format_type == "jsonl":
            return self._collect_jsonl()
        elif self.format_type == "csv":
            return self._collect_csv()
        else:
            raise ValueError(f"Unsupported format: {self.format_type}")

    def _collect_json(self) -> List[AgentInteraction]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._parse_data(data)

    def _collect_jsonl(self) -> List[AgentInteraction]:
        interactions = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    interactions.extend(self._parse_data(data))
        return interactions

    def _collect_csv(self) -> List[AgentInteraction]:
        interactions = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                interaction = self._parse_csv_row(row)
                interactions.append(interaction)
        return interactions

    def _parse_data(self, data: Any) -> List[AgentInteraction]:
        if isinstance(data, dict):
            if "interactions" in data:
                data = data["interactions"]
            else:
                return [self._dict_to_interaction(data)]
        return [self._dict_to_interaction(item) for item in data]

    def _dict_to_interaction(self, data: Dict[str, Any]) -> AgentInteraction:
        tool_calls = []
        if "tool_calls" in data:
            for tc in data["tool_calls"]:
                tool_calls.append(ToolCall(**tc))
        data["tool_calls"] = tool_calls
        return AgentInteraction(**data)

    def _parse_csv_row(self, row: Dict[str, str]) -> AgentInteraction:
        interaction_data = {
            "user_input": row.get("user_input", ""),
            "agent_response": row.get("agent_response", ""),
            "metadata": {}
        }
        for key, value in row.items():
            if key not in ["user_input", "agent_response"]:
                interaction_data["metadata"][key] = value
        return AgentInteraction(**interaction_data)


class APICollector(BaseCollector):
    def __init__(self, api_url: str, api_key: Optional[str] = None, params: Optional[Dict[str, Any]] = None):
        self.api_url = api_url
        self.api_key = api_key
        self.params = params or {}

    def collect(self) -> List[AgentInteraction]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.get(self.api_url, headers=headers, params=self.params)
        response.raise_for_status()
        data = response.json()
        return self._parse_response(data)

    def _parse_response(self, data: Any) -> List[AgentInteraction]:
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        elif isinstance(data, dict) and "interactions" in data:
            data = data["interactions"]
        
        if isinstance(data, list):
            interactions = []
            for item in data:
                if isinstance(item, dict):
                    tool_calls = []
                    if "tool_calls" in item:
                        for tc in item["tool_calls"]:
                            tool_calls.append(ToolCall(**tc))
                    item["tool_calls"] = tool_calls
                    interactions.append(AgentInteraction(**item))
            return interactions
        return []
