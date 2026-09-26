# LKIO MVP2-C 代码结构图谱主架构实施规划 (Code Structural Graph Master Plan)

> **阶段代号**：`MVP2-C` (Code Structural Graph)  
> **上游依赖**：`MVP2-B (100% COMPLETED / FROZEN)`（代码符号、身份与物理持久化基石）  
> **当前状态**：**`READY_TO_PLAN ➔ SUBMITTED_FOR_REVIEW`**  
> **规划目标**：在已冻结的 MVP2-B 符号与文件实体基础之上，构建工程级单项目代码结构图谱。严格遵循“静态结构事实”与“符号解析/推断”两层分离架构，建立确定性关系身份、未决目标沉淀机制、强类型 DTO 流水线与高吞吐幂等持久化。

---

## 一、架构全景与流水线模型 (End-to-End Graph Architecture)

MVP2-C 坚守**单向消费原则**：MVP2-B 产出的 `Entity (FILE / SYMBOL)` 与 `Relation (defines)` 作为底层冻结事实输入，MVP2-C 不再对源码重新进行符号解析，而是专注抽取和推导符号之间、文件与符号之间的结构关系。

```text
                            MVP2-B 冻结底座 (Frozen Foundation)
                 ┌────────────────────────────────────────────────────────┐
                 │  Persisted Entities (FILE, CLASS, METHOD, etc.)        │
                 │  + Provenance Edges (FILE -- defines --> SYMBOL)       │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                 ══════════════════════════════════════════════════════════
                                  MVP2-C 两层抽取与解析架构
                 ══════════════════════════════════════════════════════════
                   Tier 1: 静态显式结构事实层 (C-01 ~ C-04)
                   ┌────────────────────────────────────────────────────┐
                   │  imports, exports, extends, implements             │
                   │  (AST 显式语法声明，100% 事实，relation_kind=STATIC) │
                   └─────────────────────────┬──────────────────────────┘
                                             │
                                             ▼
                   Tier 2: 作用域解析与调用推断层 (C-05 ~ C-08)
                   ┌────────────────────────────────────────────────────┐
                   │  Intra-project Symbol Resolver (路径/别名/限定名)     │
                   │  calls, constructor invocation, overrides          │
                   │  (分流: RESOLVED ➔ 内部实体, UNRESOLVED ➔ 外部/未决) │
                   │  (分层: STATIC=1.00000 vs INFERRED < 1.00000)       │
                   └─────────────────────────┬──────────────────────────┘
                                             │
                                             ▼
                                     RelationCandidate DTO
                                             │
                                             ▼
                                Relation Identity & Dedup
                                             │
                                             ▼
                          Relation Persistence & Idempotency Pipeline
                                             │
                                             ▼
                 ══════════════════════════════════════════════════════════
                   Tier 3: 系统级验证与性能基准 (C-09)
                 ══════════════════════════════════════════════════════════
                   三大真实项目 (4,618 文件) 结构图谱验证 + 双 Pass 恒等性证明
```

---

## 二、八大架构锁设计 (LOCK-GRAPH-01 ~ LOCK-GRAPH-08)

为了杜绝关系提取过程中的语义倒灌、膨胀失控与黑盒丢弃，MVP2-C 确立 8 大不可突破的架构红线：

