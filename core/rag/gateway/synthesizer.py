"""LKIO Evidence-Grounded Answer Synthesizer
Synthesizes verified answers with explicit citations from RAGQueryResult.
"""

from core.rag.engine import RAGQueryResult
from core.rag.gateway.provider import LLMProvider


class GroundedAnswerSynthesizer:
    """Produces structured, grounded markdown answers with strict citations."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def synthesize(self, query_result: RAGQueryResult) -> str:
        """Constructs an evidence-backed answer."""
        if not query_result.results:
            return f"### LKIO RAG 检索结果\n\n未检索到与查询 `{query_result.query}` 相关的实体或代码。"

        top_results = query_result.results[:5]

        # If LLM Provider is available, prompt it with retrieved facts
        if self.provider:
            context_blocks: list[str] = []
            for idx, r in enumerate(top_results, start=1):
                ev_str = ""
                if r.evidences:
                    e = r.evidences[0]
                    ev_str = f" [Source: {e.project_key} {e.file_path}:{e.start_line or ''}]"
                context_blocks.append(f"{idx}. {r.title} ({r.summary}){ev_str}")

            prompt = (
                f"User Question: {query_result.query}\n\n"
                f"Retrieved Evidences:\n" + "\n".join(context_blocks) + "\n\n"
                f"Answer the user strictly using the above facts with citations."
            )
            llm_reply = self.provider.chat([{"role": "user", "content": prompt}])
            answer_text = llm_reply
        else:
            # Deterministic zero-hallucination structured synthesis
            lines = [
                f"### LKIO RAG 检索回答: {query_result.query}",
                f"> **查询意图**: `{query_result.plan.intent.value}` (置信度: {query_result.plan.confidence})",
                "",
                "#### 核心检索结果",
            ]
            for idx, r in enumerate(top_results, start=1):
                proj_tag = f"[{r.project_key}]" if r.project_key else ""
                lines.append(f"{idx}. **{proj_tag} {r.title}** (综合评分: {r.fused_score})")
                lines.append(f"   - **摘要**: {r.summary}")
                if r.file_path:
                    lines.append(f"   - **路径**: `{r.file_path}`")

            answer_text = "\n".join(lines)

        # Append Grounding Citations Table
        citations_table = [
            "",
            "#### 溯源证据链 (Grounding Evidence Citations)",
            "| 序号 | 证据类型 | 所属工程 | 物理文件路径 | 代码行号 | 关联 Key / Hash |",
            "|---|---|---|---|---|---|",
        ]
        c_count = 0
        for r in top_results:
            for ev in r.evidences:
                c_count += 1
                line_str = f"L{ev.start_line}" if ev.start_line else "-"
                key_or_hash = ev.entity_key or ev.relation_key or (ev.commit_hash[:8] if ev.commit_hash else "-")
                citations_table.append(
                    f"| {c_count} | `{ev.evidence_type.value}` | `{ev.project_key}` | `{ev.file_path}` | {line_str} | `{key_or_hash}` |"
                )

        if c_count == 0:
            citations_table.append("| - | 无物理证据 | - | - | - | - |")

        return answer_text + "\n" + "\n".join(citations_table)
