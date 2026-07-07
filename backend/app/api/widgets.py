import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.widget import (
    WidgetCreate,
    WidgetExecutionResult,
    WidgetRead,
    WidgetUpdate,
)
from app.services import widget_service
from app.services.widget_service import WidgetQueryError
from app.services.workspace_service import get_workspace

router = APIRouter(tags=["widgets"])


@router.post("/api/workspaces/{workspace_id}/widgets", response_model=WidgetRead, status_code=201)
async def create_widget(
    workspace_id: uuid.UUID, data: WidgetCreate, db: AsyncSession = Depends(get_db)
):
    workspace = await get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        return await widget_service.create_widget(db, workspace_id, data)
    except WidgetQueryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/workspaces/{workspace_id}/widgets", response_model=list[WidgetRead])
async def list_widgets(
    workspace_id: uuid.UUID, dataset_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)
):
    return await widget_service.list_widgets(db, workspace_id, dataset_id)


@router.get("/api/widgets/{widget_id}", response_model=WidgetRead)
async def get_widget(widget_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    widget = await widget_service.get_widget(db, widget_id)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget


@router.put("/api/widgets/{widget_id}", response_model=WidgetRead)
async def update_widget(widget_id: uuid.UUID, data: WidgetUpdate, db: AsyncSession = Depends(get_db)):
    widget = await widget_service.get_widget(db, widget_id)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    try:
        return await widget_service.update_widget(db, widget, data)
    except WidgetQueryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/api/widgets/{widget_id}", status_code=204)
async def delete_widget(widget_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    widget = await widget_service.get_widget(db, widget_id)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    await widget_service.delete_widget(db, widget)


@router.post("/api/widgets/{widget_id}/handler", response_model=WidgetExecutionResult)
async def execute_widget(widget_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """The endpoint a rendered dashboard calls (via the Bridge API) to get a
    widget's live data: runs its stored query fresh against the dataset every
    time, rather than serving a snapshot taken at generation time."""
    widget = await widget_service.get_widget(db, widget_id)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    try:
        return await widget_service.execute_widget(db, widget)
    except WidgetQueryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
