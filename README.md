# OwlLock

OwlLock is a Linux desktop security tool that locks applications and unlocks them using **face recognition**. A background guardian monitors for locked app launches and prompts for face (or password) authentication.

## One-Line Install

```bash
git clone <repo-url> && cd facelock
bash install.sh
```

That single command will:

- detect your Linux distro and install system dependencies (cmake, boost, mesa, etc.)
- verify your camera permissions (video group)
- create a Python virtual environment (`.venv`)
- install OwlLock and all its Python dependencies (dlib, face-recognition, OpenCV, PyQt6)
- install the desktop launcher, app icon, and systemd background service
- enable and start the background guardian service

## Requirements

- **Python 3.10+** (tested up to 3.14)
- **Linux** with systemd (for the background service)
- A working webcam
- An X11 or Wayland desktop environment (GNOME, KDE, etc.)

## Usage

| Command | What it does |
|---------|-------------|
| `bash install.sh` | Full install |
| `bash install.sh --uninstall` | Remove all OwlLock files |
| `bash install.sh --no-system-deps` | Skip system package install |
| `bash install.sh --help` | Show help |

### Launching

- Open **OwlLock** from the application menu
- Or run: `.venv/bin/python -m src.facelock.app`

The GUI lets you:
1. Register your face (20 samples → saved to SQLite)
2. Browse installed applications
3. Lock/unlock any app with a toggle
4. Manage face profiles (list/delete)

### Background Service

The background guardian runs as a systemd user service. It monitors `/proc` every 1.5 seconds. When a locked app is detected:

- `SIGSTOP` pauses the process
- A face unlock dialog appears
- On success: `SIGCONT` resumes the app
- On failure/denial: `SIGKILL` terminates the app

Check status:

```bash
systemctl --user status owllock.service
```

## Uninstall

```bash
bash install.sh --uninstall
```

This removes: desktop entry, icon, systemd service, cache, and optionally the database and virtual environment.

## Project Layout

```
├── install.sh                  # One-line installer
├── pyproject.toml              # Python package config
├── scripts/
│   ├── auth-prompt.py          # Standalone face auth dialog (spawned by guardian)
│   ├── install_desktop.py      # Installs .desktop, icon, systemd service
│   └── owllock-launcher.sh     # Launcher wrapper with env setup
├── packaging/
│   ├── owllock.desktop         # Desktop entry template
│   └── owllock.service         # Systemd service template
├── src/facelock/               # Application source
│   ├── app.py                  # Entry point
│   ├── auth/                   # Camera, face detection, encoding, guardian
│   ├── database/               # SQLite storage
│   ├── gui/                    # PyQt6 dialogs and main window
│   └── services/               # Desktop file scanner
└── assests/
    └── logo.png                # App icon
```
