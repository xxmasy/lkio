# LKIO 持续基础设施演进开发规范

> 文档定位：LKIO 从「静态 Repository Intelligence Prototype」演进为「持续在线、跨仓库、可被 Agent 调用的 Repository Intelligence Infrastructure」的唯一开发基线。
>
> 核心原则：**阶段不可越级、能力不可口头验收、Benchmark 不得为功能迁就、正确性优先于性能、基础设施优先于 Agent 花活。**
>
> 版本：V1.0
> 
> 路线：Real-time Incremental Indexing → Multi-Repo → MCP → Agent Closed Loop
>
> 核心 Gate：Stage 0 → Stage 1 → Gate 1 → Stage 2 → Gate 2 → Stage 3 → Gate 3 → Stage 4 → Final Gate

---

# 0. 总体目标与边界

## 0.1 最终目标

LKIO 最终不是一个“更强的 RAG”，而是一个可以被 Coding Agent 持续调用的 Repository Intelligence Infrastructure：

```text
Repository / Repositories
        ↓
Continuous Indexing
        ↓
AST / Symbol / Dependency Graph
        ↓
Hybrid Retrieval
        ↓
Git / Historical State
        ↓
Impact / Evidence / Decision
        ↓
Unified SDK
        ↓
MCP
        ↓
Cursor / Claude Code / Codex / Other Agents
        ↓
Code Modification
        ↓
Validation
        ↓
LKIO Re-analysis
        ↓
Evidence-backed Decision
```

## 0.2 四阶段固定顺序

```text
Stage 1  实时增量索引
    ↓ Gate 1
Stage 2  Multi-Repo 跨仓库拓扑
    ↓ Gate 2
Stage 3  MCP 基础设施
    ↓ Gate 3
Stage 4  Agent 编码与重构反馈闭环
    ↓ Final Gate
Production Candidate
```

**严禁跳过 Stage 1 直接做 Agent。**

原因：如果 Repository State 不是稳定、可回滚、可验证的事实层，那么 Agent 只会把错误放大。

## 0.3 三层门禁铁律 (Three-tier Gate Hierarchy)

LKIO 必须严格区分三种通过状态，严禁混淆：

```text
             ┌─────────────────────────┐
             │   Gate A: Implementation │
             │   代码功能与接口是否完成 │
             └────────────┬────────────┘
                          ↓
             ┌─────────────────────────┐
             │   Gate B: Benchmark     │
             │   在固定基准测试集上正确 │
             └────────────┬────────────┘
                          ↓
             ┌─────────────────────────┐
             │   Gate C: Production     │
             │   分布、规模、并发、故障 │
             │   真实生产条件下仍然可靠 │
             └─────────────────────────┘
```

- **Gate A (Implementation Complete)**: 核心算法、数据模型与基础单元测试已实现；
- **Gate B (Benchmark Validated)**: 在固定的 Golden/Synthetic 测试集与消融主表上满足指标阈值；
- **Gate C (Production Proven)**: 在百万行级规模、超大跨仓拓扑、高并发读写、故障注入与真实 Agent 市场分布漂移下验证可靠。

**铁律：只有 Gate A ✅ + Gate B ✅ + Gate C ✅ 全部达成，才能宣称“生产级通过（Production Gate Passed）”。否则只能客观标示为“实现完成”或“基准测试通过”。**

---

# 1. 开发总纪律

## 1.1 第一原则：先建立事实层，再建立智能层

允许的顺序：

```text
Repository State
→ Index
→ Graph
→ Evidence
→ Decision
→ MCP
→ Agent
```

禁止：

```text
先做 Agent
→ Agent 自己猜代码
→ 再补索引
```

## 1.2 第二原则：Incremental 与 Full Rebuild 必须可证明等价

任何增量更新完成后，都必须满足：

```text
FullRebuild(repo_after_change)
        ==
IncrementalUpdate(repo_before_change, change_set)
```

等价至少包括：

- Symbol 集合一致
- Symbol Identity 一致
- Definition / Reference 一致
- Dependency Edge 一致
- 删除边一致
- Retrieval Index 一致或满足允许的近似误差协议
- Graph traversal 结果一致
- Impact Analysis 结果一致
- Snapshot metadata 一致

**这是 Stage 1 的最高级别正确性不变量。**

## 1.3 第三原则：Snapshot First

所有写入都必须基于 Snapshot / Revision。

禁止前台查询直接读取“正在更新中的 Graph”。

合法流程：

```text
Current Snapshot
        ↓
Create Candidate Snapshot
        ↓
Apply Delta
        ↓
Validate
        ↓
Publish Atomically
```

如果 Validate 失败：

```text
Candidate Snapshot discard
Current Snapshot untouched
```

## 1.4 第四原则：Benchmark 不能反向迁就实现

