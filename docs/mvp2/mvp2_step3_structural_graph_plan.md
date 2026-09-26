# LKIO MVP2-C 代码结构图谱主架构实施规划 (Code Structural Graph Master Plan - Revised Baseline)

> **阶段代号**：`MVP2-C` (Code Structural Graph — 代码结构图谱)  
> **上游基石**：`MVP2-B (100% COMPLETED / FROZEN)`（代码符号提取、身份体系与真实工程验证全量冻结）  
> **当前状态**：**`READY_TO_PLAN ➔ PLAN_FROZEN (Ready for C-00)`**  
> **规划目标**：在已冻结的 MVP2-B 符号与文件实体基础之上，构建工程级代码结构图谱。严格遵循“静态结构事实”与“符号解析/调用推断”两层分离架构，确立关系作为逻辑图边的粒度契约、未决到解析的身份绝对稳定契约、确定性单一主键模型、强类型 DTO 流水线与高吞吐幂等持久化。

---

## 一、架构全景与两层演化流水线 (Two-tier Graph Architecture)

MVP2-C 坚守**单向消费原则**：MVP2-B 产出的 `Entity (FILE / SYMBOL)` 与 `Relation (defines)` 作为底层冻结事实输入，MVP2-C 严禁对源码重新进行符号定义抽取，专注提取和推导实体之间的结构关系。

```text
                            MVP2-B 冻结底座 (Frozen Foundation)
                 ┌────────────────────────────────────────────────────────┐
                 │  Persisted Entities (FILE, CLASS, METHOD, etc.)        │
                 │  + Provenance Edges (FILE -- defines --> SYMBOL)       │
                 └───────────────────────────┬────────────────────────────┘
                                             │ (只读单向消费)
                                             ▼
                 ══════════════════════════════════════════════════════════
                                  MVP2-C 两层抽取与解析架构
                 ══════════════════════════════════════════════════════════
                   Tier 1: 静态显式结构事实层 (C-01 ~ C-04)
                   ┌────────────────────────────────────────────────────┐
                   │  imports, exports, extends, implements             │
                   │  (AST 显式语法声明，100% 事实，relation_kind=STATIC) │
                   │  (imports/exports: FILE ➔ FILE 模块依赖)            │
                   │  (extends/implements: SYMBOL ➔ SYMBOL 类型继承)    │
                   └─────────────────────────┬──────────────────────────┘
                                             │
                                             ▼
                   Tier 2: 作用域解析与调用推断层 (C-05 ~ C-08)
                   ┌────────────────────────────────────────────────────┐
                   │  Deterministic ResolverContext (路径/别名/限定名)    │
                   │  calls, constructor invocation                     │
                   │  (分流: RESOLVED ➔ 内部实体, UNRESOLVED ➔ 外部/未决) │
                   │  (分层: STATIC=1.00000 vs INFERRED < 1.00000)       │
                   │  (身份稳定: UNRESOLVED ➔ RESOLVED Key 绝对不漂移)    │
                   └─────────────────────────┬──────────────────────────┘
                                             │
                                             ▼
                                     RelationCandidate DTO
                                 (Strongly Typed Enums)
                                             │
                                             ▼
                                Relation Identity Anchor
                                (relation_key TEXT UNIQUE)
                                             │
                                             ▼
                          Relation Persistence & Idempotency Pipeline
                               (Occurrences Evidence Aggregation)
                                             │
                                             ▼
                 ══════════════════════════════════════════════════════════
                   Tier 3: 系统级验证与性能基准 (C-09)
                 ══════════════════════════════════════════════════════════
                   三大真实项目 (4,618 文件) 结构图谱验证 + 双 Pass 恒等性证明
```

---

## 二、十二大架构锁设计 (LOCK-GRAPH-01 ~ LOCK-GRAPH-12)

为防止关系提取过程中的语义倒灌、身份漂移、边爆炸与黑盒丢弃，MVP2-C 确立 12 大不可突破的架构红线：

