import uuid

from app.ai.tools.registry import register_tool
from app.providers.manager import get_provider_manager
from app.services import document_service


@register_tool("parse_pdf")
def parse_pdf(content: bytes) -> tuple[int, dict, list[dict]]:
    return document_service.parse_pdf(content)


@register_tool("chunk_text")
def chunk_text(text: str) -> list[str]:
    return document_service.chunk_text(text)


@register_tool("embed_chunks")
async def embed_chunks(chunks: list[dict]) -> list[list[float]]:
    if not chunks:
        return []
    embedder = get_provider_manager().get_embedding()
    return await embedder.embed([c["text"] for c in chunks])


@register_tool("index_chunks")
async def index_chunks(
    workspace_id: str, document_id: str, chunks: list[dict], vectors: list[list[float]]
) -> list[dict]:
    vector_provider = get_provider_manager().get_vector()
    indexed: list[dict] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        embedding_id = str(uuid.uuid4())
        await vector_provider.upsert(
            embedding_id,
            vector,
            {
                "workspace_id": workspace_id,
                "document_id": document_id,
                "text": chunk["text"],
                "page": chunk["page"],
                "type": "chunk",
            },
        )
        indexed.append({**chunk, "embedding_id": embedding_id})
    return indexed
