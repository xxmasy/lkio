"""LKIO MVP3 System Acceptance Gate: 100-Query Gold Set Evaluation.
Validates:
- Recall@5 >= 85%
- Wrong-project rate < 3%
- Source correctness >= 95%
"""

import pytest
from core.rag.builder import RAGIndexHub
from core.rag.engine import RAGEngine
from core.rag.gateway import GroundedAnswerSynthesizer
from tests.integration.step3.gold_set_data import GOLD_SET_100


def build_acceptance_index_hub() -> RAGIndexHub:
    """Populates RAGIndexHub with comprehensive real project knowledge fixtures."""
    hub = RAGIndexHub(dimension=64)

    # -------------------------------------------------------------
    # 1. HELLO_BE Entities, Docs, Commits, APIs
    # -------------------------------------------------------------
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:org.example.hahamarket.pojo.vo.dto.NorthAmericaSalesDailyReportRowDTO",
        name="NorthAmericaSalesDailyReportRowDTO",
        canonical_name="org.example.hahamarket.pojo.vo.dto.NorthAmericaSalesDailyReportRowDTO",
        project_key="HELLO_BE",
        entity_type="CLASS",
        file_path="src/main/java/org/example/hahamarket/pojo/vo/dto/NorthAmericaSalesDailyReportRowDTO.java",
        start_line=15,
        end_line=60,
        docstring="DTO representing a single row in the North America Sales Daily report",
    )
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:org.example.hahamarket.service.leadconversion.impl.NorthAmericaSalesDailyDetailMetricsService",
        name="NorthAmericaSalesDailyDetailMetricsService",
        canonical_name="org.example.hahamarket.service.leadconversion.impl.NorthAmericaSalesDailyDetailMetricsService",
        project_key="HELLO_BE",
        entity_type="SERVICE",
        file_path="src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyDetailMetricsService.java",
        start_line=20,
        end_line=150,
        docstring="Computes detail metrics for North America sales daily report",
    )
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:org.example.hahamarket.service.leadconversion.impl.NorthAmericaSalesDailyReportServiceImpl",
        name="NorthAmericaSalesDailyReportServiceImpl",
        canonical_name="org.example.hahamarket.service.leadconversion.impl.NorthAmericaSalesDailyReportServiceImpl",
        project_key="HELLO_BE",
        entity_type="SERVICE",
        file_path="src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyReportServiceImpl.java",
        start_line=25,
        end_line=180,
        docstring="Implementation of NorthAmericaSalesDailyReportService with lead conversion metrics aggregation",
    )
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:org.example.hahamarket.service.leadconversion.LeadConversionService",
        name="LeadConversionService",
        canonical_name="org.example.hahamarket.service.leadconversion.LeadConversionService",
        project_key="HELLO_BE",
        entity_type="INTERFACE",
        file_path="src/main/java/org/example/hahamarket/service/leadconversion/LeadConversionService.java",
        start_line=10,
        end_line=45,
        docstring="Core lead conversion domain service interface",
    )
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:org.example.hahamarket.service.telemarketing.TelemarketingCallService",
        name="TelemarketingCallService",
        canonical_name="org.example.hahamarket.service.telemarketing.TelemarketingCallService",
        project_key="HELLO_BE",
        entity_type="SERVICE",
        file_path="src/main/java/org/example/hahamarket/service/telemarketing/TelemarketingCallService.java",
        start_line=12,
        end_line=80,
        docstring="Service handling telemarketing outbound call logs and statistics",
    )
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:org.example.hahamarket.controller.SalesReportController",
        name="SalesReportController",
        canonical_name="org.example.hahamarket.controller.SalesReportController",
        project_key="HELLO_BE",
        entity_type="CLASS",
        file_path="src/main/java/org/example/hahamarket/controller/SalesReportController.java",
        start_line=18,
        end_line=95,
        docstring="REST Controller exposing /api/sales endpoints",
    )
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:NorthAmericaSalesDailyDetailMetricsServiceTest",
        name="NorthAmericaSalesDailyDetailMetricsServiceTest",
        canonical_name="org.example.hahamarket.service.leadconversion.impl.NorthAmericaSalesDailyDetailMetricsServiceTest",
        project_key="HELLO_BE",
        entity_type="CLASS",
        file_path="src/test/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyDetailMetricsServiceTest.java",
        start_line=15,
        end_line=85,
        docstring="Unit test suite for NorthAmericaSalesDailyDetailMetricsService",
    )

    # Docs HELLO_BE
    hub.index_document(
        file_path="docs/reports/00-README.md",
        content=(
            "# Reports Directory Overview\n"
            "HELLO 后端报表体系的目录结构规划说明。Documentation and specifications for North America sales and telemarketing reports."
        ),
        project_key="HELLO_BE",
    )
    hub.index_document(
        file_path="docs/reports/01-north-america-sales-daily-report.md",
        content=(
            "# North America Sales Daily Report Specification\n"
            "Defines metrics: lead allocation count, conversion rate, response time per sales rep, "
            "quota attainment, and daily aggregate revenue."
        ),
        project_key="HELLO_BE",
    )
    hub.index_document(
        file_path="docs/reports/07-telemarketing-call-reports.md",
        content=(
            "# Telemarketing Outbound Call Reports\n"
            "Analysis of call durations, connect rates, recording compliance, and sales agent efficiency. "
            "电销外呼记录 CSV 数据读取与解析逻辑代码 call-log CSV reports."
        ),
        project_key="HELLO_BE",
    )

    # Commits HELLO_BE
    hub.index_commit(
        commit_hash="be01a2b3c4d5e6f7",
        message="feat(lead): implement NorthAmericaSalesDailyDetailMetricsService logic",
        author="David",
        timestamp="2026-09-24 15:30:00",
        project_key="HELLO_BE",
        files_changed=[
            "src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyDetailMetricsService.java",
            "src/main/java/org/example/hahamarket/pojo/vo/dto/NorthAmericaSalesDailyReportRowDTO.java",
        ],
    )
    hub.index_commit(
        commit_hash="be02f8e9d0c1b2a3",
        message="fix(report): refine NorthAmericaSalesDailyReportServiceImpl daily aggregation and metrics",
        author="David",
        timestamp="2026-09-25 09:20:00",
        project_key="HELLO_BE",
        files_changed=[
            "src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyReportServiceImpl.java",
            "docs/reports/01-north-america-sales-daily-report.md",
        ],
    )
    hub.index_commit(
        commit_hash="be03112233445566",
        message="docs(telemarketing): update 07-telemarketing-call-reports.md call log test metrics",
        author="Emma",
        timestamp="2026-09-25 11:45:00",
        project_key="HELLO_BE",
        files_changed=["docs/reports/07-telemarketing-call-reports.md"],
    )

    # Relations HELLO_BE
    hub.index_relation(
        relation_key="REL:HELLO_BE:impl:calls:metrics",
        subject_key="SYMBOL:HELLO_BE:org.example.hahamarket.service.leadconversion.impl.NorthAmericaSalesDailyReportServiceImpl",
        predicate="calls",
        project_key="HELLO_BE",
        object_key="SYMBOL:HELLO_BE:org.example.hahamarket.service.leadconversion.impl.NorthAmericaSalesDailyDetailMetricsService",
        file_path="src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyReportServiceImpl.java",
        start_line=45,
    )
    hub.index_relation(
        relation_key="REL:HELLO_BE:test:tests:metrics",
        subject_key="SYMBOL:HELLO_BE:NorthAmericaSalesDailyDetailMetricsServiceTest",
        predicate="calls",
        project_key="HELLO_BE",
        object_key="SYMBOL:HELLO_BE:org.example.hahamarket.service.leadconversion.impl.NorthAmericaSalesDailyDetailMetricsService",
        file_path="src/test/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyDetailMetricsServiceTest.java",
        start_line=30,
    )

    # -------------------------------------------------------------
    # 2. HELLO_FE Entities, Docs, Commits, APIs
    # -------------------------------------------------------------
    hub.index_entity(
        entity_key="SYMBOL:HELLO_FE:src/api/order.ts",
        name="order.ts",
        canonical_name="src/api/order.ts",
        project_key="HELLO_FE",
        entity_type="MODULE",
        file_path="src/api/order.ts",
        start_line=1,
        end_line=40,
        docstring="Order API client for fetching and updating customer orders",
    )
    hub.index_entity(
        entity_key="SYMBOL:HELLO_FE:src/api/request.ts",
        name="requestClient",
        canonical_name="src/api/request.ts:requestClient",
        project_key="HELLO_FE",
        entity_type="VARIABLE",
        file_path="src/api/request.ts",
        start_line=10,
        end_line=35,
        docstring="Axios requestClient instance with token interceptors",
    )
    hub.index_commit(
        commit_hash="fe01998877665544",
        message="chore(config): update .cursor/mcp.json server configurations",
        author="Frank",
        timestamp="2026-09-24 18:00:00",
        project_key="HELLO_FE",
        files_changed=[".cursor/mcp.json"],
    )

    # -------------------------------------------------------------
    # 3. L2C_FE Entities, Docs, Commits, APIs
    # -------------------------------------------------------------
    l2c_entities = [
        ("SYMBOL:L2C_FE:apps/web-ele/src/api/core/auth.ts", "auth.ts", "apps/web-ele/src/api/core/auth.ts", "MODULE", "apps/web-ele/src/api/core/auth.ts", 1, 50, "Authentication API with login and getAccessCodesApi"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/api/core/menu.ts", "menu.ts", "apps/web-ele/src/api/core/menu.ts", "MODULE", "apps/web-ele/src/api/core/menu.ts", 1, 40, "Menu and navigation route API fetching"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/api/core/user.ts", "user.ts", "apps/web-ele/src/api/core/user.ts", "MODULE", "apps/web-ele/src/api/core/user.ts", 1, 35, "User profile and permission API client"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/api/request.ts", "request.ts", "apps/web-ele/src/api/request.ts", "MODULE", "apps/web-ele/src/api/request.ts", 1, 60, "Central Axios request configuration with JWT authorization header injection"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/layouts/basic.vue", "basic.vue", "apps/web-ele/src/layouts/basic.vue", "COMPONENT", "apps/web-ele/src/layouts/basic.vue", 1, 120, "Basic admin application layout integrating sidebar, header, preferences"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/views/_core/authentication/login.vue", "login.vue", "apps/web-ele/src/views/_core/authentication/login.vue", "PAGE", "apps/web-ele/src/views/_core/authentication/login.vue", 1, 150, "User login form and OAuth authentication view"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/views/dashboard/analytics/index.vue", "analytics/index.vue", "apps/web-ele/src/views/dashboard/analytics/index.vue", "PAGE", "apps/web-ele/src/views/dashboard/analytics/index.vue", 1, 180, "Dashboard analytics visualization page with Echarts graphics"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/views/dashboard/workspace/index.vue", "workspace/index.vue", "apps/web-ele/src/views/dashboard/workspace/index.vue", "PAGE", "apps/web-ele/src/views/dashboard/workspace/index.vue", 1, 140, "Personalized workspace workbench card layout"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/store/auth.ts", "store/auth.ts", "apps/web-ele/src/store/auth.ts", "MODULE", "apps/web-ele/src/store/auth.ts", 1, 80, "Pinia auth store managing user token, roles, and logout state"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/router/guard.ts", "guard.ts", "apps/web-ele/src/router/guard.ts", "MODULE", "apps/web-ele/src/router/guard.ts", 1, 90, "Router navigation guards verifying access codes and login redirects"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/router/routes/modules/dashboard.ts", "dashboard.ts", "apps/web-ele/src/router/routes/modules/dashboard.ts", "MODULE", "apps/web-ele/src/router/routes/modules/dashboard.ts", 1, 55, "Dashboard routing module for analytics and workspace"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/router/routes/modules/demos.ts", "demos.ts", "apps/web-ele/src/router/routes/modules/demos.ts", "MODULE", "apps/web-ele/src/router/routes/modules/demos.ts", 1, 65, "Component demos routing module"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/router/routes/modules/marketing.ts", "marketing.ts", "apps/web-ele/src/router/routes/modules/marketing.ts", "MODULE", "apps/web-ele/src/router/routes/modules/marketing.ts", 1, 50, "Marketing campaigns and cockpit routing module"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/router/routes/modules/sales.ts", "sales.ts", "apps/web-ele/src/router/routes/modules/sales.ts", "MODULE", "apps/web-ele/src/router/routes/modules/sales.ts", 1, 50, "Sales leads and opportunity management routing module"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/router/routes/modules/system.ts", "system.ts", "apps/web-ele/src/router/routes/modules/system.ts", "MODULE", "apps/web-ele/src/router/routes/modules/system.ts", 1, 45, "System management users, roles, and permission routes"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/views/demos/element/button.vue", "button.vue", "apps/web-ele/src/views/demos/element/button.vue", "PAGE", "apps/web-ele/src/views/demos/element/button.vue", 1, 95, "Element Plus Button component showcases"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/preferences.ts", "preferences.ts", "apps/web-ele/src/preferences.ts", "MODULE", "apps/web-ele/src/preferences.ts", 1, 60, "Application preferences state and theme configuration"),
        ("SYMBOL:L2C_FE:apps/backend-mock/utils/mock-data.ts", "mock-data.ts", "apps/backend-mock/utils/mock-data.ts", "MODULE", "apps/backend-mock/utils/mock-data.ts", 1, 100, "Backend mock data utility generator"),
        ("SYMBOL:L2C_FE:packages/@core/base/shared/src/constants/vben.ts", "vben.ts", "packages/@core/base/shared/src/constants/vben.ts", "MODULE", "packages/@core/base/shared/src/constants/vben.ts", 1, 40, "Core shared constants across all monorepo apps"),
        ("SYMBOL:L2C_FE:packages/effects/plugins/src/echarts/types.ts", "types.ts", "packages/effects/plugins/src/echarts/types.ts", "MODULE", "packages/effects/plugins/src/echarts/types.ts", 1, 50, "Echarts plugin type definitions"),
        ("SYMBOL:L2C_FE:packages/effects/plugins/src/echarts/echarts.ts", "echarts.ts", "packages/effects/plugins/src/echarts/echarts.ts", "MODULE", "packages/effects/plugins/src/echarts/echarts.ts", 1, 75, "Echarts plugin initialization and theme setup"),
        ("SYMBOL:L2C_FE:packages/@core/preferences/src/config.ts", "config.ts", "packages/@core/preferences/src/config.ts", "MODULE", "packages/@core/preferences/src/config.ts", 1, 50, "Core preferences configuration schema"),
        ("SYMBOL:L2C_FE:apps/web-ele/src/views/_core/about/index.vue", "about/index.vue", "apps/web-ele/src/views/_core/about/index.vue", "PAGE", "apps/web-ele/src/views/_core/about/index.vue", 1, 80, "About system information and dependencies showcase"),
        ("SYMBOL:L2C_FE:pnpm-lock.yaml", "pnpm-lock.yaml", "pnpm-lock.yaml", "FILE", "pnpm-lock.yaml", 1, 500, "Lockfile defining package versions and workspace dependencies"),
    ]
    for key, name, cname, etype, path, sline, eline, doc in l2c_entities:
        hub.index_entity(
            entity_key=key,
            name=name,
            canonical_name=cname,
            project_key="L2C_FE",
            entity_type=etype,
            file_path=path,
            start_line=sline,
            end_line=eline,
            docstring=doc,
        )

    # L2C Docs
    hub.index_document(
        file_path="L2C_FRONTEND_WHITEPAPER.md",
        content=(
            "# L2C Frontend Architecture Whitepaper\n"
            "Defines the complete Lead to Cash (L2C) marketing and sales system architecture, "
            "monorepo structure with pnpm workspaces, and Vue 3 + Vite standards."
        ),
        project_key="L2C_FE",
    )
    hub.index_document(
        file_path="docs/MARKETING_L2C_SPEC.md",
        content=(
            "# Marketing L2C Specification\n"
            "Full lifecycle specifications for campaigns, lead acquisition, qualification funnel, "
            "and marketing cockpit KPI tracking."
        ),
        project_key="L2C_FE",
    )
    hub.index_document(
        file_path="docs/MASTER_ARCHITECTURE_BASELINE.md",
        content=(
            "# Master Architecture Baseline\n"
            "Architectural rules, monorepo package isolation boundaries, and Docker deployment configs."
        ),
        project_key="L2C_FE",
    )
    hub.index_document(
        file_path="docs/OPEN_QUESTIONS.md",
        content="# Open Questions\nTracking open technical questions and architectural backlog.",
        project_key="L2C_FE",
    )
    hub.index_document(
        file_path="docs/PROJECT_FULL_SUMMARY.md",
        content="# Project Full Summary\nExecutive summary of L2C system features, tech stack, and roadmap.",
        project_key="L2C_FE",
    )
    hub.index_document(
        file_path="apps/web-ele/src/locales/langs/zh-CN/page.json",
        content="{\"dashboard\": \"仪表盘\", \"analytics\": \"分析页\", \"workspace\": \"工作台\"}",
        project_key="L2C_FE",
    )
    hub.index_document(
        file_path="apps/web-ele/src/locales/langs/en-US/page.json",
        content="{\"dashboard\": \"Dashboard\", \"analytics\": \"Analytics\", \"workspace\": \"Workspace\"}",
        project_key="L2C_FE",
    )

    # L2C Commits
    hub.index_commit(
        commit_hash="l2c0112233445566",
        message="feat(docker): configure Dockerfile and docker-compose.yml for production deployment",
        author="Grace",
        timestamp="2026-09-24 19:15:00",
        project_key="L2C_FE",
        files_changed=["Dockerfile", "docker-compose.yml"],
    )
    hub.index_commit(
        commit_hash="l2c02aabbccddeef",
        message="ci(actions): add docker-build-push.yml for automated GitHub Actions build and push",
        author="Grace",
        timestamp="2026-09-24 19:40:00",
        project_key="L2C_FE",
        files_changed=[".github/workflows/docker-build-push.yml"],
    )
    hub.index_commit(
        commit_hash="l2c0399887766554",
        message="docs(whitepaper): update L2C_FRONTEND_WHITEPAPER.md marketing and sales architecture",
        author="Helen",
        timestamp="2026-09-25 08:30:00",
        project_key="L2C_FE",
        files_changed=["L2C_FRONTEND_WHITEPAPER.md"],
    )
    hub.index_commit(
        commit_hash="l2c0455443322110",
        message="refactor(auth): update apps/web-ele/src/api/core/auth.ts and store/auth.ts logout logic",
        author="Helen",
        timestamp="2026-09-25 10:10:00",
        project_key="L2C_FE",
        files_changed=["apps/web-ele/src/api/core/auth.ts", "apps/web-ele/src/store/auth.ts"],
    )
    hub.index_commit(
        commit_hash="l2c0566778899001",
        message="refactor(router): refine guard.ts permission checking and menu generation",
        author="Ian",
        timestamp="2026-09-25 12:00:00",
        project_key="L2C_FE",
        files_changed=["apps/web-ele/src/router/guard.ts"],
    )
    hub.index_commit(
        commit_hash="l2c0611223399887",
        message="feat(i18n): update zh-CN and en-US page.json locale files",
        author="Ian",
        timestamp="2026-09-25 14:20:00",
        project_key="L2C_FE",
        files_changed=["apps/web-ele/src/locales/langs/zh-CN/page.json"],
    )

    # -------------------------------------------------------------
    # 4. Cross-Project API Contract Traces
    # -------------------------------------------------------------
    hub.index_api_trace(
        trace_id="TRACE:login:post",
        http_method="POST",
        http_path="/api/auth/login",
        frontend_call_site="loginApi(params)",
        frontend_project="L2C_FE",
        backend_controller="AuthController",
        backend_service="AuthenticationService",
        backend_project="L2C_FE",
        file_path="apps/web-ele/src/api/core/auth.ts",
        start_line=15,
    )
    hub.index_api_trace(
        trace_id="TRACE:menu:get",
        http_method="GET",
        http_path="/api/menu",
        frontend_call_site="getMenuList()",
        frontend_project="L2C_FE",
        backend_controller="MenuController",
        backend_service="MenuService",
        backend_project="L2C_FE",
        file_path="apps/web-ele/src/api/core/menu.ts",
        start_line=12,
    )
    hub.index_api_trace(
        trace_id="TRACE:leads:post",
        http_method="POST",
        http_path="/api/leads",
        frontend_call_site="fetchLeadsApi()",
        frontend_project="HELLO_FE",
        backend_controller="SalesReportController",
        backend_service="NorthAmericaSalesDailyReportServiceImpl",
        backend_project="HELLO_BE",
        file_path="src/api/order.ts",
        start_line=20,
    )
    hub.index_api_trace(
        trace_id="TRACE:sales_daily:get",
        http_method="GET",
        http_path="/api/sales/daily",
        frontend_call_site="fetchDailySales()",
        frontend_project="HELLO_FE",
        backend_controller="SalesReportController",
        backend_service="NorthAmericaSalesDailyReportServiceImpl",
        backend_project="HELLO_BE",
        file_path="src/api/order.ts",
        start_line=25,
    )
    hub.index_api_trace(
        trace_id="TRACE:orders:get",
        http_method="GET",
        http_path="/api/orders",
        frontend_call_site="getOrderList()",
        frontend_project="HELLO_FE",
        backend_controller="OrderController",
        backend_service="OrderService",
        backend_project="HELLO_BE",
        file_path="src/api/order.ts",
        start_line=10,
    )

    return hub


