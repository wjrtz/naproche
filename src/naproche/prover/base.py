from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from naproche.logic.fol import Formula

class Prover(ABC):
    @abstractmethod
    def prove(
        self,
        axioms: List[Tuple[str, Formula]],
        conjecture: Tuple[str, Formula],
        timeout: float
    ) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
