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

    // Priority: bin_op should be lower than func_app/subscript to bind looser,
    // but in Lark ?term precedence depends on order.
    // However, relation needs to bind loosest.
    // "F : A -> B" -> colon(F, to(A,B))
    // If -> is BIN_OP, "A -> B" is term.
    // "F : Term" matches relation.
    // But "F : A \leftrightarrow B"? \leftrightarrow is REL_OP.
    // relation: term REL_OP term.
    // "F : A" is relation. "\leftrightarrow B"?
    // "F : A" cannot be LHS of another relation if relation is not in term.
    // Maybe we need chained relations or support "F : (A <-> B)"?
    // Actually "F : A <-> B" is usually "F : (A <-> B)" i.e. F maps A to B bijectively.
    // So <-> should be BIN_OP (constructor for map type) OR
    // colon binds weaker than <->? No, colon usually binds weaker.
    // If <-> is REL_OP, then "A <-> B" is Formula.
    // "F : Formula" is not allowed by grammar.
    // So <-> must be BIN_OP for this syntax to work as a Type/Set constructor.

    // Let's move LEFTTRIGHTARROW to BIN_OP.

    ?simple_term: VARIABLE
                | NUMBER
                | LATEX_CMD
                | "(" term ")"

    func_app: LATEX_CMD "{" term "}" ("{" term "}")*
            | LATEX_CMD "(" term ("," term)* ")"  // \cmd(x) or \cmd(x,y)
            | VARIABLE "(" term ("," term)* ")"  // f(x) or f(x,y)

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
                return Constant(item.value[1:])
        return item

    def VARIABLE(self, token):
        # This will be called when VARIABLE is a leaf
        # But in func_app, VARIABLE is part of rule
        return Variable(token.value)

    def func_app(self, items):
        first = items[0]
        # Lark might pass transformed children or raw tokens depending on rule
        # If VARIABLE was transformed to Variable object, then `first` is Variable.

        if isinstance(first, Variable):
             # Rule: VARIABLE "(" term ...
             func_name = first.name
             args = items[1:]
        elif isinstance(first, Token):
            # Probably LATEX_CMD token
            if first.type == "LATEX_CMD":
                func_name = first.value[1:]
                args = items[1:]
            elif first.type == "VARIABLE":
                 # Should be caught by isinstance(Variable) if transformed
                 func_name = first.value
                 args = items[1:]
            else:
                 func_name = str(first)
                 args = items[1:]
        else:
             # Maybe it's a Constant (from simple_term rule?)
             # But func_app uses explicit tokens in rule definition
             if hasattr(first, 'name'):
                 func_name = first.name
                 args = items[1:]
             else:
                 # Fallback
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
        text = text[1:-1]
    elif text.startswith("\\[") and text.endswith("\\]"):
        text = text[2:-2]

    if text.endswith("."):
        text = text[:-1]

    tree = parser_instance.parse(text)
    return MathTransformer().transform(tree)