测试数据必须先冻结，再实现。

禁止：

- 为了通过测试修改 golden answer
- 为了提升准确率删除难例
- 为了减少 latency 偷掉必要语义边
- 为了提高 recall 放宽 precision 但不记录变化
- 让生产代码复制测试 oracle 的实现逻辑

## 1.5 第五原则：所有性能指标必须区分 P50 / P95 / P99

不得只报告“平均耗时”。

至少记录：

- P50
- P95
- P99
- Max
- 输入规模
- Changed semantic surface area
- Repository size

---

# 2. Stage 0：基线冻结与架构护栏

> Stage 0 不是新功能阶段，而是后续三阶段的防失控层。

## 2.1 目标

冻结现有 LKIO 的正确性基线，使后续增量、跨仓、MCP 改造都可以判断“是否破坏现有能力”。

## 2.2 必须完成

### 2.2.1 当前 Benchmark 冻结

必须冻结当前：

- 15 evaluation layers
- 8 baseline / ablation configurations
- 120 blind decision cases
- Calibration split
- Test split
- manifests.py SHA-256 signatures
- 207 passed / 2 skipped 基线状态

保存：

```text
benchmarks/baseline_v1/
├── manifests/
├── golden/
├── configs/
├── metrics.json
└── README.md
```

### 2.2.2 现有核心不变量冻结

必须保留：

```text
I1 Cycle Safety
I2 Seed Isolation
I3 Depth Bound
I4 Shortest-Hop Preservation
I5 Monotonic Classification
I6 Evidence Accumulation
```

### 2.2.3 统一 Entity Identity

必须确认：

```text
repo_id
snapshot_id
file_id
symbol_id
edge_id
```

未来所有实体都必须有 namespace，不允许裸 symbol name 作为全局唯一标识。

示例：

```text
repo://hello-be/src/service/LeadService.java#LeadService
```

而不是：

```text
LeadService
```

### 2.2.4 Unified SDK 契约冻结第一版

```python
class LKIO:
    search(query, top_k=10)
    symbol(name_or_query)
    references(symbol_key)
    dependencies(seed_key, depth=3)
    impact(changes, depth=3)
    history(symbol_or_path, limit=10)
    snapshot(commit_id)
    explain(entity_key)
    decision(task, payload)
```

此时允许实现内部变化，但公共语义不能随便变化。

## 2.3 Stage 0 Gate

必须全部满足：

```text
[ ] baseline benchmark 可重复运行
[ ] benchmark 结果与冻结版本一致
[ ] 核心 graph invariant 全通过
[ ] 所有实体带 repo/snapshot namespace
[ ] Unified SDK contract 有测试
[ ] 旧接口有兼容策略
[ ] 每个新增模块有 unit test
```

**任一项失败：不得进入 Stage 1。**

---

# 3. Stage 1：Real-time Incremental Indexing

# 3.1 阶段目标

把 LKIO 从：

```text
静态全量扫描 Repository
```

升级为：

```text
Git / Working Tree Change
→ 局部更新
→ 原子发布
→ 查询不中断
```

这里的核心不是“重新解析 changed files”，而是：

> **建立可事务提交、可回滚、可并发查询、可证明与 Full Rebuild 等价的 Repository State Engine。**

---

# 3.2 Stage 1 明确不做的事情

本阶段禁止加入：

- Multi-Repo Graph
- MCP Server
- Agent autonomous editing
- Agent planning
- PR review agent
- 新的复杂 LLM reasoning chain
- 与增量无关的大规模 retrieval 重构

可以为未来留下扩展点，但不能把 Stage 1 变成“大重写”。

---

# 3.3 Change Detection

## 3.3.1 输入来源

至少支持：

1. Git commit
2. Working tree
3. Git webhook / external trigger（接口先预留）

## 3.3.2 Diff 仅负责发现候选变化文件

必须明确：

```text
Unified Diff
≠
AST Semantic Delta
```

合法流程：

```text
Git Diff
↓
Affected Files
↓
Read Old Blob
Read New Blob
↓
Tree-sitter Parse
↓
AST Delta
↓
Symbol Delta
↓
Relationship Delta
```

禁止直接从 diff 行文本推断完整符号关系。

## 3.3.3 Change Classification

必须能够分类：

```text
ADDED
MODIFIED
DELETED
RENAMED
COPIED（可选）
UNCHANGED
```

必须覆盖：

- 文件新增
- 文件删除
- 文件修改
- 文件重命名
- 纯格式变化
- 注释变化
- import 变化
- symbol body 变化
- symbol signature 变化

---

# 3.4 AST 局域增量解析

## 3.4.1 目标

对于 changed files，只重算受影响文件及其必要语义区域。

第一版可以采用：

```text
changed file → parse whole file
```

