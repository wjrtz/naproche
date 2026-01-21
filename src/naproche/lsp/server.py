import os
import sys
import logging
import urllib.parse
from pygls.lsp.server import LanguageServer
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_SAVE,
    DidOpenTextDocumentParams,
    DidChangeTextDocumentParams,
    DidSaveTextDocumentParams,
    Diagnostic,
    DiagnosticSeverity,
    Range,
    Position,
)
from naproche.parser.preprocessor import extract_forthel_blocks
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.converter import convert_ast
from naproche.check.engine import Engine, Reporter
from lark.exceptions import LarkError, UnexpectedInput

server = LanguageServer("naproche-ls", "v0.1")

class DiagnosticCollector(Reporter):
    def __init__(self, diagnostics, uri, current_block_start_line=0):
        self.diagnostics = diagnostics
        self.uri = uri
        self.current_block_start_line = current_block_start_line
        self.current_step_lines = {} # Map step index to line number (approx)

    def set_current_block_offset(self, start_offset, doc_content):
        # Compute line number from offset
        self.current_block_start_line = doc_content.count('\n', 0, start_offset)
        self.doc_content = doc_content
        self.block_start_offset = start_offset

    def log(self, message):
        pass

    def error(self, message):
        line = self.current_block_start_line
        d = Diagnostic(
            range=Range(
                start=Position(line=line, character=0),
                end=Position(line=line+1, character=0),
            ),
            message=f"Error: {message}",
            severity=DiagnosticSeverity.Error,
            source="Naproche",
        )
        self.diagnostics.append(d)

    def step_verified(self, step_num, description, success, source):
        if not success:
            # Simple approximation: report at the start of the current block
            line = self.current_block_start_line

            d = Diagnostic(
                range=Range(
                    start=Position(line=line, character=0),
                    end=Position(line=line+1, character=0),
                ),
                message=f"Verification failed: {description} {source}",
                severity=DiagnosticSeverity.Error,
                source="Naproche",
            )
            self.diagnostics.append(d)

def uri_to_path(uri: str) -> str:
    parsed = urllib.parse.urlparse(uri)
    return urllib.parse.unquote(parsed.path)

def validate(ls: LanguageServer, params):
    text_doc = ls.workspace.get_text_document(params.text_document.uri)
    content = text_doc.source
    uri = params.text_document.uri

    diagnostics = []

    try:
        blocks = extract_forthel_blocks(content)
    except Exception as e:
        diagnostics.append(Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=1)),
            message=f"Error extracting blocks: {e}",
            severity=DiagnosticSeverity.Error
        ))
        ls.publish_diagnostics(uri, diagnostics)
        return

    # Base path for imports
    file_path = uri_to_path(uri)
    if file_path:
        base_path = os.path.dirname(file_path)
        if "math" in base_path:
             root_path = base_path.split("math")[0] + "math"
        else:
             root_path = base_path
    else:
        root_path = "."

    collector = DiagnosticCollector(diagnostics, uri)
    engine = Engine(base_path=root_path, reporter=collector)

    # Process each block
    for i, block in enumerate(blocks):
        collector.set_current_block_offset(block.start_offset, content)

        try:
            ast = parse_cnl(block.content)
            statements = convert_ast(ast)

            engine.check(statements)

        except LarkError as e:
            block_start_line = content.count('\n', 0, block.start_offset)

            err_line_in_block = 0
            err_col_in_block = 0

            # Try to extract line/column from exception if available
            if hasattr(e, 'line') and e.line is not None:
                err_line_in_block = e.line - 1
            if hasattr(e, 'column') and e.column is not None:
                err_col_in_block = e.column - 1

            abs_line = block_start_line + err_line_in_block

            # Ensure non-negative
            if abs_line < 0: abs_line = 0
            if err_col_in_block < 0: err_col_in_block = 0

            d = Diagnostic(
                range=Range(
                    start=Position(line=abs_line, character=err_col_in_block),
                    end=Position(line=abs_line, character=err_col_in_block + 1),
                ),
                message=f"Parse Error: {e}",
                severity=DiagnosticSeverity.Error,
                source="Naproche Parser"
            )
            diagnostics.append(d)
        except Exception as e:
             d = Diagnostic(
                range=Range(
                    start=Position(line=collector.current_block_start_line, character=0),
                    end=Position(line=collector.current_block_start_line+1, character=0),
                ),
                message=f"Error in block: {e}",
                severity=DiagnosticSeverity.Error,
                source="Naproche"
            )
             diagnostics.append(d)

    ls.publish_diagnostics(uri, diagnostics)

@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls, params: DidOpenTextDocumentParams):
    validate(ls, params)

@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: DidChangeTextDocumentParams):
    validate(ls, params)

@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls, params: DidSaveTextDocumentParams):
    validate(ls, params)

def main():
    server.start_io()

if __name__ == "__main__":
    main()
