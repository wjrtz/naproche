import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from naproche.logic.models import Statement, Sentence, Definition, Theorem, Axiom, Proof, Directive, Lemma
from naproche.logic.translator import Translator
from naproche.logic.fol import Formula, Predicate, Not
from naproche.prover.driver import run_provers, EProver, VampireProver, DummyProver, Prover
from naproche.check.cache import ProverCache, compute_hash

# We need to import the parser components to handle included files
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def verify_task(axioms_repr, context_repr, proof_context_repr, goal_repr, active_provers_names, cache_enabled=True):
    all_axioms = axioms_repr + context_repr + proof_context_repr
    cache = ProverCache()
    h = compute_hash(all_axioms, ("goal", goal_repr))

    # Check if we are benchmarking. Benchmarking happens if active_provers_names has more than 1 prover.
    is_benchmarking = len(active_provers_names) > 1

    if cache_enabled and not is_benchmarking:
        cached = cache.get(h)
        if cached is not None:
            return (True, cached, h, [])

    provers = []
    for name in active_provers_names:
        if name == "eprover":
            provers.append(EProver())
        elif name == "vampire":
            provers.append(VampireProver())
        elif name == "dummy":
            provers.append(DummyProver())

    success, results = run_provers(provers, all_axioms, ("goal", goal_repr))

    # Store result in cache if successful and cache is enabled
    # The requirement says: "for everything wrapt inside [cache off] [cache on] the cache should be invalidated."
    # This implies we shouldn't read from cache, and maybe also update it if we found a proof?
    # Or maybe we should NOT write to cache if [cache off]?
    # Usually [cache off] means "don't trust cache" and "don't populate cache"? Or just "force check"?
    # If "cache should be invalidated", it suggests removing it or just ignoring it.
    # The requirement says "support for a --no-cache argument which disables the cache and also invalidate cache commands inside the formilaziton".
    # This implies --no-cache overrides everything.
    # If cache_enabled is False, we definitely skip reading.
    # Should we write? If we just proved something expensive, maybe we should cache it for later runs (if cache is re-enabled)?
    # But if "cache off" means "I changed something deeply or I suspect cache corruption", maybe writing is fine.
    # However, standard practice for "no-cache" is usually "no read", but "write" depends.
    # If I "invalidate", I essentially treat it as unknown.
    # If I solve it, I can update the cache with the new result.
    # So writing is probably fine, unless [cache off] implies "don't touch cache".
    # Let's assume writing is beneficial unless explicitly forbidden (like "read-only cache" which is different).
    if success and cache_enabled:
        cache.set(h, True)

    return (False, success, h, results)

