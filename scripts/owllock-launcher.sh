#!/usr/bin/env bash
# Launcher that runs OwlLock using the project's venv Python and logs output.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PY="$PROJECT_ROOT/.venv/bin/python3"
LOG_DIR="$HOME/.cache/owllock"
LOG_FILE="$LOG_DIR/owllock-launcher.log"

mkdir -p "$LOG_DIR"
echo "=== OwlLock launcher start: $(date) ===" >> "$LOG_FILE"
echo "ARGS: $*" >> "$LOG_FILE"
echo "PWD=$PWD" >> "$LOG_FILE"
echo "SCRIPT_DIR=$SCRIPT_DIR" >> "$LOG_FILE"
echo "PROJECT_ROOT=$PROJECT_ROOT" >> "$LOG_FILE"
echo "ENV snapshot:" >> "$LOG_FILE"
env >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

# Use offscreen Qt platform when running in background mode;
# save display variables so auth-prompt can restore them.
for arg in "$@"; do
    if [ "$arg" = "--background" ]; then
        export QT_QPA_PLATFORM=offscreen
        export OWLLOCK_DISPLAY="${DISPLAY:-}"
        export OWLLOCK_WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}"
        echo "Saved DISPLAY=$OWLLOCK_DISPLAY WAYLAND_DISPLAY=$OWLLOCK_WAYLAND_DISPLAY" >> "$LOG_FILE"
        break
    fi
done

if [ -x "$VENV_PY" ]; then
    echo "Using venv python: $VENV_PY" >> "$LOG_FILE"
    # Ensure Python can import the local src/ package by running from project root
    cd "$PROJECT_ROOT"
    echo "cd to $(pwd)" >> "$LOG_FILE"
    exec "$VENV_PY" -m src.facelock.app "$@" >> "$LOG_FILE" 2>&1
else
    echo "Venv python not found; falling back to system python" >> "$LOG_FILE"
    PY="$(command -v python3 || command -v python)"
    echo "Using python: $PY" >> "$LOG_FILE"
    cd "$PROJECT_ROOT"
    echo "cd to $(pwd)" >> "$LOG_FILE"
    exec "$PY" -m src.facelock.app "$@" >> "$LOG_FILE" 2>&1
fi
