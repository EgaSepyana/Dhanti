import asyncio
from collections.abc import AsyncIterator

import httpx
from loguru import logger

from app.providers.base import LLMProvider

# Status codes that mean "this provider is unavailable right now" (rate limit,
# out of credits, transient server error) rather than a genuine request bug.
FALLBACK_STATUS_CODES = {402, 429, 500, 502, 503, 504}

# Worth retrying once against the SAME provider before giving up on it:
# transient network hiccups and server-side errors, not auth/billing issues.
RETRY_STATUS_CODES = {500, 502, 503, 504}
RETRY_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)
RETRY_DELAY_SECONDS = 0.5


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, RETRY_EXCEPTIONS):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in RETRY_STATUS_CODES


class FallbackLLMProvider(LLMProvider):
    """Tries the primary provider first (retrying once on a timeout or
    transient server error), then falls back to the secondary provider when
    the primary is rate-limited, out of credits, or still down after retry."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    def _should_fall_back(self, exc: Exception) -> bool:
        return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in FALLBACK_STATUS_CODES

    async def generate(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        primary_name = type(self._primary).__name__
        fallback_name = type(self._fallback).__name__
        try:
            return await self._primary.generate(messages, model, temperature, max_tokens)
        except Exception as exc:
            if _is_retryable(exc):
                logger.warning(f"LLM retry    | {primary_name} error={exc} -> retrying once")
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                try:
                    return await self._primary.generate(messages, model, temperature, max_tokens)
                except Exception as retry_exc:
                    exc = retry_exc
            if not self._should_fall_back(exc):
                logger.error(f"LLM no fallback | {primary_name} error={exc} (not a fallback-eligible error)")
                raise
            logger.warning(f"LLM fallback | {primary_name} -> {fallback_name} reason={exc}")
            # Don't pass through the primary's model id: it belongs to a
            # different provider's namespace. Let the fallback use its own default.
            return await self._fallback.generate(messages, None, temperature, max_tokens)

    async def generate_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        primary_name = type(self._primary).__name__
        fallback_name = type(self._fallback).__name__
        attempted_retry = False
        while True:
            try:
                async for chunk in self._primary.generate_stream(
                    messages, model, temperature, max_tokens
                ):
                    yield chunk
                return
            except Exception as exc:
                if _is_retryable(exc) and not attempted_retry:
                    logger.warning(f"LLM stream retry    | {primary_name} error={exc} -> retrying once")
                    attempted_retry = True
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                if not self._should_fall_back(exc):
                    logger.error(
                        f"LLM stream no fallback | {primary_name} error={exc} (not a fallback-eligible error)"
                    )
                    raise
                logger.warning(f"LLM stream fallback | {primary_name} -> {fallback_name} reason={exc}")
                break

        async for chunk in self._fallback.generate_stream(messages, None, temperature, max_tokens):
            yield chunk
