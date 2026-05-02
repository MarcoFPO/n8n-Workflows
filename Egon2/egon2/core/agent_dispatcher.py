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
import time
import uuid
from enum import StrEnum

from egon2.core.context_manager import ContextManager
from egon2.core.message_queue import IncomingMessage, safe_wrap
from egon2.core.task_manager import TaskManager
from egon2.agents.registry import AgentRegistry
from egon2.database import Database
from egon2.executors.ssh_executor import SSHExecutor
from egon2.llm_client import LLMClient, LLMMessage
from egon2.personality import render_system_prompt

logger = logging.getLogger(__name__)


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
        if agent is None:
            agent = await self._registry.get("researcher")
        if agent is None:
            await self._tasks.fail(task_id, reason="no_agent_available")
            return "Kein Spezialist verfügbar."

        brief = json.dumps(
            {
                "task_id": task_id,
                "specialist": agent.id,
                "objective": msg.raw_text,
                "context": "",
                "constraints": [],
                "expected_output": "Strukturierte Antwort auf die Anfrage.",
                "work_location": agent.work_location,
            },
            ensure_ascii=False,
        )

        active = [a.id for a in await self._registry.list_active()]
        system_prompt = render_system_prompt(active)
        context_msgs = await self._ctx.build_context(msg, active, system_prompt)

        specialist_messages = [
            LLMMessage(role="system", content=agent.system_prompt),
            LLMMessage(role="user", content=brief),
        ]

        t0 = time.monotonic()
        try:
            resp = await self._llm.chat(
                messages=specialist_messages,
                max_tokens=4096,
                temperature=0.0,
            )
            duration_ms = int((time.monotonic() - t0) * 1000)

            result_text = resp.content
            try:
                parsed = json.loads(resp.content)
                if isinstance(parsed, dict) and "result" in parsed:
                    result_text = str(parsed["result"])
            except (ValueError, TypeError):
                pass

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

    async def _handle_direct(self, msg: IncomingMessage) -> str:
        """Direktantwort ohne Spezialist (Fragen + Konversation)."""
        active = [a.id for a in await self._registry.list_active()]
        system_prompt = render_system_prompt(active)
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
                "/stats — Spezialist-Statistiken (folgt)\n"
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
        return f"Kommando {cmd} in Phase 1 noch nicht implementiert."


__all__ = ["AgentDispatcher", "Intent", "SLASH_COMMANDS", "CANCEL_PHRASES"]
