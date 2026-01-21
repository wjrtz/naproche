import subprocess
import tempfile
import os
from typing import List, Tuple
from naproche.prover.tptp import formulas_to_tptp_file
from naproche.logic.fol import Formula


def run_prover(
    axioms: List[Tuple[str, Formula]], conjecture: Tuple[str, Formula], timeout=5
) -> bool:
    tptp_content = formulas_to_tptp_file(axioms, conjecture)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".p", delete=False) as tmp:
        tmp.write(tptp_content)
        tmp_path = tmp.name

    try:
        eprover_path = os.environ.get("NAPROCHE_EPROVER")
        if not eprover_path:
            local_path = os.path.abspath("eprover/PROVER/eprover")
            if os.path.exists(local_path):
                eprover_path = local_path
            else:
                eprover_path = "eprover"

        cmd = [eprover_path, "--auto", "--silent", f"--cpu-limit={timeout}", tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Check for SZS status Theorem (ignore leading char # or %)
        if "SZS status Theorem" in result.stdout:
            return True
        elif "SZS status CounterSatisfiable" in result.stdout:
            return False

        return False

    except FileNotFoundError:
        print(f"eprover not found at {eprover_path}")
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
