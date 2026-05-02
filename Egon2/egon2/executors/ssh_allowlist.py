"""SSH-Allowlist: Binary → Argument-Validatoren.

Argv-basierte Prüfung (kein Shell-String). Jeder Token wird gegen die
Validatoren des jeweiligen Binaries geprüft.
"""
from __future__ import annotations

import re
from typing import Callable


def _exact(*allowed: str) -> Callable[[str], bool]:
    s = frozenset(allowed)
    return lambda a: a in s


_SHELL_META = re.compile(r"[;&|<>$`\\\"'\n\r\t*?\[\]{}()!#~]")


def _no_meta(arg: str) -> bool:
    return _SHELL_META.search(arg) is None


_READ_ROOTS = ("/opt/", "/etc/", "/var/log/", "/proc/", "/sys/", "/home/", "/root/")


def _read_path(arg: str) -> bool:
    return _no_meta(arg) and any(arg.startswith(r) for r in _READ_ROOTS)


def _egon_tmp_path(arg: str) -> bool:
    return _no_meta(arg) and arg.startswith("/tmp/egon-")


def _path_token(arg: str) -> bool:
    return _no_meta(arg) and not arg.startswith("-")


def _is_int(arg: str) -> bool:
    return arg.isdigit()


_UNIT = re.compile(r"^[A-Za-z0-9@._-]+\.(service|timer|socket|target)$")


def _unit_name(arg: str) -> bool:
    return bool(_UNIT.match(arg))


_TIME_TOKEN = re.compile(r"^[0-9:\- ]+$|^(today|yesterday|now)$")


def _time_token(arg: str) -> bool:
    return bool(_TIME_TOKEN.match(arg))


_URL = re.compile(r"^https://[A-Za-z0-9._\-/?=&%:]+$")


def _https_url(arg: str) -> bool:
    return bool(_URL.match(arg))


_SSH_COMMAND_ALLOWLIST: dict[str, dict] = {
    "ls": {
        "min_args": 0, "max_args": 8,
        "args": [_exact("-la", "-l", "-a", "--color=never"), _read_path, _path_token],
        "denied_flags": frozenset({"-R", "--recursive"}),
    },
    "cat": {
        "min_args": 1, "max_args": 5,
        "args": [_read_path],
        "denied_flags": frozenset(),
    },
    "grep": {
        "min_args": 2, "max_args": 6,
        "args": [_exact("-i", "-n", "-E", "-F", "--color=never"), _no_meta, _read_path],
        "denied_flags": frozenset({"-r", "-R", "--include", "--exclude", "-e"}),
    },
    "find": {
        "min_args": 1, "max_args": 8,
        "args": [_read_path, _no_meta],
        "denied_flags": frozenset({"-exec", "-execdir", "-delete", "-fprint", "-fprintf", "-ok"}),
    },
    "echo": {
        "min_args": 0, "max_args": 5,
        "args": [_no_meta],
        "denied_flags": frozenset({"-e", "-E", "-n"}),
    },
    "curl": {
        "min_args": 1, "max_args": 6,
        "args": [_exact("-sS", "-fsSL", "--max-time", "30", "--output"), _https_url, _egon_tmp_path],
        "denied_flags": frozenset({"-X", "--request", "-d", "--data", "-T", "--upload-file",
                                   "-K", "--config", "--unix-socket", "--proxy"}),
    },
    "df": {
        "min_args": 0, "max_args": 1,
        "args": [_exact("-h")],
        "denied_flags": frozenset(),
    },
    "free": {
        "min_args": 0, "max_args": 1,
        "args": [_exact("-h", "-m")],
        "denied_flags": frozenset(),
    },
    "ps": {
        "min_args": 0, "max_args": 1,
        "args": [_exact("aux", "-ef")],
        "denied_flags": frozenset(),
    },
    "journalctl": {
        "min_args": 0, "max_args": 6,
        "args": [_exact("-u", "-n", "--since", "--no-pager"), _unit_name, _is_int, _time_token],
        "denied_flags": frozenset({"-f", "--follow", "-o", "--output", "-D", "--directory"}),
    },
    "systemctl": {
        "min_args": 1, "max_args": 4,
        "args": [_exact("status", "is-active", "is-enabled", "list-units",
                        "--type=service", "--no-pager",
                        "start", "stop", "restart", "reload",
                        "enable", "disable", "daemon-reload"), _unit_name],
        "denied_flags": frozenset({"edit", "mask", "unmask", "kill",
                                   "set-property", "import-environment"}),
    },
    "apt": {
        "min_args": 1, "max_args": 5,
        "args": [_exact("list", "--installed", "install", "update", "upgrade",
                        "autoremove", "--yes", "-y"), _no_meta],
        "denied_flags": frozenset({"remove", "purge", "dist-upgrade", "source", "build-dep"}),
    },
    "pct": {
        "min_args": 1, "max_args": 12,
        "args": [_no_meta],
        "denied_flags": frozenset(),
    },
    "uptime": {
        "min_args": 0, "max_args": 0,
        "args": [],
        "denied_flags": frozenset(),
    },
    "ip": {
        "min_args": 1, "max_args": 5,
        "args": [_exact("addr", "route", "link", "neigh", "show"), _no_meta],
        "denied_flags": frozenset({"add", "del", "flush", "replace"}),
    },
    "ss": {
        "min_args": 0, "max_args": 3,
        "args": [_exact("-tulnp", "-tlnp", "-ulnp", "-tnp", "-unp"), _no_meta],
        "denied_flags": frozenset(),
    },
    "ping": {
        "min_args": 1, "max_args": 5,
        "args": [_exact("-c", "-W", "-i"), _is_int, _no_meta],
        "denied_flags": frozenset({"-f", "--flood"}),
    },
    "apt-cache": {
        "min_args": 1, "max_args": 2,
        "args": [_exact("show", "policy"), _no_meta],
        "denied_flags": frozenset(),
    },
    "hostname": {
        "min_args": 0, "max_args": 0,
        "args": [],
        "denied_flags": frozenset(),
    },
    "uname": {
        "min_args": 0, "max_args": 1,
        "args": [_exact("-a", "-r", "-s")],
        "denied_flags": frozenset(),
    },
}

__all__ = ["_SSH_COMMAND_ALLOWLIST"]
