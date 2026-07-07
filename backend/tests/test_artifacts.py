import uuid

import httpx
from httpx import ASGITransport

from app.core.database import async_session_factory
from app.main import app
from app.models.workspace import Workspace

DATASET_CONTENT = {
    "columns": [{"name": "revenue", "type": "float"}],
    "rows": [{"revenue": 100.0}],
    "schema": {"row_count": 1, "column_count": 1},
    "stats": {},
}


async def _create_workspace() -> uuid.UUID:
    async with async_session_factory() as db:
        workspace = Workspace(name=f"artifact-test-{uuid.uuid4().hex[:8]}")
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)
        return workspace.id


async def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_create_artifact_returns_version_1():
    workspace_id = await _create_workspace()
    async with await _client() as client:
        res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={"type": "dataset", "title": "Sales Data", "content": DATASET_CONTENT},
        )
    assert res.status_code == 201
    body = res.json()
    assert body["version"] == 1
    assert body["parent_id"] is None
    assert body["title"] == "Sales Data"


async def test_dashboard_artifacts_default_to_executable():
    """Canvas (Phase 6/7) refuses to render an artifact whose permissions.execute
    isn't true, so dashboard artifacts (HTML code — see code_generation_agent)
    must get it by default — while non-runnable types (text/dataset/
    visualization) must not."""
    workspace_id = await _create_workspace()
    dashboard_content = {
        "runtime": "html",
        "entry": "<html></html>",
        "assets": [],
        "permissions": {},
    }

    async with await _client() as client:
        dashboard_res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={"type": "dashboard", "title": "Dash", "content": dashboard_content},
        )
        dataset_res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={"type": "dataset", "title": "Data", "content": DATASET_CONTENT},
        )

    assert dashboard_res.json()["permissions"]["execute"] is True
    assert dataset_res.json()["permissions"]["execute"] is False


async def test_create_artifact_with_invalid_content_rejected():
    workspace_id = await _create_workspace()
    async with await _client() as client:
        res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={"type": "dataset", "title": "Bad", "content": {"columns": []}},
        )
    assert res.status_code == 422
    assert "missing required keys" in res.json()["detail"]


async def test_update_artifact_creates_new_version_old_still_accessible():
    workspace_id = await _create_workspace()
    async with await _client() as client:
        create_res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={"type": "dataset", "title": "Sales Data", "content": DATASET_CONTENT},
        )
        v1 = create_res.json()

        updated_content = {**DATASET_CONTENT, "rows": [{"revenue": 200.0}]}
        update_res = await client.put(
            f"/api/artifacts/{v1['id']}",
            json={"title": "Sales Data v2", "content": updated_content},
        )
        assert update_res.status_code == 200
        v2 = update_res.json()

        assert v2["version"] == 2
        assert v2["parent_id"] == v1["id"]
        assert v2["id"] != v1["id"]

        # v1 must still be independently fetchable
        v1_refetch = await client.get(f"/api/artifacts/{v1['id']}")
        assert v1_refetch.status_code == 200
        assert v1_refetch.json()["version"] == 1
        assert v1_refetch.json()["content"] == DATASET_CONTENT

        versions_res = await client.get(f"/api/artifacts/{v1['id']}/versions")
        versions = versions_res.json()
        assert [v["version"] for v in versions] == [1, 2]


async def test_list_artifacts_returns_only_latest_version():
    workspace_id = await _create_workspace()
    async with await _client() as client:
        create_res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={"type": "dataset", "title": "Sales Data", "content": DATASET_CONTENT},
        )
        v1 = create_res.json()
        await client.put(
            f"/api/artifacts/{v1['id']}",
            json={"content": DATASET_CONTENT},
        )

        list_res = await client.get(f"/api/workspaces/{workspace_id}/artifacts")
        artifacts = list_res.json()

    assert len(artifacts) == 1
    assert artifacts[0]["version"] == 2


async def test_lineage_traces_dashboard_back_to_dataset():
    workspace_id = await _create_workspace()
    async with await _client() as client:
        dataset_res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={"type": "dataset", "title": "Sales Data", "content": DATASET_CONTENT},
        )
        dataset = dataset_res.json()

        viz_content = {"library": "echarts", "config": {}, "data_source": dataset["id"]}
        viz_res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={
                "type": "visualization",
                "title": "Revenue Chart",
                "content": viz_content,
                "relations": [{"type": "derived", "target_id": dataset["id"]}],
            },
        )
        viz = viz_res.json()

        dashboard_content = {
            "runtime": "html",
            "entry": "<html></html>",
            "assets": [],
            "permissions": {},
        }
        dashboard_res = await client.post(
            f"/api/workspaces/{workspace_id}/artifacts",
            json={
                "type": "dashboard",
                "title": "Sales Dashboard",
                "content": dashboard_content,
                "relations": [
                    {"type": "derived", "target_id": dataset["id"]},
                    {"type": "derived", "target_id": viz["id"]},
                ],
            },
        )
        dashboard = dashboard_res.json()

        lineage_res = await client.get(f"/api/artifacts/{dashboard['id']}/lineage")

    lineage_ids = {a["id"] for a in lineage_res.json()}
    assert dataset["id"] in lineage_ids
    assert viz["id"] in lineage_ids