**这里的“增量”首先是 Repository-level incremental，不要求第一版做到 Tree-sitter node-level incremental。**

原因：

```text
单文件重新 parse
```

与：

```text
全仓 8000+ 文件重新 parse
```

已经是巨大变化。

后续再考虑 AST node-level incremental。

## 3.4.2 必须保留 old/new AST

```text
old_tree
new_tree
```

用于计算：

```text
SymbolDelta
RelationshipDelta
```

---

# 3.5 Symbol Delta Engine

必须支持：

```text
added
modified
deleted
renamed
moved
```

## 3.5.1 Symbol Identity

必须定义 stable identity。

建议至少包含：

```text
repo_id
file path
language
qualified name
parent symbol
symbol kind
```

不能仅使用：

```text
name
```

## 3.5.2 Signature Change

必须能够识别：

```text
foo(a)
→
foo(a, b)
```

并明确标识：

```text
SIGNATURE_CHANGED
```

而不是简单处理成 delete + add 后丢失连续性。

## 3.5.3 Rename / Move

允许第一版使用启发式匹配，但必须输出：

```text
confidence
match_reason
```

不能把猜测直接当确定事实。

---

# 3.6 Relationship Delta Engine

这是 Stage 1 最重要的模块之一。

## 3.6.1 修改一个 Symbol 后必须检查

至少：

- incoming references
- outgoing references
- call edges
- import edges
- type references
- inheritance edges
- implementation edges
- route/API edges（如果当前仓库内已支持）

## 3.6.2 Edge Delta

必须支持：

```text
EDGE_ADDED
EDGE_DELETED
EDGE_MODIFIED
```

## 3.6.3 Stale Edge 清理

禁止出现：

```text
旧 symbol 已删除
↓
旧 edge 仍残留
↓
impact traversal 继续经过旧 edge
```

因此必须专门加入：

```text
stale_edge_detection
```

并要求生产 benchmark：

```text
stale-edge rate = 0%
```

---

# 3.7 Snapshot / Copy-on-Write

推荐模型：

```text
Repository
 └── Branch
      ├── Snapshot 100
      ├── Snapshot 101
      ├── Snapshot 102 ← current
      └── Snapshot 103 ← candidate
```

## 3.7.1 更新流程

```text
Current Snapshot
↓
Clone / Fork Metadata
↓
Apply File Delta
↓
Apply Symbol Delta
↓
Apply Edge Delta
↓
Rebuild Affected Retrieval Data
↓
Run Consistency Validation
↓
Publish Atomic
```

## 3.7.2 Publish 原则

必须满足：

```text
publish(new_snapshot)
```

是原子动作。

如果失败：

```text
current_snapshot 保持不变
```

## 3.7.3 Zero-Downtime

查询线程不能读到：

- 一半新 Graph
- 一半旧 Graph
- 新 Symbol + 旧 Edge
- 新 Embedding + 旧 Symbol metadata

---

# 3.8 Incremental Retrieval Index

必须考虑：

- lexical index 更新
- vector index 更新
- symbol index 更新
- metadata index 更新

第一版可以允许：

```text
Graph fully incremental
Vector index micro-batch
```

但必须显式记录 index freshness：

```text
graph_revision
retrieval_revision
vector_revision
```

不得假装所有索引已经同步。

---

# 3.9 Stage 1 Benchmark

新增：

## Layer 16 — Incremental Correctness

| 测试 | 门槛 |
|---|---:|
| Add file | 100% |
| Delete file | 100% |
| Modify file | 100% |
| Rename file | 100% |
| Add symbol | 100% |
| Delete symbol | 100% |
| Modify symbol | 100% |
| Rename symbol | 100% |
| Signature change | 100% |
| Add edge | 100% |
| Delete edge | 100% |
| Stale edge rate | 0% |
| Query during update | 0 downtime |
| Rollback after failed build | 100% |
| Incremental vs rebuild semantic equivalence | 100% |

## Layer 17 — Incremental Performance

至少测试：

```text
1 changed file
5 changed files
20 changed files
100 changed files
```

每组记录：

```text
Repository LOC
File count
Symbol count
Edge count
Changed files
Changed symbols
Changed edges
P50
P95
P99
Full rebuild time
Incremental time
Speedup
```

## Stage 1 性能目标

目标不是“任何修改都毫秒级”。

应定义：

```text
Update cost ∝ semantic change surface
```

而不是：

```text
Update cost ∝ total repository size
```

建议第一版内部目标：

```text
Single-file small change:
P95 < 500ms

10-file ordinary change:
P95 < 2s

100-file broad change:
P95 < 10s
```

以上是 LKIO 自定义工程目标，不是行业标准；必须随真实规模重新校准。

---

# 3.10 Stage 1 Gate 1：不可越级条件

以下全部满足，才允许 Stage 2：

