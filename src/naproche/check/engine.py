import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from naproche.logic.models import Statement, Sentence, Definition, Theorem, Axiom, Proof, Directive, Lemma
from naproche.logic.translator import Translator
from naproche.logic.fol import Formula, Predicate, Not
from naproche.prover.driver import run_prover
from naproche.check.cache import ProverCache, compute_hash

# We need to import the parser components to handle included files
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast

def verify_task(axioms_repr, context_repr, proof_context_repr, goal_repr):
    all_axioms = axioms_repr + context_repr + proof_context_repr
    cache = ProverCache()
    h = compute_hash(all_axioms, ("goal", goal_repr))
    cached = cache.get(h)
    if cached is not None:
        return (True, cached, h)
    result = run_prover(all_axioms, ("goal", goal_repr))
    return (False, result, h)

class Reporter:
    """Abstract base class for reporting checking progress and results."""
    def log(self, message):
        pass
    def error(self, message):
        pass
    def step_verified(self, step_num, description, success, source):
        pass

class StdoutReporter(Reporter):
    def log(self, message):
        print(message)

    def error(self, message):
        print(f"Error: {message}")

    def step_verified(self, step_num, description, success, source):
        status = "Verified" if success else "Failed"
        print(f"Step {step_num}: {description} -> {status} {source}")


class Engine:
    def __init__(self, base_path=".", reporter=None):
        self.translator = Translator()
        self.axioms = []
        self.context = []
        self.counter = 0
        self.cache = ProverCache()
        self.base_path = base_path
        self.processed_files = set()
        self.reporter = reporter if reporter else StdoutReporter()

    def check(self, statements: list[Statement], is_included=False):
        for stmt in statements:
            self.process_statement(stmt, is_included)

    def process_file(self, filepath):
        if filepath in self.processed_files:
            return
        self.processed_files.add(filepath)

        full_path = os.path.join(self.base_path, filepath)
        if not os.path.exists(full_path):
            if os.path.exists(os.path.join(self.base_path, "math", filepath)):
                full_path = os.path.join(self.base_path, "math", filepath)
            else:
                self.reporter.log(f"Warning: Included file not found: {filepath}")
                return

        self.reporter.log(f"Processing included file: {full_path}")
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            blocks = extract_forthel_blocks(content)
            all_stmts = []
            for block in blocks:
                try:
                    # block is a ForthelBlock, need block.content
                    ast = parse_cnl(block.content)
                    stmts = convert_ast(ast)
                    all_stmts.extend(stmts)
                except Exception as e:
                    # self.reporter.log(f"Error parsing included block: {e}")
                    pass

            # Recursively check/process with is_included=True
            self.check(all_stmts, is_included=True)
        except Exception as e:
            self.reporter.log(f"Error processing included file {full_path}: {e}")

    def process_statement(self, stmt: Statement, is_included=False):
        if isinstance(stmt, Directive):
            path = stmt.path
            self.process_file(path)

        elif isinstance(stmt, Definition) or isinstance(stmt, Axiom) or isinstance(stmt, Lemma):
            # Treat Lemmas as Axioms if included or generally useful results
            formulas = self.translator.translate_statement(stmt)
            for f in formulas:
                name = f"ax_{self.counter}"
                self.counter += 1
                self.axioms.append((name, f))
                self.reporter.log(f"Added axiom: {f}")

        elif isinstance(stmt, Theorem):
            # If included, treat theorem as axiom (proved result)
            if is_included:
                self.reporter.log(f"Importing Theorem: {stmt.author if stmt.author else 'Unknown'}")
                formulas = self.translator.translate_statement(stmt)
                # Assume last formula is the theorem claim
                if formulas:
                     f = formulas[-1]
                     name = f"thm_{self.counter}"
                     self.counter += 1
                     self.axioms.append((name, f))
                     self.reporter.log(f"Added axiom (Theorem): {f}")
            else:
                self.reporter.log(f"Checking Theorem: {stmt.author if stmt.author else 'Unknown'}")
                formulas = self.translator.translate_statement(stmt)
                if not formulas:
                    self.reporter.error("Could not translate theorem statement.")
                    return

                if len(formulas) > 0:
                    self.current_goal = formulas[-1]
                    for f in formulas[:-1]:
                        self.context.append((f"ctx_{self.counter}", f))
                        self.counter += 1
                        self.reporter.log(f"Added context: {f}")
                    self.reporter.log(f"Goal: {self.current_goal}")

        elif isinstance(stmt, Proof):
            if is_included:
                pass # Skip proofs of included files
            else:
                self.reporter.log("Checking Proof (Parallel)...")
                self.check_proof(stmt)

    def check_proof(self, proof: Proof):
        proof_context = []
        tasks = []

        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:

            for i, s in enumerate(proof.content):
                if isinstance(s, Sentence):
                    f = self.translator.translate_sentence(s)
                    if not f:
                        self.reporter.error(f"Step {i+1}: Could not translate '{s.text}'")
                        continue

                    text = s.text.strip()
                    is_assumption = False
                    if text.startswith("Assume") or text.startswith("Let") or text.startswith("Take") or text.startswith("Define") or text.startswith("Consider"):
                        is_assumption = True

                    if isinstance(f, Predicate) and f.name == "contrary":
                        if hasattr(self, 'current_goal'):
                            neg_goal = Not(self.current_goal)
                            proof_context.append((f"step_{i}", neg_goal))
                            self.reporter.log(f"Step {i+1}: Assumed contrary: {neg_goal}")
                        continue

                    elif isinstance(f, Predicate) and f.name == "false":
                        self.reporter.log(f"Step {i+1}: Contradiction.")
                        ctx_copy = list(proof_context)
                        future = executor.submit(verify_task, self.axioms, self.context, ctx_copy, Predicate("false", []))
                        tasks.append((future, i+1, "Contradiction"))

                    elif is_assumption:
                        self.reporter.log(f"Step {i+1}: Assumption/Definition: {f}")
                        proof_context.append((f"step_{i}", f))
                    else:
                        self.reporter.log(f"Step {i+1}: Verifying {f}")
                        ctx_copy = list(proof_context)
                        future = executor.submit(verify_task, self.axioms, self.context, ctx_copy, f)
                        tasks.append((future, i+1, f"Verification of {f}"))

                        proof_context.append((f"step_{i}", f))

            self.reporter.log("Waiting for verification tasks...")
            for future, step_num, desc in tasks:
                try:
                    res = future.result()
                    if len(res) == 3:
                        is_cached, success, h = res
                        if not is_cached:
                            self.cache.set(h, success)
                    else:
                        is_cached, success = res

                    source = "(Cached)" if is_cached else "(Prover)"
                    self.reporter.step_verified(step_num, desc, success, source)

                except Exception as e:
                    self.reporter.error(f"Step {step_num}: Task failed with error: {e}")
