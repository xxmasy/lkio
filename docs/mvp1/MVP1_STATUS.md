# LKIO MVP1 (Project Ingestion) 执行跟踪与状态总表

> **当前阶段**：**MVP1 (Project Ingestion)**  
> **前置阶段状态**：**MVP0 = COMPLETED / FROZEN**  
> **当前状态**：**COMPLETED / FROZEN**  
> **后续阶段状态**：**MVP2 = READY_TO_PLAN**  
> **基线规范**：`docs/mvp/MVP1实施基线LKIO — Local Knowledge Intelligence OS.md`  
> **核心原则**：只读、可追溯、幂等、可恢复、可验证

---

## 🛑 永久冻结的 5 大架构红线

1. **三个源项目只读**：`HELLO_FE`, `HELLO_BE`, `L2C_FE` 绝对只读，禁止写回或修改任何文件。
2. **MVP1 不引入 Tree-sitter**：代码 AST 解析保留给 MVP2，MVP1 严禁提前引入。
3. **Git 一律通过 subprocess 调用 Git CLI**：统一使用标准 Git 命令行工具，保证跨平台一致性与透明度。
4. **严禁解析 .git 内部结构**：禁止任何针对 `.git/objects`、`refs`、`index` 等内部二进制文件的直接读取和反序列化。
5. **敏感文件永不进入 Knowledge Core**：`.env`, 密钥 (`*.pem`, `*.key`), Token, 私钥, 证书等敏感资产严禁扫描入库。

---

## MVP1 细分实施步骤规划

| 步骤编号 | 步骤目标 | 计划产出 | 当前状态 | 归档文档 |
|---|---|---|---|---|
| **Step 1.1** | 数据表扩展与 Alembic 迁移 | `ingestion_runs` 与 `project_snapshots` 表结构定义与数据库迁移 | **COMPLETED** | `docs/mvp1/mvp1_step1_schema_migration.md` |
| **Step 1.2** | Git CLI 客户端与只读文件系统扫描器 | `subprocess` 安全调用 Git、敏感文件强过滤、文件属性与哈希计算、目录反推 | **COMPLETED** | `docs/mvp1/mvp1_step2_git_and_fs_scanner.md` |
| **Step 1.3** | 清单解析、语言推导与框架检测器 | `package.json`/`pom.xml`/`pyproject.toml` 依赖提取、语言与框架证据生成 | **COMPLETED** | `docs/mvp1/mvp1_step3_manifest_and_framework.md` |
| **Step 1.4** | 完整 Ingestion Pipeline、幂等入库与 CLI | 实体与关系入库、删除标记、快照审计、部分失败隔离与命令行工具 | **COMPLETED** | `docs/mvp1/mvp1_step4_pipeline_and_cli.md` |
| **Step 1.5** | 后端扫描 API 与前端工程详情看板 | Scan API、项目扫描历史展示、框架语言与依赖展示、触发扫描交互 | **COMPLETED** | `docs/mvp1/mvp1_step5_api_and_ui.md` |
| **Step 1.6** | 三项目全量真实扫描、Gold Set 与验收结项 | 真实扫描三大工程、只读性严格双核验、Gold Set 回归测试、终审验收报告 | **COMPLETED** | `docs/mvp1/mvp1_acceptance_report.md` |
