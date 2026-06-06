#!/usr/bin/env bash
# OwlLock installer — fully automated setup for any Linux / macOS laptop.
#
# This script will:
#   1. Install Python 3.10+ if missing (via system package manager or pyenv)
#   2. Install all system-level build dependencies (cmake, boost, etc.)
#   3. Create a Python virtual environment
#   4. Install Python dependencies (face-recognition, opencv, PyQt6, etc.)
#   5. Install desktop launcher, icon, and systemd service
#   6. Start the background service
#
# Usage:
#   bash install.sh                        # install everything
#   bash install.sh --uninstall            # remove all installed files
#   bash install.sh --help                 # show this message
#   bash install.sh --no-system-deps       # skip system package install
#   bash install.sh --prefer-system-python # use system python even if newer is available via pyenv

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-}"
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
NC='\033[0m'

log()  { printf "${CYAN}[OwlLock]${NC} %s\n" "$1"; }
ok()   { printf "${GREEN}[  OK  ]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[ WARN ]${NC} %s\n" "$1"; }
die()  { printf "${RED}[ FAIL ]${NC} %s\n" "$1" >&2; exit 1; }
step() { echo; printf "${CYAN}━━━ %s ━━━${NC}\n" "$1"; }

# ── Help ────────────────────────────────────────────────────────────

show_help() {
    sed -n '2,14p' "$0"
    echo
    echo "Options:"
    echo "  --uninstall              Remove all OwlLock files"
    echo "  --no-system-deps         Skip system package installation"
    echo "  --prefer-system-python   Use system python even if pyenv has a newer version"
    echo "  --help                   Show this help message"
    exit 0
}

for arg in "$@"; do
    [ "$arg" = "--help" ] && show_help
done

# ── OS detection ────────────────────────────────────────────────────

detect_os() {
    case "$(uname -s)" in
        Linux)
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                echo "$ID"
            elif command -v lsb_release >/dev/null 2>&1; then
                lsb_release -si | tr '[:upper:]' '[:lower:]'
            else
                echo "linux"
            fi
            ;;
        Darwin) echo "macos" ;;
        *)      echo "unsupported" ;;
    esac
}

detect_pm() {
    case "$(detect_os)" in
        ubuntu|debian|linuxmint|pop|elementary|zorin) echo "apt" ;;
        fedora|rhel|centos)                           echo "dnf" ;;
        arch|manjaro|endeavouros)                     echo "pacman" ;;
        opensuse|suse)                                echo "zypper" ;;
        alpine)                                       echo "apk" ;;
        macos)                                        echo "brew" ;;
        *)                                            echo "unknown" ;;
    esac
}

OS=$(detect_os)
PM=$(detect_pm)

# ── Preflight checks ───────────────────────────────────────────────

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

check_python_version() {
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

# ── Package manager helpers ─────────────────────────────────────────

pkg_install() {
    local pkgs=("$@")
    case "$PM" in
        apt)
            sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${pkgs[@]}"
            ;;
        dnf)
            sudo dnf install -y "${pkgs[@]}"
            ;;
        pacman)
            sudo pacman -S --needed --noconfirm "${pkgs[@]}"
            ;;
        zypper)
            sudo zypper install -y "${pkgs[@]}"
            ;;
        apk)
            sudo apk add --no-cache "${pkgs[@]}"
            ;;
        brew)
            brew install "${pkgs[@]}"
            ;;
        *)
            return 1
            ;;
    esac
}

pkg_is_installed() {
    local pkg="$1"
    case "$PM" in
        apt)     dpkg -s "$pkg" >/dev/null 2>&1 ;;
        dnf)     rpm -q "$pkg" >/dev/null 2>&1 ;;
        pacman)  pacman -Qi "$pkg" >/dev/null 2>&1 ;;
        zypper)  rpm -q "$pkg" >/dev/null 2>&1 ;;
        apk)     apk info -e "$pkg" >/dev/null 2>&1 ;;
        brew)    brew list "$pkg" >/dev/null 2>&1 ;;
        *)       return 1 ;;
    esac
}

# ── Python installation ─────────────────────────────────────────────

