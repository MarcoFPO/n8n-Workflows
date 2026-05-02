"""Shell-Executor: Lokale Subprozess-Ausführung (kein Shell-Interpreter)."""
from __future__ import annotations

import asyncio
import shlex
import time
from pathlib import Path

import structlog

from egon2.executors.result import ExecResult

log = structlog.get_logger("egon2.shell")

DEFAULT_TIMEOUT_S: float = 120.0
MAX_OUTPUT_BYTES: int = 1 * 1024 * 1024

ALLOWED_COMMANDS: frozenset[str] = frozenset({
    "ls", "cat", "grep", "find", "echo", "curl", "python3",
})


class CommandNotAllowedError(Exception):
    pass


class ShellExecutor:
    def __init__(self, cwd: Path, env: dict[str, str] | None = None) -> None:
        self._cwd = cwd
        self._env = env or {}

    async def run(self, command: str, timeout: float = DEFAULT_TIMEOUT_S) -> ExecResult:
        argv = shlex.split(command, posix=True)
        if not argv:
            raise CommandNotAllowedError("empty command")
        binary = Path(argv[0]).name
        if binary not in ALLOWED_COMMANDS:
            raise CommandNotAllowedError(f"'{binary}' not in whitelist")

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._cwd),
                env={**self._env},
            )
        except (FileNotFoundError, PermissionError) as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return ExecResult(
                exit_code=-2, stdout="", stderr="", duration_ms=duration_ms,
                command=command, host="local", timed_out=False, error=str(exc),
            )

        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
            duration_ms = int((time.monotonic() - start) * 1000)
            return ExecResult(
                exit_code=-1, stdout="", stderr="", duration_ms=duration_ms,
                command=command, host="local", timed_out=True,
                error=f"timeout after {timeout}s",
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            exit_code=int(proc.returncode or 0),
            stdout=_truncate_bytes(stdout_b),
            stderr=_truncate_bytes(stderr_b),
            duration_ms=duration_ms, command=command, host="local", timed_out=False,
        )


def _truncate_bytes(b: bytes) -> str:
    if len(b) <= MAX_OUTPUT_BYTES:
        return b.decode("utf-8", errors="replace")
    return b[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace") + " [...truncated]"


__all__ = ["ShellExecutor", "CommandNotAllowedError"]
