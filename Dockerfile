FROM python:3.11-slim

# Install system dependencies
# Added picosat for eprover dependency
# Added unzip for vampire binary extraction
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    picosat \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    lark \
    pytest \
    ruff \
    pygls \
    lsprotocol

# Install Eprover (using Ubuntu deb package for version 3.0.03)
# Note: python:3.11-slim is Debian-based, but Ubuntu packages are often compatible.
# This avoids compiling from source which is slow.
# Using apt-get install on the .deb file to handle dependencies automatically.
WORKDIR /tmp
RUN curl -L -o eprover.deb http://archive.ubuntu.com/ubuntu/pool/universe/e/eprover/eprover_3.0.03+ds-1_amd64.deb && \
    apt-get update && apt-get install -y ./eprover.deb && \
    rm eprover.deb && \
    rm -rf /var/lib/apt/lists/*

# Install Vampire (precompiled binary)
# Using v5.0.0 which provides precompiled static binaries for Linux.
WORKDIR /usr/local/bin
RUN curl -L https://github.com/vprover/vampire/releases/download/v5.0.0/vampire-Linux-X64.zip -o vampire.zip && \
    unzip vampire.zip && \
    chmod +x vampire && \
    rm vampire.zip

# Set up environment for the application
WORKDIR /app

# Set environment variables for provers
# eprover from deb installs to /usr/bin/eprover
ENV NAPROCHE_EPROVER=/usr/bin/eprover
ENV NAPROCHE_VAMPIRE=/usr/local/bin/vampire

# Copy source code
COPY . .

# Add src to PYTHONPATH so tests can import the package
ENV PYTHONPATH=/app/src
