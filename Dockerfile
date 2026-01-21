FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    curl \
    git \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    lark \
    pytest \
    ruff \
    pygls \
    lsprotocol

# Compile Eprover
WORKDIR /tmp
RUN curl -L https://github.com/eprover/eprover/archive/refs/tags/E-3.2.5.tar.gz -o eprover.tar.gz && \
    tar -xzf eprover.tar.gz && \
    cd eprover-E-3.2.5 && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf eprover.tar.gz eprover-E-3.2.5

# Compile Vampire
# Vampire compilation can be tricky. Using a known tag.
# Using v4.8casc2024 as it seems stable and recent enough.
WORKDIR /tmp
RUN curl -L https://github.com/vprover/vampire/archive/refs/tags/v4.9casc2024.tar.gz -o vampire.tar.gz && \
    tar -xzf vampire.tar.gz && \
    cd vampire-4.9casc2024 && \
    cmake . -DBUILD_SHARED_LIBS=0 && \
    make -j$(nproc) && \
    cp bin/vampire /usr/local/bin/vampire && \
    cd .. && \
    rm -rf vampire.tar.gz vampire-4.9casc2024

# Set up environment for the application
WORKDIR /app

# Set environment variables for provers
ENV NAPROCHE_EPROVER=/usr/local/bin/eprover
ENV NAPROCHE_VAMPIRE=/usr/local/bin/vampire

# Copy source code
COPY . .

# Add src to PYTHONPATH so tests can import the package
ENV PYTHONPATH=/app/src