| 锁编号 | 架构锁名称 | 严格定义与不可突破边界 | 破坏后果与防御机制 |
|---|---|---|---|
| **`LOCK-GRAPH-01`** | **Frozen Symbol Consumer** | MVP2-C 仅作为下游消费者，严格消费 MVP2-B 已持久化的 `Entity` 与 `defines` 关系事实。**严禁为了图谱构建反向修改 B-03 ~ B-07 的符号抽取器、Key 算法或持久化契约**。 | 防御符号身份语义污染，保证 MVP2-B 基石 100% 不变性。 |
| **`LOCK-GRAPH-02`** | **Relation Identity 确定性** | 关系身份独立于实体身份。关系的逻辑唯一性由确定性 `relation_key` 保证：`RELATION:{project_key}:{subject_key}:{predicate}:{target_ident}`。物理主键由 `(subject_entity_id, predicate, COALESCE(object_entity_id, sentinel_uuid), raw_target)` 联合防重。 | 杜绝图谱边的重复插入与重跑主键漂移。 |
| **`LOCK-GRAPH-03`** | **Static 与 Inferred 严格两级分层** | 关系必须具备强类型枚举 `relation_kind: "STATIC" \| "INFERRED"`：<br>1. **`STATIC`**：AST 语法明确声明（如 explicit import/extends），置信度严格恒等于 `Decimal("1.00000")`；<br>2. **`INFERRED`**：多态调度、启发式解析，置信度严格 `< Decimal("1.00000")`。严禁混淆“语法事实”与“推断估算”。 | 保证代码结构基准数据具有 100% 确定性，推断数据可独立过滤审计。 |
| **`LOCK-GRAPH-04`** | **静态关系与调用推断严格解耦** | 将结构事实（`imports`, `exports`, `extends`, `implements`）与调用图（`calls`）物理隔离在不同阶段实施。**严禁在未建立完备模块与继承图谱前，一上来就构建全量调用图**。 | 避免在缺乏类型上下文时陷入多态与重载的解析泥潭。 |
| **`LOCK-GRAPH-05`** | **RelationCandidate DTO 强类型管道** | AST 关系提取器严禁直接调用 SQL 写入数据库。必须全部产出不可变的 `RelationCandidate` DTO，经由统一编排、解析器匹配与持久化管道批量入库。 | 保持测试可隔离性、确定性批处理与错误局部隔离。 |
| **`LOCK-GRAPH-06`** | **未决目标显式沉淀契约 (Unresolved Policy)** | 面对第三方库（npm/Maven）或未索引源码中的目标实体，**严禁静默丢弃 (Drop)**。必须作为可观测事实沉淀：`resolution_status = "UNRESOLVED"`，且保留 `raw_target` 原始标识符。 | 外部边界（SDK/第三方库）是架构全景的关键组成部分，丢弃会导致图谱断裂。 |
| **`LOCK-GRAPH-07`** | **分层两阶段演进 (Two-tier Stages)** | MVP2-C 划分为两大内部阶梯：Tier 1（C-01 ~ C-04 静态显式结构关系）与 Tier 2（C-05 ~ C-08 作用域解析与调用推断），逐级验收冻结。 | 杜绝大一统交付导致的验收黑盒与回归爆炸。 |
| **`LOCK-GRAPH-08`** | **三大外部工程绝对物理只读与双 Pass 幂等** | 继承严格只读铁律：验证过程严禁修改 `HELLO_FE`, `HELLO_BE`, `L2C_FE` 任何文件（`git status --porcelain` 增量严格为 0）。图谱写入必须满足双 Pass 恒等：Pass 2 `created=0, deleted=0, updated=N`，关系三元组 100% 恒等。 | 保护外部宿主环境，确保企业级重复执行的生产确定性。 |

---

## 三、十步子阶段演化蓝图 (C-00 ~ C-09)

为践行步步为营的工程纪律，MVP2-C 细化为 10 个子阶段：

```text
MVP2-C (Code Structural Graph)
├── C-00: Schema & Relation Contract Migration (关系表模型升级与未决目标支持)
├── C-01: RelationCandidate DTO & Identity Subsystem (DTO 契约与确定性 Relation Key)
├── C-02: Static Module Relations Extractor (imports / exports 显式依赖提取)
├── C-03: Static Hierarchy Relations Extractor (extends / implements 继承关系提取)
├── C-04: Static Relation Persistence & Dedup Pipeline (静态事实批量入库与去重流水线)
├── C-05: Intra-project Symbol Resolver (项目内模块路径/别名/FQN 解析引擎)
├── C-06: Invocation Relations Extractor (calls 显式调用提取)
├── C-07: Inferred Relations & Confidence Calibration (多态与启发式调用推断分层)
├── C-08: Relation Lifecycle, Soft-Delete & Idempotency Pipeline (关系软删除、复活与双 Pass)
└── C-09: Real Projects System Verification Gate (三大真实工程图谱验证与只读终审)
```

