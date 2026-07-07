"""Fast, network-free tests for FallbackLLMProvider's retry-before-fallback
logic (Phase 8.5), using fake in-memory providers instead of real API calls."""

import httpx
import pytest

from app.providers.base import LLMProvider
from app.providers.llm.fallback import FallbackLLMProvider


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://example.test/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"{status_code} error", request=request, response=response)


class FakeLLMProvider(LLMProvider):
    """Raises `errors` in sequence (one per call), then returns `reply` forever."""

    def __init__(self, errors: list[Exception] | None = None, reply: str = "ok"):
        self.errors = list(errors or [])
        self.reply = reply
        self.call_count = 0

    async def generate(self, messages, model=None, temperature=0.7, max_tokens=None):
        self.call_count += 1
        if self.errors:
            raise self.errors.pop(0)
        return self.reply

    async def generate_stream(self, messages, model=None, temperature=0.7, max_tokens=None):
        self.call_count += 1
        if self.errors:
            raise self.errors.pop(0)
        for chunk in self.reply:
            yield chunk


async def test_retries_primary_once_on_timeout_before_using_fallback():
    primary = FakeLLMProvider(errors=[httpx.TimeoutException("slow")], reply="from primary")
    fallback = FakeLLMProvider(reply="from fallback")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    result = await provider.generate([{"role": "user", "content": "hi"}])

    assert result == "from primary"
    assert primary.call_count == 2  # first attempt failed, retry succeeded
    assert fallback.call_count == 0


async def test_falls_back_to_groq_after_retry_still_fails():
    primary = FakeLLMProvider(errors=[_http_error(500), _http_error(500)])
    fallback = FakeLLMProvider(reply="from fallback")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    result = await provider.generate([{"role": "user", "content": "hi"}])

    assert result == "from fallback"
    assert primary.call_count == 2  # original attempt + one retry, both failed
    assert fallback.call_count == 1


async def test_immediately_falls_back_on_payment_required_without_retrying():
    primary = FakeLLMProvider(errors=[_http_error(402)])
    fallback = FakeLLMProvider(reply="from fallback")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    result = await provider.generate([{"role": "user", "content": "hi"}])

    assert result == "from fallback"
    assert primary.call_count == 1  # no retry for a billing/auth failure
    assert fallback.call_count == 1


async def test_non_fallback_error_propagates_without_falling_back():
    primary = FakeLLMProvider(errors=[_http_error(400)])
    fallback = FakeLLMProvider(reply="from fallback")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    with pytest.raises(httpx.HTTPStatusError):
        await provider.generate([{"role": "user", "content": "hi"}])

    assert fallback.call_count == 0


async def test_generate_stream_retries_then_falls_back():
    primary = FakeLLMProvider(errors=[_http_error(503), _http_error(503)])
    fallback = FakeLLMProvider(reply="fb")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    chunks = [c async for c in provider.generate_stream([{"role": "user", "content": "hi"}])]

    assert "".join(chunks) == "fb"
    assert primary.call_count == 2
    assert fallback.call_count == 1
