# Naproche (Python Implementation)

A Python re-implementation of the Naproche system for proof checking of natural mathematical documents.

## Features

- **Robust Parsing**: Uses `lark` for flexible CNL parsing.
- **Parallel Checking**: Verifies proof steps in parallel using multiprocessing.
- **Caching**: Caches proof results in an SQLite database (`.naproche_cache.db`) to speed up re-checking.
- **Prover Integration**: Supports automated theorem provers (currently `eprover` and `vampire`) via TPTP.

## Installation

This project is managed with `uv`.

1. Install `uv`:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install dependencies and the package:
   ```bash
   uv sync
   ```
   Or using pip:
   ```bash
   pip install -e .
   ```

## External Dependencies

The system requires automated theorem provers to be installed and available in the system path or configured via environment variables.

- **Eprover**: Set `NAPROCHE_EPROVER` to the path of the `eprover` executable.
- **Vampire**: Set `NAPROCHE_VAMPIRE` to the path of the `vampire` executable.

The provided `Dockerfile` sets up an environment with these provers pre-installed.

## Usage

Check a `.ftl.tex` file using the installed CLI:

```bash
naproche math/examples/cantor.ftl.tex
```

Or run directly from source:

```bash
uv run naproche math/examples/cantor.ftl.tex
```

## Structure

- `src/naproche/parser`: Grammar and parsing logic.
- `src/naproche/logic`: Internal models and logical translation.
- `src/naproche/prover`: ATP driver and TPTP generation.
- `src/naproche/check`: Checking engine, parallelism, and caching.