### 正确性

```text
[ ] Incremental == Full Rebuild
[ ] Symbol delta 全测试通过
[ ] Edge delta 全测试通过
[ ] stale edge = 0
[ ] cycle safety 未回退
[ ] shortest-hop 未回退
[ ] impact F1 未明显回退
[ ] historical benchmark 未回退
```

### 一致性

```text
[ ] 查询永不读半成品
[ ] Snapshot publish 原子
[ ] 更新失败可 rollback
[ ] snapshot revision 可追踪
```

### 性能

```text
[ ] 单文件增量明显优于全量重建
[ ] P50/P95/P99 已记录
[ ] 测试覆盖不同 changed surface area
```

### 工程

```text
[ ] 单元测试
[ ] 集成测试
[ ] 并发测试
[ ] 崩溃恢复测试
[ ] benchmark 自动执行
```

**任何一个核心 correctness gate 不通过，禁止进入 Multi-Repo。**

---

# 4. Stage 2：Multi-Repo Boundary Breaking

# 4.1 阶段目标

从：

```text
Repository-local Intelligence
```

升级到：

```text
Cross-Repository Intelligence
```

核心示例：

```text
HELLO_FE
  ↓ HTTP
HELLO_BE
  ↓ Service
Domain
  ↓ DAO / ORM
Database
```

---

# 4.2 Stage 2 不做什么

禁止：

- Agent autonomous edit
- MCP workflow
- 自动 PR 创建
- 自动 merge
- 自动修复

Stage 2 的任务只是：

> **让 LKIO 正确理解“仓库边界之外”的证据。**

---

# 4.3 Repo Identity

Graph 必须从：

```text
symbol_id
```

升级为：

```text
(repo_id, snapshot_id, entity_id)
```

所有 edge 必须记录：

```text
source_repo
source_snapshot
source_entity
edge_type
target_repo
target_snapshot
target_entity
evidence
confidence
```

---

# 4.4 API Contract Matcher

第一版目标：

```text
Frontend
axios.get('/api/lead/daily-metrics')

        ↕

Backend
@GetMapping('/api/lead/daily-metrics')
```

创建：

```text
API_CALLS
```

边。

## 匹配证据必须分级

```text
EXACT
STRONG
HEURISTIC
UNKNOWN
```

禁止把模糊匹配直接当 EXACT。

---

# 4.5 Contract Matching 层次

优先级建议：

```text
1. OpenAPI / explicit schema
2. Static route annotation
3. Typed client generated from schema
4. Axios / fetch static literal
5. naming heuristic
6. LLM semantic guess
```

越靠后 confidence 越低。

---

# 4.6 DTO / Schema Contract

需要打通：

```text
Frontend TypeScript interface
        ↕
Backend DTO / POJO
        ↕
OpenAPI / JSON Schema
        ↕
Database model（在有明确证据时）
```

第一阶段不要试图“理解所有业务语义”。

只证明：

```text
Field A
存在
类型 X
来源 Y
目标 Z
```

---

# 4.7 Cross-Repo Impact

目标：

```text
Backend DTO field changed
        ↓
Controller
        ↓
API Contract
        ↓
Frontend API client
        ↓
Store
        ↓
Component
```

必须保留 evidence path：

```text
repo A/file X/symbol A
→ API_CALLS
→ repo B/file Y/symbol B
→ REFERENCES
→ repo B/file Z/symbol C
```

不能只输出最终节点。

---

# 4.8 Multi-Repo Graph 安全性

必须重新验证：

- Cycle Safety
- Shortest Path
- Depth Boundary
- Evidence Accumulation
- Duplicate Expansion
- Cross-repo loop

必须有专门 adversarial case：

```text
A repo → B repo → C repo → A repo
```

并保证：

```text
termination = 100%
max depth violation = 0
```

---

# 4.9 Stage 2 Benchmark

新增：

## Layer 18 — Cross-Repo Retrieval

测试：

- API endpoint discovery
- Cross repo symbol discovery
- DTO field lineage
- schema lineage
- client → server mapping

## Layer 19 — Cross-Repo Impact

至少包含：

```text
1-hop cross repo
2-hop cross repo
3-hop cross repo
```

以及：

```text
frontend → backend
backend → frontend
service A → service B
shared SDK → consumers
```

## Layer 20 — Cross-Repo False Positive

必须测试：

- same endpoint name, different service
- same class name, different repo
- same DTO name, different version
- same route path on different service

目标：

```text
false-positive rate <= internally defined threshold
```

阈值必须在 benchmark 冻结后再调整，不允许为了过关事后改阈值。

---

# 4.10 Stage 2 Gate 2

必须满足：