| 锁编号 | 架构锁名称 | 严格定义与不可突破边界 | 破坏后果与防御机制 |
|---|---|---|---|
| **`LOCK-GRAPH-01`** | **Frozen Symbol Consumer** | MVP2-C 仅作为下游消费者，严格消费 MVP2-B 已持久化的 `Entity` 与 `defines` 关系事实。**严禁为了图谱构建反向修改 B-03 ~ B-07 的符号抽取器、Key 算法或持久化契约**。 | 防御符号身份语义污染，保证 MVP2-B 基石 100% 不变性。 |
| **`LOCK-GRAPH-02`** | **Relation Identity 确定性** | 关系身份独立于实体身份。关系的逻辑唯一性由确定性 `relation_key` 保证，格式锁死为不可变锚点公式。`relation_key TEXT UNIQUE NOT NULL` 是数据库唯一的逻辑防重权威。 | 杜绝图谱边的重复插入、主键漂移与复合主键语义冲突。 |
| **`LOCK-GRAPH-03`** | **Static 与 Inferred 严格两级分层** | 关系必须具备强类型枚举 `RelationKind: STATIC \| INFERRED`：<br>1. **`STATIC`**：AST 语法明确声明（如 explicit import/extends），置信度严格恒等于 `Decimal("1.00000")`；<br>2. **`INFERRED`**：多态调度、启发式解析，置信度严格 `< Decimal("1.00000")`。严禁混淆“语法事实”与“推断估算”。 | 保证代码结构基准数据具有 100% 确定性，推断数据可独立过滤审计。 |
| **`LOCK-GRAPH-04`** | **静态关系与调用推断严格解耦** | 将结构事实（`imports`, `exports`, `extends`, `implements`）与调用图（`calls`）物理隔离在不同阶段实施。**严禁在未建立完备模块与继承图谱前，一上来就构建调用图**。 | 避免在缺乏类型上下文时陷入多态与重载的解析泥潭。 |
| **`LOCK-GRAPH-05`** | **RelationCandidate DTO 强类型管道** | AST 关系提取器严禁直接调用 SQL 写入数据库。必须全部产出强类型不可变的 `RelationCandidate` DTO（使用 `Enum` 约束类型），经由统一解析器与持久化管道批量入库。 | 彻底杜绝拼写错误（如 `"impotrs"`），保证测试与运行期的强类型安全。 |
| **`LOCK-GRAPH-06`** | **未决目标显式沉淀契约 (Unresolved Policy)** | 面对第三方库（npm/Maven）或未索引源码中的目标实体，**严禁静默丢弃 (Drop)**。必须作为可观测事实沉淀：`resolution_status = UNRESOLVED`，`object_entity_id = NULL`，且保留 `raw_target` 原始标识符。 | 外部边界（SDK/第三方库）是架构全景的关键组成部分，丢弃会导致图谱断裂。 |
| **`LOCK-GRAPH-07`** | **分层两阶段演进 (Two-tier Stages)** | MVP2-C 划分为两大内部阶梯：Tier 1（C-01 ~ C-04 静态显式结构关系）与 Tier 2（C-05 ~ C-08 作用域解析与调用推断），逐级验收冻结。 | 杜绝大一统交付导致的验收黑盒与回归爆炸。 |
| **`LOCK-GRAPH-08`** | **三大外部工程绝对物理只读与双 Pass 幂等** | 继承严格只读铁律：验证过程严禁修改 `HELLO_FE`, `HELLO_BE`, `L2C_FE` 任何文件（`git status --porcelain` 增量严格为 0）。图谱写入必须满足双 Pass 恒等：Pass 2 `created=0, deleted=0, updated=N`，关系集合 100% 恒等。 | 保护外部宿主环境，确保企业级重复执行的生产确定性。 |
| **`LOCK-GRAPH-09`** | **关系粒度契约 (Edge vs Occurrence)** | **Relation 严格代表图中的单一有向逻辑边 (Logical Edge)，Occurrence 代表源码发生位点 (Source Occurrence)**。同一方法内对同一目标的多次调用（如 line 10 和 line 15 的 `foo()`）只产生一条 `Relation`，多次调用位点聚合到 `evidence["occurrences"]` 数组中。 | 杜绝边爆炸，保证图谱拓扑紧凑，同时无损保留全量源码证据点。 |
| **`LOCK-GRAPH-10`** | **解析身份绝对稳定契约 (Resolution Identity Stability)** | 当关系从 `UNRESOLVED` 原地升级为 `RESOLVED` 时，**`relation_key` 必须保持 100% 绝对不变**！`relation_key` 仅基于源码中不可变的 Anchor 计算，`object_entity_id` 与 `resolution_status` 仅作为属性更新。 | 杜绝状态自愈或模块加载时的“删除旧 Key 插入新 Key”主键漂移。 |
| **`LOCK-GRAPH-11`** | **谓词与实体粒度正交契约 (Predicate & Target Granularity)** | `imports` / `exports` 在 Tier 1 严格定义为 **`FILE ➔ FILE`（模块间依赖）**。具体的符号绑定（如 `{ A, B as C }`）进入 `metadata["import_specifiers"]`。Vue `<template>` 组件引用记录于 `metadata["template_references"]`，严禁提前私自新增 `uses` / `renders` 谓词。 | 保证各 Predicate 的主客体粒度纯净正交，杜绝图谱语义混乱。 |
| **`LOCK-GRAPH-12`** | **单一防重权威与无截断存储 (Single Authority & No Truncation)** | 数据库由 `relation_key TEXT UNIQUE NOT NULL` 承担唯一的逻辑与物理防重。`raw_target` 字段在数据库中严格定义为 `TEXT` 类型，严禁静默截断（Silent Truncation）。 | 继承 MVP2-B 存储安全哲学，彻底消除超长标识符截断导致的关系碰撞。 |

