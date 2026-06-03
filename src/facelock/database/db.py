"""SQLite-backed storage helpers for FaceLock.

This module provides a small, dependency-free wrapper around `sqlite3`
to store user encodings, locked applications, and access logs.
"""
from __future__ import annotations

import io
import os
import sqlite3
import datetime
from typing import Iterable, List, Optional, Dict

import numpy as np

DEFAULT_DB_PATH = os.path.expanduser("~/.facelock/facelock.db")


def _ensure_parent(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    db_path = db_path or DEFAULT_DB_PATH
    _ensure_parent(db_path)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database schema if missing."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            label TEXT UNIQUE,
            encoding BLOB,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS locked_apps (
            id INTEGER PRIMARY KEY,
            name TEXT,
            exec TEXT,
            icon TEXT,
            locked INTEGER DEFAULT 0,
            desktop_file TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY,
            ts TEXT,
            app_name TEXT,
            result TEXT,
            note TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def _np_to_blob(arr: np.ndarray) -> bytes:
    bio = io.BytesIO()
    # use numpy's binary format
    np.save(bio, arr, allow_pickle=False)
    return bio.getvalue()


def _blob_to_np(blob: bytes) -> np.ndarray:
    bio = io.BytesIO(blob)
    bio.seek(0)
    return np.load(bio, allow_pickle=False)


def save_user_encoding(label: str, encoding: np.ndarray, db_path: Optional[str] = None) -> None:
    """Save or update a user's encoding vector."""
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    blob = _np_to_blob(encoding)
    ts = datetime.datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO users(label, encoding, created_at) VALUES(?,?,?) ON CONFLICT(label) DO UPDATE SET encoding=excluded.encoding, created_at=excluded.created_at",
        (label, blob, ts),
    )
    conn.commit()
    conn.close()


def get_user_encoding(label: str, db_path: Optional[str] = None) -> Optional[np.ndarray]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT encoding FROM users WHERE label = ?", (label,))
    row = cur.fetchone()
    conn.close()
    if not row or row[0] is None:
        return None
    return _blob_to_np(row[0])


def list_users(db_path: Optional[str] = None) -> List[Dict]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, label, created_at FROM users ORDER BY label")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_locked_app(name: str, exec_cmd: str, icon: Optional[str] = None, desktop_file: Optional[str] = None, locked: bool = True, db_path: Optional[str] = None) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO locked_apps(name, exec, icon, locked, desktop_file) VALUES(?,?,?,?,?)",
        (name, exec_cmd, icon, 1 if locked else 0, desktop_file),
    )
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return rowid


def list_locked_apps(db_path: Optional[str] = None) -> List[Dict]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, name, exec, icon, locked, desktop_file FROM locked_apps ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    out: List[Dict] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "name": r["name"],
                "exec": r["exec"],
                "icon": r["icon"],
                "locked": bool(r["locked"]),
                "desktop_file": r["desktop_file"],
            }
        )
    return out


def set_locked(app_id: int, locked: bool, db_path: Optional[str] = None) -> None:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE locked_apps SET locked = ? WHERE id = ?", (1 if locked else 0, app_id))
    conn.commit()
    conn.close()


def add_access_log(app_name: str, result: str, note: Optional[str] = None, db_path: Optional[str] = None) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    ts = datetime.datetime.utcnow().isoformat()
    cur.execute("INSERT INTO access_logs(ts, app_name, result, note) VALUES(?,?,?,?)", (ts, app_name, result, note))
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return rowid


def query_access_logs(limit: int = 100, db_path: Optional[str] = None) -> List[Dict]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, ts, app_name, result, note FROM access_logs ORDER BY ts DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Inspect FaceLock database")
    ap.add_argument("--db", help="Database path (optional)")
    args = ap.parse_args()
    init_db(args.db)
    users = list_users(args.db)
    apps = list_locked_apps(args.db)
    logs = query_access_logs(50, args.db)
    print(json.dumps({"users": users, "locked_apps": apps, "logs": logs}, indent=2, ensure_ascii=False))
