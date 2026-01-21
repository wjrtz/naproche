import unittest
import os
import io
import contextlib
from naproche.check.engine import Engine
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
from naproche.prover.driver import ProverResult
from naproche.check.cache import ProverCache

# Mock provers
class MockEProver:
    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.called = False

    def run(self, tptp_path, timeout):
        self.called = True
        return ProverResult(self.should_succeed, 0.0, "eprover", "Mock")

    @property
    def name(self):
        return "eprover"

class MockVampireProver:
    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.called = False

    def run(self, tptp_path, timeout):
        self.called = True
        return ProverResult(self.should_succeed, 0.0, "vampire", "Mock")

    @property
    def name(self):
        return "vampire"

class MockDummyProver:
    def __init__(self):
        pass
    def run(self, tptp_path, timeout):
        return ProverResult(True, 0.0, "dummy", "Mock")
    @property
    def name(self):
        return "dummy"

# Helper to parse text into statements
def parse_text(text):
    ast = parse_cnl(text)
    return convert_ast(ast)

class TestFeatures(unittest.TestCase):
    def setUp(self):
        if os.path.exists(".naproche_cache.db"):
            os.remove(".naproche_cache.db")

        # Patch classes in engine module where they are used
        import naproche.check.engine as engine_module

        self.original_EProver = engine_module.EProver
        self.original_VampireProver = engine_module.VampireProver
        self.original_DummyProver = engine_module.DummyProver

        engine_module.EProver = lambda: MockEProver(True)
        engine_module.VampireProver = lambda: MockVampireProver(True)
        engine_module.DummyProver = lambda: MockDummyProver()

    def tearDown(self):
        import naproche.check.engine as engine_module
        engine_module.EProver = self.original_EProver
        engine_module.VampireProver = self.original_VampireProver
        engine_module.DummyProver = self.original_DummyProver

        if os.path.exists(".naproche_cache.db"):
            os.remove(".naproche_cache.db")

    def test_prover_directive_vampire(self):
        text = """
        [prover vampire]
        \\begin{theorem}
        1=1.
        \\end{theorem}
        """
        stmts = parse_text(text)
        engine = Engine()
        engine.check(stmts)
        self.assertEqual(engine.active_provers, ["vampire"])

    def test_prover_directive_dummy(self):
        text = """
        [prover dummy]
        \\begin{theorem}
        1=1.
        \\end{theorem}
        \\begin{proof}
        1=0.
        \\end{proof}
        """
        # dummy should prove 1=0.

        stmts = parse_text(text)
        engine = Engine()

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            engine.check(stmts)
        output = f.getvalue()

        self.assertIn("Verified (Prover)", output)

    def test_benchmark_mode_corrected(self):
        text = """
        \\begin{theorem}
        1=1.
        \\end{theorem}
        \\begin{proof}
        1=1.
        \\end{proof}
        """
        stmts = parse_text(text)
        engine = Engine(benchmark_mode=True)

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            engine.check(stmts)
        output = f.getvalue()

        self.assertIn("[Benchmark]", output)
        self.assertIn("eprover: Success", output)
        self.assertIn("vampire: Success", output)
        self.assertIn("Suggestion: Use [prover eprover]", output)

    def test_no_cache_flag_corrected(self):
        text = """
        \\begin{theorem}
        1=1.
        \\end{theorem}
        \\begin{proof}
        1=1.
        \\end{proof}
        """
        stmts = parse_text(text)

        # Run 1: Normal
        engine1 = Engine(no_cache=False)
        f1 = io.StringIO()
        with contextlib.redirect_stdout(f1):
            engine1.check(stmts)
        out1 = f1.getvalue()
        self.assertIn("(Prover)", out1)

        # Run 2: No cache (should be Prover again, and NOT Cached)
        engine2 = Engine(no_cache=True)
        f2 = io.StringIO()
        with contextlib.redirect_stdout(f2):
            engine2.check(stmts)
        out2 = f2.getvalue()
        self.assertIn("(Prover)", out2)
        self.assertNotIn("(Cached)", out2)

        # Run 3: Normal (should use cache from Run 1)
        engine3 = Engine(no_cache=False)
        f3 = io.StringIO()
        with contextlib.redirect_stdout(f3):
            engine3.check(stmts)
        out3 = f3.getvalue()
        self.assertIn("(Cached)", out3)

    def test_cache_directives_final_revised(self):
        text = """
        \\begin{proof}
        [cache off]
        \\begin{lemma} 1=1. \\end{lemma}
        \\begin{proof} 1=1. \\end{proof}
        [cache on]
        \\begin{lemma} 1=1. \\end{lemma}
        \\begin{proof} 1=1. \\end{proof}
        \\end{proof}
        """

        stmts = parse_text(text)

        # Pre-populate cache manually
        pre_text = """
        \\begin{theorem} 1=1. \\end{theorem}
        \\begin{proof} 1=1. \\end{proof}
        """
        pre_stmts = parse_text(pre_text)
        engine0 = Engine()
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            engine0.check(pre_stmts) # Populates cache for 1=1.

        # Run Test
        engine = Engine()

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            engine.check(stmts)
        output = f.getvalue()

        # We expect verification logs.
        # Check that we have both source types.
        # The output order should be: Prover (first), Cached (second).
        self.assertIn("(Prover)", output)
        self.assertIn("(Cached)", output)

if __name__ == '__main__':
    unittest.main()
