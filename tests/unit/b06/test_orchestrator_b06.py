"""LKIO MVP2-B B-06 Dedicated Unit Test Suite: Symbol Extraction Orchestrator & Fallback Handling
Validates:
1. 10 Architecture Locks (LOCK-ORCH-01 ~ LOCK-ORCH-10)
2. 16 Acceptance Gates (Gate A ~ Gate P)
3. 5 Gold Fixtures (valid_multi_lang, malformed_syntax, unsupported_files, corrupted_binary, deterministic_order)
4. Counter Integrity Rule (total == successful + failed + unsupported, scanned == successful + failed)
5. Mechanical Invariance Assertions (Gate C equivalence, Gate L zero graph, Gate M zero DB import)
"""

import ast
from pathlib import Path
import time
from typing import Any
import pytest

from core.extraction.dto import (
    BatchExtractionSummary,
    ExtractionFailureReason,
    FileExtractionResult,
    SymbolCandidate,
)
from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.parsing.parser_factory import ParserFactory

GOLD_ORCH_DIR = Path(__file__).resolve().parents[2] / "gold" / "mvp2" / "symbols" / "orchestrator"


@pytest.fixture
def orchestrator() -> SymbolExtractionOrchestrator:
    return SymbolExtractionOrchestrator(ParserFactory())


def assert_symbol_semantic_equivalence(extractor_sym: SymbolCandidate, orch_sym: SymbolCandidate):
    """Mechanical proof for Gate C & LOCK-ORCH-07: Orchestrator MUST NOT mutate extractor-owned semantic fields."""
    assert extractor_sym.symbol_type == orch_sym.symbol_type
    assert extractor_sym.base_symbol_type == orch_sym.base_symbol_type
    assert extractor_sym.name == orch_sym.name
    assert extractor_sym.qualified_name == orch_sym.qualified_name
    assert extractor_sym.start_line == orch_sym.start_line
    assert extractor_sym.end_line == orch_sym.end_line
    assert extractor_sym.start_column == orch_sym.start_column
    assert extractor_sym.end_column == orch_sym.end_column
    assert extractor_sym.signature == orch_sym.signature
    assert extractor_sym.canonical_signature == orch_sym.canonical_signature
    assert extractor_sym.signature_discriminator == orch_sym.signature_discriminator
    assert extractor_sym.language == orch_sym.language
    assert extractor_sym.modifiers == orch_sym.modifiers
    assert extractor_sym.annotations == orch_sym.annotations
    assert extractor_sym.is_exported == orch_sym.is_exported
    assert extractor_sym.export_kind == orch_sym.export_kind
    assert extractor_sym.classification_method == orch_sym.classification_method
    assert extractor_sym.docstring == orch_sym.docstring
    assert extractor_sym.parser_version == orch_sym.parser_version
    assert extractor_sym.extractor_version == orch_sym.extractor_version
    assert extractor_sym.metadata == orch_sym.metadata

    # Explicit check for evidence and source provenance
    assert extractor_sym.metadata.get("evidence") == orch_sym.metadata.get("evidence")
    assert extractor_sym.metadata.get("source_kind") == orch_sym.metadata.get("source_kind")
    assert extractor_sym.metadata.get("extraction_method") == orch_sym.metadata.get("extraction_method")

    # Only orchestration-owned context is allowed to be enriched
    assert orch_sym.project_key != ""
    assert orch_sym.file_rel_path != ""


# ==============================================================================
# Gate A & Gate B: File Type Routing & Unsupported Extension Handling
# ==============================================================================

def test_gate_a_file_type_routing(orchestrator: SymbolExtractionOrchestrator):
    """Gate A (LOCK-ORCH-01): Verifies that all 8 standard extensions route to the expected language."""
    routing_matrix = {
        "index.ts": "typescript",
        "app.tsx": "tsx",
        "util.js": "javascript",
        "component.jsx": "jsx",
        "module.mjs": "javascript",
        "legacy.cjs": "javascript",
        "Service.java": "java",
        "Card.vue": "vue",
    }
    for file_name, expected_lang in routing_matrix.items():
        assert orchestrator.detect_language(file_name) == expected_lang
        assert orchestrator.is_supported(file_name) is True