install_python_via_pyenv() {
    log "Installing Python via pyenv..."

    # Install pyenv dependencies first
    case "$OS" in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            pkg_install make build-essential libssl-dev zlib1g-dev libbz2-dev \
                libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
                libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev \
                libgdbm-dev libnss3-dev libedit-dev
            ;;
        fedora|rhel|centos)
            pkg_install make gcc patch zlib-devel bzip2 bzip2-devel readline-devel \
                sqlite sqlite-devel openssl-devel tk-devel libffi-devel \
                xz-devel libuuid-devel gdbm-devel libnsl2-devel
            ;;
        arch|manjaro|endeavouros)
            pkg_install base-devel openssl zlib xz tk libffi
            ;;
        macos)
            pkg_install openssl readline sqlite3 xz zlib tcl-tk libffi
            ;;
    esac

    # Install pyenv if not present
    if ! command -v pyenv >/dev/null 2>&1; then
        log "Installing pyenv..."
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL https://pyenv.run | bash
        elif command -v wget >/dev/null 2>&1; then
            wget -q -O- https://pyenv.run | bash
        else
            die "Need curl or wget to install pyenv"
        fi
    fi

    # Ensure pyenv is in PATH for this script
    export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
    if [ -d "$PYENV_ROOT/bin" ]; then
        export PATH="$PYENV_ROOT/bin:$PATH"
    fi
    if command -v pyenv >/dev/null 2>&1; then
        eval "$(pyenv init -)"
    else
        die "pyenv not found after installation"
    fi

    # Install Python 3.12 (latest stable) via pyenv
    local PYENV_PYTHON_VERSION="3.12.9"
    log "Installing Python $PYENV_PYTHON_VERSION via pyenv (this may take a while)..."
    if ! pyenv versions --bare 2>/dev/null | grep -q "^$PYENV_PYTHON_VERSION$"; then
        pyenv install "$PYENV_PYTHON_VERSION" || die "Failed to install Python $PYENV_PYTHON_VERSION via pyenv"
    else
        ok "Python $PYENV_PYTHON_VERSION already installed via pyenv"
    fi

    # Use it locally for this project
    pyenv local "$PYENV_PYTHON_VERSION" 2>/dev/null || true
    echo "$PYENV_ROOT/shims/python3"
}

install_python_via_package_manager() {
    log "Installing Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ via $PM..."
    case "$PM" in
        apt)
            pkg_install python3 python3-venv python3-pip python3-dev
            echo "python3"
            ;;
        dnf)
            pkg_install python3 python3-devel python3-pip python3-venv
            echo "python3"
            ;;
        pacman)
            pkg_install python python-pip python-virtualenv
            echo "python"
            ;;
        zypper)
            pkg_install python3 python3-devel python3-pip python3-venv
            echo "python3"
            ;;
        apk)
            pkg_install python3 py3-pip py3-virtualenv
            echo "python3"
            ;;
        brew)
            pkg_install python@3.12
            echo "$(brew --prefix python@3.12)/bin/python3.12"
            ;;
        *)
            return 1
            ;;
    esac
}

# ── System dependencies ─────────────────────────────────────────────

