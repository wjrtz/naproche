import os
import multiprocessing
import time
from concurrent.futures import ThreadPoolExecutor
from naproche.logic.models import (
    Statement,
    Sentence,
    Definition,
    Theorem,
    Axiom,
    Proof,
    Directive,
    Lemma,
)
from naproche.logic.translator import Translator
from naproche.logic.fol import Predicate, Not
from naproche.check.cache import ProverCache, compute_hash
from naproche.check.prover_manager import ProverManager

# We need to import the parser components to handle included files
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast


def verify_task(
    axioms_repr,
    context_repr,
    proof_context_repr,
    goal_repr,
    prover_instance,
    use_cache=True,
    benchmark_mode=False,
    prover_manager=None,
):
    all_axioms = axioms_repr + context_repr + proof_context_repr
    h = compute_hash(all_axioms, ("goal", goal_repr))

    if use_cache and not benchmark_mode:
        cache = ProverCache()
        cached = cache.get(h)
        if cached is not None:
            return (True, cached, h, {})

    if benchmark_mode and prover_manager:
        results = {}
        success = False

        all_provers = prover_manager.get_all_provers()

        # In benchmark mode, we run all provers
        # We could parallelize this, but for now lets run sequentially or use small timeouts
        # The verify_task is already running in a thread from check_proof

        for p in all_provers:
            start_time = time.time()
            res = p.prove(all_axioms, ("goal", goal_repr), timeout=1.0) # Short timeout for benchmark? Or standard?
            end_time = time.time()
            duration = end_time - start_time
            results[p.name] = {"success": res, "time": duration}
            if res:
                success = True

        return (False, success, h, results)
    else:
        # Standard mode
        result = prover_instance.prove(all_axioms, ("goal", goal_repr), timeout=5.0)
        return (False, result, h, {})


class Reporter:
    """Abstract base class for reporting checking progress and results."""

    def log(self, message):
        pass

    def error(self, message):
        pass

    def step_verified(self, step_num, description, success, source, benchmark_info=None):
        pass


class StdoutReporter(Reporter):
    def log(self, message):
        print(message)

    def error(self, message):
        print(f"Error: {message}")

    def step_verified(self, step_num, description, success, source, benchmark_info=None):
        status = "Verified" if success else "Failed"
        print(f"Step {step_num}: {description} -> {status} {source}")
        if benchmark_info:
            print(f"  Benchmark Results:")
            best_prover = None
            min_time = float('inf')

            for name, data in benchmark_info.items():
                s = "Success" if data["success"] else "Fail"
                t = f"{data['time']:.4f}s"
                print(f"    {name}: {t} ({s})")

                if data["success"] and data["time"] < min_time:
                    min_time = data["time"]
                    best_prover = name

            if best_prover:
                print(f"  Suggestion: Use [prover {best_prover}]")


