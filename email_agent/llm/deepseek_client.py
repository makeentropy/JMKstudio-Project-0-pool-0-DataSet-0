from .openai_client import OpenAILLM
from typing import List, Generator
from .base import ChatMessage, LLMResponse


class DeepSeekLLM(OpenAILLM):
    def __init__(self, config):
        if not config.api_base:
            config.api_base = "https://api.deepseek.com/v1"
        if not config.model:
            config.model = "deepseek-chat"
        super().__init__(config)
