import re
from typing import Any, Dict, List

from ..collector.models import AgentInteraction, ToolCall


class Sanitizer:
    def __init__(self):
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.phone_pattern = re.compile(r'(\+?\d{1,4}[-.\s]?)?(\d{2,4}[-.\s]?){2,4}\d{2,4}')
        self.ipv4_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        self.ipv6_pattern = re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b')

    def sanitize_text(self, text: str) -> str:
        text = self.email_pattern.sub('[EMAIL]', text)
        text = self.phone_pattern.sub('[PHONE]', text)
        text = self.ipv4_pattern.sub('[IP]', text)
        text = self.ipv6_pattern.sub('[IP]', text)
        return text

    def sanitize_tool_call(self, tool_call: ToolCall) -> ToolCall:
        sanitized_arguments = {}
        for key, value in tool_call.arguments.items():
            if isinstance(value, str):
                sanitized_arguments[key] = self.sanitize_text(value)
            else:
                sanitized_arguments[key] = value
        return ToolCall(
            name=tool_call.name,
            arguments=sanitized_arguments,
            result=tool_call.result,
        )

    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_text(value)
            else:
                sanitized[key] = value
        return sanitized

    def sanitize(self, interactions: List[AgentInteraction]) -> List[AgentInteraction]:
        sanitized_list = []
        for interaction in interactions:
            sanitized_user_input = self.sanitize_text(interaction.user_input)
            sanitized_agent_response = self.sanitize_text(interaction.agent_response)
            sanitized_tool_calls = [self.sanitize_tool_call(tc) for tc in interaction.tool_calls]
            sanitized_metadata = self.sanitize_metadata(interaction.metadata)
            sanitized_list.append(AgentInteraction(
                id=interaction.id,
                timestamp=interaction.timestamp,
                user_input=sanitized_user_input,
                agent_response=sanitized_agent_response,
                tool_calls=sanitized_tool_calls,
                metadata=sanitized_metadata,
            ))
        return sanitized_list
