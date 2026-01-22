from lark import Lark, Transformer, v_args, Token
from naproche.logic.fol import Term, Formula, Predicate, Function, Variable, Constant, Equal, Implies, Iff, And

math_grammar = r"""
    ?start: expression

    ?expression: implication
               | relation
               | term

    ?implication: expression IMPLIES expression
                | expression IFF expression

    ?relation: term REL_OP term (REL_OP term)*

    // Precedence:
    // 1. set_op (cap, cup, setminus) - highest binding in terms (after func/subscript)
    // 2. arrow_op (to)
    // 3. relation (:, =, etc)

    ?term: arrow_term

    ?arrow_term: set_term (ARROW set_term)*

    ?set_term: simple_term_wrapper (SET_OP simple_term_wrapper)*

    ?simple_term_wrapper: bin_op_other
                        | simple_term
                        | func_app
                        | subscript
                        | set_comp
                        | tuple
                        | set_enum

    // Catch-all for other bin ops if any (times, plus, etc) - putting them at set_term level or higher?
    // Let's put them at set_term level for now, or make a separate level.
    // For now, let's treat set_op explicitly.

    ?bin_op_other: simple_term_wrapper BIN_OP_OTHER simple_term_wrapper

    simple_term: VARIABLE
                | NUMBER
                | LATEX_CMD
                | IDENTIFIER
                | "(" term ")"

    tuple: "(" term ("," term)+ ")"
    set_enum: "{" term ("," term)* "}"

    func_app: LATEX_CMD "{" term "}" ("{" term "}")*
            | LATEX_CMD "(" term ("," term)* ")"
            | VARIABLE "(" term ("," term)* ")"
            | FUNC_NAME "(" term ("," term)* ")"

    subscript: term "_" (simple_term | "{" term "}")

    set_comp: "\\class" "{" term "|" text_condition_plain "}"
            | "{" expression "|" text_condition_plain "}"
            | "{" expression "\\mid" text_condition_plain "}"
            | "\\{" expression "\\mid" text_condition_escaped "\\}"

    text_condition_plain: /(.|\n)+?(?=})/
    text_condition_escaped: /(.|\n)+?(?=\\})/

    COLON: ":"
    TO: /\\to/ | /\\rightarrow/
    LEFTTRIGHTARROW: /\\leftrightarrow/

    IMPLIES: /\\implies/ | /\\Longrightarrow/
    IFF: /\\iff/ | /\\Longleftrightarrow/

    REL_OP: "<" | "=" | "\\leq" | "\\le" | "\\in" | "\\subseteq" | ">" | "\\geq" | "\\ge" | "\\neq" | COLON

    ARROW: TO | RIGHTARROW | LEFTTRIGHTARROW
    SET_OP: "\\setminus" | "\\cup" | "\\cap"

    // Other binary ops
    BIN_OP_OTHER: "\\times" | "+" | "-" | "\\cdot" | "\\circ"

    VARIABLE: /[a-zA-Z]/
    FUNC_NAME: /[a-zA-Z]+/
    NUMBER: /\d+/
    LATEX_CMD: "\\" /[a-zA-Z]+/
    IDENTIFIER: /[a-zA-Z][a-zA-Z0-9_]*/

    RIGHTARROW: /\\rightarrow/

    %import common.WS
    %ignore WS
"""

