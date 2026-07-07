from collections.abc import Callable
from functools import lru_cache

from app.core.config import get_settings
from app.providers.base import EmbeddingProvider, LLMProvider, StorageProvider, VectorProvider
from app.providers.embedding.huggingface import HuggingFaceEmbeddingProvider
from app.providers.llm.fallback import FallbackLLMProvider
from app.providers.llm.gemini import GeminiProvider
from app.providers.llm.glm import GLMProvider
from app.providers.llm.groq import GroqProvider
from app.providers.llm.openrouter import OpenRouterProvider
from app.providers.storage.supabase import SupabaseStorageProvider
from app.providers.vector.qdrant import QdrantProvider


def _make_openrouter_with_groq_fallback() -> LLMProvider:
    return FallbackLLMProvider(primary=OpenRouterProvider(), fallback=GroqProvider())


def _make_glm_with_groq_fallback() -> LLMProvider:
    return FallbackLLMProvider(primary=GLMProvider(), fallback=GroqProvider())


def _make_gemini_with_groq_fallback() -> LLMProvider:
    return FallbackLLMProvider(primary=GeminiProvider(), fallback=GroqProvider())


def _make_groq_with_gemini_fallback() -> LLMProvider:
    return FallbackLLMProvider(primary=GroqProvider(), fallback=GeminiProvider())


LLM_REGISTRY: dict[str, Callable[[], LLMProvider]] = {
    "openrouter": OpenRouterProvider,
    "groq": GroqProvider,
    "glm": GLMProvider,
    "gemini": GeminiProvider,
    "openrouter_with_groq_fallback": _make_openrouter_with_groq_fallback,
    "glm_with_groq_fallback": _make_glm_with_groq_fallback,
    "gemini_with_groq_fallback": _make_gemini_with_groq_fallback,
    "groq_with_gemini_fallback": _make_groq_with_gemini_fallback,
}

# A model id belongs to exactly one provider's catalog — passing it as a
# `model=` override to whichever provider happens to be primary right now
# (e.g. Gemini) would send that provider a model id it doesn't recognize.
# This maps each selectable override (see frontend/src/lib/models.ts) to the
# provider chain that actually owns it, so picking a model also picks its
# provider instead of just relabeling the current primary's request.
MODEL_TO_PROVIDER_KEY: dict[str, str] = {
    "gemini-2.5-flash": "gemini_with_groq_fallback",
    "z-ai/glm-5.2": "glm_with_groq_fallback",
    "qwen/qwen3-32b": "groq",
    "qwen/qwen3.6-27b": "groq",
    "llama-3.3-70b-versatile": "groq",
    "openai/gpt-oss-120b": "groq",
}
EMBEDDING_REGISTRY: dict[str, type[EmbeddingProvider]] = {
    "huggingface": HuggingFaceEmbeddingProvider,
}
VECTOR_REGISTRY: dict[str, type[VectorProvider]] = {
    "qdrant": QdrantProvider,
}
STORAGE_REGISTRY: dict[str, type[StorageProvider]] = {
    "supabase": SupabaseStorageProvider,
}


class ProviderManager:
    """Config-driven registry: swapping a provider is a settings change, not a code change."""

    def __init__(self) -> None:
        settings = get_settings()
        self._llm_key = settings.llm_provider
        self._embedding_key = settings.embedding_provider
        self._vector_key = settings.vector_provider
        self._storage_key = settings.storage_provider

        self._llm: LLMProvider | None = None
        self._embedding: EmbeddingProvider | None = None
        self._vector: VectorProvider | None = None
        self._storage: StorageProvider | None = None

    def get_llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = LLM_REGISTRY[self._llm_key]()
        return self._llm

    def get_embedding(self) -> EmbeddingProvider:
        if self._embedding is None:
            self._embedding = EMBEDDING_REGISTRY[self._embedding_key]()
        return self._embedding

    def get_vector(self) -> VectorProvider:
        if self._vector is None:
            self._vector = VECTOR_REGISTRY[self._vector_key]()
        return self._vector

    def get_storage(self) -> StorageProvider:
        if self._storage is None:
            self._storage = STORAGE_REGISTRY[self._storage_key]()
        return self._storage


@lru_cache
def get_provider_manager() -> ProviderManager:
    return ProviderManager()


def get_llm_for_model(model: str | None) -> LLMProvider:
    """Resolve an explicit model override to the provider chain that actually
    owns it. Falls back to the default chain (which will pass `model` to
    whichever provider is primary) for an empty/unrecognized override."""
    if not model:
        return get_provider_manager().get_llm()
    provider_key = MODEL_TO_PROVIDER_KEY.get(model)
    if provider_key is None:
        return get_provider_manager().get_llm()
    return LLM_REGISTRY[provider_key]()
