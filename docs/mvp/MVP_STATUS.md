# LKIO MVP 执行跟踪与状态总表

> **当前基线**：LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md
> **当前唯一允许 ACTIVE 的阶段**：**MVP0**
> **核心原则**：
> 1. 源项目（`HELLO_FE`, `HELLO_BE`, `L2C_FE`）只读，严禁修改。
> 2. 每个步骤做完必须留下归档文档，放在 `docs/mvp/`。
> 3. 文档必须对照上一轮 Plan 检验，明确记录完成了哪一个 MVP 的哪个步骤。
> 4. 下一个任务开始前，必须核验上一阶段的完成情况才能启动规划。

---

## 1. MVP 阶段状态矩阵

| MVP 代号 | 阶段名称 | 当前状态 | 依赖阶段 | 验收状态 | 归档文档 |
|---|---|---|---|---|---|
| **MVP0** | **Environment & Knowledge Core** | **COMPLETED** | 无（起始阶段） | **ALL PASSED** | `docs/mvp/mvp0_acceptance_report.md` |
| MVP1 | Project Ingestion (只读扫描/增量) | **READY_TO_PLAN** | MVP0 (已验收) | 待启动 | - |
| MVP2 | Code / AST / Cross-project Graph | **LOCKED** | MVP1 | 未开始 | - |
| MVP3 | Hybrid RAG (Keyword+pgvector+Graph) | **LOCKED** | MVP1, MVP2 | 未开始 | - |
| MVP4 | LLM Wiki (带证据投影) | **LOCKED** | MVP3 | 未开始 | - |
| MVP5 | Event & Change Intelligence | **LOCKED** | MVP1 | 未开始 | - |
| MVP6 | Laya Decision Engine (4大决策任务) | **LOCKED** | MVP4, MVP5 | 未开始 | - |
| MVP7 | Impact Analysis Engine (影响链分析) | **LOCKED** | MVP2, MVP5, MVP6 | 未开始 | - |
| MVP8 | Evaluation / Calibration / Learning Loop | **LOCKED** | MVP6, MVP7 | 未开始 | - |

---

## 2. MVP0 细分步骤规划与进展

| 步骤编号 | 步骤目标 | 计划产出 | 当前状态 | 检查与验证文档 |
|---|---|---|---|---|
| **Step 0.1** | 环境基线核验与 Docker Compose 部署 | Docker, Node 24, Python 3.12, uv, Git 核验; `infra/compose.yaml` 启动 pgvector 0.8.6-pg18 | **COMPLETED** | `docs/mvp/mvp0_step1_env_and_infra.md` |
| **Step 0.2** | 目录规范与 Python 核心工程初始化 | `uv init`, 依赖锁定, 目录结构骨架, 根配置文件 (`projects.yaml`, `.env.example`) | **COMPLETED** | `docs/mvp/mvp0_step2_backend_and_schema.md` |
| **Step 0.3** | 数据库模型与 Alembic 迁移脚本 | SQLAlchemy 2.x 模型 (`projects`, `sources`, `entities`, `relations`), Alembic 迁移成功 | **COMPLETED** | `docs/mvp/mvp0_step3_db_models_migration.md` |
| **Step 0.4** | 三大真实项目种子数据注入与幂等性验证 | 注入 HELLO_FE, HELLO_BE, L2C_FE; 建立 `paired_with` 关系; 幂等性执行验证 | **COMPLETED** | `docs/mvp/mvp0_step4_seed_and_idempotency.md` |
| **Step 0.5** | 后端 API 端点实现与单元测试通过 | Health, Projects, Entities, Relations, Graph API (`/api/v1/health`, etc.); pytest 测试 | **COMPLETED** | `docs/mvp/mvp0_step5_api_and_tests.md` |
| **Step 0.6** | 前端控制台构建 (Vue 3 + Element Plus + Cytoscape) | Overview 统计、Projects 列表与详情、2D Cytoscape 拓扑图谱展示 | **COMPLETED** | `docs/mvp/mvp0_step6_frontend_graph.md` |
| **Step 0.7** | MVP0 验收门总检验与基线冻结 | 对照 Section 14 & 66 逐项验收，形成 MVP0 结项终审报告 | **COMPLETED** | `docs/mvp/mvp0_acceptance_report.md` |
