from typing import Dict, Optional, List
from naproche.prover import EProver, VampireProver, DummyProver, Prover

class ProverManager:
    def __init__(self):
        self._provers: Dict[str, Prover] = {
            "eprover": EProver(),
            "vampire": VampireProver(),
            "dummy": DummyProver(),
        }
        self.active_prover_name = "vampire"

    def get_prover(self, name: str) -> Optional[Prover]:
        return self._provers.get(name)

    def set_active_prover(self, name: str) -> bool:
        if name in self._provers:
            self.active_prover_name = name
            return True
        return False

    def get_active_prover(self) -> Prover:
        return self._provers[self.active_prover_name]

    def get_all_provers(self) -> List[Prover]:
        return list(self._provers.values())
