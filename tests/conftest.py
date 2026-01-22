import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def set_prover_env():
    # Set environment variables for provers if not already set
    if "NAPROCHE_VAMPIRE" not in os.environ:
        os.environ["NAPROCHE_VAMPIRE"] = "/app/provers/vampire"

    if "NAPROCHE_EPROVER" not in os.environ:
        os.environ["NAPROCHE_EPROVER"] = "/app/provers/eprover"

    print(f"NAPROCHE_VAMPIRE set to: {os.environ['NAPROCHE_VAMPIRE']}")
    print(f"NAPROCHE_EPROVER set to: {os.environ['NAPROCHE_EPROVER']}")
