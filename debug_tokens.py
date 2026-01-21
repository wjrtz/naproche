from lark import Lark

grammar = r"""
start: element*

element: directive
       | environment
       | sentence

directive: "[" directive_name directive_arg* "]"
directive_name: "/"? word
directive_arg: path | /[^\s\]]+/

path: "\\path{" /[^}]+/ "}"

environment: BEGIN "{" env_name "}" optional_arg? element* END "{" env_name "}"

BEGIN.2: "\\begin"
END.2: "\\end"

env_name: /[a-zA-Z*]+/
optional_arg: "[" /[^\]]+/ "]"

sentence: atom+ "."?

atom: math | word | other_symbol | punctuation

math: INLINE_MATH | DISPLAY_MATH
INLINE_MATH: "$" /[^$]+/ "$"
DISPLAY_MATH: "\\[" /(.|\n)+?/ "\\]"

word: /[a-zA-Z0-9_]+/
other_symbol: /[^\s\w$.\[\]\\{}]+/ | BACKSLASH | BRACE_OPEN | BRACE_CLOSE
punctuation: "," | ":" | ";"

BACKSLASH: "\\"
BRACE_OPEN: "{"
BRACE_CLOSE: "}"
BRACKET_OPEN: "["
BRACKET_CLOSE: "]"

COMMENT: "%" /[^\n]*/
%import common.WS
%ignore WS
%ignore COMMENT
"""

parser = Lark(grammar, parser="earley", start="start")

def test_tokenize(text):
    print(f"--- Tokenizing: {text!r} ---")
    try:
        # Earley parser uses dynamic lexer usually, so we might not see tokens directly
        # unless we assume standard lexer. But let's try to parse and see errors.
        # To inspect tokens we need to force standard lexer or use lex function if available.

        # Lark's earley parser doesn't use a standard separate lexer unless specified.
        # But we can try to lex with a LALR parser built on same grammar to see tokens.

        l = Lark(grammar, parser="lalr")
        tokens = l.lex(text)
        for t in tokens:
            print(t)
    except Exception as e:
        print(f"Lexing error: {e}")

    print(f"--- Parsing: {text!r} ---")
    try:
        print(parser.parse(text).pretty())
    except Exception as e:
        print(f"Parsing error: {e}")

test_tokenize("Take a function $G$.")
test_tokenize("[unfoldlow off]")
