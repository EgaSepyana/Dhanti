from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "DHANTI"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # PostgreSQL
    database_url: str

    # Supabase
    supabase_url: str
    supabase_service_key: str
    supabase_bucket: str = "dhanti-files"

    # Redis
    redis_url: str

    # OpenRouter
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "qwen/qwen3-235b-a22b"

    # Groq (fallback LLM provider when the primary is rate-limited/out of credits)
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_default_model: str = "qwen/qwen3-32b"

    # GLM (default/primary LLM provider)
    glm_api_key: str = ""
    glm_base_url: str = "https://integrate.api.nvidia.com/v1"
    glm_default_model: str = "z-ai/glm-5.2"

    # Gemini (additional selectable LLM provider — not in the default fallback chain)
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/interactions"
    gemini_default_model: str = "gemini-2.5-flash"

    # Hugging Face
    hf_api_key: str
    hf_embedding_model: str = "BAAI/bge-m3"
    hf_inference_url: str = "https://router.huggingface.co/hf-inference"

    # Qdrant
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str = "dhanti_vectors"

    # File upload
    max_file_size_mb: int = 50
    allowed_file_types: str = "csv,xlsx,xls,pdf"

    # AI settings
    ai_max_tokens: int = 4096
    ai_temperature: float = 0.7
    ai_context_token_budget: int = 8000
    ai_execution_timeout_seconds: int = 120

    # Provider selection (config-driven; swap without code changes)
    # Groq primary: its free tier allows 1000 requests/min vs Gemini's 20/min,
    # and this pipeline fires several sequential LLM calls per user turn —
    # Gemini as primary meant every turn burned into that 20/min ceiling
    # before falling back. Gemini now only carries load when Groq itself fails.
    llm_provider: str = "groq_with_gemini_fallback"
    embedding_provider: str = "huggingface"
    vector_provider: str = "qdrant"
    storage_provider: str = "supabase"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_file_types_list(self) -> list[str]:
        return [t.strip().lower() for t in self.allowed_file_types.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
