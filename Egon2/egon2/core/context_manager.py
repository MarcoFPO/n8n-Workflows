"""ContextManager — Baut den vollständigen LLM-Message-Stack.

Siehe `docs/LLD-Core.md` §2 für die vollständige Spezifikation.

Aufbau:
  1. System-Prompt (gerendert mit aktiven Spezialisten)
  2. Knowledge-Block (Top-N, safe_wrap; nur wenn Knowledge-Client vorhanden)
  3. Rolling Window (letzte N Konversations-Nachrichten)
  4. Aktuelle User-Message (wrapped_text)

Token-Budget wird konservativ über `len(text) / 3.0` geschätzt.
Bei Überschreitung werden zuerst Knowledge-Einträge, dann älteste
Window-Nachrichten weggeschnitten. Der System-Prompt wird nie gekürzt.
"""

from __future__ import annotations

import logging
import math
import re
import uuid
from collections.abc import Iterable
from typing import Any

from egon2.core.message_queue import IncomingMessage, safe_wrap
from egon2.database import Database, iso_utc_now
from egon2.personality import render_system_prompt

logger = logging.getLogger(__name__)


# --- Budgets / Konstanten (LLD-Core §2.2) -------------------------------

ROLLING_WINDOW: int = 20
"""Anzahl der jüngsten Konversations-Nachrichten im Rolling Window."""

KNOWLEDGE_BUDGET: int = 8_000
"""Konservatives Token-Budget für Knowledge-Einträge."""

MAX_TOTAL_TOKENS: int = 150_000
"""Maximales Token-Budget für den gesamten Message-Stack."""

RESERVED_OUTPUT: int = 4_096
"""Reservierte Tokens für die LLM-Antwort."""

KNOWLEDGE_TOP_K: int = 5
"""Top-N Knowledge-Einträge die abgefragt werden."""


# --- Stopwords für Keyword-Extraktion -----------------------------------

_STOPWORDS: frozenset[str] = frozenset({
    # DE
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines",
    "und", "oder", "aber", "doch", "sondern", "denn", "weil", "wenn", "dass",
    "ist", "sind", "war", "waren", "wird", "werden", "habe", "hat", "haben",
    "ich", "du", "er", "sie", "es", "wir", "ihr", "mich", "dich", "ihn",
    "uns", "euch", "mein", "dein", "sein", "ihr", "unser", "kein", "keine",
    "mit", "ohne", "von", "zu", "zum", "zur", "bei", "auf", "aus", "für",
    "über", "unter", "vor", "nach", "durch", "gegen", "um", "an", "in", "im",
    "auch", "noch", "schon", "nur", "mal", "doch", "ja", "nein", "nicht",
    "sehr", "mehr", "weniger", "viel", "wenig", "alle", "alles", "etwas",
    "kann", "könnte", "muss", "müsste", "soll", "sollte", "will", "würde",
    "diese", "dieser", "dieses", "jene", "jener", "jenes",
    # EN
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "can", "i", "you",
    "he", "she", "it", "we", "they", "this", "that", "these", "those",
    "of", "to", "in", "on", "at", "by", "for", "with", "from", "as", "if",
    "not", "no", "yes", "so", "too", "very", "just", "only", "more", "less",
})


# ----------------------------------------------------------------------------
# ContextManager
# ----------------------------------------------------------------------------


