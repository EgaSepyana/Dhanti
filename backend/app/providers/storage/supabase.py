import asyncio

from supabase import Client, create_client

from app.core.config import get_settings
from app.providers.base import StorageProvider


class SupabaseStorageProvider(StorageProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self._client: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        self._bucket = settings.supabase_bucket

    async def upload(
        self, path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        await asyncio.to_thread(
            self._client.storage.from_(self._bucket).upload,
            path,
            data,
            {"content-type": content_type, "upsert": "true"},
        )

    async def download(self, path: str) -> bytes:
        return await asyncio.to_thread(self._client.storage.from_(self._bucket).download, path)

    async def delete(self, path: str) -> None:
        await asyncio.to_thread(self._client.storage.from_(self._bucket).remove, [path])
