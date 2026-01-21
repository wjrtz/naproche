from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from naproche.logic.fol import Formula

@dataclass
class ProverResult:
    success: bool
    # used_axioms is None if dependencies are unknown/unsupported.
    # Empty list means no axioms used (tautology).
    used_axioms: Optional[List[str]] = field(default=None)
    output: str = ""

class Prover(ABC):
    @abstractmethod
    def prove(
        self,
        axioms: List[Tuple[str, Formula]],
        conjecture: Tuple[str, Formula],
        timeout: float
    ) -> ProverResult:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
