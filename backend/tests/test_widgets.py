import io
import uuid

import httpx
import pandas as pd
from httpx import ASGITransport

from app.core.database import async_session_factory
from app.main import app
from app.models.dataset import Dataset
from app.models.file import File
from app.models.workspace import Workspace
from app.services import file_service


async def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _setup_dataset() -> tuple[uuid.UUID, uuid.UUID]:
    """Real workspace + file + dataset with actual parquet data in storage,
    so widget execution exercises the real DuckDB/Supabase round trip."""
    df = pd.DataFrame(
        {
            "region": ["East", "West", "East", "West"],
            "revenue": [100.0, 200.0, 150.0, 250.0],
        }
    )
    async with async_session_factory() as db:
        workspace = Workspace(name=f"widget-test-{uuid.uuid4().hex[:8]}")
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)

        file_id = uuid.uuid4()
        data_path = f"{workspace.id}/{file_id}/data.parquet"
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        await file_service.upload_bytes(data_path, buffer.getvalue(), "application/octet-stream")

        file_row = File(
            id=file_id,
            workspace_id=workspace.id,
            name="sales.xlsx",
            type="xlsx",
            size_bytes=len(buffer.getvalue()),
            storage_path=f"{workspace.id}/{file_id}/sales.xlsx",
            status="parsed",
        )
        db.add(file_row)
        await db.commit()

        dataset = Dataset(
            workspace_id=workspace.id,
            file_id=file_id,
            name="sales.xlsx",
            columns=[
                {"name": "region", "type": "string", "stats": {}},
                {"name": "revenue", "type": "float", "stats": {}},
            ],
            row_count=len(df),
            profile={},
            data_path=data_path,
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)

        return workspace.id, dataset.id


async def test_create_widget_and_execute_returns_live_query_results():
    workspace_id, dataset_id = await _setup_dataset()

    async with await _client() as client:
        create_res = await client.post(
            f"/api/workspaces/{workspace_id}/widgets",
            json={
                "dataset_id": str(dataset_id),
                "name": "revenue_by_region",
                "title": "Revenue by Region",
                "type": "chart",
                "query": "SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region ORDER BY region",
                "config": {"chart_type": "bar"},
            },
        )
        assert create_res.status_code == 201
        widget = create_res.json()
        assert widget["type"] == "chart"

        exec_res = await client.post(f"/api/widgets/{widget['id']}/handler")
        assert exec_res.status_code == 200
        body = exec_res.json()
        assert body["columns"] == ["region", "total"]
        assert body["row_count"] == 2
        rows_by_region = {row["region"]: row["total"] for row in body["rows"]}
        assert rows_by_region == {"East": 250.0, "West": 450.0}


async def test_create_widget_rejects_unsafe_sql():
    workspace_id, dataset_id = await _setup_dataset()

    async with await _client() as client:
        res = await client.post(
            f"/api/workspaces/{workspace_id}/widgets",
            json={
                "dataset_id": str(dataset_id),
                "name": "malicious",
                "title": "Malicious",
                "type": "table",
                "query": "DROP TABLE dataset",
            },
        )
    assert res.status_code == 422
    assert "SELECT" in res.json()["detail"]


async def test_create_widget_rejects_file_reader_functions():
    workspace_id, dataset_id = await _setup_dataset()

    async with await _client() as client:
        res = await client.post(
            f"/api/workspaces/{workspace_id}/widgets",
            json={
                "dataset_id": str(dataset_id),
                "name": "escape",
                "title": "Escape",
                "type": "table",
                "query": "SELECT * FROM read_csv('/etc/passwd')",
            },
        )
    assert res.status_code == 422
    assert "disallowed keyword" in res.json()["detail"]


async def test_list_update_delete_widget():
    workspace_id, dataset_id = await _setup_dataset()

    async with await _client() as client:
        create_res = await client.post(
            f"/api/workspaces/{workspace_id}/widgets",
            json={
                "dataset_id": str(dataset_id),
                "name": "total_revenue",
                "title": "Total Revenue",
                "type": "metric",
                "query": "SELECT SUM(revenue) AS total FROM dataset",
            },
        )
        widget_id = create_res.json()["id"]

        list_res = await client.get(f"/api/workspaces/{workspace_id}/widgets")
        assert len(list_res.json()) == 1

        update_res = await client.put(
            f"/api/widgets/{widget_id}",
            json={"title": "Total Revenue (USD)"},
        )
        assert update_res.status_code == 200
        assert update_res.json()["title"] == "Total Revenue (USD)"

        delete_res = await client.delete(f"/api/widgets/{widget_id}")
        assert delete_res.status_code == 204

        get_res = await client.get(f"/api/widgets/{widget_id}")
        assert get_res.status_code == 404