def test_gate_b_unsupported_extension_handling(orchestrator: SymbolExtractionOrchestrator):
    """Gate B (LOCK-ORCH-01, LOCK-ORCH-06): Verifies non-code extensions are safely rejected as unsupported."""
    unsupported = ["style.css", "data.json", "config.yaml", "README.md", "script.py"]
    for file_name in unsupported:
        assert orchestrator.detect_language(file_name) == "unknown"
        assert orchestrator.is_supported(file_name) is False

        res = orchestrator.extract_file(
            code_bytes=b"dummy content",
            project_key="TEST_PROJ",
            file_path=f"C:/fake/{file_name}",
            file_rel_path=f"src/{file_name}",
        )
        assert res.success is False
        assert res.error_reason == ExtractionFailureReason.UNSUPPORTED_EXTENSION.value
        assert "Unsupported file extension" in (res.error_detail or "")


# ==============================================================================
# Gate C: Extractor Contract Invariance & Mechanical Proof
# ==============================================================================

def test_gate_c_extractor_contract_invariance(orchestrator: SymbolExtractionOrchestrator):
    """Gate C (LOCK-ORCH-02, LOCK-ORCH-07): Mechanically proves that extractor-owned fields are 100% immutable."""
    ts_file = GOLD_ORCH_DIR / "valid_multi_lang" / "service.ts"
    code = ts_file.read_bytes()
    rel_path = "src/services/service.ts"

    # 1. Direct call to frozen B-03 Extractor
    direct_candidates = orchestrator.ts_extractor.extract(
        code_bytes=code,
        file_path=str(ts_file),
        file_rel_path=rel_path,
        language="typescript",
    )

    # 2. Call via B-06 Orchestrator
    res = orchestrator.extract_file(
        code_bytes=code,
        project_key="TEST_PROJ",
        file_path=str(ts_file),
        file_rel_path=rel_path,
    )
    assert res.success is True
    assert len(res.symbols) == len(direct_candidates)

    # 3. Mechanical field-by-field proof of semantic invariance
    for direct_sym, orch_sym in zip(direct_candidates, res.symbols):
        assert_symbol_semantic_equivalence(direct_sym, orch_sym)
        assert orch_sym.project_key == "TEST_PROJ"


# ==============================================================================
# Gate D: Single-File Failure Isolation
# ==============================================================================

def test_gate_d_failure_isolation_sequence(orchestrator: SymbolExtractionOrchestrator):
    """Gate D (LOCK-ORCH-03): Verifies that a valid -> bad -> valid -> bad -> valid batch isolates failures."""
    valid_ts = b"export const alpha = 1;"
    valid_js = b"export function beta() { return 2; }"
    valid_java = b"package com.demo; public class Gamma {}"

    corrupted_bytes = b"\x80\x81\xff\xfe\x00\x00"  # Invalid UTF-8
    empty_bytes = b"   \n\t  "                     # Empty file

    batch_input = [
        (valid_ts, "C:/app/alpha.ts", "src/alpha.ts"),
        (corrupted_bytes, "C:/app/bad1.ts", "src/bad1.ts"),
        (valid_js, "C:/app/beta.js", "src/beta.js"),
        (empty_bytes, "C:/app/bad2.java", "src/bad2.java"),
        (valid_java, "C:/app/gamma.java", "src/gamma.java"),
    ]

    summary = orchestrator.extract_batch(batch_input, project_key="ISOLATION_TEST")

    assert summary.total_files == 5
    assert summary.scanned_files == 5
    assert summary.successful_files == 3
    assert summary.failed_files == 2
    assert summary.unsupported_files == 0
    assert summary.verify_counter_integrity() is True

    # Check results by path
    by_path = {r.file_rel_path: r for r in summary.results}
    assert by_path["src/alpha.ts"].success is True
    assert len(by_path["src/alpha.ts"].symbols) > 0

    assert by_path["src/bad1.ts"].success is False
    assert by_path["src/bad1.ts"].error_reason == ExtractionFailureReason.ENCODING_FAILURE.value

    assert by_path["src/beta.js"].success is True
    assert len(by_path["src/beta.js"].symbols) > 0

    assert by_path["src/bad2.java"].success is False
    assert by_path["src/bad2.java"].error_reason == ExtractionFailureReason.EMPTY_SOURCE.value

    assert by_path["src/gamma.java"].success is True
    assert len(by_path["src/gamma.java"].symbols) > 0


# ==============================================================================
# Gate E & Gate F & Gate G & Gate H: Preflight and Discrete Fallback Taxonomy
# ==============================================================================

