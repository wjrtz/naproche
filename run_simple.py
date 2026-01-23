from naproche.check.engine import Engine
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
from naproche.logic.models import Directive
import os

f = "math/examples/simple.ftl.tex"
print(f"Verifying {f}...")
with open(f, "r") as file:
    content = file.read()

blocks = extract_forthel_blocks(content)
all_stmts = []
for block in blocks:
    ast = parse_cnl(block.content)
    stmts = convert_ast(ast)
    all_stmts.extend(stmts)

print("Parsed statements:")
for s in all_stmts:
    if isinstance(s, Directive):
        print(f"Directive: {s.name} args={s.args}")
    else:
        print(f"Stmt: {type(s)}")

engine = Engine(base_path="math")
engine.check(all_stmts)
