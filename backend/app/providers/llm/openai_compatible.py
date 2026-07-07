import json
import time
from collections.abc import AsyncIterator

import httpx
from loguru import logger

from app.core.config import get_settings
from app.providers.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Base for any provider exposing an OpenAI-style /chat/completions API
    (OpenRouter, Groq, and most other inference gateways)."""

    # Subclasses can set extra provider-specific request fields (e.g. Groq's
    # reasoning_format) without the shared base needing to know about them.
    _extra_body: dict = {}

    # Subclasses can cap how many tokens they'll ever request, independent of
    # ai_max_tokens/a caller's override — e.g. a provider whose free tier caps
    # tokens-per-minute lower than the app's general default.
    _max_tokens_ceiling: int | None = None

    def __init__(self, base_url: str, api_key: str, default_model: str) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._default_model = default_model

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _resolve_max_tokens(self, max_tokens: int | None) -> int:
        resolved = max_tokens if max_tokens is not None else get_settings().ai_max_tokens
        if self._max_tokens_ceiling is not None:
            resolved = min(resolved, self._max_tokens_ceiling)
        return resolved

    async def generate(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        settings = get_settings()
        provider = self.__class__.__name__
        resolved_model = model or self._default_model
        resolved_max_tokens = self._resolve_max_tokens(max_tokens)
        logger.info(
            f"LLM call   -> {provider:<14} model={resolved_model} max_tokens={resolved_max_tokens}"
        )
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=settings.ai_execution_timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": resolved_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": resolved_max_tokens,
                        **self._extra_body,
                    },
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            elapsed = time.monotonic() - started
            logger.error(
                f"LLM FAILED <- {provider:<14} model={resolved_model} "
                f"time={elapsed:.2f}s error={exc}"
            )
            raise
        elapsed = time.monotonic() - started
        usage = data.get("usage", {})
        logger.success(
            f"LLM done   <- {provider:<14} model={resolved_model} time={elapsed:.2f}s "
            f"completion_tokens={usage.get('completion_tokens', '?')} "
            f"total_tokens={usage.get('total_tokens', '?')}"
        )
        return data["choices"][0]["message"]["content"]

    async def generate_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        settings = get_settings()
        provider = self.__class__.__name__
        resolved_model = model or self._default_model
        resolved_max_tokens = self._resolve_max_tokens(max_tokens)
        logger.info(
            f"LLM stream -> {provider:<14} model={resolved_model} max_tokens={resolved_max_tokens}"
        )
        started = time.monotonic()
        chunk_count = 0
        try:
            async with httpx.AsyncClient(timeout=settings.ai_execution_timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": resolved_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": resolved_max_tokens,
                        "stream": True,
                        **self._extra_body,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        payload = line[len("data: ") :]
                        if payload.strip() == "[DONE]":
                            break
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            chunk_count += 1
                            yield content
        except Exception as exc:
            elapsed = time.monotonic() - started
            logger.error(
                f"LLM stream FAILED <- {provider:<14} model={resolved_model} "
                f"time={elapsed:.2f}s chunks={chunk_count} error={exc}"
            )
            raise
        elapsed = time.monotonic() - started
        logger.success(
            f"LLM stream done   <- {provider:<14} model={resolved_model} "
            f"time={elapsed:.2f}s chunks={chunk_count}"
        )