---

## 三、关系身份与 Relation Key 形式化规范 (Relation Identity Specification)

为实现 `LOCK-GRAPH-10`（解析身份绝对稳定），`relation_key` 必须与后期的解析结果（`object_entity_id`）彻底解耦，仅依赖**源码发生上下文的不可变锚点 (Immutable Source Anchor)**：

### 1. Relation Key 格式定义
```text
RELATION:{project_key}:{subject_entity_key}:{predicate}:{normalized_raw_target}:{relation_kind}:{candidate_discriminator}
```

各分量定义与不可变性保证：
1. **`project_key`**：项目唯一标识（如 `"HELLO_BE"`）；
2. **`subject_entity_key`**：关系的发生者主体 Key（如 `FILE:HELLO_BE:src/main/.../OrderController.java` 或 `SYMBOL:HELLO_BE:...:METHOD:submit:...`）；
3. **`predicate`**：强类型关系谓词（`imports`, `exports`, `extends`, `implements`, `calls`）；
4. **`normalized_raw_target`**：源码中引用的**目标字面量标准化字符串**：
   - TS/JS Import: `"./utils"`, `"@/store/user"`, `"lodash/cloneDeep"`
   - Java Import: `"com.example.service.OrderService"`, `"java.util.List"`
   - Extends/Implements: `"BaseService"`, `"OrderService"`
   - Calls: `"orderService.calculateTotal"`, `"new OrderRecord"`
   - **核心保证**：这是 AST 静态提取的原生事实，无论项目内是否找得到实体，该字符串永不改变！
5. **`relation_kind`**：`"STATIC"` 或 `"INFERRED"`；
6. **`candidate_discriminator`**：静态关系恒等于 `"default"`；仅在 C-07 多态推断生成多个候选目标时使用（如针对不同实现类的歧义派发 `"impl_OrderServiceImpl"`）。

### 2. 状态跃迁恒等性证明 (Invariance Proof under Resolution)

```text
阶段 T1 (源码首次扫描, 未决状态):
  subject_entity_key      = "FILE:HELLO_FE:src/views/User.vue"
  predicate               = "imports"
  normalized_raw_target   = "@/store/user"
  relation_kind           = "STATIC"
  candidate_discriminator = "default"
  ----------------------------------------------------------------------------------------
  relation_key            = "RELATION:HELLO_FE:FILE:HELLO_FE:src/views/User.vue:imports:@/store/user:STATIC:default"
  object_entity_id        = NULL
  resolution_status       = "UNRESOLVED"

阶段 T2 (Resolver 加载 tsconfig 别名, 原地解析成功):
  subject_entity_key      = "FILE:HELLO_FE:src/views/User.vue"
  predicate               = "imports"
  normalized_raw_target   = "@/store/user"
  relation_kind           = "STATIC"
  candidate_discriminator = "default"
  ----------------------------------------------------------------------------------------
  relation_key            = "RELATION:HELLO_FE:FILE:HELLO_FE:src/views/User.vue:imports:@/store/user:STATIC:default" (100% 恒等不变!)
  object_entity_id        = 8f4c2e11-7a91-4c12-9c12-32a514d2e109 (绑定到 src/store/user.ts)
  resolution_status       = "RESOLVED"
```

