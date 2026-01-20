import hashlib
import json
import os
from naproche.logic.fol import Formula

CACHE_FILE = ".naproche_cache.json"

def get_formula_string(formula: Formula) -> str:
    return str(formula)

def compute_hash(axioms: list[tuple[str, Formula]], conjecture: tuple[str, Formula]) -> str:
    # We use the string representation of formulas to compute hash
    # Axioms order matters? Yes.
    # But usually set of axioms implies semantics.
    # To be safe, we sort axioms by name or content?
    # Actually, the prover input order might matter for performance but not validity.
    # Let's just use the list as is.

    data = []
    for name, f in axioms:
        data.append(f"{name}:{get_formula_string(f)}")

    name, f = conjecture
    data.append(f"CONJ:{name}:{get_formula_string(f)}")

    full_str = "|".join(data)
    return hashlib.sha256(full_str.encode('utf-8')).hexdigest()

class ProverCache:
    def __init__(self):
        self.cache = {}
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}

    def get(self, key: str):
        return self.cache.get(key)

    def set(self, key: str, value: bool):
        self.cache[key] = value
        # Basic persistence: save on every write or batch?
        # For now, save on write.
        with open(CACHE_FILE, 'w') as f:
            json.dump(self.cache, f)
