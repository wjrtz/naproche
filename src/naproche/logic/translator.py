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

        def parse_term(math_str):
            res = self.parse_math_safe(math_str)
            if isinstance(res, Variable):
                if not as_axiom:
                   return Constant(res.name.lower())
            return res

        def is_math(s): return "$" in s or r"\\" in s or r"\[" in s

        clean_atoms = []
        for a in atoms_str:
            if a == "(": break
            clean_atoms.append(a)

        if clean_atoms and clean_atoms[-1] == ".":
            clean_atoms.pop()

        # --- Trailing Quantifiers ---
        if "for" in clean_atoms:
            indices = [i for i, x in enumerate(clean_atoms) if x == "for"]
            if indices and indices[-1] > 0:
                f_idx = indices[-1]
                if f_idx + 1 < len(clean_atoms):
                    next_word = clean_atoms[f_idx+1]
                    if next_word in ["all", "every", "each"]:
                        quant_part = clean_atoms[f_idx:]
                        body_part = clean_atoms[:f_idx]

                        body_sentence = Sentence(text=" ".join(body_part), atoms=body_part)
                        body_formula = self.translate_sentence(body_sentence, as_axiom=as_axiom)

                        if body_formula:
                            maths = [x for x in quant_part if is_math(x)]
                            if len(maths) >= 2:
                                var = self.parse_math_safe(maths[0])
                                domain = self.parse_math_safe(maths[1])
                                if var and domain:
                                    v = Variable(var.name) if isinstance(var, Constant) else var
                                    return Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), body_formula))

        n = len(clean_atoms)
        if n == 0:
            return None

        if n == 1 and is_math(clean_atoms[0]):
            return self.parse_math_safe(clean_atoms[0])

        prefixes = ["Assume", "Then", "Thus", "Therefore", "Hence", "Indeed", "Case"]
        effective_atoms = clean_atoms
        if clean_atoms and clean_atoms[0] in prefixes:
            effective_atoms = clean_atoms[1:]

        n_eff = len(effective_atoms)

        if "Assume" in clean_atoms and "contrary" in clean_atoms:
            return Predicate("contrary", [])

        if clean_atoms and clean_atoms[0] == "Assume" and len(clean_atoms) > 2:
             if is_math(clean_atoms[1]) and clean_atoms[2] == "is":
                 term = self.parse_math_safe(clean_atoms[1])
                 if as_axiom:
                     term = Variable(term.name) if isinstance(term, Constant) else term

                 rest = clean_atoms[3:]
                 if rest and rest[0] in ["a", "an"]:
                     rest = rest[1:]

                 if len(rest) == 1:
                     noun = rest[0]
                     return Predicate(noun, [term])
                 elif len(rest) > 1 and "element" in rest and "of" in rest:
                     of_idx = rest.index("of")
                     if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                         domain = parse_term(rest[of_idx+1])
                         return Predicate("in", [term, domain])

                 elif len(rest) > 1 and "of" in rest:
                     of_idx = rest.index("of")
                     if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                         noun_phrase = "_".join(rest[:of_idx])
                         domain = parse_term(rest[of_idx+1])
                         return Predicate(noun_phrase, [term, domain])

        if clean_atoms and clean_atoms[0] == "Let":
            if "be" in clean_atoms:
                be_idx = clean_atoms.index("be")
                if be_idx == 2 and is_math(clean_atoms[1]):
                    term = self.parse_math_safe(clean_atoms[1])
                    if isinstance(term, Constant) and as_axiom:
                        term = Variable(term.name)
                    if isinstance(term, Variable) and not as_axiom:
                         term = parse_term(clean_atoms[1])

                    rest = clean_atoms[be_idx+1:]
                    if rest and rest[0] in ["a", "an"]:
                        rest = rest[1:]

                    if len(rest) == 1:
                        noun = rest[0]
                        return Predicate(noun, [term])
                    elif len(rest) > 1 and "element" in rest and "of" in rest:
                         of_idx = rest.index("of")
                         if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                             domain = parse_term(rest[of_idx+1])
                             return Predicate("in", [term, domain])

            if len(clean_atoms) > 2 and is_math(clean_atoms[1]):
                t = self.parse_math_safe(clean_atoms[1])
                if isinstance(t, Equal):
                    return t

        if "Then" in clean_atoms:
            for a in clean_atoms[1:]:
                 if is_math(a):
                     f = self.parse_math_safe(a)
                     if isinstance(f, Formula): return f

        if "For" in clean_atoms and ("all" in clean_atoms or "every" in clean_atoms):
             vars_domains = []
             i = 0
             while i < len(clean_atoms):
                 v = None
                 d = None
                 if clean_atoms[i] in ["element", "elements"] and i+3 < len(clean_atoms):
                      if clean_atoms[i+2] == "of" and is_math(clean_atoms[i+1]) and is_math(clean_atoms[i+3]):
                          v = self.parse_math_safe(clean_atoms[i+1])
                          d = self.parse_math_safe(clean_atoms[i+3])

                 if v and d:
                      vars_domains.append((v,d))
                 i += 1

             body = None
             if "have" in clean_atoms:
                 h_idx = clean_atoms.index("have")
                 if h_idx + 1 < len(clean_atoms) and is_math(clean_atoms[h_idx+1]):
                     body = self.parse_math_safe(clean_atoms[h_idx+1])

             if not body:
                 if is_math(clean_atoms[-1]):
                      body = self.parse_math_safe(clean_atoms[-1])

             if not body and "is" in clean_atoms and is_math(clean_atoms[-1]):
                  if clean_atoms[-1] in ["object", "set"]:
                       noun = clean_atoms[-1]
                       if "is" in clean_atoms:
                            is_idx = clean_atoms.index("is")
                            if is_idx > 0 and is_math(clean_atoms[is_idx-1]):
                                 term = self.parse_math_safe(clean_atoms[is_idx-1])
                                 body = Predicate(noun, [term])

             if vars_domains and body:
                 result = body
                 for v, d in reversed(vars_domains):
                     v_obj = Variable(v.name) if isinstance(v, Constant) else v
                     if isinstance(v_obj, Function): v_obj = Variable(v_obj.name)
                     result = Quantifier("forall", [v_obj], Implies(Predicate("in", [v_obj, d]), result))
                 return result

        if n_eff >= 3 and effective_atoms[1] == "is" and is_math(effective_atoms[0]):
             term = parse_term(effective_atoms[0])
             rest = effective_atoms[2:]
             if rest and rest[0] in ["a", "an"]:
                 rest = rest[1:]

             is_negated = False
             if rest and rest[0] == "not":
                 is_negated = True
                 rest = rest[1:]
                 if rest and rest[0] in ["a", "an"]:
                     rest = rest[1:]

             if len(rest) == 1:
                 noun = rest[0]
                 return Predicate(noun, [term])
             elif len(rest) > 1 and "element" in rest and "of" in rest:
                 of_idx = rest.index("of")
                 if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                     domain = parse_term(rest[of_idx+1])
                     return Predicate("in", [term, domain])
             elif len(rest) >= 2 and rest[-2] == "to" and is_math(rest[-1]):
                 noun = "_".join(rest[:-2])
                 other = parse_term(rest[-1])
                 return Predicate(noun, [term, other])
             elif len(rest) >= 2 and "with" in rest:
                 with_idx = rest.index("with")
                 if with_idx + 1 < len(rest) and is_math(rest[with_idx+1]):
                      noun = "_".join(rest[:with_idx])
                      other = parse_term(rest[with_idx+1])
                      return Predicate(noun, [term, other])
             elif len(rest) > 1 and "of" in rest:
                 of_idx = rest.index("of")
                 if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                     noun = "_".join(rest[:of_idx])
                     other = parse_term(rest[of_idx+1])
                     return Predicate(noun, [term, other])

        if clean_atoms and clean_atoms[0] == "Let" and n == 2 and is_math(clean_atoms[1]):
            f = self.parse_math_safe(clean_atoms[1])
            if isinstance(f, Equal): return f
            if isinstance(f, Predicate): return f

        if clean_atoms and clean_atoms[0] == "Take":
             formulas = []
             cond = None
             if "that" in clean_atoms:
                 that_idx = clean_atoms.index("that")
                 if that_idx + 1 < n and is_math(clean_atoms[that_idx+1]):
                     cond = self.parse_math_safe(clean_atoms[that_idx+1])

             limit = clean_atoms.index("such") if "such" in clean_atoms else n

             for i in range(1, limit):
                 if is_math(clean_atoms[i]):
                     prev_word = clean_atoms[i-1] if i > 0 else ""
                     raw_math = clean_atoms[i]
                     inner = raw_math.replace("$", "").replace(r"\[", "").replace(r"\]", "")
                     vars_str = inner.split(",")

                     for v_str in vars_str:
                         v_term = self.parse_math_safe(v_str.strip())
                         if isinstance(v_term, (Constant, Variable)):
                             if prev_word in ["integer", "integers"]:
                                 formulas.append(Predicate("integer", [v_term]))
                             elif prev_word in ["map", "maps"]:
                                 formulas.append(Predicate("map", [v_term]))
                             elif prev_word in ["set", "sets"]:
                                 formulas.append(Predicate("set", [v_term]))
                             elif prev_word == "element":
                                 if i+1 < limit and clean_atoms[i+1] == "of" and i+2 < limit and is_math(clean_atoms[i+2]):
                                     domain = self.parse_math_safe(clean_atoms[i+2])
                                     formulas.append(Predicate("in", [v_term, domain]))

             if cond:
                 formulas.append(cond)

             if not formulas:
                 for a in clean_atoms[1:]:
                     if is_math(a):
                         t = self.parse_math_safe(a)
                         if isinstance(t, Equal):
                             formulas.append(t)
                             break

             if len(formulas) == 1:
                 return formulas[0]
             elif len(formulas) > 1:
                 res = formulas[0]
                 for f in formulas[1:]:
                     res = And(res, f)
                 return res

        if clean_atoms and (clean_atoms[0] == "Define" or (n > 1 and clean_atoms[0] == "Indeed" and clean_atoms[1] == "Define")):
            defn = None
            for a in clean_atoms:
                if is_math(a):
                    t = self.parse_math_safe(a)
                    if isinstance(t, Equal):
                        defn = t
                        break

            if defn:
                if "for" in clean_atoms and "in" in clean_atoms:
                    try:
                        f_idx = clean_atoms.index("for")
                        i_idx = clean_atoms.index("in")
                        if f_idx < i_idx and f_idx + 1 < n and i_idx + 1 < n:
                            var = self.parse_math_safe(clean_atoms[f_idx+1])
                            domain = self.parse_math_safe(clean_atoms[i_idx+1])
                            if var and domain:
                                v = Variable(var.name) if isinstance(var, Constant) else var
                                return Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), defn))
                    except ValueError:
                        pass
                return defn

            return Predicate("definition", [])

        if "Contradiction" in clean_atoms or "contradiction" in clean_atoms:
            return Predicate("false", [])
        if "End" in clean_atoms or "qed" in clean_atoms:
            return None

        return None
