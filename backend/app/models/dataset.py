import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    columns: Mapped[list] = mapped_column(JSONB, nullable=False)  # [{name, type, stats}]
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    data_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ----- Pydantic schemas -----


class DatasetRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    workspace_id: uuid.UUID
    file_id: uuid.UUID
    name: str
    columns: list
    row_count: int | None
    profile: dict
    created_at: datetime


class DatasetDetail(DatasetRead):
    sample_rows: list[dict] = []
