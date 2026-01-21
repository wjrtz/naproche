from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Term:
    pass


@dataclass(frozen=True)
class Variable(Term):
    name: str

    def __str__(self):
        return self.name.upper()


@dataclass(frozen=True)
class Constant(Term):
    name: str

    def __str__(self):
        return self.name.lower()


@dataclass(frozen=True)
class Function(Term):
    name: str
    args: List[Term]

    def __str__(self):
        args_str = ",".join(str(a) for a in self.args)
        return f"{self.name}({args_str})"


@dataclass(frozen=True)
class Formula:
    pass


@dataclass(frozen=True)
class Predicate(Formula):
    name: str
    args: List[Term]

    def __str__(self):
        args_str = ",".join(str(a) for a in self.args)
        return f"{self.name}({args_str})"


@dataclass(frozen=True)
class Equal(Formula):
    left: Term
    right: Term

    def __str__(self):
        return f"{self.left} = {self.right}"


@dataclass(frozen=True)
class Not(Formula):
    formula: Formula

    def __str__(self):
        return f"~ ({self.formula})"


@dataclass(frozen=True)
class And(Formula):
    left: Formula
    right: Formula

    def __str__(self):
        return f"({self.left} & {self.right})"


@dataclass(frozen=True)
class Or(Formula):
    left: Formula
    right: Formula

    def __str__(self):
        return f"({self.left} | {self.right})"


@dataclass(frozen=True)
class Implies(Formula):
    left: Formula
    right: Formula

    def __str__(self):
        return f"({self.left} => {self.right})"


@dataclass(frozen=True)
class Iff(Formula):
    left: Formula
    right: Formula

    def __str__(self):
        return f"({self.left} <=> {self.right})"


@dataclass(frozen=True)
class Quantifier(Formula):
    type: str  # "forall" or "exists"
    vars: List[Variable]
    body: Formula

    def __str__(self):
        vars_str = ",".join(str(v) for v in self.vars)
        q = "!" if self.type == "forall" else "?"
        return f"({q} [{vars_str}] : {self.body})"
