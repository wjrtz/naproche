import sys
from naproche.logic.translator import Translator
from naproche.logic.models import Sentence
from naproche.logic.fol import Formula

def test(t, text, atoms):
    print(f"Testing: {text}")
    print(f"Atoms: {atoms}")
    s = Sentence(text=text, atoms=atoms)
    res = t.translate_sentence(s, as_axiom=True)
    print(f"Result: {res}")
    print(f"Macros: {t.macros.keys()}")
    print("-" * 20)

t = Translator()

# Test Case 1: "Let $x, y$ be objects"
# The parser produces atoms=['Let', '$x, y$', 'be', 'objects', '.']
# But usually clean_atoms removes '.'
test(t, "Let $x, y$ be objects", ['Let', '$x, y$', 'be', 'objects'])

# Test Case 2: "Let $X, Y$ be sets"
test(t, "Let $X, Y$ be sets", ['Let', '$X, Y$', 'be', 'sets'])

# Test Case 3: "Let $f : S \to T$ stand for ..."
# Atoms for $f : S \to T$ might be complex if space separated?
# Usually parser keeps math as one token if inside $...$
# "Let $f : S \to T$ stand for $f$ is a function and $\dom(f) = S$ and $\ran(f) \subseteq T$."
# Let's approximate atoms based on parser behavior (split by spaces outside math)
atoms3 = ['Let', '$f : S \\to T$', 'stand', 'for', '$f$', 'is', 'a', 'function', 'and', '$\\dom(f) = S$', 'and', '$\\ran(f) \\subseteq T$']
test(t, "Let $f : S \\to T$ stand for ...", atoms3)

# Test Case 4: "Assume $x, y$ are objects"
test(t, "Assume $x, y$ are objects", ['Assume', '$x, y$', 'are', 'objects'])
