from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import json
import logging
from dataclasses import dataclass, field
from enum import Enum

from datasets import Dataset, DatasetDict, load_dataset
from config.config import settings


logger = logging.getLogger(__name__)


class TrainingFramework(str, Enum):
    HUGGINGFACE = "huggingface"
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    LLAMAINDEX = "llamaindex"
    LANGCHAIN = "langchain"


@dataclass
class TrainingConfig:
    framework: TrainingFramework = TrainingFramework.HUGGINGFACE
    batch_size: int = 32
    learning_rate: float = 2e-5
    num_epochs: int = 3
    max_seq_length: int = 512
    validation_split: float = 0.1
    shuffle: bool = True
    random_seed: int = 42
    output_dir: Optional[Path] = None
    model_name_or_path: Optional[str] = None
    tokenizer_name: Optional[str] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


class DatasetLoader:
    def __init__(self, dataset_dir: Optional[Union[str, Path]] = None):
        self.dataset_dir = Path(dataset_dir) if dataset_dir else settings.FINAL_DATA_DIR
        
    def find_latest_dataset(self) -> Optional[Path]:
        if not self.dataset_dir.exists():
            return None
            
        dataset_dirs = sorted(
            [d for d in self.dataset_dir.iterdir() if d.is_dir() and d.name.startswith("dataset_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        return dataset_dirs[0] if dataset_dirs else None
        
    def load_from_dir(self, dataset_dir: Optional[Union[str, Path]] = None) -> DatasetDict:
        target_dir = Path(dataset_dir) if dataset_dir else self.find_latest_dataset()
        
        if target_dir is None or not target_dir.exists():
            raise ValueError(f"Dataset directory not found: {target_dir}")
            
        metadata_path = target_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            logger.info(f"Loading dataset from: {target_dir}")
            logger.info(f"Metadata: {metadata}")
        
        data_files = {}
        train_path = target_dir / "train" / "train.jsonl"
        val_path = target_dir / "val" / "val.jsonl"
        test_path = target_dir / "test" / "test.jsonl"
        
        if train_path.exists():
            data_files["train"] = str(train_path)
        if val_path.exists():
            data_files["validation"] = str(val_path)
        if test_path.exists():
            data_files["test"] = str(test_path)
            
        if not data_files:
            raise ValueError(f"No data files found in {target_dir}")
            
        return load_dataset("json", data_files=data_files)
        
    def load_split(self, dataset_dir: Optional[Union[str, Path]] = None, split: str = "train") -> Dataset:
        dataset_dict = self.load_from_dir(dataset_dir)
        if split not in dataset_dict:
            raise ValueError(f"Split '{split}' not found. Available splits: {list(dataset_dict.keys())}")
        return dataset_dict[split]


class TrainingDataFormatter:
    @staticmethod
    def format_for_chat(
        dataset: Dataset,
        user_key: str = "user_input",
        assistant_key: str = "agent_response",
        system_prompt: Optional[str] = None,
    ) -> Dataset:
        def format_example(example: Dict[str, Any]) -> Dict[str, Any]:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": example.get(user_key, "")})
            messages.append({"role": "assistant", "content": example.get(assistant_key, "")})
            return {"messages": messages}
            
        return dataset.map(format_example)
        
    @staticmethod
    def format_for_instruction(
        dataset: Dataset,
        instruction_template: Optional[str] = None,
        input_key: str = "user_input",
        output_key: str = "agent_response",
    ) -> Dataset:
        def format_example(example: Dict[str, Any]) -> Dict[str, Any]:
            instruction = example.get(input_key, "")
            if instruction_template:
                instruction = instruction_template.format(instruction=instruction)
            return {
                "instruction": instruction,
                "input": "",
                "output": example.get(output_key, ""),
            }
            
        return dataset.map(format_example)
        
    @staticmethod
    def filter_by_quality(
        dataset: Dataset,
        min_quality_score: float = 0.0,
        verified_only: bool = False,
    ) -> Dataset:
        def filter_example(example: Dict[str, Any]) -> bool:
            if verified_only and not example.get("is_verified", False):
                return False
            quality_score = example.get("quality_score", 1.0)
            return quality_score >= min_quality_score
            
        return dataset.filter(filter_example)


class AgentTrainingIntegration:
    def __init__(
        self,
        config: Optional[TrainingConfig] = None,
        dataset_dir: Optional[Union[str, Path]] = None,
    ):
        self.config = config or TrainingConfig()
        self.loader = DatasetLoader(dataset_dir)
        self.formatter = TrainingDataFormatter()
        self.dataset_dict: Optional[DatasetDict] = None
        
    def prepare_dataset(
        self,
        format_type: str = "chat",
        system_prompt: Optional[str] = None,
        min_quality_score: float = 0.0,
        verified_only: bool = False,
        **kwargs,
    ) -> DatasetDict:
        self.dataset_dict = self.loader.load_from_dir()
        
        for split in self.dataset_dict:
            if min_quality_score > 0 or verified_only:
                self.dataset_dict[split] = self.formatter.filter_by_quality(
                    self.dataset_dict[split],
                    min_quality_score=min_quality_score,
                    verified_only=verified_only,
                )
                
            if format_type == "chat":
                self.dataset_dict[split] = self.formatter.format_for_chat(
                    self.dataset_dict[split],
                    system_prompt=system_prompt,
                    **kwargs,
                )
            elif format_type == "instruction":
                self.dataset_dict[split] = self.formatter.format_for_instruction(
                    self.dataset_dict[split],
                    **kwargs,
                )
                
        logger.info(f"Dataset prepared. Splits: {list(self.dataset_dict.keys())}")
        return self.dataset_dict
        
    def get_huggingface_dataset(self) -> DatasetDict:
        if self.dataset_dict is None:
            self.prepare_dataset()
        return self.dataset_dict
        
    def save_prepared_dataset(self, output_dir: Optional[Union[str, Path]] = None) -> Path:
        if self.dataset_dict is None:
            raise ValueError("No dataset prepared. Call prepare_dataset() first.")
            
        save_dir = Path(output_dir) if output_dir else (
            Path(settings.BASE_DIR) / "prepared_datasets" / f"prepared_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        save_dir.mkdir(parents=True, exist_ok=True)
        
        self.dataset_dict.save_to_disk(str(save_dir))
        logger.info(f"Prepared dataset saved to: {save_dir}")
        return save_dir
        
    def register_training_callback(self, callback: Callable[[DatasetDict, TrainingConfig], Any]) -> None:
        self.training_callback = callback
        
    def run_training(
        self,
        trainer: Optional[Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if self.dataset_dict is None:
            self.prepare_dataset()
            
        if hasattr(self, "training_callback") and self.training_callback:
            result = self.training_callback(self.dataset_dict, self.config)
            return {"status": "success", "result": result}
            
        return {
            "status": "ready",
            "message": "Dataset prepared for training",
            "dataset_splits": {k: len(v) for k, v in self.dataset_dict.items()},
            "config": {
                "framework": self.config.framework.value,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "num_epochs": self.config.num_epochs,
            },
        }
