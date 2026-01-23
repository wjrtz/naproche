from lark import Lark, Transformer, Token

code = r"""
from lark import Lark, Transformer, Token

grammar = r'''
start: element*

element: directive
       | environment
       | sentence

directive: BRACKET_OPEN directive_name directive_arg* BRACKET_CLOSE
directive_name: "/"? word
directive_arg: path | /[^\s\]]+/

path: "\\path{" /[^}]+/ "}"

environment: BEGIN "{" env_name "}" optional_arg? element* END "{" env_name "}"

BEGIN.2: "\\begin"
END.2: "\\end"

env_name: /[a-zA-Z*]+/
optional_arg: "[" /[^\]]+/ "]"

sentence: atom+ DOT

atom: math | latex_cmd | word | other_symbol | punctuation

math: INLINE_MATH | DISPLAY_MATH
INLINE_MATH: /\$[^$]+\$/
DISPLAY_MATH: /\\\[(.|\n)+?\\\]/ | /\$\$(.|\n)+?\$\$/

latex_cmd: "\\" /[a-zA-Z]+/

word: /[a-zA-Z0-9_]+/
other_symbol: /[^\s\w$.\[\]\\{}]+/ | BACKSLASH | BRACE_OPEN | BRACE_CLOSE | BRACKET_OPEN | BRACKET_CLOSE
punctuation: "," | ":" | ";"

DOT: "."

BACKSLASH: "\\"
BRACE_OPEN: "{"
BRACE_CLOSE: "}"
BRACKET_OPEN: "["
BRACKET_CLOSE: "]"

COMMENT: "%" /[^\n]*/
%import common.WS
%ignore WS
%ignore COMMENT
'''

class DebugTransformer(Transformer):
    def start(self, items):
        return items

    def directive(self, items):
        return items

    def path(self, items):
        print(f"DEBUG PATH: {items}")
        if len(items) >= 2:
            return items[1].value
        return "FAIL"

parser = Lark(grammar, parser="earley", start="start")
tree = parser.parse('[read \\path{examples/preliminaries.ftl.tex}]')
print(DebugTransformer().transform(tree))
"""

exec(code)
