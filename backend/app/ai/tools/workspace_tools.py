import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.registry import register_tool
from app.models.artifact import Artifact
from app.models.dataset import Dataset
from app.models.document import Document
from app.models.file import File


@register_tool("list_workspace_files")
async def list_workspace_files(db: AsyncSession, workspace_id: uuid.UUID) -> list[File]:
    result = await db.execute(
        select(File).where(File.workspace_id == workspace_id).order_by(File.created_at.desc())
    )
    return list(result.scalars().all())


@register_tool("list_workspace_datasets")
async def list_workspace_datasets(db: AsyncSession, workspace_id: uuid.UUID) -> list[Dataset]:
    result = await db.execute(
        select(Dataset)
        .where(Dataset.workspace_id == workspace_id)
        .order_by(Dataset.created_at.desc())
    )
    return list(result.scalars().all())


@register_tool("list_workspace_documents")
async def list_workspace_documents(db: AsyncSession, workspace_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


@register_tool("list_workspace_artifacts")
async def list_workspace_artifacts(db: AsyncSession, workspace_id: uuid.UUID) -> list[Artifact]:
    result = await db.execute(
        select(Artifact)
        .where(Artifact.workspace_id == workspace_id)
        .order_by(Artifact.created_at.desc())
    )
    return list(result.scalars().all())