class ContextManager:
    """Baut den LLM-Message-Stack inklusive Token-Budget-Management."""

    def __init__(
        self,
        db: Database,
        knowledge_client: Any | None = None,
    ) -> None:
        self._db = db
        self._knowledge = knowledge_client

    # --- Public API --------------------------------------------------------

    async def build_context(
        self,
        msg: IncomingMessage,
        active_agents: list[str],
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """Liefert den vollständigen Message-Stack für einen LLM-Call.

        Args:
            msg: Die eingehende User-Nachricht (Pflicht: `wrapped_text`).
            active_agents: Liste aktiver Spezialisten — fließt in den
                System-Prompt ein, falls dieser nicht explizit übergeben.
            system_prompt: Optional vorgerenderter System-Prompt. Wenn None,
                wird `personality.render_system_prompt(active_agents)` genutzt.

        Returns:
            Liste von `{"role": ..., "content": ...}`-Dicts im OpenAI-Format.
        """
        sys_content = system_prompt or render_system_prompt(active_agents)
        sys_msg: dict[str, str] = {"role": "system", "content": sys_content}
        sys_tokens = self._estimate_tokens(sys_content)

        # Knowledge-Block (optional)
        knowledge_msg: dict[str, str] | None = None
        knowledge_tokens = 0
        if self._knowledge is not None:
            knowledge_block = await self._fetch_knowledge_block(msg.raw_text)
            if knowledge_block:
                knowledge_msg = {"role": "system", "content": knowledge_block}
                knowledge_tokens = self._estimate_tokens(knowledge_block)

        # Aktuelle User-Message (immer wrapped_text — niemals raw an LLM)
        current_user_msg: dict[str, str] = {
            "role": "user",
            "content": msg.wrapped_text,
        }
        current_tokens = self._estimate_tokens(msg.wrapped_text)

        # Rolling Window
        window = await self._load_rolling_window(ROLLING_WINDOW)
        window_tokens = sum(self._estimate_tokens(m["content"]) for m in window)

        # Budget-Verwaltung: zuerst Knowledge zurechtstutzen, dann Window.
        budget_used = (
            sys_tokens + knowledge_tokens + window_tokens
            + current_tokens + RESERVED_OUTPUT
        )
        if budget_used > MAX_TOTAL_TOKENS:
            # 1) Knowledge kürzen — nur Top-Einträge behalten oder ganz weglassen.
            if knowledge_msg is not None and knowledge_tokens > KNOWLEDGE_BUDGET:
                trimmed = self._trim_to_budget(
                    knowledge_msg["content"], KNOWLEDGE_BUDGET
                )
                knowledge_msg = {"role": "system", "content": trimmed}
                knowledge_tokens = self._estimate_tokens(trimmed)
                budget_used = (
                    sys_tokens + knowledge_tokens + window_tokens
                    + current_tokens + RESERVED_OUTPUT
                )

            # 2) Window von vorne (älteste zuerst) abschneiden.
            while window and budget_used > MAX_TOTAL_TOKENS:
                dropped = window.pop(0)
                window_tokens -= self._estimate_tokens(dropped["content"])
                budget_used = (
                    sys_tokens + knowledge_tokens + window_tokens
                    + current_tokens + RESERVED_OUTPUT
                )

            if budget_used > MAX_TOTAL_TOKENS:
                logger.warning(
                    "ContextManager: budget exceeded even after trimming "
                    "(used=%d, max=%d) — sending anyway",
                    budget_used,
                    MAX_TOTAL_TOKENS,
                )

        messages: list[dict[str, str]] = [sys_msg]
        if knowledge_msg is not None:
            messages.append(knowledge_msg)
        messages.extend(window)
        messages.append(current_user_msg)
        return messages

    async def save_exchange(
        self,
        channel: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """Speichert User+Assistant-Nachricht in der `conversations`-Tabelle."""
        ts = iso_utc_now()
        async with self._db.connection() as conn:
            await conn.execute(
                "INSERT INTO conversations (id, channel, role, content, timestamp) "
                "VALUES (?, ?, 'user', ?, ?)",
                (uuid.uuid4().hex, channel, user_text, ts),
            )
            await conn.execute(
                "INSERT INTO conversations (id, channel, role, content, timestamp) "
                "VALUES (?, ?, 'assistant', ?, ?)",
                (uuid.uuid4().hex, channel, assistant_text, ts),
            )
            await conn.commit()

    # --- Internals ---------------------------------------------------------

    def _estimate_tokens(self, text: str) -> int:
        """Konservative Token-Schätzung: `ceil(len(text) / 3.0)`.

        Für Deutsch + Code + JSON-Briefe leicht überschätzend, was für die
        Budget-Disziplin gut ist (lieber zu früh kürzen).
        """
        if not text:
            return 0
        return math.ceil(len(text) / 3.0)

    def _extract_keywords(self, text: str, *, limit: int = 8) -> list[str]:
        """Deterministische Keyword-Extraktion für Knowledge-Suche."""
        if not text:
            return []
        tokens = re.findall(r"[a-zäöüß0-9_\-]{3,}", text.lower())
        tokens = [t for t in tokens if t not in _STOPWORDS]
        # Häufigkeit zählen, aber Original-Reihenfolge bei Gleichstand
        freq: dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        sorted_tokens = sorted(
            freq.items(), key=lambda kv: (-kv[1], -len(kv[0]))
        )
        return [t for t, _ in sorted_tokens[:limit]]

    async def _fetch_knowledge_block(self, raw_text: str) -> str:
        """Befragt den Knowledge-Client (falls vorhanden) und baut den Block.

        Soft-fail: bei jeder Exception wird leise nur ein Warning geloggt
        und ein leerer Block zurückgegeben — Egon antwortet dann ohne
        Knowledge-Anreicherung. Der Knowledge-Store ist nice-to-have,
        nicht kritisch für die Funktion.
        """
        if self._knowledge is None:
            return ""
        keywords = self._extract_keywords(raw_text)
        if not keywords:
            return ""
        try:
            results = await self._knowledge.search(
                keywords, limit=KNOWLEDGE_TOP_K
            )
        except Exception as exc:  # noqa: BLE001 — soft-fail
            logger.warning(
                "ContextManager: knowledge search failed (soft-fail): %s", exc
            )
            return ""
        if not results:
            return ""

        lines: list[str] = ["# Relevantes Wissen"]
        for entry in results:
            title = self._entry_field(entry, "title") or "(ohne Titel)"
            content = self._entry_field(entry, "content") or ""
            wrapped = safe_wrap("knowledge", content)
            lines.append(f"## {title}\n{wrapped}")
        return "\n\n".join(lines)

    @staticmethod
    def _entry_field(entry: Any, key: str) -> str | None:
        """Robuster Feld-Zugriff: dict, dataclass oder Pydantic-Model."""
        if isinstance(entry, dict):
            value = entry.get(key)
        else:
            value = getattr(entry, key, None)
        if value is None:
            return None
        return str(value)

    async def _load_rolling_window(
        self, limit: int
    ) -> list[dict[str, str]]:
        """Lädt die letzten `limit` Nachrichten aus `conversations`.

        Reihenfolge im Resultat: aufsteigend nach `timestamp` (älteste zuerst),
        damit sie chronologisch in den LLM-Kontext gehängt werden können.
        """
        async with self._db.connection() as conn:
            cur = await conn.execute(
                """
                SELECT role, content FROM (
                    SELECT role, content, timestamp
                      FROM conversations
                     ORDER BY timestamp DESC
                     LIMIT ?
                ) ORDER BY timestamp ASC
                """,
                (limit,),
            )
            rows = await cur.fetchall()
            await cur.close()
        return [{"role": str(r["role"]), "content": str(r["content"])} for r in rows]

    def _trim_to_budget(self, content: str, token_budget: int) -> str:
        """Schneidet `content` so zurecht, dass die Token-Schätzung passt."""
        if self._estimate_tokens(content) <= token_budget:
            return content
        # 3 Zeichen ≈ 1 Token (siehe _estimate_tokens) — etwas Sicherheitsabschlag.
        max_chars = max(0, token_budget * 3 - 32)
        if max_chars <= 0:
            return ""
        return content[:max_chars] + " […gekürzt]"


__all__ = [
    "ContextManager",
    "ROLLING_WINDOW",
    "KNOWLEDGE_BUDGET",
    "MAX_TOTAL_TOKENS",
    "RESERVED_OUTPUT",
    "KNOWLEDGE_TOP_K",
]
