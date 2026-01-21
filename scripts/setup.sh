#!/bin/bash
set -e

# 1. System Deps
# Added 'zstd' to the list so tar can unpack the Eprover archive
echo "Installing System Deps..."
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential curl git picosat unzip binutils wget zstd zlib1g-dev

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
    echo "Downloading and building Eprover..."
    # Using master branch as tags were failing to resolve to valid tarballs
    curl -L -s https://github.com/eprover/eprover/tarball/master -o eprover.tar.gz
    tar -xf eprover.tar.gz

    # Check directory name (tarball/master usually extracts to user-repo-hash)
    DIR_NAME=$(find . -maxdepth 1 -type d -name "eprover-eprover*" | head -n 1)

    if [ -z "$DIR_NAME" ] || [ ! -d "$DIR_NAME" ]; then
         echo "Error: Could not find Eprover source directory."
         ls -d */
         exit 1
    fi

    cd "$DIR_NAME"

    # Configure and build
    ./configure
    make -j$(nproc)

    # Move binary
    if [ -f "PROVER/eprover" ]; then
        mv PROVER/eprover ../provers/eprover
    elif [ -f "bin/eprover" ]; then
        mv bin/eprover ../provers/eprover
    else
        echo "Error: Eprover binary not found after build."
        exit 1
    fi

    cd ..
    rm -rf "$DIR_NAME" eprover.tar.gz
fi

echo "Setup Complete"

# Export environment variables for provers
# Use absolute paths relative to this script location
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NAPROCHE_VAMPIRE="$REPO_ROOT/provers/vampire"
export NAPROCHE_EPROVER="$REPO_ROOT/provers/eprover"
