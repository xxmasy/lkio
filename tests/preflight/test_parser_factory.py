"""Preflight Tests for ParserFactory
Validates singleton instance, language registration, lazy parser construction, and thread safety.
"""

import threading
import pytest
from core.parsing.parser_factory import ParserFactory


def test_parser_factory_singleton():
    f1 = ParserFactory()
    f2 = ParserFactory()
    assert f1 is f2


def test_parser_factory_get_all_languages():
    factory = ParserFactory()
    langs = ["typescript", "tsx", "javascript", "jsx", "java"]
    for l in langs:
        p = factory.get(l)
        assert p is not None
        # Verify parser can parse a minimal string
        tree = p.parse(b"")
        assert tree.root_node is not None


def test_parser_factory_unsupported_language():
    factory = ParserFactory()
    with pytest.raises(ValueError, match="Unsupported language"):
        factory.get("unsupported_lang_xyz")


def test_parser_factory_thread_safety():
    factory = ParserFactory()
    parsers_collected = []
    errors = []

    def worker():
        try:
            p = factory.get("typescript")
            parsers_collected.append(p)
            tree = p.parse(b"const a: number = 1;")
            assert tree.root_node.type == "program"
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(parsers_collected) == 10


def test_parser_factory_detect_language():
    factory = ParserFactory()
    assert factory.detect_language("foo.ts") == "typescript"
    assert factory.detect_language("foo.tsx") == "tsx"
    assert factory.detect_language("foo.js") == "javascript"
    assert factory.detect_language("foo.jsx") == "jsx"
    assert factory.detect_language("foo.java") == "java"
    assert factory.detect_language("foo.vue") == "vue"
    assert factory.detect_language("foo.unknown") == "unknown"
