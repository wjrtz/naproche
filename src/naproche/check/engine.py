import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from naproche.logic.models import Statement, Sentence, Definition, Theorem, Axiom, Proof
from naproche.logic.translator import Translator
from naproche.logic.fol import Formula, Predicate, Not
from naproche.prover.driver import run_prover
from naproche.check.cache import ProverCache, compute_hash

def verify_task(axioms_repr, context_repr, proof_context_repr, goal_repr):
    # Reconstruct objects not needed if we pass strings?
    # But run_prover expects Formula objects or similar to generate TPTP.
    # To make it simple for multiprocessing, we can pass the TPTP content directly?
    # Or pass the objects if they are picklable. Formula classes are dataclasses, so picklable.

    all_axioms = axioms_repr + context_repr + proof_context_repr

    # Check cache
    cache = ProverCache() # Reload cache in worker? Or share?
    # SQLite is better for concurrent access. JSON file is race-condition prone.
    # But for demonstration, we compute hash here.

    h = compute_hash(all_axioms, ("goal", goal_repr))
    cached = cache.get(h)
    if cached is not None:
        return (True, cached)

    result = run_prover(all_axioms, ("goal", goal_repr))

    # We should update cache. But workers writing to JSON is bad.
    # Return result and let main process update cache.
    return (False, result, h)

class Engine:
    def __init__(self):
        self.translator = Translator()
        self.axioms = []
        self.context = []
        self.counter = 0
        self.cache = ProverCache()

    def check(self, statements: list[Statement]):
        for stmt in statements:
            self.process_statement(stmt)

    def process_statement(self, stmt: Statement):
        if isinstance(stmt, Definition) or isinstance(stmt, Axiom):
            formulas = self.translator.translate_statement(stmt)
            for f in formulas:
                name = f"ax_{self.counter}"
                self.counter += 1
                self.axioms.append((name, f))
                print(f"Added axiom: {f}")

        elif isinstance(stmt, Theorem):
            print(f"Checking Theorem: {stmt.author if stmt.author else 'Unknown'}")
            formulas = self.translator.translate_statement(stmt)
            if not formulas:
                print("Error: Could not translate theorem statement.")
                return

            if len(formulas) > 0:
                self.current_goal = formulas[-1]
                for f in formulas[:-1]:
                    self.context.append((f"ctx_{self.counter}", f))
                    self.counter += 1
                    print(f"Added context: {f}")
                print(f"Goal: {self.current_goal}")

        elif isinstance(stmt, Proof):
            print("Checking Proof (Parallel)...")
            self.check_proof(stmt)

    def check_proof(self, proof: Proof):
        proof_context = []
        tasks = [] # List of (future, step_index, description)

        # We use a ThreadPoolExecutor because run_prover is I/O bound (subprocess)
        # ProcessPoolExecutor would require pickling everything which is fine but slower start.
        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:

            for i, s in enumerate(proof.content):
                if isinstance(s, Sentence):
                    f = self.translator.translate_sentence(s)
                    if not f:
                        print(f"Step {i+1}: Could not translate '{s.text}'")
                        continue

                    text = s.text.strip()
                    is_assumption = False
                    if text.startswith("Assume") or text.startswith("Let") or text.startswith("Take") or text.startswith("Define") or text.startswith("Consider"):
                        is_assumption = True

                    if isinstance(f, Predicate) and f.name == "contrary":
                        if hasattr(self, 'current_goal'):
                            neg_goal = Not(self.current_goal)
                            proof_context.append((f"step_{i}", neg_goal))
                            print(f"Step {i+1}: Assumed contrary: {neg_goal}")
                        continue

                    elif isinstance(f, Predicate) and f.name == "false":
                        print(f"Step {i+1}: Contradiction.")
                        # Submit task
                        # We must capture the CURRENT state of proof_context (copy list)
                        ctx_copy = list(proof_context)
                        future = executor.submit(verify_task, self.axioms, self.context, ctx_copy, Predicate("false", []))
                        tasks.append((future, i+1, "Contradiction"))
                        # Even for contradiction, we might continue parsing? No, usually end of proof.
                        # But we continue loop to submit all tasks if any.

                    elif is_assumption:
                        print(f"Step {i+1}: Assumption/Definition: {f}")
                        proof_context.append((f"step_{i}", f))
                    else:
                        print(f"Step {i+1}: Verifying {f}")
                        ctx_copy = list(proof_context)
                        future = executor.submit(verify_task, self.axioms, self.context, ctx_copy, f)
                        tasks.append((future, i+1, f"Verification of {f}"))

                        proof_context.append((f"step_{i}", f))

            # Collect results
            print("Waiting for verification tasks...")
            for future, step_num, desc in tasks:
                try:
                    res = future.result()
                    # res is (is_cached, success, hash) or (is_cached, success)
                    if len(res) == 3:
                        is_cached, success, h = res
                        if not is_cached:
                            self.cache.set(h, success)
                    else:
                        is_cached, success = res

                    status = "Verified" if success else "Failed"
                    source = "(Cached)" if is_cached else "(Prover)"
                    print(f"Step {step_num}: {desc} -> {status} {source}")

                except Exception as e:
                    print(f"Step {step_num}: Task failed with error: {e}")

# Re-define verify_task outside class to be pickle-able if using ProcessPool,
# but for ThreadPool it's fine.
# However, verify_task logic for caching needs improvement.
