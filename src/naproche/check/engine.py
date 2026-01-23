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
from naproche.logic.fol import (
    Predicate,
    Not,
    Quantifier,
    Implies,
    Constant,
    Variable,
    substitute,
    Function,
    Equal,
    And,
    Or,
    Iff,
)
from naproche.check.cache import ProverCache, compute_hash_formula, get_formula_string
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
    timeout_override=None
):
    all_axioms = axioms_repr + context_repr + proof_context_repr

    # Precompute hashes
    # We need map from name to hash to identify used axioms
    axiom_hashes = {}
    for name, f in all_axioms:
        axiom_hashes[name] = compute_hash_formula(f)

    goal_name, goal_f = ("goal", goal_repr)
    goal_hash = compute_hash_formula(goal_f)

    # Context hash for failure caching (all axioms)
    # We use a simple concatenation of sorted hashes for stability
    sorted_hashes = sorted(axiom_hashes.values())
    context_hash_str = "|".join(sorted_hashes)

    # We also include goal in context hash for failure matching just in case
    full_context_hash = f"{context_hash_str}|GOAL:{goal_hash}"

    available_hashes_set = set(axiom_hashes.values())

    if use_cache and not benchmark_mode:
        cache = ProverCache()
        cached_result = cache.get_proof(goal_hash, available_hashes_set, full_context_hash)
        if cached_result is not None:
            return (True, cached_result, goal_hash, {})

    if benchmark_mode and prover_manager:
        results = {}
        success = False

        all_provers = prover_manager.get_all_provers()

        for p in all_provers:
            start_time = time.time()
            res = p.prove(all_axioms, (goal_name, goal_f), timeout=1.0)
            end_time = time.time()
            duration = end_time - start_time
            results[p.name] = {"success": res.success, "time": duration}
            if res.success:
                success = True

        return (False, success, goal_hash, results)
    else:
        # Standard mode
        t = timeout_override if timeout_override else 5.0
        result = prover_instance.prove(all_axioms, (goal_name, goal_f), timeout=t)

        if use_cache and not benchmark_mode:
            cache = ProverCache()
            if result.success:
                if result.used_axioms is None:
                     # Unknown dependencies -> conservative caching (like old behavior)
                     # We store all current available hashes as dependencies.
                     # This effectively means if ANY axiom changes, this proof is invalid.
                     used_hashes = list(available_hashes_set)
                else:
                    # Map names to hashes
                    used_hashes = []
                    for name in result.used_axioms:
                        if name in axiom_hashes:
                            used_hashes.append(axiom_hashes[name])

                cache.save_proof(goal_hash, used_hashes, True, full_context_hash)
            else:
                # Save failure with full context
                cache.save_proof(goal_hash, [], False, full_context_hash)

        return (False, result.success, goal_hash, {})


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
        self.timelimit = 5.0

        # Add built-in structural axioms for set theory basics used in examples
        self._add_builtin_axioms()

        if use_cache:
            self.cache = ProverCache()
        else:
            self.cache = None

    def _add_builtin_axioms(self):
        # ! [X, A, B] : (in(X, setminus(A, B)) <=> (in(X, A) & ~in(X, B)))
        x = Variable("X_set")
        a = Variable("A_set")
        b = Variable("B_set")

        # setminus
        f_setminus = Function("setminus", [a, b])
        lhs = Predicate("in", [x, f_setminus])
        rhs = And(Predicate("in", [x, a]), Not(Predicate("in", [x, b])))
        ax_setminus = Quantifier("forall", [x, a, b], Iff(lhs, rhs))
        self.axioms.append(("builtin_setminus", ax_setminus))

        # cap
        f_cap = Function("cap", [a, b])
        lhs_cap = Predicate("in", [x, f_cap])
        rhs_cap = And(Predicate("in", [x, a]), Predicate("in", [x, b]))
        ax_cap = Quantifier("forall", [x, a, b], Iff(lhs_cap, rhs_cap))
        self.axioms.append(("builtin_cap", ax_cap))

        # cup
        f_cup = Function("cup", [a, b])
        lhs_cup = Predicate("in", [x, f_cup])
        rhs_cup = Or(Predicate("in", [x, a]), Predicate("in", [x, b]))
        ax_cup = Quantifier("forall", [x, a, b], Iff(lhs_cup, rhs_cup))
        self.axioms.append(("builtin_cup", ax_cup))

        # empty_set
        c_empty = Constant("empty_set")
        ax_empty = Quantifier("forall", [x], Not(Predicate("in", [x, c_empty])))
        self.axioms.append(("builtin_empty", ax_empty))

        # singleton(Y) -> {Y}
        y = Variable("Y_sing")
        f_sing = Function("singleton", [y])
        lhs_sing = Predicate("in", [x, f_sing])
        rhs_sing = Equal(x, y)
        ax_sing = Quantifier("forall", [x, y], Iff(lhs_sing, rhs_sing))
        self.axioms.append(("builtin_singleton", ax_sing))

        # set_enum(Y, Z) -> {Y, Z} (pair set)
        z = Variable("Z_enum")
        f_enum = Function("set_enum", [y, z])
        lhs_enum = Predicate("in", [x, f_enum])
        rhs_enum = Or(Equal(x, y), Equal(x, z))
        ax_enum = Quantifier("forall", [x, y, z], Iff(lhs_enum, rhs_enum))
        self.axioms.append(("builtin_set_enum", ax_enum))

        # pair equality: (a,b) = (c,d) => a=c & b=d
        # Handled by provers usually if tuples are supported, but explicitly:
        # We model pair as Function("pair", [a,b]).
        # Need: ! [A,B,C,D] : (pair(A,B) = pair(C,D) => (A=C & B=D))
        # Note: Converse (A=C & B=D => pair(A,B)=pair(C,D)) is true by equality logic.
        va, vb, vc, vd = Variable("Va"), Variable("Vb"), Variable("Vc"), Variable("Vd")
        pair1 = Function("pair", [va, vb])
        pair2 = Function("pair", [vc, vd])
        conc = And(Equal(va, vc), Equal(vb, vd))
        ax_pair = Quantifier("forall", [va, vb, vc, vd], Implies(Equal(pair1, pair2), conc))
        self.axioms.append(("builtin_pair_eq", ax_pair))


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
            elif stmt.name == "timelimit" and stmt.args:
                try:
                    self.timelimit = float(stmt.args[0])
                    self.reporter.log(f"Timelimit set to {self.timelimit}")
                except:
                    pass
            elif stmt.name == "synonym" and stmt.args:
                arg = stmt.args[0]
                # Format: word/-s or word/plural
                if "/" in arg:
                    parts = arg.split("/")
                    base = parts[0]
                    suffix = parts[1]
                    if suffix.startswith("-"):
                        plural = base + suffix[1:]
                    else:
                        plural = suffix
                    self.translator.add_synonym(base, plural)
                    self.reporter.log(f"Added synonym: {plural} -> {base}")

        elif (
            isinstance(stmt, Definition)
            or isinstance(stmt, Axiom)
            or isinstance(stmt, Lemma)
        ):
            # Treat Lemmas as Axioms if included or generally useful results
            formulas = self.translator.translate_statement(stmt)
            for f in formulas:
                # Skip stand_for predicates in axiom list
                if isinstance(f, Predicate) and f.name == "stand_for":
                    pass
                else:
                    name = f"ax_{self.counter}"
                    self.counter += 1
                    self.axioms.append((name, f))
                    self.reporter.log(f"Added axiom: {f}")

            # Check for macros (keep log, but don't add to axioms if we skip above)
            for f in formulas:
                if isinstance(f, Predicate) and f.name == "stand_for":
                    if len(f.args) == 2:
                        phrase_term = f.args[0]
                        repl_term = f.args[1]
                        if isinstance(phrase_term, Constant):
                            phrase = phrase_term.name
                            self.translator.add_macro(phrase, repl_term)
                            self.reporter.log(f"Added macro: '{phrase}' -> {repl_term}")

        elif isinstance(stmt, Sentence):
            # Handle top-level sentences (like 'Let ... stand for ...') as Axioms/Assumptions
            formulas = self.translator.translate_statement(stmt)
            for f in formulas:
                # Skip stand_for predicates
                if isinstance(f, Predicate) and f.name == "stand_for":
                    pass
                else:
                    name = f"ax_{self.counter}"
                    self.counter += 1
                    self.axioms.append((name, f))
                    self.reporter.log(f"Added axiom (Sentence): {f}")

            # Check for macros
            for f in formulas:
                if isinstance(f, Predicate) and f.name == "stand_for":
                    if len(f.args) == 2:
                        phrase_term = f.args[0]
                        repl_term = f.args[1]
                        if isinstance(phrase_term, Constant):
                            phrase = phrase_term.name
                            self.translator.add_macro(phrase, repl_term)
                            self.reporter.log(f"Added macro: '{phrase}' -> {repl_term}")

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
                self.reporter.log(f"Checking Proof (Parallel)... with {len(stmt.content)} steps")
                self.check_proof(stmt)

    def check_proof(self, proof: Proof):
        proof_context = []
        scope_stack = []

        # Decompose the current goal to setup the proof context
        current_goal = getattr(self, "current_goal", None)
        if current_goal:
            self.reporter.log(f"Decomposing goal: {current_goal}")
            while True:
                if isinstance(current_goal, Quantifier) and current_goal.type == "forall":
                    # Strip forall: substitute variables with constants
                    # Since we want to prove it for arbitrary X, we pick a constant 'x'.
                    # We rely on the fact that translator maps Proof variables to lowercase constants.
                    # e.g. Variable("X") -> Constant("x")

                    term = current_goal.body
                    for v in current_goal.vars:
                        # Assuming Variable names are uppercase, we lowercase them
                        c = Constant(v.name.lower())
                        term = substitute(term, v.name, c)
                    current_goal = term

                    # We don't add constant declaration to context explicitly in FOL,
                    # but logically it exists.
                elif isinstance(current_goal, Implies):
                    # Strip implication: assume LHS
                    proof_context.append((f"goal_assump_{self.counter}", current_goal.left))
                    self.counter += 1
                    self.reporter.log(f"  Assumed from goal: {current_goal.left}")
                    current_goal = current_goal.right
                else:
                    break
            self.reporter.log(f"  New goal focus: {current_goal}")
        else:
            self.reporter.log("Warning: No current goal to prove (Proof block without Theorem?).")

        tasks = []

        # Use current active prover
        current_prover = self.prover_manager.get_active_prover()

        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            for i, stmt in enumerate(proof.content):
                # Handle Directive inside proof (e.g. timelimit)
                if isinstance(stmt, Directive):
                    if stmt.name == "timelimit":
                        try:
                            self.timelimit = float(stmt.args[0])
                            self.reporter.log(f"Timelimit set to {self.timelimit}")
                        except: pass
                    continue

                if not isinstance(stmt, Sentence):
                    continue

                s = stmt
                f = self.translator.translate_sentence(s)

                text = s.text.strip()
                atoms = getattr(s, "atoms", [])

                # Check for "Case" prefix (handled by translator returning a formula, but we need scoping)
                # If translator returns assumption for Case, we should push scope.
                # If translator strips "Case", we check text.
                is_case = atoms and atoms[0] == "Case"

                if atoms and (atoms[0] == "End" or (len(atoms) > 1 and atoms[0] == "Case" and atoms[1] == "End")):
                    # Pop scope
                    if scope_stack:
                         proof_context = scope_stack.pop()
                         self.reporter.log(f"Step {i+1}: End of case/scope.")
                    continue

                if not f:
                    # Check if it's a structural end marker we can ignore silently
                    if "End" in atoms or "qed" in atoms or "Proof" in atoms:
                        continue

                    self.reporter.error(
                        f"Step {i + 1}: Could not translate '{s.text}'"
                    )
                    continue

                if is_case:
                     # Start new scope
                     # Save current context to stack
                     scope_stack.append(list(proof_context))
                     self.reporter.log(f"Step {i+1}: Case assumption: {f}")
                     proof_context.append((f"step_{i}", f))
                     continue

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
                    # If we decomposed the goal, we should use the *current* goal focus
                    # or the original goal? "contrary" usually means negation of current goal.
                    if current_goal:
                        goal_to_negate = current_goal
                        neg_goal = Not(goal_to_negate)
                        proof_context.append((f"step_{i}", neg_goal))
                        self.reporter.log(
                            f"Step {i + 1}: Assumed contrary: {neg_goal}"
                        )
                    else:
                        self.reporter.error("Cannot assume contrary: No current goal.")
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
                        self.timelimit
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
                        self.timelimit
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

                    # Note: We don't need to save to cache here anymore, verify_task does it

                    source = "(Cached)" if is_cached else f"({current_prover.name})"
                    if self.benchmark_mode:
                        source = "(Benchmark)"

                    self.reporter.step_verified(step_num, desc, success, source, benchmark_info)

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.reporter.error(f"Step {step_num}: Task failed with error: {e}")