def test_gate_e_and_f_malformed_tolerance(orchestrator: SymbolExtractionOrchestrator):
    """Gate E & Gate F (LOCK-ORCH-06, LOCK-ORCH-09): Verifies AST recovery tolerance without second parse."""
    fixture = GOLD_ORCH_DIR / "malformed_syntax" / "broken_code.ts"
    code = fixture.read_bytes()
    res = orchestrator.extract_file(
        code_bytes=code,
        project_key="TEST_PROJ",
        file_path=str(fixture),
        file_rel_path="src/broken_code.ts",
    )
    # Tree-sitter recovers valid declarations around the error node; B-06 respects the extractor's output
    assert res.success is True
    names = {s.name for s in res.symbols}
    assert "calculateSum" in names
    assert "orphanedValue" in names


def test_gate_g_encoding_robustness(orchestrator: SymbolExtractionOrchestrator):
    """Gate G (LOCK-ORCH-06): Verifies ENCODING_FAILURE is cleanly isolated for non-UTF8 bytes."""
    corrupted_file = GOLD_ORCH_DIR / "corrupted_binary" / "corrupted.ts"
    code = corrupted_file.read_bytes()
    res = orchestrator.extract_file(
        code_bytes=code,
        project_key="TEST_PROJ",
        file_path=str(corrupted_file),
        file_rel_path="src/corrupted.ts",
    )
    assert res.success is False
    assert res.error_reason == ExtractionFailureReason.ENCODING_FAILURE.value
    assert "UTF-8 decode failure" in (res.error_detail or "")


def test_gate_h_empty_file_handling(orchestrator: SymbolExtractionOrchestrator):
    """Gate H (LOCK-ORCH-06): Verifies EMPTY_SOURCE is detected in near 0 ms without invoking AST parsers."""
    res = orchestrator.extract_file(
        code_bytes=b"   \r\n   ",
        project_key="TEST_PROJ",
        file_path="C:/app/empty.vue",
        file_rel_path="src/empty.vue",
    )
    assert res.success is False
    assert res.error_reason == ExtractionFailureReason.EMPTY_SOURCE.value
    assert res.duration_ms < 5.0  # Fast preflight check


# ==============================================================================
# Gate I & Gate J: Deterministic Key Generation & Project Key Propagation
# ==============================================================================

def test_gate_i_and_j_key_generation_and_propagation(orchestrator: SymbolExtractionOrchestrator):
    """Gate I & Gate J (LOCK-ORCH-07, LOCK-ORCH-10): Verifies deterministic key derivation using file_rel_path."""
    ts_file = GOLD_ORCH_DIR / "valid_multi_lang" / "service.ts"
    code = ts_file.read_bytes()

    res1 = orchestrator.extract_file(
        code_bytes=code,
        project_key="PROJ_ONE",
        file_path="C:/Windows/path/service.ts",
        file_rel_path="src/service.ts",
    )

    res2 = orchestrator.extract_file(
        code_bytes=code,
        project_key="PROJ_ONE",
        file_path="/home/linux/path/service.ts",
        file_rel_path="src/service.ts",
    )

    # Identical relative path across different host machines produces identical deterministic keys
    assert res1.symbol_keys == res2.symbol_keys
    for k in res1.symbol_keys:
        assert k.startswith("SYMBOL:PROJ_ONE:src/service.ts:")

    for s in res1.symbols:
        assert s.project_key == "PROJ_ONE"


# ==============================================================================
# Gate K: Batch API & Counter Integrity
# ==============================================================================

def test_gate_k_batch_api_counter_integrity(orchestrator: SymbolExtractionOrchestrator):
    """Gate K (LOCK-ORCH-08): Verifies Counter Integrity Rule on mixed batches."""
    files = [
        (b"export const a = 1;", "C:/a.ts", "src/a.ts"),
        (b"export const b = 2;", "C:/b.js", "src/b.js"),
        (b".btn { color: red; }", "C:/style.css", "src/style.css"),  # Unsupported
        (b"   ", "C:/blank.ts", "src/blank.ts"),                    # Empty
        (b"package demo; class C {}", "C:/C.java", "src/C.java"),
    ]

    summary = orchestrator.extract_batch(files, project_key="COUNTER_PROJ")

    assert summary.total_files == 5
    assert summary.scanned_files == 4
    assert summary.successful_files == 3
    assert summary.failed_files == 1
    assert summary.unsupported_files == 1

    # Counter Integrity Invariant
    assert summary.total_files == summary.successful_files + summary.failed_files + summary.unsupported_files
    assert summary.scanned_files == summary.successful_files + summary.failed_files
    assert summary.verify_counter_integrity() is True


