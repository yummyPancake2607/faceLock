#!/usr/bin/env bash
# OwlLock installer — one-line setup for the face-auth app locker.
#
# Usage:
#   bash install.sh                    # install everything
#   bash install.sh --uninstall        # remove all installed files
#   bash install.sh --no-system-deps   # skip system package installation
#   bash install.sh --help             # show this message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10

OWLLOCK_DESKTOP="owllock.desktop"
OWLLOCK_SERVICE="owllock.service"
OWLLOCK_ICON="owllock.png"

# ── Terminal helpers ────────────────────────────────────────────────

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

log()  { printf "${CYAN}[OwlLock]${NC} %s\n" "$1"; }
ok()   { printf "${GREEN}[  OK  ]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[ WARN ]${NC} %s\n" "$1"; }
die()  { printf "${RED}[ FAIL ]${NC} %s\n" "$1" >&2; exit 1; }

# ── Help ────────────────────────────────────────────────────────────

show_help() {
    sed -n '2,8p' "$0"
    echo
    echo "Options:"
    echo "  --uninstall       Remove all OwlLock files (desktop entry, icon, service, venv)"
    echo "  --no-system-deps  Skip system package installation (requires manual dep setup)"
    echo "  --help            Show this help message"
    exit 0
}

for arg in "$@"; do
    [ "$arg" = "--help" ] && show_help
done

# ── Preflight checks ───────────────────────────────────────────────

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

check_python() {
    local py="$1"
    if ! command -v "$py" >/dev/null 2>&1; then
        return 1
    fi
    local version
    version=$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || return 1
    local major="${version%.*}"
    local minor="${version#*.}"
    if [ "$major" -gt "$MIN_PYTHON_MAJOR" ] || { [ "$major" -eq "$MIN_PYTHON_MAJOR" ] && [ "$minor" -ge "$MIN_PYTHON_MINOR" ]; }; then
        echo "$version"
        return 0
    fi
    return 1
}

# ── System package installation ────────────────────────────────────

detect_pm() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "apt"
    elif command -v dnf >/dev/null 2>&1; then
        echo "dnf"
    elif command -v pacman >/dev/null 2>&1; then
        echo "pacman"
    elif command -v zypper >/dev/null 2>&1; then
        echo "zypper"
    else
        echo "unknown"
    fi
}

install_system_deps() {
    local pm
    pm=$(detect_pm)
    log "Detected package manager: $pm"

    case "$pm" in
        apt)
            log "Installing build dependencies (cmake, build-essential, libboost, libgl)..."
            sudo apt-get update -qq && sudo apt-get install -y -qq \
                cmake \
                build-essential \
                libboost-all-dev \
                libgl1-mesa-glx \
                libglib2.0-0 \
                libxkbcommon-x11-0 \
                libegl1-mesa \
                libxcb-cursor0 \
                2>/dev/null || warn "Some system packages could not be installed. dlib may need to compile from source."
            ;;
        dnf)
            log "Installing build dependencies (cmake, gcc-c++, boost, mesa-libGL)..."
            sudo dnf install -y \
                cmake \
                gcc-c++ \
                boost-devel \
                mesa-libGL \
                glib2 \
                libxkbcommon-x11 \
                2>/dev/null || warn "Some system packages could not be installed."
            ;;
        pacman)
            log "Installing build dependencies (cmake, base-devel, boost, mesa)..."
            sudo pacman -S --needed --noconfirm \
                cmake \
                base-devel \
                boost \
                mesa \
                glib2 \
                libxkbcommon-x11 \
                2>/dev/null || warn "Some system packages could not be installed."
            ;;
        zypper)
            log "Installing build dependencies (cmake, gcc-c++, boost, Mesa-libGL)..."
            sudo zypper install -y \
                cmake \
                gcc-c++ \
                boost-devel \
                Mesa-libGL \
                glib2 \
                libxkbcommon-x11-0 \
                2>/dev/null || warn "Some system packages could not be installed."
            ;;
        *)
            warn "Unknown package manager. Skipping system deps."
            warn "You may need to install manually: cmake, boost, gcc-c++, mesa-libGL"
            ;;
    esac
}

# ── Uninstall ──────────────────────────────────────────────────────

uninstall() {
    log "Uninstalling OwlLock..."

    # Stop and disable systemd service
    if systemctl --user list-units --all 2>/dev/null | grep -q "$OWLLOCK_SERVICE"; then
        systemctl --user stop "$OWLLOCK_SERVICE" 2>/dev/null || true
        systemctl --user disable "$OWLLOCK_SERVICE" 2>/dev/null || true
        ok "Stopped and disabled systemd service"
    fi

    # Remove service file
    local service_dst="$HOME/.config/systemd/user/$OWLLOCK_SERVICE"
    if [ -f "$service_dst" ]; then
        rm -f "$service_dst"
        ok "Removed $service_dst"
        systemctl --user daemon-reload 2>/dev/null || true
    fi

    # Remove desktop file
    local desktop_dst="$HOME/.local/share/applications/$OWLLOCK_DESKTOP"
    if [ -f "$desktop_dst" ]; then
        rm -f "$desktop_dst"
        ok "Removed $desktop_dst"
    fi

    # Remove icon
    local icon_paths
    icon_paths=$(find "$HOME/.local/share/icons" -name "$OWLLOCK_ICON" 2>/dev/null) || true
    for p in $icon_paths; do
        rm -f "$p"
        ok "Removed $p"
    done

    # Remove cache
    if [ -d "$HOME/.cache/owllock" ]; then
        rm -rf "$HOME/.cache/owllock"
        ok "Removed cache"
    fi

    # Remove database (ask first)
    local db_path="$HOME/.facelock"
    if [ -d "$db_path" ]; then
        warn "Database directory found at $db_path (contains face profiles and settings)"
        printf "${YELLOW}Delete it? [y/N]${NC} "
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            rm -rf "$db_path"
            ok "Removed $db_path"
        else
            warn "Kept $db_path"
        fi
    fi

    # Remove virtual environment (ask first)
    if [ -d "$VENV_DIR" ]; then
        warn "Virtual environment found at $VENV_DIR"
        printf "${YELLOW}Delete it? [y/N]${NC} "
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            rm -rf "$VENV_DIR"
            ok "Removed virtual environment"
        else
            warn "Kept $VENV_DIR"
        fi
    fi

    ok "OwlLock has been uninstalled."
    exit 0
}