class Engine:
    def __init__(self, base_path=".", benchmark_mode=False, no_cache=False):
        self.translator = Translator()
        self.axioms = []
        self.context = []
        self.counter = 0
        self.cache = ProverCache()
        self.base_path = base_path
        self.processed_files = set()
        self.benchmark_mode = benchmark_mode
        self.no_cache = no_cache
        self.local_cache_enabled = True # Tracks [cache on/off] state
        self.active_provers = ["eprover", "vampire"] if benchmark_mode else ["eprover"]

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
                print(f"Warning: Included file not found: {filepath}")
                return

        print(f"Processing included file: {full_path}")
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            blocks = extract_forthel_blocks(content)
            all_stmts = []
            for block in blocks:
                try:
                    ast = parse_cnl(block)
                    stmts = convert_ast(ast)
                    all_stmts.extend(stmts)
                except Exception as e:
                    # print(f"Error parsing included block: {e}")
                    pass

            # Recursively check/process with is_included=True
            self.check(all_stmts, is_included=True)
        except Exception as e:
            print(f"Error processing included file {full_path}: {e}")

    def process_statement(self, stmt: Statement, is_included=False):
        if isinstance(stmt, Directive):
            if stmt.action == "read":
                path = stmt.value
                self.process_file(path)
            elif stmt.action == "prover":
                if self.benchmark_mode:
                    print(f"Note: Ignoring [prover {stmt.value}] directive due to benchmark mode.")
                else:
                    prover_name = stmt.value
                    if prover_name not in ["eprover", "vampire", "dummy"]:
                         print(f"Warning: Unknown prover '{prover_name}'. Ignoring.")
                    else:
                         self.active_provers = [prover_name]
                         print(f"Switched prover to: {prover_name}")
            elif stmt.action == "cache":
                val = stmt.value.lower()
                if val == "on":
                    self.local_cache_enabled = True
                    print("Local cache enabled.")
                elif val == "off":
                    self.local_cache_enabled = False
                    print("Local cache disabled.")
                else:
                    print(f"Warning: Unknown cache directive value '{val}'. Use 'on' or 'off'.")

        elif isinstance(stmt, Definition) or isinstance(stmt, Axiom) or isinstance(stmt, Lemma):
            # Treat Lemmas as Axioms if included or generally useful results
            formulas = self.translator.translate_statement(stmt)
            for f in formulas:
                name = f"ax_{self.counter}"
                self.counter += 1
                self.axioms.append((name, f))
                print(f"Added axiom: {f}")

        elif isinstance(stmt, Theorem):
            # If included, treat theorem as axiom (proved result)
            if is_included:
                print(f"Importing Theorem: {stmt.author if stmt.author else 'Unknown'}")
                formulas = self.translator.translate_statement(stmt)
                # Assume last formula is the theorem claim
                if formulas:
                     f = formulas[-1]
                     name = f"thm_{self.counter}"
                     self.counter += 1
                     self.axioms.append((name, f))
                     print(f"Added axiom (Theorem): {f}")
            else:
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
            if is_included:
                pass # Skip proofs of included files
            else:
                print("Checking Proof (Parallel)...")
                self.check_proof(stmt)

    def check_proof(self, proof: Proof):
        proof_context = []
        tasks = []

        provers_to_use = list(self.active_provers)

        # Determine effective cache state
        # If global no_cache is True, cache is disabled regardless of local state.
        # Otherwise, use local_cache_enabled.
        effective_cache_enabled = (not self.no_cache) and self.local_cache_enabled

        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:

            for i, s in enumerate(proof.content):
                # Update cache or prover state if directive found
                if isinstance(s, Directive):
                    if s.action == "cache":
                        val = s.value.lower()
                        if val == "on":
                            self.local_cache_enabled = True
                            print("Local cache enabled (inside proof).")
                        elif val == "off":
                            self.local_cache_enabled = False
                            print("Local cache disabled (inside proof).")

                        # Update effective cache enabled for subsequent steps
                        effective_cache_enabled = (not self.no_cache) and self.local_cache_enabled
                        continue
                    elif s.action == "prover":
                        prover_name = s.value
                        if prover_name in ["eprover", "vampire", "dummy"]:
                             # Only update if not in benchmark mode (benchmark uses all)
                             if not self.benchmark_mode:
                                 provers_to_use = [prover_name]
                                 print(f"Switched prover to: {prover_name} (inside proof)")
                             else:
                                 print(f"Note: Ignoring [prover {prover_name}] inside proof due to benchmark mode.")
                        else:
                             print(f"Warning: Unknown prover '{prover_name}'. Ignoring.")
                        continue

                # Recursively process nested blocks inside proof (like Lemma or Proof)
                if isinstance(s, Lemma) or isinstance(s, Proof):
                     print(f"Checking nested {type(s).__name__}...")
                     self.process_statement(s)
                     continue

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
                        ctx_copy = list(proof_context)
                        future = executor.submit(verify_task, self.axioms, self.context, ctx_copy, Predicate("false", []), provers_to_use, effective_cache_enabled)
                        tasks.append((future, i+1, "Contradiction"))

                    elif is_assumption:
                        print(f"Step {i+1}: Assumption/Definition: {f}")
                        proof_context.append((f"step_{i}", f))
                    else:
                        print(f"Step {i+1}: Verifying {f}")
                        ctx_copy = list(proof_context)
                        future = executor.submit(verify_task, self.axioms, self.context, ctx_copy, f, provers_to_use, effective_cache_enabled)
                        tasks.append((future, i+1, f"Verification of {f}"))

                        proof_context.append((f"step_{i}", f))

            print("Waiting for verification tasks...")
            for future, step_num, desc in tasks:
                try:
                    res = future.result()
                    # verify_task returns: (False, success, h, results)
                    if len(res) == 4:
                        is_cached, success, h, results = res
                        if not is_cached and success:
                             # We already set cache in verify_task if success.
                             pass

                        # Benchmarking info
                        if len(results) > 1:
                            print(f"  [Benchmark] Step {step_num}:")
                            fastest_prover = None
                            min_time = float('inf')

                            for r in results:
                                status = "Success" if r.success else "Failed"
                                print(f"    - {r.prover_name}: {status} ({r.time_taken:.4f}s)")
                                if r.success and r.time_taken < min_time:
                                    min_time = r.time_taken
                                    fastest_prover = r.prover_name

                            if fastest_prover:
                                print(f"  => Suggestion: Use [prover {fastest_prover}]")

                    else:
                        # Legacy fallback if I messed up unpack
                        print("Error: unexpected result format from verify_task")
                        continue

                    status = "Verified" if success else "Failed"
                    source = "(Cached)" if is_cached else "(Prover)"
                    print(f"Step {step_num}: {desc} -> {status} {source}")

                except Exception as e:
                    logger.error(f"Step {step_num}: Task failed with error: {e}", exc_info=True)
