from lark import Lark, Transformer, v_args, Token
from naproche.logic.fol import Term, Formula, Predicate, Function, Variable, Constant, Equal

math_grammar = r"""
    ?start: expression

    ?expression: relation
               | term

    ?relation: term REL_OP term

    ?term: simple_term
         | func_app
         | subscript
         | set_comp
         | bin_op

    ?simple_term: VARIABLE
                | NUMBER
                | LATEX_CMD
                | "(" term ")"

    func_app: LATEX_CMD "{" term "}" ("{" term "}")*
            | LATEX_CMD "(" term ")"
            | VARIABLE "(" term ("," term)* ")"  // f(x) or f(x,y)

    subscript: term "_" (simple_term | "{" term "}")

    bin_op: term BIN_OP term

    set_comp: "\\class" "{" term "|" text_condition "}"

    text_condition: /.+?(?=})/

    VARIABLE: /[a-zA-Z]/
    NUMBER: /\d+/
    LATEX_CMD: "\\" /[a-zA-Z]+/
    REL_OP: "<" | "=" | "\\leq" | "\\in" | "\\subseteq" | ">" | "\\geq" | "\\neq"
    BIN_OP: "\\setminus" | "\\cup" | "\\cap" | "\\times" | "+" | "-" | "\\cdot"

    %import common.WS
    %ignore WS
"""

class MathTransformer(Transformer):
    def expression(self, items):
        return items[0]

    def relation(self, items):
        left, op, right = items
        op_str = str(op)
        if op_str == "=":
            return Equal(left, right)
        elif op_str == "\\in":
            return Predicate("in", [left, right])
        elif op_str == "<":
            return Predicate("less", [left, right])
        elif op_str == "\\leq":
            return Predicate("leq", [left, right])
        elif op_str == "\\subseteq":
            return Predicate("subset", [left, right])
        return Predicate(op_str.replace("\\", ""), [left, right])

    def bin_op(self, items):
        left, op, right = items
        op_str = str(op).replace("\\", "")
        return Function(op_str, [left, right])

    def simple_term(self, items):
        item = items[0]
        if isinstance(item, Token):
            if item.type == "VARIABLE":
                return Constant(item.value)
            elif item.type == "NUMBER":
                return Constant(item.value)
            elif item.type == "LATEX_CMD":
                return Constant(item.value[1:])
        return item

    def func_app(self, items):
        first = items[0]
        if isinstance(first, Token):
            # VARIABLE(args)
            func_name = first.value
            args = items[1:]
        else:
            # LATEX_CMD or result of LATEX_CMD token
            # But wait, LATEX_CMD token is consumed in rule.
            # In rule: LATEX_CMD "{" term ...
            # items[0] is the token LATEX_CMD
            func_name = first.value[1:]
            args = items[1:]

        return Function(func_name, args)

    def subscript(self, items):
        base, sub = items
        return Function("subscript", [base, sub])

    def term(self, items):
        return items[0]

parser_instance = Lark(math_grammar, parser="earley", start="start")

def parse_math(text):
    text = text.strip()
    if text.startswith("$") and text.endswith("$"):
        text = text[1:-1]
    elif text.startswith("\\[") and text.endswith("\\]"):
        text = text[2:-2]

    if text.endswith("."):
        text = text[:-1]

    tree = parser_instance.parse(text)
    return MathTransformer().transform(tree)
