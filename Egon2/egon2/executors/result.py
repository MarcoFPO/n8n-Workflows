from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    command: str
    host: str
    timed_out: bool
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def as_text(self) -> str:
        parts: list[str] = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(f"[stderr]\n{self.stderr}")
        if self.error:
            parts.append(f"[error] {self.error}")
        if not parts:
            parts.append(f"exit_code={self.exit_code}")
        return "\n".join(parts)


__all__ = ["ExecResult"]
