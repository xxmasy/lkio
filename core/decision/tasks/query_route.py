"""Query Route Evaluator for MVP6 Laya Decision Engine
Routes user requests across ["ENTITY", "CODE", "GRAPH", "RAG", "EVENT", "WIKI", "HUMAN"].
"""

import re
from core.decision.models import (
    DecisionRequest,
    DecisionResult,
    QueryRouteDestination,
)
from core.decision.policy import ConfidencePolicy


class QueryRouteEvaluator:
    """Classifies user inquiries to route to the optimal retrieval/knowledge subsystem."""

    EVENT_PATTERNS = [r"什么时候", r"第一次出现", r"改过几次", r"历史", r"变更", r"commit", r"时间线", r"timeline", r"谁改的"]
    GRAPH_PATTERNS = [r"依赖", r"拓扑", r"调用了谁", r"被谁调用", r"继承", r"实现", r"跨工程", r"关系", r"graph", r"caller", r"callee"]
    WIKI_PATTERNS = [r"架构", r"总览", r"wiki", r"文档", r"业务流程", r"业务规则", r"技术选型", r"overview", r"说明书"]
    ENTITY_PATTERNS = [r"定义在", r"符号", r"类在", r"函数在", r"组件在", r"路由", r"endpoint", r"api 路径"]

    def __init__(self, confidence_policy: ConfidencePolicy | None = None):
        self.policy = confidence_policy or ConfidencePolicy()

    def evaluate(self, request: DecisionRequest) -> DecisionResult:
        query_text = (request.state.query_text or "").strip()
        lower_q = query_text.lower()

        matched_route = QueryRouteDestination.RAG.value
        prob = 0.85
        rationale = "Defaulted to Hybrid RAG multi-channel fusion retrieval."

        if any(re.search(pat, lower_q) for pat in self.EVENT_PATTERNS):
            matched_route = QueryRouteDestination.EVENT.value
            prob = 0.94
            rationale = "Temporal / historical query patterns detected; routing to TemporalQueryEngine (MVP5)."
        elif any(re.search(pat, lower_q) for pat in self.GRAPH_PATTERNS):
            matched_route = QueryRouteDestination.GRAPH.value
            prob = 0.92
            rationale = "Structural / relationship traversal patterns detected; routing to Graph Engine (MVP2)."
        elif any(re.search(pat, lower_q) for pat in self.WIKI_PATTERNS):
            matched_route = QueryRouteDestination.WIKI.value
            prob = 0.91
            rationale = "System overview / architectural summary patterns detected; routing to Wiki Sections (MVP4)."
        elif any(re.search(pat, lower_q) for pat in self.ENTITY_PATTERNS):
            matched_route = QueryRouteDestination.ENTITY.value
            prob = 0.90
            rationale = "Targeted symbol / entity lookup patterns detected; routing to Knowledge Core Entities."

        model_conf = prob
        evidence_conf = 0.90
        graph_conf = 0.90
        hist_acc = 0.95

        final_conf = self.policy.calculate_final_confidence(
            model_conf=model_conf,
            evidence_conf=evidence_conf,
            graph_conf=graph_conf,
            historical_acc=hist_acc,
        )

        tier, requires_review = self.policy.evaluate_tier(final_conf)

        return DecisionResult(
            decision=matched_route,
            probability=prob,
            model_confidence=model_conf,
            evidence_confidence=evidence_conf,
            graph_confidence=graph_conf,
            historical_accuracy=hist_acc,
            final_confidence=final_conf,
            requires_human_review=requires_review,
            model_version="laya-route-v1",
            policy_version="route-eval-v1",
            rationale=rationale,
            action_recommendation=tier,
        )
