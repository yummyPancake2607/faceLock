"""Application scanner for Linux .desktop files.

Provides helpers to find and parse .desktop files under common locations
and return a normalized list of application metadata.
"""
from __future__ import annotations

import glob
import json
import os
import shlex
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DEFAULT_DESKTOP_DIRS = [
    "/usr/share/applications",
    "/usr/local/share/applications",
    os.path.expanduser("~/.local/share/applications"),
]


def find_desktop_files(paths: Optional[Iterable[str]] = None) -> List[str]:
    """Return a list of .desktop file paths found under the given directories."""
    paths = list(paths) if paths is not None else DEFAULT_DESKTOP_DIRS
    files: List[str] = []
    for p in paths:
        p = os.path.expanduser(p)
        if not os.path.isdir(p):
            continue
        pattern = os.path.join(p, "**", "*.desktop")
        files.extend(glob.glob(pattern, recursive=True))
    return sorted(set(files))


def _parse_exec(exec_value: str) -> str:
    """Return the executable command from an Exec= value, stripping placeholders.

    Examples:
      "blender %F" -> "blender"
      "/usr/bin/code --unity-launch %U" -> "/usr/bin/code"
    """
    if not exec_value:
        return ""
    try:
        parts = shlex.split(exec_value)
    except Exception:
        parts = exec_value.split()
    if not parts:
        return ""
    # strip desktop entry field codes like %U %u %F %f
    cmd = parts[0]
    return cmd


def parse_desktop_file(path: str) -> Optional[Dict]:
    """Parse a single .desktop file and return normalized metadata.

    Returns None if parsing fails or required fields are missing.
    """
    p = Path(path)
    if not p.exists():
        return None
    parser = ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        with p.open("r", encoding="utf-8", errors="ignore") as fh:
            parser.read_file(fh)
    except Exception:
        return None

    if "Desktop Entry" not in parser:
        return None

    ent = parser["Desktop Entry"]
    name = ent.get("Name") or ent.get("GenericName") or p.stem
    exec_raw = ent.get("Exec", "")
    exec_cmd = _parse_exec(exec_raw)
    icon = ent.get("Icon")
    categories = [c.strip() for c in ent.get("Categories", "").split(";") if c.strip()]
    terminal = ent.get("Terminal", "false").lower() in ("true", "1", "yes")

    return {
        "desktop_file": str(p),
        "name": name,
        "exec": exec_cmd,
        "exec_raw": exec_raw,
        "icon": icon,
        "categories": categories,
        "terminal": terminal,
    }


def scan_applications(paths: Optional[Iterable[str]] = None) -> List[Dict]:
    """Scan given directories (or defaults) and return parsed applications.

    The result is a list of application metadata dicts.
    """
    desktop_files = find_desktop_files(paths)
    apps: List[Dict] = []
    for f in desktop_files:
        parsed = parse_desktop_file(f)
        if not parsed:
            continue
        # skip entries without a usable exec command
        if not parsed.get("exec"):
            continue
        apps.append(parsed)
    # sort by visible name for deterministic output
    apps.sort(key=lambda a: (a.get("name") or "").lower())
    return apps


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Scan desktop files and print JSON list")
    ap.add_argument("paths", nargs="*", help="Directories to scan (optional)")
    args = ap.parse_args()
    paths = args.paths if args.paths else None
    apps = scan_applications(paths)
    print(json.dumps(apps, indent=2, ensure_ascii=False))
