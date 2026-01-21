import argparse
import sys
import os
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
from naproche.check.engine import Engine
from lark.exceptions import LarkError

def main():
    parser = argparse.ArgumentParser(description="Naproche - Natural Proof Checking")
    parser.add_argument("file", help="The .ftl.tex file to check")
    parser.add_argument("--benchmark", action="store_true", help="Run all available provers and output benchmark info")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    args = parser.parse_args()

    try:
        with open(args.file, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Checking {args.file}...")

    blocks = extract_forthel_blocks(content)
    all_statements = []

    for i, block in enumerate(blocks):
        try:
            ast = parse_cnl(block)
            statements = convert_ast(ast)
            all_statements.extend(statements)
        except LarkError as e:
            print(f"\n[Error] Parsing failed in Block {i+1}:")
            print(e)
            pass
        except Exception as e:
            print(f"\n[Error] Unexpected error in Block {i+1}: {e}")

    # Determine base path for imports
    base_path = os.path.dirname(os.path.abspath(args.file))
    # If checking math/examples/cantor.ftl.tex, base_path is math/examples/
    # If input is relative, we resolve it.

    # Actually, often imports are relative to the root of the "formalization library".
    # Cantor imports `examples/preliminaries.ftl.tex`.
    # If cantor is in `math/examples/cantor.ftl.tex`.
    # And preliminaries is `math/examples/preliminaries.ftl.tex`.
    # Then `examples/preliminaries.ftl.tex` implies the root is `math/`.

    # We can try to guess the root.
    # If file is `.../math/examples/cantor.ftl.tex`, root is `.../math`.
    if "math" in base_path:
        # Split at 'math'
        root_path = base_path.split("math")[0] + "math"
    else:
        root_path = base_path

    print(f"\nVerifying {len(all_statements)} statements...")
    engine = Engine(base_path=root_path, benchmark_mode=args.benchmark, no_cache=args.no_cache)
    if args.benchmark:
        print("Benchmarking mode enabled: [eprover, vampire]")
    if args.no_cache:
        print("Cache disabled by --no-cache")

    engine.check(all_statements)

    print("\nDone.")

if __name__ == "__main__":
    main()
