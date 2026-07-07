import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.schemas import AgentResult, AgentTask
from app.models.dataset import Dataset
from app.models.document import Document
from app.models.file import File


class FileAgent(BaseAgent):
    """Locates a workspace file and reports its parsed dataset/document, if any.

    Actual CSV/XLSX/PDF parsing happens at upload time (Phase 1's background
    parser); this agent's job in an AI pipeline is to resolve a file reference
    into the ids downstream agents need.
    """

    name = "file_agent"

    async def run(self, task: AgentTask, db: AsyncSession) -> AgentResult:
        file_id = task.input.get("file_id")
        if not file_id:
            return self._error(task, "file_agent requires 'file_id' in input")

        file_row = await db.get(File, uuid.UUID(str(file_id)))
        if file_row is None:
            return self._error(task, f"File '{file_id}' not found")

        output = {
            "file": {
                "id": str(file_row.id),
                "name": file_row.name,
                "type": file_row.type,
                "status": file_row.status,
            }
        }

        if file_row.status == "error":
            return self._error(task, f"File '{file_row.name}' failed to parse")
        if file_row.status in ("uploaded", "parsing"):
            return AgentResult(
                task_id=task.task_id,
                status="partial",
                output=output,
                metadata={"agent": self.name, "reason": "file still parsing"},
            )

        dataset = (
            await db.execute(select(Dataset).where(Dataset.file_id == file_row.id))
        ).scalar_one_or_none()
        if dataset:
            output["dataset_id"] = str(dataset.id)

        document = (
            await db.execute(select(Document).where(Document.file_id == file_row.id))
        ).scalar_one_or_none()
        if document:
            output["document_id"] = str(document.id)

        return self._success(task, output)
