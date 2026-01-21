#!/bin/bash
set -e

# Determine project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROVERS_DIR="$PROJECT_ROOT/provers"

# Flags
DO_SYSTEM=false
DO_PYTHON=false
DO_PROVERS=false
EXPLICIT_MODE=false

# Parse args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --install-system-deps) DO_SYSTEM=true; EXPLICIT_MODE=true ;;
        --install-python-deps) DO_PYTHON=true; EXPLICIT_MODE=true ;;
        --install-provers) DO_PROVERS=true; EXPLICIT_MODE=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Default behavior if no specific install flags: Python + Provers
if [ "$EXPLICIT_MODE" = false ]; then
    DO_PYTHON=true
    DO_PROVERS=true
fi

# 1. System Dependencies
if [ "$DO_SYSTEM" = true ]; then
    echo "Installing system dependencies..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y \
            build-essential \
            curl \
            git \
            picosat \
            unzip \
            binutils \
            wget \
            zstd \
            && rm -rf /var/lib/apt/lists/*
    else
        echo "Warning: apt-get not found. Skipping system package installation."
    fi
fi

# 2. Python Dependencies
if [ "$DO_PYTHON" = true ]; then
    # Install uv if needed
    if ! command -v uv &> /dev/null; then
        echo "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    echo "Installing Python dependencies..."
    cd "$PROJECT_ROOT"
    if [ ! -d "src" ]; then
        echo "Source directory not found. Installing dependencies only."
        uv sync --no-install-project
    else
        uv sync
    fi
fi

# 3. Provers
if [ "$DO_PROVERS" = true ]; then
    mkdir -p "$PROVERS_DIR"

    # Vampire
    if [ ! -f "$PROVERS_DIR/vampire" ]; then
        echo "Installing Vampire..."
        curl -L https://github.com/vprover/vampire/releases/download/v5.0.0/vampire-Linux-X64.zip -o vampire.zip
        unzip -q vampire.zip
        mv vampire "$PROVERS_DIR/vampire"
        chmod +x "$PROVERS_DIR/vampire"
        rm vampire.zip
        echo "Vampire installed."
    else
        echo "Vampire already installed."
    fi

    # Eprover
    if [ ! -f "$PROVERS_DIR/eprover" ]; then
        echo "Installing Eprover..."

        # Check if we can use apt-get to install deps automatically, but we want the binary in provers/
        # Or just use the manual extraction but be careful about dependencies.
        # Dockerfile previously used `apt-get install ./eprover.deb`.
        # This installs into /usr/bin/eprover.
        # If we are in Docker (implied by --install-system-deps usually, or check env), maybe we should stick to that?
        # But user wants standalone script.
        # So we will extract, but if on Debian/Ubuntu and running as root, we could `apt-get install` it then copy?

        # Let's stick to extraction, but we ensured 'picosat' is installed in system deps.

        if command -v ar &> /dev/null && command -v tar &> /dev/null; then
            curl -L -o eprover.deb http://archive.ubuntu.com/ubuntu/pool/universe/e/eprover/eprover_3.0.03+ds-1_amd64.deb
            ar x eprover.deb
            if [ -f "data.tar.xz" ]; then
                tar xf data.tar.xz
            elif [ -f "data.tar.zst" ]; then
                if command -v unzstd &> /dev/null; then
                     unzstd data.tar.zst
                     tar xf data.tar
                     rm data.tar
                elif command -v zstd &> /dev/null; then
                     tar -I zstd -xf data.tar.zst
                else
                     echo "Error: data.tar.zst found but 'zstd' is not installed."
                     echo "Please install zstd."
                     # Clean up partial
                     rm -rf usr debian-binary control.tar.zst data.tar.xz data.tar.zst eprover.deb
                     exit 1
                fi
            fi

            if [ -f "usr/bin/eprover" ]; then
                cp usr/bin/eprover "$PROVERS_DIR/eprover"
                chmod +x "$PROVERS_DIR/eprover"
                echo "Eprover installed."
            else
                echo "Error: usr/bin/eprover not found in extracted deb."
                exit 1
            fi
            # Cleanup
            rm -rf usr debian-binary control.tar.zst data.tar.xz data.tar.zst eprover.deb
        else
            echo "Error: 'ar' or 'tar' not found. Cannot extract Eprover."
            exit 1
        fi
    else
        echo "Eprover already installed."
    fi
fi

echo "Setup steps complete."
