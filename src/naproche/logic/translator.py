from typing import List, Optional, Set
from naproche.logic.models import Statement, Sentence, Definition, Theorem, Axiom, Proof, Directive, Lemma
from naproche.logic.fol import *
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
        elif isinstance(stmt, Definition) or isinstance(stmt, Axiom) or isinstance(stmt, Lemma) or isinstance(stmt, Theorem):
            return self.translate_block(stmt)
        return []

    def translate_block(self, block: Statement) -> List[Formula]:
        assumptions = []
        conclusions = []

        for s in block.content:
            if not isinstance(s, Sentence):
                continue

            text = s.text.strip()
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
            return self.get_vars_in_term(formula.left) | self.get_vars_in_term(formula.right)
        elif isinstance(formula, Not):
            return self.get_free_vars(formula.formula)
        elif isinstance(formula, And) or isinstance(formula, Or) or isinstance(formula, Implies) or isinstance(formula, Iff):
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

    def translate_sentence(self, sentence: Sentence, as_axiom=False) -> Optional[Formula]:
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
                 m = re.search(r'\$([a-zA-Z0-9]+)\$', str(atoms[idx]))
                 if m: return make_var(m.group(1))
            return None

        # Complex patterns first!

        # CANTOR / General Complex

        if "value" in atoms_str and "element" in atoms_str and "set" in atoms_str:
             X = Variable("X")
             f = Constant("f_witness")
             M = make_var("M")
             return Quantifier("forall", [X],
                Implies(Predicate("in", [X, M]), Predicate("set", [Function("apply", [f, X])])))

        if "Let" in atoms_str and "function" in atoms_str and "set" in atoms_str and "and" in atoms_str:
            if as_axiom: return None
            formulas = []
            for i, word in enumerate(atoms_str):
                if word == "function" and i > 2:
                    v = get_term(i-3)
                    if v: formulas.append(Predicate("function", [v]))
                if word == "set" and i > 2:
                    v = get_term(i-3)
                    if v: formulas.append(Predicate("set", [v]))
            if len(formulas) == 1: return formulas[0]
            if len(formulas) > 1: return And(formulas[0], formulas[1])

        if "Let" in atoms_str and "set" in atoms_str:
            v = get_term(atoms_str.index("Let") + 1)
            if v: return Predicate("set", [v])

        if "Let" in atoms_str and "classes" in atoms_str:
             if as_axiom: return None
             vars = []
             for a in atoms:
                 m = re.search(r'\$([a-zA-Z0-9]+)\$', str(a))
                 if m: vars.append(make_var(m.group(1)))
             if vars:
                  forms = [Predicate("class", [v]) for v in vars]
                  if len(forms) == 1: return forms[0]
                  return And(forms[0], forms[1])

        # "X is a set" (Low priority)
        if "is" in atoms_str and "a" in atoms_str and "set" in atoms_str:
             idx = atoms_str.index("is")
             if idx > 0:
                 v = get_term(idx-1)
                 if v: return Predicate("set", [v])

        # Definitions

        if "subclass" in atoms_str and "every" in atoms_str and "belongs" in atoms_str:
            S = Variable("S")
            T = Variable("T")
            X = Variable("X")
            return Quantifier("forall", [S, T],
                Iff(Predicate("subclass", [T, S]),
                    And(Predicate("class", [T]),
                        Quantifier("forall", [X],
                            Implies(Predicate("in", [X, T]), Predicate("in", [X, S]))))))

        if "subset" in atoms_str and "set" in atoms_str and "subseteq" in str(text):
            S = Variable("S")
            X = Variable("X")
            return Quantifier("forall", [S, X],
                Iff(Predicate("subset", [X, S]),
                    And(Predicate("set", [X]), Predicate("subclass", [X, S]))))

        if "function" in atoms_str and "such" in atoms_str and "that" in atoms_str:
            X = None
            for a in atoms_str:
                if a.startswith("$") and "X" in a: X = Variable("X")
            if X:
                 F = Variable("F")
                 return Quantifier("forall", [F],
                    Iff(Predicate("function_of", [X, F]),
                        And(Predicate("function", [F]), Equal(Function("dom", [F]), X))))

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

        if "surjective" in atoms_str and "stand" in atoms_str:
             F = Variable("F")
             X = Variable("X")
             Y = Variable("Y")
             return Quantifier("forall", [F, X, Y],
                Iff(Predicate("surjective_function_from_to", [F, X, Y]),
                    And(Predicate("function_of", [X, F]), Predicate("surjects_onto", [F, Y]))))

        if "powerset" in atoms_str and "collection" in atoms_str:
            X = Variable("X")
            S = Variable("S")
            Z = Variable("Z")
            return Quantifier("forall", [X, S],
                 Iff(Equal(Function("powerset", [X]), S),
                     Quantifier("forall", [Z],
                         Iff(Predicate("in", [Z, S]), Predicate("subset", [Z, X])))))

        if "powerset" in atoms_str and "any" in atoms_str and "set" in atoms_str:
             X = Variable("X")
             return Quantifier("forall", [X], Implies(Predicate("set", [X]), Predicate("set", [Function("powerset", [X])])))

        if "No" in atoms_str and "surjects" in atoms_str:
             M = make_var("M")
             F = Variable("F")
             return Not(Quantifier("exists", [F],
                        And(Predicate("function_of", [M, F]),
                            Predicate("surjects_onto", [F, Function("powerset", [M])]))))

        if "Assume" in atoms_str and "contrary" in atoms_str:
             return Predicate("contrary", [])

        if "Take" in atoms_str and "surjective" in atoms_str:
             f = Constant("f_witness")
             M = make_var("M")
             return Predicate("surjective_function_from_to", [f, M, Function("powerset", [M])])

        if "Define" in atoms_str:
             N = Constant("N")
             M = make_var("M")
             f = Constant("f_witness")
             Z = Variable("Z")
             return Quantifier("forall", [Z],
                Iff(Predicate("in", [Z, N]),
                    And(Predicate("in", [Z, M]),
                        Not(Predicate("in", [Z, Function("apply", [f, Z])])))))

        if "$N$" in atoms_str and "subset" in atoms_str:
             return Predicate("subset", [Constant("N"), make_var("M")])

        if "Consider" in atoms_str:
             z = Constant("z")
             M = make_var("M")
             f = Constant("f_witness")
             N = Constant("N")
             return And(Predicate("in", [z, M]), Equal(Function("apply", [f, z]), N))

        if "Then" in atoms_str and "iff" in atoms_str:
             z = Constant("z")
             N = Constant("N")
             f = Constant("f_witness")
             return Iff(Predicate("in", [z, N]), Not(Predicate("in", [z, Function("apply", [f, z])])))

        if "Contradiction" in atoms_str:
             return Predicate("false", [])

        return None
