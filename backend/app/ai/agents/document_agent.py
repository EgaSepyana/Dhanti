import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.schemas import AgentResult, AgentTask
from app.ai.tools import document_tools
from app.models.document import Document


class DocumentAgent(BaseAgent):
    """Embeds and indexes a parsed document's chunks so it's ready for RAG. Output: text artifact."""

    name = "document_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        document_id = task.input.get("document_id")
        if not document_id:
            return self._error(task, "document_agent requires 'document_id' in input")

        document = await db.get(Document, uuid.UUID(str(document_id)))
        if document is None:
            return self._error(task, f"Document '{document_id}' not found")

        chunks = document.chunks or []
        unindexed = [c for c in chunks if not c.get("embedding_id")]

        if unindexed:
            vectors = await document_tools.embed_chunks(unindexed)
            indexed = await document_tools.index_chunks(
                task.workspace_id, str(document.id), unindexed, vectors
            )
            indexed_by_page_text = {(c["page"], c["text"]): c for c in indexed}
            chunks = [
                indexed_by_page_text.get((c["page"], c["text"]), c) for c in chunks
            ]
            document.chunks = chunks
            await db.commit()

        preview = "\n\n".join(c["text"] for c in chunks[:10])
        output = {
            "text": preview,
            "format": "plain",
            "page_count": document.page_count,
            "chunks_indexed": len(chunks),
        }

        return self._success(
            task, output, artifact_type="text", metadata={"document_id": str(document.id)}
        )
