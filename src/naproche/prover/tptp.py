from typing import List, Optional
from naproche.logic.fol import Formula


def to_tptp(formula: Formula, name: str, role: str) -> str:
    return f"fof({name}, {role}, {formula})."


def formulas_to_tptp_file(
    axioms: List[tuple[str, Formula]], conjecture: Optional[tuple[str, Formula]]
) -> str:
    lines = []
    for name, form in axioms:
        lines.append(to_tptp(form, name, "axiom"))
    if conjecture:
        name, form = conjecture
        lines.append(to_tptp(form, name, "conjecture"))
    return "\n".join(lines)
