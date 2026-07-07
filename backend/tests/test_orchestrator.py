import io
import uuid

import pandas as pd
from pypdf.generic import DictionaryObject, NameObject, StreamObject
from pypdf import PdfWriter
from sqlalchemy import select

from app.ai.orchestrator import run_orchestrator
from app.core.database import async_session_factory
from app.models.artifact import Artifact
from app.models.file import File
from app.models.workspace import Workspace
from app.services import file_service


def _make_xlsx_bytes() -> bytes:
    df = pd.DataFrame(
        {
            "product": ["Widget", "Gadget", "Gizmo", "Widget", "Gadget", "Gizmo"],
            "region": ["East", "East", "West", "West", "East", "West"],
            "revenue": [1200.5, 980.0, 1500.75, 1100.25, 875.0, 2000.0],
            "units": [12, 9, 15, 11, 8, 20],
        }
    )
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def _make_pdf_bytes(text_lines: list[str]) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    content_parts = ["BT", "/F1 14 Tf", "72 720 Td"]
    for line in text_lines:
        safe = line.replace("(", "\\(").replace(")", "\\)")
        content_parts.append(f"({safe}) Tj")
        content_parts.append("0 -20 Td")
    content_parts.append("ET")

    stream_obj = StreamObject()
    stream_obj.set_data(" ".join(content_parts).encode())
    contents_ref = writer._add_object(stream_obj)

    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_ref = writer._add_object(font)

    font_dict = DictionaryObject()
    font_dict[NameObject("/F1")] = font_ref
    resources = DictionaryObject()
    resources[NameObject("/Font")] = font_dict

    page[NameObject("/Contents")] = contents_ref
    page[NameObject("/Resources")] = resources

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


async def _upload_and_parse(db, workspace_id: uuid.UUID, filename: str, content: bytes, ext: str) -> uuid.UUID:
    file_id = uuid.uuid4()
    storage_path = f"{workspace_id}/{file_id}/{filename}"
    file_row = File(
        id=file_id,
        workspace_id=workspace_id,
        name=filename,
        type=ext,
        size_bytes=len(content),
        storage_path=storage_path,
        status="uploaded",
    )
    db.add(file_row)
    await db.commit()

    await file_service.upload_bytes(storage_path, content, file_service.CONTENT_TYPES[ext])
    await file_service.process_file(file_id, content, ext)
    return file_id


async def _setup_workspace_with_data() -> uuid.UUID:
    async with async_session_factory() as db:
        workspace = Workspace(name=f"orchestrator-test-{uuid.uuid4().hex[:8]}")
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)

        await _upload_and_parse(db, workspace.id, "sales.xlsx", _make_xlsx_bytes(), "xlsx")
        await _upload_and_parse(
            db,
            workspace.id,
            "report.pdf",
            _make_pdf_bytes(
                [
                    "Quarterly Report",
                    "Revenue grew steadily across all regions this quarter.",
                    "The West region outperformed expectations.",
                ]
            ),
            "pdf",
        )

        return workspace.id


def _agents_in_plan(result: dict) -> list[str]:
    return [step["agent"] for step in result["plan"]]


async def test_data_analysis_intent_and_plan():
    workspace_id = await _setup_workspace_with_data()

    async with async_session_factory() as db:
        result = await run_orchestrator(db, workspace_id, "Analyze this dataset")

    assert result["intent_result"]["intent"] == "data_analysis"
    agents = _agents_in_plan(result)
    assert "dataset_agent" in agents
    assert "insight_agent" in agents

    for step_id, step_result in result["step_results"].items():
        assert step_result["status"] == "success", f"{step_id} failed: {step_result}"


async def test_summarize_pdf_intent_and_plan():
    workspace_id = await _setup_workspace_with_data()

    async with async_session_factory() as db:
        result = await run_orchestrator(db, workspace_id, "Summarize this PDF")

    assert result["intent_result"]["intent"] in ("summarize", "document_analysis")
    assert "document_agent" in _agents_in_plan(result)

    for step_id, step_result in result["step_results"].items():
        assert step_result["status"] == "success", f"{step_id} failed: {step_result}"


