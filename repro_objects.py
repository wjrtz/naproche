from naproche.logic.translator import Translator
from naproche.logic.models import Sentence

t = Translator()

def test(text):
    print(f"Testing: '{text}'")
    # Simulate parser splitting
    # "Let $x, y$ be objects." -> ['Let', '$x, y$', 'be', 'objects', '.']
    import re
    # naive split that keeps math together if possible, but here we just simulate what parser does
    # The parser usually splits by spaces but keeps math blocks.
    # "$x, y$" is one atom if it matches MATH regex.
    # If source is `Let $x, y$ be objects.`

    # Case 1: Single math block with comma
    atoms = ['Let', '$x, y$', 'be', 'objects', '.']
    s = Sentence(text=text, atoms=atoms)
    f = t.translate_sentence(s, as_axiom=True)
    print(f"Result 1 (Single Block): {f}")

    # Case 2: Separate tokens (if parser splits on comma inside math? Unlikely for MATH regex)
    # But maybe "Let $x$, $y$ be objects."
    atoms2 = ['Let', '$x$', ',', '$y$', 'be', 'objects', '.']
    s2 = Sentence(text=text, atoms=atoms2)
    f2 = t.translate_sentence(s2, as_axiom=True)
    print(f"Result 2 (Separate Tokens): {f2}")

test("Let $x, y$ be objects.")
