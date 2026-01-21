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

    COLON: ":"
    TO: /\\to/
    RIGHTARROW: /\\rightarrow/
    LEFTTRIGHTARROW: /\\leftrightarrow/

    REL_OP: "<" | "=" | "\\leq" | "\\in" | "\\subseteq" | ">" | "\\geq" | "\\neq" | COLON | LEFTTRIGHTARROW
    BIN_OP: "\\setminus" | "\\cup" | "\\cap" | "\\times" | "+" | "-" | "\\cdot" | "\\circ" | TO | RIGHTARROW

    VARIABLE: /[a-zA-Z]/
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
            # f : A -> B is usually parsed as "f" and "A->B" if -> is BIN_OP?
            # But here ":" is REL_OP.
            # If A -> B is parsed as Term, then it works.
            # If -> is REL_OP, then "A -> B" is Formula.
            # "f : A -> B" is "f REL (A REL B)". But REL_OP is not recursive in `expression` usually?
            # grammar: relation: term REL_OP term.
            # So "A -> B" must be a term for "f : (A -> B)" to work.
            # But I added -> to REL_OP.
            # So "A -> B" is a relation (Formula).
            # Then "f : (A -> B)" is "Term REL Formula" ?? Invalid.
            # -> should be BIN_OP if it creates a type/set?
            # In legacy, -> is used in mapNotion.
            # Let's keep -> in REL_OP for now, but maybe it should be BIN_OP for arrow types?
            # If I make it BIN_OP, "A -> B" is a Function/Term "arrow(A,B)".
            # Then "f : A -> B" is "f : arrow(A,B)" -> Predicate("colon", [f, arrow(A,B)]).
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
                return Constant(item.value[1:])
        return item

    def VARIABLE(self, token):
        # Explicitly handle VARIABLE token if it bypasses simple_term
        return Variable(token.value)

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