### 1. C-00: Schema & Relation Contract Migration
- **目标**：评估并升级现有的 `relations` 数据库表结构，以原生支持 MVP2-C 所需的显式契约。
- **核心变更**：
  1. `object_entity_id`: 支持 `nullable=True`（当目标未决或指向外部库时为 `NULL`）；
  2. 新增字段 `relation_kind`: `VARCHAR(32)`，取值 `STATIC` 或 `INFERRED`，默认 `STATIC`；
  3. 新增字段 `resolution_status`: `VARCHAR(32)`，取值 `RESOLVED`（已解析到内部 Entity）或 `UNRESOLVED`（未决/外部实体）；
  4. 新增字段 `raw_target`: `VARCHAR(512)`，记录源码中的原始目标字符串（如 `"lodash/cloneDeep"` 或 `"com.example.service.OrderService"`）；
  5. 新增字段 `relation_key`: `TEXT UNIQUE`，关系的全局确定性逻辑主键；
  6. 数据库迁移脚本（Alembic）与 SQLite 双引擎兼容层无损适配。

### 2. C-01: RelationCandidate DTO & Identity Subsystem
- **目标**：建立全系统统一的不可变关系中间表达 `RelationCandidate` 与确定性 Key 算法。
- **DTO 规范**：
  ```python
  @dataclass(frozen=True)
  class RelationCandidate:
      subject_entity_key: str          # 来源实体 Key (FILE 或 SYMBOL)
      predicate: str                   # imports, exports, extends, implements, calls
      object_entity_key: str | None    # 目标实体 Key (已解析时提供，未决时为 None)
      raw_target: str                  # 源码中的原始引用字面量
      relation_kind: str               # "STATIC" | "INFERRED"
      confidence: Decimal              # STATIC=1.00000, INFERRED < 1.00000
      resolution_status: str           # "RESOLVED" | "UNRESOLVED"
      evidence: dict[str, Any]         # 语法行号、AST 节点类型、修饰符
      source_file_rel_path: str        # 关系发生的相对文件路径
      metadata: dict[str, Any]         # 扩展元数据 (如 is_type_only, is_default_export)
  ```
- **Relation Key 规范**：
  - 格式：`RELATION:{project_key}:{subject_key}:{predicate}:{target_ident}:{kind}`
  - 其中 `target_ident` 在已解析时为 `object_entity_key`，在未决时为 `raw_target` 的规范化哈希。

### 3. C-02: Static Module Relations Extractor (`imports` / `exports`)
- **目标**：不碰 AST 符号定义，专注从语法树提取文件与模块级依赖关系。
- **语言覆盖**：
  - **TypeScript / JavaScript**:
    - `import { A, B as C } from './utils'` ➔ `FILE -- imports --> A, B (raw_target: "./utils")`
    - `import * as Path from 'path'` ➔ 命名空间导入
    - `export { Foo } from './bar'` ➔ 重导出与直接导出
    - `import type { User } from './types'` ➔ 标记 `metadata.is_type_only = True`
  - **Java**:
    - `import com.example.model.Order;` ➔ 单类型导入
    - `import com.example.util.*;` ➔ 通配符导入（按语法事实记录）
    - `import static com.example.Constants.TIMEOUT;` ➔ 静态方法/变量导入
  - **Vue SFC**:
    - `<script>` 与 `<script setup>` 内的 ES Module 导入导出
    - `<template>` 中对已导入组件的显式引用（Vue 结构边）

### 4. C-03: Static Hierarchy Relations Extractor (`extends` / `implements`)
- **目标**：提取类、接口的类型继承与实现层级。
- **语言覆盖**：
  - **Java**:
    - `class OrderServiceImpl extends BaseService implements OrderService, Auditable`
    - 抽取：`CLASS -- extends --> BaseService`, `CLASS -- implements --> OrderService, Auditable`
  - **TypeScript**:
    - `interface AdminUser extends User, Permissions`
    - `class CustomComponent extends BaseComponent<Props>`
