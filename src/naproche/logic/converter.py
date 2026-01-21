from typing import List, Dict, Any, Optional
from naproche.logic.models import (
    Statement,
    Sentence,
    Directive,
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
        return Directive(name=item["name"], args=item["args"])

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