async def test_dashboard_generation_full_pipeline():
    workspace_id = await _setup_workspace_with_data()

    async with async_session_factory() as db:
        result = await run_orchestrator(db, workspace_id, "Create a dashboard from sales.xlsx")

    assert result["intent_result"]["intent"] == "dashboard_generation"
    agents = _agents_in_plan(result)
    assert agents == [
        "file_agent",
        "dataset_agent",
        "insight_agent",
        "visualization_agent",
        "widget_planner_agent",
        "text_to_sql_agent",
        "dashboard_agent",
        "code_generation_agent",
    ]

    for step_id, step_result in result["step_results"].items():
        assert step_result["status"] == "success", f"{step_id} failed: {step_result}"

    artifact_types = {a["type"] for a in result["artifacts"]}
    assert {"dataset", "visualization", "dashboard"}.issubset(artifact_types)

    async with async_session_factory() as db:
        for artifact_summary in result["artifacts"]:
            artifact = await db.get(Artifact, uuid.UUID(artifact_summary["id"]))
            assert artifact is not None
            assert artifact.version == 1
            assert artifact.workspace_id == workspace_id


async def test_dashboard_revision_creates_new_version_of_existing_dashboard():
    workspace_id = await _setup_workspace_with_data()

    async with async_session_factory() as db:
        first_run = await run_orchestrator(db, workspace_id, "Create a dashboard from sales.xlsx")
    dashboard_before = next(a for a in first_run["artifacts"] if a["type"] == "dashboard")

    async with async_session_factory() as db:
        revision_run = await run_orchestrator(
            db, workspace_id, "Change the bar chart to a line chart"
        )

    assert revision_run["intent_result"]["intent"] == "dashboard_revision"
    assert _agents_in_plan(revision_run) == ["dashboard_revision_agent"]
    for step_id, step_result in revision_run["step_results"].items():
        assert step_result["status"] == "success", f"{step_id} failed: {step_result}"

    dashboard_after = next(a for a in revision_run["artifacts"] if a["type"] == "dashboard")
    assert dashboard_after["id"] != dashboard_before["id"]
    assert dashboard_after["version"] == dashboard_before["version"] + 1

    async with async_session_factory() as db:
        original = await db.get(Artifact, uuid.UUID(dashboard_before["id"]))
        revised = await db.get(Artifact, uuid.UUID(dashboard_after["id"]))
        assert revised.parent_id == uuid.UUID(dashboard_before["id"])
        # "Dashboard" is now code (see code_generation_agent) — there's no
        # JSON widget list to inspect anymore, just an HTML document. Assert
        # the revision actually changed the code and mentions a line chart,
        # without pinning down the LLM's exact HTML/JS structure.
        assert revised.content["entry"] != original.content["entry"]
        assert "line" in revised.content["entry"].lower()


async def test_agent_error_produces_graceful_partial_result():
    workspace_id = await _setup_workspace_with_data()

    async with async_session_factory() as db:
        result = await run_orchestrator(db, workspace_id, "Analyze this dataset")
        # Force one step to reference a nonexistent dataset to simulate a downstream
        # failure. The LLM-proposed plan may legitimately prepend extra agents (e.g.
        # file_agent) before the dataset consumers, so target the first step that
        # actually consumes a dataset_id rather than assuming it's plan[0].
        broken_plan = result["plan"]
        broken_step = next(step for step in broken_plan if "dataset_id" in step["input"])
        broken_step["input"]["dataset_id"] = str(uuid.uuid4())

        from app.ai.orchestrator import _node_execute_agents

        state = {
            "workspace_id": str(workspace_id),
            "prompt": "Analyze this dataset",
            "db": db,
            "plan": broken_plan,
            "context": result["context"],
            "intent_result": result["intent_result"],
            "step_results": {},
            "artifacts": [],
        }
        outcome = await _node_execute_agents(state)

    assert outcome["step_results"][broken_step["step_id"]]["status"] == "error"
    # The pipeline must not raise/abort — remaining independent steps still get a result.
    assert len(outcome["step_results"]) == len(broken_plan)
