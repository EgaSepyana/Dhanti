import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.document import Document, DocumentDetail, DocumentRead

router = APIRouter(prefix="/api/workspaces/{workspace_id}/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
async def list_documents(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.workspace_id == workspace_id))
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    workspace_id: uuid.UUID, document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    document = await db.get(Document, document_id)
    if document is None or document.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