class MathTransformer(Transformer):
    def expression(self, items):
        return items[0]

    def implication(self, items):
        left, op, right = items
        if getattr(op, 'type', '') == 'IFF':
            return Iff(left, right)
        return Implies(left, right)

    def relation(self, items):
        if len(items) == 3:
            return self._binary_relation(items[0], items[1], items[2])

        # Chained relation: term op term op term ...
        # Convert to And(op(t1,t2), And(op(t2,t3), ...))
        # items: [t1, op1, t2, op2, t3, ...]

        left = items[0]
        exprs = []
        for i in range(1, len(items), 2):
            op = items[i]
            right = items[i+1]
            exprs.append(self._binary_relation(left, op, right))
            left = right

        res = exprs[0]
        for e in exprs[1:]:
            res = And(res, e)
        return res

    def _binary_relation(self, left, op, right):
        op_str = str(op)
        if op_str == "=":
            return Equal(left, right)
        elif op_str == "\\in":
            return Predicate("in", [left, right])
        elif op_str == "<":
            return Predicate("less", [left, right])
        elif op_str == "\\leq" or op_str == "\\le":
            return Predicate("leq", [left, right])
        elif op_str == "\\geq" or op_str == "\\ge":
            return Predicate("geq", [left, right])
        elif op_str == "\\neq":
            return Predicate("neq", [left, right])
        elif op_str == "\\subseteq":
            return Predicate("subset", [left, right])
        elif op_str == ":":
            return Predicate("colon", [left, right])
        return Predicate(op_str.replace("\\", ""), [left, right])

    def arrow_term(self, items):
        # items: [term, op, term, op, term...]
        # Right associative? Or Left?
        # A \to B \to C usually A \to (B \to C).
        # But here it's likely just binary usage mostly.
        # Lark handles (ARROW set_term)* as list.
        # We'll treat it left associative for now or just binary.
        # If len(items) == 1, return item.
        node = items[0]
        for i in range(1, len(items), 2):
            op = items[i]
            right = items[i+1]
            op_str = str(op).replace("\\", "")
            node = Function(op_str, [node, right])
        return node

    def set_term(self, items):
        node = items[0]
        for i in range(1, len(items), 2):
            op = items[i]
            right = items[i+1]
            op_str = str(op).replace("\\", "")
            node = Function(op_str, [node, right])
        return node

    def bin_op_other(self, items):
        left, op, right = items
        op_str = str(op).replace("\\", "")
        return Function(op_str, [left, right])

    def simple_term(self, items):
        item = items[0]
        if isinstance(item, Token):
            if item.type == "VARIABLE":
                return Variable(item.value)
            elif item.type == "NUMBER":
                return Constant(f"'{item.value}'")
            elif item.type == "LATEX_CMD":
                return Constant(item.value[1:])
            elif item.type == "IDENTIFIER":
                return Constant(item.value)
        return item

    def tuple(self, items):
        if len(items) == 2:
            return Function("pair", items)
        return Function("tuple", items)

    def set_enum(self, items):
        if not items:
            return Constant("empty_set")
        if len(items) == 1:
            return Function("singleton", items)
        return Function("set_enum", items)

    def VARIABLE(self, token):
        return Variable(token.value)

    def func_app(self, items):
        first = items[0]
        if isinstance(first, Variable):
             func_name = first.name
             args = items[1:]
        elif isinstance(first, Constant):
             func_name = first.name
             args = items[1:]
        elif isinstance(first, Token):
            if first.type == "LATEX_CMD":
                func_name = first.value[1:]
                args = items[1:]
            elif first.type == "FUNC_NAME":
                 func_name = first.value
                 args = items[1:]
            elif first.type == "VARIABLE":
                 func_name = first.value
                 args = items[1:]
            else:
                 func_name = str(first)
                 args = items[1:]
        else:
             if hasattr(first, 'name'):
                 func_name = first.name
                 args = items[1:]
             else:
                 func_name = str(first)
                 args = items[1:]

        return Function(func_name, args)

    def subscript(self, items):
        base, sub = items
        return Function("subscript", [base, sub])

    def set_comp(self, items):
        # Return special function/object to be handled by translator
        # items: [expression, text_condition]
        expr = items[0]
        cond = items[1]

        # Extract text from Tree/Token
        if hasattr(cond, 'children'):
            # It's a Tree
            cond_str = "".join(str(c) for c in cond.children)
        else:
            cond_str = str(cond)

        return Function("set_comp", [expr, Constant(f"'{cond_str}'")])

    def term(self, items):
        return items[0]

    def simple_term_wrapper(self, items):
        return items[0]

parser_instance = Lark(math_grammar, parser="earley", start="start")

def parse_math(text):
    text = text.strip()
    if text.startswith("$") and text.endswith("$"):
        if text.startswith("$$") and text.endswith("$$"):
             text = text[2:-2]
        else:
             text = text[1:-1]
    elif text.startswith("\\[") and text.endswith("\\]"):
        text = text[2:-2]

    text = text.strip()

    if text.endswith("."):
        text = text[:-1]

    tree = parser_instance.parse(text)
    res = MathTransformer().transform(tree)
    return res
