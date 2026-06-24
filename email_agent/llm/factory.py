from .base import BaseLLM
from .openai_client import OpenAILLM
from .deepseek_client import DeepSeekLLM
from .ollama_client import OllamaLLM


class LLMFactory:
    _providers = {
        "openai": OpenAILLM,
        "deepseek": DeepSeekLLM,
        "ollama": OllamaLLM,
    }

    @classmethod
    def create(cls, config) -> BaseLLM:
        provider = config.provider.lower()
        if provider not in cls._providers:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Available: {', '.join(cls._providers.keys())}"
            )
        return cls._providers[provider](config)

    @classmethod
    def register_provider(cls, name: str, provider_class):
        cls._providers[name.lower()] = provider_class

    @classmethod
    def available_providers(cls) -> list:
        return list(cls._providers.keys())
