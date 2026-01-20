import subprocess
import tempfile
import os
from typing import List, Optional, Tuple
from naproche.prover.tptp import formulas_to_tptp_file
from naproche.logic.fol import Formula

def run_prover(axioms: List[Tuple[str, Formula]], conjecture: Tuple[str, Formula], timeout=5) -> bool:
    tptp_content = formulas_to_tptp_file(axioms, conjecture)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.p', delete=False) as tmp:
        tmp.write(tptp_content)
        tmp_path = tmp.name

    try:
        # eprover --auto --silent --cpu-limit=...
        cmd = ["eprover", "--auto", f"--cpu-limit={timeout}", tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # DEBUG output
        if result.returncode != 0:
             print(f"Prover failed with code {result.returncode}")
             print(f"Prover stderr: {result.stderr}")

        # print(f"Prover output:\n{result.stdout}")

        if "# SZS status Theorem" in result.stdout:
            return True
        elif "# SZS status CounterSatisfiable" in result.stdout:
            return False
        elif "# SZS status Unsatisfiable" in result.stdout:
             pass

        return False

    except FileNotFoundError:
        print("eprover not found.")
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