```text
[ ] Repo namespace 完整
[ ] Cross-repo edges 有 evidence
[ ] API contract matcher 有 evidence levels
[ ] DTO/schema lineage 可验证
[ ] Cross-repo cycle safe
[ ] Cross-repo shortest path 正确
[ ] Cross-repo impact benchmark 达标
[ ] False positive 有明确边界
[ ] Existing single-repo benchmark 无明显回退
```

没有通过，禁止 Stage 3 MCP 对外开放。

---

# 5. Stage 3：MCP Infrastructure

# 5.1 阶段目标

把 LKIO 从：

```text
内部代码能力
```

升级为：

```text
可被外部 Agent 标准化调用的事实层
```

核心原则：

> MCP 是 Adapter，不是 Core Engine。

---

# 5.2 MCP 架构

```text
Cursor / Claude Code / Codex / Other Agent
                    ↓
                 MCP
                    ↓
              LKIO Adapter
                    ↓
              LKIO Unified SDK
                    ↓
              LKIO Core Engine
```

禁止在 MCP Tool 中写：

- graph traversal business logic
- retrieval logic
- decision rules
- duplicate implementation

---

# 5.3 MCP Tools 固定第一版

```text
lkio_search
lkio_symbol
lkio_references
lkio_dependencies
lkio_impact
lkio_history
lkio_snapshot
lkio_explain
lkio_decision
```

每个 tool 必须有：

- schema
- required fields
- optional fields
- output schema
- error schema
- timeout
- max result size
- evidence policy
- revision semantics

---

# 5.4 Tool Output 必须结构化

禁止只返回长文本。

例如：

```json
{
  "result": {},
  "snapshot_id": "...",
  "evidence": [],
  "confidence": 0.91,
  "warnings": [],
  "truncated": false
}
```

Agent 必须可以程序化读取：

```text
result
snapshot
confidence
evidence
warnings
```

---

# 5.5 Tool Determinism

相同：

```text
snapshot
query
parameters
```

应该尽可能得到稳定结果。

若存在非确定因素，必须显式标记：

```text
nondeterministic = true
reason = ...
```

---

# 5.6 Permission / Isolation

MCP 第一版建议：**只读**。

允许：

```text
search
symbol
references
dependencies
impact
history
snapshot
explain
decision
```

禁止：

```text
write_file
commit
push
merge
delete
```

原因：

Stage 3 的任务是证明 LKIO 是可靠事实层，不是执行层。

---

# 5.7 MCP Observability

必须记录：

```text
request_id
agent_id（可选）
tool
repo
snapshot
parameters hash
latency
result_count
truncated
confidence
error
```

不得默认记录完整敏感源码内容。

---

# 5.8 Stage 3 Benchmark

需要新增：

```text
Tool Schema Validation
Tool Error Handling
Tool Timeout
Tool Determinism
Concurrent Requests
Snapshot Consistency
Evidence Completeness
```

至少验证：

```text
10 concurrent read queries
100 concurrent mixed read queries
```

以及：

```text
Agent query during snapshot publish
```

必须仍返回完整旧 snapshot 或完整新 snapshot。

不得返回混合状态。

---

# 5.9 Stage 3 Gate 3

```text
[ ] 9 个 core tools 稳定
[ ] schema frozen
[ ] output structured
[ ] no business logic duplication
[ ] read-only safety verified
[ ] concurrency tests passed
[ ] snapshot consistency passed
[ ] errors structured
[ ] latency measured
[ ] observability complete
```

通过后才允许开发 Stage 4 Agent 闭环。

---

# 6. Stage 4：Agent Coding / Refactoring Feedback Loop

# 6.1 阶段目标

把：

```text
Agent 只是问 LKIO
```

变成：

```text
Agent 使用 LKIO 做修改前后的事实验证
```

---

# 6.2 标准闭环

```text
User Requirement
        ↓
Agent
        ↓
LKIO dependencies / references / history
        ↓
Agent Planning
        ↓
Code Modification
        ↓
Diff
        ↓
LKIO impact(diff)
        ↓
Build / Test
        ↓
LKIO Re-index
        ↓
Post-change topology validation
        ↓
Decision Engine
        ↓
Evidence-backed Result
```

---

# 6.3 Agent 不允许直接相信自己的上下文

Agent 的 repository reasoning 必须优先使用：

```text
LKIO evidence
```

而不是只使用：

```text
LLM context guess
```

例如：

```text
“谁调用 MetricsService？”
```

应优先：

```text
lkio_references("MetricsService")
```

而不是让 Agent grep 几个文件然后自行猜测。

---

# 6.4 修改前 Impact

Agent 修改前应执行：

```text
dependencies(seed)
references(seed)
history(seed)
impact(planned_change)
```

形成：

```text
Pre-change Evidence
```

---

# 6.5 修改后 Impact

代码修改以后：

