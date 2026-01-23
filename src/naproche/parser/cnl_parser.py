from lark import Lark, Transformer, Token


class CNLTransformer(Transformer):
    def start(self, items):
        # Flatten the list because sentence might return a list of items
        flat = []
        for i in items:
            if isinstance(i, list):
                flat.extend(i)
            else:
                flat.append(i)
        return flat

    def element(self, items):
        return items[0]

    def directive(self, items):
        # items[0] is '['
        # items[1] is directive_name
        # items[2:-1] are directive_args
        # items[-1] is ']'

        name = items[1]
        args = items[2:-1]

        clean_args = []
        for arg in args:
            if isinstance(arg, Token):
                clean_args.append(arg.value)
            else:
                clean_args.append(str(arg))

        return {"type": "directive", "name": name, "args": clean_args}

    def directive_name(self, items):
        return "".join([str(i) for i in items])

    def directive_arg(self, items):
        # This returns the child, which could be the path string (from path method)
        # or a Token from regex.
        item = items[0]
        if isinstance(item, Token):
            return item.value
        return item

    def path(self, items):
        # path: "\\path{" /[^}]+/ "}"
        # Empirically, items contains only the regex match token
        if len(items) >= 1:
            if isinstance(items[0], Token):
                return items[0].value
            return str(items[0])
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

        # We need to flatten content here as well if it contains lists (from sentences)
        raw_content = items[content_start_idx:-2]
        content = []
        for x in raw_content:
            if isinstance(x, list):
                content.extend([i for i in x if isinstance(i, dict) and "type" in i])
            elif isinstance(x, dict) and "type" in x:
                content.append(x)

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
        # Detect directive at start of sentence
        # Pattern: [ name args... ]
        if len(items) >= 3 and str(items[0]) == '[':
            try:
                # Find matching bracket
                end_idx = -1
                depth = 0
                for k, at in enumerate(items):
                    s = str(at)
                    if s == '[':
                        depth += 1
                    elif s == ']':
                        depth -= 1
                        if depth == 0:
                            end_idx = k
                            break

                if end_idx > 1:
                    # Check if it looks like a directive
                    # Inside brackets: items[1:end_idx]
                    # Name is usually first word.
                    inner = items[1:end_idx]
                    if inner:
                         # Construct directive
                         name_token = inner[0]
                         args = inner[1:]

                         directive_obj = {
                             "type": "directive",
                             "name": str(name_token),
                             "args": [str(a) for a in args]
                         }

                         result = [directive_obj]

                         # Check if there is remaining text
                         rest = items[end_idx+1:]

                         if rest and not (len(rest) == 1 and str(rest[0]) == '.'):
                             # Check if rest has actual content
                             has_content = any(str(a) not in ['.'] for a in rest)
                             if has_content:
                                 result.append({"type": "sentence", "atoms": rest})

                         return result
            except Exception:
                pass

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
