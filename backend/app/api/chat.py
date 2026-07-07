import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.database import get_db
from app.models.conversation import ChatRequest
from app.services import chat_service

router = APIRouter(tags=["chat"])


@router.post("/api/conversations/{conversation_id}/chat")
async def chat(conversation_id: uuid.UUID, data: ChatRequest, db: AsyncSession = Depends(get_db)):
    conversation = await chat_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return StreamingResponse(
        chat_service.stream_chat(
            conversation_id, conversation.workspace_id, data.prompt, model_override=data.model
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
