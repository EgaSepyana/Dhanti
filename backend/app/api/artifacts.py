import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.artifact import (
    ArtifactCreate,
    ArtifactRead,
    ArtifactUpdate,
    ArtifactVersionSummary,
)
from app.services import artifact_service
from app.services.artifact_service import ArtifactValidationError
from app.services.workspace_service import get_workspace

router = APIRouter(tags=["artifacts"])


@router.post(
    "/api/workspaces/{workspace_id}/artifacts", response_model=ArtifactRead, status_code=201
)
async def create_artifact(
    workspace_id: uuid.UUID, data: ArtifactCreate, db: AsyncSession = Depends(get_db)
):
    workspace = await get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        return await artifact_service.create_artifact(db, workspace_id, data)
    except ArtifactValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/artifacts", response_model=list[ArtifactRead])
async def list_artifacts(
    workspace_id: uuid.UUID, type: str | None = None, db: AsyncSession = Depends(get_db)
):
    return await artifact_service.list_artifacts(db, workspace_id, type)


@router.get("/api/artifacts/{artifact_id}", response_model=ArtifactRead)
async def get_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    artifact = await artifact_service.get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.put("/api/artifacts/{artifact_id}", response_model=ArtifactRead)
async def update_artifact(
    artifact_id: uuid.UUID, data: ArtifactUpdate, db: AsyncSession = Depends(get_db)
):
    artifact = await artifact_service.get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        return await artifact_service.update_artifact(db, artifact, data)
    except ArtifactValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/artifacts/{artifact_id}/versions", response_model=list[ArtifactVersionSummary])
async def get_artifact_versions(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    artifact = await artifact_service.get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return await artifact_service.get_version_history(db, artifact_id)


@router.get("/api/artifacts/{artifact_id}/lineage", response_model=list[ArtifactRead])
async def get_artifact_lineage(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    artifact = await artifact_service.get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return await artifact_service.get_lineage(db, artifact_id)
