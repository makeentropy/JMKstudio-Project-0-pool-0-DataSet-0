import json
import requests
from typing import List, Generator
from .base import BaseLLM, ChatMessage, LLMResponse


class OllamaLLM(BaseLLM):
    def __init__(self, config):
        super().__init__(config)
        self.api_base = config.api_base or "http://localhost:11434/api"
        self.model = config.model or "llama2"
        self.temperature = config.temperature

    def chat(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        try:
            payload = {
                "model": kwargs.get("model", self.model),
                "messages": self._build_messages(messages),
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                },
            }
            response = requests.post(
                f"{self.api_base}/chat",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
            )
        except Exception as e:
            return LLMResponse(content="", error=str(e))

    def chat_stream(self, messages: List[ChatMessage], **kwargs) -> Generator[str, None, None]:
        try:
            payload = {
                "model": kwargs.get("model", self.model),
                "messages": self._build_messages(messages),
                "stream": True,
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                },
            }
            response = requests.post(
                f"{self.api_base}/chat",
                json=payload,
                timeout=120,
                stream=True,
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode("utf-8", errors="replace"))
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            break
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            yield f"\n[Error: {e}]"
