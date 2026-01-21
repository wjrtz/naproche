from lark import Lark, Transformer, Token


class CNLTransformer(Transformer):
    def start(self, items):
        return items

    def element(self, items):
        return items[0]

    def directive(self, items):
        if len(items) == 1:
            return {"type": "directive", "path": items[0]}
        path_val = "UNKNOWN"
        for item in items:
            if isinstance(item, str):
                path_val = item
        return {"type": "directive", "path": path_val}

    def prover_directive(self, items):
        # items[0] is prover_name, which might be a Tree or Token
        name = items[0]
        # if using Transformer, name should already be processed by prover_name
        return {"type": "prover_directive", "prover_name": name}

    def prover_name(self, items):
        return items[0].value

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
            if (
                isinstance(possible_arg, str)
                and not isinstance(possible_arg, Token)
                and possible_arg != items[-2]
            ):
                optional_arg = possible_arg
                content_start_idx = 3

        content = [
            x
            for x in items[content_start_idx:-2]
            if isinstance(x, dict) and "type" in x
        ]

        return {
            "type": "environment",
            "name": env_name,
            "arg": optional_arg,
            "content": content,
        }

    def env_name(self, items):
        return items[0].value

    def optional_arg(self, items):
        return items[0].value

    def sentence(self, items):
        return {"type": "sentence", "atoms": items}

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


with open("src/naproche/parser/grammar.lark", "r") as f:
    grammar = f.read()

parser = Lark(grammar, parser="earley", start="start")


def parse_cnl(text):
    tree = parser.parse(text)
    return CNLTransformer().transform(tree)
