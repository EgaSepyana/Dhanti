import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.artifact import Artifact, ArtifactCreate, ArtifactUpdate

ChildArtifact = aliased(Artifact)

REQUIRED_KEYS: dict[str, set[str]] = {
    "text": {"text", "format"},
    "dataset": {"columns", "rows", "schema", "stats"},
    "visualization": {"library", "config", "data_source"},
    # "dashboard" IS code generation: content is a self-contained HTML+CSS+JS
    # document (see code_generation_agent), not a JSON widget/layout config —
    # there is no separate JSON dashboard schema anymore.
    "dashboard": {"runtime", "entry", "assets", "permissions"},
    "workflow": {"steps", "dependencies", "execution_mode"},
}

# Types rendered inside the Canvas sandbox (Phase 6/7). Everything else
# (text, dataset, visualization) is rendered directly by the parent app and
# has no business executing code, so it stays non-executable.
CANVAS_RUNNABLE_TYPES = {"dashboard"}


class ArtifactValidationError(Exception):
    pass


def default_permissions_for_type(artifact_type: str) -> dict:
    return {"read": True, "write": True, "execute": artifact_type in CANVAS_RUNNABLE_TYPES}


def validate_content(artifact_type: str, content: dict) -> None:
    required = REQUIRED_KEYS.get(artifact_type)
    if required is None:
        raise ArtifactValidationError(f"Unknown artifact type '{artifact_type}'")
    missing = required - content.keys()
    if missing:
        raise ArtifactValidationError(
            f"Artifact type '{artifact_type}' missing required keys: {sorted(missing)}"
        )


async def create_artifact(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    data: ArtifactCreate,
    metadata: dict | None = None,
) -> Artifact:
    validate_content(data.type, data.content)

    artifact = Artifact(
        workspace_id=uuid.UUID(str(workspace_id)),
        type=data.type,
        title=data.title,
        description=data.description,
        content=data.content,
        version=1,
        relations=[r.model_dump(mode="json") for r in data.relations],
        permissions=default_permissions_for_type(data.type),
        metadata_=metadata or {},
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


async def get_artifact(db: AsyncSession, artifact_id: uuid.UUID) -> Artifact | None:
    return await db.get(Artifact, artifact_id)


async def list_artifacts(
    db: AsyncSession, workspace_id: uuid.UUID, artifact_type: str | None = None
) -> list[Artifact]:
    """Returns only the latest version of each artifact lineage — i.e. artifacts
    that no other artifact declares as its parent_id."""
    child_exists = (
        select(ChildArtifact.id).where(ChildArtifact.parent_id == Artifact.id).exists()
    )

    stmt = (
        select(Artifact)
        .where(Artifact.workspace_id == workspace_id)
        .where(~child_exists)
        .order_by(Artifact.updated_at.desc())
    )
    if artifact_type:
        stmt = stmt.where(Artifact.type == artifact_type)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_artifact(db: AsyncSession, artifact: Artifact, data: ArtifactUpdate) -> Artifact:
    """Creates a new version row; never mutates the existing row in place."""
    validate_content(artifact.type, data.content)

    new_version = Artifact(
        workspace_id=artifact.workspace_id,
        type=artifact.type,
        title=data.title if data.title is not None else artifact.title,
        description=data.description if data.description is not None else artifact.description,
        content=data.content,
        version=artifact.version + 1,
        parent_id=artifact.id,
        permissions=artifact.permissions,
        relations=(
            [r.model_dump(mode="json") for r in data.relations]
            if data.relations is not None
            else artifact.relations
        ),
        metadata_=artifact.metadata_,
    )
    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)
    return new_version


async def get_version_history(db: AsyncSession, artifact_id: uuid.UUID) -> list[Artifact]:
    """Full version chain for the lineage containing artifact_id, oldest first."""
    current = await db.get(Artifact, artifact_id)
    if current is None:
        return []

    root = current
    while root.parent_id is not None:
        parent = await db.get(Artifact, root.parent_id)
        if parent is None:
            break
        root = parent

    chain = [root]
    node = root
    while True:
        child = (
            await db.execute(select(Artifact).where(Artifact.parent_id == node.id))
        ).scalar_one_or_none()
        if child is None:
            break
        chain.append(child)
        node = child

    return chain


async def get_lineage(db: AsyncSession, artifact_id: uuid.UUID) -> list[Artifact]:
    """Walks relations (derived/depends_on/visualizes/extends) backward to
    build the artifact's ancestry, e.g. Dashboard -> Visualization -> Dataset."""
    visited: set[uuid.UUID] = {artifact_id}
    ancestors: list[Artifact] = []
    queue: list[uuid.UUID] = []

    start = await db.get(Artifact, artifact_id)
    if start is None:
        return []
    queue.extend(_relation_target_ids(start))

    while queue:
        target_id = queue.pop(0)
        if target_id in visited:
            continue
        visited.add(target_id)

        artifact = await db.get(Artifact, target_id)
        if artifact is None:
            continue
        ancestors.append(artifact)
        queue.extend(_relation_target_ids(artifact))

    return ancestors


def _relation_target_ids(artifact: Artifact) -> list[uuid.UUID]:
    ids = []
    for relation in artifact.relations:
        target = relation.get("target_id")
        if target:
            ids.append(target if isinstance(target, uuid.UUID) else uuid.UUID(target))
    return ids
