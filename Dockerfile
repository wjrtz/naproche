FROM python:3.11-slim

WORKDIR /app

# Ensure uv is in PATH for all subsequent run commands
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"

# Copy the setup script first to leverage caching if dependencies haven't changed
COPY pyproject.toml uv.lock* README.md ./
COPY scripts/setup.sh ./scripts/setup.sh

# Install sudo and run setup script
RUN apt-get update && apt-get install -y sudo && ./scripts/setup.sh

# Copy the rest of the application
COPY . .

# Sync again to install the project itself
RUN ./scripts/setup.sh

# Set up environment
# Ensure .venv/bin is in PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV NAPROCHE_EPROVER=/app/provers/eprover
ENV NAPROCHE_VAMPIRE=/app/provers/vampire
ENV PYTHONPATH=/app/src

CMD ["naproche"]
