"""LKIO Query Intent Classifier and Router
Classifies user natural language queries into 8 core intents and computes dynamic multi-index routing plans.
"""

from dataclasses import dataclass, field
import re
from core.rag.models import IndexType, QueryIntent


@dataclass
class QueryPlan:
    """Execution plan for multi-channel retrieval."""
    raw_query: str
    clean_query: str
    intent: QueryIntent
    confidence: float
    channels: dict[IndexType, float]      # Channel -> weight (sums to 1.0)
    target_project: str | None = None     # Filtered project key if identified
    extracted_entities: list[str] = field(default_factory=list)
    extracted_paths: list[str] = field(default_factory=list)


class QueryRouter:
    """Routes queries to appropriate index channels with calibrated weights."""

    # Project keyword mappings
    PROJECT_ALIASES = {
        "hello_fe": "HELLO_FE",
        "hello-fe": "HELLO_FE",
        "hello-frontend": "HELLO_FE",
        "hello frontend": "HELLO_FE",
        "hello前端": "HELLO_FE",
        "hello_be": "HELLO_BE",
        "hello-be": "HELLO_BE",
        "hello-backend": "HELLO_BE",
        "hello backend": "HELLO_BE",
        "hello后端": "HELLO_BE",
        "hahamarket": "HELLO_BE",
        "l2c": "L2C_FE",
        "l2c_fe": "L2C_FE",
        "l2c project": "L2C_FE",
        "l2c前端": "L2C_FE",
        "vben": "L2C_FE",
    }

    def route(self, query: str) -> QueryPlan:
        """Analyzes query and produces an execution plan."""
        q_clean = query.strip()
        intent, confidence = self._classify_intent(q_clean)
        target_proj = self._extract_project(q_clean)
        entities = self._extract_entities(q_clean)
        paths = self._extract_paths(q_clean)

        weights = self._get_channel_weights(intent)

        return QueryPlan(
            raw_query=query,
            clean_query=q_clean,
            intent=intent,
            confidence=confidence,
            channels=weights,
            target_project=target_proj,
            extracted_entities=entities,
            extracted_paths=paths,
        )

    def _classify_intent(self, q: str) -> tuple[QueryIntent, float]:
        q_lower = q.lower()

        # 1. History Intent
        if any(w in q_lower for w in ["谁改", "谁修改", "提交", "commit", "git log", "最近修改", "变更历史", "作者", "什么时候改"]) or re.search(r"\bauthor\b", q_lower):
            return QueryIntent.HISTORY_QUERY, 0.95

        # 2. Impact Intent
        if any(w in q_lower for w in ["影响", "波及", "下游", "impact", "dependents", "被谁使用", "影响链"]):
            return QueryIntent.IMPACT_QUERY, 0.92

        # 3. Relation Intent (calls, imports, extends, API routes)
        if any(w in q_lower for w in ["调用", "引用", "继承", "实现", "calls", "imports", "extends", "implements", "接口调用", "api", "endpoint", "路由"]):
            if "/" in q or "api" in q_lower or any(w in q_lower for w in ["调用", "引用", "继承"]):
                return QueryIntent.RELATION_QUERY, 0.90

        # 4. Entity Lookup Intent
        # Matches "在哪", "where is", "定义", or exact PascalCase identifier
        if any(w in q_lower for w in ["在哪里", "在哪个文件", "where is", "定义位置", "类定义", "符号"]):
            return QueryIntent.ENTITY_LOOKUP, 0.95

        # Check if single or two words look like a class name or file name (e.g. LeadService, user.ts)
        words = q.split()
        if len(words) == 1:
            w = words[0]
            if re.match(r"^[A-Z][a-zA-Z0-9]+$", w) or "." in w:
                return QueryIntent.ENTITY_LOOKUP, 0.90

        # 5. Business Intent
        if any(w in q_lower for w in ["业务", "规则", "为什么", "流程", "设计原则", "分配规则", "销售", "转换", "business", "workflow"]):
            return QueryIntent.BUSINESS_QUERY, 0.88

        # 6. Code Lookup Intent
        if any(w in q_lower for w in ["实现", "代码", "代码块", "函数体", "逻辑", "how is", "code", "implementation"]):
            return QueryIntent.CODE_LOOKUP, 0.85

        # 7. Semantic Query
        if any(w in q_lower for w in ["架构", "设计", "怎么处理", "原理", "规范", "overview", "architecture"]):
            return QueryIntent.SEMANTIC_QUERY, 0.80

        # Default
        return QueryIntent.UNKNOWN, 0.50

    def _extract_project(self, q: str) -> str | None:
        q_lower = q.lower()
        for alias, proj_key in self.PROJECT_ALIASES.items():
            if alias in q_lower:
                return proj_key
        return None

    def _extract_entities(self, q: str) -> list[str]:
        """Extracts potential PascalCase or camelCase symbol tokens."""
        tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9_]{2,}\b", q)
        return [t for t in tokens if any(c.isupper() for c in t)]

    def _extract_paths(self, q: str) -> list[str]:
        """Extracts potential file paths or URL route strings."""
        return re.findall(r"[\w\-_./]+\.[a-zA-Z0-9]+|/[\w\-_/]+", q)

    def _get_channel_weights(self, intent: QueryIntent) -> dict[IndexType, float]:
        """Returns calibrated channel weights summing to 1.0."""
        if intent == QueryIntent.ENTITY_LOOKUP:
            return {
                IndexType.ENTITY: 0.65,
                IndexType.KEYWORD: 0.25,
                IndexType.VECTOR: 0.10,
            }
        elif intent == QueryIntent.CODE_LOOKUP:
            return {
                IndexType.KEYWORD: 0.45,
                IndexType.VECTOR: 0.35,
                IndexType.ENTITY: 0.20,
            }
        elif intent == QueryIntent.RELATION_QUERY:
            return {
                IndexType.GRAPH: 0.60,
                IndexType.ENTITY: 0.20,
                IndexType.KEYWORD: 0.20,
            }
        elif intent == QueryIntent.BUSINESS_QUERY:
            return {
                IndexType.VECTOR: 0.45,
                IndexType.KEYWORD: 0.35,
                IndexType.GRAPH: 0.20,
            }
        elif intent == QueryIntent.HISTORY_QUERY:
            return {
                IndexType.TEMPORAL: 0.70,
                IndexType.KEYWORD: 0.30,
            }
        elif intent == QueryIntent.IMPACT_QUERY:
            return {
                IndexType.GRAPH: 0.65,
                IndexType.ENTITY: 0.20,
                IndexType.KEYWORD: 0.15,
            }
        elif intent == QueryIntent.SEMANTIC_QUERY:
            return {
                IndexType.VECTOR: 0.50,
                IndexType.KEYWORD: 0.30,
                IndexType.GRAPH: 0.20,
            }
        else:
            return {
                IndexType.KEYWORD: 0.40,
                IndexType.ENTITY: 0.30,
                IndexType.VECTOR: 0.30,
            }
