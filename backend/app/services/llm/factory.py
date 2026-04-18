from app.core.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.openai_provider import OpenAIProvider


def build_llm_provider(settings: Settings) -> LLMProvider | None:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    return None
