"""C-03 Static Hierarchy Relations Extractor Tests
Validates:
- Gate J: Java class extends and multiple implements extraction
- Gate K: Java interface multiple extends extraction
- Gate L: TypeScript class extends/implements and interface extends extraction
"""

from decimal import Decimal
import pytest

from core.graph.extractors.hierarchy_relations import HierarchyRelationExtractor
from core.graph.models import RelationKind, RelationPredicate, ResolutionStatus
from core.extraction.normalizer import EMPTY_SIGNATURE_DISCRIMINATOR


@pytest.fixture
def extractor():
    return HierarchyRelationExtractor()


def test_gate_j_java_class_hierarchy(extractor):
    """Gate J: Java class extends and implements extraction."""
    code = b"""
package org.example.service;

public class OrderServiceImpl extends BaseServiceImpl implements OrderService, Auditable {
    public void process() {}
}
"""
    results = extractor.extract_from_code(
        code_bytes=code,
        language="java",
        project_key="TEST_BE",
        file_rel_path="src/main/java/org/example/service/OrderServiceImpl.java",
    )

    assert len(results) == 3
    extends_rel = [r for r in results if r.predicate == RelationPredicate.EXTENDS]
    implements_rel = [r for r in results if r.predicate == RelationPredicate.IMPLEMENTS]

    assert len(extends_rel) == 1
    assert extends_rel[0].normalized_raw_target == "BaseServiceImpl"
    assert extends_rel[0].relation_kind == RelationKind.STATIC
    assert extends_rel[0].confidence == Decimal("1.00000")
    assert extends_rel[0].resolution_status == ResolutionStatus.UNRESOLVED
    assert extends_rel[0].subject_entity_key == f"SYMBOL:TEST_BE:src/main/java/org/example/service/OrderServiceImpl.java:CLASS:OrderServiceImpl:{EMPTY_SIGNATURE_DISCRIMINATOR}"

    assert len(implements_rel) == 2
    targets = {r.normalized_raw_target for r in implements_rel}
    assert targets == {"OrderService", "Auditable"}


def test_gate_k_java_interface_hierarchy(extractor):
    """Gate K: Java interface multiple extends extraction."""
    code = b"""
package org.example.service;

public interface OrderService extends BaseService, Serializable {
}
"""
    results = extractor.extract_from_code(
        code_bytes=code,
        language="java",
        project_key="TEST_BE",
        file_rel_path="src/main/java/org/example/service/OrderService.java",
    )

    assert len(results) == 2
    targets = {r.normalized_raw_target for r in results}
    assert targets == {"BaseService", "Serializable"}
    assert all(r.predicate == RelationPredicate.EXTENDS for r in results)
    assert all(r.subject_entity_key == f"SYMBOL:TEST_BE:src/main/java/org/example/service/OrderService.java:INTERFACE:OrderService:{EMPTY_SIGNATURE_DISCRIMINATOR}" for r in results)


def test_gate_l_typescript_hierarchy(extractor):
    """Gate L: TypeScript class and interface hierarchy extraction."""
    code = b"""
export interface ComponentProps extends BaseProps, ThemeProps {
    id: string;
}

export class CustomWidget extends BaseWidget implements Renderable, Disposable {
    render() {}
}
"""
    results = extractor.extract_from_code(
        code_bytes=code,
        language="typescript",
        project_key="TEST_FE",
        file_rel_path="src/widgets/CustomWidget.ts",
    )

    assert len(results) == 5

    # Interface extends
    iface_rels = [r for r in results if ":INTERFACE:ComponentProps:" in r.subject_entity_key]
    assert len(iface_rels) == 2
    assert {r.normalized_raw_target for r in iface_rels} == {"BaseProps", "ThemeProps"}
    assert all(r.predicate == RelationPredicate.EXTENDS for r in iface_rels)

    # Class extends & implements
    class_rels = [r for r in results if ":CLASS:CustomWidget:" in r.subject_entity_key]
    assert len(class_rels) == 3
    ext = [r for r in class_rels if r.predicate == RelationPredicate.EXTENDS]
    imp = [r for r in class_rels if r.predicate == RelationPredicate.IMPLEMENTS]

    assert len(ext) == 1
    assert ext[0].normalized_raw_target == "BaseWidget"
    assert len(imp) == 2
    assert {r.normalized_raw_target for r in imp} == {"Renderable", "Disposable"}
