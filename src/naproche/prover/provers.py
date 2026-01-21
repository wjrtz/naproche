from abc import ABC, abstractmethod
from typing import List, Tuple
from naproche.logic.fol import Formula
from naproche.prover.tptp import formulas_to_tptp_file
import tempfile
import os
import subprocess
import time

class Prover(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, axioms: List[Tuple[str, Formula]], conjecture: Tuple[str, Formula], timeout=5) -> Tuple[bool, float, str]:
        """
        Runs the prover.
        Returns a tuple: (success, time_taken, output/info)
        """
        pass

class DummyProver(Prover):
    def __init__(self):
        super().__init__("dummy")

    def run(self, axioms: List[Tuple[str, Formula]], conjecture: Tuple[str, Formula], timeout=5) -> Tuple[bool, float, str]:
        return True, 0.0, "Dummy prover always succeeds"

class TptpProver(Prover):
    def __init__(self, name: str, binary_path: str, args: List[str]):
        super().__init__(name)
        self.binary_path = binary_path
        self.args = args

    def run(self, axioms: List[Tuple[str, Formula]], conjecture: Tuple[str, Formula], timeout=5) -> Tuple[bool, float, str]:
        tptp_content = formulas_to_tptp_file(axioms, conjecture)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".p", delete=False) as tmp:
            tmp.write(tptp_content)
            tmp_path = tmp.name

        start_time = time.time()
        try:
            cmd = [self.binary_path] + self.args + [tmp_path]
            # Replace placeholder for cpu-limit if it exists
            cmd = [arg.replace("{timeout}", str(timeout)) for arg in cmd]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+2) # slight buffer

            elapsed = time.time() - start_time

            success = self.check_success(result.stdout)
            return success, elapsed, result.stdout

        except subprocess.TimeoutExpired:
            return False, time.time() - start_time, "Timeout"
        except FileNotFoundError:
            return False, 0.0, f"Prover binary not found at {self.binary_path}"
        except Exception as e:
            return False, time.time() - start_time, f"Error: {e}"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @abstractmethod
    def check_success(self, output: str) -> bool:
        pass

class EProver(TptpProver):
    def __init__(self):
        eprover_path = os.environ.get("NAPROCHE_EPROVER")
        if not eprover_path:
            local_path = os.path.abspath("eprover/PROVER/eprover")
            if os.path.exists(local_path):
                eprover_path = local_path
            else:
                eprover_path = "eprover"

        super().__init__("eprover", eprover_path, ["--auto", "--silent", "--cpu-limit={timeout}"])

    def check_success(self, output: str) -> bool:
        if "SZS status Theorem" in output:
            return True
        return False

class VampireProver(TptpProver):
    def __init__(self):
        vampire_path = os.environ.get("NAPROCHE_VAMPIRE")
        if not vampire_path:
            # Assuming vampire might be in a similar location or just 'vampire'
             local_path = os.path.abspath("vampire")
             if os.path.exists(local_path):
                 vampire_path = local_path
             else:
                 vampire_path = "vampire"

        super().__init__("vampire", vampire_path, ["--mode", "casc", "-t", "{timeout}"])

    def check_success(self, output: str) -> bool:
        if "SZS status Theorem" in output:
            return True
        return False
