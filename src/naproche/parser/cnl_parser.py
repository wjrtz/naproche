from lark import Lark, Transformer, v_args, Token

class CNLTransformer(Transformer):
    def start(self, items):
        return items

    def element(self, items):
        return items[0]

    def directive(self, items):
        return items[0]

    def read_directive(self, items):
        # items[0] is "read", items[1] is path
        # But wait, grammar is "[" "read" path "]"
        # Lark strips terminals if not named? No.
        # "read" is a terminal string. path is a rule.
        # Let's check items.
        # Actually grammar is `read_directive: "[" "read" path "]"`.
        # Lark might pass the string "read" and the result of path.
        # But usually string literals are discarded in the tree if not aliased,
        # UNLESS ! is used or if they are part of the rule.
        # However, this is a transformer.
        # Let's look at `path` rule: `path: "\\path{" /[^}]+/ "}"`
        # `path` transformer returns the value.
        # So `read_directive` items will likely contain `path` value.
        # Let's assume the transformer for path returns the string.
        # `read_directive` probably gets [path_string].
        # But wait, "[" and "]" and "read" are literals. They might not be in items unless forced.
        # Let's verify standard lark behavior. Default: literals are filtered out.
        # So items will contain children that are rules or terminals (if named).
        # `path` is a rule.
        return {'type': 'directive', 'action': 'read', 'value': items[0]}

    def prover_directive(self, items):
        # prover_directive: "[" "prover" word "]"
        # items[0] should be the result of `word` rule.
        return {'type': 'directive', 'action': 'prover', 'value': items[0]}

    def cache_directive(self, items):
        # cache_directive: "[" "cache" word "]"
        return {'type': 'directive', 'action': 'cache', 'value': items[0]}

    def path(self, items):
        if len(items) >= 1:
            return items[0].value
        return ""

    def environment(self, items):
        env_name = items[1]
        content_start_idx = 2
        optional_arg = None

        if len(items) > 3:
            possible_arg = items[2]
            if isinstance(possible_arg, str) and not isinstance(possible_arg, Token) and possible_arg != items[-2]:
                 optional_arg = possible_arg
                 content_start_idx = 3

        content = [x for x in items[content_start_idx:-2] if isinstance(x, dict) and 'type' in x]

        return {'type': 'environment', 'name': env_name, 'arg': optional_arg, 'content': content}

    def env_name(self, items):
        return items[0].value

    def optional_arg(self, items):
        return items[0].value

    def sentence(self, items):
        return {'type': 'sentence', 'atoms': items}

    def atom(self, items):
        return items[0]

    def math(self, items):
        return items[0]

    def word(self, items):
        return items[0].value

    def other_symbol(self, items):
        item = items[0]
        if isinstance(item, Token):
            return item.value
        return str(item)

    def punctuation(self, items):
        return items[0].value

    def INLINE_MATH(self, token):
        return token.value

    def DISPLAY_MATH(self, token):
        return token.value

    def BACKSLASH(self, token):
        return token.value

    def BRACE_OPEN(self, token):
        return token.value

    def BRACE_CLOSE(self, token):
        return token.value

    def BRACKET_OPEN(self, token):
        return token.value

    def BRACKET_CLOSE(self, token):
        return token.value

with open('src/naproche/parser/grammar.lark', 'r') as f:
    grammar = f.read()

parser = Lark(grammar, parser='earley', start='start')

def parse_cnl(text):
    tree = parser.parse(text)
    return CNLTransformer().transform(tree)
