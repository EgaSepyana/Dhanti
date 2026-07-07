import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # csv, xlsx, xls, pdf
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="uploaded", server_default="uploaded")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ----- Pydantic schemas -----


class FileRead(BaseModel):
    model_config = {"from_attributes": True, "populate_by_name": True}

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    type: str
    size_bytes: int | None
    status: str
    metadata_: dict = Field(default_factory=dict, serialization_alias="metadata")
    created_at: datetime


class FileUploadResponse(BaseModel):
    file_id: uuid.UUID
    status: str
