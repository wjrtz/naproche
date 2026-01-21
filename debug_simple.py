from naproche.parser.cnl_parser import parse_cnl

try:
    parse_cnl("Take a function $G$.")
except Exception as e:
    print(f"Error 1: {e}")

try:
    parse_cnl("[unfoldlow off]")
except Exception as e:
    print(f"Error 2: {e}")
