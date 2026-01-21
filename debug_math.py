from naproche.parser.math_parser import parse_math

tests = [
    r"\Sum{\kappa}{D} < \Prod{\lambda}{D}",
    r"\Prod{\lambda}{D} \leq \Sum{\kappa}{D}",
    r"f(i)",
    r"\kappa_{i}",
    r"\lambda_{i} \setminus \Delta(i)",
    r"G(m,j) = f"
]

for t in tests:
    print(f"Parsing: {t}")
    try:
        res = parse_math(t)
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")
