FROM python:3.11-slim

WORKDIR /app

# Ensure uv is in PATH for all subsequent run commands
ENV PATH="/root/.cargo/bin:$PATH"

# Copy the setup script first to leverage caching if dependencies haven't changed
COPY pyproject.toml uv.lock* ./
COPY scripts/setup.sh ./scripts/setup.sh

# Run setup with system deps
RUN ./scripts/setup.sh --install-system-deps --install-python-deps --install-provers

# Copy the rest of the application
COPY . .

# Sync again to install the project itself
RUN ./scripts/setup.sh --install-python-deps

# Set up environment
# Ensure .venv/bin is in PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV NAPROCHE_EPROVER=/app/provers/eprover
ENV NAPROCHE_VAMPIRE=/app/provers/vampire
ENV PYTHONPATH=/app/src

CMD ["naproche"]
