"""FaceLock GUI application entrypoint."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.facelock.database import db
from src.facelock.auth.system_auth import require_system_password
from src.facelock.gui.main_window import build_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch the FaceLock GUI")
    parser.add_argument("--db", dest="db_path", help="SQLite database path")
    parser.add_argument(
        "--scan-path",
        dest="scan_paths",
        action="append",
        default=None,
        help="Additional .desktop directory to scan (can be repeated)",
    )
    args = parser.parse_args(argv)

    db.init_db(args.db_path)
    app, window = build_app(scan_paths=args.scan_paths, db_path=args.db_path)
    if not require_system_password(window):
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
