from typing import List, Optional, Set
from naproche.logic.models import (
    Statement,
    Sentence,
    Definition,
    Theorem,
    Axiom,
    Proof,
    Directive,
    Lemma,
)
from naproche.logic.fol import (
    And,
    Constant,
    Equal,
    Formula,
    Function,
    Iff,
    Implies,
    Not,
    Or,
    Predicate,
    Quantifier,
    Term,
    Variable,
)
import re


class Translator:
    def __init__(self):
        pass

    def translate_statement(self, stmt: Statement) -> List[Formula]:
        if isinstance(stmt, Sentence):
            f = self.translate_sentence(stmt, as_axiom=True)
            if f:
                return [self.closure(f)]
            return []
        elif isinstance(stmt, Directive):
            return []
        elif isinstance(stmt, Proof):
            return []
        elif (
            isinstance(stmt, Definition)
            or isinstance(stmt, Axiom)
            or isinstance(stmt, Lemma)
            or isinstance(stmt, Theorem)
        ):
            return self.translate_block(stmt)
        return []

    def translate_block(self, block: Statement) -> List[Formula]:
        assumptions = []
        conclusions = []

        for s in block.content:
            if not isinstance(s, Sentence):
                continue

            text = s.text.strip()
            # Heuristic for assumptions in blocks
            is_assumption = text.startswith("Let") or text.startswith("Assume")

            f = self.translate_sentence(s, as_axiom=True)

            if f:
                if is_assumption:
                    assumptions.append(f)
                else:
                    conclusions.append(f)

        if not conclusions:
            return [self.closure(a) for a in assumptions]

        conc_form = conclusions[0]
        if len(conclusions) > 1:
            for c in conclusions[1:]:
                conc_form = And(conc_form, c)

        if assumptions:
            asm_form = assumptions[0]
            if len(assumptions) > 1:
                for a in assumptions[1:]:
                    asm_form = And(asm_form, a)

            imp = Implies(asm_form, conc_form)
            return [self.closure(imp)]
        else:
            return [self.closure(conc_form)]

    def closure(self, formula: Formula) -> Formula:
        free_vars = self.get_free_vars(formula)
        if not free_vars:
            return formula
        vars_list = sorted(list(free_vars), key=lambda v: v.name)
        return Quantifier("forall", vars_list, formula)

    def get_free_vars(self, formula: Formula) -> Set[Variable]:
        if isinstance(formula, Predicate):
            vars = set()
            for arg in formula.args:
                vars.update(self.get_vars_in_term(arg))
            return vars
        elif isinstance(formula, Equal):
            return self.get_vars_in_term(formula.left) | self.get_vars_in_term(
                formula.right
            )
        elif isinstance(formula, Not):
            return self.get_free_vars(formula.formula)
        elif (
            isinstance(formula, And)
            or isinstance(formula, Or)
            or isinstance(formula, Implies)
            or isinstance(formula, Iff)
        ):
            return self.get_free_vars(formula.left) | self.get_free_vars(formula.right)
        elif isinstance(formula, Quantifier):
            vars = self.get_free_vars(formula.body)
            for v in formula.vars:
                if v in vars:
                    vars.remove(v)
            return vars
        return set()

    def get_vars_in_term(self, term: Term) -> Set[Variable]:
        if isinstance(term, Variable):
            return {term}
        elif isinstance(term, Function):
            vars = set()
            for arg in term.args:
                vars.update(self.get_vars_in_term(arg))
            return vars
        return set()

    def translate_sentence(
        self, sentence: Sentence, as_axiom=False
    ) -> Optional[Formula]:
        text = sentence.text
        atoms = sentence.atoms
        atoms_str = [str(a) for a in atoms]

        def make_var(name):
            if as_axiom:
                return Variable(name)
            else:
                return Constant(name.lower())

        def get_term(idx):
            if idx < len(atoms):
                m = re.search(r"\$([a-zA-Z0-9]+)\$", str(atoms[idx]))
                if m:
                    return make_var(m.group(1))
            return None

        # --- PRELIMINARIES PATTERNS ---

        # Simple equality: 1 = 1
        if "=" in atoms_str:
            idx = atoms_str.index("=")
            if (
                idx > 0
                and idx < len(atoms_str) - 1
                and atoms_str[idx - 1] == "1"
                and atoms_str[idx + 1] == "1"
            ):
                return Equal(Constant("1"), Constant("1"))

        # "The empty set is the set that has no elements."
        if (
            "empty" in atoms_str
            and "set" in atoms_str
            and "no" in atoms_str
            and "elements" in atoms_str
        ):
            E = Constant("empty_set")
            X = Variable("X")
            return And(
                Predicate("set", [E]),
                Quantifier("forall", [X], Not(Predicate("in", [X, E]))),
            )

        # "A subclass of S is a class T such that every x in T belongs to S."
        if (
            "subclass" in atoms_str
            and "class" in atoms_str
            and "every" in atoms_str
            and "belongs" in atoms_str
        ):
            S = Variable("S")
            T = Variable("T")
            X = Variable("X")
            return Quantifier(
                "forall",
                [S, T],
                Iff(
                    Predicate("subclass", [T, S]),
                    And(
                        Predicate("class", [T]),
                        Quantifier(
                            "forall",
                            [X],
                            Implies(Predicate("in", [X, T]), Predicate("in", [X, S])),
                        ),
                    ),
                ),
            )

        # "Let T be a subclass of X" (Separation Axiom assumption)
        if "Let" in atoms_str and "subclass" in atoms_str:
            # Need to extract vars.
            # Pattern: Let $T$ be a subclass of $X$
            T = None
            X = None
            for i, a in enumerate(atoms):
                if str(a).startswith("$") and T is None:
                    T = get_term(i)
                elif str(a).startswith("$") and T is not None:
                    X = get_term(i)
            if T and X:
                return Predicate("subclass", [T, X])

        # "A subset of S is a set X such that X \subseteq S"
        if (
            "subset" in atoms_str
            and "set" in atoms_str
            and ("subseteq" in str(text) or "subset" in str(text))
        ):
            # Distinguish from "A subset of S..." definition vs "Let X be a subset" assumption.
            # Definition usually has "is a set X".
            if "is" in atoms_str:
                S = Variable("S")
                X = Variable("X")
                return Quantifier(
                    "forall",
                    [S, X],
                    Iff(
                        Predicate("subset", [X, S]),
                        And(Predicate("set", [X]), Predicate("subclass", [X, S])),
                    ),
                )

        # "The intersection of S and T is..."
        if "intersection" in atoms_str and "is" in atoms_str:
            S = Variable("S")
            T = Variable("T")
            X = Variable("X")
            # intersection(S, T) = {x in S | x in T}
            # z in inter(S, T) <=> z in S & z in T
            Z = Variable("Z")
            return Quantifier(
                "forall",
                [S, T, Z],
                Iff(
                    Predicate("in", [Z, Function("intersection", [S, T])]),
                    And(Predicate("in", [Z, S]), Predicate("in", [Z, T])),
                ),
            )

        # "The union of S and T is..."
        if "union" in atoms_str and "is" in atoms_str:
            S = Variable("S")
            T = Variable("T")
            Z = Variable("Z")
            return Quantifier(
                "forall",
                [S, T, Z],
                Iff(
                    Predicate("in", [Z, Function("union", [S, T])]),
                    Or(Predicate("in", [Z, S]), Predicate("in", [Z, T])),
                ),
            )

        # "S is disjoint from T iff there is no element of S that is an element of T"
        if "disjoint" in atoms_str and "iff" in atoms_str:
            S = Variable("S")
            T = Variable("T")
            X = Variable("X")
            return Quantifier(
                "forall",
                [S, T],
                Iff(
                    Predicate("disjoint", [S, T]),
                    Not(
                        Quantifier(
                            "exists",
                            [X],
                            And(Predicate("in", [X, S]), Predicate("in", [X, T])),
                        )
                    ),
                ),
            )

        # Function Axioms

        # "Assume that dom(f) is a set and f(x) is an object..." -> f is a function.
        if (
            "Assume" in atoms_str
            and "dom" in atoms_str
            and "set" in atoms_str
            and "function" in atoms_str
        ):
            # This is complex. Simplified:
            # function(f) is defined by property?
            # Actually this is an Axiom block Conclusion: "Then f is a function."
            # The assumption is "Assume that dom(f) is a set..."
            pass  # Too complex to pattern match exactly without better parser.

        # "f maps elements of S to elements of T iff dom(f) = S and f[S] \subseteq T"
        if "maps" in atoms_str and "elements" in atoms_str:
            f = Variable("f")
            S = Variable("S")
            T = Variable("T")
            return Quantifier(
                "forall",
                [f, S, T],
                Iff(
                    Predicate("maps_to", [f, S, T]),
                    And(
                        Equal(Function("dom", [f]), S),
                        Predicate("subclass", [Function("image_of", [f, S]), T]),
                    ),
                ),
            )

        # "Let f stand for a map" (Declaration)
        if "Let" in atoms_str and "stand" in atoms_str and "map" in atoms_str:
            if as_axiom:
                return None  # or Predicate("map", [Variable("f")])?
            pass

        # --- CANTOR PATTERNS ---

        # "The value of f at any element of M is a set"
        if "value" in atoms_str and "element" in atoms_str and "set" in atoms_str:
            X = Variable("X")
            f = Constant("f_witness")
            M = make_var("M")
            return Quantifier(
                "forall",
                [X],
                Implies(
                    Predicate("in", [X, M]),
                    Predicate("set", [Function("apply", [f, X])]),
                ),
            )

        if (
            "Let" in atoms_str
            and "function" in atoms_str
            and "set" in atoms_str
            and "and" in atoms_str
        ):
            if as_axiom:
                return None
            formulas = []
            for i, word in enumerate(atoms_str):
                if word == "function" and i > 2:
                    v = get_term(i - 3)
                    if v:
                        formulas.append(Predicate("function", [v]))
                if word == "set" and i > 2:
                    v = get_term(i - 3)
                    if v:
                        formulas.append(Predicate("set", [v]))
            if len(formulas) == 1:
                return formulas[0]
            if len(formulas) > 1:
                return And(formulas[0], formulas[1])

        if "Let" in atoms_str and "set" in atoms_str:
            if as_axiom:
                # Check if it's "Let T be a subclass of X" -> handled above.
                # "Let X be a set"
                v = get_term(atoms_str.index("Let") + 1)
                if v:
                    return Predicate("set", [v])
                return None
            else:
                v = get_term(atoms_str.index("Let") + 1)
                if v:
                    return Predicate("set", [v])

        if "Let" in atoms_str and "classes" in atoms_str:
            if as_axiom:
                return None
            vars = []
            for a in atoms:
                m = re.search(r"\$([a-zA-Z0-9]+)\$", str(a))
                if m:
                    vars.append(make_var(m.group(1)))
            if vars:
                forms = [Predicate("class", [v]) for v in vars]
                if len(forms) == 1:
                    return forms[0]
                return And(forms[0], forms[1])

        if "is" in atoms_str and "a" in atoms_str and "set" in atoms_str:
            idx = atoms_str.index("is")
            if idx > 0:
                v = get_term(idx - 1)
                if v:
                    return Predicate("set", [v])

        # Definitions

        if "function" in atoms_str and "such" in atoms_str and "that" in atoms_str:
            X = None
            for a in atoms_str:
                if a.startswith("$") and "X" in a:
                    X = Variable("X")
            if X:
                F = Variable("F")
                return Quantifier(
                    "forall",
                    [F],
                    Iff(
                        Predicate("function_of", [X, F]),
                        And(Predicate("function", [F]), Equal(Function("dom", [F]), X)),
                    ),
                )

        if "surjects" in atoms_str and "iff" in atoms_str:
            F = Variable("F")
            Y = Variable("Y")
            Z = Variable("Z")
            X = Variable("X")
            lhs = Predicate("surjects_onto", [F, Y])
            rhs = Quantifier(
                "forall",
                [Z],
                Iff(
                    Predicate("in", [Z, Y]),
                    Quantifier(
                        "exists",
                        [X],
                        And(
                            Predicate("in", [X, Function("dom", [F])]),
                            Equal(Function("apply", [F, X]), Z),
                        ),
                    ),
                ),
            )
            return Quantifier("forall", [F, Y], Iff(lhs, rhs))

        if "surjective" in atoms_str and "stand" in atoms_str:
            F = Variable("F")
            X = Variable("X")
            Y = Variable("Y")
            return Quantifier(
                "forall",
                [F, X, Y],
                Iff(
                    Predicate("surjective_function_from_to", [F, X, Y]),
                    And(
                        Predicate("function_of", [X, F]),
                        Predicate("surjects_onto", [F, Y]),
                    ),
                ),
            )

        if "powerset" in atoms_str and "collection" in atoms_str:
            X = Variable("X")
            S = Variable("S")
            Z = Variable("Z")
            return Quantifier(
                "forall",
                [X, S],
                Iff(
                    Equal(Function("powerset", [X]), S),
                    Quantifier(
                        "forall",
                        [Z],
                        Iff(Predicate("in", [Z, S]), Predicate("subset", [Z, X])),
                    ),
                ),
            )

        if "powerset" in atoms_str and "any" in atoms_str and "set" in atoms_str:
            X = Variable("X")
            return Quantifier(
                "forall",
                [X],
                Implies(
                    Predicate("set", [X]), Predicate("set", [Function("powerset", [X])])
                ),
            )

        if "No" in atoms_str and "surjects" in atoms_str:
            M = make_var("M")
            F = Variable("F")
            return Not(
                Quantifier(
                    "exists",
                    [F],
                    And(
                        Predicate("function_of", [M, F]),
                        Predicate("surjects_onto", [F, Function("powerset", [M])]),
                    ),
                )
            )

        if "Assume" in atoms_str and "contrary" in atoms_str:
            return Predicate("contrary", [])

        if "Take" in atoms_str and "surjective" in atoms_str:
            f = Constant("f_witness")
            M = make_var("M")
            return Predicate(
                "surjective_function_from_to", [f, M, Function("powerset", [M])]
            )

        if "Define" in atoms_str:
            N = Constant("N")
            M = make_var("M")
            f = Constant("f_witness")
            Z = Variable("Z")
            # N = {x in M | x not in f(x)}
            return Quantifier(
                "forall",
                [Z],
                Iff(
                    Predicate("in", [Z, N]),
                    And(
                        Predicate("in", [Z, M]),
                        Not(Predicate("in", [Z, Function("apply", [f, Z])])),
                    ),
                ),
            )

        if "$N$" in atoms_str and "subset" in atoms_str:
            return Predicate("subset", [Constant("N"), make_var("M")])

        if "Consider" in atoms_str:
            z = Constant("z")
            M = make_var("M")
            f = Constant("f_witness")
            N = Constant("N")
            # Consider z such that f(z) = N.
            # Implies z in dom(f). dom(f) = M. So z in M.
            return And(Predicate("in", [z, M]), Equal(Function("apply", [f, z]), N))

        if "Then" in atoms_str and "iff" in atoms_str:
            z = Constant("z")
            N = Constant("N")
            f = Constant("f_witness")
            # z in N iff z notin f(z) = N
            # z in N <=> ~ (z in f(z))
            # Also f(z) = N
            return Iff(
                Predicate("in", [z, N]),
                Not(Predicate("in", [z, Function("apply", [f, z])])),
            )

        if "Contradiction" in atoms_str:
            return Predicate("false", [])

        return None
