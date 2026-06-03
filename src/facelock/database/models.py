"""Dataclasses for FaceLock database records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserRecord:
    id: int
    label: str
    created_at: str


@dataclass
class LockedApp:
    id: int
    name: str
    exec: str
    icon: Optional[str]
    locked: bool
    desktop_file: Optional[str]


@dataclass
class AccessLog:
    id: int
    ts: str
    app_name: str
    result: str
    note: Optional[str]
