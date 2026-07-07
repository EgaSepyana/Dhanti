from app.core.config import get_settings
from app.providers.llm.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            default_model=settings.openrouter_default_model,
        )
