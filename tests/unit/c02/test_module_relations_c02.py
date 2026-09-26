"""C-02 Static Module Relations Extractor Tests
Validates:
- Gate G: TS/JS explicit imports, re-exports, type-only flags, and occurrence preservation
- Gate H: Java single-type, wildcard, and static import extraction
- Gate I: Vue SFC script imports and template component references preservation
"""

from decimal import Decimal
import pytest

from core.graph.extractors.module_relations import ModuleRelationExtractor
from core.graph.models import RelationKind, RelationPredicate, ResolutionStatus


@pytest.fixture
def extractor():
    return ModuleRelationExtractor()


def test_gate_g_ts_js_module_relations(extractor):
    """Gate G: TS/JS explicit imports and re-exports extraction."""
    code = b"""
import { ref, computed as c } from 'vue';
import type { User } from './types';
import * as Path from 'path';
import './global.css';

export { Helper } from './helper';
"""
    results = extractor.extract_from_code(
        code_bytes=code,
        language="typescript",
        project_key="TEST_FE",
        file_rel_path="src/components/MyComp.ts",
    )

    by_target = {r.normalized_raw_target: r for r in results}
    assert "vue" in by_target
    assert "./types" in by_target
    assert "path" in by_target
    assert "./global.css" in by_target
    assert "./helper" in by_target

    # Verify 'vue' import
    vue_rel = by_target["vue"]
    assert vue_rel.predicate == RelationPredicate.IMPORTS
    assert vue_rel.relation_kind == RelationKind.STATIC
    assert vue_rel.confidence == Decimal("1.00000")
    assert vue_rel.resolution_status == ResolutionStatus.UNRESOLVED
    assert vue_rel.subject_entity_key == "FILE:TEST_FE:src/components/MyComp.ts"
    specs = vue_rel.metadata["import_specifiers"]
    assert any(s["imported"] == "ref" and s["local"] == "ref" for s in specs)
    assert any(s["imported"] == "computed" and s["local"] == "c" for s in specs)

    # Verify type-only
    type_rel = by_target["./types"]
    assert type_rel.metadata["is_type_only"] is True

    # Verify re-export
    helper_rel = by_target["./helper"]
    assert helper_rel.predicate == RelationPredicate.EXPORTS
    assert helper_rel.metadata["is_reexport"] is True


def test_gate_h_java_module_relations(extractor):
    """Gate H: Java import statements (single-type, wildcard, static)."""
    code = b"""
package org.example.service;

import java.util.List;
import java.util.Map;
import org.springframework.stereotype.*;
import static org.example.Constants.TIMEOUT;

public class MyService {}
"""
    results = extractor.extract_from_code(
        code_bytes=code,
        language="java",
        project_key="TEST_BE",
        file_rel_path="src/main/java/org/example/service/MyService.java",
    )

    targets = {r.normalized_raw_target: r for r in results}
    assert "java.util.List" in targets
    assert "java.util.Map" in targets
    assert "org.springframework.stereotype.*" in targets
    assert "org.example.Constants.TIMEOUT" in targets

    wildcard_rel = targets["org.springframework.stereotype.*"]
    assert wildcard_rel.metadata["is_wildcard"] is True

    static_rel = targets["org.example.Constants.TIMEOUT"]
    assert static_rel.metadata["is_static"] is True


def test_gate_i_vue_sfc_module_relations(extractor):
    """Gate I: Vue SFC imports and template references integration."""
    vue_code = b"""
<template>
  <div class="user-profile">
    <UserCard :id="1" />
    <user-badge />
  </div>
</template>

<script setup lang="ts">
import UserCard from './UserCard.vue';
import UserBadge from '@/components/UserBadge.vue';
import { useAuth } from '@/store/auth';
</script>
"""
    results = extractor.extract_from_code(
        code_bytes=vue_code,
        language="vue",
        project_key="TEST_FE",
        file_rel_path="src/views/Profile.vue",
    )

    targets = {r.normalized_raw_target: r for r in results}
    assert "./UserCard.vue" in targets
    assert "@/components/UserBadge.vue" in targets
    assert "@/store/auth" in targets

    card_rel = targets["./UserCard.vue"]
    assert "template_references" in card_rel.metadata
    assert card_rel.metadata["template_references"][0]["component_local_name"] == "UserCard"

    badge_rel = targets["@/components/UserBadge.vue"]
    assert "template_references" in badge_rel.metadata
    assert badge_rel.metadata["template_references"][0]["component_local_name"] == "UserBadge"

    # useAuth is not used as an XML component tag
    auth_rel = targets["@/store/auth"]
    assert "template_references" not in auth_rel.metadata
