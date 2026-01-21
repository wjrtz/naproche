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
export PATH="$HOME/.cargo/bin:$PATH"

# Run sync only if pyproject.toml exists
if [ -f "pyproject.toml" ]; then
    uv sync --frozen || uv sync
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
