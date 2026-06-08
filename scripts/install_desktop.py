#!/usr/bin/env python3
"""Install OwlLock .desktop launcher and icon for the current user.

Usage:
  python scripts/install_desktop.py [--system]

This copies the project icon into the user's icon folder and writes a
.desktop file into ~/.local/share/applications so the app appears in the
GNOME/KDE application launcher.

    The desktop entry runs the bundled launcher script so it can always find
    the project's virtual environment and source tree.
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path

APP_NAME = "OwlLock"
DESKTOP_FILENAME = "owllock.desktop"
ICON_NAME = "owllock.png"
SERVICE_FILENAME = "owllock.service"

DESKTOP_TEMPLATE = """[Desktop Entry]
Type=Application
Name=OwlLock
Comment=Lock applications and unlock with face authentication
Exec={venv_python} -m src.facelock.app
Path={project_root}
Icon={icon_path}
Terminal=false
Categories=Utility;Security;
StartupNotify=false
"""

SERVICE_TEMPLATE = """[Unit]
Description=OwlLock background service
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={launcher} --background
WorkingDirectory={workdir}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


def _launcher_path(project_root: Path) -> str:
    return str(project_root / "scripts" / "owllock-launcher.sh")


def install(user: bool = True) -> int:
    home = Path.home()
    if user:
        applications_dir = home / ".local" / "share" / "applications"
        icons_dir = home / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        systemd_dir = home / ".config" / "systemd" / "user"
    else:
        applications_dir = Path("/usr/share/applications")
        icons_dir = Path("/usr/share/icons/hicolor/256x256/apps")
        systemd_dir = Path("/usr/lib/systemd/user")

    applications_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)
    systemd_dir.mkdir(parents=True, exist_ok=True)

    project_root = Path(__file__).resolve().parents[1]
    logo_src = project_root / "assests" / "logo.png"
    if not logo_src.exists():
        print("Warning: logo.png not found in assests/; skipping icon install")
        icon_dst = "owllock"
    else:
        icon_dst_path = icons_dir / ICON_NAME
        shutil.copy2(logo_src, icon_dst_path)
        # ensure readable
        icon_dst_path.chmod(icon_dst_path.stat().st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        icon_dst = str(icon_dst_path)

    launcher = _launcher_path(project_root)
    venv_python = str(project_root / ".venv" / "bin" / "python3")

    desktop_text = DESKTOP_TEMPLATE.format(
        venv_python=venv_python,
        project_root=str(project_root),
        icon_path=icon_dst,
    )
    desktop_path = applications_dir / DESKTOP_FILENAME
    desktop_path.write_text(desktop_text, encoding="utf-8")
    desktop_path.chmod(0o644)

    service_text = SERVICE_TEMPLATE.format(launcher=launcher, workdir=str(project_root))
    service_dst = systemd_dir / SERVICE_FILENAME
    service_dst.write_text(service_text, encoding="utf-8")
    service_dst.chmod(0o644)
    if user:
        import subprocess

        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now", SERVICE_FILENAME], check=False)

    print(f"Installed {DESKTOP_FILENAME} -> {desktop_path}")
    if logo_src.exists():
        print(f"Installed icon -> {icon_dst}")
    print(f"Installed systemd service -> {service_dst}")
    print("You may need to run 'update-desktop-database' or re-login for changes to appear.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", action="store_true", help="Install system-wide (requires sudo)")
    args = parser.parse_args(argv)
    return install(user=not args.system)


if __name__ == "__main__":
    raise SystemExit(main())