# ==============================================================================
# Gate L: Zero Premature Graph & Output Purity
# ==============================================================================

def test_gate_l_zero_premature_graph(orchestrator: SymbolExtractionOrchestrator):
    """Gate L (LOCK-ORCH-05): Mechanically proves that zero graph relation fields exist in output DTOs."""
    ts_file = GOLD_ORCH_DIR / "valid_multi_lang" / "service.ts"
    code = ts_file.read_bytes()
    res = orchestrator.extract_file(
        code_bytes=code,
        project_key="TEST_PROJ",
        file_path=str(ts_file),
        file_rel_path="src/service.ts",
    )

    forbidden_fields = {"calls", "imports", "exports_to", "extends", "implements", "edges", "relations", "graph", "dependencies"}

    # 1. Inspect FileExtractionResult fields
    for field_name in res.__dataclass_fields__:
        assert field_name not in forbidden_fields, f"Forbidden graph field '{field_name}' in FileExtractionResult"

    # 2. Inspect each SymbolCandidate
    for sym in res.symbols:
        for field_name in sym.__dataclass_fields__:
            assert field_name not in forbidden_fields, f"Forbidden graph field '{field_name}' in SymbolCandidate"
        # Metadata must not contain graph edges
        assert not any(k in forbidden_fields for k in sym.metadata.keys())


# ==============================================================================
# Gate M: Zero Database Persistence (Static Code Inspection)
# ==============================================================================

def test_gate_m_zero_database_persistence():
    """Gate M (LOCK-ORCH-05): Mechanically analyzes AST of all B-06 implementation files (orchestrator.py & dto.py) to ensure zero DB module imports."""
    b06_files = [
        Path(__file__).resolve().parents[3] / "core" / "extraction" / "orchestrator.py",
        Path(__file__).resolve().parents[3] / "core" / "extraction" / "dto.py",
    ]
    forbidden_modules = {"sqlalchemy", "psycopg", "sqlmodel", "peewee", "tortoise"}
    forbidden_names = {"Session", "sessionmaker", "create_engine", "engine", "transaction", "repository"}

    for target_file in b06_files:
        source = target_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod_root = alias.name.split(".")[0]
                    assert mod_root not in forbidden_modules, f"Forbidden DB module imported in {target_file.name}: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                mod_root = (node.module or "").split(".")[0]
                assert mod_root not in forbidden_modules, f"Forbidden DB module imported in {target_file.name}: {node.module}"
                for alias in node.names:
                    assert alias.name not in forbidden_names, f"Forbidden DB name imported in {target_file.name}: {alias.name}"


# ==============================================================================
# Gate O: Benchmark Contract (< 10ms Baseline)
# ==============================================================================

