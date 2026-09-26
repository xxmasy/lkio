# LKIO MVP4 (LLM Wiki & Evidence Projection) 实施基线与主规划

> **阶段代号**：**MVP4 (LLM Wiki & Evidence Projection)**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN** (基础环境与模型底座)  
> - **MVP1 = COMPLETED / FROZEN** (三大项目只读摄取、快照与 Git 历史)  
> - **MVP2 = COMPLETED / FROZEN** (代码符号、结构图谱、跨工程依赖、API契约全链路追溯)  
> - **MVP3 = COMPLETED / FROZEN** (五大检索索引、意图路由器、RRF融合重排、101-Query Gold Set)  
> **当前状态**：**IN_PROGRESS**  
> **基线规范**：`LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md` 第 25 ~ 26 节、第 38 节、第 3111 节  
> **核心原则**：知识投影而非真理源、100% 证据锚定、实体变更局部失效 (Stale Detection)、单章节增量更新

---

## 一、🛑 永久冻结架构红线 (MVP4 强制约束)

1. **源项目绝对只读**：`HELLO_FE`、`HELLO_BE`、`L2C_FE` 绝对物理只读，严禁任何写操作或生成临时文件。
2. **Wiki = 知识投影，绝非 Source of Truth**：数据库中的 Entity、Relation、Source、Commit 是唯一真理源。Wiki 只是基于结构事实的具象化投影。
3. **禁止生成无 Evidence 的事实性内容**：Wiki 中的每一个章节、模块描述和架构断言必须带有确凿的 `EvidenceCitation`（文件路径、代码起始行、实体 Key 或 Commit Hash）。
4. **严禁全量重写，强制单章节增量更新**：严禁每次源码变更都触发全量 Wiki 重新生成。必须依据实体依赖图进行 Stale 标记，仅重新生成标记为 `STALE` 的章节。
5. **解耦 LLM 供应商**：上层业务只依赖 `LLMProvider(Protocol)` 接口，支持 `MockOffline`、`Ollama`、`LMStudio/OpenAI-compatible`，换模型绝不影响知识库逻辑。
6. **离线高可靠验证**：所有单元测试与集成测试必须在无外网依赖、无商用 API Key 状态下 100% 通过。

---

## 二、MVP4 核心架构设计

### 1. 13 大标准项目 Wiki 页面规范 (Standard Project Wiki)

根据基线规范第 25.2 节，每个工程必须具备固定的 13 个 Wiki 章节：

| 章节名称 (Section Name) | 核心内容 | 依赖的主要事实源 |
|---|---|---|
| **1. Project Overview** | 项目定位、业务价值、核心角色与运行环境 | `Source`, `Project`, `README.md` |
| **2. Architecture** | 系统分层架构、目录骨架设计、核心模式 | `Entity` (DIRECTORY/MODULE), 架构白皮书 |
| **3. Frontend** | 前端技术栈、组件体系、路由守卫与状态管理 | `Entity` (COMPONENT/PAGE), `package.json` |
| **4. Backend** | 后端服务架构、分层模型、Spring Boot 核心配置 | `Entity` (SERVICE/CLASS/CONTROLLER), `pom.xml` |
| **5. API** | 外部 HTTP 接口清单、前后端契约调用链路 | `GraphIndex` (API Contract Traces, routes_to) |
| **6. Database** | 持久化模型、实体关系、ORM 映射 | `Entity` (MODEL/ENTITY), MyBatis / JPA 映射 |
| **7. Business Domain** | 业务领域模型、聚合根、核心实体概念 | `Entity` (VO/DTO/POJO), 业务文档 |
| **8. Business Process** | 核心业务流程与时序流转（如销售线索流转、工单流转） | 业务规范文档, `Relation` (calls) |
| **9. Business Rules** | 核心计算口径、状态机流转规则、配额分配逻辑 | 规则文档, Service 实现方法与测试用例 |
| **10. Dependencies** | 内部跨模块依赖与外部核心第三方依赖拓扑 | `CrossProjectCandidate` (depends_on, cross_imports) |
| **11. Recent Changes** | 最近演进历史、重要提交与作者变更记录 | `TemporalIndex` (Git commits, file changes) |
| **12. Known Risks** | 架构坏味道、未决技术债、高耦合模块 | `OPEN_QUESTIONS.md`, 异常处理逻辑 |
| **13. Open Decisions** | 待决架构决策、待验证技术路线 | `OPEN_QUESTIONS.md`, 设计备忘录 |

### 2. 状态机与生命周期 (`WikiSectionStatus`)

每个 Wiki Section 具备明确的状态机：

```text
                  Generate / Initialize
                            │
                            ▼
                      [ GENERATED ]
                            │
                   Verify / Audit Pass
                            │
                            ▼
                      [ VERIFIED ]
                            │
                Source Change / AST Mod
                            │
                            ▼
                       [ STALE ] ─────────────┐
                            │                 │ Conflict detected
               Incremental Regenerate         ▼
                            │           [ CONFLICTED ]
                            ▼
                      [ GENERATED ]
```

---

## 三、MVP4 细分子步骤规划

| 步骤代号 | 任务目标 | 核心输出 | 当前状态 |
|---|---|---|---|
| **Step 4.0** | MVP4 规划、架构基线固化与 6 大红线锁死 | `docs/mvp4/mvp4_step0_planning_and_baseline.md` | **COMPLETED** |
| **Step 4.1 (MVP4-A)** | Wiki 数据库实体模型与迁移 (`core/models/wiki.py`) | `WikiSection` 实体模型、4 态生命周期、状态机转换方法 | **READY_TO_IMPLEMENT** |
| **Step 4.2 (MVP4-B)** | Local LLM Gateway 供应商适配器 (`core/rag/gateway/`) | `OllamaProvider`, `OpenAICompatibleProvider`, Gateway Factory | **TODO** |
| **Step 4.3 (MVP4-C)** | 13 大标准 Wiki 章节生成器 (`core/wiki/generators/`) | 13 个专用生成器、结合 MVP3 RAG 事实检索与证据组装 | **TODO** |
| **Step 4.4 (MVP4-D)** | 实体变更失效检测引擎 (`core/wiki/stale_detector.py`) | 实体/文件与 Wiki 章节的依赖拓扑映射与 Stale 检测 | **TODO** |
| **Step 4.5 (MVP4-E)** | 增量重新生成流水线与持久化 (`core/wiki/pipeline.py`) | 批量扫描、Stale 过滤、增量生成与幂等存储 | **TODO** |
| **Step 4.6 (MVP4-F)** | 三大工程全量 Wiki 验收与结项归档 (`tests/integration/step4/`) | 39 个章节全量生成验证、100% 证据覆盖度审计与终审报告 | **TODO** |

---

## 四、MVP4 终审验收门禁 (Verification Gates)

1. **GATE-WIKI-01 (13 Sections Completeness)**: 每个纳管工程必须完整生成 13 个标准 Wiki 章节，三大工程共 39 个章节无遗漏。
2. **GATE-WIKI-02 (100% Evidence Grounding)**: 每个章节的事实陈述必须 100% 附带可溯源的物理证据（`EvidenceCitation`），严禁虚构。
3. **GATE-WIKI-03 (Incremental Stale Regeneration)**: 单文件变更时，仅将直接关联的 Wiki Section 标记为 `STALE` 并增量重新生成，未受影响的章节保持不变。
4. **GATE-WIKI-04 (Zero-Dependency Offline CI)**: 所有单测与集成测试在离线环境下使用本地 Provider 100% 通过。
5. **GATE-WIKI-05 (Source Read-Only Invariance)**: 三大源工程目录持续保持物理只读。
