from pathlib import Path
from typing import List, Callable

from ..collector.models import AgentInteraction
from .deduplicator import Deduplicator
from .sanitizer import Sanitizer
from .normalizer import Normalizer
from .quality import QualityChecker, QualityMetrics
from .utils import (
    ensure_directory,
    load_interactions_from_jsonl,
    save_interactions_to_jsonl,
)


class CleaningPipeline:
    def __init__(
        self,
        deduplication_method: str = "content",
        time_window_seconds: int = 3600,
        min_text_length: int = 5,
        max_text_length: int = 10000,
    ):
        self.deduplicator = Deduplicator()
        self.sanitizer = Sanitizer()
        self.normalizer = Normalizer()
        self.quality_checker = QualityChecker(
            min_text_length=min_text_length,
            max_text_length=max_text_length,
        )
        self.deduplication_method = deduplication_method
        self.time_window_seconds = time_window_seconds

    def process(self, interactions: List[AgentInteraction]) -> List[AgentInteraction]:
        processed = interactions.copy()
        processed = self.normalizer.normalize(processed)
        if self.deduplication_method == "id":
            processed = self.deduplicator.deduplicate_by_id(processed)
        elif self.deduplication_method == "time":
            processed = self.deduplicator.deduplicate_by_time_window(
                processed, self.time_window_seconds
            )
        else:
            processed = self.deduplicator.deduplicate_by_content(processed)
        processed = self.sanitizer.sanitize(processed)
        processed = self.quality_checker.filter(processed)
        return processed

    def evaluate(self, interactions: List[AgentInteraction]) -> QualityMetrics:
        return self.quality_checker.assess_batch(interactions)

    def run_from_directory(
        self,
        input_dir: str,
        output_dir: str,
        output_filename: str = None,
    ) -> Path:
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        ensure_directory(output_path)
        interactions = load_interactions_from_jsonl(input_path)
        processed = self.process(interactions)
        return save_interactions_to_jsonl(processed, output_path, output_filename)
