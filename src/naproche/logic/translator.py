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

        # --- Helper for parsing math ---
        def parse_term(math_str):
            res = self.parse_math_safe(math_str)
            if isinstance(res, Variable):
                if not as_axiom:
                   return Constant(res.name.lower())
            return res

        # --- MATCHING HELPERS ---
        def is_math(s): return "$" in s or "\\[" in s
        def is_word(s, w): return s == w

        # --- PATTERN MATCHING ---

        # Clean atoms (remove citation)
        clean_atoms = []
        for a in atoms_str:
            if a == "(": break
            clean_atoms.append(a)

        if clean_atoms and clean_atoms[-1] == ".":
            clean_atoms.pop()

        # --- Trailing Quantifiers ---
        # "P(x) for all x in A"
        # Check for "for" near the end
        if "for" in clean_atoms:
            # We only support simple "for all/every <var> in/of <domain>" at the end
            # Find the LAST "for" to avoid confusion with "For all ..." at start
            # But "For all ..." at start is handled by separate block.

            # If "For" is at start (index 0), it's a leading quantifier.
            # If "for" is later, it might be trailing.

            indices = [i for i, x in enumerate(clean_atoms) if x == "for"]
            if indices and indices[-1] > 0:
                f_idx = indices[-1]
                # Check if it looks like a quantifier
                # "for all/every/each ..."
                if f_idx + 1 < len(clean_atoms):
                    next_word = clean_atoms[f_idx+1]
                    if next_word in ["all", "every", "each"]:
                        # Extract quantifier part
                        quant_part = clean_atoms[f_idx:]
                        body_part = clean_atoms[:f_idx]

                        # Parse body recursively (without the quantifier part)
                        # We construct a synthetic Sentence for the body
                        body_sentence = Sentence(text=" ".join(body_part), atoms=body_part)
                        # Avoid infinite recursion if body is same (shouldn't happen as we reduced length)
                        body_formula = self.translate_sentence(body_sentence, as_axiom=as_axiom)

                        if body_formula:
                            # Parse quantifier part
                            # "for all [elements] <var> [in/of] <domain>"
                            # <var> and <domain> are likely math
                            # Scan for math in quant_part
                            maths = [x for x in quant_part if is_math(x)]
                            if len(maths) >= 2:
                                var = self.parse_math_safe(maths[0])
                                domain = self.parse_math_safe(maths[1])
                                if var and domain:
                                    v = Variable(var.name) if isinstance(var, Constant) else var
                                    return Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), body_formula))
                            elif len(maths) == 1:
                                # "for all x" (no domain?) or "for all x in D" where x in D is one formula?
                                # Maybe "for x in D" where x is math, D is math.
                                pass

        n = len(clean_atoms)

        # 1. <Formula> .
        if n == 1 and is_math(clean_atoms[0]):
            return self.parse_math_safe(clean_atoms[0])

        # 2. Assume/Then/Thus/Therefore/Hence/Indeed/Case <Formula> .
        prefixes = ["Assume", "Then", "Thus", "Therefore", "Hence", "Indeed", "Case"]
        if n >= 2 and clean_atoms[0] in prefixes:
             # Check if we should strip prefix and treat as "X is Y" or similar
             # e.g. "Then $x$ is $y$."
             # We can just remove the prefix and continue matching if it didn't match the simple case

             # But first check heuristic: if exactly one math term and nothing else significant?
             # existing logic:
             maths = [a for a in clean_atoms[1:] if is_math(a)]
             if len(maths) == 1 and len(clean_atoms) == 2:
                 # "Then $Formula$."
                 return self.parse_math_safe(maths[0])

             # If "Then $x$ is ...", strip "Then" and fall through?
             # We can modify clean_atoms, but we need to be careful about index dependencies later.
             # Or we just duplicate the "is" check here or recurse?
             # Recursion is safest if we treat "Then ..." as wrapper.
             # But we need to be careful of infinite recursion.

             # Let's try to match "Then <Term> is ..." specifically here or allow fallthrough
             # If we remove prefix from clean_atoms, we affect `n` and indices.
             # Let's create a `effective_atoms` list?
             pass

        # Helper to strip prefix for "Then ..." patterns
        # We use a loop to allow multiple prefixes? No, usually one.
        effective_atoms = clean_atoms
        if clean_atoms and clean_atoms[0] in prefixes:
            effective_atoms = clean_atoms[1:]

        # Now use effective_atoms for "is" pattern
        n_eff = len(effective_atoms)

        # "Assume the contrary"
        if "Assume" in clean_atoms and "contrary" in clean_atoms:
            return Predicate("contrary", [])

        # "Assume <Term> is [a/an] <NounPhrase>"
        if clean_atoms[0] == "Assume" and len(clean_atoms) > 2:
             # Similar logic to "Let ... be ..." or "... is ..."
             # Assume $x$ is ...
             if is_math(clean_atoms[1]) and clean_atoms[2] == "is":
                 term = self.parse_math_safe(clean_atoms[1])
                 # Assume usually introduces facts about existing vars or new vars?
                 # If new, treat as Variable. If existing, constant?
                 # Let's use parse_term (Variable -> Constant if !as_axiom)
                 # Actually if it's "Assume", it is an axiom/assumption.
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
                     # "... is a tiling of $M$" -> tiling(term, M)
                     of_idx = rest.index("of")
                     if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                         noun_phrase = "_".join(rest[:of_idx])
                         # clean up "a_", "an_" prefix if we didn't remove it correctly?
                         # (already removed at start of rest)
                         domain = parse_term(rest[of_idx+1])
                         return Predicate(noun_phrase, [term, domain])

        # 3. Let <Term> be [a/an] <NounPhrase> .
        # e.g. "Let $X$ be a set." -> set(X)
        # e.g. "Let $n$ be an integer." -> integer(n)
        if clean_atoms[0] == "Let":
            # Find "be"
            if "be" in clean_atoms:
                be_idx = clean_atoms.index("be")
                if be_idx == 2 and is_math(clean_atoms[1]):
                    # Let $X$ be ...
                    term = self.parse_math_safe(clean_atoms[1])
                    if isinstance(term, Constant) and as_axiom:
                        term = Variable(term.name) # Ensure variable for Let
                    if isinstance(term, Variable) and not as_axiom:
                         # Force constant if it's a "Let" statement inside a proof (usually introduces a new constant)?
                         term = parse_term(clean_atoms[1])

                    # Parse NounPhrase after "be"
                    rest = clean_atoms[be_idx+1:]
                    if rest and rest[0] in ["a", "an"]:
                        rest = rest[1:]

                    if len(rest) == 1:
                        noun = rest[0]
                        # "set" -> set(X), "integer" -> integer(X)
                        # We use the noun as the predicate name
                        return Predicate(noun, [term])
                    elif len(rest) > 1 and "element" in rest and "of" in rest:
                         # ... element of $D$
                         of_idx = rest.index("of")
                         if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                             domain = parse_term(rest[of_idx+1])
                             return Predicate("in", [term, domain])

            # "Let y = ..."
            if len(clean_atoms) > 2 and is_math(clean_atoms[1]):
                # If there is math that parses to Equality, return it.
                # "Let $y = f(x)$ ." -> equal(y, f(x))
                t = self.parse_math_safe(clean_atoms[1])
                if isinstance(t, Equal):
                    return t

        # "Then F[...] = ..."
        if "Then" in clean_atoms:
            # "Then $F : A \to B$"
            # Check if there is a math atom that parses to Formula (or something we can interpret as formula)
            for a in clean_atoms[1:]:
                 if is_math(a):
                     # Try parsing
                     f = self.parse_math_safe(a)
                     if isinstance(f, Formula): return f
                     # If it parses to a Term, maybe it's a relation "F: A->B"?
                     # The math parser might return a Function or similar.
                     # We can assume it is a predicate if we see relation ops.
                     # But parse_math_safe handles relation ops and returns Predicate.
                     # If it returned Term/Function, maybe it failed to see relation?
                     pass

        # "For all/every ..." patterns
        if "For" in clean_atoms and ("all" in clean_atoms or "every" in clean_atoms):
             # General pattern matching for quantifiers
             # "For all elements $x$ of $A$ we have $P(x)$"
             # "For all elements $x$ of $A$ $P(x)$"

             vars_domains = []
             i = 0
             while i < len(clean_atoms):
                 v = None
                 d = None

                 # Pattern: "elements $x$ of $Y$" or "element $x$ of $Y$"
                 if clean_atoms[i] in ["element", "elements"] and i+3 < len(clean_atoms):
                      if clean_atoms[i+2] == "of" and is_math(clean_atoms[i+1]) and is_math(clean_atoms[i+3]):
                          v = self.parse_math_safe(clean_atoms[i+1])
                          d = self.parse_math_safe(clean_atoms[i+3])

                 if v and d:
                      vars_domains.append((v,d))
                 i += 1

             # Try to find the body
             body = None

             # If "we have <Formula>", body is the formula
             if "have" in clean_atoms:
                 h_idx = clean_atoms.index("have")
                 if h_idx + 1 < len(clean_atoms) and is_math(clean_atoms[h_idx+1]):
                     body = self.parse_math_safe(clean_atoms[h_idx+1])

             # Or just the last math element if no "we have"
             if not body:
                 # Last element if it's math
                 if is_math(clean_atoms[-1]):
                      body = self.parse_math_safe(clean_atoms[-1])
                      if not isinstance(body, Formula):
                           # Maybe "$H(F(x))$ is an object" -> predicate
                           pass

             # Special case: "... is a set/object"
             if not body and "is" in clean_atoms and is_math(clean_atoms[-1]):
                  # Wait, if last is math, maybe we missed it.
                  # Look for "is [an] object/set" pattern at end
                  if clean_atoms[-1] in ["object", "set"]:
                       noun = clean_atoms[-1]
                       # Term is before "is"
                       # Scan backwards from "is"
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

        # 4. <Term> is [a/an] <NounPhrase> .
        # e.g. "$X$ is a set." -> set(X)
        # Using effective_atoms to handle "Then $X$ is ..."
        if n_eff >= 3 and effective_atoms[1] == "is" and is_math(effective_atoms[0]):
             term = parse_term(effective_atoms[0])
             rest = effective_atoms[2:]
             if rest and rest[0] in ["a", "an"]:
                 rest = rest[1:]

             # Handle "not"
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
                 # ... element of $D$
                 of_idx = rest.index("of")
                 if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                     domain = parse_term(rest[of_idx+1])
                     return Predicate("in", [term, domain])
             elif len(rest) >= 2 and rest[-2] == "to" and is_math(rest[-1]):
                 # "... is adjacent to $y$"
                 # noun phrase is everything before "to"
                 noun = "_".join(rest[:-2])
                 other = parse_term(rest[-1])
                 return Predicate(noun, [term, other])
             elif len(rest) >= 2 and "with" in rest:
                 # "... is equinumerous with $Y$"
                 with_idx = rest.index("with")
                 if with_idx + 1 < len(rest) and is_math(rest[with_idx+1]):
                      noun = "_".join(rest[:with_idx])
                      other = parse_term(rest[with_idx+1])
                      return Predicate(noun, [term, other])
             elif len(rest) > 1 and "of" in rest:
                 # "... is a tiling of $M$"
                 of_idx = rest.index("of")
                 if of_idx + 1 < len(rest) and is_math(rest[of_idx+1]):
                     noun = "_".join(rest[:of_idx])
                     other = parse_term(rest[of_idx+1])
                     return Predicate(noun, [term, other])

        # 5. Let <Formula> .
        if clean_atoms[0] == "Let" and n == 2 and is_math(clean_atoms[1]):
            f = self.parse_math_safe(clean_atoms[1])
            if isinstance(f, Equal): return f
            if isinstance(f, Predicate): return f

        # 6. Take ...
        if clean_atoms[0] == "Take":
             # "Take integers $i, j$ such that ..."
             # "Take a map F such that ..."

             # Extract properties from the noun phrase?
             # "Take integers $i, j$" -> integer(i) & integer(j)
             # "Take a map $F$" -> map(F)

             formulas = []

             # Check for "such that" condition
             cond = None
             if "that" in clean_atoms:
                 that_idx = clean_atoms.index("that")
                 if that_idx + 1 < n and is_math(clean_atoms[that_idx+1]):
                     cond = self.parse_math_safe(clean_atoms[that_idx+1])

             # Try to find variables and types before "such that"
             # e.g. "integers $i, j$" or "a map $F$"

             limit = clean_atoms.index("such") if "such" in clean_atoms else n

             # scan for math atoms in range [1, limit)
             for i in range(1, limit):
                 if is_math(clean_atoms[i]):
                     # Check word before
                     prev_word = clean_atoms[i-1] if i > 0 else ""
                     # if prev_word is "integers", "map", "element" ...

                     # Parse variables from "$i, j$"
                     # This requires unpacking comma list if it's inside math delimiter
                     # But parse_math_safe treats "$i, j$" as a single Token or fails?
                     # We need to manually split if comma is present inside math

                     raw_math = clean_atoms[i]
                     # strip delimiters
                     inner = raw_math.replace("$", "").replace("\\[", "").replace("\\]", "")
                     vars_str = inner.split(",")

                     for v_str in vars_str:
                         v_term = self.parse_math_safe(v_str.strip())
                         if isinstance(v_term, (Constant, Variable)):
                             # It's a variable being introduced.
                             # If prev word is a type, add predicate
                             if prev_word in ["integer", "integers"]:
                                 formulas.append(Predicate("integer", [v_term]))
                             elif prev_word in ["map", "maps"]:
                                 formulas.append(Predicate("map", [v_term]))
                             elif prev_word in ["set", "sets"]:
                                 formulas.append(Predicate("set", [v_term]))
                             elif prev_word == "element":
                                 # "Take an element $x$ of $D$"
                                 if i+1 < limit and clean_atoms[i+1] == "of" and i+2 < limit and is_math(clean_atoms[i+2]):
                                     domain = self.parse_math_safe(clean_atoms[i+2])
                                     formulas.append(Predicate("in", [v_term, domain]))

             if cond:
                 formulas.append(cond)

             if not formulas:
                 # Fallback: "Take $x = ...$" without type
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

        # 7. Define ...
        if clean_atoms[0] == "Define" or (n > 1 and clean_atoms[0] == "Indeed" and clean_atoms[1] == "Define"):
            # "Define $x = y$ ..."
            # "Define $F(x) = ...$ for $x$ in $A$."

            defn = None
            for a in clean_atoms:
                if is_math(a):
                    t = self.parse_math_safe(a)
                    if isinstance(t, Equal):
                        defn = t
                        break

            if defn:
                # Check for "for ... in ..." condition
                # e.g. "for $x$ in $A$"
                if "for" in clean_atoms and "in" in clean_atoms:
                    try:
                        f_idx = clean_atoms.index("for")
                        i_idx = clean_atoms.index("in")
                        if f_idx < i_idx and f_idx + 1 < n and i_idx + 1 < n:
                            var = self.parse_math_safe(clean_atoms[f_idx+1])
                            domain = self.parse_math_safe(clean_atoms[i_idx+1])
                            if var and domain:
                                # This is a quantified definition or conditional definition?
                                # Usually "Define f(x) = ... for x in A" implies: forall x in A, f(x) = ...
                                v = Variable(var.name) if isinstance(var, Constant) else var
                                return Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), defn))
                    except ValueError:
                        pass
                return defn

            return Predicate("definition", [])

        # 8. Contradiction/End/Qed
        if "Contradiction" in clean_atoms or "contradiction" in clean_atoms:
            return Predicate("false", [])
        if "End" in clean_atoms or "qed" in clean_atoms:
            return None

        # Fallback: try to find *any* math formula if sentence is short?
        # No, too risky.

        return None