```text
Diff
↓
Incremental Index
↓
Post-change Graph
↓
Impact
↓
Compare Pre/Post
```

必须回答：

```text
What changed?
What depended on it?
What new edges appeared?
What old edges disappeared?
Did declared scope match actual impact?
```

---

# 6.6 Decision Gate

决策模型可以使用：

```text
Laya
LLM
Local Classifier
Rules
Custom Model
```

必须通过接口抽象为：

```python
DecisionEngine
```

LKIO 不应绑定单一模型。

---

# 6.7 Decision 输出

至少：

```json
{
  "choice": "ALLOW|REVIEW|BLOCK",
  "score": 0.91,
  "confidence": 0.88,
  "evidence": [],
  "reason": [],
  "risk": "LOW|MEDIUM|HIGH",
  "policy": "..."
}
```

注意：

> **confidence 不等于 permission。**

高 confidence 也不代表高风险动作应该自动放行。

---

# 6.8 Decision Governance

生产级治理必须考虑：

```text
P(correct)
P(false_positive)
P(false_negative)
Risk cost
Business criticality
Evidence completeness
Test coverage
```

最终策略可能是：

```text
LOW RISK + HIGH CONFIDENCE
→ ALLOW

MEDIUM RISK / MEDIUM CONFIDENCE
→ HUMAN REVIEW

HIGH RISK / INSUFFICIENT EVIDENCE
→ BLOCK
```

具体阈值必须通过治理数据确定，不允许仅凭本地 120 样本硬编码。

---

# 6.9 Stage 4 Benchmark

新增真实 workflow benchmark：

```text
Task
→ Locate
→ Explain
→ Plan
→ Modify
→ Test
→ Impact Validate
→ Decision
```

指标至少包括：

| 指标 | 说明 |
|---|---|
| Task Success | 最终任务是否完成 |
| Localization Accuracy | 是否找到正确修改区域 |
| Impact Precision | 实际影响是否准确 |
| Impact Recall | 是否漏掉影响 |
| Test Pass Rate | 测试通过 |
| Regression Rate | 引入回归 |
| Evidence Coverage | 决策有多少可验证证据 |
| Agent Step Count | Agent 探索步骤 |
| Token Consumption | Token 成本 |
| End-to-end Latency | 完整任务耗时 |

---

# 6.10 Final Gate

Stage 4 不应该以“Agent 会改代码”为完成标准。

必须满足：

```text
[ ] Agent 能使用 LKIO 完成 repository exploration
[ ] Agent 能使用 LKIO 做 pre-change impact analysis
[ ] Agent 修改后可触发 incremental re-index
[ ] Post-change graph 与实际代码一致
[ ] 能发现至少一类真实 regression
[ ] Decision 有 evidence chain
[ ] 高风险任务不会仅因模型 confidence 高而直接放行
[ ] Workflow benchmark 可重复
[ ] 生产安全边界明确
```

---

# 7. 跨阶段统一数据模型

## 7.1 Repository

```python
Repository:
    repo_id
    name
    source
    default_branch
    languages
```

## 7.2 Snapshot

```python
Snapshot:
    snapshot_id
    repo_id
    branch
    commit_id
    parent_snapshot_id
    created_at
    status
```

状态：

```text
BUILDING
VALIDATING
PUBLISHED
FAILED
DISCARDED
```

## 7.3 Entity

```python
Entity:
    entity_id
    repo_id
    snapshot_id
    kind
    qualified_name
    file_path
    span
```

## 7.4 Edge

```python
Edge:
    edge_id
    source_entity
    target_entity
    edge_type
    repo_scope
    snapshot_id
    evidence
    confidence
```

## 7.5 Evidence

```python
Evidence:
    evidence_id
    source_type
    source_location
    snapshot_id
    excerpt
    confidence
```

允许：

```text
AST
STATIC
GIT
API_CONTRACT
SCHEMA
TEXT
HEURISTIC
LLM
```

其中 evidence 必须有 provenance。

---

# 8. 一致性模型

LKIO 未来必须明确区分：

```text
Repository State
Graph State
Retrieval State
Decision State
```

不能假设它们永远瞬时一致。

建议：

```text
repo_revision = R100

Graph revision = R100
Symbol index = R100
Vector index = R99
```

如果出现这种情况，查询结果必须知道：

```text
vector_index_stale = true
```

而不是假装完整一致。

---

# 9. 错误恢复与回滚规范

所有阶段都必须支持：

```text
Build Failure
Parse Failure
Graph Failure
Index Failure
Publish Failure
```

统一策略：

```text
Candidate Snapshot fails
        ↓
Discard candidate
        ↓
Current Snapshot unchanged
```

禁止：

```text
部分成功 → 直接 publish
```

---

# 10. 并发模型

必须覆盖：

