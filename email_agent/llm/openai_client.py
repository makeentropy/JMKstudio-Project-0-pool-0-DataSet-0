import json
import requests
from typing import List, Generator
from .base import BaseLLM, ChatMessage, LLMResponse


class OpenAILLM(BaseLLM):
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key
        self.api_base = config.api_base or "https://api.openai.com/v1"
        self.model = config.model or "gpt-3.5-turbo"
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        try:
            payload = {
                "model": kwargs.get("model", self.model),
                "messages": self._build_messages(messages),
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                usage=usage,
            )
        except Exception as e:
            return LLMResponse(content="", error=str(e))

    def chat_stream(self, messages: List[ChatMessage], **kwargs) -> Generator[str, None, None]:
        try:
            payload = {
                "model": kwargs.get("model", self.model),
                "messages": self._build_messages(messages),
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "stream": True,
            }
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=60,
                stream=True,
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8", errors="replace")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError):
                            continue
        except Exception as e:
            yield f"\n[Error: {e}]"
