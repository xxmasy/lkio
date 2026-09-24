"""Preflight Language Matrix Tests (Lock 8 & Lock 9)
Validates grammar ABI compatibility and syntax parsing across TS, TSX, JS, JSX, and Java.
"""

from pathlib import Path
import pytest
from core.parsing.parser_factory import ParserFactory

GOLD_DIR = Path(__file__).resolve().parent.parent / "gold" / "mvp2" / "preflight"


def test_ts_grammar_and_syntax():
    """Lock 8 & 9: TypeScript AST validation."""
    sample_path = GOLD_DIR / "sample.ts"
    code = sample_path.read_bytes()

    factory = ParserFactory()
    parser = factory.get("typescript")
    tree = parser.parse(code)

    assert tree.root_node.type == "program"
    assert not tree.root_node.has_error

    types = [c.type for c in tree.root_node.children]
    assert "interface_declaration" in types
    assert "function_declaration" in types


def test_tsx_grammar_and_syntax():
    """Lock 8 & 9: TSX AST validation."""
    sample_path = GOLD_DIR / "sample.tsx"
    code = sample_path.read_bytes()

    factory = ParserFactory()
    parser = factory.get("tsx")
    tree = parser.parse(code)

    assert tree.root_node.type == "program"
    assert not tree.root_node.has_error

    # Find export_statement -> function_declaration -> jsx_element
    export_node = tree.root_node.children[0]
    assert export_node.type == "export_statement"


def test_js_grammar_and_syntax():
    """Lock 8 & 9: JavaScript AST validation."""
    sample_path = GOLD_DIR / "sample.js"
    code = sample_path.read_bytes()

    factory = ParserFactory()
    parser = factory.get("javascript")
    tree = parser.parse(code)

    assert tree.root_node.type == "program"
    assert not tree.root_node.has_error
    assert tree.root_node.children[0].type == "function_declaration"


def test_jsx_grammar_and_syntax():
    """Lock 8 & 9: JSX AST validation."""
    sample_path = GOLD_DIR / "sample.jsx"
    code = sample_path.read_bytes()

    factory = ParserFactory()
    parser = factory.get("jsx")
    tree = parser.parse(code)

    assert tree.root_node.type == "program"
    assert not tree.root_node.has_error
    assert tree.root_node.children[0].type == "export_statement"


def test_java_grammar_and_syntax():
    """Lock 8 & 9: Java AST validation."""
    sample_path = GOLD_DIR / "sample.java"
    code = sample_path.read_bytes()

    factory = ParserFactory()
    parser = factory.get("java")
    tree = parser.parse(code)

    assert tree.root_node.type == "program"
    assert not tree.root_node.has_error

    child_types = [c.type for c in tree.root_node.children]
    assert "package_declaration" in child_types
    assert "class_declaration" in child_types