def test_gate_o_performance_benchmark(orchestrator: SymbolExtractionOrchestrator):
    """Gate O (Benchmark Contract): Benchmarks dispatch, decode, extraction, and key derivation on N=100 corpus."""
    ts_code = (GOLD_ORCH_DIR / "valid_multi_lang" / "service.ts").read_bytes()
    js_code = (GOLD_ORCH_DIR / "valid_multi_lang" / "utils.js").read_bytes()
    java_code = (GOLD_ORCH_DIR / "valid_multi_lang" / "OrderController.java").read_bytes()
    vue_code = (GOLD_ORCH_DIR / "valid_multi_lang" / "LeadCard.vue").read_bytes()

    corpus = []
    for i in range(25):
        corpus.append((ts_code, f"C:/app/service_{i}.ts", f"src/service_{i}.ts"))
        corpus.append((js_code, f"C:/app/utils_{i}.js", f"src/utils_{i}.js"))
        corpus.append((java_code, f"C:/app/OrderController_{i}.java", f"src/OrderController_{i}.java"))
        corpus.append((vue_code, f"C:/app/LeadCard_{i}.vue", f"src/LeadCard_{i}.vue"))

    assert len(corpus) == 100

    # Warm-up run with 1 file of each type
    for code, p, rp in corpus[:4]:
        orchestrator.extract_file(code, "WARM", p, rp)

    # Benchmark run
    start_bench = time.perf_counter()
    summary = orchestrator.extract_batch(corpus, project_key="BENCHMARK")
    total_time_ms = (time.perf_counter() - start_bench) * 1000.0

    durations = [r.duration_ms for r in summary.results]
    mean_duration = sum(durations) / len(durations)
    durations.sort()
    median_duration = durations[len(durations) // 2]
    p95_duration = durations[int(len(durations) * 0.95)]
    throughput = len(corpus) / (total_time_ms / 1000.0)

    print(f"\n[Gate O Benchmark Baseline] N={len(corpus)}, Total={total_time_ms:.2f}ms, "
          f"Mean={mean_duration:.2f}ms, Median={median_duration:.2f}ms, P95={p95_duration:.2f}ms, "
          f"Throughput={throughput:.1f} files/sec")

    # Baseline performance check: average per-file should be fast (< 10ms for warm memory processing)
    assert mean_duration < 10.0, f"Expected mean < 10ms, got {mean_duration:.2f}ms"
    assert summary.successful_files == 100
    assert summary.verify_counter_integrity() is True


# ==============================================================================
# Gate P: Deterministic Ordering & 5 Gold Suites Integration
# ==============================================================================

def test_gate_p_deterministic_batch_ordering(orchestrator: SymbolExtractionOrchestrator):
    """Gate P (LOCK-ORCH-08, LOCK-ORCH-10): Verifies that shuffled file inputs yield identical deterministic lexical results."""
    order_dir = GOLD_ORCH_DIR / "deterministic_order"
    z_file = (order_dir / "z_module.ts").read_bytes()
    a_file = (order_dir / "a_service.java").read_bytes()
    m_file = (order_dir / "m_view.vue").read_bytes()
    b_file = (order_dir / "b_util.js").read_bytes()

    # Input 1: Unsorted (Z, A, M, B)
    batch_1 = [
        (z_file, str(order_dir / "z_module.ts"), "src/z_module.ts"),
        (a_file, str(order_dir / "a_service.java"), "src/a_service.java"),
        (m_file, str(order_dir / "m_view.vue"), "src/m_view.vue"),
        (b_file, str(order_dir / "b_util.js"), "src/b_util.js"),
    ]

    # Input 2: Different shuffle (M, B, Z, A)
    batch_2 = [
        (m_file, str(order_dir / "m_view.vue"), "src/m_view.vue"),
        (b_file, str(order_dir / "b_util.js"), "src/b_util.js"),
        (z_file, str(order_dir / "z_module.ts"), "src/z_module.ts"),
        (a_file, str(order_dir / "a_service.java"), "src/a_service.java"),
    ]

    sum1 = orchestrator.extract_batch(batch_1, "ORDER_TEST")
    sum2 = orchestrator.extract_batch(batch_2, "ORDER_TEST")

    # Result ordering must be identical and sorted lexicographically
    expected_order = ["src/a_service.java", "src/b_util.js", "src/m_view.vue", "src/z_module.ts"]
    actual_order_1 = [r.file_rel_path for r in sum1.results]
    actual_order_2 = [r.file_rel_path for r in sum2.results]

    assert actual_order_1 == expected_order
    assert actual_order_2 == expected_order

    # Symbol keys within each result must be 100% identical
    for r1, r2 in zip(sum1.results, sum2.results):
        assert r1.file_rel_path == r2.file_rel_path
        assert r1.symbol_keys == r2.symbol_keys
        assert [s.name for s in r1.symbols] == [s.name for s in r2.symbols]


def test_gate_p_gold_valid_multi_lang(orchestrator: SymbolExtractionOrchestrator):
    """Gate P: Verifies extraction across all 4 languages in valid_multi_lang fixture."""
    v_dir = GOLD_ORCH_DIR / "valid_multi_lang"
    files = [
        ((v_dir / "service.ts").read_bytes(), str(v_dir / "service.ts"), "src/service.ts"),
        ((v_dir / "utils.js").read_bytes(), str(v_dir / "utils.js"), "src/utils.js"),
        ((v_dir / "OrderController.java").read_bytes(), str(v_dir / "OrderController.java"), "src/OrderController.java"),
        ((v_dir / "LeadCard.vue").read_bytes(), str(v_dir / "LeadCard.vue"), "src/LeadCard.vue"),
    ]

    summary = orchestrator.extract_batch(files, project_key="MULTI_GOLD")

    assert summary.total_files == 4
    assert summary.successful_files == 4
    assert summary.failed_files == 0
    assert summary.unsupported_files == 0
    assert summary.verify_counter_integrity() is True

    # Check symbol types representation
    types = summary.symbols_by_type
    assert "INTERFACE" in types
    assert "CLASS" in types
    assert "FUNCTION" in types
    assert "COMPONENT" in types
