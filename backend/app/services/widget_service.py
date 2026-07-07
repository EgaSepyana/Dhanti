import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.widget import Widget, WidgetCreate, WidgetExecutionResult, WidgetUpdate
from app.services import duckdb_service
from app.services.duckdb_service import WidgetQueryError

__all__ = ["WidgetQueryError"]


async def create_widget(db: AsyncSession, workspace_id: uuid.UUID, data: WidgetCreate) -> Widget:
    duckdb_service.validate_widget_sql(data.query)

    widget = Widget(
        workspace_id=workspace_id,
        dataset_id=data.dataset_id,
        name=data.name,
        title=data.title,
        type=data.type,
        query=data.query,
        config=data.config,
    )
    db.add(widget)
    await db.commit()
    await db.refresh(widget)
    return widget


async def get_widget(db: AsyncSession, widget_id: uuid.UUID) -> Widget | None:
    return await db.get(Widget, widget_id)


async def list_widgets(
    db: AsyncSession, workspace_id: uuid.UUID, dataset_id: uuid.UUID | None = None
) -> list[Widget]:
    stmt = select(Widget).where(Widget.workspace_id == workspace_id).order_by(Widget.created_at.asc())
    if dataset_id:
        stmt = stmt.where(Widget.dataset_id == dataset_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_widget(db: AsyncSession, widget: Widget, data: WidgetUpdate) -> Widget:
    if data.query is not None:
        duckdb_service.validate_widget_sql(data.query)
        widget.query = data.query
    if data.title is not None:
        widget.title = data.title
    if data.config is not None:
        widget.config = data.config
    await db.commit()
    await db.refresh(widget)
    return widget


async def delete_widget(db: AsyncSession, widget: Widget) -> None:
    await db.delete(widget)
    await db.commit()


async def execute_widget(db: AsyncSession, widget: Widget) -> WidgetExecutionResult:
    dataset = await db.get(Dataset, widget.dataset_id)
    if dataset is None:
        raise WidgetQueryError(f"Dataset '{widget.dataset_id}' not found")

    columns, rows, row_count = await duckdb_service.execute_widget_query(dataset, widget.query)
    return WidgetExecutionResult(columns=columns, rows=rows, row_count=row_count)