install_system_deps() {
    log "Detected OS: $OS"
    log "Detected package manager: $PM"

    case "$OS" in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            log "Installing system dependencies for Debian/Ubuntu..."
            pkg_install \
                cmake \
                build-essential \
                libboost-all-dev \
                libgl1-mesa-glx \
                libglib2.0-0 \
                libxkbcommon-x11-0 \
                libegl1-mesa \
                libxcb-cursor0 \
                libsm6 \
                libxext6 \
                libxrender-dev \
                libgomp1 \
                git \
                wget \
                curl \
                ca-certificates \
            || warn "Some system packages could not be installed."
            ;;
        fedora|rhel|centos)
            log "Installing system dependencies for Fedora/RHEL..."
            # Enable EPEL on RHEL/CentOS if not enabled
            if [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
                pkg_install epel-release 2>/dev/null || true
            fi
            pkg_install \
                cmake \
                gcc-c++ \
                boost-devel \
                mesa-libGL \
                glib2 \
                libxkbcommon-x11 \
                libXext-devel \
                libXrender-devel \
                libgomp \
                git \
                wget \
                curl \
            || warn "Some system packages could not be installed."
            ;;
        arch|manjaro|endeavouros)
            log "Installing system dependencies for Arch Linux..."
            pkg_install \
                cmake \
                base-devel \
                boost \
                mesa \
                glib2 \
                libxkbcommon-x11 \
                libxcb \
                libxext \
                libxrender \
                git \
                wget \
                curl \
            || warn "Some system packages could not be installed."
            ;;
        opensuse|suse)
            log "Installing system dependencies for openSUSE..."
            pkg_install \
                cmake \
                gcc-c++ \
                boost-devel \
                Mesa-libGL \
                glib2 \
                libxkbcommon-x11-0 \
                libXext-devel \
                libXrender-devel \
                git \
                wget \
                curl \
            || warn "Some system packages could not be installed."
            ;;
        alpine)
            log "Installing system dependencies for Alpine Linux..."
            pkg_install \
                cmake \
                build-base \
                boost-dev \
                mesa-gl \
                glib \
                libxkbcommon \
                libxcb \
                git \
                wget \
                curl \
            || warn "Some system packages could not be installed."
            ;;
        macos)
            log "Installing system dependencies for macOS..."
            # Ensure Homebrew is installed
            if ! command -v brew >/dev/null 2>&1; then
                log "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
                    die "Homebrew installation failed. Install it manually: https://brew.sh"
                }
            fi
            pkg_install \
                cmake \
                boost \
                glib \
                pkg-config \
                git \
                wget \
            || warn "Some system packages could not be installed."
            # On macOS, XQuartz provides X11 libs
            if ! pkg_is_installed xquartz 2>/dev/null; then
                warn "XQuartz may be needed for GUI support on macOS."
                warn "Install it with: brew install --cask xquartz"
            fi
            ;;
        *)
            warn "Unknown OS: $OS. Attempting to install generic build tools..."
            warn "You may need to manually install: cmake, boost, gcc-c++, mesa-libGL"
            ;;
    esac
}

# ── Uninstall ──────────────────────────────────────────────────────

