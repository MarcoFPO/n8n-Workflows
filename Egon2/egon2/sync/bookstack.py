from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from egon2.database import Database
from egon2.settings import Settings

logger = logging.getLogger(__name__)


class BookStackSync:
    def __init__(self, db: Database, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._base_url = settings.bookstack_url.rstrip("/")
        self._book_id = settings.bookstack_egon_book_id
        self._headers = {
            "Authorization": (
                f"Token {settings.bookstack_token_id}:"
                f"{settings.bookstack_token_secret}"
            ),
            "Accept": "application/json",
        }

    async def sync_pending(self) -> tuple[int, int]:
        if not self._settings.bookstack_token_id or not self._settings.bookstack_token_secret:
            logger.info("bookstack.sync_skipped reason=no_credentials")
            return (0, 0)

        if not await self._has_required_columns():
            logger.warning("bookstack.sync_skipped reason=schema_missing")
            return (0, 0)

        rows = await self._load_pending()
        if not rows:
            return (0, 0)

        synced = 0
        errors = 0
        async with httpx.AsyncClient(timeout=30.0, headers=self._headers) as client:
            self._client = client
            for row in rows:
                note_id = row["id"]
                content = row["content"] or ""
                title = (row["title"] if "title" in row.keys() else None) or self._derive_title(content, note_id)
                page_id = row["bookstack_page_id"]
                try:
                    if page_id:
                        ok = await self._update_page(str(page_id), title, content)
                        if ok:
                            await self._mark_synced(note_id, int(page_id))
                            synced += 1
                        else:
                            await self._mark_error(note_id)
                            errors += 1
                    else:
                        new_id = await self._create_page(note_id, title, content)
                        if new_id is not None:
                            await self._mark_synced(note_id, int(new_id))
                            synced += 1
                        else:
                            await self._mark_error(note_id)
                            errors += 1
                except Exception:
                    logger.exception("bookstack.sync_note_failed id=%s", note_id)
                    await self._mark_error(note_id)
                    errors += 1
        return (synced, errors)

    async def _create_page(self, note_id: str, title: str, content: str) -> str | None:
        url = f"{self._base_url}/api/pages"
        payload: dict[str, Any] = {
            "book_id": self._book_id,
            "name": title[:240] or f"Notiz {note_id[:8]}",
            "markdown": content,
        }
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            page_id = data.get("id")
            if page_id is None:
                logger.warning("bookstack.create_no_id note=%s", note_id)
                return None
            return str(page_id)
        except httpx.HTTPError as exc:
            logger.warning("bookstack.create_failed note=%s err=%s", note_id, exc)
            return None

    async def _update_page(self, page_id: str, title: str, content: str) -> bool:
        url = f"{self._base_url}/api/pages/{page_id}"
        payload: dict[str, Any] = {
            "name": title[:240] or f"Notiz {page_id}",
            "markdown": content,
        }
        try:
            resp = await self._client.put(url, json=payload)
            resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("bookstack.update_failed page=%s err=%s", page_id, exc)
            return False

    async def _has_required_columns(self) -> bool:
        async with self._db.connection() as conn:
            cur = await conn.execute("PRAGMA table_info(notes)")
            cols = {row[1] for row in await cur.fetchall()}
            await cur.close()
        return "bookstack_page_id" in cols and "synced_bookstack" in cols

    async def _load_pending(self) -> list[Any]:
        async with self._db.connection() as conn:
            cur = await conn.execute(
                """
                SELECT id, title, content, bookstack_page_id, synced_bookstack
                  FROM notes
                 WHERE synced_bookstack = 0
                 ORDER BY created_at ASC
                 LIMIT 50
                """
            )
            rows = await cur.fetchall()
            await cur.close()
            return list(rows)

    async def _mark_synced(self, note_id: str, page_id: int) -> None:
        async with self._db.connection() as conn:
            await conn.execute(
                """
                UPDATE notes
                   SET synced_bookstack = 1,
                       bookstack_page_id = ?
                 WHERE id = ?
                """,
                (page_id, note_id),
            )
            await conn.commit()

    async def _mark_error(self, note_id: str) -> None:
        async with self._db.connection() as conn:
            await conn.execute(
                "UPDATE notes SET synced_bookstack = 2 WHERE id = ?",
                (note_id,),
            )
            await conn.commit()

    @staticmethod
    def _derive_title(content: str, note_id: str) -> str:
        first_line = (content or "").strip().splitlines()[0] if content.strip() else ""
        if first_line:
            return first_line[:120]
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        return f"Notiz {ts} ({note_id[:8]})"


__all__ = ["BookStackSync"]