- **契约保证**：全部标记为 `relation_kind = "STATIC", confidence = Decimal("1.00000")`。

### 5. C-04: Static Relation Persistence & Dedup Pipeline
- **目标**：实现 Tier 1 静态关系的批量持久化流水线，形成第一阶段交付闭环。
- **功能**：
  - 校验 `subject_entity_key` 必须已在 MVP2-B 数据库中存在；
  - 基于 `relation_key` 的幂等 Upsert；
  - 静态事实去重与冲突拒绝。

### 6. C-05: Intra-project Symbol Resolver (项目内符号解析器)
- **目标**：解决“`raw_target` 到底对应项目内哪一个具体的 `Entity`”。
- **解析机制**：
  1. **TS/JS 路径决议**：
     - 相对路径解析：`./service` ➔ 解析为同一目录下的 `service.ts` 或 `service/index.ts`；
     - 模块别名解析：根据 `tsconfig.json` / `vite.config` 中的路径别名（如 `@/` ➔ `src/`）进行物理映射；
  2. **Java FQN 决议**：
     - 包名 + 类名匹配：`com.example.OrderService` ➔ 匹配 `canonical_name` 或限定名；
     - 同包隐式可见性决议：同包下的类默认互可见；
  3. **决议状态沉淀**：
     - 命中项目内已知实体 ➔ 绑定 `object_entity_id`, `resolution_status = "RESOLVED"`；
     - 属于 JDK/Spring/npm 等外部库或无法定位 ➔ `object_entity_id = NULL`, `resolution_status = "UNRESOLVED"`。

### 7. C-06: Invocation Relations Extractor (`calls`)
- **目标**：从方法体与函数体中提取显式方法/函数调用。
- **提取范围**：
  - 显式直接调用：`this.calculateTotal()`, `Math.max()`, `orderService.submit(order)`;
  - 构造函数实例化：`new OrderRecord(...)`;
  - 记录调用的语法证据：`evidence: {"call_site_line": 42, "argument_count": 2}`。

### 8. C-07: Inferred Relations & Confidence Calibration
- **目标**：对无法在 AST 中 100% 静态确定的调用进行多态与推断解析，严格隔离。
- **推断规则**：
  - **接口多态调用**：针对 `OrderService.submit()`（接口方法），若项目内仅有单一实现类 `OrderServiceImpl`，建立推断调用：`confidence = Decimal("0.85000")`，`relation_kind = "INFERRED"`；若有多重实现，则建立多条候选推断边并均摊置信度；
  - **动态属性/方法调用**：TS/JS 中 `obj[methodName]()`，标记为 `INFERRED` 并记录推断原因；
  - **严格红线**：推断置信度严禁标为 `1.00000`，且推断算法不改变已有 `STATIC` 边。

### 9. C-08: Relation Lifecycle, Soft-Delete & Idempotency Pipeline
- **目标**：构建完整关系的生命周期状态机与双 Pass 幂等保证。
- **状态机行为**：
  - 文件修改导致调用或引用消失 ➔ 关系标记为 `status = "DELETED"`（软删除）；
  - 文件恢复调用 ➔ 关系自愈复活为 `status = "ACTIVE"`；
  - Pass 2 重跑断言：`created=0, deleted=0, updated=N`，关系集合 100% 恒等。

### 10. C-09: Real Projects System Verification Gate
- **目标**：在三大真实工程（4,618 文件）上执行 MVP2-C 系统级验收门禁。
- **验证内容**：
  - 采样与全量模块图谱构建；
  - 真实代码外部依赖（Unresolved）审计与统计分布；
  - 零外部源码修改（`git status --porcelain` 增量严格为 0）；
  - 性能基准建立（单文件建图延迟与吞吐量）。

---

## 四、未决目标沉淀机制 (The Unresolved Fact Policy)

传统的代码分析工具最严重的缺陷在于：**遇到未识别或外部符号时直接丢弃，导致调用链路在系统边界处突然断裂**。

MVP2-C 将“未决目标”提升为一等公民事实（First-class Observable Fact）：

