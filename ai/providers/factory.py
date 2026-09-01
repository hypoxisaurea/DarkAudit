"""Select a multimodal provider without coupling callers to an SDK."""
from ai.config import AISettings
from .base import MultimodalProvider
from .fake_provider import FakeMultimodalProvider
from .openai_provider import OpenAIResponsesProvider

def create_provider(settings: AISettings | None = None) -> MultimodalProvider:
    settings = settings or AISettings.from_env()
    if settings.provider == "fake": return FakeMultimodalProvider()
    if settings.provider == "openai":
        if not settings.model: raise ValueError("DARKAUDIT_MODEL is required for the OpenAI provider")
        return OpenAIResponsesProvider(settings.model)
    raise ValueError(f"Unsupported DARKAUDIT_PROVIDER: {settings.provider}")
