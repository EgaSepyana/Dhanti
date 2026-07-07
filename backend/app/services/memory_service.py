import json
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.providers.manager import get_provider_manager

EXTRACTION_PROMPT = """Extract any durable facts worth remembering long-term from this exchange: \
workspace goals, user preferences, recurring context, or important constraints. \
Ignore one-off analysis results or transient details. Respond with ONLY a JSON array, no \
markdown fences, no explanation:
[{"category": "workspace" | "user_preference" | "artifact", "content": "<concise fact>"}]
Respond with [] if nothing is worth remembering long-term."""

# A short JSON array of brief facts (often empty) — this runs after every
# single chat turn, so an oversized default here compounds fast.
MEMORY_EXTRACTION_MAX_TOKENS = 300


def _extract_json_array(raw: str) -> list:
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


async def extract_and_store_memories(
    db: AsyncSession, workspace_id: uuid.UUID | str, prompt: str, response: str
) -> list[Memory]:
    llm = get_provider_manager().get_llm()
    try:
        raw = await llm.generate(
            [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"User: {prompt}\nAssistant: {response}"},
            ],
            temperature=0.0,
            max_tokens=MEMORY_EXTRACTION_MAX_TOKENS,
        )
        facts = _extract_json_array(raw)
    except Exception:
        facts = []

    contents = [f["content"] for f in facts if isinstance(f, dict) and f.get("content")]
    if not contents:
        return []

    embedder = get_provider_manager().get_embedding()
    vector_provider = get_provider_manager().get_vector()
    vectors = await embedder.embed(contents)

    stored: list[Memory] = []
    for fact, vector in zip(facts, vectors, strict=False):
        embedding_id = str(uuid.uuid4())
        memory = Memory(
            workspace_id=uuid.UUID(str(workspace_id)),
            category=fact.get("category", "workspace"),
            content=fact["content"],
            embedding_id=embedding_id,
        )
        db.add(memory)
        await vector_provider.upsert(
            embedding_id,
            vector,
            {
                "workspace_id": str(workspace_id),
                "type": "memory",
                "category": memory.category,
                "text": memory.content,
            },
        )
        stored.append(memory)

    await db.commit()
    return stored


async def retrieve_relevant_memories(
    workspace_id: uuid.UUID | str, query: str, top_k: int = 5
) -> list[dict]:
    try:
        embedder = get_provider_manager().get_embedding()
        vector = (await embedder.embed([query]))[0]
        results = await get_provider_manager().get_vector().search(vector, top_k=top_k * 2)
    except Exception:
        return []

    matches = [
        r
        for r in results
        if r["payload"].get("workspace_id") == str(workspace_id)
        and r["payload"].get("type") == "memory"
    ]
    return matches[:top_k]
