import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace, WorkspaceCreate, WorkspaceUpdate


async def create_workspace(db: AsyncSession, data: WorkspaceCreate) -> Workspace:
    workspace = Workspace(name=data.name, description=data.description)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def list_workspaces(db: AsyncSession) -> list[Workspace]:
    result = await db.execute(select(Workspace).order_by(Workspace.created_at.desc()))
    return list(result.scalars().all())


async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace | None:
    return await db.get(Workspace, workspace_id)


async def update_workspace(
    db: AsyncSession, workspace: Workspace, data: WorkspaceUpdate
) -> Workspace:
    if data.name is not None:
        workspace.name = data.name
    if data.description is not None:
        workspace.description = data.description
    if data.settings is not None:
        workspace.settings = data.settings
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def delete_workspace(db: AsyncSession, workspace: Workspace) -> None:
    await db.delete(workspace)
    await db.commit()
