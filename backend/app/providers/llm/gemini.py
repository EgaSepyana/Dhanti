from app.core.config import get_settings
from app.providers.llm.openai_compatible import OpenAICompatibleProvider


class GeminiProvider(OpenAICompatibleProvider):
    """DHANTI's default/primary LLM provider — Gemini via its
    OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            base_url=settings.gemini_base_url,
            api_key=settings.gemini_api_key,
            default_model=settings.gemini_default_model,
        )
