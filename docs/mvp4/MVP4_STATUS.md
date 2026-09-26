# LKIO MVP4 (LLM Wiki & Evidence Projection) 执行跟踪与状态总表

> **当前阶段**：**MVP4 (LLM Wiki & Evidence Projection)**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2 = COMPLETED / FROZEN**  
> - **MVP3 = COMPLETED / FROZEN**  
> **当前状态**：**COMPLETED / FROZEN** ✅  
> **实施基线**：`docs/mvp4/mvp4_step0_planning_and_baseline.md`  
> **验收报告**：`docs/mvp4/mvp4_acceptance_report.md`  
> **核心原则**：知识投影而非真理源、100% 证据锚定、实体变更局部失效、单章节增量更新

---

## 🛑 永久冻结架构红线

1. **源项目绝对只读**：`HELLO_FE`、`HELLO_BE`、`L2C_FE` 绝对物理只读，严禁任何写操作或生成临时文件。
2. **Wiki = 知识投影，绝非 Source of Truth**：数据库中的 Entity、Relation、Source、Commit 是唯一真理源。
3. **禁止生成无 Evidence 的事实性内容**：每一个章节必须带有确凿的 `EvidenceCitation`。
4. **严禁全量重写，强制单章节增量更新**：依据实体依赖图进行 Stale 标记，仅重新生成 `STALE` 章节。
5. **解耦 LLM 供应商**：上层业务只依赖 `LLMProvider(Protocol)` 抽象接口。
6. **离线高可靠验证**：所有单元与集成测试在无外网依赖、无商用 API Key 状态下 100% 通过。

---

## MVP4 细分实施步骤规划与状态

| 步骤代号 | 任务目标 | 核心输出 | 当前状态 | 归档文档 |
|---|---|---|---|---|
| **Step 4.0** | MVP4 规划、架构基线固化与 6 大红线锁死 | 冻结实施基线与 6 大红线 | **COMPLETED / FROZEN** | `docs/mvp4/mvp4_step0_planning_and_baseline.md` |
| **Step 4.1 (MVP4-A)** | Wiki 数据库实体模型与迁移 (`core/models/wiki.py`) | `WikiSection` 实体模型与状态机 | **COMPLETED / FROZEN** | `infra/db/alembic/versions/20260926_2000_f7d3a812b345_create_wiki_sections_for_mvp4.py` |
| **Step 4.2 (MVP4-B)** | Local LLM Gateway 供应商适配器 (`core/rag/gateway/`) | `OllamaProvider`, `OpenAICompatibleProvider`, Gateway Factory | **COMPLETED / FROZEN** | `core/rag/gateway/factory.py` |
| **Step 4.3 (MVP4-C)** | 13 大标准 Wiki 章节生成器 (`core/wiki/generators/`) | 13 个专用生成器、RAG 事实检索与证据组装 | **COMPLETED / FROZEN** | `core/wiki/generators/section_generators.py` |
| **Step 4.4 (MVP4-D)** | 实体变更失效检测引擎 (`core/wiki/stale_detector.py`) | 实体/文件与章节依赖拓扑映射与 Stale 检测 | **COMPLETED / FROZEN** | `core/wiki/stale_detector.py` |
| **Step 4.5 (MVP4-E)** | 增量重新生成流水线与持久化 (`core/wiki/pipeline.py`) | Stale 过滤、增量生成与幂等存储流水线 | **COMPLETED / FROZEN** | `core/wiki/pipeline.py` |
| **Step 4.6 (MVP4-F)** | 三大工程全量 Wiki 验收与结项归档 (`tests/integration/step4/`) | 39 章节生成、100% 证据覆盖度审计与验收报告 | **COMPLETED / FROZEN** | `docs/mvp4/mvp4_acceptance_report.md` |
