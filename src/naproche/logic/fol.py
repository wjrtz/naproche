from dataclasses import dataclass
from typing import List, Union

@dataclass
class Term:
    pass

@dataclass
class Variable(Term):
    name: str
    def __str__(self):
        return self.name.upper()

@dataclass
class Constant(Term):
    name: str
    def __str__(self):
        return self.name.lower()

@dataclass
class Function(Term):
    name: str
    args: List[Term]
    def __str__(self):
        args_str = ",".join(str(a) for a in self.args)
        return f"{self.name}({args_str})"

@dataclass
class Formula:
    pass

@dataclass
class Predicate(Formula):
    name: str
    args: List[Term]
    def __str__(self):
        args_str = ",".join(str(a) for a in self.args)
        return f"{self.name}({args_str})"

@dataclass
class Equal(Formula):
    left: Term
    right: Term
    def __str__(self):
        return f"{self.left} = {self.right}"

@dataclass
class Not(Formula):
    formula: Formula
    def __str__(self):
        return f"~ ({self.formula})"

@dataclass
class And(Formula):
    left: Formula
    right: Formula
    def __str__(self):
        return f"({self.left} & {self.right})"

@dataclass
class Or(Formula):
    left: Formula
    right: Formula
    def __str__(self):
        return f"({self.left} | {self.right})"

@dataclass
class Implies(Formula):
    left: Formula
    right: Formula
    def __str__(self):
        return f"({self.left} => {self.right})"

@dataclass
class Iff(Formula):
    left: Formula
    right: Formula
    def __str__(self):
        return f"({self.left} <=> {self.right})"

@dataclass
class Quantifier(Formula):
    type: str # "forall" or "exists"
    vars: List[Variable]
    body: Formula
    def __str__(self):
        vars_str = ",".join(str(v) for v in self.vars)
        q = "!" if self.type == "forall" else "?"
        return f"({q} [{vars_str}] : {self.body})"
