"""AgentDispatcher (Phase 1) — Intent-Klassifikation + Spezialist-Routing.

Siehe `docs/LLD-Core.md` §4 für die vollständige Spezifikation.

Phase-1-Umfang:
- Slash-Kommandos werden direkt behandelt (kein LLM).
- Cancel-Phrasen werden auf `raw_text` (case-insensitive) erkannt — H4-Fix.
- Intent + Spezialist werden in einem einzigen LLM-Call klassifiziert.
- Spezialist-Calls liefern JSON-Briefe; `_compose_user_reply` formuliert
  längere Outputs (>300 Zeichen) im Egon-Stil neu.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from enum import StrEnum

import httpx

from egon2.core.context_manager import ContextManager
from egon2.core.message_queue import IncomingMessage, safe_wrap
from egon2.core.task_manager import TaskManager
from egon2.agents.registry import AgentRegistry, AgentSpec
from egon2.database import Database
from egon2.exceptions import DuplicateAgentError, DynamicAgentLimitError
from egon2.executors.ssh_executor import SSHExecutor
from egon2.llm_client import LLMClient, LLMMessage
from egon2.personality import render_system_prompt
from egon2.settings import get_settings

logger = logging.getLogger(__name__)

def _extract_result(raw: str) -> str:
    """Extrahiert den Nutzteil aus LLM-Antworten.

    Fall 1: Gesamte Antwort ist JSON → `result`-Feld zurückgeben.
    Fall 2: Freitext + JSON-Trailer → Trailer abschneiden (nur wenn der
            Block tatsächlich als JSON parsebar ist).
    Fall 3: Reiner Freitext → unverändert zurückgeben.
    """
    text = raw.strip()
    # Fall 1
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "result" in parsed:
            return str(parsed["result"]).strip()
    except (ValueError, TypeError):
        pass
    # Fall 2: letzten Absatz suchen der mit { beginnt und gültiges JSON ist
    last_brace = text.rfind('\n{')
    if last_brace != -1:
        candidate = text[last_brace:].strip()
        try:
            json.loads(candidate)
            return text[:last_brace].rstrip()
        except (ValueError, TypeError):
            pass
    return text


class Intent(StrEnum):
    TASK = "task"
    NOTE = "note"
    QUESTION = "question"
    CONVERSATION = "conversation"
    CANCEL = "cancel"
    SLASH_COMMAND = "slash_command"


SLASH_COMMANDS: frozenset[str] = frozenset({
    "/status", "/stats", "/suche", "/agenten", "/hilfe",
    "/note", "/task", "/wissen",
})

CANCEL_PHRASES: tuple[str, ...] = (
    "stop", "abbrechen", "vergiss", "cancel", "nein, lass", "halt", "stopp",
)

_BUILTIN_IDS: frozenset[str] = frozenset({
    "researcher", "journalist", "it_admin", "developer", "analyst",
    "controller", "archivist", "designer", "secretary", "inspector",
})


class AgentDispatcher:
    """Phase-1-Dispatcher: Intent → Routing → Spezialist (optional)."""

    def __init__(
        self,
        db: Database,
        llm: LLMClient,
        tasks: TaskManager,
        registry: AgentRegistry,
        context: ContextManager,
        ssh_executor: SSHExecutor | None = None,
    ) -> None:
        self._db = db
        self._llm = llm
        self._tasks = tasks
        self._registry = registry
        self._ctx = context
        self._ssh = ssh_executor

    # ---------------- Public API ----------------

    async def handle(self, msg: IncomingMessage) -> str:
        """Haupteinstiegspunkt — gibt Antworttext zurück."""
        raw = msg.raw_text.strip()

        # 1) Slash-Kommandos
        if raw.startswith("/"):
            return await self._handle_slash(raw, msg)

        # 2) Cancel-Erkennung auf raw_text (H4-Fix)
        lowered = raw.lower()
        if any(lowered.startswith(p) for p in CANCEL_PHRASES):
            if not msg.metadata.get("forwarded", False):
                return await self._handle_cancel(msg)

        # 3) Intent + Spezialist klassifizieren
        intent, specialist_id = await self._classify(msg)
        logger.info(
            "dispatcher.intent_classified intent=%s specialist=%s msg=%s",
            intent, specialist_id, msg.message_id,
        )

        # 4) Routing
        if intent == Intent.NOTE:
            return await self._handle_note(raw, msg)
        if intent in (Intent.QUESTION, Intent.CONVERSATION):
            return await self._handle_direct(msg)
        if intent == Intent.TASK:
            return await self._handle_task(msg, specialist_id)
        # Fallback
        return await self._handle_direct(msg)

    # ---------------- Klassifikation ----------------

    async def _classify(self, msg: IncomingMessage) -> tuple[str, str]:
        """Ein LLM-Call → `(intent, specialist_id)`. Fallback bei JSON-Fehler."""
        prompt = (
            "Klassifiziere die folgende Nachricht. Antworte NUR mit gültigem JSON "
            "ohne Markdown-Codeblöcke.\n\n"
            f"Nachricht: {msg.raw_text[:500]}\n\n"
            "Mögliche Intents: task, note, question, conversation, cancel\n"
            "Mögliche Spezialisten (nur bei intent=task): researcher, journalist, "
            "it_admin, developer, analyst, controller, archivist, designer, "
            "secretary, inspector, dynamic\n"
            "Bei intent != task: specialist = \"direct\"\n\n"
            "JSON-Format: {\"intent\": \"...\", \"specialist\": \"...\"}"
        )
        try:
            resp = await self._llm.chat(
                messages=[LLMMessage(role="user", content=prompt)],
                max_tokens=80,
                temperature=0.0,
                fresh_context=True,
            )
            text = resp.content.strip()
            # Defensive: extrahiere JSON falls in Codeblock
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
            intent = str(data.get("intent", "conversation"))
            specialist = str(data.get("specialist", "direct"))
            return intent, specialist
        except Exception as exc:  # noqa: BLE001
            logger.warning("dispatcher.classify_fallback error=%s", exc)
            return Intent.CONVERSATION.value, "direct"

    # ---------------- Routing-Branches ----------------

    async def _handle_task(self, msg: IncomingMessage, specialist_id: str) -> str:
        task_id = await self._tasks.create(
            title=msg.raw_text[:80],
            description=msg.raw_text,
            source_channel=msg.channel.value,
            request_id=msg.message_id,
        )
        await self._tasks.start(task_id)

        agent = await self._registry.select_for_intent(specialist_id)
        if agent is None and specialist_id not in _BUILTIN_IDS and specialist_id not in ("direct", "dynamic", ""):
            agent = await self._create_dynamic_agent_for_task(msg, specialist_id)
        if agent is None:
            agent = await self._registry.get("researcher")
        if agent is None:
            await self._tasks.fail(task_id, reason="no_agent_available")
            return "Kein Spezialist verfügbar."

        settings = get_settings()
        system_context = (
            "Du bist ein Spezialist im Egon2-Ensemble. "
            "Egon2 ist bereits vollständig konfiguriert und verbunden: "
            f"Matrix ({settings.matrix_user_id} auf {settings.matrix_homeserver}), "
            "Telegram (Token konfiguriert, Whitelist aktiv), "
            f"SearXNG ({settings.searxng_url or 'konfiguriert'}). "
            "Alle Credentials sind in /opt/egon2/.env gesetzt. "
            "Frage NIEMALS nach Tokens, Zugangsdaten oder Chat-IDs — sie sind bereits konfiguriert. "
            f"Die aktuelle Anfrage kommt über den Kanal: {msg.channel.value}."
        )
        brief = json.dumps(
            {
                "task_id": task_id,
                "specialist": agent.id,
                "objective": msg.raw_text,
                "context": system_context,
                "constraints": [],
                "expected_output": "Strukturierte Antwort auf die Anfrage.",
                "work_location": agent.work_location,
            },
            ensure_ascii=False,
        )

        active = [a.id for a in await self._registry.list_active()]
        _s = get_settings()
        system_prompt = render_system_prompt(active, matrix_user_id=_s.matrix_user_id, matrix_homeserver=_s.matrix_homeserver)
        context_msgs = await self._ctx.build_context(msg, active, system_prompt)

        specialist_messages = [
            LLMMessage(role="system", content=agent.system_prompt),
            LLMMessage(role="user", content=brief),
        ]

        t0 = time.monotonic()
        try:
            resp = await asyncio.wait_for(
                self._llm.chat(
                    messages=specialist_messages,
                    max_tokens=4096,
                    temperature=0.0,
                ),
                timeout=120.0,
            )
            duration_ms = int((time.monotonic() - t0) * 1000)

            result_text = _extract_result(resp.content)
            subtasks_raw: list = []
            try:
                parsed = json.loads(resp.content)
                if isinstance(parsed, dict):
                    raw_st = parsed.get("subtasks", [])
                    if isinstance(raw_st, list):
                        subtasks_raw = raw_st
            except (ValueError, TypeError):
                pass

            if subtasks_raw:
                try:
                    result_text = await self._handle_subtasks(
                        task_id, subtasks_raw, msg, result_text
                    )
                except Exception:
                    logger.exception(
                        "dispatcher.subtasks_failed parent=%s", task_id
                    )

            await self._tasks.finish(task_id, result=result_text)
            await self._registry.bump_use_count(agent.id)
            await self._registry.record_assignment(
                task_id=task_id,
                agent_id=agent.id,
                brief=brief,
                result=result_text,
                status="done",
                tokens_input=resp.tokens_input,
                tokens_output=resp.tokens_output,
                cost_estimate=resp.cost_estimate,
                duration_ms=duration_ms,
                quality_score=4,
            )

            if len(result_text) > 300:
                reply = await self._compose_reply(result_text, msg, context_msgs)
            else:
                reply = result_text

            await self._ctx.save_exchange(
                msg.channel.value, msg.raw_text, reply
            )
            return reply

        except Exception as exc:  # noqa: BLE001
            logger.exception("dispatcher.task_failed task=%s", task_id)
            try:
                await self._tasks.fail(task_id, reason=str(exc)[:200])
            except Exception:  # noqa: BLE001 — Task evtl. schon terminal
                pass
            return f"Etwas ist schiefgelaufen. {exc}"

    async def _handle_subtasks(
        self,
        parent_task_id: str,
        subtasks_raw: list,
        msg: IncomingMessage,
        parent_result: str,
    ) -> str:
        normalized: list[dict] = []
        for entry in subtasks_raw:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title", "") or "").strip()
            description = str(entry.get("description", "") or "").strip()
            specialist = str(entry.get("specialist", "") or "").strip() or "researcher"
            if not (title or description):
                continue
            normalized.append({
                "title": title or description[:80],
                "description": description or title,
                "specialist": specialist,
            })
        if not normalized:
            return parent_result

        normalized = normalized[:5]

        coros = []
        sub_ids: list[str] = []
        for st in normalized:
            sub_id = await self._tasks.create(
                title=st["title"][:80],
                description=st["description"],
                source_channel=msg.channel.value,
                parent_task_id=parent_task_id,
            )
            sub_ids.append(sub_id)
            coros.append(self._run_subtask(sub_id, st["specialist"], st["description"]))

        results = await asyncio.gather(*coros, return_exceptions=True)

        parts: list[str] = []
        for st, res in zip(normalized, results):
            if isinstance(res, Exception):
                parts.append(f"## {st['title']}\n[Fehler: {res}]")
            else:
                parts.append(f"## {st['title']}\n{res}")

        aggregated = "\n\n".join(parts)
        combined = f"{parent_result}\n\n---\n\n{aggregated}" if parent_result else aggregated

        try:
            summary_resp = await self._llm.chat(
                messages=[
                    LLMMessage(
                        role="user",
                        content=(
                            "Fasse die folgenden Sub-Task-Ergebnisse zu einer "
                            "kohärenten Antwort zusammen:\n\n" + combined
                        ),
                    )
                ],
                max_tokens=2048,
                temperature=0.3,
                fresh_context=True,
            )
            return summary_resp.content
        except Exception as exc:  # noqa: BLE001
            logger.warning("dispatcher.subtasks_summary_failed err=%s", exc)
            return combined

    async def _run_subtask(
        self,
        task_id: str,
        specialist_id: str,
        description: str,
    ) -> str:
        agent = await self._registry.select_for_intent(specialist_id)
        if agent is None:
            agent = await self._registry.get("researcher")
        if agent is None:
            try:
                await self._tasks.fail(task_id, reason="no_agent_available")
            except Exception:  # noqa: BLE001
                pass
            return "[Kein Spezialist verfügbar.]"

        try:
            await self._tasks.start(task_id, agent_id=agent.id)
        except Exception:  # noqa: BLE001
            pass

        brief = json.dumps(
            {
                "task_id": task_id,
                "specialist": agent.id,
                "objective": description,
                "context": "",
                "constraints": ["Keine weiteren Sub-Tasks erzeugen."],
                "expected_output": "Knappe strukturierte Antwort.",
                "work_location": agent.work_location,
            },
            ensure_ascii=False,
        )

        t0 = time.monotonic()
        try:
            resp = await asyncio.wait_for(
                self._llm.chat(
                    messages=[
                        LLMMessage(role="system", content=agent.system_prompt),
                        LLMMessage(role="user", content=brief),
                    ],
                    max_tokens=2048,
                    temperature=0.0,
                ),
                timeout=90.0,
            )
            duration_ms = int((time.monotonic() - t0) * 1000)
        except Exception as exc:  # noqa: BLE001
            logger.exception("dispatcher.subtask_llm_failed task=%s", task_id)
            try:
                await self._tasks.fail(task_id, reason=str(exc)[:200])
            except Exception:  # noqa: BLE001
                pass
            return f"[Fehler: {exc}]"

        result_text = _extract_result(resp.content)

        try:
            await self._tasks.finish(task_id, result=result_text)
        except Exception:  # noqa: BLE001
            pass
        try:
            await self._registry.bump_use_count(agent.id)
            await self._registry.record_assignment(
                task_id=task_id,
                agent_id=agent.id,
                brief=brief,
                result=result_text,
                status="done",
                tokens_input=resp.tokens_input,
                tokens_output=resp.tokens_output,
                cost_estimate=resp.cost_estimate,
                duration_ms=duration_ms,
                quality_score=4,
            )
        except Exception:  # noqa: BLE001
            logger.exception("dispatcher.subtask_record_failed task=%s", task_id)
        return result_text

    async def _compose_reply(
        self,
        result: str,
        msg: IncomingMessage,
        context: list[dict[str, str]],
    ) -> str:
        """Formuliert das Spezialist-Ergebnis im Egon-Stil. Fallback: Rohtext."""
        wrapped = safe_wrap("agent_result", result)
        compose_msgs: list[dict[str, str] | LLMMessage] = list(context)
        compose_msgs.append(
            LLMMessage(
                role="user",
                content=(
                    "Fasse das folgende Ergebnis für Marco zusammen, im "
                    "trocken-britischen Egon-Stil:\n" + wrapped
                ),
            )
        )
        try:
            resp = await asyncio.wait_for(
                self._llm.chat(
                    messages=compose_msgs,
                    max_tokens=1024,
                    temperature=0.5,
                ),
                timeout=30.0,
            )
            return resp.content
        except Exception as exc:  # noqa: BLE001
            logger.warning("dispatcher.compose_fallback error=%s", exc)
            return result

    async def _create_dynamic_agent_for_task(
        self, msg: IncomingMessage, specialist_id: str
    ) -> AgentSpec | None:
        prompt = (
            f"Erstelle einen System-Prompt für einen Spezialisten mit ID "
            f"'{specialist_id}', der zu folgender Anfrage passt:\n\n"
            f"{msg.raw_text[:600]}\n\n"
            "Antworte NUR mit gültigem JSON ohne Markdown-Codeblöcke: "
            "{\"name\": \"...\", \"description\": \"...\", "
            "\"system_prompt\": \"...\", \"capabilities\": [max 4 Strings]}"
        )
        try:
            resp = await self._llm.chat(
                messages=[LLMMessage(role="user", content=prompt)],
                max_tokens=1024,
                temperature=0.2,
                fresh_context=True,
            )
            text = resp.content.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
            name = str(data.get("name", specialist_id))
            description = str(data.get("description", ""))
            system_prompt = str(data.get("system_prompt", ""))
            caps_raw = data.get("capabilities", [])
            capabilities = (
                [str(c) for c in caps_raw if c][:4]
                if isinstance(caps_raw, list)
                else []
            )
            if not system_prompt:
                return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("dispatcher.dynamic_llm_failed err=%s", exc)
            return None

        try:
            return await self._registry.create_dynamic_agent(
                agent_id=specialist_id,
                name=name,
                description=description,
                system_prompt=system_prompt,
                capabilities=capabilities,
            )
        except (DynamicAgentLimitError, DuplicateAgentError) as exc:
            logger.info(
                "dispatcher.dynamic_fallback id=%s err=%s", specialist_id, exc
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("dispatcher.dynamic_create_failed err=%s", exc)
            return None

    async def _handle_direct(self, msg: IncomingMessage) -> str:
        """Direktantwort ohne Spezialist (Fragen + Konversation)."""
        active = [a.id for a in await self._registry.list_active()]
        _s = get_settings()
        system_prompt = render_system_prompt(active, matrix_user_id=_s.matrix_user_id, matrix_homeserver=_s.matrix_homeserver)
        context_msgs = await self._ctx.build_context(msg, active, system_prompt)
        try:
            resp = await self._llm.chat(
                messages=context_msgs,
                max_tokens=1024,
                temperature=0.5,
            )
            reply = resp.content
        except Exception as exc:  # noqa: BLE001
            logger.exception("dispatcher.direct_failed")
            return f"LLM-Fehler: {exc}"
        await self._ctx.save_exchange(msg.channel.value, msg.raw_text, reply)
        return reply

    async def _handle_note(self, text: str, msg: IncomingMessage) -> str:
        note_id = uuid.uuid4().hex
        async with self._db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO notes (id, content, source_channel)
                VALUES (?, ?, ?)
                """,
                (note_id, text, msg.channel.value),
            )
            await conn.commit()
        return "Notiert."

    async def _handle_cancel(self, msg: IncomingMessage) -> str:
        task = await self._tasks.get_last_running(msg.channel.value)
        if task:
            try:
                await self._tasks.cancel(task["id"], reason="user_request")
            except Exception as exc:  # noqa: BLE001
                logger.warning("dispatcher.cancel_failed err=%s", exc)
                return "Konnte den Task nicht abbrechen."
            return f"Task abgebrochen: {task['title'][:60]}"
        return "Kein laufender Task gefunden."

    async def _handle_slash(self, raw: str, msg: IncomingMessage) -> str:
        """Phase-1-Slash-Kommandos."""
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/hilfe":
            return (
                "Egon der 2. — verfügbare Kommandos:\n"
                "/status — laufende Tasks\n"
                "/stats — Spezialist-Statistiken\n"
                "/suche <query> — Web-Recherche via SearXNG\n"
                "/agenten [rollback <id>] — Agenten-Übersicht\n"
                "/note <text> — Notiz speichern\n"
                "/hilfe — diese Übersicht\n"
                "Oder einfach auf Deutsch schreiben."
            )
        if cmd == "/status":
            recent = await self._tasks.list_recent(5)
            if not recent:
                return "Keine Tasks."
            lines = [f"[{t['status']}] {t['title'][:50]}" for t in recent]
            return "\n".join(lines)
        if cmd in ("/note", "/wissen"):
            if rest:
                return await self._handle_note(rest, msg)
            return "Bitte Text nach dem Kommando angeben."
        if cmd == "/suche":
            return await self._handle_search(rest, msg)
        if cmd == "/stats":
            return await self._handle_stats()
        if cmd == "/agenten":
            return await self._handle_agenten(rest)
        return f"Kommando {cmd} in Phase 1 noch nicht implementiert."

    async def _handle_search(self, query: str, msg: IncomingMessage) -> str:
        if not query:
            return "Bitte eine Suchanfrage angeben: /suche <query>"
        settings = get_settings()
        results: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(
                    f"{settings.searxng_url.rstrip('/')}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": "de",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                results = (data.get("results", []) or [])[:5]
        except Exception as exc:  # noqa: BLE001
            logger.warning("dispatcher.searxng_failed error=%s", exc)
            return f"SearXNG nicht erreichbar: {exc}"

        if not results:
            return f"Keine Treffer für: {query}"

        snippets: list[str] = []
        for r in results:
            title = (r.get("title") or "").strip()
            url = (r.get("url") or "").strip()
            content = (r.get("content") or "").strip()
            snippets.append(safe_wrap("searxng", f"{title}\n{url}\n{content}"))

        researcher = await self._registry.get("researcher")
        if researcher is None:
            return "\n\n".join(f"- {r.get('title')}: {r.get('url')}" for r in results)

        brief = (
            f"objective: Beantworte die Suchanfrage: {query}\n"
            f"context:\n" + "\n".join(snippets) + "\n"
            "constraints: max 5 Quellen, alle mit URL belegen\n"
            "expected_output: knappe Zusammenfassung mit Quellen"
        )
        try:
            resp = await self._llm.chat(
                messages=[
                    LLMMessage(role="system", content=researcher.system_prompt),
                    LLMMessage(role="user", content=brief),
                ],
                max_tokens=2048,
                temperature=0.2,
            )
            result_text = _extract_result(resp.content)
            await self._registry.bump_use_count(researcher.id)
            if len(result_text) > 300:
                active = [a.id for a in await self._registry.list_active()]
                system_prompt = render_system_prompt(active)
                context_msgs = await self._ctx.build_context(msg, active, system_prompt)
                return await self._compose_reply(result_text, msg, context_msgs)
            return result_text
        except Exception as exc:  # noqa: BLE001
            logger.exception("dispatcher.search_llm_failed")
            return f"LLM-Fehler bei /suche: {exc}"

    async def _handle_stats(self) -> str:
        async with self._db.connection() as conn:
            cur = await conn.execute(
                "SELECT status, COUNT(*) FROM tasks GROUP BY status"
            )
            rows = await cur.fetchall()
            await cur.close()
            status_counts = {r[0]: r[1] for r in rows}
            total = sum(status_counts.values())

            cur = await conn.execute(
                """
                SELECT id, name, use_count FROM agents
                 WHERE status IN ('active','pending_approval')
                 ORDER BY use_count DESC LIMIT 3
                """
            )
            top_rows = await cur.fetchall()
            await cur.close()

            cur = await conn.execute(
                """
                SELECT
                    COALESCE(SUM(cost_estimate), 0),
                    COALESCE(SUM(tokens_input), 0),
                    COALESCE(SUM(tokens_output), 0)
                  FROM agent_assignments
                """
            )
            sums = await cur.fetchone()
            await cur.close()

        total_cost = float(sums[0] or 0.0)
        total_in = int(sums[1] or 0)
        total_out = int(sums[2] or 0)

        lines = [
            "Egon2 — Statistiken",
            f"Tasks gesamt: {total}",
            f"  done: {status_counts.get('done', 0)}",
            f"  failed: {status_counts.get('failed', 0)}",
            f"  cancelled: {status_counts.get('cancelled', 0)}",
            f"  running: {status_counts.get('running', 0)}",
            f"  pending: {status_counts.get('pending', 0)}",
            "",
            "Top-Spezialisten (use_count):",
        ]
        if top_rows:
            for r in top_rows:
                lines.append(f"  {r[0]} ({r[1]}) — {r[2]}")
        else:
            lines.append("  (keine)")
        lines.append("")
        lines.append(f"Kosten gesamt: {total_cost:.2f} EUR")
        lines.append(f"Tokens: {total_in} in / {total_out} out")
        return "\n".join(lines)

    async def _handle_agenten(self, rest: str) -> str:
        parts = rest.split(maxsplit=1) if rest else []
        if parts and parts[0].lower() == "rollback":
            agent_id = parts[1].strip() if len(parts) > 1 else ""
            if not agent_id:
                return "Bitte agent_id angeben: /agenten rollback <id>"
            rollback = getattr(self._registry, "rollback_prompt", None)
            if rollback is None:
                return "rollback_prompt nicht implementiert."
            try:
                await rollback(agent_id)
                return f"Prompt für {agent_id} zurückgerollt."
            except Exception as exc:  # noqa: BLE001
                return f"Rollback fehlgeschlagen: {exc}"

        async with self._db.connection() as conn:
            cur = await conn.execute(
                "SELECT id, name, status, use_count FROM agents ORDER BY status, id"
            )
            rows = await cur.fetchall()
            await cur.close()

        if not rows:
            return "Keine Agenten registriert."
        lines = []
        for r in rows:
            tag = "active" if r[2] in ("active", "pending_approval") else "inactive"
            lines.append(f"[{tag}] {r[0]} — {r[1]} (use: {r[3]})")
        return "\n".join(lines)


__all__ = ["AgentDispatcher", "Intent", "SLASH_COMMANDS", "CANCEL_PHRASES"]