**结论**：`relation_key` 作为主键在整个生命周期内物理无颠簸，`resolution_status` 与 `object_entity_id` 的变更只是原地属性更新，完美落实 `LOCK-GRAPH-10`。

---

## 四、谓词与实体粒度矩阵 (Predicate & Target Granularity Matrix)

根据 `LOCK-GRAPH-09` 与 `LOCK-GRAPH-11`，五大核心关系谓词的主客体粒度与证据模型严格规范如下：

| 谓词 (Predicate) | 主体类型 (Subject) | 客体类型 (Object) | 语义定义 | 发生位点与证据模型 (Evidence / Metadata) |
|---|---|---|---|---|
| **`imports`** | `FILE` | `FILE` (内部) 或 `NULL` (外部/未决) | 模块/文件间依赖关系 | `raw_target: "./utils"`<br>`metadata.import_specifiers: [{"imported": "A", "local": "C"}]`<br>`metadata.is_type_only: bool` |
| **`exports`** | `FILE` | `FILE` (重导出) 或 `SYMBOL` (模块导出) | 模块向外暴露的接口 | `raw_target: "./bar"` 或 `raw_target: "MyService"`<br>`metadata.is_default: bool`<br>`metadata.exported_name: str` |
| **`extends`** | `CLASS` / `INTERFACE` | `CLASS` / `INTERFACE` 或 `NULL` | 类型继承关系 | `raw_target: "BaseController"`<br>`evidence.ast_node: "extends_clause"` |
| **`implements`** | `CLASS` / `ENUM` | `INTERFACE` 或 `NULL` | 接口实现关系 | `raw_target: "OrderService"`<br>`evidence.ast_node: "implements_clause"` |
| **`calls`** | `METHOD` / `FUNCTION` | `METHOD` / `FUNCTION` / `CONSTRUCTOR` 或 `NULL` | 方法/函数调用关系 | `raw_target: "calcTotal"`<br>`evidence.occurrences: [{"line": 10, "args": 2}, {"line": 15, "args": 2}]` |

### Vue Template 边界特别约定
Vue SFC 的 `<template>` 中对组件的标签引用（如 `<UserCard :id="userId" />`）：
- 模块依赖已经由 `<script>` 中的 `import UserCard from './UserCard.vue'` 显式确立（`FILE --imports--> FILE`）；
- 模板渲染事实严格作为属性写入该关系元数据：`metadata["template_references"] = [{"tag": "UserCard", "line": 4}]`；
- **严禁提前扩展 `uses`, `renders` 等非受控谓词**，严格保持图谱关系的精简与纯粹。

---

## 五、强类型 DTO 规范 (Strongly-Typed RelationCandidate)

```python
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class RelationKind(str, Enum):
    STATIC = "STATIC"        # AST 语法明确声明的事实 (confidence == 1.00000)
    INFERRED = "INFERRED"    # 多态分发、启发式匹配推断 (confidence < 1.00000)


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"    # 成功解析并绑定至项目内已知 Entity
    UNRESOLVED = "UNRESOLVED"# 外部依赖 (npm/Maven/JDK) 或项目内未索引实体


class RelationPredicate(str, Enum):
    IMPORTS = "imports"
    EXPORTS = "exports"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CALLS = "calls"


@dataclass(frozen=True)
class SourceOccurrence:
    """源码具体发生位点事实 (LOCK-GRAPH-09)"""
    line: int
    column: int
    argument_count: int | None = None
    snippet_hint: str | None = None


@dataclass(frozen=True)
class RelationCandidate:
    """不可变关系候选 DTO (LOCK-GRAPH-05)"""
    project_key: str
    subject_entity_key: str
    predicate: RelationPredicate
    normalized_raw_target: str
    relation_kind: RelationKind = RelationKind.STATIC
    confidence: Decimal = Decimal("1.00000")
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    object_entity_key: str | None = None
    candidate_discriminator: str = "default"
    occurrences: tuple[SourceOccurrence, ...] = field(default_factory=tuple)
    source_file_rel_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def relation_key(self) -> str:
        """全局唯一确定性逻辑主键 (LOCK-GRAPH-02, LOCK-GRAPH-10)"""
        return (
            f"RELATION:{self.project_key}:"
            f"{self.subject_entity_key}:"
            f"{self.predicate.value}:"
            f"{self.normalized_raw_target}:"
            f"{self.relation_kind.value}:"
            f"{self.candidate_discriminator}"
        )
```

