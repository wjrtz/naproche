import os
import subprocess
import tempfile
import re
from typing import List, Tuple, Optional
from naproche.prover.base import Prover, ProverResult
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
    ) -> ProverResult:
        tptp_content = formulas_to_tptp_file(axioms, conjecture)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".p", delete=False) as tmp:
            tmp.write(tptp_content)
            tmp_path = tmp.name

        try:
            vampire_path = os.environ.get("NAPROCHE_VAMPIRE", "vampire")

            # Vampire commands might vary, but standard TPTP usage:
            # vampire --mode casc -t <timeout> <file>
            cmd = [vampire_path, "--mode", "casc", "--output_axiom_names", "on", "-t", str(int(timeout)), tmp_path]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
            except FileNotFoundError:
                return ProverResult(success=False, output="Vampire executable not found")

            if "SZS status Theorem" in result.stdout:
                used_axioms = self._extract_used_axioms(result.stdout)

                # Check for proof start marker
                if "SZS output start Proof" in result.stdout:
                     return ProverResult(success=True, used_axioms=used_axioms, output=result.stdout)
                else:
                    # Success but no proof object -> Unknown dependencies
                    return ProverResult(success=True, used_axioms=None, output=result.stdout)

            # Vampire might output unsat for Theorem in some modes, but SZS is standard
            return ProverResult(success=False, output=result.stdout)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _extract_used_axioms(self, output: str) -> List[str]:
        # Look for file('filename', name)
        # Broader regex to capture more complex names
        # file\('.*?',\s*([a-zA-Z0-9_\-\.]+)\)
        used = set()
        for line in output.splitlines():
            if "file(" in line:
                match = re.search(r"file\('.*?',\s*([a-zA-Z0-9_\-\.]+)\)", line)
                if match:
                    name = match.group(1)
                    if name != "unknown":
                        used.add(name)
        return list(used)
