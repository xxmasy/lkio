"""C-01 RelationCandidate DTO & Identity Subsystem Tests
Validates:
- Gate D: Strongly-typed enum creation and deterministic relation_key calculation
- Gate E: LOCK-GRAPH-10 Resolution Identity Stability (UNRESOLVED -> RESOLVED key invariance)
- Gate F: LOCK-GRAPH-09 SourceOccurrence value object and evidence preservation
"""

from decimal import Decimal
import pytest

from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
    SourceOccurrence,
)


def test_gate_d_relation_candidate_and_key():
    """Gate D: RelationCandidate produces deterministic relation_key."""
    cand = RelationCandidate(
        project_key="HELLO_FE",
        subject_entity_key="FILE:HELLO_FE:src/views/User.vue",
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="@/store/user",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        source_file_rel_path="src/views/User.vue",
    )

    expected_key = "RELATION:HELLO_FE:FILE:HELLO_FE:src/views/User.vue:imports:@/store/user:STATIC:default"
    assert cand.relation_key == expected_key
    assert cand.predicate == RelationPredicate.IMPORTS
    assert cand.relation_kind == RelationKind.STATIC
    assert cand.resolution_status == ResolutionStatus.UNRESOLVED


def test_gate_e_resolution_identity_stability():
    """Gate E (LOCK-GRAPH-10): Resolution status change must NOT mutate relation_key."""
    unresolved_cand = RelationCandidate(
        project_key="HELLO_BE",
        subject_entity_key="SYMBOL:HELLO_BE:OrderService.java:CLASS:OrderService:1234",
        predicate=RelationPredicate.IMPLEMENTS,
        normalized_raw_target="BaseService",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        object_entity_key=None,
    )
    original_key = unresolved_cand.relation_key

    # Resolve to known target entity
    resolved_cand = unresolved_cand.with_resolution("SYMBOL:HELLO_BE:BaseService.java:INTERFACE:BaseService:5678")

    assert resolved_cand.resolution_status == ResolutionStatus.RESOLVED
    assert resolved_cand.object_entity_key == "SYMBOL:HELLO_BE:BaseService.java:INTERFACE:BaseService:5678"
    # KEY INVARIANCE: relation_key MUST remain 100% identical!
    assert resolved_cand.relation_key == original_key


def test_gate_f_occurrence_preservation_and_immutability():
    """Gate F (LOCK-GRAPH-09): Multiple call occurrences attached to single edge without key mutation."""
    occ1 = SourceOccurrence(line=10, column=4, argument_count=2, snippet_hint="calc(a, b)")
    occ2 = SourceOccurrence(line=15, column=4, argument_count=2, snippet_hint="calc(c, d)")

    cand = RelationCandidate(
        project_key="HELLO_BE",
        subject_entity_key="SYMBOL:HELLO_BE:Controller.java:METHOD:run:1111",
        predicate=RelationPredicate.CALLS,
        normalized_raw_target="service.calc",
        relation_kind=RelationKind.STATIC,
        occurrences=(occ1, occ2),
    )

    assert len(cand.occurrences) == 2
    assert cand.occurrences[0].line == 10
    assert cand.occurrences[1].line == 15
    assert cand.occurrences[0].to_dict() == {"line": 10, "column": 4, "argument_count": 2, "snippet_hint": "calc(a, b)"}

    # Frozen immutability check
    with pytest.raises(Exception):
        cand.project_key = "MUTATED"