```text
Query during update
Multiple readers during publish
Two updates racing
Repeated webhook
Out-of-order webhook
```

第一版允许采用：

```text
single-writer / multi-reader
```

即：

```text
1 writer
N readers
```

后续再考虑并行写入。

---

# 11. 幂等性

以下操作必须幂等：

```text
git webhook replay
same commit processed twice
same file diff processed twice
failed job retry
```

建议使用：

```text
(repo_id, commit_id)
```

作为 commit-level idempotency key。

更细粒度：

```text
(repo_id, snapshot_id, file_path, content_hash)
```

---

# 12. Observability

所有增量更新必须留下：

```text
update_id
repo_id
base_snapshot
candidate_snapshot
commit_id
changed_files
changed_symbols
added_edges
deleted_edges
validation_result
build_latency
publish_latency
status
```

建议输出一条完整流水线事件：

```text
UPDATE_STARTED
FILES_CHANGED
AST_BUILT
SYMBOL_DELTA_READY
EDGE_DELTA_READY
INDEX_UPDATED
VALIDATION_STARTED
VALIDATION_PASSED
SNAPSHOT_PUBLISHED
```

失败则：

```text
UPDATE_FAILED
ROLLBACK_COMPLETED
```

---

# 13. 性能与扩展性基线

阶段一开始就要建立 scale matrix。

至少：

```text
8k files
10k files
50k files
100k files
```

后续目标：

```text
500k files
1M files
```

每个规模记录：

```text
LOC
files
symbols
edges
index size
memory
initial build
incremental update
query latency
P95
P99
```

---

# 14. Regression Policy

每次合并代码必须至少执行：

```text
Existing LKIO-Bench
+
Current Stage Benchmark
+
Unit Tests
+
Integration Tests
```

如果新增功能导致：

```text
Recall ↓
Impact F1 ↓
Temporal ↓
Decision ↓
Calibration ↓
```

必须记录 regression。

禁止为了“整体看起来进步”而删除负向指标。

---

# 15. PR / Commit 规范

建议按照阶段拆分：

```text
feat(index): introduce snapshot abstraction
feat(index): add change detector
feat(index): implement symbol delta
feat(index): implement relation delta
feat(index): implement atomic publish
feat(bench): add incremental correctness suite
feat(bench): add incremental performance suite
```

禁止一个 PR 同时完成：

```text
Incremental + Multi-Repo + MCP + Agent
```

因为无法审计问题来源。

---

# 16. 每阶段必须有独立 Demo

## Stage 1 Demo

演示：

```text
8000+ file repo
↓
修改一个 Java 方法
↓
Git diff
↓
增量更新
↓
不重启
↓
查询立即看到新 Graph
↓
旧边消失
↓
新边存在
```

并展示：

```text
full rebuild = X ms
incremental = Y ms
speedup = X/Y
```

## Stage 2 Demo

```text
FE axios
↓
API Contract
↓
BE Controller
↓
Service
↓
DTO
↓
FE Component
```

然后修改 BE DTO，展示跨仓 Impact。

## Stage 3 Demo

在 Cursor / Claude Code / Codex 中调用：

```text
lkio.symbol
lkio.references
lkio.impact
lkio.history
```

只读。

## Stage 4 Demo

真实重构：

```text
Agent
→ LKIO search
→ LKIO dependencies
→ 修改代码
→ 测试
→ LKIO impact
→ decision
```

---

# 17. 绝对禁止的开发行为

## 禁止 1：未通过 Gate 就进入下一阶段

这是最高优先级规则。

## 禁止 2：为了性能牺牲事实准确性

禁止：

```text
省掉边
↓
速度更快
```

除非结果明确标识 approximate。

## 禁止 3：把启发式猜测包装成确定事实

必须：

```text
exact
strong
heuristic
unknown
```

## 禁止 4：把 confidence 当成 truth

confidence 是模型输出，不是客观事实。

## 禁止 5：把 Laya 固化为 LKIO 核心

Laya 是：

```text
Decision Backend
```

LKIO 是：

```text
Repository Intelligence System
```

必须保持可替换。

## 禁止 6：为了 Demo 偷掉真实边界

例如：

```text
只支持当前项目路径
只支持当前语言
只支持 happy path
```

如果有边界，必须明确记录。

## 禁止 7：把所有问题交给 LLM

结构化关系优先由：

```text
AST
Static Analysis
Git
Graph
Contract
```

LLM 用于：

```text
解释
归纳
决策
不确定语义补充
```

---

# 18. Open Source 策略

LKIO 开源时至少公开：

```text
core/
benchmarks/
docs/
examples/
MCP adapter/
```

## 18.1 必须同时公开 Benchmark

原因：

```text
开源代码
+
开源 benchmark
+
开源 golden data / manifests
```

才能允许第三方复现。

