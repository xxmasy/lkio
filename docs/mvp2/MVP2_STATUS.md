# LKIO MVP2 (Code Intelligence & Structural Graph) 执行跟踪与状态总表

> **当前阶段**：**MVP2 (Code Intelligence & Structural Graph)**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> **当前状态**：**READY_TO_IMPLEMENT (BASELINE FROZEN)**  
> **基线规范**：`docs/mvp/MVP2实施基线LKIO — Code Intelligence & Structural Graph.md`  
> **核心原则**：只读、确定性身份、静态事实优于推断、严格隔离业务推理

---

## 🛑 永久冻结的 6 大架构红线

1. **三个源项目只读**：`HELLO_FE`, `HELLO_BE`, `L2C_FE` 绝对物理只读，禁止写回或修改任何文件。
2. **严禁解析 .git 内部结构**：禁止任何针对 `.git` 内部二进制文件的直接读取。
3. **Git 一律通过 subprocess 调用 Git CLI**：统一使用标准 Git 命令行工具，保证跨平台一致性与透明度。
4. **敏感文件永不进入 Knowledge Core**：`.env`, 密钥 (`*.pem`, `*.key`), Token, 私钥, 证书等绝对物理阻断。
5. **严禁伪置信度**：所有关系必须绑定证据与抽取方法，禁止 AI 虚构无证据置信度。
6. **AST 是结构事实，不是业务推理 (MVP2 新增)**：Tree-sitter 提取的是客观结构事实，严禁引入 LLM 猜测业务逻辑。

---

## MVP2 细分实施步骤规划

| 步骤代号 | 步骤目标 | 核心产出 | 当前状态 | 归档文档 |
|---|---|---|---|---|
| **Step 2.0** | 规划、架构基线固化与前置审查 | 冻结 MVP2 实施基线、登记架构债务、确立 6 大红线与步骤规划 | **COMPLETED** | `docs/mvp2/mvp2_step0_planning_and_baseline.md` |
| **Step 2.1 (MVP2-A)** | Tree-sitter 基础设施与 Vue SFC 解析 | 现代化 Tree-sitter 依赖引入、ParserFactory、Vue SFC 坐标金标准、Preflight 验收 | **COMPLETED / FROZEN** | `docs/mvp2/mvp2_a_preflight_report.md` |
| **Step 2.2 (MVP2-B)** | 代码符号提取 (Symbol Extraction) | B-00~B-07 COMPLETED / FROZEN (全语言抽取编排与数据库持久化流水线闭环); B-08 (Real Projects Verification) READY_TO_PLAN | **B-07 COMPLETED / B-08 READY_TO_PLAN** | `docs/mvp2/mvp2_step8_b08_real_projects_verification_plan.md` |
| **Step 2.3 (MVP2-C)** | 代码结构图谱 (Code Structural Graph) | 单工程结构关系提取（defines, imports, exports, calls, extends）、静态(1.0)与推断(<1.0)置信度分离 | LOCKED | `docs/mvp2/mvp2_step3_structural_graph.md` |
| **Step 2.4 (MVP2-D)** | 跨工程代码图谱 (Cross-project Graph) | 跨项目公共模块、共享组件与公共依赖静态关联推导 | TODO | `docs/mvp2/mvp2_step4_cross_project_graph.md` |
| **Step 2.5 (MVP2-E)** | 契约端到端追溯 (API to Backend Traceability) | 前端 API Client 路由 ➔ HTTP Endpoint ➔ 后端 Controller ➔ Service ➔ DB 契约追溯链 | TODO | `docs/mvp2/mvp2_step5_api_traceability.md` |
| **Step 2.6** | 全量扫描、Gold Set 回归与 MVP2 终审结项 | 三大工程全量代码图谱入库、只读双重核验、Gold Set 回归测试、终审验收报告与数据库冷备份 | TODO | `docs/mvp2/mvp2_acceptance_report.md` |
