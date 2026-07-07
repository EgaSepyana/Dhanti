import json
import uuid

import httpx
from httpx import ASGITransport
from sqlalchemy import select

from app.core.database import async_session_factory
from app.main import app
from app.models.conversation import Conversation, Message
from test_orchestrator import _setup_workspace_with_data


async def _create_conversation(workspace_id: uuid.UUID) -> uuid.UUID:
    async with async_session_factory() as db:
        conversation = Conversation(workspace_id=workspace_id, title="test chat")
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation.id


def _parse_sse(raw: str) -> list[dict]:
    events = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type, data_line = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_type = line[len("event: ") :]
            elif line.startswith("data: "):
                data_line = line[len("data: ") :]
        if event_type and data_line is not None:
            events.append({"event": event_type, "data": json.loads(data_line)})
    return events


async def test_chat_streams_text_status_artifact_and_done_events():
    workspace_id = await _setup_workspace_with_data()
    conversation_id = await _create_conversation(workspace_id)

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream(
            "POST",
            f"/api/conversations/{conversation_id}/chat",
            json={"prompt": "Create a dashboard from sales.xlsx"},
            timeout=180,
        ) as response:
            assert response.status_code == 200
            raw = ""
            async for chunk in response.aiter_text():
                raw += chunk

    events = _parse_sse(raw)
    event_types = [e["event"] for e in events]

    assert "status" in event_types
    assert "artifact" in event_types
    assert "text" in event_types
    assert event_types[-1] == "done"

    text_events = [e for e in events if e["event"] == "text"]
    assert len(text_events) > 1, "expected the response to stream in multiple chunks, not one blob"
    full_reply = "".join(e["data"]["content"] for e in text_events)
    assert len(full_reply.strip()) > 0

    artifact_events = [e for e in events if e["event"] == "artifact"]
    assert len(artifact_events) >= 1
    assert {"dataset", "visualization", "dashboard"}.issubset(
        {a["data"]["type"] for a in artifact_events}
    )


async def test_chat_persists_messages_and_maintains_context_across_turns():
    workspace_id = await _setup_workspace_with_data()
    conversation_id = await _create_conversation(workspace_id)

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for prompt in ["Analyze this dataset", "What were the main findings?"]:
            async with client.stream(
                "POST",
                f"/api/conversations/{conversation_id}/chat",
                json={"prompt": prompt},
                timeout=180,
            ) as response:
                assert response.status_code == 200
                async for _ in response.aiter_text():
                    pass

    async with async_session_factory() as db:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = list(result.scalars().all())

    assert len(messages) == 4  # user, assistant, user, assistant
    assert [m.role for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[0].content == "Analyze this dataset"
    assert messages[2].content == "What were the main findings?"
    assert all(m.content.strip() for m in messages if m.role == "assistant")
