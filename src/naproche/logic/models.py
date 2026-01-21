from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Statement:
    pass


@dataclass
class Sentence(Statement):
    text: str
    atoms: List[str]  # Simplified for now


@dataclass
class Block(Statement):
    name: str
    content: List[Statement]


@dataclass
class Directive(Statement):
    name: str
    args: List[str]


@dataclass
class Theorem(Block):
    author: Optional[str] = None


@dataclass
class Definition(Block):
    pass


@dataclass
class Axiom(Block):
    pass


@dataclass
class Lemma(Block):
    pass


@dataclass
class Proof(Block):
    pass
