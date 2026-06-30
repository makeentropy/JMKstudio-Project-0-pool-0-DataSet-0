from typing import Any, Dict, List, Optional
from .models import AgentInteraction, ToolCall
from .storage import StorageManager


class DataCollectorSDK:
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage = StorageManager(storage_dir)
        self._current_interactions: List[AgentInteraction] = []

    def collect_interaction(
        self,
        user_input: str,
        agent_response: str,
        tool_calls: Optional[List[ToolCall]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentInteraction:
        interaction = AgentInteraction(
            user_input=user_input,
            agent_response=agent_response,
            tool_calls=tool_calls or [],
            metadata=metadata or {}
        )
        self._current_interactions.append(interaction)
        return interaction

    def add_tool_call(
        self,
        interaction: AgentInteraction,
        name: str,
        arguments: Dict[str, Any],
        result: Optional[Any] = None
    ) -> ToolCall:
        tool_call = ToolCall(
            name=name,
            arguments=arguments,
            result=result
        )
        interaction.tool_calls.append(tool_call)
        return tool_call

    def flush(self, filename: Optional[str] = None) -> None:
        if self._current_interactions:
            self.storage.save(self._current_interactions, filename)
            self._current_interactions.clear()

    def save_now(
        self,
        user_input: str,
        agent_response: str,
        tool_calls: Optional[List[ToolCall]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        filename: Optional[str] = None
    ) -> AgentInteraction:
        interaction = self.collect_interaction(
            user_input, agent_response, tool_calls, metadata
        )
        self.flush(filename)
        return interaction

    def get_saved_interactions(self) -> List[AgentInteraction]:
        return self.storage.load_all()

    def clear(self) -> None:
        self._current_interactions.clear()
        self.storage.clear_all()

    def __enter__(self) -> "DataCollectorSDK":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._current_interactions:
            self.flush()
