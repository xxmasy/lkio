"""LKIO Standard 13 Wiki Section Generators
Generates evidence-grounded markdown documentation for all 13 required sections.
"""

from typing import Protocol
from core.models.wiki import StandardWikiSection
from core.rag.engine import RAGEngine, RAGQueryResult
from core.rag.gateway.provider import LLMProvider
from core.rag.models import EvidenceCitation, EvidenceType
from core.wiki.models import WikiSectionDTO


class SectionGenerator(Protocol):
    """Protocol for an individual Wiki section generator."""

    def generate(self, project_key: str, engine: RAGEngine, provider: LLMProvider | None = None) -> WikiSectionDTO:
        ...


SECTION_METADATA = {
    StandardWikiSection.PROJECT_OVERVIEW: {
        "title": "Project Overview (项目概览)",
        "query": "项目整体定位 核心业务价值 与 架构角色 overview",
    },
    StandardWikiSection.ARCHITECTURE: {
        "title": "System Architecture (系统架构与分层设计)",
        "query": "系统分层架构 目录骨架与设计模式 architecture",
    },
    StandardWikiSection.FRONTEND: {
        "title": "Frontend Architecture (前端架构与组件体系)",
        "query": "前端技术栈 Vue 组件库 状态管理 store 路由守卫",
        "pattern": r"(\.vue|views|components|router|store|layout|apps/web)",
    },
    StandardWikiSection.BACKEND: {
        "title": "Backend Architecture (后端服务与微服务分层)",
        "query": "后端 Spring Boot Controller Service 模块架构",
        "pattern": r"(service|controller|impl|\.java|spring|backend)",
    },
    StandardWikiSection.API: {
        "title": "API Contracts (外部接口与契约调用链)",
        "query": "HTTP API 路由接口 前后端调用契约 traces",
        "pattern": r"(api|controller|endpoint|trace|request)",
    },
    StandardWikiSection.DATABASE: {
        "title": "Database & Domain Models (持久化与数据模型)",
        "query": "数据库模型 DTO VO POJO 实体与持久化",
        "pattern": r"(model|dto|vo|pojo|entity|table|mapper|database)",
    },
    StandardWikiSection.BUSINESS_DOMAIN: {
        "title": "Business Domain (业务领域模型与概念)",
        "query": "核心业务领域 业务概念 销售与商机模型",
    },
    StandardWikiSection.BUSINESS_PROCESS: {
        "title": "Business Process (核心业务流程与时序流转)",
        "query": "业务流程 线索流转 转化漏斗 流程图",
    },
    StandardWikiSection.BUSINESS_RULES: {
        "title": "Business Rules (计算规则与状态机约束)",
        "query": "核心计算规则 配额分配口径 状态机流转约束",
    },
    StandardWikiSection.DEPENDENCIES: {
        "title": "Dependencies & Workspaces (依赖拓扑与子包关系)",
        "query": "外部依赖库 内部工作区依赖 package.json pom.xml",
        "pattern": r"(package|pom|workspace|pnpm|dependencies)",
    },
    StandardWikiSection.RECENT_CHANGES: {
        "title": "Recent Changes (变更历史与版本演进)",
        "query": "最近提交记录 commit 变更历史 author",
        "pattern": r"(commit|log|history)",
    },
    StandardWikiSection.KNOWN_RISKS: {
        "title": "Known Risks & Tech Debt (技术风险与架构负债)",
        "query": "技术债务 未决问题 风险 open questions risks",
        "pattern": r"(questions|risks|debt|todo)",
    },
    StandardWikiSection.OPEN_DECISIONS: {
        "title": "Open Decisions (架构决策与待定事项)",
        "query": "待决事项 架构决策 open decisions backlog",
        "pattern": r"(decisions|questions|open)",
    },
}