```text
源码片段:
import { ElMessage } from 'element-plus';
import { useUserStore } from '@/store/user';

                             AST Extractor
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Raw Imports Extracted        │
                   │ 1. target: 'element-plus'    │
                   │ 2. target: '@/store/user'    │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                        Symbol Resolver Engine
                                  │
          ┌───────────────────────┴───────────────────────┐
          │                                               │
          ▼                                               ▼
   解析为内部 Entity                               外部第三方库/未决
   (@/store/user ➔ UserStore)                      (element-plus)
          │                                               │
          ▼                                               ▼
   Relation: IMPORTS                              Relation: IMPORTS
   subject: FileEntity                            subject: FileEntity
   object: UserStore (UUID)                       object: NULL (外部未引)
   resolution_status: RESOLVED                    resolution_status: UNRESOLVED
   raw_target: '@/store/user'                     raw_target: 'element-plus'
   confidence: 1.00000                            confidence: 1.00000
```

### 未决沉淀的核心价值：
1. **明确系统物理边界**：通过聚合 `resolution_status = "UNRESOLVED"` 的关系，可全自动提炼出三大工程的**第三方依赖全景图（Third-party Bill of Materials）**；
2. **渐进式解析能力**：当后续加载公共包或跨工程模块（MVP2-D）时，可原地将 `UNRESOLVED` 边升级为 `RESOLVED`，无需全量重扫。

---

## 五、实施节奏与交付矩阵 (Milestone Roadmap)

| 阶段代号 | 核心任务 | 验收成果与交付物 | 预计门禁数 |
|---|---|---|---|
| **`C-00`** | 关系表 Schema 升级与 Alembic 迁移 | `core/models/relation.py` 升级，支持 NULL 目标与 `relation_kind` | Gate A ~ C (3 Gates) |
| **`C-01`** | `RelationCandidate` DTO 与确定性 Key | 强类型 DTO、Evidence 结构与 `relation_key` 生成器 | Gate D ~ F (3 Gates) |
| **`C-02`** | `imports` / `exports` 静态模块关系提取 | TS/JS/Java/Vue 模块级与重定向导入导出提取 | Gate G ~ I (3 Gates) |
| **`C-03`** | `extends` / `implements` 静态继承体系提取 | 类/接口继承与实现层级提取 | Gate J ~ L (3 Gates) |
| **`C-04`** | Tier 1 静态关系持久化管道 | 静态事实入库、去重防重与双 Pass 恒等 | Gate M ~ O (3 Gates) |
| **`C-05`** | 项目内符号解析器 (Symbol Resolver) | 路径别名、同包解析、FQN 限定名解析引擎 | Gate P ~ R (3 Gates) |
| **`C-06`** | `calls` 方法与函数调用提取器 | 显式调用提取与调用点证据记录 | Gate S ~ U (3 Gates) |
| **`C-07`** | 推断关系与置信度校准体系 | 多态调用推断、动态调用分层（`< 1.00000`） | Gate V ~ X (3 Gates) |
| **`C-08`** | 关系生命周期与软删除状态机 | 关系删除、复活自愈与三段式计数闭环 | Gate Y ~ AA (3 Gates) |
| **`C-09`** | 三大真实工程图谱系统级验证 | 4,618 文件全真验证、只读审计与性能基线 | Gate AB ~ AF (5 Gates) |

---

## 六、MVP2-C 终审验收前置承诺

在开启生产代码实现前，我们郑重确立以下前置承诺：
1. **MVP2-B 零变动保护**：MVP2-C 实施全程绝不修改已冻结的 `tests/unit/b00_b02` ~ `b07` 及 `tests/integration/b08` 任何既有测试。
2. **关系唯一性硬约束**：数据库 `relations` 表在新增支持 `object_entity_id = NULL` 时，唯一约束升级保证物理零重复。
3. **真实工程只读绝对保证**：全过程确保 `git -C <repo> status --porcelain` 增量严格为 0。

本主规划已整理完毕，请审阅。一旦您确认通过，我们将正式开启 **`C-00 Schema / Relation Contract Migration`** 的实施！
