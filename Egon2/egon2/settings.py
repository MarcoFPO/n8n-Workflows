"""Egon2 Settings — Pydantic-Settings-basierte Konfiguration.

Werte können per Umgebungsvariable oder `.env`-Datei überschrieben werden.
Singleton-Zugriff via `get_settings()` (lru_cache).

Beispiele:
    EGON2_LLM_API_URL=http://...           # einzelner Wert
    EGON2_TELEGRAM_WHITELIST='[123,456]'   # JSON-Liste

Hinweis: Es gibt KEIN festes Präfix — pydantic-settings liest die Felder
1:1 aus den Environment-Variablen (also `LLM_API_URL`, `MATRIX_PASSWORD`, …).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Globale Egon2-Konfiguration."""

    # --- LLM ---
    llm_api_url: str = "http://10.1.1.105:3001/v1/chat/completions"
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 4096
    llm_timeout: float = 60.0

    # --- Matrix (optional — soft-fail wenn leer) ---
    matrix_homeserver: str = "https://matrix.doehlercomputing.de"
    matrix_user_id: str = "@egon:doehlercomputing.de"
    matrix_password: str = ""
    matrix_device_name: str = "Egon2-Bot"

    # --- Telegram (optional — soft-fail wenn leer) ---
    telegram_token: str = ""
    telegram_whitelist: list[int] = Field(default_factory=list)

    # --- Externe Dienste ---
    knowledge_url: str = "http://10.1.1.107:8080"
    searxng_url: str = "http://10.1.1.204"

    # --- Pfade ---
    data_dir: Path = Path("/opt/egon2/data")
    backup_dir: Path = Path("/opt/egon2/backup")
    scheduler_db_path: Path = Path("/opt/egon2/data/scheduler.db")
    ssh_key_path: str = "/opt/egon2/.ssh/id_ed25519"
    ssh_known_hosts: str = ""  # leer = known_hosts-Prüfung deaktiviert

    # --- Limits ---
    daily_cost_eur_soft_limit: float = 5.0
    message_queue_maxsize: int = 100
    consumer_semaphore_size: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def db_path(self) -> Path:
        """Pfad zur Haupt-SQLite-Datei egon2.db."""
        return self.data_dir / "egon2.db"

    @property
    def matrix_enabled(self) -> bool:
        return bool(self.matrix_password)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton-Zugriff auf die Settings.

    Per `@lru_cache` einmalig instanziiert. Tests können den Cache via
    `get_settings.cache_clear()` zurücksetzen.
    """
    return Settings()


__all__ = ["Settings", "get_settings"]
