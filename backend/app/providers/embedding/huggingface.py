import httpx

from app.core.config import get_settings
from app.providers.base import EmbeddingProvider


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self._url = (
            f"{settings.hf_inference_url}/models/{settings.hf_embedding_model}"
            "/pipeline/feature-extraction"
        )
        self._api_key = settings.hf_api_key

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"inputs": texts, "options": {"wait_for_model": True}},
            )
            response.raise_for_status()
            return response.json()
