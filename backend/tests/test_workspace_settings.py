import httpx
from httpx import ASGITransport

from app.main import app


async def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_workspace_settings_persist_language_and_model_preferences():
    async with await _client() as client:
        create_res = await client.post("/api/workspaces", json={"name": "Settings test"})
        workspace = create_res.json()

        update_res = await client.put(
            f"/api/workspaces/{workspace['id']}",
            json={"settings": {"language": "Spanish", "model": "qwen/qwen3-32b"}},
        )
        assert update_res.status_code == 200
        assert update_res.json()["settings"] == {"language": "Spanish", "model": "qwen/qwen3-32b"}

        get_res = await client.get(f"/api/workspaces/{workspace['id']}")
        assert get_res.json()["settings"] == {"language": "Spanish", "model": "qwen/qwen3-32b"}
