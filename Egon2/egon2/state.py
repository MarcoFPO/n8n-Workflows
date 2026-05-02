"""AppState — zentraler Container aller Laufzeit-Singletons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from egon2.agents.registry import AgentRegistry
from egon2.core.agent_dispatcher import AgentDispatcher
from egon2.core.context_manager import ContextManager
from egon2.core.message_queue import MessageConsumer, MessageQueue
from egon2.core.scheduler import EgonScheduler
from egon2.core.task_manager import TaskManager
from egon2.database import Database
from egon2.executors.shell_executor import ShellExecutor
from egon2.executors.ssh_executor import SSHExecutor
from egon2.interfaces.matrix_bot import MatrixBot
from egon2.interfaces.telegram_bot import TelegramBot
from egon2.llm_client import LLMClient
from egon2.settings import Settings


@dataclass
class AppState:
    settings: Settings
    db: Database | None = None
    llm: LLMClient | None = None
    queue: MessageQueue | None = None
    consumer: MessageConsumer | None = None
    tasks: TaskManager | None = None
    registry: AgentRegistry | None = None
    context: ContextManager | None = None
    dispatcher: AgentDispatcher | None = None
    matrix_bot: MatrixBot | None = None
    telegram_bot: TelegramBot | None = None
    scheduler: EgonScheduler | None = None
    ssh_executor: SSHExecutor | None = None
    shell_executor: ShellExecutor | None = None
    knowledge: Any | None = None  # Phase 3


__all__ = ["AppState"]
