# LKIO MVP2-B B-07 实施规划：数据库持久化与幂等合并流水线 (Symbol Persistence & Idempotency Pipeline)

> **阶段代号**：`MVP2-B-07`  
> **上游阶段**：`MVP2-B-06 (COMPLETED / FROZEN)`  
> **下游阶段**：`MVP2-B-08 (Real Projects Smoke & Full Verification)`  
> **当前状态**：**IN_PROGRESS**  
> **核心原则**：消费 B-06 产出、确定性 Key 幂等合并、文件级软删除同步、事务隔离容错、严格只读三大外部工程、严禁早熟图谱构建

---

## 一、阶段定位与架构边界

### 1. 架构定位
在 LKIO MVP2-B 的符号生命周期中：
```text
B-03/B-04/B-05 (AST Extractors)
      │
      │ 纯内存 AST 提取事实
      ▼
B-06 (Orchestrator)
      │
      │ 统一路由 / 沙箱隔离 / 失败分类 / Key 计算 / 字典序归一
      ▼
 FileExtractionResult / BatchExtractionSummary (Frozen DTOs)
      │
      ▼
B-07 (Symbol Persistence & Idempotency Pipeline)  <-- 本阶段
 ┌────────────────────────────────────────────────────────┐
 │ 1. 纯消费 B-06 DTO，严禁二次 AST 解析                 │
 │ 2. 基于 entity_key (TEXT UNIQUE) 的确定性幂等 Upsert   │
 │ 3. 单文件作用域软删除同步 (status = 'DELETED')         │
 │ 4. 复活符号自动激活 (status = 'ACTIVE')                │
 │ 5. FILE ── defines ──► SYMBOL 事实关系建立             │
 │ 6. 单文件独立事务沙箱与失败隔离                        │
 │ 7. 统计计数完整性硬约束 (Counter Integrity)           │
 └────────────────────────────────────────────────────────┘
      │
      ▼
Knowledge Core (PostgreSQL / SQLite Compatible: entities & relations)
```

### 2. 六大持久化架构锁 (LOCK-PERSIST-01 ~ LOCK-PERSIST-06)

| 锁编号 | 架构锁名称 | 严格定义与不可突破边界 |
|---|---|---|
| **LOCK-PERSIST-01** | **纯 DTO 消费隔离** | B-07 仅消费 B-06 输出的 `FileExtractionResult` / `SymbolCandidate`，绝对禁止调用 Tree-sitter Parser 或重新解释 AST 语义。 |
| **LOCK-PERSIST-02** | **基于 Key 的逻辑幂等 Upsert** | 符号入库必须以 `entity_key`（B-00/B-01 迁移为 TEXT UNIQUE）为逻辑唯一凭据。重复对同一文件执行入库，新增实体数必须恒等于 0，更新实体数恒等于有效符号数，主键 ID 保持不变。 |
| **LOCK-PERSIST-03** | **文件作用域软删除同步** | 当文件在增量同步中发现某些符号消失时，仅对该文件历史上定义的符号标记 `status = 'DELETED'`，绝对禁止物理调用 `db.delete()` 删除实体记录。 |
| **LOCK-PERSIST-04** | **复活符号无损激活** | 曾被标记为 `DELETED` 的符号若在后续扫描中重新出现，状态必须原子恢复为 `status = 'ACTIVE'`，并更新最新的行号、签名与元数据。 |
| **LOCK-PERSIST-05** | **严格只建 defines 事实边** | B-07 仅允许建立 `FILE ── defines ──► SYMBOL` 事实关系（置信度恒为 `Decimal("1.00000")`）。严禁引入 `calls`, `imports`, `extends`, `implements` 等跨符号结构关系（留待 MVP2-C）。 |
| **LOCK-PERSIST-06** | **单文件事务隔离与容错** | 批量入库时以单个文件为事务隔离单元（Savepoint / Per-file Transaction）。单个文件入库发生异常必须独立回滚，不得污染数据库 Session，不得中断其他有效文件的入库。 |

---

## 二、核心持久化协议与算法设计

### 1. 实体字段映射契约
| Entity 字段 | 映射来源 / 计算方式 | 约束说明 |
|---|---|---|
| `id` | `uuid.uuid4()` (新建时) / 保持既有不变 (更新时) | 主键不可变 |
| `project_id` | `project.id` (UUID) | 外键关联 |
| `entity_type` | `cand.symbol_type` (如 `FUNCTION`, `COMPONENT`, `METHOD`) | 字符串 |
| `entity_key` | `cand.compute_key()` (或 B-06 产出的 `sym_key`) | TEXT UNIQUE 唯一约束 |
| `name` | `cand.name` (截断保护 <= 255) | 短名称 |
| `canonical_name` | `f"{project_key}_{cand.qualified_name}"` (截断保护 <= 255) | 全局限定名 |
| `path` | `cand.file_rel_path` | 正斜杠规范化路径 |
| `status` | `"ACTIVE"` / `"DELETED"` | 统一全大写状态码 |
| `metadata_` | 包含所有 20 项字段的深度 JSONB 载荷 | 无损保留 provenance & AST facts |

