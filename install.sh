#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

log() {
    printf '\033[1;36m[%s]\033[0m %s\n' "OwlLock" "$1"
}

die() {
    printf '\033[1;31m[%s]\033[0m %s\n' "OwlLock" "$1" >&2
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

log "Starting OwlLock installation from $PROJECT_ROOT"
require_cmd "$PYTHON_BIN"

if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

log "Upgrading pip tooling"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

log "Installing OwlLock into the virtual environment"
"$VENV_DIR/bin/python" -m pip install -e "$PROJECT_ROOT"

if command -v loginctl >/dev/null 2>&1; then
    log "Enabling user lingering so OwlLock can start after boot"
    loginctl enable-linger "$USER" >/dev/null 2>&1 || true
fi

log "Installing desktop launcher, icon, and background service"
"$VENV_DIR/bin/python" "$PROJECT_ROOT/scripts/install_desktop.py"

if command -v update-desktop-database >/dev/null 2>&1; then
    log "Refreshing desktop database"
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

log "OwlLock is installed"
log "Background service is enabled for your user account"
log "Launch it from the app menu using OwlLock"
