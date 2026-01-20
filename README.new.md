# Naproche (Python Implementation)

A Python re-implementation of the Naproche system for proof checking of natural mathematical documents.

## Features

- **Robust Parsing**: Uses `lark` for flexible CNL parsing.
- **Parallel Checking**: Verifies proof steps in parallel using multiprocessing.
- **Caching**: Caches proof results to speed up re-checking.
- **Prover Integration**: Supports automated theorem provers (currently `eprover`) via TPTP.

## Installation

1. Install Python 3.8+.
2. Install dependencies:
   ```bash
   pip install lark
   ```
3. Install `eprover` and ensure it is in your PATH.

## Usage

Check a `.ftl.tex` file:

```bash
python3 src/naproche/main.py path/to/file.ftl.tex
```

## Structure

- `src/naproche/parser`: Grammar and parsing logic.
- `src/naproche/logic`: Internal models and logical translation.
- `src/naproche/prover`: ATP driver and TPTP generation.
- `src/naproche/check`: Checking engine, parallelism, and caching.
