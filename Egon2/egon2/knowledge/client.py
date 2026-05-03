from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class KnowledgeEntry:
    id: str
    title: str
    content: str
    domain: str
    importance: int
    source: str


class KnowledgeClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def ping(self) -> bool:
        for path in ("/health", "/ping"):
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"{self._base_url}{path}")
                    if resp.status_code < 500:
                        return True
            except httpx.HTTPError as exc:
                logger.debug("knowledge.ping_failed path=%s err=%s", path, exc)
        return False

    async def search(
        self, keywords: list[str], limit: int = 5
    ) -> list[KnowledgeEntry]:
        if not keywords:
            return []
        query = " ".join(k for k in keywords if k).strip()
        if not query:
            return []

        attempts = (
            ("/search", {"q": query, "limit": limit}),
            ("/api/search", {"query": query, "limit": limit}),
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for path, params in attempts:
                    try:
                        resp = await client.get(
                            f"{self._base_url}{path}", params=params
                        )
                    except httpx.HTTPError as exc:
                        logger.debug(
                            "knowledge.search_attempt_failed path=%s err=%s",
                            path,
                            exc,
                        )
                        continue
                    if resp.status_code >= 400:
                        logger.debug(
                            "knowledge.search_status path=%s code=%s",
                            path,
                            resp.status_code,
                        )
                        continue
                    try:
                        data = resp.json()
                    except ValueError as exc:
                        logger.debug("knowledge.search_parse path=%s err=%s", path, exc)
                        continue
                    return _coerce_entries(data, limit)
        except Exception as exc:  # noqa: BLE001
            logger.warning("knowledge.search_failed err=%s", exc)
            return []
        return []

    async def aclose(self) -> None:
        return None


def _coerce_entries(data: object, limit: int) -> list[KnowledgeEntry]:
    items: list[dict] = []
    if isinstance(data, list):
        items = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        for key in ("results", "items", "entries", "data"):
            value = data.get(key)
            if isinstance(value, list):
                items = [x for x in value if isinstance(x, dict)]
                break

    out: list[KnowledgeEntry] = []
    for raw in items[:limit]:
        try:
            out.append(
                KnowledgeEntry(
                    id=str(raw.get("id", "")),
                    title=str(raw.get("title", "")),
                    content=str(raw.get("content", "")),
                    domain=str(raw.get("domain", "")),
                    importance=int(raw.get("importance", 0) or 0),
                    source=str(raw.get("source", "")),
                )
            )
        except (TypeError, ValueError) as exc:
            logger.debug("knowledge.coerce_skipped err=%s", exc)
    return out


__all__ = ["KnowledgeClient", "KnowledgeEntry"]
