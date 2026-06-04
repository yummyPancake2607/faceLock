# OwlLock

OwlLock is a Linux desktop security tool that keeps a background guardian running all the time and only opens the GUI when you need it.

The security model is simple:

- the background service starts automatically after boot through systemd user lingering
- the service watches for locked applications in the background
- the GUI is launched only on demand
- when the GUI opens, it asks for your password first

## How It Works

OwlLock is split into three parts:

1. a background service that stays active after boot
2. a launcher wrapper that always runs from the project root and virtual environment
3. a GUI that handles face enrollment, app locking, and password-gated management

The background service is installed as a systemd user service. During installation, OwlLock also enables user lingering, which allows the user service to start right after boot instead of waiting for a manual login session.

The GUI is not started automatically. You open it from the application menu only when you want to manage locked apps, register faces, or change settings.

## One-Line Install

After cloning the repository, run:

```bash
bash install.sh
```

That single command will:

- create or reuse the local `.venv`
- install the Python package in editable mode
- install the desktop launcher and icon
- install the background systemd user service
- enable user lingering so the service can start after boot
- enable and start the OwlLock service for the current user

## What Gets Installed

The installer writes these user files:

- `~/.local/share/applications/owllock.desktop`
- `~/.local/share/icons/hicolor/256x256/apps/owllock.png`
- `~/.config/systemd/user/owllock.service`

It also enables the user service so it starts automatically on boot.

## Launching OwlLock

- To open the GUI, use the app menu and click **OwlLock**
- The GUI asks for your password before it opens
- The background security service keeps running even when the GUI is closed

## Manual Commands

If you want to run the pieces directly:

```bash
# install everything
bash install.sh

# inspect the service
systemctl --user status owllock.service

# restart the background guardian
systemctl --user restart owllock.service

# open the GUI from the project
./.venv/bin/python3 -m src.facelock.app
```

## Requirements

OwlLock expects a Linux desktop environment with:

- Python 3
- systemd user services
- a working webcam for face authentication
- the system packages required by Qt/OpenCV/face-recognition

If the GUI does not show immediately after install, log out and back in once so the desktop menu refreshes.

## Project Layout

- `install.sh` - one-line installer
- `scripts/install_desktop.py` - installs the launcher, icon, and service
- `scripts/owllock-launcher.sh` - wrapper that runs OwlLock from the repo root
- `packaging/owllock.desktop` - desktop menu entry
- `packaging/owllock.service` - systemd user service for the background guardian
- `src/facelock/` - application code

## Notes

- The GUI is intentionally not part of the boot process.
- The background guardian is the always-on security component.
- If you want true pre-login system-wide enforcement, that is a separate system service design from the current user-service setup.