uninstall() {
    log "Uninstalling OwlLock..."

    if systemctl --user list-units --all 2>/dev/null | grep -q "$OWLLOCK_SERVICE"; then
        systemctl --user stop "$OWLLOCK_SERVICE" 2>/dev/null || true
        systemctl --user disable "$OWLLOCK_SERVICE" 2>/dev/null || true
        ok "Stopped and disabled systemd service"
    fi

    local service_dst="$HOME/.config/systemd/user/$OWLLOCK_SERVICE"
    if [ -f "$service_dst" ]; then
        rm -f "$service_dst"
        ok "Removed $service_dst"
        systemctl --user daemon-reload 2>/dev/null || true
    fi

    local desktop_dst="$HOME/.local/share/applications/$OWLLOCK_DESKTOP"
    if [ -f "$desktop_dst" ]; then
        rm -f "$desktop_dst"
        ok "Removed $desktop_dst"
    fi

    local icon_paths
    icon_paths=$(find "$HOME/.local/share/icons" -name "$OWLLOCK_ICON" 2>/dev/null) || true
    for p in $icon_paths; do
        rm -f "$p"
        ok "Removed $p"
    done

    if [ -d "$HOME/.cache/owllock" ]; then
        rm -rf "$HOME/.cache/owllock"
        ok "Removed cache"
    fi

    local db_path="$HOME/.facelock"
    if [ -d "$db_path" ]; then
        warn "Database directory found at $db_path (contains face profiles)"
        printf "${YELLOW}Delete it? [y/N]${NC} "
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            rm -rf "$db_path"
            ok "Removed $db_path"
        else
            warn "Kept $db_path"
        fi
    fi

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

echo
echo "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo "${CYAN}║         OwlLock Installer                        ║${NC}"
echo "${CYAN}║         Face-auth app locker for Linux           ║${NC}"
echo "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo

PREFER_SYSTEM_PYTHON=false
SKIP_DEPS=false
for arg in "$@"; do
    [ "$arg" = "--prefer-system-python" ] && PREFER_SYSTEM_PYTHON=true
    [ "$arg" = "--no-system-deps" ] && SKIP_DEPS=true
done

# 1. OS check
step "Detecting operating system"
log "OS: $OS  |  Package manager: $PM"
if [ "$OS" = "unsupported" ]; then
    die "Unsupported operating system: $(uname -s). OwlLock requires Linux or macOS."
fi
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" != "arm64" ] && [ "$(uname -m)" != "x86_64" ]; then
    warn "macOS on $(uname -m) is untested. Proceed with caution."
fi
ok "System: $(uname -s) $(uname -m)"

# 2. Install system dependencies
if [ "$SKIP_DEPS" = false ]; then
    step "System dependencies"
    install_system_deps
    ok "System dependencies installed"
fi

# 3. Python check / install
step "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+"

PYTHON=""
# First check if PYTHON_BIN is set and works
if [ -n "$PYTHON_BIN" ]; then
    version=$(check_python_version "$PYTHON_BIN") && {
        PYTHON="$PYTHON_BIN"
        ok "Using specified Python: $PYTHON_BIN ($version)"
    }
fi

# Check common Python binaries
if [ -z "$PYTHON" ]; then
    for candidate in python3 python python3.12 python3.11 python3.10; do
        version=$(check_python_version "$candidate") && {
            PYTHON="$candidate"
            ok "Found $candidate $version"
            break
        }
    done
fi

# Try pyenv if available and not preferring system python
if [ -z "$PYTHON" ] && [ "$PREFER_SYSTEM_PYTHON" = false ]; then
    if command -v pyenv >/dev/null 2>&1; then
        export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
        eval "$(pyenv init -)"
        for candidate in python3 python; do
            version=$(check_python_version "$candidate") && {
                PYTHON="$candidate"
                ok "Found pyenv $candidate $version"
                break
            }
        done
    fi
fi

# Install Python if still missing
if [ -z "$PYTHON" ]; then
    log "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ not found. Attempting to install..."

    # Try package manager first
    PYTHON=$(install_python_via_package_manager) && {
        version=$(check_python_version "$PYTHON") && {
            ok "Installed Python $version via $PM"
        } || {
            PYTHON=""
        }
    }

    # Fall back to pyenv if package manager didn't work
    if [ -z "$PYTHON" ]; then
        warn "Package manager couldn't provide Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+."
        log "Trying pyenv..."
        PYTHON=$(install_python_via_pyenv) && {
            version=$(check_python_version "$PYTHON") && {
                ok "Installed Python $version via pyenv"
            } || {
                die "pyenv Python installation failed. Install Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ manually."
            }
        }
    fi
fi

[ -z "$PYTHON" ] && die "Could not find or install Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+"
PYTHON_PATH=$(command -v "$PYTHON")
ok "Using Python: $PYTHON_PATH"

# 4. Ensure venv module is available
step "Virtual environment tools"
if ! "$PYTHON" -c "import venv" 2>/dev/null; then
    log "venv module not found. Installing..."
    case "$PM" in
        apt)   pkg_install python3-venv ;;
        dnf)   pkg_install python3-venv ;;
        pacman) ok "On Arch, venv is included with Python." ;;
        zypper) pkg_install python3-venv ;;
        apk)   pkg_install py3-virtualenv ;;
        brew)  ok "Homebrew Python includes venv." ;;
    esac
fi
ok "venv module available"

# 5. Video group check (Linux only)
if [ "$OS" != "macos" ]; then
    step "Camera permissions"
    if groups | grep -q '\bvideo\b'; then
        ok "User is in the 'video' group — camera should be accessible"
    else
        warn "User is NOT in the 'video' group."
        warn "Running: sudo usermod -a -G video $USER"
        sudo usermod -a -G video "$USER" 2>/dev/null || warn "Could not add to video group automatically."
        warn "You'll need to log out and back in for camera access."
    fi
fi

# 6. Virtual environment
step "Virtual environment"
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON" -m venv "$VENV_DIR"
    ok "Created virtual environment at $VENV_DIR"
else
    ok "Virtual environment already exists at $VENV_DIR"
fi

log "Upgrading pip, setuptools, wheel..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel -q
ok "pip tooling upgraded"

# 7. Install Python package
step "Python dependencies"
log "Installing OwlLock and dependencies..."
log "This may take a while (especially dlib/face-recognition compilation)..."

# Try pre-built wheels first to avoid compilation
"$VENV_DIR/bin/python" -m pip install --only-binary=:all: numpy opencv-python -q 2>/dev/null || true

# Install edge detection model (needed for face-recognition)
log "Installing face-recognition and dependencies..."
if "$VENV_DIR/bin/python" -m pip install -e "$PROJECT_ROOT" 2>&1; then
    ok "OwlLock installed in virtual environment"
