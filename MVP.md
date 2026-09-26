# LKIO 阶段执行跟踪看板 (MVP.md)

> 当前版本：v0.1  
> 基线文件：[LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md](file:///C:/WorkSpace/lkio/LKIO_%E6%9C%AC%E5%9C%B0%E7%9F%A5%E8%AF%86%E6%99%BA%E8%83%BD%E6%93%8D%E4%BD%9C%E7%B3%BB%E7%BB%9F_MVP%E5%AE%9E%E6%96%BD%E5%9F%BA%E7%BA%BF_v0.1.md)
>
> ### 🛑 永久冻结架构红线（后续任何 Agent 均严禁擅自变更）：
> 1. **三个源项目只读**：`HELLO_FE`, `HELLO_BE`, `L2C_FE` 绝对只读，禁止写回或修改任何文件。
> 2. **MVP1 不引入 Tree-sitter**：代码 AST 解析保留给 MVP2，MVP1 严禁提前引入。
> 3. **Git 一律通过 subprocess 调用 Git CLI**：统一使用标准 Git 命令行工具，保证跨平台一致性与透明度。
> 4. **严禁解析 .git 内部结构**：禁止任何针对 `.git/objects`、`refs`、`index` 等内部二进制文件的直接读取和反序列化。
> 5. **敏感文件永不进入 Knowledge Core**：`.env`, 密钥 (`*.pem`, `*.key`), Token, 私钥, 证书等敏感资产严禁扫描入库。

---

## 1. MVP 状态总表 (每次仅允许一个 ACTIVE MVP)

| MVP 编号 | 阶段名称 | 当前状态 | 阻塞依赖 | 验收门状态 | 阶段结项报告 |
|---|---|---|---|---|---|
| **MVP0** | **Environment & Knowledge Core** | **COMPLETED / FROZEN** | 无 | **ALL PASSED** | [mvp0_acceptance_report.md](file:///C:/WorkSpace/lkio/docs/mvp/mvp0_acceptance_report.md) |
| **MVP1** | **Project Ingestion (只读扫描/增量同步)** | **COMPLETED / FROZEN** | MVP0 (已冻结) | **ALL PASSED** | [mvp1_acceptance_report.md](file:///C:/WorkSpace/lkio/docs/mvp1/mvp1_acceptance_report.md) |
| **MVP2** | **Code Intelligence & Structural Graph** | **COMPLETED / FROZEN** | MVP1 (已冻结) | **ALL PASSED** | [mvp2_acceptance_report.md](file:///C:/WorkSpace/lkio/docs/mvp2/mvp2_acceptance_report.md) |
| **MVP3** | **Hybrid RAG (Keyword+pgvector+Graph)** | **COMPLETED / FROZEN** | MVP1, MVP2 | **ALL PASSED** | [mvp3_acceptance_report.md](file:///C:/WorkSpace/lkio/docs/mvp3/mvp3_acceptance_report.md) |
| **MVP4** | **LLM Wiki (带证据投影)** | **COMPLETED / FROZEN** | MVP3 (已冻结) | **ALL PASSED** | [mvp4_acceptance_report.md](file:///C:/WorkSpace/lkio/docs/mvp4/mvp4_acceptance_report.md) |
| **MVP5** | **Event & Change Intelligence** | **READY_TO_PLAN** | MVP1, MVP2 | 待启动规划 | - |
| **MVP6** | Laya Decision Engine (4大决策任务) | **LOCKED** | MVP4, MVP5 | 未开始 | - |
| **MVP7** | Impact Analysis Engine (影响链分析) | **LOCKED** | MVP2, MVP5, MVP6 | 未开始 | - |
| **MVP8** | Evaluation / Calibration / Learning Loop | **LOCKED** | MVP6, MVP7 | 未开始 | - |

---

## 2. 纳管项目状态

| Project Key | 本地只读路径 | 类型 | 架构角色 | 实体数 | 关系数 | 配对工程 |
|---|---|---|---|---|---|---|
| `HELLO_FE` | `C:\WorkSpace\hello` | frontend | primary_frontend | 3 | 3 | `HELLO_BE` |
| `HELLO_BE` | `C:\WorkSpace\hello-backend` | backend | paired_backend | 3 | 3 | `HELLO_FE` |
| `L2C_FE` | `C:\WorkSpace\L2C project` | frontend | future_frontend | 3 | 2 | 独立 (暂无配对) |

---

## 3. 归档文档索引

- [MVP0 Step 0.1 基础环境与 Docker 容器](file:///C:/WorkSpace/lkio/docs/mvp/mvp0_step1_env_and_infra.md)
- [MVP0 Step 0.2 目录骨架与 Python 依赖](file:///C:/WorkSpace/lkio/docs/mvp/mvp0_step2_backend_and_schema.md)
- [MVP0 Step 0.3 数据库模型与 Alembic 迁移](file:///C:/WorkSpace/lkio/docs/mvp/mvp0_step3_db_models_migration.md)
- [MVP0 Step 0.4 种子数据注入与幂等性核验](file:///C:/WorkSpace/lkio/docs/mvp/mvp0_step4_seed_and_idempotency.md)
- [MVP0 Step 0.5 后端 API 与自动化测试](file:///C:/WorkSpace/lkio/docs/mvp/mvp0_step5_api_and_tests.md)
- [MVP0 Step 0.6 前端控制台与 2D 拓扑图谱](file:///C:/WorkSpace/lkio/docs/mvp/mvp0_step6_frontend_graph.md)
- [MVP0 全量验收与结项报告](file:///C:/WorkSpace/lkio/docs/mvp/mvp0_acceptance_report.md)
