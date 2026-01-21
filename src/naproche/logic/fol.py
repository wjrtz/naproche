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


def substitute_term(term: Term, var_name: str, replacement: Term) -> Term:
    if isinstance(term, Variable):
        if term.name == var_name:
            return replacement
        return term
    elif isinstance(term, Function):
        new_args = [substitute_term(a, var_name, replacement) for a in term.args]
        return Function(term.name, new_args)
    elif isinstance(term, Constant):
        return term
    return term


def substitute(formula: Formula, var_name: str, replacement: Term) -> Formula:
    if isinstance(formula, Predicate):
        new_args = [substitute_term(a, var_name, replacement) for a in formula.args]
        return Predicate(formula.name, new_args)
    elif isinstance(formula, Equal):
        return Equal(
            substitute_term(formula.left, var_name, replacement),
            substitute_term(formula.right, var_name, replacement),
        )
    elif isinstance(formula, Not):
        return Not(substitute(formula.formula, var_name, replacement))
    elif isinstance(formula, And):
        return And(
            substitute(formula.left, var_name, replacement),
            substitute(formula.right, var_name, replacement),
        )
    elif isinstance(formula, Or):
        return Or(
            substitute(formula.left, var_name, replacement),
            substitute(formula.right, var_name, replacement),
        )
    elif isinstance(formula, Implies):
        return Implies(
            substitute(formula.left, var_name, replacement),
            substitute(formula.right, var_name, replacement),
        )
    elif isinstance(formula, Iff):
        return Iff(
            substitute(formula.left, var_name, replacement),
            substitute(formula.right, var_name, replacement),
        )
    elif isinstance(formula, Quantifier):
        if any(v.name == var_name for v in formula.vars):
            return formula
        return Quantifier(
            formula.type,
            formula.vars,
            substitute(formula.body, var_name, replacement),
        )
    return formula
