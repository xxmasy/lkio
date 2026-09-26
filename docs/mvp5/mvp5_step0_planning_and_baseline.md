# LKIO MVP5 (Event & Change Intelligence) 实施基线与架构规划

> **阶段代号**：**MVP5**  
> **阶段名称**：**Event & Change Intelligence（事件与变更时空智能）**  
> **前置依赖**：MVP0 (FROZEN), MVP1 (FROZEN), MVP2 (FROZEN), MVP3 (FROZEN), MVP4 (FROZEN)  
> **当前状态**：**IN_PROGRESS (ACTIVE)**  
> **基线依据**：`LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md` 第 27 条（Event / Change Intelligence）、第 28 条（Temporal Query）、第 3120 行（MVP5 验收条目）

---

## 一、MVP5 核心定位与设计原则

根据实施基线第 27.1 条：
> **“Event 是整个系统的时间骨架 (Temporal Backbone)。”**

在 LKIO 架构中：
- MVP0~MVP2 构建了**静态知识图谱**（Projects, Entities, Relations, Symbols, AST）。
- MVP3~MVP4 构建了**检索与知识投影**（Hybrid RAG, Evidence-grounded Wiki）。
- **MVP5 赋予系统时序与演变感知能力**：代码和业务不是静止的，而是沿着时间轴通过 Commit、PR、文件修改、实体变更、配置调整等事件不断演进。
- MVP5 是后续 **MVP6 (Laya Decision Engine)** 与 **MVP7 (Impact Analysis Engine)** 的时间基石。

---

## 二、🛑 永久冻结架构红线 (Inviolable Redlines)

1. **源项目绝对物理只读**：
   - `HELLO_FE`、`HELLO_BE`、`L2C_FE` 绝对只读。
   - 严禁任何写操作、临时文件或工作区污染。Git 操作后 `git status --porcelain` 必须严格保持空或原状。
2. **Git 一律通过 subprocess 调用 Git CLI**：
   - 严禁解析 `.git/` 内部二进制文件（objects, refs, packfile, index）。跨平台统一透明调用标准 Git CLI。
3. **禁止全量保存 Patch Diff 文本（防数据膨胀）**：
   - 依据基线第 27.3 条红线：“第一版不要全文保存所有 patch；只保存：commit SHA, changed file, diff summary (insertions/deletions/change_type), hash。必要时再读取 Git 原始 diff。”
4. **确定性 Event Key 与双 Pass 绝对幂等性**：
   - 每一个 Event 必须拥有全局确定性唯一键 `event_key`（例如 `EVENT:<project_key>:COMMIT:<sha>`、`EVENT:<project_key>:FILE_CHANGED:<sha>:<rel_path>`）。
   - 相同事件重复扫描必须幂等，严禁产生重复记录或无序漂移。
5. **事件与实体拓扑双向锚定**：
   - `FILE_CHANGED` 事件按文件路径自动与现有 `Entity`（文件、模块、符号、路由）关联合成 `ENTITY_CHANGED` 事件，保持图谱与时间线的无缝联动。
6. **离线高可靠验证**：
   - 测试必须具备无依赖可执行性，支持内存/SQLite 与 PostgreSQL，单体离线环境通过率 100%。

---

## 三、数据库设计：`events` 数据模型与状态机