### 2. 软删除与复活状态机
```text
           [首次发现]
              │
              ▼
        ┌───────────┐
        │  ACTIVE   │ ◄──────────────────┐
        └─────┬─────┘                    │
              │                          │
        [文件扫描消失]               [文件扫描重新出现]
              │ (status='DELETED')       │ (status='ACTIVE')
              ▼                          │
        ┌───────────┐                    │
        │  DELETED  │ ───────────────────┘
        └───────────┘
```

### 3. defines 关系维护规则
- **Subject**: `file_entity.id`
- **Predicate**: `"defines"`
- **Object**: `sym_entity.id`
- **Confidence**: `Decimal("1.00000")`
- **Metadata**: `{"extraction_method": "static_ast", "symbol_type": cand.symbol_type, "base_symbol_type": cand.base_symbol_type, "language": cand.language}`
- **幂等保护**: 依赖 `(subject_entity_id, predicate, object_entity_id)` 唯一索引，存在时不重复添加。

---

## 三、双引擎支持 (PostgreSQL + SQLite)

为确保单元测试零环境依赖（无需启动 Docker/Postgres 即可毫秒级自测），在 `core/db/base.py` 中注入 SQLite 编译适配钩子：
```python
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"
```
生产环境（PostgreSQL 18 + pgvector）保持完全不受影响，编译结果仍为标准的 `JSONB` 与 `UUID`。

---

## 四、Acceptance Gates (Gate A ~ P)

- **Gate A (Schema & Dialect Compatibility)**: SQLAlchemy SQLite 编译适配器通过，内存 SQLite 支持全套表结构。
- **Gate B (First-time Insert)**: 首次持久化正确写入 `entities`，`status="ACTIVE"`，并建立 `defines` 关系。
- **Gate C (Idempotent Re-Run)**: 相同文件二次执行，`created=0, updated=N, deleted=0`，实体主键与总数不变。
- **Gate D (Vanished Symbol Soft-Delete)**: 符号在源码中删除后，实体状态变更为 `status="DELETED"`，物理记录不删除。
- **Gate E (Resurrected Symbol Reactivation)**: 删除的符号重新出现时，状态自愈恢复为 `status="ACTIVE"`。
- **Gate F (Defines Relation Integrity)**: 关系主体为 `FILE`，谓词为 `defines`，客体为 `SYMBOL`，置信度恒为 1.00000。
- **Gate G (Multi-Language Coverage)**: TS, JS, Java, Vue 4 种语言金标准样本全量持久化成功。
- **Gate H (Transaction Isolation Rollback)**: 单文件入库异常触发局部回滚，不影响其他文件入库与 Session 状态。
- **Gate I (Metadata Completeness)**: 20 项元数据字段完整持久化进 `metadata_`，无截断无丢失。
- **Gate J (Counter Integrity)**: `BatchPersistenceSummary` 计数恒等式严格成立：`extracted == created + updated`。
- **Gate K (Zero Premature Graph Edges)**: 静态扫描持久化代码，严禁构建 `calls`, `imports`, `extends`, `implements` 边。
- **Gate L (Zero Direct Extractor/Parser Calls)**: 静态扫描持久化代码，严禁导入 Tree-sitter Parser 或直接调用语言 Extractor。
- **Gate M (Defensive String Truncation)**: 极长符号名或限定名安全截断，防止超出 `String(255)` 约束。
- **Gate N (Strict Read-Only Guarantee)**: 执行持久化前后，三大外部仓库（`HELLO_FE`, `HELLO_BE`, `L2C_FE`）`git status --porcelain` 严格不变。
- **Gate O (Performance Benchmark)**: 内存持久化 100 个文件，平均单文件持久化耗时 < 5ms。
- **Gate P (Key Collision Resolution)**: 同一文件中出现重复 Key 时安全处理，不产生冲突异常。

---

## 五、实施步骤规划

1. **Step 1: 基础设施增强**
   - 在 `core/db/base.py` 中注册 SQLite 的 `JSONB` 和 `UUID` 编译钩子。
2. **Step 2: 核心持久化管道升级 (`ingestion/symbols.py`)**
   - 提取并完善 `SymbolPersistenceService`。
   - 实现 `persist_file_symbols(db, project_id, project_key, file_entity, extraction_result, source_id)`。
   - 实现 `persist_batch_symbols(db, project_id, project_key, file_results_map)`。
   - 兼容保留并增强 `sync_file_symbols` 与 `sync_project_symbols`。
3. **Step 3: 专属单元测试套件 (`tests/unit/b07/test_persistence_b07.py`)**
   - 覆盖 Gate A ~ P 全部 16 项验证。
4. **Step 4: 回归与只读验证**
   - 执行 `pytest tests/unit/b07 -q`。
   - 执行 `pytest tests/unit/b06 -q`。
   - 验证三大源仓库工作区只读无损。
5. **Step 5: 归档与状态推进**
   - 编写 `docs/mvp2/mvp2_step7_b07_persistence_report.md`。
   - 更新 `docs/mvp2/MVP2_STATUS.md`。
