import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import WorkspaceContext
from app.core.config import get_settings
from app.models.artifact import Artifact
from app.models.dataset import Dataset
from app.models.document import Document
from app.models.file import File
from app.providers.manager import get_provider_manager
from app.services import memory_service

MAX_ITEMS_PER_CATEGORY = 20


async def build_context(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    prompt: str,
    recent_messages: list[dict] | None = None,
) -> WorkspaceContext:
    """Gathers workspace context for intent analysis, planning, and agents:
    recent conversation, file metadata, dataset schemas, document summaries,
    existing artifacts, and vector-search-relevant document chunks."""
    ws_id = uuid.UUID(str(workspace_id))

    files = (
        await db.execute(
            select(File).where(File.workspace_id == ws_id).order_by(File.created_at.desc())
        )
    ).scalars().all()
    datasets = (
        await db.execute(
            select(Dataset).where(Dataset.workspace_id == ws_id).order_by(Dataset.created_at.desc())
        )
    ).scalars().all()
    documents = (
        await db.execute(
            select(Document).where(Document.workspace_id == ws_id).order_by(Document.created_at.desc())
        )
    ).scalars().all()
    artifacts = (
        await db.execute(
            select(Artifact).where(Artifact.workspace_id == ws_id).order_by(Artifact.created_at.desc())
        )
    ).scalars().all()

    relevant_chunks = await _search_relevant_chunks(prompt, ws_id) if documents else []
    relevant_memories = await memory_service.retrieve_relevant_memories(ws_id, prompt)

    return WorkspaceContext(
        workspace_id=str(ws_id),
        prompt=prompt,
        recent_messages=recent_messages or [],
        files=[
            {"id": str(f.id), "name": f.name, "type": f.type, "status": f.status}
            for f in files[:MAX_ITEMS_PER_CATEGORY]
        ],
        datasets=[
            {
                "id": str(d.id),
                "file_id": str(d.file_id),
                "name": d.name,
                "row_count": d.row_count,
                "columns": [c["name"] for c in d.columns],
            }
            for d in datasets[:MAX_ITEMS_PER_CATEGORY]
        ],
        documents=[
            {"id": str(d.id), "file_id": str(d.file_id), "name": d.name, "page_count": d.page_count}
            for d in documents[:MAX_ITEMS_PER_CATEGORY]
        ],
        artifacts=[
            {"id": str(a.id), "type": a.type, "title": a.title, "version": a.version}
            for a in artifacts[:MAX_ITEMS_PER_CATEGORY]
        ],
        relevant_chunks=relevant_chunks,
        relevant_memories=relevant_memories,
    )


async def _search_relevant_chunks(prompt: str, workspace_id: uuid.UUID) -> list[dict]:
    try:
        embedder = get_provider_manager().get_embedding()
        vector = (await embedder.embed([prompt]))[0]
        results = await get_provider_manager().get_vector().search(vector, top_k=5)
    except Exception:
        return []
    return [
        r
        for r in results
        if r["payload"].get("workspace_id") == str(workspace_id)
        and r["payload"].get("type") == "chunk"
    ]


def summarize_context(context: WorkspaceContext) -> str:
    """Compact text summary for LLM prompts, trimmed to the configured token budget."""
    lines: list[str] = []

    if context.recent_messages:
        lines.append(
            "Recent conversation:\n"
            + "\n".join(
                f"{m['role']}: {m['content'][:300]}" for m in context.recent_messages
            )
        )
    if context.relevant_memories:
        lines.append(
            "Known context/preferences: "
            + " | ".join(m["payload"].get("text", "") for m in context.relevant_memories)
        )
    if context.files:
        lines.append(
            "Files: " + ", ".join(f"{f['name']} ({f['status']})" for f in context.files)
        )
    if context.datasets:
        lines.append(
            "Datasets: "
            + ", ".join(f"{d['name']} [{', '.join(d['columns'][:8])}]" for d in context.datasets)
        )
    if context.documents:
        lines.append(
            "Documents: "
            + ", ".join(f"{d['name']} ({d['page_count']} pages)" for d in context.documents)
        )
    if context.artifacts:
        lines.append(
            "Existing artifacts: "
            + ", ".join(f"{a['type']}:{a['title']}" for a in context.artifacts)
        )
    if context.relevant_chunks:
        lines.append(
            "Relevant document excerpts: "
            + " | ".join(c["payload"].get("text", "")[:200] for c in context.relevant_chunks)
        )

    summary = "\n".join(lines) if lines else "Workspace is empty (no files uploaded yet)."

    settings = get_settings()
    max_chars = settings.ai_context_token_budget * 4  # crude ~4 chars/token budget
    return summary[:max_chars]
