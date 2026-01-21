from lark import Lark, Transformer, v_args, Token
from naproche.logic.fol import Term, Formula, Predicate, Function, Variable, Constant, Equal

math_grammar = r"""
    ?start: expression

    ?expression: relation
               | term

    ?relation: term REL_OP term

    ?term: bin_op
         | simple_term
         | func_app
         | subscript
         | set_comp

    simple_term: VARIABLE
                | NUMBER
                | LATEX_CMD
                | "(" term ")"

    func_app: LATEX_CMD "{" term "}" ("{" term "}")*
            | LATEX_CMD "(" term ("," term)* ")"  // \cmd(x) or \cmd(x,y)
            | VARIABLE "(" term ("," term)* ")"  // f(x) or f(x,y)
            | FUNC_NAME "(" term ("," term)* ")" // setminus(A,B)

    subscript: term "_" (simple_term | "{" term "}")

    bin_op: term BIN_OP term

    set_comp: "\\class" "{" term "|" text_condition "}"

    text_condition: /.+?(?=})/

    COLON: ":"
    TO: /\\to/
    RIGHTARROW: /\\rightarrow/
    LEFTTRIGHTARROW: /\\leftrightarrow/

    REL_OP: "<" | "=" | "\\leq" | "\\in" | "\\subseteq" | ">" | "\\geq" | "\\neq" | COLON
    BIN_OP: "\\setminus" | "\\cup" | "\\cap" | "\\times" | "+" | "-" | "\\cdot" | "\\circ" | TO | RIGHTARROW | LEFTTRIGHTARROW

    VARIABLE: /[a-zA-Z]/
    FUNC_NAME: /[a-zA-Z]+/
    NUMBER: /\d+/
    LATEX_CMD: "\\" /[a-zA-Z]+/

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
        elif op_str == ":":
            return Predicate("colon", [left, right])
        elif op_str == "\\to" or op_str == "\\rightarrow":
             return Predicate("to", [left, right])
        elif op_str == "\\leftrightarrow":
             return Predicate("leftrightarrow", [left, right])
        return Predicate(op_str.replace("\\", ""), [left, right])

    def bin_op(self, items):
        left, op, right = items
        op_str = str(op).replace("\\", "")
        return Function(op_str, [left, right])

    def simple_term(self, items):
        item = items[0]
        if isinstance(item, Token):
            if item.type == "VARIABLE":
                return Variable(item.value)
            elif item.type == "NUMBER":
                return Constant(item.value)
            elif item.type == "LATEX_CMD":
                # Strip backslash from LATEX_CMD
                return Constant(item.value[1:])
        return item

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

    def term(self, items):
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

    if text.endswith("."):
        text = text[:-1]

    tree = parser_instance.parse(text)
    res = MathTransformer().transform(tree)
    return res
