# LKIO MVP5 (Event & Change Intelligence) 执行跟踪与状态总表

> **当前阶段**：**MVP5 (Event & Change Intelligence)**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2 = COMPLETED / FROZEN**  
> - **MVP3 = COMPLETED / FROZEN**  
> - **MVP4 = COMPLETED / FROZEN**  
> **当前状态**：**COMPLETED / FROZEN** ✅  
> **实施基线**：`docs/mvp5/mvp5_step0_planning_and_baseline.md`  
> **验收报告**：`docs/mvp5/mvp5_acceptance_report.md`  
> **核心原则**：Event 为系统时间骨架、严禁全量保存 Patch 文本、确定性 Event Key 幂等去重、实体双向关联

---

## 🛑 永久冻结架构红线

1. **源项目绝对只读**：`HELLO_FE`、`HELLO_BE`、`L2C_FE` 物理只读，禁止写回任何变更或生成临时文件。
2. **Git 一律通过 subprocess 调用 Git CLI**：严禁解析 `.git/` 内部二进制文件。
3. **禁止全量保存 Patch Diff 文本**：只保存 commit SHA, changed file, diff summary (insertions/deletions/change_type), hash，防数据膨胀。
4. **确定性 Event Key 与双 Pass 绝对幂等性**：依据 `(project_key, event_type, ...)` 计算确定性 `event_key`，重扫 0 重复。
5. **事件与实体拓扑双向关联**：文件变更事件自动关联合成实体变更事件。
6. **离线高可靠验证**：所有测试在无外网、无商业 API 状态下 100% 通过。

---

## MVP5 细分实施步骤规划与状态

| 步骤代号 | 任务目标 | 核心输出 | 当前状态 | 归档文档 |
|---|---|---|---|---|
| **Step 5.0** | MVP5 规划、架构基线固化与 6 大红线锁死 | 冻结实施基线与 6 大红线 | **COMPLETED / FROZEN** | `docs/mvp5/mvp5_step0_planning_and_baseline.md` |
| **Step 5.1 (MVP5-A)** | Event 实体模型、枚举与 Alembic 迁移脚本 | `core/models/event.py`, `infra/db/alembic/versions/` | **COMPLETED / FROZEN** | `core/models/event.py` |
| **Step 5.2 (MVP5-B)** | Git 时序变更提取器 (`GitChangeExtractor`) | `core/events/git_extractor.py` (CLI Subprocess, 0 diff bloat) | **COMPLETED / FROZEN** | `core/events/git_extractor.py` |
| **Step 5.3 (MVP5-C)** | 事件增量摄取流水线与幂等存储 | `core/events/pipeline.py` (Double-pass idempotent) | **COMPLETED / FROZEN** | `core/events/pipeline.py` |
| **Step 5.4 (MVP5-D)** | 时空查询引擎 (`TemporalQueryEngine`) | `core/events/temporal_engine.py` (Timeline, First Appearance, Frequency) | **COMPLETED / FROZEN** | `core/events/temporal_engine.py` |
| **Step 5.5 (MVP5-E)** | 三大工程全量真实事件验收测试 | `tests/integration/step5/test_mvp5_events_acceptance.py` | **COMPLETED / FROZEN** | `tests/integration/step5/test_mvp5_events_acceptance.py` |
| **Step 5.6 (MVP5-F)** | 终审结项报告与状态看板冻结 | `docs/mvp5/mvp5_acceptance_report.md`, `MVP.md` | **COMPLETED / FROZEN** | `docs/mvp5/mvp5_acceptance_report.md` |
