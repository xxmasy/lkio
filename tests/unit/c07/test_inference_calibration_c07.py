"""C-07 Inferred Relations & Confidence Calibration Tests
Validates:
- Gate V: Polymorphic interface call expansion (confidence = 1.0 / N, relation_kind = INFERRED)
- Gate W: Static vs Inferred discriminator and distinct relation_keys (LOCK-GRAPH-03)
- Gate X: Confidence monotonicity and calibration policy bounds (LOCK-GRAPH-07)
"""

from decimal import Decimal
import pytest

from core.graph.inference import InferenceCalibrationEngine
from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
    SourceOccurrence,
)


@pytest.fixture
def engine():
    return InferenceCalibrationEngine()


def test_gate_v_polymorphic_dispatch_expansion(engine):
    """Gate V: Expands static interface call into N inferred dispatch candidates with 1.0/N confidence."""
    static_call = RelationCandidate(
        project_key="TEST_BE",
        subject_entity_key="SYMBOL:TEST_BE:src/service/Client.java:METHOD:run:e3b0c44298fc1c14",
        predicate=RelationPredicate.CALLS,
        normalized_raw_target="orderService.process",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=15, column=8),),
        source_file_rel_path="src/service/Client.java",
    )

    implementations = [
        {"symbol_key": "SYMBOL:TEST_BE:src/impl/OrderServiceFast.java:METHOD:process:e3b0c44298fc1c14"},
        {"symbol_key": "SYMBOL:TEST_BE:src/impl/OrderServiceStandard.java:METHOD:process:e3b0c44298fc1c14"},
    ]

    inferred_list = engine.expand_polymorphic_dispatch(static_call, implementations)
    assert len(inferred_list) == 2

    for c in inferred_list:
        assert c.relation_kind == RelationKind.INFERRED
        assert c.confidence == Decimal("0.50000")  # 1.0 / 2
        assert c.resolution_status == ResolutionStatus.RESOLVED
        assert c.predicate == RelationPredicate.CALLS
        assert c.occurrences == static_call.occurrences

    # Single implementation test
    single_impl = [implementations[0]]
    single_inferred = engine.expand_polymorphic_dispatch(static_call, single_impl)
    assert len(single_inferred) == 1
    assert single_inferred[0].confidence == Decimal("0.90000")


def test_gate_w_static_vs_inferred_discriminator(engine):
    """Gate W: Static call and inferred call candidates have distinct discriminators and keys (LOCK-GRAPH-03)."""
    static_call = RelationCandidate(
        project_key="TEST_BE",
        subject_entity_key="SYMBOL:TEST_BE:src/service/Client.java:METHOD:run:e3b0c44298fc1c14",
        predicate=RelationPredicate.CALLS,
        normalized_raw_target="orderService.process",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=15, column=8),),
        source_file_rel_path="src/service/Client.java",
    )

    implementations = [
        {"symbol_key": "SYMBOL:TEST_BE:src/impl/OrderServiceImpl.java:METHOD:process:e3b0c44298fc1c14"}
    ]
    inferred_list = engine.expand_polymorphic_dispatch(static_call, implementations)
    inferred = inferred_list[0]

    assert static_call.relation_kind == RelationKind.STATIC
    assert inferred.relation_kind == RelationKind.INFERRED

    # Prove relation keys are distinct
    assert static_call.relation_key != inferred.relation_key
    assert ":STATIC:default" in static_call.relation_key
    assert ":INFERRED:dispatch_0" in inferred.relation_key


def test_gate_x_confidence_monotonicity_and_bounds(engine):
    """Gate X: Confidence strictly <= 1.00000; inferred confidence strictly < 1.00000 (LOCK-GRAPH-07)."""
    framework_c = engine.create_framework_convention_relation(
        project_key="TEST_FE",
        subject_entity_key="FILE:TEST_FE:src/views/Home.vue",
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="@/components/Header",
        object_entity_key="FILE:TEST_FE:src/components/Header.vue",
        source_file_rel_path="src/views/Home.vue",
        convention_name="vue_sfc_template",
    )

    assert framework_c.relation_kind == RelationKind.INFERRED
    assert framework_c.confidence == Decimal("0.70000")
    assert framework_c.confidence < Decimal("1.00000")
    assert framework_c.confidence > Decimal("0.00000")
    assert ":INFERRED:convention_vue_sfc_template" in framework_c.relation_key
