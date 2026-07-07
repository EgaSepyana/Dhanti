from app.core.config import get_settings
from app.providers.llm.openai_compatible import OpenAICompatibleProvider


class GLMProvider(OpenAICompatibleProvider):
    """Selectable LLM provider — z-ai/glm-5.2 via NVIDIA's OpenAI-compatible
    inference API. Not the default: see app.providers.manager for the
    active provider chain."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            base_url=settings.glm_base_url,
            api_key=settings.glm_api_key,
            default_model=settings.glm_default_model,
        )