for arg in "$@"; do
    [ "$arg" = "--uninstall" ] && uninstall
done

# ── Main installation ──────────────────────────────────────────────

log "Starting OwlLock installation"
echo ""

# 1. Python check
log "Checking Python..."
PYTHON=""
for candidate in python3 python; do
    version=$(check_python "$candidate") && {
        PYTHON="$candidate"
        ok "Found $candidate $version"
        break
    }
done
if [ -z "$PYTHON" ]; then
    die "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ is required. Install it and try again."
fi

# 2. System dependencies
skip_deps=false
for arg in "$@"; do
    [ "$arg" = "--no-system-deps" ] && skip_deps=true
done
if [ "$skip_deps" = false ]; then
    echo ""
    log "Checking system dependencies..."
    install_system_deps
fi

# 3. Video group check
echo ""
log "Checking camera permissions..."
if groups | grep -q '\bvideo\b'; then
    ok "User is in the 'video' group — camera should be accessible"
else
    warn "User is NOT in the 'video' group."
    warn "Run: sudo usermod -a -G video $USER && then log out and back in."
    warn "Without this, the camera may not open."
fi

# 4. Virtual environment
echo ""
log "Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON" -m venv "$VENV_DIR"
    ok "Created virtual environment at $VENV_DIR"
else
    ok "Virtual environment already exists at $VENV_DIR"
fi

log "Upgrading pip, setuptools, wheel..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel -q
ok "pip tooling upgraded"

# 5. Install Python package
echo ""
log "Installing OwlLock and dependencies (this may take a while to compile dlib)..."
"$VENV_DIR/bin/python" -m pip install -e "$PROJECT_ROOT" 2>&1 | tail -5 || {
    die "pip install failed. Check the error above. Common fixes:
  - Install system deps: cmake, build-essential, libboost-all-dev
  - On Arch: base-devel, boost, cmake
  - Then re-run: bash install.sh"
}
ok "OwlLock installed in virtual environment"

# Add project root to sys.path so 'from src.facelock.xxx' imports work from console entries
PYTHON_SITE="$VENV_DIR/lib/python*/site-packages"
for _p in $PYTHON_SITE; do
    if [ -d "$_p" ]; then
        echo "$PROJECT_ROOT" > "$_p/owllock-path.pth"
        ok "Added project root to sys.path ($_p/owllock-path.pth)"
        break
    fi
done

# 6. Verify key imports
echo ""
log "Verifying imports..."
"$VENV_DIR/bin/python" -c "
import cv2; print('  opencv-python:', cv2.__version__)
import numpy; print('  numpy:', numpy.__version__)
import face_recognition; print('  face-recognition:', face_recognition.__version__)
from PyQt6.QtCore import QT_VERSION_STR; print('  PyQt6:', QT_VERSION_STR)
import src.facelock.auth.camera; print('  owllock.camera: OK')
import src.facelock.auth.detector; print('  owllock.detector: OK')
import src.facelock.auth.encoder; print('  owllock.encoder: OK')
" 2>&1 || warn "Some imports failed. Functionality may be limited."
ok "All core imports verified"

# 7. User lingering (systemd)
echo ""
if command -v loginctl >/dev/null 2>&1; then
    log "Enabling user lingering so OwlLock can start after boot..."
    loginctl enable-linger "$USER" 2>/dev/null || true
    ok "User lingering enabled"
else
    warn "loginctl not found. The background service may not start automatically after boot."
fi

# 8. Install desktop files
echo ""
log "Installing desktop launcher, icon, and background service..."
"$VENV_DIR/bin/python" "$PROJECT_ROOT/scripts/install_desktop.py" || {
    warn "Desktop/service installation had issues. You can manually run:"
    warn "  $VENV_DIR/bin/python $PROJECT_ROOT/scripts/install_desktop.py"
}

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# 9. Start service
echo ""
log "Starting OwlLock background service..."
if systemctl --user daemon-reload 2>/dev/null && systemctl --user start "$OWLLOCK_SERVICE" 2>/dev/null; then
    ok "Background service started"
else
    warn "Could not start systemd service. You may need to log out and back in, or run:"
    warn "  systemctl --user daemon-reload"
    warn "  systemctl --user start owllock.service"
fi

# ── Done ─────────────────────────────────────────────────────────────
echo ""
log "${GREEN}OwlLock is installed!${NC}"
echo ""
echo "  ${CYAN}Next steps:${NC}"
echo "  1. Log out and back in (so the desktop entry appears in your app menu)"
echo "  2. Launch OwlLock from the app menu"
echo "  3. Register your face, then lock an app"
echo ""
echo "  ${CYAN}Quick start from terminal:${NC}"
echo "    $VENV_DIR/bin/python -m src.facelock.app"
echo ""
echo "  ${CYAN}Check service status:${NC}"
echo "    systemctl --user status owllock.service"
echo ""
echo "  ${CYAN}View logs:${NC}"
echo "    tail -f ~/.cache/owllock/owllock-launcher.log"
echo ""