class Engine:
    def __init__(self, base_path=".", reporter=None, use_cache=True, benchmark=False):
        self.translator = Translator()
        self.axioms = []
        self.context = []
        self.counter = 0
        self.base_path = base_path
        self.processed_files = set()
        self.reporter = reporter if reporter else StdoutReporter()
        self.global_use_cache = use_cache
        self.current_cache_enabled = use_cache
        self.benchmark_mode = benchmark
        self.prover_manager = ProverManager()

        if use_cache:
            self.cache = ProverCache()
        else:
            self.cache = None

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
            with open(full_path, "r") as f:
                content = f.read()
            blocks = extract_forthel_blocks(content)
            all_stmts = []
            for block in blocks:
                try:
                    # block is a ForthelBlock, need block.content
                    ast = parse_cnl(block.content)
                    stmts = convert_ast(ast)
                    all_stmts.extend(stmts)
                except Exception:
                    # self.reporter.log(f"Error parsing included block: {e}")
                    pass

            # Recursively check/process with is_included=True
            self.check(all_stmts, is_included=True)
        except Exception as e:
            self.reporter.log(f"Error processing included file {full_path}: {e}")

    def process_statement(self, stmt: Statement, is_included=False):
        if isinstance(stmt, Directive):
            if stmt.name == "read" and stmt.args:
                path = stmt.args[0]
                self.process_file(path)
            elif stmt.name == "cache" and stmt.args:
                arg = stmt.args[0]
                if arg == "on":
                    self.current_cache_enabled = self.global_use_cache
                elif arg == "off":
                    self.current_cache_enabled = False
            elif stmt.name == "prover" and stmt.args:
                prover_name = stmt.args[0]
                if self.prover_manager.set_active_prover(prover_name):
                    self.reporter.log(f"Switched to prover: {prover_name}")
                else:
                    self.reporter.error(f"Unknown prover: {prover_name}")

        elif (
            isinstance(stmt, Definition)
            or isinstance(stmt, Axiom)
            or isinstance(stmt, Lemma)
        ):
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
                self.reporter.log(
                    f"Importing Theorem: {stmt.author if stmt.author else 'Unknown'}"
                )
                formulas = self.translator.translate_statement(stmt)
                # Assume last formula is the theorem claim
                if formulas:
                    f = formulas[-1]
                    name = f"thm_{self.counter}"
                    self.counter += 1
                    self.axioms.append((name, f))
                    self.reporter.log(f"Added axiom (Theorem): {f}")
            else:
                self.reporter.log(
                    f"Checking Theorem: {stmt.author if stmt.author else 'Unknown'}"
                )
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
                pass  # Skip proofs of included files
            else:
                self.reporter.log("Checking Proof (Parallel)...")
                self.check_proof(stmt)

    def check_proof(self, proof: Proof):
        proof_context = []
        tasks = []

        # Use current active prover
        current_prover = self.prover_manager.get_active_prover()

        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            for i, s in enumerate(proof.content):
                if isinstance(s, Sentence):
                    f = self.translator.translate_sentence(s)
                    if not f:
                        self.reporter.error(
                            f"Step {i + 1}: Could not translate '{s.text}'"
                        )
                        continue

                    text = s.text.strip()
                    is_assumption = False
                    if (
                        text.startswith("Assume")
                        or text.startswith("Let")
                        or text.startswith("Take")
                        or text.startswith("Define")
                        or text.startswith("Consider")
                    ):
                        is_assumption = True

                    if isinstance(f, Predicate) and f.name == "contrary":
                        if hasattr(self, "current_goal"):
                            neg_goal = Not(self.current_goal)
                            proof_context.append((f"step_{i}", neg_goal))
                            self.reporter.log(
                                f"Step {i + 1}: Assumed contrary: {neg_goal}"
                            )
                        continue

                    elif isinstance(f, Predicate) and f.name == "false":
                        self.reporter.log(f"Step {i + 1}: Contradiction.")
                        ctx_copy = list(proof_context)
                        future = executor.submit(
                            verify_task,
                            self.axioms,
                            self.context,
                            ctx_copy,
                            Predicate("false", []),
                            current_prover,
                            self.current_cache_enabled,
                            self.benchmark_mode,
                            self.prover_manager,
                        )
                        tasks.append((future, i + 1, "Contradiction"))

                    elif is_assumption:
                        self.reporter.log(f"Step {i + 1}: Assumption/Definition: {f}")
                        proof_context.append((f"step_{i}", f))
                    else:
                        self.reporter.log(f"Step {i + 1}: Verifying {f}")
                        ctx_copy = list(proof_context)
                        future = executor.submit(
                            verify_task,
                            self.axioms,
                            self.context,
                            ctx_copy,
                            f,
                            current_prover,
                            self.current_cache_enabled,
                            self.benchmark_mode,
                            self.prover_manager,
                        )
                        tasks.append((future, i + 1, f"Verification of {f}"))

                        proof_context.append((f"step_{i}", f))

            self.reporter.log("Waiting for verification tasks...")
            for future, step_num, desc in tasks:
                try:
                    res = future.result()
                    # verify_task returns (is_cached, success, h, results)
                    if len(res) == 4:
                        is_cached, success, h, benchmark_info = res
                    elif len(res) == 3: # Backward compat or cache hit?
                        is_cached, success, h = res
                        benchmark_info = {}

                    if not is_cached and self.current_cache_enabled and not self.benchmark_mode:
                        if self.cache:
                            self.cache.set(h, success)

                    source = "(Cached)" if is_cached else f"({current_prover.name})"
                    if self.benchmark_mode:
                        source = "(Benchmark)"

                    self.reporter.step_verified(step_num, desc, success, source, benchmark_info)

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.reporter.error(f"Step {step_num}: Task failed with error: {e}")