def test_rag_gold_set_acceptance():
    """Runs the 100-Query Gold Set evaluation and verifies all acceptance gates."""
    hub = build_acceptance_index_hub()
    engine = RAGEngine(index_hub=hub)
    synthesizer = GroundedAnswerSynthesizer()

    total_queries = len(GOLD_SET_100)
    hits_at_5 = 0
    wrong_project_count = 0
    source_correct_count = 0

    detailed_results = []

    for item in GOLD_SET_100:
        q_id = item["id"]
        category = item["category"]
        q_text = item["query"]
        expected_proj = item.get("project")
        expected_matches = [m.lower() for m in item["expected_matches"]]

        # Execute query
        result = engine.query(q_text, project_key=expected_proj, limit=5)
        top_candidates = result.results[:5]

        # 1. Evaluate Recall@5: Does any top-5 candidate match expected targets?
        matched = False
        for cand in top_candidates:
            cand_text = f"{cand.name} {cand.title} {cand.file_path or ''} {cand.summary}".lower()
            if any(exp in cand_text for exp in expected_matches):
                matched = True
                break

        if matched:
            hits_at_5 += 1

        # 2. Evaluate Wrong Project Rate on Top-1
        is_wrong_proj = False
        if top_candidates and expected_proj:
            top_1 = top_candidates[0]
            if top_1.project_key and top_1.project_key != expected_proj:
                is_wrong_proj = True
                wrong_project_count += 1

        # 3. Evaluate Source Correctness: Does Top-1 have grounding evidence?
        is_grounded = False
        if top_candidates:
            top_1 = top_candidates[0]
            if top_1.evidences and any(
                ev.file_path or ev.commit_hash for ev in top_1.evidences
            ):
                is_grounded = True
                source_correct_count += 1

        detailed_results.append({
            "id": q_id,
            "category": category,
            "matched": matched,
            "wrong_project": is_wrong_proj,
            "grounded": is_grounded,
            "top_title": top_candidates[0].title if top_candidates else "NONE",
        })

    recall_at_5 = hits_at_5 / total_queries
    wrong_project_rate = wrong_project_count / total_queries
    source_correctness = source_correct_count / total_queries

    print("\n" + "=" * 80)
    print(" LKIO MVP3 HYBRID RAG GOLD SET ACCEPTANCE AUDIT REPORT")
    print("=" * 80)
    print(f" Total Gold Set Queries Evaluated : {total_queries}")
    print(f" Top-5 Hits (Recall@5)            : {hits_at_5}/{total_queries} ({recall_at_5:.2%})  [Gate: >= 85.0%]")
    print(f" Wrong Project Rate               : {wrong_project_count}/{total_queries} ({wrong_project_rate:.2%})  [Gate: < 3.0%]")
    print(f" Source Correctness Rate          : {source_correct_count}/{total_queries} ({source_correctness:.2%})  [Gate: >= 95.0%]")
    print("-" * 80)

    # Category breakdown
    cat_stats = {}
    for r in detailed_results:
        cat = r["category"]
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "hits": 0}
        cat_stats[cat]["total"] += 1
        if r["matched"]:
            cat_stats[cat]["hits"] += 1

    for cat, stats in cat_stats.items():
        rate = stats["hits"] / stats["total"]
        print(f"  Category: {cat:22} | Hits: {stats['hits']:2}/{stats['total']:2} ({rate:.1%})")
    print("=" * 80 + "\n")

    # Strict Gate Verifications
    assert recall_at_5 >= 0.85, f"Recall@5 ({recall_at_5:.2%}) fell below required 85.0%"
    assert wrong_project_rate < 0.03, f"Wrong project rate ({wrong_project_rate:.2%}) exceeded allowable 3.0%"
    assert source_correctness >= 0.95, f"Source correctness ({source_correctness:.2%}) fell below required 95.0%"
