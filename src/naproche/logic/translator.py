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
from naproche.parser.math_parser import parse_math, MathTransformer


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

    def parse_math_safe(self, text):
        try:
            return parse_math(text)
        except Exception:
            return None

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

        def get_term_from_math(math_atom):
            res = self.parse_math_safe(math_atom)
            if isinstance(res, (Term, Variable, Constant, Function)):
                return res
            return None

        # --- MATH FORMULA DETECTION ---
        if len(atoms_str) == 1 and ("$" in atoms_str[0] or "\\[" in atoms_str[0]):
             # Just math expression
             return self.parse_math_safe(atoms_str[0])

        # "Assume the contrary"
        if "Assume" in atoms_str and "contrary" in atoms_str:
            return Predicate("contrary", [])

        # "Then <Math>"
        if len(atoms_str) >= 2 and atoms_str[0] == "Then" and ("$" in atoms_str[1] or "\\[" in atoms_str[1]):
             # Then <Formula>
             f = self.parse_math_safe(atoms_str[1])
             if f: return f

        # "Then f is an element of ProdSet..."
        if "Then" in atoms_str and "element" in atoms_str:
            var = None
            domain = None
            for a in atoms_str:
                if "$" in a:
                    t = get_term_from_math(a)
                    if t:
                        if var is None: var = t
                        else: domain = t
            if var and domain:
                return Predicate("in", [var, domain])

        # "Take a function G such that ..."
        # "Take an element j of D ..."
        if "Take" in atoms_str:
            if "and" not in atoms_str: # Simple take
                var = None
                domain = None
                for i, word in enumerate(atoms_str):
                    if word == "element":
                        # next might be variable
                        if i+1 < len(atoms_str) and "$" in atoms_str[i+1]:
                            var = get_term_from_math(atoms_str[i+1])
                    if word == "of" and var:
                         if i+1 < len(atoms_str) and "$" in atoms_str[i+1]:
                            domain = get_term_from_math(atoms_str[i+1])
                            break

                if var and domain:
                    return Predicate("in", [var, domain])

                if "function" in atoms_str:
                     # Take a function G such that ...
                     for a in atoms_str:
                         if "$" in a:
                             t = get_term_from_math(a)
                             if t:
                                 return Predicate("function", [t])

        # "Define ..."
        if "Define" in atoms_str:
            for a in atoms_str:
                if "$" in a:
                    f = self.parse_math_safe(a)
                    if isinstance(f, (Equal, Predicate)):
                        return f
            return Predicate("definition", [])

        # "For every element i of D, lambda_i is a set"
        if "set" in atoms_str and "For" in atoms_str:
             # Pattern: For every element $i$ of $D$ $\lambda_{i}$ is a set .
             var = None
             domain = None
             target = None

             # Extract var/domain
             if "element" in atoms_str:
                 try:
                     idx = atoms_str.index("element")
                     if idx + 3 < len(atoms_str) and atoms_str[idx+2] == "of":
                         var = get_term_from_math(atoms_str[idx+1])
                         domain = get_term_from_math(atoms_str[idx+3])
                 except ValueError:
                     pass

             # Extract target
             for a in atoms_str:
                 if "$" in a:
                     t = get_term_from_math(a)
                     if t and t != var and t != domain:
                         target = t

             if var and domain and target:
                 v = Variable(var.name) if isinstance(var, Constant) else var
                 if isinstance(v, Function): v = Variable(v.name)
                 return Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), Predicate("set", [target])))

        # "For every element i of D and every element d of Delta(i) we have d in lambda_i"
        if "For" in atoms_str and "we" in atoms_str and "have" in atoms_str:
             # Double quantification
             vars_domains = []

             # Naive scan for "element X of Y"
             i = 0
             while i < len(atoms_str):
                 if atoms_str[i] == "element":
                     if i + 3 < len(atoms_str) and atoms_str[i+2] == "of":
                         v = get_term_from_math(atoms_str[i+1])
                         d = get_term_from_math(atoms_str[i+3])
                         if v and d:
                             vars_domains.append((v, d))
                 i += 1

             body = None
             # Check end of sentence for formula
             # "we have <formula> ."
             if "have" in atoms_str:
                 try:
                     h_idx = atoms_str.index("have")
                     if h_idx + 1 < len(atoms_str):
                         body = self.parse_math_safe(atoms_str[h_idx+1])
                 except ValueError:
                     pass

             if vars_domains and body:
                 # Construct nested quantifiers
                 result = body
                 for v, d in reversed(vars_domains):
                     v_obj = Variable(v.name) if isinstance(v, Constant) else v
                     if isinstance(v_obj, Function): v_obj = Variable(v_obj.name)
                     result = Quantifier("forall", [v_obj], Implies(Predicate("in", [v_obj, d]), result))
                 return result

        # "For every ..." generic
        if "For" in atoms_str and "every" in atoms_str:
            var = None
            domain = None
            body = None

            # scan for "element $i$ of $D$"
            if "element" in atoms_str:
                try:
                    idx = atoms_str.index("element")
                    # Look ahead for var and domain
                    # "element $i$ of $D$" -> idx, idx+1($i$), idx+2(of), idx+3($D$)
                    if idx + 3 < len(atoms_str) and atoms_str[idx+2] == "of":
                        var = get_term_from_math(atoms_str[idx+1])
                        domain = get_term_from_math(atoms_str[idx+3])
                except ValueError:
                    pass

            # scan for body formula
            for i in range(len(atoms_str)-1, -1, -1):
                if "$" in atoms_str[i] or "\\[" in atoms_str[i]:
                    f = self.parse_math_safe(atoms_str[i])
                    if isinstance(f, Formula):
                        body = f
                        break

            if var and domain and body:
                v = Variable(var.name) if isinstance(var, Constant) else var
                if isinstance(v, Function): v = Variable(v.name)
                return Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), body))

        # "Let i be an element of D"
        if "Let" in atoms_str and "element" in atoms_str:
             var = None
             domain = None
             if "be" in atoms_str:
                 try:
                     idx = atoms_str.index("be")
                     # $i$ be ...
                     if idx > 0 and "$" in atoms_str[idx-1]:
                         var = get_term_from_math(atoms_str[idx-1])

                     # ... element of $D$
                     if idx + 2 < len(atoms_str) and atoms_str[idx+1] == "an" and atoms_str[idx+2] == "element":
                         if idx + 4 < len(atoms_str) and atoms_str[idx+3] == "of":
                             domain = get_term_from_math(atoms_str[idx+4])
                 except ValueError:
                     pass

             if var and domain:
                 return Predicate("in", [var, domain])

        # "Indeed ..."
        if "Indeed" in atoms_str:
             for a in atoms_str:
                 if "$" in a:
                     t = get_term_from_math(a)
                     if t: return Predicate("set", [t])

        # "Then F[...] = ..."
        if "Then" in atoms_str:
            for a in atoms_str:
                if "$" in a:
                    f = self.parse_math_safe(a)
                    if isinstance(f, Formula): return f

        # "G(m,j)(j) is an element of Delta(j)"
        # "f(j) is not an element of Delta(j)"
        if "element" in atoms_str:
            negated = "not" in atoms_str
            var = None
            domain = None
            for a in atoms_str:
                if "$" in a:
                    t = get_term_from_math(a)
                    if t:
                        if var is None: var = t
                        else: domain = t

            if var and domain:
                pred = Predicate("in", [var, domain])
                if negated: return Not(pred)
                return pred

        # "Take an element j of D and an element m of kappa_j such that ..."
        if "Take" in atoms_str and "and" in atoms_str:
             vars_domains = []
             i = 0
             while i < len(atoms_str):
                 if atoms_str[i] == "element":
                     if i + 3 < len(atoms_str) and atoms_str[i+2] == "of":
                         v = get_term_from_math(atoms_str[i+1])
                         d = get_term_from_math(atoms_str[i+3])
                         if v and d:
                             vars_domains.append((v, d))
                 i += 1

             cond = None
             if "that" in atoms_str:
                 try:
                     idx = atoms_str.index("that")
                     if idx + 1 < len(atoms_str):
                         cond = self.parse_math_safe(atoms_str[idx+1])
                 except ValueError:
                     pass

             formulas = []
             for v, d in vars_domains:
                 formulas.append(Predicate("in", [v, d]))
             if cond:
                 formulas.append(cond)

             if len(formulas) > 1:
                 # ideally combine all with And
                 res = formulas[0]
                 for f in formulas[1:]:
                     res = And(res, f)
                 return res
             elif len(formulas) == 1:
                 return formulas[0]

        # "End"
        if "End" in atoms_str:
            return None # End of proof block, structural

        if "Contradiction" in atoms_str:
            return Predicate("false", [])

        # Fallback to old regex based for simple cases not covered
        # ... (keep old logic if needed, or rely on math parser)

        # Checking old equality: 1 = 1
        if "=" in atoms_str:
             # If math parser didn't catch it (atoms were split)
             pass

        return None
