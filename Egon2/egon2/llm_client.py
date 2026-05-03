"""LLMClient — Async-HTTP-Client für den OpenAI-kompatiblen Claude-Wrapper.

Spricht den Endpoint `LLM_API_URL` (OpenAI-kompatibler Chat-Completions-Endpoint).
Nutzt `httpx.AsyncClient` als Pool (eager im `__init__`).

Wirft semantisch typisierte Exceptions:
- `LLMTimeoutError` bei httpx-Timeouts
- `LLMRateLimitError` bei HTTP 429
- `LLMClientError` bei sonstigen 4xx/5xx oder Netzwerkfehlern
- `LLMParseError` wenn Response nicht parsebar ist
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

import httpx

from egon2.exceptions import (
    LLMClientError,
    LLMParseError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from egon2.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(slots=True)
class LLMResponse:
    content: str
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    finish_reason: str = "stop"
    cost_estimate: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """Async-Client zum OpenAI-kompatiblen LLM-Wrapper."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._url = settings.llm_api_url
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=self._timeout, write=10.0, pool=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def ping(self) -> bool:
        """Sehr leichter Verbindungstest — sendet eine 1-Token-Anfrage."""
        try:
            await self.chat(
                messages=[LLMMessage(role="user", content="Antworte mit einem einzigen Wort: BEREIT")],
                max_tokens=10,
                temperature=0.0,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm.ping_failed: %s", exc)
            return False

    async def chat(
        self,
        messages: Sequence[LLMMessage] | Sequence[dict[str, str]],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.5,
        fresh_context: bool = False,  # nur informativ — der Wrapper kümmert sich
    ) -> LLMResponse:
        """Sendet einen Chat-Completion-Request, parst die Antwort."""
        msg_dicts: list[dict[str, str]] = []
        for m in messages:
            if isinstance(m, LLMMessage):
                msg_dicts.append(m.to_dict())
            elif isinstance(m, dict):
                msg_dicts.append({"role": m["role"], "content": m["content"]})
            else:
                raise TypeError(f"Unsupported message type: {type(m)!r}")

        payload = {
            "model": self._model,
            "messages": msg_dicts,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        try:
            resp = await self._client.post(self._url, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"LLM timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(f"LLM HTTP error: {exc}") from exc

        if resp.status_code == 429:
            raise LLMRateLimitError(f"LLM rate limit: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise LLMClientError(
                f"LLM HTTP {resp.status_code}: {resp.text[:300]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMParseError(f"LLM response not JSON: {exc}") from exc

        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish = choice.get("finish_reason", "stop")
            usage = data.get("usage", {}) or {}
            return LLMResponse(
                content=content,
                model=data.get("model", self._model),
                tokens_input=int(usage.get("prompt_tokens", 0) or 0),
                tokens_output=int(usage.get("completion_tokens", 0) or 0),
                finish_reason=finish or "stop",
                cost_estimate=0.0,
                raw=data,
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMParseError(f"LLM response shape invalid: {exc}") from exc


__all__ = ["LLMClient", "LLMMessage", "LLMResponse"]
