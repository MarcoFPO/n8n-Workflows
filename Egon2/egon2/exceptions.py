"""Egon2 Exception-Hierarchie.

Siehe LLD-Architektur §5.1 für die vollständige Spezifikation.
Alle Egon2-Fehler erben von Egon2Error. Subklassen sind nach Domäne gruppiert
(LLM, Datenbank, Agenten, Tasks, SSH, Shell, Knowledge, Interface, SearXNG).
"""

from __future__ import annotations


class Egon2Error(Exception):
    """Basis-Exception für alle Egon2-Fehler."""


# --- Konfiguration ---
class ConfigurationError(Egon2Error):
    """Settings-Validierung fehlgeschlagen oder Pflichtwert fehlt."""


# --- Datenbank ---
class DatabaseError(Egon2Error):
    """SQLite-Fehler (aiosqlite)."""


# --- Tasks ---
class TaskError(DatabaseError):
    """Basis für Task-spezifische DB-Fehler."""


class TaskNotFoundError(TaskError):
    """Task-ID nicht in DB."""


class InvalidTaskTransitionError(TaskError):
    """Ungültiger Status-Übergang im Task-Lifecycle."""


class ParentTaskNotFoundError(TaskError):
    """parent_task_id zeigt auf einen nicht existenten Task."""


# --- LLM ---
class LLMError(Egon2Error):
    """Basis für LLM-Backend-Fehler."""


class LLMClientError(LLMError):
    """HTTP-, Connection- oder Parse-Fehler vom LLM-Backend.

    Attribute:
        status_code: int | None — HTTP-Status wenn verfügbar
        attempt: int — Retry-Versuch bei dem der Fehler aufgetreten ist
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        attempt: int = 0,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.attempt = attempt


class LLMRateLimitError(LLMClientError):
    """HTTP 429 — Rate Limit.

    Attribute:
        retry_after: float | None — Sekunden aus dem Retry-After-Header
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class LLMParseError(LLMError):
    """Response-Format unbekannt, leer oder JSON-Decoding fehlgeschlagen."""


class LLMTimeoutError(LLMError):
    """READ_TIMEOUT überschritten."""


# --- Agenten ---
class AgentError(Egon2Error):
    """Basis für Agenten-Fehler."""


class NoAgentFoundError(AgentError):
    """Kein aktiver Spezialist für die geforderten Capabilities gefunden."""


class AgentTimeoutError(AgentError):
    """Spezialist-LLM-Call hat das Timeout überschritten."""


class SystemPromptTooLargeError(Egon2Error):
    """Der zusammengebaute System-Prompt überschreitet das Token-Budget."""


class DynamicAgentLimitError(AgentError):
    """Maximale Anzahl dynamischer Agenten (20) erreicht."""


class DuplicateAgentError(AgentError):
    """Ein zu ähnlicher Agent existiert bereits."""


# --- SSH ---
class SSHError(Egon2Error):
    """Basis für SSH-Executor-Fehler."""


class SSHConnectionError(SSHError):
    """Host nicht erreichbar oder Authentifizierung fehlgeschlagen."""


class SSHTimeoutError(SSHError):
    """COMMAND_TIMEOUT überschritten."""


# --- Shell ---
class ShellError(Egon2Error):
    """Basis für Shell-Executor-Fehler."""


class CommandNotAllowedError(ShellError):
    """Kommando nicht in der Whitelist."""


class ConfirmationRequiredError(ShellError):
    """Bestätigung für destruktives Kommando fehlt oder ist abgelaufen."""


# --- Knowledge ---
class KnowledgeError(Egon2Error):
    """Basis für Knowledge-Store-Fehler."""


class KnowledgeClientError(KnowledgeError):
    """HTTP-Fehler oder Timeout bei der Kommunikation mit dem MCP-Server."""


class KnowledgeEntryNotFoundError(KnowledgeError):
    """Entry-ID nicht im Knowledge Store vorhanden."""


# --- Interface ---
class InterfaceError(Egon2Error):
    """Basis für Interface-Fehler (Matrix, Telegram)."""


class MatrixSendError(InterfaceError):
    """Senden einer Nachricht an den Matrix-Homeserver fehlgeschlagen."""


class TelegramSendError(InterfaceError):
    """Senden einer Nachricht an die Telegram Bot API fehlgeschlagen."""


# --- SearXNG ---
class SearXNGError(Egon2Error):
    """Basis für SearXNG-Fehler."""


class SearXNGClientError(SearXNGError):
    """HTTP-Fehler oder Timeout vom SearXNG-Backend."""


class SearXNGNoResultsError(SearXNGError):
    """SearXNG hat keine Ergebnisse zurückgegeben (non-fatal)."""


__all__ = [
    "Egon2Error",
    "ConfigurationError",
    "DatabaseError",
    "TaskError",
    "TaskNotFoundError",
    "InvalidTaskTransitionError",
    "ParentTaskNotFoundError",
    "LLMError",
    "LLMClientError",
    "LLMRateLimitError",
    "LLMParseError",
    "LLMTimeoutError",
    "AgentError",
    "NoAgentFoundError",
    "AgentTimeoutError",
    "SystemPromptTooLargeError",
    "DynamicAgentLimitError",
    "DuplicateAgentError",
    "SSHError",
    "SSHConnectionError",
    "SSHTimeoutError",
    "ShellError",
    "CommandNotAllowedError",
    "ConfirmationRequiredError",
    "KnowledgeError",
    "KnowledgeClientError",
    "KnowledgeEntryNotFoundError",
    "InterfaceError",
    "MatrixSendError",
    "TelegramSendError",
    "SearXNGError",
    "SearXNGClientError",
    "SearXNGNoResultsError",
]
