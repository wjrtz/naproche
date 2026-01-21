import os
import subprocess
import tempfile
from typing import List, Tuple
from naproche.prover.base import Prover
from naproche.prover.tptp import formulas_to_tptp_file
from naproche.logic.fol import Formula

class VampireProver(Prover):
    @property
    def name(self) -> str:
        return "vampire"

    def prove(
        self,
        axioms: List[Tuple[str, Formula]],
        conjecture: Tuple[str, Formula],
        timeout: float
    ) -> bool:
        tptp_content = formulas_to_tptp_file(axioms, conjecture)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".p", delete=False) as tmp:
            tmp.write(tptp_content)
            tmp_path = tmp.name

        try:
            vampire_path = os.environ.get("NAPROCHE_VAMPIRE", "vampire")

            # Vampire commands might vary, but standard TPTP usage:
            # vampire --mode casc -t <timeout> <file>
            cmd = [vampire_path, "--mode", "casc", "-t", str(int(timeout)), tmp_path]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
            except FileNotFoundError:
                return False

            if "SZS status Theorem" in result.stdout:
                return True
            # Vampire might output unsat for Theorem in some modes, but SZS is standard
            return False

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
