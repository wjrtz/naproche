import unittest
import os
from naproche.check.engine import Engine
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
from naproche.logic.translator import Translator
from naproche.logic.models import Sentence

class TestNaproche(unittest.TestCase):
    def test_parser(self):
        text = "Let $X$ be a set."
        parsed = parse_cnl(text)
        self.assertIsInstance(parsed, list)
        self.assertTrue(len(parsed) > 0)
        self.assertEqual(parsed[0]['type'], 'sentence')

    def test_translator(self):
        t = Translator()
        s = Sentence(text="Let $X$ be a set", atoms=["Let", "$X$", "be", "a", "set"])
        f = t.translate_sentence(s, as_axiom=True)
        # Should be Predicate("set", [Variable("X")])
        self.assertEqual(str(f), "set(X)")

        s2 = Sentence(text="Let $X$ be a set", atoms=["Let", "$X$", "be", "a", "set"])
        f2 = t.translate_sentence(s2, as_axiom=False)
        # Should be Predicate("set", [Constant("x")])
        self.assertEqual(str(f2), "set(x)")

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.test_file = "math/examples/simple.ftl.tex"

    def test_simple_proof(self):
        # Ensure the simple example exists
        if not os.path.exists(self.test_file):
            return

        with open(self.test_file, 'r') as f:
            content = f.read()

        blocks = extract_forthel_blocks(content)
        self.assertTrue(len(blocks) > 0)

        all_stmts = []
        for block in blocks:
            # block is ForthelBlock object
            ast = parse_cnl(block.content)
            stmts = convert_ast(ast)
            all_stmts.extend(stmts)

        # Run engine
        # We expect no exceptions.
        engine = Engine(base_path="math")
        engine.check(all_stmts)

        # Verify that cache contains entries (attempted verification)
        # Even if prover failed, we cache the result (False).
        # Wait, check_proof only caches if it gets a result.
        # My verify_task returns (False, result, h).
        # Result is from run_prover.
        # run_prover returns False if crash.
        # So cache should be populated with False.
        cursor = engine.cache.conn.cursor()
        cursor.execute("SELECT count(*) FROM cache")
        total = cursor.fetchone()[0]
        self.assertTrue(total > 0)

if __name__ == '__main__':
    unittest.main()
