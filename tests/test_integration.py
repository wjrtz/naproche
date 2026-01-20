import unittest
import os
from naproche.check.engine import Engine
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
from naproche.check.cache import CACHE_FILE

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.simple_file = "math/examples/simple.ftl.tex"
        self.cantor_file = "math/examples/cantor.ftl.tex"
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)

    def test_simple_proof_verification(self):
        if not os.path.exists(self.simple_file):
            return

        with open(self.simple_file, 'r') as f:
            content = f.read()

        blocks = extract_forthel_blocks(content)
        all_stmts = []
        for block in blocks:
            ast = parse_cnl(block)
            stmts = convert_ast(ast)
            all_stmts.extend(stmts)

        engine = Engine(base_path="math")
        engine.check(all_stmts)

        # Now engine.cache.cache should have entries because check populated it
        successes = [v for v in engine.cache.cache.values() if v]
        self.assertTrue(len(successes) > 0, "Expected at least one successful verification")

    def test_cantor_runs(self):
        if not os.path.exists(self.cantor_file):
            return

        with open(self.cantor_file, 'r') as f:
            content = f.read()

        blocks = extract_forthel_blocks(content)
        all_stmts = []
        for block in blocks:
            ast = parse_cnl(block)
            stmts = convert_ast(ast)
            all_stmts.extend(stmts)

        engine = Engine(base_path="math")
        engine.check(all_stmts)

if __name__ == "__main__":
    unittest.main()
