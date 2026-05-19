from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from ..collector.models import AgentInteraction


@dataclass
class QualityMetrics:
    total_count: int
    valid_count: int
    completeness_score: float
    text_quality_score: float
    overall_score: float


class QualityChecker:
    def __init__(
        self,
        min_text_length: int = 5,
        max_text_length: int = 10000,
    ):
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length

    def assess_completeness(self, interaction: AgentInteraction) -> float:
        score = 0.0
        if interaction.user_input:
            score += 0.4
        if interaction.agent_response:
            score += 0.4
        if interaction.tool_calls is not None:
            score += 0.2
        return score

    def assess_text_quality(self, text: str) -> float:
        if not text:
            return 0.0
        length = len(text)
        if length < self.min_text_length:
            return 0.2
        if length > self.max_text_length:
            return 0.5
        return 1.0

    def assess_interaction(self, interaction: AgentInteraction) -> Tuple[bool, Dict[str, float]]:
        completeness = self.assess_completeness(interaction)
        input_quality = self.assess_text_quality(interaction.user_input)
        response_quality = self.assess_text_quality(interaction.agent_response)
        text_quality = (input_quality + response_quality) / 2.0
        overall = (completeness + text_quality) / 2.0
        is_valid = overall >= 0.5
        metrics = {
            "completeness": completeness,
            "text_quality": text_quality,
            "overall": overall,
        }
        return is_valid, metrics

    def assess_batch(self, interactions: List[AgentInteraction]) -> QualityMetrics:
        if not interactions:
            return QualityMetrics(0, 0, 0.0, 0.0, 0.0)
        total = len(interactions)
        valid = 0
        total_completeness = 0.0
        total_text_quality = 0.0
        for interaction in interactions:
            is_valid, metrics = self.assess_interaction(interaction)
            if is_valid:
                valid += 1
            total_completeness += metrics["completeness"]
            total_text_quality += metrics["text_quality"]
        avg_completeness = total_completeness / total
        avg_text_quality = total_text_quality / total
        overall = (avg_completeness + avg_text_quality) / 2.0
        return QualityMetrics(
            total_count=total,
            valid_count=valid,
            completeness_score=avg_completeness,
            text_quality_score=avg_text_quality,
            overall_score=overall,
        )

    def filter(self, interactions: List[AgentInteraction]) -> List[AgentInteraction]:
        filtered = []
        for interaction in interactions:
            is_valid, _ = self.assess_interaction(interaction)
            if is_valid:
                filtered.append(interaction)
        return filtered
