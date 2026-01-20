import argparse
import sys
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
from naproche.check.engine import Engine
from lark.exceptions import LarkError

def main():
    parser = argparse.ArgumentParser(description="Naproche - Natural Proof Checking")
    parser.add_argument("file", help="The .ftl.tex file to check")
    args = parser.parse_args()

    try:
        with open(args.file, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Checking {args.file}...")

    # 1. Extract ForTheL blocks
    # We should keep track of line numbers. extract_forthel_blocks currently returns list of strings.
    # We can improve it to return (line_offset, content).
    blocks = extract_forthel_blocks(content)

    # 2. Parse and Convert
    all_statements = []

    for i, block in enumerate(blocks):
        try:
            # print(f"Processing Block {i+1}...")
            ast = parse_cnl(block)
            statements = convert_ast(ast)
            all_statements.extend(statements)
        except LarkError as e:
            print(f"\n[Error] Parsing failed in Block {i+1}:")
            # e.pos_in_stream, e.line, e.column might be available
            print(e)
            # Continue or exit?
            # For checking, we might want to stop or continue.
            pass
        except Exception as e:
            print(f"\n[Error] Unexpected error in Block {i+1}: {e}")

    # 3. Check
    print(f"\nVerifying {len(all_statements)} statements...")
    engine = Engine()
    engine.check(all_statements)

    print("\nDone.")

if __name__ == "__main__":
    main()
