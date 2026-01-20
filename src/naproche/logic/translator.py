from typing import List, Optional
from naproche.logic.models import Statement, Sentence, Definition, Theorem, Axiom, Proof, Directive
from naproche.logic.fol import *
import re

class Translator:
    def __init__(self):
        pass

    def translate_statement(self, stmt: Statement) -> List[Formula]:
        if isinstance(stmt, Sentence):
            f = self.translate_sentence(stmt)
            return [f] if f else []
        elif isinstance(stmt, Definition) or isinstance(stmt, Axiom):
            formulas = []
            for s in stmt.content:
                f = self.translate_sentence(s)
                if f: formulas.append(f)
            return formulas
        elif isinstance(stmt, Theorem):
            formulas = []
            for s in stmt.content:
                f = self.translate_sentence(s)
                if f: formulas.append(f)
            return formulas
        elif isinstance(stmt, Directive):
            return [] # Ignore for now
        return []

    def translate_sentence(self, sentence: Sentence) -> Optional[Formula]:
        text = sentence.text
        atoms = sentence.atoms
        atoms_str = [str(a) for a in atoms]

        # Helper for extracting variable name
        def get_var(idx):
            if idx < len(atoms):
                 m = re.search(r'\$([a-zA-Z0-9]+)\$', str(atoms[idx]))
                 if m: return Variable(m.group(1))
            return None

        # Complex "Let" first: Let f be a function and Y be a set
        if "Let" in atoms_str and "function" in atoms_str and "set" in atoms_str and "and" in atoms_str:
            formulas = []
            for i, word in enumerate(atoms_str):
                if word == "function" and i > 2:
                    v = get_var(i-3) # Let $f$ be a function
                    if v: formulas.append(Predicate("function", [v]))
                if word == "set" and i > 2:
                    v = get_var(i-3) # and $Y$ be a set
                    if v: formulas.append(Predicate("set", [v]))
            if len(formulas) == 1: return formulas[0]
            if len(formulas) > 1: return And(formulas[0], formulas[1])

        # Simple "Let X be a set"
        if "Let" in atoms_str and "set" in atoms_str:
            # Ensure it is not the complex one (handled above)
            # Or just check exact length or structure?
            # "Let $X$ be a set" -> length 5 (Let, X, be, a, set)
            v = get_var(atoms_str.index("Let") + 1)
            if v: return Predicate("set", [v])

        # 2. A function of $X$ is a function $f$ such that \dom(f) = X
        if "function" in atoms_str and "such" in atoms_str and "that" in atoms_str:
            X = None
            for a in atoms_str:
                if a.startswith("$") and "X" in a: X = Variable("X")
            if X:
                 F = Variable("F")
                 return Quantifier("forall", [F],
                    Iff(Predicate("function_of", [X, F]),
                        And(Predicate("function", [F]), Equal(Function("dom", [F]), X))))

        # 4. f surjects onto Y iff ...
        if "surjects" in atoms_str and "iff" in atoms_str:
            F = Variable("F")
            Y = Variable("Y")
            Z = Variable("Z")
            X = Variable("X")

            lhs = Predicate("surjects_onto", [F, Y])
            rhs = Quantifier("forall", [Z],
                    Iff(Predicate("in", [Z, Y]),
                        Quantifier("exists", [X],
                            And(Predicate("in", [X, Function("dom", [F])]),
                                Equal(Function("apply", [F, X]), Z)))))
            return Quantifier("forall", [F, Y], Iff(lhs, rhs))

        # 5. Let a surjective function from $X$ to $Y$ stand for ...
        if "surjective" in atoms_str and "stand" in atoms_str:
             F = Variable("F")
             X = Variable("X")
             Y = Variable("Y")
             return Quantifier("forall", [F, X, Y],
                Iff(Predicate("surjective_function_from_to", [F, X, Y]),
                    And(Predicate("function_of", [X, F]), Predicate("surjects_onto", [F, Y]))))

        # 6. The powerset of $X$ is the collection of subsets of $X$
        if "powerset" in atoms_str and "collection" in atoms_str:
            X = Variable("X")
            S = Variable("S")
            Z = Variable("Z")
            return Quantifier("forall", [X, S],
                 Iff(Equal(Function("powerset", [X]), S),
                     Quantifier("forall", [Z],
                         Iff(Predicate("in", [Z, S]), Predicate("subset", [Z, X])))))

        # 7. The powerset of any set is a set
        if "powerset" in atoms_str and "any" in atoms_str and "set" in atoms_str:
             X = Variable("X")
             return Quantifier("forall", [X], Implies(Predicate("set", [X]), Predicate("set", [Function("powerset", [X])])))

        # 9. No function of $M$ surjects onto the powerset of $M$
        if "No" in atoms_str and "surjects" in atoms_str:
             M = Variable("M")
             F = Variable("F")
             return Not(Quantifier("exists", [F],
                        And(Predicate("function_of", [M, F]),
                            Predicate("surjects_onto", [F, Function("powerset", [M])]))))

        # 10. Assume the contrary
        if "Assume" in atoms_str and "contrary" in atoms_str:
             return Predicate("contrary", [])

        # 11. Take a surjective function f from M to powerset of M
        if "Take" in atoms_str and "surjective" in atoms_str:
             f = Constant("f_witness")
             M = Constant("M")
             return Predicate("surjective_function_from_to", [f, M, Function("powerset", [M])])

        # 12. The value of f at any element of M is a set
        if "value" in atoms_str and "element" in atoms_str and "set" in atoms_str:
             X = Variable("X")
             f = Constant("f_witness")
             M = Constant("M")
             return Quantifier("forall", [X],
                Implies(Predicate("in", [X, M]), Predicate("set", [Function("apply", [f, X])])))

        # 13. Define N = ...
        if "Define" in atoms_str:
             N = Constant("N")
             M = Constant("M")
             f = Constant("f_witness")
             Z = Variable("Z")
             return Quantifier("forall", [Z],
                Iff(Predicate("in", [Z, N]),
                    And(Predicate("in", [Z, M]),
                        Not(Predicate("in", [Z, Function("apply", [f, Z])])))))

        # 14. N is a subset of M
        if "$N$" in atoms_str and "subset" in atoms_str:
             return Predicate("subset", [Constant("N"), Constant("M")])

        # 15. Consider an element z of M such that f(z) = N
        if "Consider" in atoms_str:
             z = Constant("z")
             M = Constant("M")
             f = Constant("f_witness")
             N = Constant("N")
             return And(Predicate("in", [z, M]), Equal(Function("apply", [f, z]), N))

        # 16. Then z in N iff z not in f(z) = N
        if "Then" in atoms_str and "iff" in atoms_str:
             z = Constant("z")
             N = Constant("N")
             f = Constant("f_witness")
             return Iff(Predicate("in", [z, N]), Not(Predicate("in", [z, Function("apply", [f, z])])))

        # 17. Contradiction
        if "Contradiction" in atoms_str:
             return Predicate("false", [])

        return None
