import unittest
from naproche.check.engine import Engine, Reporter


class MockReporter(Reporter):
    def __init__(self):
        self.logs = []
        self.errors = []
        self.verified_steps = []

    def log(self, message):
        self.logs.append(message)

    def error(self, message):
        self.errors.append(message)

    def step_verified(self, step_num, description, success, source):
        self.verified_steps.append((step_num, description, success, source))


class TestEngineReporter(unittest.TestCase):
    def test_reporter_integration(self):
        reporter = MockReporter()
        engine = Engine(reporter=reporter)

        # We need to construct some statements manually or parse them.
        # Let's verify that log calls happen.

        # Create a dummy theorem statement (mock)
        # Actually it's easier to use parsed statements if possible, or mock objects.

        # Let's use a real parse flow for simplicity
        from naproche.parser.cnl_parser import parse_cnl
        from naproche.logic.converter import convert_ast

        text = "Let $x$ be a set."
        ast = parse_cnl(text)
        stmts = convert_ast(ast)

        # "Let $x$ be a set." is a Sentence. convert_ast leaves it as a Sentence if not in block.
        # process_statement doesn't handle top-level Sentence.
        # We need to wrap it in a Definition or Axiom to trigger processing.
        # Or test a specific statement type.

        from naproche.logic.models import Axiom

        stmt = Axiom(name="ax1", content=stmts)  # stmts is list of sentences

        engine.check([stmt])

        self.assertTrue(len(reporter.logs) > 0)
        self.assertTrue(any("Added axiom" in msg for msg in reporter.logs))

        # Note: "Let x be a set" inside a Theorem context adds to context.
        # If top level, it might be treated as Axiom or Definition.
        # In current Engine logic:
        # process_statement handles Definition/Axiom.
        # "Let ..." usually parses to Sentence.
        # If it is top level, convert_ast produces ... ?
        # convert_ast converts [Sentence] -> [Theorem?] or [Proof?]
        # Actually convert_ast logic determines structure.
        # If no theorem started, "Let..." is loose sentence.
        # Is it valid?

        # Let's check what convert_ast does with a single sentence.
        # It probably puts it in a default block or treats it as top level?
        # Looking at converter.py is out of scope, but assuming it produces something Engine consumes.
        # If engine.check runs without error, we are good.


if __name__ == "__main__":
    unittest.main()