## 18.2 README 的事实边界

必须明确：

```text
LKIO 当前 benchmark 证明的是受控测试集上的 repository reasoning 能力。
不代表已经证明跨组织、跨语言、跨规模的生产泛化能力。
Decision layer 尤其受 sample size 与 distribution shift 影响。
```

## 18.3 不允许的宣传口径

不要写：

```text
SOTA
超越 Sourcegraph
超越所有 GraphRAG
生产级企业 AI
```

除非未来已经有公开、可复现、同口径外部证据。

---

# 19. 最终 Roadmap 表

| 阶段 | 核心目标 | 必须完成 | 禁止进入下一阶段的条件 |
|---|---|---|---|
| Stage 0 | 基线冻结 | benchmark / identity / SDK contract | 基线不可复现 |
| Stage 1 | Incremental Index | delta / snapshot / rollback / equivalence | Incremental ≠ Full Rebuild |
| Stage 2 | Multi-Repo | contract / cross-repo graph / impact | cross-repo evidence 不完整 |
| Stage 3 | MCP | read-only tools / schema / observability | tool 非确定 / snapshot 不一致 |
| Stage 4 | Agent Loop | pre/post impact / validation / decision | Agent 无法形成证据闭环 |
| Final | Production Candidate | scale / reliability / governance | 核心生产安全边界不明确 |

---

# 20. 最终完成定义（Definition of Done）

LKIO 只有同时满足以下条件，才能称为：

> **Continuous Repository Intelligence Infrastructure Candidate**

## Repository State

```text
[ ] 增量更新
[ ] 可回滚
[ ] 原子发布
[ ] 幂等
[ ] 并发安全
```

## Intelligence

```text
[ ] AST
[ ] Symbol
[ ] Graph
[ ] Retrieval
[ ] Git
[ ] Impact
[ ] Decision
```

## Multi-Repo

```text
[ ] API Contract
[ ] DTO / Schema
[ ] Cross-repo Graph
[ ] Cross-repo Impact
```

## Agent Infrastructure

```text
[ ] MCP
[ ] Structured Tools
[ ] Evidence
[ ] Snapshot Awareness
[ ] Observability
```

## Agent Loop

```text
[ ] Discover
[ ] Plan
[ ] Modify
[ ] Test
[ ] Re-index
[ ] Re-impact
[ ] Decide
```

## Governance

```text
[ ] Confidence
[ ] Risk
[ ] Evidence completeness
[ ] Human review gate
[ ] Audit trail
```

## Benchmark

```text
[ ] Existing LKIO-Bench 不回退
[ ] Incremental Benchmark
[ ] Multi-Repo Benchmark
[ ] MCP Benchmark
[ ] Agent Workflow Benchmark
[ ] Scale Benchmark
```

---

# 21. 当前立即执行清单

当前状态：**Stage 1 / Real-time Incremental Indexing**

按以下顺序执行，不允许调整顺序：

```text
01. 冻结现有 LKIO-Bench v1.0
02. 冻结 Repository / Snapshot / Entity Identity
03. 冻结 Unified SDK contract
04. 建立 Snapshot abstraction
05. 建立 Change Detector
06. 建立 old/new blob 获取机制
07. 建立 Symbol Delta
08. 建立 Relationship Delta
09. 建立 stale-edge validation
10. 建立 Candidate Snapshot
11. 建立 validation pipeline
12. 建立 Atomic Publish
13. 建立 rollback
14. 建立 incremental-vs-rebuild oracle
15. 增加 Layer 16 Incremental Correctness
16. 增加 Incremental Performance Benchmark
17. 做并发与故障恢复测试
18. 跑全量 regression benchmark
19. 生成 Stage 1 Report
20. 只有 Gate 1 全部通过后，才能开始 Stage 2
```

---

# 22. 最核心的工程判断

LKIO 下一阶段不是“增加几个功能”，而是完成一次架构范式变化：

```text
过去：
Repository
→ Analyze
→ Answer

现在：
Repository
→ Observe Changes
→ Maintain State
→ Publish Revision
→ Reason Continuously
→ Expose Evidence
→ Serve Agents
→ Validate Agent Actions
```

**Stage 1 的真正产物不是“增量解析功能”，而是 LKIO 的 Repository State Engine。**

**Stage 2 的真正产物不是“支持多个仓库”，而是 Cross-Repository Evidence Graph。**

**Stage 3 的真正产物不是“增加 MCP”，而是把 LKIO 变成标准化事实层。**

**Stage 4 的真正产物不是“让 Agent 会改代码”，而是建立 Agent 修改前后可验证的证据闭环。**

因此整个演进路线的最终核心不变：

> **LKIO 不负责替 Agent 猜，它负责让 Agent 在真实、版本化、可验证的 Repository Evidence 上做决定。**

