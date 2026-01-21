from typing import List, Tuple, Dict, Optional
from naproche.logic.fol import Formula
from naproche.prover.provers import Prover, EProver, VampireProver, DummyProver

# Global registry of available provers
AVAILABLE_PROVERS: Dict[str, Prover] = {
    "eprover": EProver(),
    "vampire": VampireProver(),
    "dummy": DummyProver(),
}

def get_prover(name: str) -> Optional[Prover]:
    return AVAILABLE_PROVERS.get(name)

def run_prover(
    axioms: List[Tuple[str, Formula]],
    conjecture: Tuple[str, Formula],
    prover_names: List[str] = ["eprover"],
    timeout=5,
    benchmark_mode=False
) -> Dict:
    """
    Runs one or more provers.

    If benchmark_mode is False, it returns True as soon as one prover succeeds.
    Returns: { 'success': bool, 'results': { prover_name: (success, time, output) } }
    """
    results = {}
    success_overall = False

    # In non-benchmark mode, we could potentially run them in parallel and return early.
    # For simplicity, let's run them sequentially for now unless benchmark is true,
    # or implement a simple loop.

    # If benchmark_mode is True, we run all specified provers.
    # If benchmark_mode is False, we stop at first success.

    for name in prover_names:
        prover = get_prover(name)
        if not prover:
            results[name] = (False, 0.0, "Prover not found")
            continue

        success, elapsed, output = prover.run(axioms, conjecture, timeout)
        results[name] = (success, elapsed, output)

        if success:
            success_overall = True
            if not benchmark_mode:
                break

    return {
        'success': success_overall,
        'results': results
    }