---

## 六、Resolver 确定性上下文契约 (ResolverContext Contract)

为确保 `C-05 Intra-project Symbol Resolver` 跨平台、跨工作区重跑具有 100% 确定性，消除不同 `tsconfig.json` / `vite.config` 探测歧义，确立确定性解析上下文契约：

```python
@dataclass(frozen=True)
class ResolverContext:
    """确定性解析上下文 (C-05)"""
    project_key: str
    project_root: str
    module_root: str
    config_source: str          # 如 "tsconfig.app.json" 或 "vite.config.ts"
    config_hash: str            # 配置文件内容的 sha256 前 16 位
    path_aliases: tuple[tuple[str, str], ...]  # 确定性排序的 (@/ -> src/) 映射表
    package_namespace: str | None = None       # Java 主包名 (如 "org.example.hahamarket")
```

**解析幂等铁律**：对相同的 `(project_key, file_rel_path, ResolverContext)`，符号解析引擎必须产生完全恒等的 `object_entity_key` 与 `resolution_status`，禁止任何依赖运行期环境或非排序遍历的非确定性行为。

---

## 七、十步子阶段切分路线 (C-00 ~ C-09)

```text
MVP2-C (Code Structural Graph)
├── C-00: Schema & Relation Contract Migration (关系模型升级与 TEXT 存储)
├── C-01: RelationCandidate DTO & Identity Subsystem (强类型枚举与 Key 恒等性证明)
├── C-02: Static Module Relations Extractor (imports / exports FILE 级显式依赖)
├── C-03: Static Hierarchy Relations Extractor (extends / implements 类型继承)
├── C-04: Static Relation Persistence & Dedup Pipeline (Tier 1 静态事实持久化与防重)
├── C-05: Intra-project Symbol Resolver (基于 ResolverContext 的项目内符号解析)
├── C-06: Invocation Relations Extractor (calls 显式调用提取与 Occurrences 聚合)
├── C-07: Inferred Relations & Confidence Calibration (Calibration Policy v1 与推断门禁)
├── C-08: Relation Lifecycle, Soft-Delete & Idempotency Pipeline (关系状态机与双 Pass)
└── C-09: Real Projects System Verification Gate (三大真实工程图谱验证与只读终审)
```

### 1. C-00: Schema & Relation Contract Migration
- **任务**：升级 `relations` 数据库表结构，兼顾 PostgreSQL 与 SQLite 双引擎。
- **变更细节**：
  1. `object_entity_id`: 调整为 `nullable=True`（支持未决与外部依赖边）；
  2. 新增字段 `relation_kind`: `String(32)`, 默认 `"STATIC"`, 不可为空；
  3. 新增字段 `resolution_status`: `String(32)`, 默认 `"UNRESOLVED"`, 不可为空；
  4. 新增字段 `raw_target`: `TEXT`, 不可为空（`LOCK-GRAPH-12` 杜绝静默截断）；
  5. 新增字段 `relation_key`: `TEXT UNIQUE NOT NULL`（单一防重主键权威）；
  6. 新增字段 `occurrences`: `JSONB` / SQLite 兼容 JSON，存储调用证据数组；
  7. 移除可能导致冲突的冗余复合唯一索引，完全由 `relation_key` 唯一索引守护。

### 2. C-01: RelationCandidate DTO & Identity Subsystem
- **任务**：实现强类型枚举、`SourceOccurrence`、`RelationCandidate` 与 Identity 证明测试。
- **门禁**：通过单元测试机械证明：在 `resolution_status` 从 `UNRESOLVED` 跃迁为 `RESOLVED`、`object_entity_id` 填入时，`relation_key` 100% 保持不变（`LOCK-GRAPH-10`）。

### 3. C-02: Static Module Relations Extractor (`imports` / `exports`)
- **任务**：提取 TS/JS/Java/Vue 的模块级 `FILE ➔ FILE` 依赖边。
- **规范**：导入符号作为 `metadata["import_specifiers"]` 沉淀，Vue Template 引用作为 `metadata["template_references"]` 沉淀。

### 4. C-03: Static Hierarchy Relations Extractor (`extends` / `implements`)
- **任务**：提取 Java 类/接口与 TypeScript 类/接口的继承体系。
- **规范**：主体与客体均为 `SYMBOL`，置信度恒为 `1.00000`，`relation_kind = STATIC`。

