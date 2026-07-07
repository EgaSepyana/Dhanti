import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.services.artifact_service import (
    ArtifactValidationError,
    default_permissions_for_type,
    validate_content,
)

__all__ = ["ArtifactValidationError", "validate_content", "generate_artifact"]


async def generate_artifact(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    artifact_type: str,
    title: str,
    content: dict,
    description: str | None = None,
    metadata: dict | None = None,
    relations: list | None = None,
) -> Artifact:
    """Orchestrator-facing artifact creation: agents always produce version 1
    (a fresh artifact per pipeline run). Editing existing artifacts through
    the API goes through artifact_service.update_artifact instead."""
    validate_content(artifact_type, content)

    artifact = Artifact(
        workspace_id=uuid.UUID(str(workspace_id)),
        type=artifact_type,
        title=title,
        description=description,
        content=content,
        version=1,
        relations=relations or [],
        permissions=default_permissions_for_type(artifact_type),
        metadata_=metadata or {},
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact
