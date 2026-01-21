import subprocess
import tempfile
import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Any
from naproche.prover.tptp import formulas_to_tptp_file
from naproche.logic.fol import Formula

class ProverResult:
    def __init__(self, success: bool, time_taken: float, prover_name: str, message: str = ""):
        self.success = success
        self.time_taken = time_taken
        self.prover_name = prover_name
        self.message = message

class Prover(ABC):
    @abstractmethod
    def run(self, tptp_path: str, timeout: int) -> ProverResult:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

class EProver(Prover):
    def run(self, tptp_path: str, timeout: int) -> ProverResult:
        eprover_path = os.environ.get("NAPROCHE_EPROVER")
        if not eprover_path:
            # Fallback attempts
            local_path = os.path.abspath("eprover/PROVER/eprover")
            if os.path.exists(local_path):
                eprover_path = local_path
            else:
                eprover_path = "eprover"

        cmd = [eprover_path, "--auto", "--silent", f"--cpu-limit={timeout}", tptp_path]

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            elapsed = time.time() - start_time

            if "SZS status Theorem" in result.stdout:
                return ProverResult(True, elapsed, self.name, "Theorem")
            elif "SZS status CounterSatisfiable" in result.stdout:
                return ProverResult(False, elapsed, self.name, "CounterSatisfiable")
            else:
                # E.g. Timeout or Unknown
                return ProverResult(False, elapsed, self.name, "Unknown/Failure")

        except FileNotFoundError:
            return ProverResult(False, 0, self.name, "Binary not found")
        except Exception as e:
            return ProverResult(False, 0, self.name, str(e))

    @property
    def name(self) -> str:
        return "eprover"

class VampireProver(Prover):
    def run(self, tptp_path: str, timeout: int) -> ProverResult:
        vampire_path = os.environ.get("NAPROCHE_VAMPIRE", "vampire")

        # vampire --mode casc -t <timeout> <file>
        cmd = [vampire_path, "--mode", "casc", "-t", str(timeout), tptp_path]

        start_time = time.time()
        try:
            # Vampire might print to stdout or stderr depending on version/mode
            result = subprocess.run(cmd, capture_output=True, text=True)
            elapsed = time.time() - start_time

            output = result.stdout + "\n" + result.stderr
            if "SZS status Theorem" in output:
                 return ProverResult(True, elapsed, self.name, "Theorem")
            elif "SZS status CounterSatisfiable" in output:
                 return ProverResult(False, elapsed, self.name, "CounterSatisfiable")
            else:
                 return ProverResult(False, elapsed, self.name, "Unknown/Failure")

        except FileNotFoundError:
            return ProverResult(False, 0, self.name, "Binary not found")
        except Exception as e:
            return ProverResult(False, 0, self.name, str(e))

    @property
    def name(self) -> str:
        return "vampire"


def run_provers(provers: List[Prover], axioms: List[Tuple[str, Formula]], conjecture: Tuple[str, Formula], timeout=5) -> Tuple[bool, List[ProverResult]]:
    tptp_content = formulas_to_tptp_file(axioms, conjecture)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.p', delete=False) as tmp:
        tmp.write(tptp_content)
        tmp_path = tmp.name

    results = []
    success = False

    try:
        # If multiple provers, we can run them in parallel or sequence.
        # For now, sequence is simpler, but if we want true "simultaneous" check returning first success,
        # we might want threads/processes.
        # However, the requirement is "benchmark ... on a proof by proof basis".
        # Benchmark implies running ALL of them to compare.

        for prover in provers:
            res = prover.run(tmp_path, timeout)
            results.append(res)
            if res.success:
                success = True

        return success, results

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# Backward compatibility if needed, but Engine will be updated to use run_provers
def run_prover(axioms: List[Tuple[str, Formula]], conjecture: Tuple[str, Formula], timeout=5) -> bool:
    success, _ = run_provers([EProver()], axioms, conjecture, timeout)
    return success
