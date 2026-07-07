from app.core.config import get_settings
from app.providers.llm.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    # Groq's Qwen 3 reasoning models think before answering by default, and
    # that hidden reasoning is charged against max_tokens like any other
    # output — a tight max_tokens budget (needed to stay under Groq's TPM
    # cap) can get entirely consumed by reasoning before the model ever
    # writes the actual answer, truncating it to nothing (finish_reason
    # "length", empty content). None of DHANTI's calls to this model need
    # chain-of-thought — they're structured extraction (JSON, SQL) or direct
    # prose — so reasoning is disabled outright rather than just hidden.
    _extra_body = {"reasoning_format": "hidden", "reasoning_effort": "none"}

    # qwen/qwen3-32b on Groq's free/on_demand tier caps tokens-per-minute (TPM)
    # at 6000 for this org, and Groq counts (prompt_tokens + max_tokens) against
    # that single-request budget regardless of actual usage. Cap well under it
    # so a request never gets rejected outright just for requesting too much —
    # 5000 leaves ~1000 tokens of headroom for the prompt itself.
    _max_tokens_ceiling = 5000

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
            default_model=settings.groq_default_model,
        )
