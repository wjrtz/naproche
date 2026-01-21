from naproche.parser.cnl_parser import parse_cnl
from lark.exceptions import LarkError


def check_blocks(blocks):
    print(f"Found {len(blocks)} ForTheL blocks.")
    for i, block in enumerate(blocks):
        print(f"--- Block {i + 1} ---")
        try:
            _parsed = parse_cnl(block)
            print(f"Successfully parsed block {i + 1}")
            # print(parsed) # Debug
        except LarkError as e:
            print(f"Error parsing block {i + 1}:")
            print(e)
        print("------------------")
