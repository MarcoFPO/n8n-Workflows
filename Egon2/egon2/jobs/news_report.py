from __future__ import annotations

import asyncio
import json as _json
import logging
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING

import httpx

from egon2.core.message_queue import safe_wrap
from egon2.core.scheduler import EgonScheduler
from egon2.llm_client import LLMMessage

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_BERLIN = ZoneInfo("Europe/Berlin")
_app: "FastAPI | None" = None

# Themen mit je max. 3 Treffern — parallel abgefragt
_TOPICS: list[tuple[str, str]] = [
    ("KI & Technologie", "Künstliche Intelligenz AI News 24h"),
    ("Wiesbaden-Biebrich", "Wiesbaden Biebrich Nachrichten"),
    ("Chemnitz", "Chemnitz Nachrichten"),
    ("Vodafone", "Vodafone Unternehmen News"),
]
_RESULTS_PER_TOPIC = 3


async def _fetch_topic(searxng_url: str, label: str, query: str) -> tuple[str, list[dict]]:
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
            resp = await client.get(
                f"{searxng_url.rstrip('/')}/search",
                params={
                    "q": query,
                    "format": "json",
                    "time_range": "day",
                    "language": "de",
                },
            )
            resp.raise_for_status()
            return label, (resp.json().get("results") or [])[:_RESULTS_PER_TOPIC]
    except Exception as exc:
        logger.warning("news_report.searxng_failed topic=%s error=%s", label, exc)
        return label, []


async def _log_run(db, status: str, output: str, started_at: str) -> None:
    try:
        async with db.connection() as conn:
            await conn.execute(
                "INSERT INTO scheduler_log (id, job_name, started_at, finished_at, status, output) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex,
                    "daily_news_report",
                    started_at,
                    datetime.now(timezone.utc).isoformat(),
                    status,
                    output[:4000],
                ),
            )
            await conn.commit()
    except Exception as exc:
        logger.warning("news_report.log_failed error=%s", exc)


async def news_report_job() -> None:
    if _app is None:
        return
    started_at = datetime.now(timezone.utc).isoformat()
    state = getattr(_app.state, "egon", None)
    if state is None or state.db is None or state.llm is None or state.registry is None:
        logger.warning("news_report.state_unavailable")
        return

    settings = state.settings

    # Themen sequenziell abfragen — parallele Requests triggern SearXNG-Rate-Limit
    topic_results: list[tuple[str, list[dict]]] = []
    for label, query in _TOPICS:
        result = await _fetch_topic(settings.searxng_url, label, query)
        topic_results.append(result)
        await asyncio.sleep(1.5)

    # Prüfen ob überhaupt etwas zurückkam
    total_hits = sum(len(results) for _, results in topic_results)
    if total_hits == 0:
        await _log_run(state.db, "skipped", "no_results", started_at)
        return

    # Kontext-Block pro Thema aufbauen
    sections: list[str] = []
    for label, results in topic_results:
        if not results:
            sections.append(f"### {label}\nKeine aktuellen Meldungen.")
            continue
        lines = []
        for r in results:
            title = (r.get("title") or "").strip()
            url = (r.get("url") or "").strip()
            content = (r.get("content") or "").strip()
            lines.append(f"- {title}\n  {url}\n  {content}")
        sections.append(f"### {label}\n" + "\n\n".join(lines))

    context_block = "\n\n".join(sections)

    journalist = await state.registry.get("journalist")
    if journalist is None:
        await _log_run(state.db, "failed", "journalist_missing", started_at)
        return

    today = datetime.now(_BERLIN).strftime("%d. %B %Y")
    brief = (
        f"objective: Tages-Briefing {today} — Neuigkeiten der letzten 24h\n"
        f"context:\n{safe_wrap('searxng', context_block)}\n"
        "constraints:\n"
        "  - Themen in der Reihenfolge: KI/AI, Wiesbaden-Biebrich, Chemnitz, Vodafone\n"
        "  - Pro Thema 2-3 Sätze, kein Thema weglassen (auch wenn keine Meldung: kurz vermerken)\n"
        "  - Quellen am Ende als kompakte Liste\n"
        "  - Ton: trocken, informativ, Egon-Stil\n"
        "expected_output: Kompaktes Briefing in natürlicher Sprache, kein JSON"
    )

    t0 = time.monotonic()
    try:
        resp = await state.llm.chat(
            messages=[
                LLMMessage(role="system", content=journalist.system_prompt),
                LLMMessage(role="user", content=brief),
            ],
            max_tokens=2048,
            temperature=0.4,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        logger.exception("news_report.llm_failed")
        await _log_run(state.db, "failed", f"llm_error: {exc}", started_at)
        return

    text = resp.content.strip()
    try:
        parsed = _json.loads(text)
        result_text = str(parsed["result"]).strip() if isinstance(parsed, dict) and "result" in parsed else text
    except (ValueError, TypeError):
        last_brace = text.rfind('\n{')
        if last_brace != -1:
            try:
                _json.loads(text[last_brace:].strip())
                text = text[:last_brace].rstrip()
            except (ValueError, TypeError):
                pass
        result_text = text

    task_id = uuid.uuid4().hex
    try:
        async with state.db.connection() as conn:
            await conn.execute(
                "INSERT INTO tasks (id, title, description, source_channel, status, assigned_agent, result) "
                "VALUES (?, ?, ?, ?, 'done', ?, ?)",
                (task_id, f"Briefing {today}", "daily_news_report", "scheduler", journalist.id, result_text),
            )
            await conn.commit()
        await state.registry.bump_use_count(journalist.id)
        await state.registry.record_assignment(
            task_id=task_id,
            agent_id=journalist.id,
            brief=brief,
            result=result_text,
            status="done",
            tokens_input=resp.tokens_input,
            tokens_output=resp.tokens_output,
            cost_estimate=resp.cost_estimate,
            duration_ms=duration_ms,
            quality_score=4,
        )
    except Exception:
        logger.exception("news_report.persist_failed")

    sent_to: list[str] = []
    matrix_room = settings.news_report_matrix_room
    if matrix_room and state.matrix_bot is not None and settings.matrix_enabled:
        try:
            await state.matrix_bot.send_message(matrix_room, result_text)
            sent_to.append("matrix")
        except Exception as exc:
            logger.warning("news_report.matrix_send_failed error=%s", exc)

    tg_chat = settings.news_report_telegram_chat
    if tg_chat and state.telegram_bot is not None and settings.telegram_enabled:
        try:
            await state.telegram_bot.send_message(tg_chat, result_text)
            sent_to.append("telegram")
        except Exception as exc:
            logger.warning("news_report.telegram_send_failed error=%s", exc)

    logger.info(
        "news_report.done topics=%d hits=%d chars=%d sent=%s duration_ms=%d",
        len(_TOPICS), total_hits, len(result_text), ",".join(sent_to) or "none", duration_ms,
    )
    await _log_run(
        state.db,
        "done",
        f"topics={len(_TOPICS)} hits={total_hits} sent={','.join(sent_to) or 'none'} chars={len(result_text)}",
        started_at,
    )


def register_jobs(scheduler: EgonScheduler, app: "FastAPI") -> None:
    global _app
    _app = app
    if scheduler.scheduler is None:
        logger.warning("news_report.scheduler_not_started")
        return
    scheduler.scheduler.add_job(
        news_report_job,
        "cron",
        hour=7,
        minute=30,
        timezone="Europe/Berlin",
        id="daily_news_report",
        replace_existing=True,
    )
    logger.info("news_report.registered cron=07:30")


__all__ = ["news_report_job", "register_jobs"]
