"""C-06 Invocation Relations Extractor Tests
Validates:
- Gate S: TS/JS call expression extraction and enclosing function subject derivation
- Gate T: Java method invocation & constructor (new Order()) extraction
- Gate U: Occurrence aggregation across multiple calls to same callee in single function body (LOCK-GRAPH-09)
"""

from decimal import Decimal
import pytest

from core.extraction.normalizer import EMPTY_SIGNATURE_DISCRIMINATOR
from core.graph.extractors.call_relations import InvocationRelationExtractor
from core.graph.models import RelationKind, RelationPredicate, ResolutionStatus


@pytest.fixture
def extractor():
    return InvocationRelationExtractor()


def test_gate_s_ts_js_call_extraction(extractor):
    """Gate S: Extracts TS/JS calls with correct enclosing function subject."""
    code = b"""
import { logInfo } from './logger';

export function processOrder(orderId: string) {
    logInfo("Processing order: " + orderId);
    validate(orderId);
}
"""
    results = extractor.extract_from_code(
        code_bytes=code,
        language="typescript",
        project_key="TEST_FE",
        file_rel_path="src/service/order.ts",
    )

    targets = {r.normalized_raw_target for r in results}
    assert "logInfo" in targets
    assert "validate" in targets

    for r in results:
        assert r.predicate == RelationPredicate.CALLS
        assert r.relation_kind == RelationKind.STATIC
        assert r.confidence == Decimal("1.00000")
        assert r.resolution_status == ResolutionStatus.UNRESOLVED
        assert r.subject_entity_key == (
            f"SYMBOL:TEST_FE:src/service/order.ts:FUNCTION:processOrder:{EMPTY_SIGNATURE_DISCRIMINATOR}"
        )


def test_gate_t_java_invocation_and_constructor(extractor):
    """Gate T: Extracts Java method invocations and new expressions."""
    code = b"""
package org.example.service;

public class OrderService {
    public void execute() {
        Order order = new Order("ORD-123");
        this.save(order);
        System.out.println("Done");
    }
}
"""
    results = extractor.extract_from_code(
        code_bytes=code,
        language="java",
        project_key="TEST_BE",
        file_rel_path="src/main/java/org/example/service/OrderService.java",
    )

    targets = {r.normalized_raw_target for r in results}
    assert "Order" in targets  # constructor
    assert "this.save" in targets  # method invocation
    assert "System.out.println" in targets  # chained method invocation

    expected_subject = (
        f"SYMBOL:TEST_BE:src/main/java/org/example/service/OrderService.java:METHOD:OrderService.execute:{EMPTY_SIGNATURE_DISCRIMINATOR}"
    )
    for r in results:
        assert r.subject_entity_key == expected_subject
        assert r.predicate == RelationPredicate.CALLS


def test_gate_u_occurrence_aggregation_for_repeated_calls(extractor):
    """Gate U: Aggregates multiple calls to the same callee into a single RelationCandidate (LOCK-GRAPH-09)."""
    code = b"""
export function runBatch() {
    notify("step 1");
    doWork();
    notify("step 2");
    notify("step 3");
}
"""
    results = extractor.extract_from_code(
        code_bytes=code,
        language="typescript",
        project_key="TEST_FE",
        file_rel_path="src/batch.ts",
    )

    # We have 3 calls to notify, 1 call to doWork
    # Should result in strictly 2 unique RelationCandidate edges
    assert len(results) == 2
    notify_rel = next(r for r in results if r.normalized_raw_target == "notify")
    dowork_rel = next(r for r in results if r.normalized_raw_target == "doWork")

    assert len(notify_rel.occurrences) == 3
    # Check lines of the 3 occurrences
    lines = [occ.line for occ in notify_rel.occurrences]
    assert lines == [3, 5, 6]

    assert len(dowork_rel.occurrences) == 1
    assert dowork_rel.occurrences[0].line == 4
