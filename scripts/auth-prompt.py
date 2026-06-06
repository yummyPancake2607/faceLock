#!/usr/bin/env python3
"""Standalone auth prompt launched by the background guardian.

Called when a locked app is detected. Shows the face unlock dialog
using the user's display server (Wayland/X11), independent of the
background guardian's headless Qt platform.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure we can import from src/
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Restore display environment so the dialog shows on the user's desktop
_display = os.environ.get("OWLLOCK_DISPLAY") or os.environ.get("DISPLAY", "")
_wayland = os.environ.get("OWLLOCK_WAYLAND_DISPLAY") or os.environ.get("WAYLAND_DISPLAY", "")

# Fall back to saved display env from the GUI session
if not _display and not _wayland:
    try:
        from src.facelock.auth.display_env import load_display_env, apply_display_env
        saved = load_display_env()
        apply_display_env(saved)
        _display = os.environ.get("DISPLAY", "")
        _wayland = os.environ.get("WAYLAND_DISPLAY", "")
    except Exception:
        pass

# Default fallback for common X11 setups
if not _display and not _wayland:
    _display = ":0"

# Remove any forced offscreen platform
os.environ.pop("QT_QPA_PLATFORM", None)
# Set the display back if the launcher saved it
if _display:
    os.environ["DISPLAY"] = _display
if _wayland:
    os.environ["WAYLAND_DISPLAY"] = _wayland

from PyQt6.QtWidgets import QApplication
from src.facelock.database import db
from src.facelock.auth.launch_auth import FaceUnlockDialog
from src.facelock.auth.system_auth import require_system_password
from src.facelock.gui.theme import apply_theme


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("app_name", help="Name of the locked application")
    parser.add_argument("--db", dest="db_path", help="SQLite database path")
    args = parser.parse_args()

    db.init_db(args.db_path)

    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    dialog = FaceUnlockDialog(app_name=args.app_name, db_path=args.db_path)
    if dialog.exec() == FaceUnlockDialog.DialogCode.Accepted:
        print("face")
        return 0

    if require_system_password(None, message=f"Face not authenticated for {args.app_name}. Enter your password to continue."):
        print("password")
        return 0

    print("denied")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
