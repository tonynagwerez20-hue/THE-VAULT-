"""Offline statement-structure checks, NOT an MQL5 compiler or runtime test.

Parse if/else and compound statements so balanced braces alone cannot hide an
orphan else. Expressions are opaque; types and API semantics are not checked.
"""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[3]


def validate_statements(source):
    # Preserve quoted literals as opaque tokens; keywords inside them or comments
    # must not participate in control-flow parsing.
    tokens = re.findall(
        r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'
        r"'(?:\\.|[^'\\])*'|[A-Za-z_]\w*|[^\s]", source
    )
    tokens = [t for t in tokens if not t.startswith(("//", "/*"))]

    def group(i, opening, closing):
        if i >= len(tokens) or tokens[i] != opening:
            raise ValueError("missing " + opening)
        depth = 1
        i += 1
        while i < len(tokens) and depth:
            depth += (tokens[i] == opening) - (tokens[i] == closing)
            i += 1
        if depth:
            raise ValueError("unclosed " + opening)
        return i

    def statement(i):
        if i >= len(tokens):
            raise ValueError("missing statement")
        token = tokens[i]
        if token == "{":
            i += 1
            while i < len(tokens) and tokens[i] != "}":
                i = statement(i)
            if i == len(tokens):
                raise ValueError("unclosed body")
            return i + 1
        if token == "if":
            i = statement(group(i + 1, "(", ")"))
            if i < len(tokens) and tokens[i] == "else":
                i = statement(i + 1)
            return i
        if token in ("for", "while", "switch"):
            return statement(group(i + 1, "(", ")"))
        if token in ("else", "}"):
            raise ValueError("orphan " + token)
        # Plain declarations/expressions/returns end at a semicolon. Grouped
        # expressions are skipped without treating their contents as statements.
        while i < len(tokens):
            if tokens[i] == ";":
                return i + 1
            if tokens[i] == "(":
                i = group(i, "(", ")")
            elif tokens[i] == "[":
                i = group(i, "[", "]")
            elif tokens[i] in ("{", "}", "else"):
                raise ValueError("unexpected " + tokens[i] + " in plain statement")
            else:
                i += 1
        raise ValueError("unterminated statement")

    i = 0
    while i < len(tokens):
        i = statement(i)


def test_parser_accepts_nested_and_dangling_else_and_ignores_literals():
    validate_statements('{ if(a) if(b) x(); else y(); else z(); }')
    validate_statements('{ if(a) { x(); } else { y(); } if(c) z(); }')
    validate_statements('{ string s="else }"; /* else */ for(int i=0;i<3;i++) x(); }')


def test_parser_rejects_second_else_after_complete_if_else():
    with pytest.raises(ValueError, match="orphan else"):
        validate_statements('{ if(a) { x(); } else { y(); } else if(c) z(); }')


def test_actual_closed_bar_decision_body_has_no_orphan_else():
    source = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")
    body = source.split("int OnClosedBar(const long opportunity_id)", 1)[1]
    body = body.split("void OnTradeTransaction(", 1)[0]
    validate_statements(body)
