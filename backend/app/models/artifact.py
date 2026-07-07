import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ArtifactType = Literal["text", "dataset", "visualization", "dashboard", "workflow"]
RelationType = Literal["derived", "depends_on", "visualizes", "extends"]


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)  # text, dataset, visualization, dashboard, workflow
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True
    )
    permissions: Mapped[dict] = mapped_column(
        JSONB, default=lambda: {"read": True, "write": True, "execute": False},
        server_default='{"read":true,"write":true,"execute":false}',
    )
    relations: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ----- Pydantic schemas -----


class ArtifactRelation(BaseModel):
    type: RelationType
    target_id: uuid.UUID


class ArtifactRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    workspace_id: uuid.UUID
    type: str
    title: str
    description: str | None
    content: dict
    version: int
    parent_id: uuid.UUID | None
    permissions: dict
    relations: list
    created_at: datetime
    updated_at: datetime


class ArtifactCreate(BaseModel):
    type: ArtifactType
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    content: dict
    relations: list[ArtifactRelation] = Field(default_factory=list)


class ArtifactUpdate(BaseModel):
    """Updating an artifact creates a new version; it never mutates the row in place."""

    title: str | None = None
    description: str | None = None
    content: dict
    relations: list[ArtifactRelation] | None = None


class ArtifactVersionSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    version: int
    title: str
    created_at: datetime