### 5. C-04: Static Relation Persistence & Dedup Pipeline
- **任务**：构建 Tier 1 静态事实批量持久化流水线，形成第一阶段交付物。
- **功能**：基于 `relation_key` 执行幂等 Upsert，Occurrences 自动数组合并，零早熟调用边。

### 6. C-05: Intra-project Symbol Resolver
- **任务**：构建确定性符号解析引擎，消费 `ResolverContext`。
- **功能**：将 `raw_target` 映射为项目内已知实体，分流标记 `RESOLVED` 与 `UNRESOLVED`。

### 7. C-06: Invocation Relations Extractor (`calls`)
- **任务**：提取显式方法、函数与构造函数调用。
- **规范**：遵循 `LOCK-GRAPH-09`，同一方法内的多次调用聚合至单条边的 `occurrences` 列表。

### 8. C-07: Inferred Relations & Confidence Calibration
- **任务**：实现多态调用推断与启发式解析，标记 `INFERRED` 与 `confidence < 1.00000`。
- **策略**：执行 **`Calibration Policy v1`**，并通过专设的校准门禁（Calibration Gate）进行精度与召回评估。

### 9. C-08: Relation Lifecycle, Soft-Delete & Idempotency Pipeline
- **任务**：建立关系软删除（`status = 'DELETED'`）与复活（`status = 'ACTIVE'`）状态机。
- **断言**：Pass 2 `created=0, deleted=0, updated=N`，关系集合 100% 恒等。

### 10. C-09: Real Projects System Verification Gate
- **任务**：三大真实工程（4,618 文件）系统级验证门禁。
- **指标**：全真代码图谱构建、第三方 BOM 清单提炼、只读终极审计与性能基线建立。

---

## 八、终审准入对照表 (Pre-Implementation Verification Matrix)

| 审阅要求事项 | 对应架构锁 / 规约 | 落实状态 |
|---|---|---|
| **1. 关系是 Edge 还是 Occurrence** | `LOCK-GRAPH-09`：Relation = logical edge, Occurrence = evidence 数组 | ✅ 明确冻结 |
| **2. UNRESOLVED ➔ RESOLVED 身份稳定性** | `LOCK-GRAPH-10`：Relation Key 仅绑定源码不可变 Anchor，解析状态变化 Key 零漂移 | ✅ 明确冻结 |
| **3. imports / exports 的实体粒度** | `LOCK-GRAPH-11`：严格规范为 `FILE ➔ FILE`，符号绑定放入 specifiers metadata | ✅ 明确冻结 |
| **4. relation_kind 纳入唯一性语义** | `LOCK-GRAPH-02` / `03`：`relation_key` 格式显式包含 `relation_kind` 与候选判别器 | ✅ 明确冻结 |
| **5. raw_target 不得静默截断** | `LOCK-GRAPH-12`：数据库定义为 `TEXT`，消除 512 字符硬截断风险 | ✅ 明确冻结 |
| **6. Vue Template 引用边界控制** | 第四节特别约定：严禁偷跑 `uses` 谓词，统一收敛至 `metadata["template_references"]` | ✅ 明确冻结 |
| **7. 强类型 DTO 约束** | 第五节：采用 `Enum` 强类型定义 `RelationKind`, `ResolutionStatus`, `RelationPredicate` | ✅ 明确冻结 |
| **8. Resolver 配置确定性** | 第六节：定义 `ResolverContext`，绑定 `config_hash` 与排序别名表 | ✅ 明确冻结 |
| **9. 0.85 置信度定位** | 第七节 C-07：定性为 `Calibration Policy v1`，增加校准验收门禁 | ✅ 明确冻结 |
| **10. 数据库唯一性权威单一化** | `LOCK-GRAPH-12`：完全由 `relation_key TEXT UNIQUE` 统一守护，移除冲突复合索引 | ✅ 明确冻结 |

---

## 九、实施准入建议

本规划已将全部 10 项终审边界要求彻底写入架构锁与形式化规范中。  
至此，**MVP2-C 主规划所有基础语义缺口已全部闭环**，可以正式批准：
1. **MVP2-C 主规划正式标记为 `PLAN_FROZEN`**；
2. **解锁并进入 `C-00 Schema & Relation Contract Migration` 实施准备！**
