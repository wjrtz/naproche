import hashlib
import sqlite3
from naproche.logic.fol import Formula

CACHE_FILE = ".naproche_cache.db"


def get_formula_string(formula: Formula) -> str:
    return str(formula)


def compute_hash(
    axioms: list[tuple[str, Formula]], conjecture: tuple[str, Formula]
) -> str:
    data = []
    for name, f in axioms:
        data.append(f"{name}:{get_formula_string(f)}")

    name, f = conjecture
    data.append(f"CONJ:{name}:{get_formula_string(f)}")

    full_str = "|".join(data)
    return hashlib.sha256(full_str.encode("utf-8")).hexdigest()


class ProverCache:
    def __init__(self):
        self.conn = sqlite3.connect(CACHE_FILE, timeout=10)
        self.create_table()

    def create_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    hash TEXT PRIMARY KEY,
                    result BOOLEAN
                )
            """)

    def get(self, key: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT result FROM cache WHERE hash = ?", (key,))
        row = cursor.fetchone()
        if row:
            return bool(row[0])
        return None

    def set(self, key: str, value: bool):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO cache (hash, result) VALUES (?, ?)",
                (key, value),
            )

    def close(self):
        self.conn.close()
