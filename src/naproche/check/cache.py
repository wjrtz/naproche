import hashlib
import sqlite3
import json
from typing import List, Set, Optional
from naproche.logic.fol import Formula

CACHE_FILE = ".naproche_cache.db"


def get_formula_string(formula: Formula) -> str:
    return str(formula)


def compute_hash_formula(formula: Formula) -> str:
    return hashlib.sha256(get_formula_string(formula).encode("utf-8")).hexdigest()


class ProverCache:
    def __init__(self):
        self.conn = sqlite3.connect(CACHE_FILE, timeout=10)
        self.create_table()

    def create_table(self):
        with self.conn:
            # We use a new schema.
            # proofs table stores:
            # goal_hash: Hash of the conjecture formula
            # dependencies: JSON list of hashes of used axioms
            # result: Boolean (Success) - We mainly cache success with dependencies.
            # For failures, we might want to store context_hash?
            # Let's support both.
            # If result is True, dependencies lists the specific axioms used.
            # If result is False, dependencies might be null, and we use context_hash.

            # Since we want to support multiple proofs for the same goal (with different dependencies),
            # we don't make goal_hash PRIMARY KEY.
            # We use a surrogate key id.
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS proofs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_hash TEXT,
                    dependencies TEXT,
                    result BOOLEAN,
                    context_hash TEXT
                )
            """)

            # Index for faster lookup
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_goal_hash ON proofs (goal_hash)
            """)

    def get_proof(self, goal_hash: str, available_axiom_hashes: Set[str], context_hash: str) -> Optional[bool]:
        """
        Check if we have a cached proof for the goal that is valid in the current context.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT dependencies, result, context_hash FROM proofs WHERE goal_hash = ?", (goal_hash,))
        rows = cursor.fetchall()

        for deps_json, result, ctx_hash in rows:
            if result:
                # Successful proof. Check if dependencies are satisfied.
                try:
                    dependencies = set(json.loads(deps_json))
                    if dependencies.issubset(available_axiom_hashes):
                        return True
                except json.JSONDecodeError:
                    continue
            else:
                # Failed proof. Check if context matches exactly.
                if ctx_hash == context_hash:
                    return False

        return None

    def save_proof(self, goal_hash: str, used_axiom_hashes: List[str], result: bool, context_hash: str):
        """
        Save a proof result.
        """
        dependencies_json = json.dumps(used_axiom_hashes)
        with self.conn:
            # Check if identical entry exists to avoid duplicates?
            # Ideally yes, but SQLite doesn't have easy "INSERT IF NOT EXISTS" for this complex logic.
            # We can just insert. Cleanup later?
            # Or check first.

            # Simple deduplication
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id FROM proofs
                WHERE goal_hash = ? AND dependencies = ? AND result = ? AND context_hash = ?
            """, (goal_hash, dependencies_json, result, context_hash))
            if cursor.fetchone():
                return

            self.conn.execute(
                "INSERT INTO proofs (goal_hash, dependencies, result, context_hash) VALUES (?, ?, ?, ?)",
                (goal_hash, dependencies_json, result, context_hash),
            )

    def close(self):
        self.conn.close()
