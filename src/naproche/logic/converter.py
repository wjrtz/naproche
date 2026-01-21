from typing import List, Dict, Any, Optional
from naproche.logic.models import (
    Statement,
    Sentence,
    Directive,
    ProverDirective,
    Theorem,
    Definition,
    Axiom,
    Lemma,
    Proof,
    Block,
)


def convert_ast(ast: List[Dict[str, Any]]) -> List[Statement]:
    statements = []
    for item in ast:
        stmt = convert_item(item)
        if stmt:
            statements.append(stmt)
    return statements


def convert_item(item: Dict[str, Any]) -> Optional[Statement]:
    if not isinstance(item, dict):
        return None

    type_ = item.get("type")

    if type_ == "directive":
        name = item.get("name")
        args = item.get("args", [])

        if name == "read":
            # Keep as Directive for Engine processing
            return Directive(name=name, args=args)
        elif name == "prover":
            prover_name = args[0] if args else "eprover"
            return ProverDirective(prover_name=prover_name)
        else:
             # Generic directive
             return Directive(name=name, args=args)

    elif type_ == "sentence":
        # Reconstruct text from atoms
        atoms = item["atoms"]
        text = " ".join([str(a) for a in atoms])
        return Sentence(text=text, atoms=atoms)

    elif type_ == "environment":
        name = item["name"]
        arg = item.get("arg")
        content_data = item["content"]
        content = convert_ast(content_data)

        if name == "theorem*":  # Handling starred versions as same for now
            return Theorem(name=name, content=content, author=arg)
        elif name == "definition*":
            return Definition(name=name, content=content)
        elif name == "axiom*":
            return Axiom(name=name, content=content)
        elif name == "lemma*":
            return Lemma(name=name, content=content)
        elif name == "proof":
            return Proof(name=name, content=content)
        elif name == "definition":
            return Definition(name=name, content=content)
        elif name == "theorem":
            return Theorem(name=name, content=content, author=arg)
        elif name == "lemma":
            return Lemma(name=name, content=content)
        elif name == "axiom":
            return Axiom(name=name, content=content)
        else:
            # Generic block
            return Block(name=name, content=content)

    return None
