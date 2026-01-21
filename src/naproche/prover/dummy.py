from typing import List, Tuple
from naproche.prover.base import Prover, ProverResult
from naproche.logic.fol import Formula

class DummyProver(Prover):
    @property
    def name(self) -> str:
        return "dummy"

    def prove(
        self,
        axioms: List[Tuple[str, Formula]],
        conjecture: Tuple[str, Formula],
        timeout: float
    ) -> ProverResult:
        # Dummy prover always succeeds and claims to use no axioms (or maybe all?)
        # For testing cache, let's say it uses all axioms.
        used = [name for name, _ in axioms]
        return ProverResult(success=True, used_axioms=used, output="Dummy Success")
