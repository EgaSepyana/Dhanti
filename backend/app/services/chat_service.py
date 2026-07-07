import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import get_orchestrator, initial_state
from app.core.database import async_session_factory
from app.models.conversation import Conversation, Message
from app.models.workspace import Workspace
from app.providers.manager import get_llm_for_model
from app.services import memory_service

STATUS_MESSAGES = {
    "build_context": "Reading workspace context...",
    "analyze_intent": "Understanding your request...",
    "plan": "Planning approach...",
    "execute_agents": "Running analysis...",
}

RECENT_MESSAGES_LIMIT = 10

# A short conversational reply, not a report — this runs on every single
# chat turn regardless of intent, so keeping it small matters a lot for a
# provider's per-minute token budget.
SUMMARY_MAX_TOKENS = 700


async def create_conversation(db: AsyncSession, workspace_id: uuid.UUID, title: str | None) -> Conversation:
    conversation = Conversation(workspace_id=workspace_id, title=title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(db: AsyncSession, workspace_id: uuid.UUID) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(db: AsyncSession, conversation_id: uuid.UUID) -> Conversation | None:
    return await db.get(Conversation, conversation_id)


async def list_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def create_message(db: AsyncSession, conversation_id: uuid.UUID, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def _get_recent_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(RECENT_MESSAGES_LIMIT)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _build_summary_prompt(prompt: str, final_state: dict, language: str | None = None) -> list[dict]:
    context = final_state.get("context") or {}
    files_desc = ", ".join(f["name"] for f in context.get("files", [])) or "no files"
    artifacts = final_state.get("artifacts", [])
    artifacts_desc = ", ".join(f"{a['type']} '{a['title']}'" for a in artifacts) or "no new artifacts"

    findings = []
    for step_result in final_state.get("step_results", {}).values():
        text = step_result.get("output", {}).get("text")
        if step_result.get("status") == "success" and text:
            findings.append(text[:500])

    excerpts = []
    for chunk in context.get("relevant_chunks", []):
        payload = chunk.get("payload", {})
        text = payload.get("text")
        page = payload.get("page")
        if text:
            excerpts.append(f"(p. {page}): {text[:400]}" if page is not None else text[:400])

    system = (
        "You are DHANTI, an AI data workspace assistant. Write a concise, conversational reply "
        "to the user. Reference the actual workspace files/datasets you used by name. Mention "
        "what artifacts were generated, if any, so the user knows what to look at. When you use "
        "a document excerpt to answer, cite its page number in parentheses like (p. 3). Do not "
        "repeat raw JSON or code; speak naturally in plain prose."
        + (f" Respond in {language}." if language else "")
    )
    user = (
        f"User asked: {prompt}\n\n"
        f"Workspace files involved: {files_desc}\n"
        f"Artifacts generated: {artifacts_desc}\n"
        + ("Analysis findings:\n" + "\n---\n".join(findings) + "\n" if findings else "")
        + ("Relevant document excerpts:\n" + "\n---\n".join(excerpts) if excerpts else "")
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def stream_chat(
    conversation_id: uuid.UUID,
    workspace_id: uuid.UUID,
    prompt: str,
    model_override: str | None = None,
) -> AsyncIterator[str]:
    """Owns its own DB session for the full duration of the stream: a FastAPI
    request-scoped session (Depends(get_db)) would be closed by the framework
    as soon as the endpoint function returns, which happens before a
    StreamingResponse finishes iterating this generator.

    A catastrophic failure anywhere in the pipeline (e.g. both LLM providers
    down) is caught and surfaced as a user-friendly "error" SSE event rather
    than a hung connection or a raw stack trace reaching the client."""
    try:
        async with async_session_factory() as db:
            workspace = await db.get(Workspace, workspace_id)
            ai_settings = (workspace.settings if workspace else {}) or {}
            language = ai_settings.get("language")
            # A per-message model picked in the chat input wins over the
            # workspace's saved default for this one turn only.
            model = model_override or ai_settings.get("model")

            await create_message(db, conversation_id, "user", prompt)
            recent_messages = await _get_recent_messages(db, conversation_id)

            graph = get_orchestrator()
            status_queue: asyncio.Queue = asyncio.Queue()
            state = initial_state(
                db, workspace_id, prompt, recent_messages, status_queue=status_queue, model=model
            )

            final_state: dict = dict(state)

            async def _run_graph() -> None:
                # Always signal completion via a sentinel, even on failure, so the
                # consumer loop below never blocks forever waiting on the queue.
                try:
                    async for update in graph.astream(state, stream_mode="updates"):
                        for node_name, node_output in update.items():
                            status_message = STATUS_MESSAGES.get(node_name)
                            if status_message:
                                await status_queue.put(("status", {"phase": node_name, "message": status_message}))
                            final_state.update(node_output)
                finally:
                    await status_queue.put(None)

            graph_task = asyncio.create_task(_run_graph())
            while True:
                item = await status_queue.get()
                if item is None:
                    break
                event_name, payload = item
                yield _sse(event_name, payload)
            await graph_task  # re-raise any exception from the graph run

            for artifact in final_state.get("artifacts", []):
                yield _sse("artifact", artifact)

            if final_state.get("simple_query_resolved"):
                # Answered by simple_query_engine with zero LLM calls — phrasing
                # this through the LLM anyway would defeat the entire point of
                # the fast path, so the computed answer IS the reply.
                full_text = next(iter(final_state.get("step_results", {}).values()))["output"]["text"]
                yield _sse("text", {"content": full_text})
            else:
                llm = get_llm_for_model(model)
                full_text = ""
                summary_messages = _build_summary_prompt(prompt, final_state, language)
                async for chunk in llm.generate_stream(
                    summary_messages, model=model, max_tokens=SUMMARY_MAX_TOKENS
                ):
                    full_text += chunk
                    yield _sse("text", {"content": chunk})

            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_text,
                artifacts=[a["id"] for a in final_state.get("artifacts", [])],
                metadata_={"intent": (final_state.get("intent_result") or {}).get("intent")},
            )
            db.add(assistant_message)
            await db.commit()

            if not final_state.get("simple_query_resolved"):
                # A trivial aggregate lookup rarely yields a durable fact worth
                # remembering, and extraction is itself an LLM call — skipping
                # it here keeps the zero-LLM-call path genuinely zero.
                await memory_service.extract_and_store_memories(db, workspace_id, prompt, full_text)
    except Exception:  # noqa: BLE001 - must degrade to a friendly message, never a hung/raw-error stream
        logger.exception(
            f"stream_chat failed | conversation_id={conversation_id} workspace_id={workspace_id}"
        )
        yield _sse(
            "error",
            {"message": "Something went wrong while processing your request. Please try again."},
        )

    yield _sse("done", {})
