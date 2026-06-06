"""Save and restore display environment variables for auth-prompt."""

from __future__ import annotations

import os
from pathlib import Path

DISPLAY_VARS = ("DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")
CACHE_DIR = Path.home() / ".cache" / "owllock"
DISPLAY_ENV_FILE = CACHE_DIR / "display.env"


def save_display_env() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for key in DISPLAY_VARS:
        val = os.environ.get(key, "")
        lines.append(f"{key}={val}")
    DISPLAY_ENV_FILE.write_text("\n".join(lines), encoding="utf-8")


def load_display_env() -> dict[str, str]:
    if not DISPLAY_ENV_FILE.exists():
        return {}
    env: dict[str, str] = {}
    for line in DISPLAY_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line:
            key, _, val = line.partition("=")
            env[key] = val
    return env


def apply_display_env(env: dict[str, str]) -> None:
    for key in DISPLAY_VARS:
        if key in env and env[key]:
            os.environ.setdefault(key, env[key])
