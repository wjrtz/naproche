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
             # Heuristic: if exactly one math term, use it.
             maths = [a for a in clean_atoms[1:] if is_math(a)]
             if len(maths) == 1:
                 return self.parse_math_safe(maths[0])

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
                         var = self.parse_math_safe(atoms_str[idx+1])
                         domain = self.parse_math_safe(atoms_str[idx+3])
                 except ValueError:
                     pass

             # Extract target
             for a in atoms_str:
                 if is_math(a):
                     t = self.parse_math_safe(a)
                     if t and (not var or t.name != var.name) and (not domain or t.name != domain.name):
                         target = t

             if var and domain and target:
                 v = Variable(var.name) if isinstance(var, Constant) else var
                 if isinstance(v, Function): v = Variable(v.name)
                 return Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), Predicate("set", [target])))

        # "For every element i of D and every element d of Delta(i) we have d in lambda_i"
        if "For" in clean_atoms and "we" in clean_atoms and "have" in clean_atoms:
             # Double quantification or Single
             vars_domains = []

             # Scan for "element X of Y" or just "$x$ of $A$"
             # The existing pattern matching was brittle using atoms_str which might contain "(citation)"

             # Better scan in clean_atoms
             i = 0
             while i < len(clean_atoms):
                 v = None
                 d = None

                 # Pattern: "element $x$ of $Y$"
                 if clean_atoms[i] == "element":
                     if i + 3 < len(clean_atoms) and clean_atoms[i+2] == "of":
                         v = self.parse_math_safe(clean_atoms[i+1])
                         d = self.parse_math_safe(clean_atoms[i+3])

                 # Pattern: "$x$ of $Y$" (if preceded by elements or implied)
                 # Wait, just matching specific indices is risky.

                 if v and d:
                     vars_domains.append((v, d))

                 i += 1

             body = None
             # Check end of sentence for formula
             # "we have <formula> ."
             if "have" in clean_atoms:
                 try:
                     h_idx = clean_atoms.index("have")
                     if h_idx + 1 < len(clean_atoms):
                         body = self.parse_math_safe(clean_atoms[h_idx+1])
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
                        var = self.parse_math_safe(atoms_str[idx+1])
                        domain = self.parse_math_safe(atoms_str[idx+3])
                except ValueError:
                    pass

            # scan for body formula
            for i in range(len(atoms_str)-1, -1, -1):
                if is_math(atoms_str[i]):
                    f = self.parse_math_safe(atoms_str[i])
                    if isinstance(f, Formula):
                        body = f
                        break

            if var and domain and body:
                v = Variable(var.name) if isinstance(var, Constant) else var
                if isinstance(v, Function): v = Variable(v.name)
                return Quantifier("forall", [v], Implies(Predicate("in", [v, domain]), body))

        # 4. <Term> is [a/an] <NounPhrase> .
        # e.g. "$X$ is a set." -> set(X)
        if n >= 3 and clean_atoms[1] == "is" and is_math(clean_atoms[0]):
             term = parse_term(clean_atoms[0])
             rest = clean_atoms[2:]
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
