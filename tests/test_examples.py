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
        # We don't remove cache here because we handle it per file in test loop

    def test_all_examples(self):
        # Prioritize core examples first for faster feedback
        core_files = glob.glob(os.path.join(self.examples_dir, "simple.ftl.tex")) + \
                     glob.glob(os.path.join(self.examples_dir, "tarski.ftl.tex")) + \
                     glob.glob(os.path.join(self.examples_dir, "cantor.ftl.tex")) + \
                     glob.glob(os.path.join(self.examples_dir, "**", "checkerboard.ftl.tex"), recursive=True)

        all_files = glob.glob(os.path.join(self.examples_dir, "**/*.ftl.tex"), recursive=True)

        # Deduplicate and sort
        files = sorted(list(set(all_files)))

        # Move core files to front
        for cf in reversed(core_files):
            if cf in files:
                files.remove(cf)
                files.insert(0, cf)

        failures = []
        for f in files:
            # Clear cache for isolation
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)

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

                cursor = engine.cache.conn.cursor()
                cursor.execute("SELECT result FROM proofs")
                results = cursor.fetchall()

                # Close connection to allow file deletion
                engine.cache.conn.close()

                failed_proofs = [r for r in results if r[0] == 0 or r[0] is False]
                if failed_proofs:
                     failures.append((f, f"{len(failed_proofs)} proofs failed (out of {len(results)})"))

            except Exception as e:
                failures.append((f, f"Crash: {e}"))

        if failures:
            msg = "\n".join([f"{f}: {e}" for f, e in failures])
            self.fail(f"Failed to verify some examples:\n{msg}")

if __name__ == "__main__":
    unittest.main()
