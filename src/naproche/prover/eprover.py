import os
import subprocess
import tempfile
import re
from typing import List, Tuple, Optional
from naproche.prover.base import Prover, ProverResult
from naproche.prover.tptp import formulas_to_tptp_file
from naproche.logic.fol import Formula

class EProver(Prover):
    @property
    def name(self) -> str:
        return "eprover"

    def prove(
        self,
        axioms: List[Tuple[str, Formula]],
        conjecture: Tuple[str, Formula],
        timeout: float
    ) -> ProverResult:
        tptp_content = formulas_to_tptp_file(axioms, conjecture)

        # Write to debug log file to avoid stdout buffering issues
        with open("debug_tptp.log", "a") as log:
            log.write(f"\n--- EProver TPTP Input ({timeout}s) ---\n")
            log.write(tptp_content)
            log.write("\n--------------------------\n")

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

            # Eprover needs --proof-object or similar to output proof
            cmd = [eprover_path, "--auto", "--silent", f"--cpu-limit={timeout}", "--proof-object", tmp_path]
            # Use run but handle potential FileNotFoundError for executable
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                with open("debug_tptp.log", "a") as log:
                    log.write("--- EProver Output ---\n")
                    log.write(result.stdout)
                    log.write(result.stderr)
                    log.write("\n----------------------\n")
            except FileNotFoundError:
                return ProverResult(success=False, output="EProver executable not found")

            if "SZS status Theorem" in result.stdout:
                used_axioms = self._extract_used_axioms(result.stdout)
                # Check if proof object was actually generated
                # Eprover usually outputs proof if requested and successful
                if "SZS output start Proof" in result.stdout or "# Proof found!" in result.stdout:
                    return ProverResult(success=True, used_axioms=used_axioms, output=result.stdout)
                else:
                    return ProverResult(success=True, used_axioms=None, output=result.stdout)

            elif "SZS status CounterSatisfiable" in result.stdout:
                return ProverResult(success=False, output=result.stdout)

            return ProverResult(success=False, output=result.stdout)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _extract_used_axioms(self, output: str) -> List[str]:
        # Eprover output format for file usually: file('...', name)
        # Broader regex
        used = set()
        for line in output.splitlines():
            if "file(" in line:
                match = re.search(r"file\('.*?',\s*([a-zA-Z0-9_\-\.]+)\)", line)
                if match:
                    name = match.group(1)
                    if name != "unknown":
                        used.add(name)
        return list(used)
