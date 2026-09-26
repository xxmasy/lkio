"""C-05 Intra-Project Symbol Resolver Tests
Validates:
- Gate P: TS/JS relative & alias module resolution
- Gate Q: Java same-package & imported class hierarchy resolution
- Gate R: Identity stability under resolution (LOCK-GRAPH-10 bit-for-bit equality)
- Intra-project boundary enforcement (LOCK-GRAPH-06 external dependencies stay UNRESOLVED)
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
from core.graph.resolver import IntraProjectSymbolResolver, ResolverContext


@pytest.fixture
def resolver_context():
    ctx = ResolverContext(project_key="TEST_FE")
    # Register files
    ctx.register_file("src/service/UserService.ts", "FILE:TEST_FE:src/service/UserService.ts")
    ctx.register_file("src/utils/logger.ts", "FILE:TEST_FE:src/utils/logger.ts")
    ctx.register_file("src/components/Button.vue", "FILE:TEST_FE:src/components/Button.vue")
    ctx.register_file("src/api/client/index.ts", "FILE:TEST_FE:src/api/client/index.ts")

    # Register symbols
    ctx.register_symbol(
        entity_key="SYMBOL:TEST_FE:src/utils/logger.ts:FUNCTION:logInfo:e3b0c44298fc1c14",
        file_rel_path="src/utils/logger.ts",
        symbol_name="logInfo",
    )
    return ctx


@pytest.fixture
def java_resolver_context():
    ctx = ResolverContext(project_key="TEST_BE")
    ctx.register_file(
        "src/main/java/org/example/service/OrderService.java",
        "FILE:TEST_BE:src/main/java/org/example/service/OrderService.java",
    )
    ctx.register_file(
        "src/main/java/org/example/service/BaseService.java",
        "FILE:TEST_BE:src/main/java/org/example/service/BaseService.java",
    )
    ctx.register_symbol(
        entity_key="SYMBOL:TEST_BE:src/main/java/org/example/service/BaseService.java:CLASS:BaseService:e3b0c44298fc1c14",
        file_rel_path="src/main/java/org/example/service/BaseService.java",
        symbol_name="BaseService",
        package_name="org.example.service",
    )
    ctx.register_symbol(
        entity_key="SYMBOL:TEST_BE:src/main/java/org/example/service/OrderService.java:INTERFACE:OrderService:e3b0c44298fc1c14",
        file_rel_path="src/main/java/org/example/service/OrderService.java",
        symbol_name="OrderService",
        package_name="org.example.service",
    )
    return ctx


def test_gate_p_ts_js_relative_and_alias_resolution(resolver_context):
    """Gate P: Resolves relative and alias import paths to concrete file entity keys."""
    resolver = IntraProjectSymbolResolver(resolver_context)

    cands = [
        # Relative import ./logger from src/service/UserService.ts
        RelationCandidate(
            project_key="TEST_FE",
            subject_entity_key="FILE:TEST_FE:src/service/UserService.ts",
            predicate=RelationPredicate.IMPORTS,
            normalized_raw_target="../utils/logger",
            relation_kind=RelationKind.STATIC,
            confidence=Decimal("1.00000"),
            resolution_status=ResolutionStatus.UNRESOLVED,
            occurrences=(SourceOccurrence(line=1, column=0),),
            source_file_rel_path="src/service/UserService.ts",
        ),
        # Alias import @/components/Button from src/service/UserService.ts
        RelationCandidate(
            project_key="TEST_FE",
            subject_entity_key="FILE:TEST_FE:src/service/UserService.ts",
            predicate=RelationPredicate.IMPORTS,
            normalized_raw_target="@/components/Button",
            relation_kind=RelationKind.STATIC,
            confidence=Decimal("1.00000"),
            resolution_status=ResolutionStatus.UNRESOLVED,
            occurrences=(SourceOccurrence(line=2, column=0),),
            source_file_rel_path="src/service/UserService.ts",
        ),
        # External library import (e.g. lodash)
        RelationCandidate(
            project_key="TEST_FE",
            subject_entity_key="FILE:TEST_FE:src/service/UserService.ts",
            predicate=RelationPredicate.IMPORTS,
            normalized_raw_target="lodash",
            relation_kind=RelationKind.STATIC,
            confidence=Decimal("1.00000"),
            resolution_status=ResolutionStatus.UNRESOLVED,
            occurrences=(SourceOccurrence(line=3, column=0),),
            source_file_rel_path="src/service/UserService.ts",
        ),
    ]

    resolved = resolver.resolve_candidates(cands)
    assert len(resolved) == 3

    # Candidate 1: relative
    assert resolved[0].resolution_status == ResolutionStatus.RESOLVED
    assert resolved[0].object_entity_key == "FILE:TEST_FE:src/utils/logger.ts"

    # Candidate 2: alias
    assert resolved[1].resolution_status == ResolutionStatus.RESOLVED
    assert resolved[1].object_entity_key == "FILE:TEST_FE:src/components/Button.vue"

    # Candidate 3: external library stays UNRESOLVED (LOCK-GRAPH-06)
    assert resolved[2].resolution_status == ResolutionStatus.UNRESOLVED
    assert resolved[2].object_entity_key is None


def test_gate_q_java_hierarchy_resolution(java_resolver_context):
    """Gate Q: Resolves Java class and interface hierarchy targets to internal symbols."""
    resolver = IntraProjectSymbolResolver(java_resolver_context)

    cand = RelationCandidate(
        project_key="TEST_BE",
        subject_entity_key="SYMBOL:TEST_BE:src/main/java/org/example/service/OrderServiceImpl.java:CLASS:OrderServiceImpl:e3b0c44298fc1c14",
        predicate=RelationPredicate.EXTENDS,
        normalized_raw_target="BaseService",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=5, column=30),),
        source_file_rel_path="src/main/java/org/example/service/OrderServiceImpl.java",
    )

    resolved = resolver.resolve_candidates([cand])
    assert len(resolved) == 1
    assert resolved[0].resolution_status == ResolutionStatus.RESOLVED
    assert resolved[0].object_entity_key == "SYMBOL:TEST_BE:src/main/java/org/example/service/BaseService.java:CLASS:BaseService:e3b0c44298fc1c14"


def test_gate_r_identity_stability_under_resolution(resolver_context):
    """Gate R: relation_key must remain bit-for-bit identical before and after resolution (LOCK-GRAPH-10)."""
    resolver = IntraProjectSymbolResolver(resolver_context)

    unresolved_cand = RelationCandidate(
        project_key="TEST_FE",
        subject_entity_key="FILE:TEST_FE:src/service/UserService.ts",
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="../utils/logger",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=1, column=0),),
        source_file_rel_path="src/service/UserService.ts",
    )
    initial_key = unresolved_cand.relation_key

    resolved_list = resolver.resolve_candidates([unresolved_cand])
    resolved_cand = resolved_list[0]

    assert resolved_cand.resolution_status == ResolutionStatus.RESOLVED
    assert resolved_cand.object_entity_key == "FILE:TEST_FE:src/utils/logger.ts"
    # Bit-for-bit invariance proof
    assert resolved_cand.relation_key == initial_key
    assert resolved_cand.relation_key == (
        f"RELATION:TEST_FE:FILE:TEST_FE:src/service/UserService.ts:imports:../utils/logger:STATIC:default"
    )
