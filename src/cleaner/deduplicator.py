from datetime import datetime, timedelta
from typing import List, Set

from ..collector.models import AgentInteraction
from .utils import compute_content_hash


class Deduplicator:
    def __init__(self):
        pass

    def deduplicate_by_id(self, interactions: List[AgentInteraction]) -> List[AgentInteraction]:
        seen_ids: Set[str] = set()
        unique = []
        for interaction in interactions:
            if interaction.id not in seen_ids:
                seen_ids.add(interaction.id)
                unique.append(interaction)
        return unique

    def deduplicate_by_content(self, interactions: List[AgentInteraction]) -> List[AgentInteraction]:
        seen_hashes: Set[str] = set()
        unique = []
        for interaction in interactions:
            data = interaction.model_dump()
            content_hash = compute_content_hash(data)
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(interaction)
        return unique

    def deduplicate_by_time_window(
        self,
        interactions: List[AgentInteraction],
        window_seconds: int = 3600,
    ) -> List[AgentInteraction]:
        if not interactions:
            return []
        sorted_interactions = sorted(interactions, key=lambda x: x.timestamp)
        result = []
        window_start = sorted_interactions[0].timestamp
        window_hashes: Set[str] = set()
        for interaction in sorted_interactions:
            time_diff = (interaction.timestamp - window_start).total_seconds()
            if time_diff > window_seconds:
                window_start = interaction.timestamp
                window_hashes.clear()
            data = interaction.model_dump()
            content_hash = compute_content_hash(data)
            if content_hash not in window_hashes:
                window_hashes.add(content_hash)
                result.append(interaction)
        return result