class StandardSectionGenerator:
    """Universal evidence-grounded generator for any of the 13 standard sections."""

    def __init__(self, section_name: StandardWikiSection) -> None:
        self.section_name = section_name
        self.meta = SECTION_METADATA[section_name]

    def generate(
        self,
        project_key: str,
        engine: RAGEngine,
        provider: LLMProvider | None = None,
    ) -> WikiSectionDTO:
        """Executes RAG retrieval, formats evidence, and synthesizes structured section."""
        query_text = f"{project_key} {self.meta['query']}"
        rag_res: RAGQueryResult = engine.query(query_text, project_key=project_key, limit=5)

        # Filter by domain pattern if specified
        target_results = rag_res.results
        pattern = self.meta.get("pattern")
        if pattern:
            import re
            filtered = [
                r for r in rag_res.results
                if (r.file_path and re.search(pattern, r.file_path.lower().replace("\\", "/")))
                or (r.name and re.search(pattern, r.name.lower()))
            ]
            if filtered:
                target_results = filtered

        # Extract grounding identifiers
        ent_keys: list[str] = []
        rel_keys: list[str] = []
        doc_paths: list[str] = []
        commit_hashes: list[str] = []
        citations: list[EvidenceCitation] = []

        for r in target_results:
            if r.entity_key and r.entity_key not in ent_keys:
                ent_keys.append(r.entity_key)
            if r.file_path and r.file_path not in doc_paths:
                doc_paths.append(r.file_path)

            for ev in r.evidences:
                citations.append(ev)
                if ev.relation_key and ev.relation_key not in rel_keys:
                    rel_keys.append(ev.relation_key)
                if ev.commit_hash and ev.commit_hash not in commit_hashes:
                    commit_hashes.append(ev.commit_hash)

        # Synthesize markdown content
        content_lines = [
            f"## {self.meta['title']}",
            "",
            f"> **所属工程**: `{project_key}`  ",
            f"> **章节代号**: `{self.section_name.value}`  ",
            f"> **检索意图**: `{rag_res.plan.intent.value}` (置信度: {rag_res.plan.confidence})",
            "",
            "### 核心事实与架构要点",
        ]

        if rag_res.results:
            for idx, r in enumerate(rag_res.results[:5], start=1):
                content_lines.append(f"{idx}. **{r.title}**")
                content_lines.append(f"   - **摘要**: {r.summary}")
                if r.file_path:
                    content_lines.append(f"   - **对应物理源码**: `{r.file_path}`")
        else:
            content_lines.append(f"- 暂未检索到与 `{project_key}` 相关的结构化实体或文档记录。")

        # Append Grounding Citations Table
        content_lines.extend([
            "",
            "### 溯源证据链 (Grounding Evidence Citations)",
            "| 序号 | 证据类型 | 物理文件路径 | 代码行号 | 关联 Key / Commit | 置信度 |",
            "|---|---|---|---|---|---|",
        ])

        seen_keys: set[str] = set()
        c_count = 0
        for ev in citations:
            line_str = f"L{ev.start_line}" if ev.start_line else "-"
            ref_key = ev.entity_key or ev.relation_key or (ev.commit_hash[:8] if ev.commit_hash else "-")
            dedup_str = f"{ev.evidence_type.value}:{ev.file_path}:{line_str}:{ref_key}"
            if dedup_str in seen_keys:
                continue
            seen_keys.add(dedup_str)
            c_count += 1
            content_lines.append(
                f"| {c_count} | `{ev.evidence_type.value}` | `{ev.file_path}` | {line_str} | `{ref_key}` | {ev.confidence:.2f} |"
            )

        if c_count == 0:
            content_lines.append("| - | 无独立物理证据 | - | - | - | 1.00 |")

        final_content = "\n".join(content_lines)

        return WikiSectionDTO(
            project_key=project_key,
            section_name=self.section_name,
            title=self.meta["title"],
            content=final_content,
            source_entity_keys=ent_keys,
            source_relation_keys=rel_keys,
            source_document_paths=doc_paths,
            source_commit_hashes=commit_hashes,
            evidence_citations=citations,
            model="deterministic-synthesizer" if not provider else getattr(provider, "model", "llm"),
            confidence=round(rag_res.plan.confidence, 2),
        )


class WikiSectionGeneratorFactory:
    """Factory creating generators for all 13 standard sections."""

    @staticmethod
    def get_generator(section_name: StandardWikiSection) -> StandardSectionGenerator:
        return StandardSectionGenerator(section_name=section_name)

    @staticmethod
    def generate_all_sections(
        project_key: str,
        engine: RAGEngine,
        provider: LLMProvider | None = None,
    ) -> list[WikiSectionDTO]:
        """Generates all 13 standard sections for a project in order."""
        sections: list[WikiSectionDTO] = []
        for sec_name in StandardWikiSection:
            gen = StandardSectionGenerator(sec_name)
            sections.append(gen.generate(project_key=project_key, engine=engine, provider=provider))
        return sections
