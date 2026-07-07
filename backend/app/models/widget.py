import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

WidgetType = Literal["table", "chart", "metric"]


class Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # table, chart, metric
    query: Mapped[str] = mapped_column(Text, nullable=False)  # DuckDB SQL, validated read-only at write time
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ----- Pydantic schemas -----


class WidgetCreate(BaseModel):
    dataset_id: uuid.UUID
    name: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    type: WidgetType
    query: str = Field(min_length=1)
    config: dict = Field(default_factory=dict)


class WidgetUpdate(BaseModel):
    title: str | None = None
    query: str | None = None
    config: dict | None = None


class WidgetRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    title: str
    type: str
    query: str
    config: dict
    created_at: datetime
    updated_at: datetime


class WidgetExecutionResult(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int
