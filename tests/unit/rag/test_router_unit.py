"""Unit tests for QueryRouter and Intent Classifier."""

from core.rag.models import IndexType, QueryIntent
from core.rag.router import QueryRouter


def test_query_router_intents():
    router = QueryRouter()

    # 1. Entity lookup
    p1 = router.route("LeadService 在哪里？")
    assert p1.intent == QueryIntent.ENTITY_LOOKUP
    assert p1.channels[IndexType.ENTITY] > 0.5
    assert "LeadService" in p1.extracted_entities

    # 2. History query
    p2 = router.route("上周是谁修改了 LeadAllocationService.java？")
    assert p2.intent == QueryIntent.HISTORY_QUERY
    assert p2.channels[IndexType.TEMPORAL] >= 0.6
    assert any("LeadAllocationService.java" in path for path in p2.extracted_paths)

    # 3. Relation query
    p3 = router.route("哪些页面调用了 /api/leads 接口？")
    assert p3.intent == QueryIntent.RELATION_QUERY
    assert p3.channels[IndexType.GRAPH] >= 0.5

    # 4. Impact query
    p4 = router.route("修改 UserDTO 会影响哪些文件？")
    assert p4.intent == QueryIntent.IMPACT_QUERY
    assert p4.channels[IndexType.GRAPH] >= 0.6

    # 5. Project alias recognition
    p5 = router.route("hello-backend 中如何处理认证？")
    assert p5.target_project == "HELLO_BE"

    p6 = router.route("L2C 前端项目使用的组件库是什么？")
    assert p6.target_project == "L2C_FE"
