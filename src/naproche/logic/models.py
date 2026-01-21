from dataclasses import dataclass, field
from typing import List, Optional, Union

@dataclass
class Statement:
    pass

@dataclass
class Sentence(Statement):
    text: str
    atoms: List[str] # Simplified for now

@dataclass
class Block(Statement):
    name: str
    content: List[Statement]

@dataclass
class Directive(Statement):
    path: str

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
