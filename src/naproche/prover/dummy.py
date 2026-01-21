from typing import List, Tuple
from naproche.prover.base import Prover
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
    ) -> bool:
        return True
