import uuid

import pytest

from app.providers.embedding.huggingface import HuggingFaceEmbeddingProvider
from app.providers.llm.fallback import FallbackLLMProvider
from app.providers.manager import get_provider_manager
from app.providers.storage.supabase import SupabaseStorageProvider
from app.providers.vector.qdrant import QdrantProvider


async def test_llm_generate_returns_text():
    # Goes through the manager's configured provider (OpenRouter with Groq
    # fallback) rather than instantiating OpenRouterProvider directly, so this
    # test reflects what production code actually calls and stays green
    # whichever of the two providers is currently available.
    provider = get_provider_manager().get_llm()
    result = await provider.generate(
        [{"role": "user", "content": "Reply with exactly one word: hello"}]
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0


async def test_llm_generate_stream_yields_chunks():
    provider = get_provider_manager().get_llm()
    chunks = [
        chunk
        async for chunk in provider.generate_stream(
            [{"role": "user", "content": "Count from 1 to 5, one number per line."}]
        )
    ]
    assert len(chunks) > 0
    assert "".join(chunks).strip()


async def test_embedding_dimension():
    provider = HuggingFaceEmbeddingProvider()
    vectors = await provider.embed(["hello world", "DHANTI is a data workspace"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    assert all(isinstance(v, float) for v in vectors[0])


async def test_vector_upsert_and_search():
    provider = QdrantProvider()
    embedder = HuggingFaceEmbeddingProvider()

    # Unique text per run: the shared test collection accumulates points across
    # runs, so a fixed sentence would tie in cosine similarity with earlier
    # runs' identical embeddings and make rank-0 non-deterministic.
    point_id = str(uuid.uuid4())
    text = f"the quick brown fox jumps over the lazy dog {point_id}"
    vector = (await embedder.embed([text]))[0]

    await provider.upsert(point_id, vector, {"test": "phase2", "text": text})

    results = await provider.search(vector, top_k=3)
    assert len(results) > 0
    assert results[0]["id"] == point_id
    assert results[0]["score"] > 0.99


async def test_storage_upload_download_delete_roundtrip():
    provider = SupabaseStorageProvider()
    path = f"_phase2-tests/{uuid.uuid4()}.txt"
    content = b"DHANTI Phase 2 provider test"

    await provider.upload(path, content, "text/plain")
    downloaded = await provider.download(path)
    assert downloaded == content

    await provider.delete(path)
    with pytest.raises(Exception):
        await provider.download(path)


async def test_fallback_llm_provider_falls_back_to_groq():
    from app.providers.llm.groq import GroqProvider
    from app.providers.llm.openrouter import OpenRouterProvider

    provider = FallbackLLMProvider(primary=OpenRouterProvider(), fallback=GroqProvider())
    result = await provider.generate(
        [{"role": "user", "content": "Reply with exactly one word: hello"}]
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0

    chunks = [
        chunk
        async for chunk in provider.generate_stream(
            [{"role": "user", "content": "Count from 1 to 5, one number per line."}]
        )
    ]
    assert len(chunks) > 0
    assert "".join(chunks).strip()


async def test_provider_manager_returns_singletons_per_type():
    manager = get_provider_manager()
    assert manager.get_llm() is manager.get_llm()
    assert manager.get_embedding() is manager.get_embedding()
    assert manager.get_vector() is manager.get_vector()
    assert manager.get_storage() is manager.get_storage()

    assert isinstance(manager.get_llm(), FallbackLLMProvider)
    assert isinstance(manager.get_embedding(), HuggingFaceEmbeddingProvider)
    assert isinstance(manager.get_vector(), QdrantProvider)
    assert isinstance(manager.get_storage(), SupabaseStorageProvider)
