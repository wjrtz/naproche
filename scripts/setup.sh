#!/bin/bash
set -e

# 1. System Deps
# Added 'zstd' to the list so tar can unpack the Eprover archive
echo "Installing System Deps..."
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential curl git picosat unzip binutils wget zstd

# 2. Python (UV)
echo "Installing Python Deps..."
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Ensure UV is on path
if [ -f "$HOME/.local/bin/env" ]; then
    source "$HOME/.local/bin/env"
else
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# Run sync only if pyproject.toml exists
if [ -f "pyproject.toml" ]; then
    # Check if src directory exists to decide if we can install the project itself
    if [ -d "src" ]; then
        echo "Installing Project and Dependencies..."
        # Install into virtual environment (with dev dependencies)
        uv sync --frozen --extra dev || uv sync --extra dev

        # Install into system/current python environment to support global usage
        # This ensures 'python -m pytest' and other direct invocations work
        uv pip install --system -e .[dev]
    else
        echo "Source directory not found. Installing dependencies only..."
        # Install dependencies only into virtual environment
        uv sync --frozen --extra dev --no-install-project || uv sync --extra dev --no-install-project
    fi

    # Force global 'pytest' command to use the project's virtual environment
    # This overrides any existing pytest (e.g. from pipx) that might use a different python
    if [ -f ".venv/bin/pytest" ]; then
        mkdir -p "$HOME/.local/bin"
        ln -sf "$(pwd)/.venv/bin/pytest" "$HOME/.local/bin/pytest"
    fi
fi

# 3. Provers
echo "Installing Provers..."
mkdir -p provers

# Vampire
if [ ! -f "provers/vampire" ]; then
    curl -L -s https://github.com/vprover/vampire/releases/download/v5.0.0/vampire-Linux-X64.zip -o vampire.zip
    unzip -q vampire.zip && mv vampire provers/vampire && chmod +x provers/vampire && rm vampire.zip
fi

# Eprover
if [ ! -f "provers/eprover" ]; then
    curl -L -s -o eprover.deb http://archive.ubuntu.com/ubuntu/pool/universe/e/eprover/eprover_3.0.03+ds-1_amd64.deb
    ar x eprover.deb

    # Extract data.tar.xz OR data.tar.zst
    if [ -f "data.tar.xz" ]; then
        tar xf data.tar.xz
    elif [ -f "data.tar.zst" ]; then
        # zstd is now installed, so this will work
        tar --use-compress-program=zstd -xf data.tar.zst
    fi

    # Move binary and clean up
    if [ -f "usr/bin/eprover" ]; then
        mv usr/bin/eprover provers/eprover
        chmod +x provers/eprover
    fi

    rm -rf usr debian-binary control.tar.zst data.tar.xz data.tar.zst eprover.deb
fi

echo "Setup Complete"