### 1. `events` 核心表结构（基线 27.2 规范）

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    event_key TEXT UNIQUE NOT NULL,                       -- 确定性全局唯一键 (LKIO 幂等底座)
    event_type VARCHAR(64) NOT NULL,                      -- COMMIT, FILE_CHANGED, ENTITY_CHANGED, API_CHANGE 等
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(id) ON DELETE SET NULL, -- 关联变更实体
    actor_type VARCHAR(32) NOT NULL,                      -- git, human, system, ci, ai
    actor_id VARCHAR(255) NOT NULL,                       -- author email / system id
    timestamp TIMESTAMPTZ NOT NULL,                       -- 事件发生时间 (authored_at)
    before_state JSONB NOT NULL DEFAULT '{}',             -- 变更前状态概要
    after_state JSONB NOT NULL DEFAULT '{}',              -- 变更后状态概要
    reason TEXT,                                          -- 变更原因 / commit subject
    source_type VARCHAR(64) NOT NULL,                     -- git_commit, pull_request, manual
    source_id UUID,                                       -- 关联 source 记录 (可选)
    confidence NUMERIC(6,5) NOT NULL DEFAULT 1.00000,     -- 静态事实置信度为 1.0
    metadata JSONB NOT NULL DEFAULT '{}',                 -- commit_sha, file_rel_path, insertions, deletions 等
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 索引规划
CREATE INDEX ix_events_project_id ON events (project_id);
CREATE INDEX ix_events_entity_id ON events (entity_id);
CREATE INDEX ix_events_event_type ON events (event_type);
CREATE INDEX ix_events_timestamp ON events (timestamp);
CREATE INDEX ix_events_project_timestamp ON events (project_id, timestamp DESC);
CREATE UNIQUE INDEX ix_events_event_key ON events (event_key);
```

### 2. 标准 EventType 枚举体系（基线 27.1）

```python
class EventType(str, Enum):
    # Git & 代码变更核心时序事件
    COMMIT = "COMMIT"
    FILE_CHANGED = "FILE_CHANGED"
    ENTITY_CHANGED = "ENTITY_CHANGED"

    # 基线 27.1 业务与系统事件类型
    CODE_CHANGE = "CODE_CHANGE"
    REQUIREMENT_CHANGE = "REQUIREMENT_CHANGE"
    BUSINESS_RULE_CHANGE = "BUSINESS_RULE_CHANGE"
    API_CHANGE = "API_CHANGE"
    DATABASE_CHANGE = "DATABASE_CHANGE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    DEPLOYMENT = "DEPLOYMENT"
    INCIDENT = "INCIDENT"
    OPERATION = "OPERATION"
    DOCUMENT_CHANGE = "DOCUMENT_CHANGE"
    AI_DECISION = "AI_DECISION"
    HUMAN_DECISION = "HUMAN_DECISION"
    METRIC_CHANGE = "METRIC_CHANGE"
```

---

## 四、时空查询引擎 (Temporal Query Engine)

实现基线第 28 条规定的 4 类核心历史时序查询：
1. **项目与实体时间线 (Timeline)**：
   - `get_project_timeline(project_id, start_time, end_time, event_types, limit, offset)`
   - `get_entity_timeline(project_id, entity_id_or_key, limit)`
   - `get_file_timeline(project_id, file_rel_path, limit)`
2. **首次出现查询 (First Appearance Query)**：
   - 目标：解答“这个 API / 实体是什么时候第一次出现的？”
   - 行为：溯源最早的引入事件与关联 Commit/Author。
3. **变更频次与审计分析 (Change Frequency & Audit)**：
   - 目标：解答“这个业务规则 / 文件改过几次？谁修改的？”
   - 行为：统计历史变更分布、修改频次热点与作者画像。
4. **增量变更追溯 (Changes Since Commit)**：
   - 目标：解答“某次 commit / 部署之后发生了什么变更？”
   - 行为：获取指定 commit 或时间点之后所有波及的 Commit、File、Entity 集合。

---

## 五、实施步骤规划

| 步骤代号 | 任务目标 | 核心输出 |
|---|---|---|
| **Step 5.0** | MVP5 实施基线、架构红线与表结构设计 | `docs/mvp5/mvp5_step0_planning_and_baseline.md` |
| **Step 5.1 (MVP5-A)** | Event 实体模型、枚举与 Alembic 迁移脚本 | `core/models/event.py`, `infra/db/alembic/versions/` |
| **Step 5.2 (MVP5-B)** | Git 时序变更提取器 (`GitChangeExtractor`) | `core/events/git_extractor.py` (CLI Subprocess, 0 diff bloat) |
| **Step 5.3 (MVP5-C)** | 事件增量摄取流水线与幂等存储 | `core/events/pipeline.py` (Double-pass idempotent) |
| **Step 5.4 (MVP5-D)** | 时空查询引擎 (`TemporalQueryEngine`) | `core/events/temporal_engine.py` (Timeline, First Appearance, Frequency) |
| **Step 5.5 (MVP5-E)** | 三大工程全量真实事件验收测试 | `tests/integration/step5/test_mvp5_events_acceptance.py` |
| **Step 5.6 (MVP5-F)** | 终审结项报告与状态看板冻结 | `docs/mvp5/mvp5_acceptance_report.md`, `MVP.md` |
