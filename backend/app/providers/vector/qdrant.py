import asyncio

from qdrant_client import QdrantClient, models

from app.core.config import get_settings
from app.providers.base import VectorProvider


class QdrantProvider(VectorProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self._client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        self._collection = settings.qdrant_collection

    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None:
        await asyncio.to_thread(
            self._client.upsert,
            collection_name=self._collection,
            points=[models.PointStruct(id=id, vector=vector, payload=metadata)],
        )

    async def search(self, vector: list[float], top_k: int = 5) -> list[dict]:
        result = await asyncio.to_thread(
            self._client.query_points,
            collection_name=self._collection,
            query=vector,
            limit=top_k,
        )
        return [{"id": p.id, "score": p.score, "payload": p.payload} for p in result.points]
