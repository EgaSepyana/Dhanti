import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.services import chat_service
from app.services.workspace_service import get_workspace

router = APIRouter(tags=["conversations"])


@router.post(
    "/api/workspaces/{workspace_id}/conversations", response_model=ConversationRead, status_code=201
)
async def create_conversation(
    workspace_id: uuid.UUID, data: ConversationCreate, db: AsyncSession = Depends(get_db)
):
    workspace = await get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return await chat_service.create_conversation(db, workspace_id, data.title)


@router.get("/api/workspaces/{workspace_id}/conversations", response_model=list[ConversationRead])
async def list_conversations(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await chat_service.list_conversations(db, workspace_id)


@router.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    conversation = await chat_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await chat_service.list_messages(db, conversation_id)
    return ConversationDetail(
        **ConversationRead.model_validate(conversation).model_dump(),
        messages=[MessageRead.model_validate(m) for m in messages],
    )


@router.post(
    "/api/conversations/{conversation_id}/messages", response_model=MessageRead, status_code=201
)
async def create_message(
    conversation_id: uuid.UUID, data: MessageCreate, db: AsyncSession = Depends(get_db)
):
    conversation = await chat_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await chat_service.create_message(db, conversation_id, data.role, data.content)
