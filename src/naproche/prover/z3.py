import os
import subprocess
import tempfile
import sys
from typing import List, Tuple
from naproche.prover.base import Prover
from naproche.prover.tptp import formulas_to_tptp_file
from naproche.logic.fol import Formula

class Z3Prover(Prover):
    @property
    def name(self) -> str:
        return "z3"

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
            # Try to find Z3 in path or assume it's "z3"
            z3_path = os.environ.get("NAPROCHE_Z3", "z3")

            # If z3 is not in path, try to find it in the python environment bin
            if z3_path == "z3":
                # Check known location if necessary, or rely on PATH
                # In this environment, we found it at sys.prefix/bin/z3 usually
                potential_path = os.path.join(sys.prefix, "bin", "z3")
                if os.path.exists(potential_path):
                    z3_path = potential_path

            # Z3 accepts TPTP via file input directly if it detects it or with -tptp
            # Usually z3 -tptp <file> works
            cmd = [z3_path, "-tptp", f"-T:{int(timeout)}", tmp_path]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
            except FileNotFoundError:
                return False

            # Z3 TPTP output usually contains "szs status Theorem" or "unsat"
            # It might depend on version.
            stdout_lower = result.stdout.lower()
            if "szs status theorem" in stdout_lower:
                return True
            if "unsat" in stdout_lower and "szs" not in stdout_lower:
                # Sometimes raw Z3 output is just 'unsat' which means theorem is valid (negation is unsat)
                # But we should be careful. Using -tptp usually gives SZS.
                pass

            return False

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
