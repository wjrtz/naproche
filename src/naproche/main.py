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
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable the proof cache"
    )
    parser.add_argument("--benchmark", action="store_true", help="Run in benchmark mode comparing provers")
    args = parser.parse_args()

    try:
        with open(args.file, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Checking {args.file}...")

    blocks = extract_forthel_blocks(content)
    all_statements = []

    for i, block in enumerate(blocks):
        try:
            # block is now a ForthelBlock object, access content attribute
            ast = parse_cnl(block.content)
            statements = convert_ast(ast)
            all_statements.extend(statements)
        except LarkError as e:
            print(
                f"\n[Error] Parsing failed in Block {i + 1} (offset {block.start_offset}):"
            )
            print(e)
            pass
        except Exception as e:
            print(f"\n[Error] Unexpected error in Block {i + 1}: {e}")

    # Determine base path for imports
    base_path = os.path.dirname(os.path.abspath(args.file))

    if "math" in base_path:
        root_path = base_path.split("math")[0] + "math"
    else:
        root_path = base_path

    print(f"\nVerifying {len(all_statements)} statements...")
    engine = Engine(base_path=root_path, use_cache=not args.no_cache, benchmark=args.benchmark)
    engine.check(all_statements)

    print("\nDone.")


if __name__ == "__main__":
    main()
