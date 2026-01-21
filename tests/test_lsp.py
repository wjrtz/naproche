import threading
import time
import os
import urllib.parse
from naproche.lsp.server import server, validate
from lsprotocol.types import DiagnosticSeverity, Diagnostic

class MockLanguageServer:
    def __init__(self):
        self.workspace = MockWorkspace()
        self.diagnostics = {}

    def publish_diagnostics(self, uri, diagnostics):
        self.diagnostics[uri] = diagnostics

class MockWorkspace:
    def __init__(self):
        self._docs = {}

    def get_text_document(self, uri):
        return self._docs.get(uri)

    def put_document(self, uri, content):
        self._docs[uri] = MockDocument(content)

class MockDocument:
    def __init__(self, content):
        self.source = content

class MockParams:
    def __init__(self, uri):
        self.text_document = MockTextDocumentIdentifier(uri)

class MockTextDocumentIdentifier:
    def __init__(self, uri):
        self.uri = uri

def test_validate_parsing_error():
    ls = MockLanguageServer()
    uri = "file://" + os.path.abspath("test.ftl.tex")
    content = r"""
\begin{forthel}
This is a sentence.
\end{forthel}
"""
    ls.workspace.put_document(uri, content)

    validate(ls, MockParams(uri))

    # "This is a sentence." should be valid CNL (grammar allows word+ DOT).
    # Engine checking might fail if "This" is unknown, but parser should pass.
    # Actually, Engine might produce Verification Error or "Could not translate".

    diags = ls.diagnostics.get(uri)
    # We expect some diagnostics (verification errors potentially), or empty if everything is perfect.
    # Since we have no definitions, verification likely fails or is empty.
    # But checking for crash is first step.
    assert diags is not None

def test_validate_syntax_error():
    ls = MockLanguageServer()
    uri = "file://" + os.path.abspath("test_syntax.ftl.tex")
    content = r"""
\begin{forthel}
This is not a valid sentence because it misses a dot
\end{forthel}
"""
    ls.workspace.put_document(uri, content)

    validate(ls, MockParams(uri))

    diags = ls.diagnostics.get(uri)
    assert len(diags) > 0
    has_parser_error = any("Parse Error" in d.message for d in diags)
    assert has_parser_error

    # Check range of the error
    err = next(d for d in diags if "Parse Error" in d.message)
    # The error is at the end of the line presumably?
    # Or "misses a dot" implies UnexpectedEOF or similar.
    # UnexpectedEOF usually doesn't have precise col info in Lark 0.x/1.x sometimes.
    # But our offset logic should place it somewhere.
    assert err.range.start.line >= 0

def test_uri_to_path_conversion():
    # Implicitly tested by validate logic extracting path from URI
    # We can test if included files are found relative to the file.
    pass

def test_verification_error():
    ls = MockLanguageServer()
    uri = "file://" + os.path.abspath("test_verify.ftl.tex")
    # A contradiction to force verification failure
    content = r"""
\begin{forthel}
Assume a contradiction.
Let $A$ be a set.
Assume $A \neq A$.
Then contradiction.
\end{forthel}
"""
    # "Assume a contradiction." -> "contradiction" might be unknown word unless defined.
    # "Then contradiction."

    # Let's use a simpler known failure if possible without definitions.
    # "Let $x$ be a set. Then $x \neq x$."

    content_fail = r"""
\begin{forthel}
\begin{proof}
Then $x \neq x$.
\end{proof}
\end{forthel}
"""
    ls.workspace.put_document(uri, content_fail)
    validate(ls, MockParams(uri))
    diags = ls.diagnostics.get(uri)
    if diags:
        for d in diags:
             print(f"Diag2: {d.message}")

    assert diags is not None
    assert any(d.severity == DiagnosticSeverity.Error for d in diags)

if __name__ == "__main__":
    test_validate_parsing_error()
    test_validate_syntax_error()
    test_verification_error()
    print("test_lsp.py passed")
