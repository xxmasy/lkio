# LKIO MVP 执行跟踪与状态总表

> **当前基线**：`LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md` / `MVP2实施基线LKIO — Code Intelligence & Structural Graph.md`  
> **当前正式锁定状态**：
> - **MVP0 = COMPLETED / FROZEN** (基础环境与知识图谱底座已固化冻结)
> - **MVP1 = COMPLETED / FROZEN** (三大项目只读摄取、快照、审计历史与回归集已固化冻结)
> - **MVP2 = COMPLETED / FROZEN** (Tree-sitter 代码结构图谱、符号提取与端到端追溯已固化冻结)
> - **MVP3 = COMPLETED / FROZEN** (Hybrid RAG 三路召回与重排已固化冻结)
> - **MVP4 = COMPLETED / FROZEN** (LLM Wiki 13大标准章节与增量失效流水线已固化冻结)
> - **MVP5 = COMPLETED / FROZEN** (Event & Change Intelligence 变更时空智能与时间线已固化冻结)
> - **MVP6 = READY_TO_PLAN** (Laya Decision Engine 待启动规划)
>
> ### 🛑 永久冻结架构红线（后续任何 Agent 均严禁擅自变更）：
> 1. **三个源项目只读**：`HELLO_FE`, `HELLO_BE`, `L2C_FE` 绝对物理只读，禁止写回或修改任何文件。
> 2. **严禁解析 .git 内部结构**：禁止任何针对 `.git/objects`、`refs`、`index` 等内部二进制文件的直接读取和反序列化。
> 3. **Git 一律通过 subprocess 调用 Git CLI**：统一使用标准 Git 命令行工具，保证跨平台一致性与透明度。
> 4. **敏感文件永不进入 Knowledge Core**：`.env`, 密钥 (`*.pem`, `*.key`), Token, 私钥, 证书等敏感资产严禁扫描入库。
> 5. **严禁伪置信度**：所有关系必须绑定证据与抽取方法，禁止 AI 虚构无证据置信度。
> 6. **AST 是结构事实，不是业务推理 (MVP2 新增冻结)**：Tree-sitter 提取的是客观静态事实，严禁引入 LLM 猜测业务逻辑。业务语义留待 MVP3/4/5。

---

## 📌 架构债务登记簿 (由 MVP1 结项交接)

1. **Technology 分类标准化 (Ontology V0.2)**：将当前混杂的 Framework 细化为 `Framework`, `Runtime`, `UI Library`, `State Management`, `Router`, `ORM`, `HTTP Client`, `Build Tool`, `Testing`，MVP1 保持现状不破坏，在代码语义图完善后统一演进。
2. **前端 Bundle 体积监测 (Engineering Metric)**：当前 Web 端 `index.js` 为 1.73 MB，作为技术债指标持续观测，绝不在 MVP2 提前进行过度优化。

---

## 1. MVP 阶段状态矩阵

| MVP 代号 | 阶段名称 | 当前状态 | 依赖阶段 | 验收状态 | 归档文档 |
|---|---|---|---|---|---|
| **MVP0** | **Environment & Knowledge Core** | **COMPLETED / FROZEN** | 无（起始阶段） | **ALL PASSED** | `docs/mvp/mvp0_acceptance_report.md` |
| **MVP1** | **Project Ingestion (只读扫描/增量)** | **COMPLETED / FROZEN** | MVP0 (已冻结) | **ALL PASSED** | `docs/mvp1/mvp1_acceptance_report.md` |
| **MVP2** | **Code Intelligence & Structural Graph** | **COMPLETED / FROZEN** | MVP1 (已冻结) | **ALL PASSED** | `docs/mvp2/mvp2_acceptance_report.md` |
| **MVP3** | **Hybrid RAG (Keyword+pgvector+Graph)** | **COMPLETED / FROZEN** | MVP1, MVP2 | **ALL PASSED** | `docs/mvp3/mvp3_acceptance_report.md` |
| **MVP4** | **LLM Wiki (带证据投影)** | **COMPLETED / FROZEN** | MVP3 (已冻结) | **ALL PASSED** | `docs/mvp4/mvp4_acceptance_report.md` |
| **MVP5** | **Event & Change Intelligence** | **COMPLETED / FROZEN** | MVP1, MVP2 | **ALL PASSED** | `docs/mvp5/mvp5_acceptance_report.md` |
| **MVP6** | **Laya Decision Engine (4大决策任务)** | **READY_TO_PLAN** | MVP4, MVP5 | 待启动规划 | - |
| MVP7 | Impact Analysis Engine (影响链分析) | **LOCKED** | MVP2, MVP5, MVP6 | 未开始 | - |
| MVP8 | Evaluation / Calibration / Learning Loop | **LOCKED** | MVP6, MVP7 | 未开始 | - |

---

## 2. MVP2 细分步骤规划与状态

| 步骤编号 | 步骤目标 | 计划产出 | 当前状态 | 归档文档 |
|---|---|---|---|---|
| **Step 2.0** | 规划、架构基线固化与前置审查 | 冻结 MVP2 实施基线、确立 6 大红线、登记 2 大架构债务 | **COMPLETED** | `docs/mvp2/mvp2_step0_planning_and_baseline.md` |
| **Step 2.1 (MVP2-A)** | Tree-sitter 基础设施与 Vue SFC 解析 | 现代化 Tree-sitter 预编译依赖引入、ParserFactory、Vue SFC 物理行号对齐切片器、三大工程冒烟测试 | **READY_TO_IMPLEMENT** | `docs/mvp2/mvp2_step1_treesitter_infra.md` |
| **Step 2.2 (MVP2-B)** | 代码符号提取 (Symbol Extraction) | 符号提取器（类、接口、函数、方法、变量、组件、Hook）、确定性 Key 生成、符号实体增量入库 | TODO | `docs/mvp2/mvp2_step2_symbol_extraction.md` |
| **Step 2.3 (MVP2-C)** | 代码结构图谱 (Code Structural Graph) | 单工程结构关系提取（defines, imports, exports, calls, extends）、静态(1.0)与推断(<1.0)置信度分离 | TODO | `docs/mvp2/mvp2_step3_structural_graph.md` |
| **Step 2.4 (MVP2-D)** | 跨工程代码图谱 (Cross-project Graph) | 跨项目公共模块、共享组件与公共依赖静态关联推导 | TODO | `docs/mvp2/mvp2_step4_cross_project_graph.md` |
| **Step 2.5 (MVP2-E)** | 契约端到端追溯 (API to Backend Traceability) | 前端 API Client 路由 ➔ HTTP Endpoint ➔ 后端 Controller ➔ Service ➔ DB 契约追溯链 | TODO | `docs/mvp2/mvp2_step5_api_traceability.md` |
| **Step 2.6** | 全量扫描、Gold Set 回归与 MVP2 终审结项 | 三大工程全量代码图谱入库、只读双重核验、Gold Set 回归测试、终审验收报告与数据库冷备份 | TODO | `docs/mvp2/mvp2_acceptance_report.md` |
