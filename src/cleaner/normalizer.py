import re
from typing import List

from ..collector.models import AgentInteraction, ToolCall


class Normalizer:
    def __init__(self):
        self.whitespace_pattern = re.compile(r'\s+')

    def normalize_text(self, text: str) -> str:
        text = text.strip()
        text = self.whitespace_pattern.sub(' ', text)
        text = text.replace('\t', ' ')
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        return text

    def normalize_tool_call(self, tool_call: ToolCall) -> ToolCall:
        return tool_call

    def normalize(self, interactions: List[AgentInteraction]) -> List[AgentInteraction]:
        normalized_list = []
        for interaction in interactions:
            normalized_user_input = self.normalize_text(interaction.user_input)
            normalized_agent_response = self.normalize_text(interaction.agent_response)
            normalized_tool_calls = [self.normalize_tool_call(tc) for tc in interaction.tool_calls]
            normalized_list.append(AgentInteraction(
                id=interaction.id,
                timestamp=interaction.timestamp,
                user_input=normalized_user_input,
                agent_response=normalized_agent_response,
                tool_calls=normalized_tool_calls,
                metadata=interaction.metadata,
            ))
        return normalized_list
