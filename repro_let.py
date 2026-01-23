from naproche.logic.translator import Translator
from naproche.logic.models import Sentence

t = Translator()

def test(text):
    print(f"Testing: '{text}'")
    s = Sentence(text=text, atoms=text.split())
    # Fix atoms splitting for commas and dots
    import re
    atoms = [a for a in re.split(r'(\s+|[,.])', text) if a.strip() and a not in [',', '.']]
    s.atoms = atoms
    f = t.translate_sentence(s, as_axiom=True)
    print(f"Result: {f}")

test("Let $X, Y$ be sets.")
test("Let $T$ be a subclass of $X$.")
test("Then $T$ is a set.")