else
    warn "pip install failed. Retrying with verbose output for debugging..."
    "$VENV_DIR/bin/python" -m pip install -e "$PROJECT_ROOT" --verbose 2>&1 | tail -30 || {
        warn ""
        warn "Common fixes for dlib/face-recognition compilation failures:"
        warn "  1. Make sure cmake and boost are installed"
        warn "  2. Increase memory/swap (dlib needs ~2GB RAM to compile)"
        warn "  3. Try installing dlib separately:"
        warn "       $VENV_DIR/bin/pip install dlib"
        warn "       $VENV_DIR/bin/pip install face-recognition"
        warn "  4. Or try the pre-compiled version:"
        warn "       $VENV_DIR/bin/pip install face-recognition-models"
        die "pip install failed. See errors above."
    }
fi

# Add project root to sys.path
PYTHON_SITE="$VENV_DIR/lib/python*/site-packages"
for _p in $PYTHON_SITE; do
    if [ -d "$_p" ]; then
        echo "$PROJECT_ROOT" > "$_p/owllock-path.pth"
        ok "Added project root to sys.path"
        break
    fi
done

# 8. Verify key imports
step "Verifying imports"
"$VENV_DIR/bin/python" -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT')
import cv2; print('  opencv-python:', cv2.__version__)
import numpy; print('  numpy:', numpy.__version__)
import face_recognition; print('  face-recognition:', face_recognition.__version__)
from PyQt6.QtCore import QT_VERSION_STR; print('  PyQt6:', QT_VERSION_STR)
import src.facelock.auth.camera; print('  camera module: OK')
import src.facelock.auth.detector; print('  detector module: OK')
import src.facelock.auth.encoder; print('  encoder module: OK')
print('All core imports verified!')
" 2>&1 || warn "Some imports failed. Functionality may be limited."

# 9. User lingering (systemd, Linux only)
if [ "$OS" != "macos" ]; then
    step "Background service setup"
    if command -v loginctl >/dev/null 2>&1; then
        log "Enabling user lingering so OwlLock can start after boot..."
        loginctl enable-linger "$USER" 2>/dev/null || true
        ok "User lingering enabled"
    else
        warn "loginctl not found. Service may not start automatically after boot."
    fi
fi

# 10. Install desktop files
log "Installing desktop launcher, icon, and service..."
if [ -f "$PROJECT_ROOT/scripts/install_desktop.py" ]; then
    "$VENV_DIR/bin/python" "$PROJECT_ROOT/scripts/install_desktop.py" || {
        warn "Desktop installation had issues. You can manually run:"
        warn "  $VENV_DIR/bin/python $PROJECT_ROOT/scripts/install_desktop.py"
    }
else
    warn "install_desktop.py not found — skipping desktop file installation"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# 11. Start service (Linux only)
if [ "$OS" != "macos" ] && command -v systemctl >/dev/null 2>&1; then
    log "Starting OwlLock background service..."
    if systemctl --user daemon-reload 2>/dev/null && systemctl --user start "$OWLLOCK_SERVICE" 2>/dev/null; then
        ok "Background service started"
    else
        warn "Could not start systemd service. You may need to log out and back in, or run:"
        warn "  systemctl --user daemon-reload"
        warn "  systemctl --user start owllock.service"
    fi
fi

# ── Done ─────────────────────────────────────────────────────────────
echo
echo "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo "${GREEN}║       OwlLock is installed!                      ║${NC}"
echo "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo
echo "  ${CYAN}Next steps:${NC}"
echo "  1. Log out and back in (so the desktop entry appears in your app menu)"
echo "  2. Launch OwlLock from the app menu"
echo "  3. Register your face, then lock an app"
echo
echo "  ${CYAN}Quick start from terminal:${NC}"
echo "    $VENV_DIR/bin/python -m src.facelock.app"
echo
if [ "$OS" != "macos" ]; then
    echo "  ${CYAN}Check service status:${NC}"
    echo "    systemctl --user status owllock.service"
    echo
    echo "  ${CYAN}View logs:${NC}"
    echo "    tail -f ~/.cache/owllock/owllock-launcher.log"
fi
echo
echo "  ${CYAN}Installation log saved to:${NC}"
echo "    $HOME/.owllock-install.log"
echo

# Save a log for reference
{
    echo "OwlLock installation completed at $(date)"
    echo "OS: $OS"
    echo "Python: $("$PYTHON" --version 2>&1)"
    echo "Virtual env: $VENV_DIR"
} > "$HOME/.owllock-install.log"
