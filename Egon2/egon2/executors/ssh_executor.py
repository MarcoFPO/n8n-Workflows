"""SSH-Executor: Argv-basierte Remote-Ausführung via asyncssh.

Security-Modell:
- Argv-Liste statt Shell-String (kein /bin/sh -c)
- Allowlist-Validierung vor jedem Connect
- pct: Vollzugriff (autonomes Handlungsmandat)
"""
from __future__ import annotations

import asyncio
import shlex
import time
from pathlib import Path

import asyncssh
import structlog

from egon2.executors.result import ExecResult
from egon2.executors.ssh_allowlist import _SSH_COMMAND_ALLOWLIST

log = structlog.get_logger("egon2.ssh")

DEFAULT_TIMEOUT_S: float = 120.0
MAX_OUTPUT_BYTES: int = 1 * 1024 * 1024  # 1 MiB


class SecurityViolation(Exception):
    """Argv hat Allowlist-Validierung nicht bestanden."""


class SSHExecutor:
    def __init__(
        self,
        key_path: Path,
        known_hosts: Path | None,
        max_connections: int = 8,
    ) -> None:
        self._key_path = key_path
        self._known_hosts = known_hosts
        self._sem = asyncio.Semaphore(max_connections)
        self._conns: dict[str, asyncssh.SSHClientConnection] = {}
        self._target_locks: dict[str, asyncio.Lock] = {}
        self._dict_lock = asyncio.Lock()

    # ---------------- Validation ----------------

    def _validate_argv(self, argv: list[str], allowlist: dict[str, dict]) -> None:
        if not argv:
            raise SecurityViolation("leeres Kommando")
        binary = Path(argv[0]).name  # blockt Bypass via /usr/bin/<cmd>
        spec = allowlist.get(binary)
        if spec is None:
            raise SecurityViolation(f"Binary nicht in Allowlist: {binary!r}")

        rest = argv[1:]
        if not (spec["min_args"] <= len(rest) <= spec["max_args"]):
            raise SecurityViolation(
                f"{binary}: {len(rest)} Args außerhalb [{spec['min_args']}, {spec['max_args']}]"
            )

        denied: frozenset[str] = spec["denied_flags"]
        validators: list = spec["args"]

        for tok in rest:
            if tok in denied:
                raise SecurityViolation(f"{binary}: verbotener Token: {tok!r}")
            if validators and not any(v(tok) for v in validators):
                raise SecurityViolation(f"{binary}: Token verletzt Pattern: {tok!r}")

    # ---------------- Public API ----------------

    async def run_argv(
        self,
        host: str,
        argv: list[str],
        user: str = "egon",
        port: int = 22,
        timeout: float = DEFAULT_TIMEOUT_S,
        allowlist: dict[str, dict] | None = None,
    ) -> ExecResult:
        """Argv-Ausführung auf Remote-Host — kein Shell-Interpreter."""
        target = f"{user}@{host}:{port}"
        start = time.monotonic()
        cmd_repr = shlex.join(argv)
        active_allowlist = allowlist or _SSH_COMMAND_ALLOWLIST

        try:
            self._validate_argv(argv, active_allowlist)
        except SecurityViolation as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            log.warning("ssh.security_violation", host=target, argv=argv, error=str(exc))
            return ExecResult(
                exit_code=-3, stdout="", stderr="",
                duration_ms=duration_ms, command=cmd_repr, host=target,
                timed_out=False, error=f"security: {exc}",
            )

        async with self._sem:
            try:
                conn = await self._connect(host, user, port)
                proc = await asyncio.wait_for(
                    conn.run(argv, check=False, env={}),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning("ssh.timeout", host=target, argv=argv, ms=duration_ms)
                await self._drop(target)
                return ExecResult(
                    exit_code=-1, stdout="", stderr="",
                    duration_ms=duration_ms, command=cmd_repr, host=target,
                    timed_out=True, error=f"timeout after {timeout}s",
                )
            except (asyncssh.Error, OSError) as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning("ssh.error", host=target, argv=argv, error=str(exc))
                await self._drop(target)
                return ExecResult(
                    exit_code=-2, stdout="", stderr="",
                    duration_ms=duration_ms, command=cmd_repr, host=target,
                    timed_out=False, error=str(exc),
                )

        duration_ms = int((time.monotonic() - start) * 1000)
        log.debug("ssh.ok", host=target, cmd=cmd_repr, ms=duration_ms, rc=proc.exit_status)
        return ExecResult(
            exit_code=int(proc.exit_status or 0),
            stdout=_truncate(proc.stdout or ""),
            stderr=_truncate(proc.stderr or ""),
            duration_ms=duration_ms, command=cmd_repr, host=target,
            timed_out=False,
        )

    async def aclose(self) -> None:
        async with self._dict_lock:
            for conn in self._conns.values():
                conn.close()
            for conn in self._conns.values():
                try:
                    await conn.wait_closed()
                except Exception:  # noqa: BLE001
                    pass
            self._conns.clear()
            self._target_locks.clear()

    # ---------------- Internals ----------------

    async def _connect(
        self, host: str, user: str, port: int
    ) -> asyncssh.SSHClientConnection:
        target = f"{user}@{host}:{port}"
        async with self._dict_lock:
            lock = self._target_locks.setdefault(target, asyncio.Lock())
        async with lock:
            conn = self._conns.get(target)
            if conn is not None and not conn.is_closed():
                return conn
            known_hosts: str | None = str(self._known_hosts) if self._known_hosts else None
            conn = await asyncssh.connect(
                host=host,
                port=port,
                username=user,
                client_keys=[str(self._key_path)],
                known_hosts=known_hosts,
                connect_timeout=15,
                keepalive_interval=30,
                keepalive_count_max=3,
            )
            self._conns[target] = conn
            return conn

    async def _drop(self, target: str) -> None:
        async with self._dict_lock:
            conn = self._conns.pop(target, None)
            self._target_locks.pop(target, None)
        if conn is not None:
            conn.close()
            try:
                await conn.wait_closed()
            except Exception:  # noqa: BLE001
                pass


def _truncate(s: str) -> str:
    b = s.encode("utf-8", errors="replace")
    if len(b) <= MAX_OUTPUT_BYTES:
        return s
    return b[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace") + " [...truncated]"


__all__ = ["SSHExecutor", "SecurityViolation"]
