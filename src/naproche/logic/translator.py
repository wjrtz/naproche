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
        self.macros = {}
        self.synonyms = {}

    def add_macro(self, phrase: str, replacement: Term):
        # print(f"DEBUG: Adding macro '{phrase}' -> {replacement}")
        self.macros[phrase.lower()] = replacement

    def add_synonym(self, singular: str, plural: str):
        self.synonyms[plural] = singular

    def normalize_noun(self, noun: str) -> str:
        return self.synonyms.get(noun, noun)

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

    def expand_colon(self, formula: Formula) -> Formula:
        if isinstance(formula, Predicate):
            if formula.name == "colon" and len(formula.args) == 2:
                f = formula.args[0]
                t = formula.args[1]
                if isinstance(t, Function) and t.name == "to" and len(t.args) == 2:
                    a = t.args[0]
                    b = t.args[1]

                    f_name = f.name if isinstance(f, (Constant, Function)) else str(f)
                    f_dom = Function("dom", [f])
                    cond1 = Equal(f_dom, a)

                    x = Variable("x_colon")
                    f_app = Function(f_name, [x])

                    lhs = Predicate("in", [x, a])
                    rhs = Predicate("in", [f_app, b])
                    cond2 = Quantifier("forall", [x], Implies(lhs, rhs))

                    return And(cond1, cond2)

            return formula
        elif isinstance(formula, Not):
            return Not(self.expand_colon(formula.formula))
        elif isinstance(formula, And):
            return And(self.expand_colon(formula.left), self.expand_colon(formula.right))
        elif isinstance(formula, Or):
            return Or(self.expand_colon(formula.left), self.expand_colon(formula.right))
        elif isinstance(formula, Implies):
            return Implies(self.expand_colon(formula.left), self.expand_colon(formula.right))
        elif isinstance(formula, Iff):
            return Iff(self.expand_colon(formula.left), self.expand_colon(formula.right))
        elif isinstance(formula, Quantifier):
            return Quantifier(formula.type, formula.vars, self.expand_colon(formula.body))
        return formula

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
                   return Constant(res.name)
            return res

        def is_math(s): return "$" in s or r"\\" in s or r"\[" in s

        # Macro: Let ... stand for ...
        if len(atoms_str) > 4 and atoms_str[0] == "Let" and "stand" in atoms_str and "for" in atoms_str:
            try:
                stand_idx = atoms_str.index("stand")
                for_idx = atoms_str.index("for")
                if stand_idx > 1 and for_idx == stand_idx + 1 and for_idx + 1 < len(atoms_str):
                    phrase_atoms = atoms_str[1:stand_idx]
                    phrase = " ".join(phrase_atoms)

                    replacement_str = atoms_str[for_idx+1]
                    if is_math(replacement_str):
                        repl_term = self.parse_math_safe(replacement_str)
                        if repl_term:
                            self.add_macro(phrase, repl_term)
                            return None
            except:
                pass

        if self.macros:
            new_atoms = []
            i = 0
            while i < len(atoms_str):
                matched = False
                for phrase, replacement in self.macros.items():
                    p_atoms = phrase.split()
                    p_len = len(p_atoms)
                    if i + p_len <= len(atoms_str):
                        segment = atoms_str[i:i+p_len]
                        if [s.lower() for s in segment] == [p.lower() for p in p_atoms]:
                            if isinstance(replacement, Constant):
                                rep_str = f"\\{replacement.name}" if replacement.name.startswith("mutilated") else replacement.name
                                rep_str = f"${replacement.name}$"
                            else:
                                rep_str = f"${str(replacement)}$"

                            new_atoms.append(rep_str)
                            i += p_len
                            matched = True
                            break
                if not matched:
                    new_atoms.append(atoms_str[i])
                    i += 1
            atoms_str = new_atoms

        clean_atoms = []
        for a in atoms_str:
            if a == "(": break
            clean_atoms.append(a)

        if clean_atoms and clean_atoms[-1] == ".":
            clean_atoms.pop()

        if "iff" in clean_atoms:
            iff_idx = clean_atoms.index("iff")
            left_atoms = clean_atoms[:iff_idx]
            right_atoms = clean_atoms[iff_idx+1:]
            left_sent = Sentence(text=" ".join(left_atoms), atoms=left_atoms)
            right_sent = Sentence(text=" ".join(right_atoms), atoms=right_atoms)
            left_f = self.translate_sentence(left_sent, as_axiom=as_axiom)
            right_f = self.translate_sentence(right_sent, as_axiom=as_axiom)
            if left_f and right_f:
                return self.expand_colon(Iff(left_f, right_f))

        # Detect "and" (Sentence conjunction)
        if "and" in clean_atoms:
            indices = [i for i, x in enumerate(clean_atoms) if x == "and"]
            for idx in reversed(indices):
                left_atoms = clean_atoms[:idx]
                right_atoms = clean_atoms[idx+1:]

                left_sent = Sentence(text=" ".join(left_atoms), atoms=left_atoms)
                right_sent = Sentence(text=" ".join(right_atoms), atoms=right_atoms)

                # Check if sides are valid sentences to avoid splitting noun phrases
                # Recursion might be slow but safe if bounded
                # We need to be careful with "element of A and B"
                # But here we are at sentence level.

                left_f = self.translate_sentence(left_sent, as_axiom=as_axiom)
                if left_f:
                    right_f = self.translate_sentence(right_sent, as_axiom=as_axiom)
                    if right_f:
                        return self.expand_colon(And(left_f, right_f))

        if "If" in clean_atoms and "then" in clean_atoms:
            try:
                then_idx = clean_atoms.index("then")
                if_idx = clean_atoms.index("If")
                if if_idx == 0:
                    left_atoms = clean_atoms[if_idx+1:then_idx]
                    right_atoms = clean_atoms[then_idx+1:]
                    left_sent = Sentence(text=" ".join(left_atoms), atoms=left_atoms)
                    right_sent = Sentence(text=" ".join(right_atoms), atoms=right_atoms)
                    left_f = self.translate_sentence(left_sent, as_axiom=as_axiom)
                    right_f = self.translate_sentence(right_sent, as_axiom=as_axiom)
                    if left_f and right_f:
                        return self.expand_colon(Implies(left_f, right_f))
            except: pass

        if clean_atoms and (clean_atoms[0] == "every" or clean_atoms[0] == "Every"):
            if "is" in clean_atoms:
                is_idx = clean_atoms.index("is")
                subj_atoms = clean_atoms[1:is_idx]
                pred_atoms = clean_atoms[is_idx+1:]

                is_negated_is = False
                if pred_atoms and pred_atoms[0] == "not":
                    is_negated_is = True
                    pred_atoms = pred_atoms[1:]

                if subj_atoms:
                    v = Variable("x_every")
                    subj_noun = "_".join(subj_atoms)
                    subj_pred = None
                    if "of" in subj_atoms:
                        of_idx = subj_atoms.index("of")
                        if of_idx < len(subj_atoms)-1 and is_math(subj_atoms[of_idx+1]):
                            noun_part = "_".join(subj_atoms[:of_idx])
                            domain_part = parse_term(subj_atoms[of_idx+1])
                            subj_pred = Predicate(noun_part, [v, domain_part])

                    if not subj_pred:
                        subj_pred = Predicate(subj_noun, [v])

                    pred_body = None
                    if "with" in pred_atoms:
                        with_idx = pred_atoms.index("with")
                        if with_idx < len(pred_atoms)-1 and is_math(pred_atoms[with_idx+1]):
                            p_noun = "_".join(pred_atoms[:with_idx])
                            p_other = parse_term(pred_atoms[with_idx+1])
                            pred_body = Predicate(p_noun, [v, p_other])

                    if not pred_body:
                        if "object" in pred_atoms:
                             pred_body = Predicate("object", [v])
                        else:
                             p_noun = "_".join(pred_atoms)
                             pred_body = Predicate(p_noun, [v])

                    if is_negated_is:
                        pred_body = Not(pred_body)

                    return Quantifier("forall", [v], Implies(subj_pred, pred_body))


        if clean_atoms and clean_atoms[0] in ["A", "An", "a", "an"] and "is" in clean_atoms:
             try:
                 is_idx = clean_atoms.index("is")
                 if is_idx > 1:
                     noun_words = clean_atoms[1:is_idx]

                     # Generic noun phrase parsing
                     name_parts = []
                     args = []
                     for w in noun_words:
                         if is_math(w):
                             t = self.parse_math_safe(w)
                             if isinstance(t, (Variable, Constant)):
                                 args.append(Variable(t.name))
                         elif w not in ["of", "in", "to", "with", "from"]:
                             name_parts.append(w)

                     noun = "_".join(name_parts)
                     noun = self.normalize_noun(noun)

                     body_atoms = clean_atoms[is_idx+1:]
                     var = None
                     for a in body_atoms:
                         if is_math(a):
                             t = self.parse_math_safe(a)
                             if isinstance(t, (Variable, Constant)):
                                 var = Variable(t.name)
                                 break
                     if var:
                         synthetic_sent = Sentence(text="", atoms=[f"${var.name}$", "is"] + body_atoms)
                         rhs = self.translate_sentence(synthetic_sent, as_axiom=as_axiom)
                         if rhs:
                             lhs = Predicate(noun, [var] + args)
                             return Quantifier("forall", [var], Iff(lhs, rhs))
             except Exception as e:
                 print(f"DEBUG: [A|An] block exception: {e}")
                 import traceback
                 traceback.print_exc()

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

                            var_str = None
                            domain = None

                            if len(maths) == 1 and r"\\in" in maths[0]:
                                parts = maths[0].split(r"\\in")
                                if len(parts) == 2:
                                    var_str = parts[0]
                                    dom_str = parts[1]
                                    if not dom_str.strip().startswith("$"): dom_str = "$" + dom_str
                                    if not dom_str.strip().endswith("$"): dom_str = dom_str + "$"
                                    domain = self.parse_math_safe(dom_str)
                                    var_str = var_str.replace("$", "").replace(r"\\[", "") # Clean var_str for splitting

                            elif len(maths) >= 2:
                                var_str = maths[0]
                                domain = self.parse_math_safe(maths[1])

                            if var_str and domain:
                                # Handle comma separated variables: $x,y$
                                raw_vars = var_str.replace("$", "").replace(r"\\[", "").replace(r"\\]", "").split(",")
                                vars_list = []
                                for rv in raw_vars:
                                    vt = self.parse_math_safe(rv.strip())
                                    if isinstance(vt, (Variable, Constant)):
                                        vars_list.append(Variable(vt.name))
                                    else:
                                        if rv.strip():
                                            vars_list.append(Variable(rv.strip()))

                                if vars_list:
                                    res = body_formula
                                    for v in reversed(vars_list):
                                        res = Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), res))
                                    return self.expand_colon(res)

                    elif next_word == "some":
                        quant_part = clean_atoms[f_idx:]
                        body_part = clean_atoms[:f_idx]
                        body_sentence = Sentence(text=" ".join(body_part), atoms=body_part)
                        body_formula = self.translate_sentence(body_sentence, as_axiom=as_axiom)
                        if body_formula:
                             rest = quant_part[1:]
                             segments = []
                             current_seg = []
                             for a in rest:
                                 if a == "and":
                                     if current_seg: segments.append(current_seg)
                                     current_seg = []
                                 else:
                                     current_seg.append(a)
                             if current_seg: segments.append(current_seg)

                             valid = True
                             parsed_vars = []
                             for seg in segments:
                                 if not seg or seg[0] != "some":
                                     valid = False
                                     break
                                 math_indices = [i for i, x in enumerate(seg) if is_math(x)]
                                 if not math_indices:
                                     valid = False
                                     break
                                 v_idx = math_indices[0]
                                 v_term = self.parse_math_safe(seg[v_idx])
                                 if not isinstance(v_term, (Variable, Constant)):
                                     valid = False
                                     break
                                 var_name = v_term.name
                                 noun_part = seg[1:v_idx]
                                 noun = "_".join(noun_part)
                                 noun = self.normalize_noun(noun)
                                 domain_pred = None
                                 if noun == "element" and v_idx + 2 < len(seg) and seg[v_idx+1] == "of":
                                      if is_math(seg[v_idx+2]):
                                           dom = self.parse_math_safe(seg[v_idx+2])
                                           domain_pred = lambda v, d=dom: Predicate("in", [v, d])
                                 else:
                                      domain_pred = lambda v, n=noun: Predicate(n, [v])
                                 if domain_pred:
                                     parsed_vars.append((var_name, domain_pred))
                                 else:
                                     valid = False
                                     break

                             if valid and parsed_vars:
                                 result = body_formula
                                 for v_name, dom_func in reversed(parsed_vars):
                                     v = Variable(v_name)
                                     cond = dom_func(v)
                                     result = Quantifier("exists", [v], And(cond, result))
                                 return self.expand_colon(result)

        n = len(clean_atoms)
        if n == 0:
            return None

        if n == 1 and is_math(clean_atoms[0]):
            return self.expand_colon(self.parse_math_safe(clean_atoms[0]))

        prefixes = ["Assume", "Then", "Thus", "Therefore", "Hence", "Indeed", "Case"]
        effective_atoms = clean_atoms
        if clean_atoms and clean_atoms[0] in prefixes:
            effective_atoms = clean_atoms[1:]

        n_eff = len(effective_atoms)
        if n_eff == 1 and is_math(effective_atoms[0]):
            return self.expand_colon(self.parse_math_safe(effective_atoms[0]))

        # Handle "Let us show that P" -> P
        if clean_atoms and len(clean_atoms) >= 4:
            if clean_atoms[0] == "Let" and clean_atoms[1] == "us" and clean_atoms[2] == "show" and clean_atoms[3] == "that":
                # Translate remainder as a sentence
                rest_atoms = clean_atoms[4:]
                rest_sent = Sentence(text=" ".join(rest_atoms), atoms=rest_atoms)
                return self.translate_sentence(rest_sent, as_axiom=as_axiom)

        res = self._translate_logic(clean_atoms, effective_atoms, n, n_eff, parse_term, is_math, as_axiom)
        # print(f"DEBUG: Result for '{text}': {res}")
        if res:
            return self.expand_colon(res)
        return None

    def _translate_logic(self, clean_atoms, effective_atoms, n, n_eff, parse_term, is_math, as_axiom):
        if "Assume" in clean_atoms and "contrary" in clean_atoms:
            return Predicate("contrary", [])

        if clean_atoms and clean_atoms[0] == "Assume" and len(clean_atoms) > 2:
             # Updated "Assume X is ..." to handle comma-separated variables in single math token
             tok = clean_atoms[1]
             rest_start_idx = 3

             # Flexible "is" detection
             is_found = False
             if clean_atoms[2] == "is":
                 is_found = True
                 rest_start_idx = 3
             elif clean_atoms[2] in ["are", "be"]: # Just in case
                 is_found = True
                 rest_start_idx = 3

             if is_math(tok) and is_found:
                 variables = []
                 term = self.parse_math_safe(tok)
                 if isinstance(term, (Variable, Constant)):
                     if as_axiom:
                         variables.append(Variable(term.name))
                     else:
                         variables.append(term)
                 else:
                     # Split manual
                     inner = tok.replace("$", "").replace(r"\\[", "").replace(r"\\]", "")
                     parts = inner.split(",")
                     for part in parts:
                         pt = self.parse_math_safe(part.strip())
                         if isinstance(pt, (Variable, Constant)):
                             if as_axiom:
                                 variables.append(Variable(pt.name))
                             else:
                                 variables.append(pt)

                 if variables:
                     rest = clean_atoms[rest_start_idx:]
                     if rest and rest[0] in ["a", "an"]:
                         rest = rest[1:]

                     if len(rest) == 1:
                         noun = rest[0]
                         preds = [Predicate(noun, [v]) for v in variables]
                         if len(preds) == 1: return preds[0]
                         res = preds[0]
                         for p in preds[1:]: res = And(res, p)
                         return res
                     elif len(rest) > 1 and "element" in rest and "of" in rest:
                         of_idx = rest.index("of")
                         if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                             domain = parse_term(rest[of_idx+1])
                             preds = [Predicate("in", [v, domain]) for v in variables]
                             if len(preds) == 1: return preds[0]
                             res = preds[0]
                             for p in preds[1:]: res = And(res, p)
                             return res

                     elif len(rest) > 1 and "of" in rest:
                         of_idx = rest.index("of")
                         if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                             noun_phrase = "_".join(rest[:of_idx])
                             domain = parse_term(rest[of_idx+1])
                             preds = [Predicate(noun_phrase, [v, domain]) for v in variables]
                             if len(preds) == 1: return preds[0]
                             res = preds[0]
                             for p in preds[1:]: res = And(res, p)
                             return res

        if clean_atoms and clean_atoms[0] == "Let":
            if "be" in clean_atoms:
                be_idx = clean_atoms.index("be")

                # Check for comma-separated variables in "Let X, Y be sets"
                variables = []

                # Scan from index 1 up to be_idx
                for i in range(1, be_idx):
                    tok = clean_atoms[i]
                    # Skip commas
                    if tok.strip() == ",":
                        continue

                    if is_math(tok):
                        term = self.parse_math_safe(tok)
                        if isinstance(term, Constant) and as_axiom:
                            term = Variable(term.name)
                        if isinstance(term, Variable) and not as_axiom:
                             term = parse_term(tok)

                        # Handle case where one math block contains multiple variables "$X, Y$"
                        if isinstance(term, (Variable, Constant)):
                             variables.append(term)
                        else:
                             # Try splitting inside math if it wasn't parsed as simple term
                             # But parse_math_safe might return None or complex term
                             # If we have comma inside math block, manual split
                             inner = tok.replace("$", "").replace(r"\\[", "").replace(r"\\]", "")
                             parts = inner.split(",")
                             for part in parts:
                                 pt = self.parse_math_safe(part.strip())
                                 if isinstance(pt, (Variable, Constant)):
                                     if as_axiom:
                                         variables.append(Variable(pt.name))
                                     else:
                                         variables.append(pt)
                    else:
                        pass

                if variables:
                    rest = clean_atoms[be_idx+1:]
                    if rest and rest[0] in ["a", "an"]:
                        rest = rest[1:]

                    # Handle "subset of"
                    if len(rest) > 1 and "subset" in rest and "of" in rest:
                         of_idx = rest.index("of")
                         if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                             domain = parse_term(rest[of_idx+1])
                             preds = [Predicate("subset", [v, domain]) for v in variables]
                             if len(preds) == 1: return preds[0]
                             res = preds[0]
                             for p in preds[1:]: res = And(res, p)
                             return res

                    # Handle "subclass of" (new fix for prelims)
                    if len(rest) > 1 and "subclass" in rest and "of" in rest:
                         of_idx = rest.index("of")
                         if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                             domain = parse_term(rest[of_idx+1])
                             preds = [Predicate("subclass", [v, domain]) for v in variables]
                             if len(preds) == 1: return preds[0]
                             res = preds[0]
                             for p in preds[1:]: res = And(res, p)
                             return res

                    if len(rest) == 1:
                        noun = rest[0]
                        noun = self.normalize_noun(noun)

                        preds = [Predicate(noun, [v]) for v in variables]
                        if len(preds) == 1: return preds[0]
                        res = preds[0]
                        for p in preds[1:]: res = And(res, p)
                        return res

                    elif len(rest) > 1 and "element" in rest and "of" in rest:
                         of_idx = rest.index("of")
                         if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                             domain = parse_term(rest[of_idx+1])
                             preds = [Predicate("in", [v, domain]) for v in variables]
                             if len(preds) == 1: return preds[0]
                             res = preds[0]
                             for p in preds[1:]: res = And(res, p)
                             return res

            if len(clean_atoms) > 2 and is_math(clean_atoms[1]):
                t = self.parse_math_safe(clean_atoms[1])
                if isinstance(t, Equal):
                    return t

        if "Then" in clean_atoms:
            for a in clean_atoms[1:]:
                 if is_math(a):
                     f = self.parse_math_safe(a)
                     if isinstance(f, Formula): return f

        if (clean_atoms and clean_atoms[0] in ["For", "for"]) and ("all" in clean_atoms or "every" in clean_atoms):
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
                 elif is_math(clean_atoms[i]):
                      # Check for embedded \in inside the math token
                      # e.g. $x,y \in \dom(f)$
                      math_content = clean_atoms[i]
                      if r"\in" in math_content:
                          # Split by \in
                          parts = math_content.split(r"\in")
                          if len(parts) == 2:
                              var_str = parts[0]
                              dom_str = parts[1]
                              if not dom_str.strip().startswith("$"): dom_str = "$" + dom_str
                              if not dom_str.strip().endswith("$"): dom_str = dom_str + "$"
                              domain = self.parse_math_safe(dom_str)
                              var_str = var_str.replace("$", "").replace(r"\\[", "") # Clean var_str for splitting

                              if var_str and domain:
                                  # Handle comma separated variables: $x,y$
                                  raw_vars = var_str.replace("$", "").replace(r"\\[", "").replace(r"\\]", "").split(",")
                                  vars_list = []
                                  for rv in raw_vars:
                                      vt = self.parse_math_safe(rv.strip())
                                      if isinstance(vt, (Variable, Constant)):
                                          vars_list.append(Variable(vt.name))
                                      else:
                                          if rv.strip():
                                              vars_list.append(Variable(rv.strip()))

                                  if vars_list:
                                      for v_item in vars_list:
                                          vars_domains.append((v_item, domain))

                      elif i+2 < len(clean_atoms):
                          if clean_atoms[i+1] == "in" and is_math(clean_atoms[i+2]):
                              var_str = clean_atoms[i]
                              d = self.parse_math_safe(clean_atoms[i+2])

                              # Handle comma separated variables
                              raw_vars = var_str.replace("$", "").replace(r"\\[", "").replace(r"\\]", "").split(",")
                              vars_list = []
                              for rv in raw_vars:
                                  vt = self.parse_math_safe(rv.strip())
                                  if isinstance(vt, (Variable, Constant)):
                                      vars_list.append(Variable(vt.name))
                                  elif rv.strip():
                                      vars_list.append(Variable(rv.strip()))

                              if vars_list and d:
                                  for v_item in vars_list:
                                      vars_domains.append((v_item, d))
                 i += 1

             body = None
             if "have" in clean_atoms:
                 h_idx = clean_atoms.index("have")
                 if h_idx + 1 < len(clean_atoms) and is_math(clean_atoms[h_idx+1]):
                     body = self.parse_math_safe(clean_atoms[h_idx+1])

             if not body:
                 if is_math(clean_atoms[-1]):
                      body = self.parse_math_safe(clean_atoms[-1])

             if not body and "is" in clean_atoms:
                  last_atom = clean_atoms[-1]
                  is_noun_math = is_math(last_atom)
                  if last_atom in ["object", "set"] or is_noun_math:
                       noun = last_atom
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


        if n_eff >= 5 and "class" in effective_atoms and "elements" in effective_atoms:
             try:
                 class_idx = effective_atoms.index("class")
                 elem_idx = effective_atoms.index("elements")
                 if effective_atoms[1] == "is" and is_math(effective_atoms[0]):
                     term_A = parse_term(effective_atoms[0])
                     of1_idx = class_idx + 1
                     if effective_atoms[of1_idx] == "of":
                         P_atoms = effective_atoms[of1_idx+1:elem_idx]
                         if P_atoms:
                             pred_name = P_atoms[0]
                             if is_math(pred_name):
                                 t = self.parse_math_safe(pred_name)
                                 if isinstance(t, Constant): pred_name = t.name
                                 elif isinstance(t, Variable): pred_name = t.name

                             of2_idx = elem_idx + 1
                             if of2_idx < n_eff and effective_atoms[of2_idx] == "of":
                                 B_atom = effective_atoms[of2_idx+1]
                                 if is_math(B_atom):
                                     domain_B = parse_term(B_atom)
                                     x = Variable("x_gen")
                                     lhs = Predicate("in", [x, term_A])
                                     rhs = And(Predicate("in", [x, domain_B]), Predicate(pred_name, [x]))
                                     return Quantifier("forall", [x], Iff(lhs, rhs))
             except Exception:
                 pass

        if n_eff >= 3 and effective_atoms[1] == "is" and is_math(effective_atoms[0]):
             term = parse_term(effective_atoms[0])
             rest = effective_atoms[2:]
             cond = None
             if "such" in rest and "that" in rest:
                 try:
                     such_idx = rest.index("such")
                     if such_idx + 1 < len(rest) and rest[such_idx+1] == "that":
                         cond_atoms = rest[such_idx+2:]
                         rest = rest[:such_idx]
                         cond_sent = Sentence(text=" ".join(cond_atoms), atoms=cond_atoms)
                         cond = self.translate_sentence(cond_sent, as_axiom=as_axiom)
                 except: pass

             if rest and rest[0] in ["a", "an"]:
                 rest = rest[1:]

             is_negated = False
             if rest and rest[0] == "not":
                 is_negated = True
                 rest = rest[1:]
                 if rest and rest[0] in ["a", "an"]:
                     rest = rest[1:]

             if rest and is_math(rest[-1]):
                  last_t = self.parse_math_safe(rest[-1])
                  if isinstance(last_t, (Variable, Constant)) and isinstance(term, (Variable, Constant)):
                       if last_t.name == term.name:
                           rest = rest[:-1]

             # Check for "element of" specifically
             if len(rest) > 1 and "element" in rest and "of" in rest:
                 of_idx = rest.index("of")
                 if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                     domain = parse_term(rest[of_idx+1])
                     pred = Predicate("in", [term, domain])
                     if cond: pred = And(pred, cond)
                     if is_negated: return Not(pred)
                     return pred

             # Generic parsing with support for "and" splitting
             segments = []
             current_seg = []
             for w in rest:
                 if w.strip() == "and":
                     if current_seg:
                         segments.append(current_seg)
                     current_seg = []
                 else:
                     current_seg.append(w)
             if current_seg: segments.append(current_seg)

             preds = []
             for seg in segments:
                 # Strip leading a/an if present
                 eff_seg = seg
                 if eff_seg and eff_seg[0] in ["a", "an"]:
                     eff_seg = eff_seg[1:]

                 name_parts = []
                 args = []
                 for w in eff_seg:
                     if is_math(w):
                         args.append(parse_term(w))
                     elif w not in ["of", "in", "to", "with", "from"]:
                         name_parts.append(w)

                 if name_parts:
                     noun = "_".join(name_parts)
                     noun = self.normalize_noun(noun)
                     preds.append(Predicate(noun, [term] + args))

             if preds:
                 if len(preds) == 1:
                     res = preds[0]
                 else:
                     res = preds[0]
                     for p in preds[1:]:
                         res = And(res, p)

                 if cond: res = And(res, cond)
                 if is_negated: return Not(res)
                 return res

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

        if clean_atoms and (clean_atoms[0] in ["Define", "define"] or (n > 1 and clean_atoms[0] == "Indeed" and clean_atoms[1] in ["Define", "define"])):
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
                                domain_axiom = None
                                if isinstance(defn, Equal) and isinstance(defn.left, Function):
                                    fname = defn.left.name
                                    z = Variable("z_dom")
                                    f_term = Constant(fname)
                                    dom_term = Function("dom", [f_term])
                                    lhs = Predicate("in", [z, dom_term])
                                    rhs = Predicate("in", [z, domain])
                                    domain_axiom = Quantifier("forall", [z], Iff(lhs, rhs))

                                value_axiom = Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), defn))
                                if domain_axiom:
                                    return And(domain_axiom, value_axiom)
                                return value_axiom
                    except ValueError:
                        pass

                # Handle SetComp
                if isinstance(defn, Equal) and isinstance(defn.right, Function) and defn.right.name == "set_comp":
                    # P = { x \in U | condition }
                    # defn.right.args: [expression, text_token]
                    expression = defn.right.args[0]
                    text_condition = defn.right.args[1]

                    var = None
                    domain_cond = None

                    if isinstance(expression, Predicate) and expression.name == "in":
                        var = expression.args[0]
                        domain_cond = expression
                    elif isinstance(expression, (Variable, Constant)):
                        var = expression
                        domain_cond = None

                    if var:
                        # Parse text condition
                        if isinstance(text_condition, Constant):
                            cond_str = text_condition.name.strip()
                        else:
                            cond_str = str(text_condition).strip()

                        # Strip outer quotes if any
                        if (cond_str.startswith("'") and cond_str.endswith("'")) or \
                           (cond_str.startswith('"') and cond_str.endswith('"')):
                            cond_str = cond_str[1:-1]

                        cond_str = cond_str.strip()

                        # Handle \text{...} wrapper
                        if cond_str.startswith("\\text{") and cond_str.endswith("}"):
                            cond_str = cond_str[6:-1]

                        cond_str = cond_str.strip()
                        # Use simple splitting for now matching cnl_parser basics
                        cond_atoms = [a for a in re.split(r'(\s+)', cond_str) if a.strip()]
                        # A simple merge pass
                        merged_atoms = []
                        buffer = ""
                        in_math = False
                        for atom in cond_atoms:
                            if "$" in atom:
                                parts = atom.split("$")
                                # If atom has $, it toggles state
                                # atom: "$a$" -> 2 parts (empty, a, empty) -> 3 parts?
                                # atom: "a$b" -> ?
                                # Let's assume standard $...$ structure
                                # Count $
                                count = atom.count("$")
                                if count % 2 == 1:
                                    # Toggle
                                    if in_math:
                                        # End math
                                        buffer += " " + atom
                                        merged_atoms.append(buffer)
                                        buffer = ""
                                        in_math = False
                                    else:
                                        # Start math
                                        buffer = atom
                                        in_math = True
                                    continue

                            if in_math:
                                buffer += " " + atom
                            else:
                                merged_atoms.append(atom)

                        if buffer:
                            merged_atoms.append(buffer)

                        # Construct Sentence
                        cond_sent = Sentence(text=cond_str, atoms=merged_atoms)
                        # Always translate definition condition as axiom to preserve variables for quantification
                        cond_form = self.translate_sentence(cond_sent, as_axiom=True)

                        if cond_form:
                            # ! [x] : (in(x, P) <-> (domain_cond & cond_form))
                            if domain_cond:
                                body = And(domain_cond, cond_form)
                            else:
                                body = cond_form

                            P_term = defn.left
                            lhs = Predicate("in", [var, P_term])

                            # Ensure var is Variable
                            v_obj = Variable(var.name) if isinstance(var, (Variable, Constant)) else var

                            return Quantifier("forall", [v_obj], Iff(lhs, body))

                return defn

            return Predicate("definition", [])

        if "Contradiction" in clean_atoms or "contradiction" in clean_atoms:
            return Predicate("false", [])
        if "End" in clean_atoms or "qed" in clean_atoms:
            return None

        if n_eff >= 3 and effective_atoms[1] == "has":
            term = parse_term(effective_atoms[0])
            quantifier = effective_atoms[2]
            noun_start = 3
            is_negated_has = False
            if quantifier == "no":
                is_negated_has = True
            elif quantifier in ["a", "an"]:
                is_negated_has = False
            else:
                noun_start = 2
            noun_atoms = effective_atoms[noun_start:]

            # Use generic parsing for noun + args
            name_parts = []
            args = []
            for w in noun_atoms:
                if is_math(w):
                    args.append(parse_term(w))
                elif w not in ["of", "in", "to", "with", "from"]:
                    name_parts.append(w)

            if name_parts:
                noun = "_".join(name_parts)
                noun = self.normalize_noun(noun)

                x = Variable("x_has")
                # Predicate is noun(x, term, other_args...) ?
                # Or noun(x, other_args..., term)?
                # "T has a supremum in S" -> supremum(x, T, S).
                # Noun parsing yields "supremum" and args=[S].
                # We need to construct predicate.
                # Usually: noun(x) & relation(x, term, args).
                # But here "supremum" is a relation "supremum(u, S, T)".
                # "T has a supremum x in S".
                # The predicate is supremum(x, T, S).
                # My generic parser extracted args=[S].
                # Name=supremum.
                # So we want Predicate("supremum", [x, term] + args).

                prop = Quantifier("exists", [x], Predicate(noun, [x, term] + args))
                if is_negated_has:
                    return Not(prop)
                return prop

        return None
