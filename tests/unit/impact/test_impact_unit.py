"""Unit tests for MVP7 Impact Analysis Engine in core/impact/
"""

import pytest
from core.impact import (
    EvidenceKind,
    FullStackImpactPropagator,
    HumanReviewFlow,
    ImpactAnalysisEngine,
    ImpactGraphTraversal,
    ImpactHopLevel,
)


@pytest.fixture
def sample_graph():
    entities = {
        "COMP:HELLO_FE:AdSetup": {
            "name": "AdSetup.vue",
            "entity_type": "PAGE",
            "project_key": "HELLO_FE",
            "path": "src/views/ads/components/AdSetup.vue",
        },
        "API:HELLO_FE:leadApi": {
            "name": "leadApi.ts",
            "entity_type": "API",
            "project_key": "HELLO_FE",
            "path": "src/api/leadApi.ts",
        },
        "CONTROLLER:HELLO_BE:LeadController": {
            "name": "LeadController.java",
            "entity_type": "CONTROLLER",
            "project_key": "HELLO_BE",
            "path": "src/main/java/org/example/hahamarket/controller/LeadController.java",
        },
        "SERVICE:HELLO_BE:LeadService": {
            "name": "LeadService.java",
            "entity_type": "SERVICE",
            "project_key": "HELLO_BE",
            "path": "src/main/java/org/example/hahamarket/service/LeadService.java",
        },
        "RULE:HELLO_BE:ConversionRule": {
            "name": "ConversionRule",
            "entity_type": "BUSINESS_RULE",
            "project_key": "HELLO_BE",
            "path": "src/main/java/org/example/hahamarket/rule/ConversionRule.java",
        },
    }

    relations = [
        # AdSetup.vue imports leadApi.ts
        {"subject_key": "COMP:HELLO_FE:AdSetup", "object_key": "API:HELLO_FE:leadApi", "relation_type": "IMPORTS", "confidence": 1.0},
        # leadApi.ts calls LeadController.java (cross-project)
        {"subject_key": "API:HELLO_FE:leadApi", "object_key": "CONTROLLER:HELLO_BE:LeadController", "relation_type": "API_CALLS", "confidence": 0.95},
        # LeadController calls LeadService
        {"subject_key": "CONTROLLER:HELLO_BE:LeadController", "object_key": "SERVICE:HELLO_BE:LeadService", "relation_type": "CALLS", "confidence": 1.0},
        # LeadService implements ConversionRule
        {"subject_key": "SERVICE:HELLO_BE:LeadService", "object_key": "RULE:HELLO_BE:ConversionRule", "relation_type": "IMPLEMENTS", "confidence": 1.0},
    ]

    return entities, relations


def test_multi_hop_traversal(sample_graph):
    entities, relations = sample_graph
    traversal = ImpactGraphTraversal(max_depth=3)

    # When LeadController changes, find who is affected upstream/downstream
    nodes, paths = traversal.traverse(
        seed_keys=["CONTROLLER:HELLO_BE:LeadController"],
        entities_by_key=entities,
        relations=relations,
        direction="both",
    )

    node_keys = {n.entity_key for n in nodes}
    assert "API:HELLO_FE:leadApi" in node_keys
    assert "SERVICE:HELLO_BE:LeadService" in node_keys
    assert "COMP:HELLO_FE:AdSetup" in node_keys

    # Check 1-hop DIRECT
    api_node = next(n for n in nodes if n.entity_key == "API:HELLO_FE:leadApi")
    assert api_node.hop == 1
    assert api_node.level == ImpactHopLevel.DIRECT

    # Check 2-hop INDIRECT
    adsetup_node = next(n for n in nodes if n.entity_key == "COMP:HELLO_FE:AdSetup")
    assert adsetup_node.hop == 2
    assert adsetup_node.level == ImpactHopLevel.INDIRECT


def test_cycle_safety():
    """Confirms traversal does not loop infinitely or overflow max_depth on circular dependencies."""
    entities = {
        "A": {"name": "A", "entity_type": "CLASS", "project_key": "P"},
        "B": {"name": "B", "entity_type": "CLASS", "project_key": "P"},
        "C": {"name": "C", "entity_type": "CLASS", "project_key": "P"},
    }
    # Cycle: A -> B -> C -> A
    relations = [
        {"subject_key": "A", "object_key": "B", "relation_type": "CALLS"},
        {"subject_key": "B", "object_key": "C", "relation_type": "CALLS"},
        {"subject_key": "C", "object_key": "A", "relation_type": "CALLS"},
    ]

    traversal = ImpactGraphTraversal(max_depth=3)
    nodes, paths = traversal.traverse(seed_keys=["A"], entities_by_key=entities, relations=relations)

    assert len(nodes) == 2  # B and C
    for p in paths:
        assert p.hops <= 3


def test_empty_and_disconnected_graphs():
    traversal = ImpactGraphTraversal(max_depth=3)
    nodes, paths = traversal.traverse(
        seed_keys=["UNKNOWN_KEY"],
        entities_by_key={},
        relations=[],
    )
    assert len(nodes) == 0
    assert len(paths) == 0

    propagator = FullStackImpactPropagator()
    report = propagator.propagate(seed_keys=["UNKNOWN_KEY"], affected_nodes=[], impact_paths=[])
    assert report.overall_impact_level == "NONE"
    assert report.requires_human_review is False


def test_depth_limiting():
    entities = {f"N{i}": {"name": f"N{i}", "entity_type": "CLASS", "project_key": "P"} for i in range(6)}
    # Linear chain: N0 -> N1 -> N2 -> N3 -> N4 -> N5
    relations = [
        {"subject_key": f"N{i}", "object_key": f"N{i+1}", "relation_type": "CALLS"}
        for i in range(5)
    ]

    # Limit to max_depth=1
    traversal_1 = ImpactGraphTraversal(max_depth=1)
    nodes_1, _ = traversal_1.traverse(seed_keys=["N0"], entities_by_key=entities, relations=relations, direction="upstream")
    assert len(nodes_1) == 1
    assert nodes_1[0].entity_key == "N1"

    # Default max_depth=3 (cannot exceed 3 by architecture lock)
    traversal_3 = ImpactGraphTraversal(max_depth=3)
    nodes_3, _ = traversal_3.traverse(seed_keys=["N0"], entities_by_key=entities, relations=relations, direction="upstream")
    assert len(nodes_3) == 3
    node_keys = {n.entity_key for n in nodes_3}
    assert node_keys == {"N1", "N2", "N3"}
    assert "N4" not in node_keys


def test_end_to_end_impact_analysis(sample_graph):
    entities, relations = sample_graph
    engine = ImpactAnalysisEngine()

    # Changing LeadService in backend
    report = engine.analyze_impact(
        seed_keys=["SERVICE:HELLO_BE:LeadService"],
        entities_by_key=entities,
        relations=relations,
        direction="both",
    )

    assert "HELLO_FE" in report.affected_projects
    assert "HELLO_BE" in report.affected_projects
    assert len(report.affected_apis) > 0
    assert len(report.affected_business_rules) > 0
    assert report.overall_impact_level in ("HIGH", "CRITICAL")
    assert report.requires_human_review is True

    # Check paths
    assert report.shortest_path is not None
    assert report.critical_path is not None
    assert "-->" in report.critical_path.description

    # Check Human Review Payload
    checklist = engine.generate_review_checklist(report)
    assert checklist["status"] == "REQUIRES_HUMAN_REVIEW"
    assert len(checklist["recommended_actions"]) >= 2
    assert "HELLO_FE" in checklist["scope"]["affected_projects"]
