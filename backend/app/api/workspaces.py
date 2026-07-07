import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.artifact import Artifact
from app.models.dataset import Dataset, DatasetRead
from app.models.document import Document, DocumentRead
from app.models.file import File, FileRead
from app.models.workspace import Workspace, WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.services import workspace_service

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class WorkspaceDetail(WorkspaceRead):
    files: list[FileRead] = []
    datasets: list[DatasetRead] = []
    documents: list[DocumentRead] = []
    artifacts: list[dict] = []


async def _get_workspace_or_404(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace:
    workspace = await workspace_service.get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("", response_model=WorkspaceRead, status_code=201)
async def create_workspace(data: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    return await workspace_service.create_workspace(db, data)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    return await workspace_service.list_workspaces(db)


@router.get("/{workspace_id}", response_model=WorkspaceDetail)
async def get_workspace(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    workspace = await _get_workspace_or_404(db, workspace_id)

    files = (
        (await db.execute(select(File).where(File.workspace_id == workspace_id))).scalars().all()
    )
    datasets = (
        (await db.execute(select(Dataset).where(Dataset.workspace_id == workspace_id)))
        .scalars()
        .all()
    )
    documents = (
        (await db.execute(select(Document).where(Document.workspace_id == workspace_id)))
        .scalars()
        .all()
    )
    artifacts = (
        (await db.execute(select(Artifact).where(Artifact.workspace_id == workspace_id)))
        .scalars()
        .all()
    )

    return WorkspaceDetail(
        **WorkspaceRead.model_validate(workspace).model_dump(),
        files=[FileRead.model_validate(f) for f in files],
        datasets=[DatasetRead.model_validate(d) for d in datasets],
        documents=[DocumentRead.model_validate(d) for d in documents],
        artifacts=[
            {"id": str(a.id), "type": a.type, "title": a.title, "version": a.version}
            for a in artifacts
        ],
    )


@router.put("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: uuid.UUID, data: WorkspaceUpdate, db: AsyncSession = Depends(get_db)
):
    workspace = await _get_workspace_or_404(db, workspace_id)
    return await workspace_service.update_workspace(db, workspace, data)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    workspace = await _get_workspace_or_404(db, workspace_id)
    await workspace_service.delete_workspace(db, workspace)
