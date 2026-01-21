import unittest
import os
import glob
from naproche.check.engine import Engine
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
from naproche.check.cache import CACHE_FILE

class TestExamples(unittest.TestCase):
    def setUp(self):
        self.examples_dir = "math/examples"
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)

    def verify_file(self, filepath):
        if not os.path.exists(filepath):
            print(f"Skipping {filepath}: not found")
            return

        print(f"Verifying {filepath}...")
        with open(filepath, "r") as f:
            content = f.read()

        blocks = extract_forthel_blocks(content)
        all_stmts = []
        try:
            for block in blocks:
                ast = parse_cnl(block.content)
                stmts = convert_ast(ast)
                all_stmts.extend(stmts)
        except Exception as e:
            self.fail(f"Parsing/Conversion failed for {filepath}: {e}")

        engine = Engine(base_path="math")
        # Engine.check handles exceptions internally usually, but let's see.
        engine.check(all_stmts)

        # We don't assert verification success for all, as some might be hard or slow.
        # But we assert no crash.
        # And we can check if at least some proofs were attempted.
        # cursor = engine.cache.conn.cursor()
        # cursor.execute("SELECT count(*) FROM proofs")
        # count = cursor.fetchone()[0]
        # if len(all_stmts) > 0:
        #    print(f"  Proofs attempted: {count}")


    def test_all_examples(self):
        files = glob.glob(os.path.join(self.examples_dir, "**/*.ftl.tex"), recursive=True)

        failures = []
        for f in files:
            if "simple.ftl.tex" in f or "checkerboard.ftl.tex" in f:
                # We enforce success for these core examples
                # (Or actually, the user said ALL examples need to verify)
                # But let's start with checking success.
                pass

            try:
                print(f"Verifying {f}...")
                with open(f, "r") as file:
                    content = file.read()

                blocks = extract_forthel_blocks(content)
                all_stmts = []
                for block in blocks:
                    ast = parse_cnl(block.content)
                    stmts = convert_ast(ast)
                    all_stmts.extend(stmts)

                engine = Engine(base_path="math")
                engine.check(all_stmts)

                # Check for verification failures in cache/reporter
                # We can inspect engine.reporter.errors or check cache
                # The engine prints errors to stdout but we can check internal state if we had access.
                # Since Engine uses default reporter which prints to stdout, we can't easily capture it unless we mock.
                # However, engine.check() usually doesn't raise exception on verification failure, only on crash.

                # To really test verification success, we need to inspect the cache.
                cursor = engine.cache.conn.cursor()
                cursor.execute("SELECT result FROM proofs")
                results = cursor.fetchall()

                # If any proof failed (result=0), we should flag it?
                # Or maybe some are expected to fail?
                # The user said "All examples need to verify successfully."
                failed_proofs = [r for r in results if r[0] == 0 or r[0] is False]
                if failed_proofs:
                     failures.append((f, f"{len(failed_proofs)} proofs failed"))

            except Exception as e:
                failures.append((f, f"Crash: {e}"))

        if failures:
            msg = "\n".join([f"{f}: {e}" for f, e in failures])
            self.fail(f"Failed to verify some examples:\n{msg}")

if __name__ == "__main__":
    unittest.main()
