# LKIO MVP2-B B-08 实施规划：三大真实项目端到端全量扫描、入库烟测与只读终极审计 (Real Projects Verification Pipeline)

> **阶段代号**：`MVP2-B-08`  
> **上游阶段**：`MVP2-B-07 (COMPLETED / FROZEN)`  
> **当前状态**：**IN_PROGRESS**  
> **核心原则**：真实工程全量检验、双 Pass 确定性幂等恒等证明、三段式计数审计、三大工程物理只读绝对红线、严禁早熟图谱构建

---

## 一、阶段定位与系统级检验目标 (System-level Verification Gate)

B-08 不是简单的外围冒烟测试，而是 **LKIO MVP2-B（Code Intelligence — Symbol Extraction）的系统级终审检验门禁 (System-level Verification Gate)**。

各子阶段的工程递进关系如下：
```text
B-03 ~ B-05: 证明“能正确理解单语言客观语法结构” (TS/JS, Java, Vue)
     ↓
    B-06   : 证明“能正确组织多语言路由、沙箱隔离与 Key 归一化” (Orchestrator)
     ↓
    B-07   : 证明“能正确、幂等、安全地实现数据库持久化与软删除” (Persistence)
     ↓
    B-08   : 证明“面对真实大型异构代码工程，整条全链路仍然 100% 成立且具备工程确定性” (System Verification)
```

### 真实工程全量语料规模
经实际文件扫描核验，三大真实工程的代码体量如下：
- **`HELLO_FE`** (`C:\WorkSpace\hello`)：**1,071** 个受支持源码文件（Vue 585, JS 417, TSX 40, TS 14, Java 15）
- **`HELLO_BE`** (`C:\WorkSpace\hello-backend`)：**1,957** 个受支持源码文件（全部为 Java Spring Boot 核心业务代码）
- **`L2C_FE`** (`C:\WorkSpace\L2C project`)：**1,575** 个受支持源码文件（TS 826, Vue 748, JS 1）
- **三大工程总计受支持源文件**：**4,603** 个文件。

---

## 二、六大系统级验证架构锁 (LOCK-VERIFY-01 ~ LOCK-VERIFY-06)

| 锁编号 | 架构锁名称 | 严格定义与不可突破边界 |
|---|---|---|
| **LOCK-VERIFY-01** | **全链路端到端闭环** | B-08 必须完整串联：真实文件发现 ➔ 多语言路由 ➔ AST 符号抽取 ➔ Key 计算 ➔ 批量持久化 ➔ defines 关系建立 ➔ 软删除/复活，严禁使用虚假 Mock 旁路替代真实链路。 |
| **LOCK-VERIFY-02** | **三大源工程绝对只读红线** | 扫描与验证过程严禁写回、修改、添加任何文件到 `HELLO_FE`, `HELLO_BE`, `L2C_FE`。验证前后 `git status --porcelain` 差异严格为 0。针对增删状态机测试，必须在临时工作区（`Temporary Verification Workspace`）执行真实源码快照副本演练，严禁碰触原始仓库。 |
| **LOCK-VERIFY-03** | **真实工程代表性双 Pass 幂等恒等证明** | 对真实工程样本进行完整 Pass 1 扫描入库后，执行完全相同的 Pass 2 扫描：<br>1. 计数恒等：`created_pass2 == 0`，`deleted_pass2 == 0`，`updated_pass2 == N`（**`N` 严格定义为 Pass 1 ACTIVE 实体总数**）；<br>2. 三集合严格恒等：<br>   - `entity_id_set(pass1) == entity_id_set(pass2)`<br>   - `entity_key_set(pass1) == entity_key_set(pass2)`<br>   - `defines_edge_set(pass1) == defines_edge_set(pass2)`。 |
| **LOCK-VERIFY-04** | **多项目物理隔离防串扰** | 三大工程混合扫描入库时，必须证明以 `(project_key, file_rel_path)` 为作用域的完全物理隔离，跨工程同名路径实体绝不产生 Key 碰撞、关系覆盖或软删除误伤。 |
| **LOCK-VERIFY-05** | **三段式计数审计与失败可追溯** | 必须严格满足三段式计数公式：<br>1. 发现层：`discovered == successful + failed + unsupported`<br>2. 抽取层：`successful_extracted == successful_persisted + failed_persisted`<br>3. 持久层：`active_symbols == created + updated`。<br>任何失败文件必须具备精确的 6 元追溯上下文：`(project, file_rel_path, language, failure_stage, failure_reason, error_detail)`。 |
| **LOCK-VERIFY-06** | **资源稳定性契约 (Resource Stability Contract)** | 真实工程批量扫描建立吞吐量基准（files/sec, symbols/sec, P50, P95）。在 Pass 1/2/3 连续执行后，文件描述符 (FD)、数据库连接 (DB Connections)、临时文件与内存 (RSS) 不发生单调持续增长，执行完毕后句柄与连接安全释放回基线。 |

---

## 三、18 项 Acceptance Gates 四层证据模型

为了保证证据链条清晰，18 项门禁按四层证据模型组织：

### Layer 1 — 文件发现与路由层 (Discovery & Routing)
- **Gate A (真实文件安全发现)**：`DirectoryScanner` 准确排除 `node_modules`, `target`, `dist`, `.git` 等，准确发现三大工程共 4,618 个受支持源文件（包含 15 个合规 `.mjs` 模块）。
- **Gate B (真实多语言路由准确率)**：4,618 个源文件按后缀与语言路由 100% 正确路由至对应语言处理器（Java: 1,972, Vue: 1,333, TS: 840, JS-family: 433, TSX: 40）。

### Layer 2 — 真实代码抽取与身份层 (Extraction & Identity)
- **Gate C (HELLO_FE 真实 Vue/TS 抽取)**：真实抽取 HELLO_FE 中的 Vue SFC、`<script setup>`、路由与组件符号。
- **Gate D (HELLO_BE 真实 Spring 抽取)**：真实抽取 HELLO_BE 中的 Controller, Service, `@RestController`, `@GetMapping`, 重载方法与字段。
- **Gate E (L2C_FE 真实大型组件抽取)**：真实抽取 L2C_FE 中的复杂 Vue 3 组件、Pinia Store、工具函数与类型定义。
- **Gate F (真实符号 Key 确定性与无损性)**：真实代码提取出的 `entity_key` 格式标准，且不随物理行漂移而失效。

### Layer 3 — 持久化与生命周期层 (Persistence & Lifecycle)
- **Gate G (真实代码端到端持久化)**：真实代码提取的符号与 `defines` 关系成功写入 Knowledge Core，元数据深度完整。
- **Gate H (真实工程代表性双 Pass 幂等恒等证明)**：真实代码执行 Pass 2 时：`created=0, updated=N, deleted=0`（N 严格为 Pass 1 ACTIVE 数），ID、Key、defines 三集合 100% 恒等。
- **Gate I (真实代码软删除与复活状态机)**：在隔离快照目录中模拟真实文件符号增删，验证 `ACTIVE ➔ DELETED ➔ ACTIVE` 状态自愈与计数正确性。
- **Gate J (三大工程混合入库物理隔离)**：同时入库三大工程，证明符号与关系按 `project_id` 物理隔离，0 跨工程污染。
- **Gate K (三段式计数硬约束审计)**：批次汇总报告中的三段式计数公式 100% 成立。
- **Gate L (真实代码同 Key 冲突防护)**：100% 继承 B-07 LOCK-PERSIST-08 语义，相同指纹去重，相异指纹触发 Identity Conflict 拒绝，不重新定义规则。
- **Gate M (真实超长标识符截断保护)**：真实工程中超长路径与符号安全截断至 `<= 255` 字符，且 `entity_key` 保持原始语义不降级。

### Layer 4 — 系统级安全与性能层 (System, Safety & Performance)
- **Gate N (三大外部工程绝对只读核验)**：整个验证过程前后，`HELLO_FE`, `HELLO_BE`, `L2C_FE` 的 `git status --porcelain` 新增变动严格为 0。
- **Gate O (真实工程采样端到端性能基准 B-08 Real-project Sampled E2E Baseline)**：建立 75 个真实文件（525 符号）的基准（解析 + 抽取 + 入库），平均单文件耗时 1.75ms。
- **Gate P (绝对零早熟图谱关系证明)**：数据库中仅包含 `predicate="defines"` 关系，绝对不存在 `calls`, `imports`, `extends` 等早熟关系，作为 MVP2-C 冻结输入契约。
- **Gate Q (资源稳定性契约 Resource Stability Contract)**：连续 3 次 Pass 循环执行，Traced 内存增量保持在稳定容差内，句柄与连接安全释放回基线。
- **Gate R (历史全量单测无回退)**：B-00 ~ B-07 全量单测（63 项）全部保持 100% 绿色通过。

---

## 四、实施计划与测试分层

### 1. 验证套件结构
```text
tests/
└── integration/
    └── b08/
        ├── __init__.py
        ├── test_real_projects_discovery_b08.py       # Layer 1: 发现与路由 (Gate A, B)
        ├── test_real_projects_extraction_b08.py      # Layer 2: 三大工程真实抽取与 Key (Gate C, D, E, F)
        ├── test_real_projects_persistence_b08.py     # Layer 3: 端到端持久化与双 Pass 幂等恒等证明 (Gate G, H, I, J)
        ├── test_real_projects_lifecycle_audit_b08.py # Layer 3: 计数审计、冲突拒绝、超长截断 (Gate K, L, M)
        ├── test_real_projects_system_audit_b08.py    # Layer 4: 只读红线、零早熟图谱、资源契约 (Gate N, P, Q, R)
        └── test_real_projects_benchmark_b08.py       # Layer 4: 吞吐量基准与分位数统计 (Gate O)
```

### 2. 数据库执行环境说明
- **默认执行**：基于 SQLite In-Memory 双引擎兼容层（具备 `JSONB` / `UUID` 适配，零外部 Docker 依赖，极速自验）。
- **生产集成**：当本地 Docker 的 PostgreSQL（端口 `54329`）运行时，自动连接执行真实 PostgreSQL 烟测。

---

## 五、验收交付物预期

1. **B-08 专属集成与系统验证套件**（`tests/integration/b08/` 6 大测试模块）。
2. **三大真实工程端到端全量扫描基准报告**。
3. **双 Pass 幂等恒等证明数据表**（ID Set, Key Set, Defines Edge Set 恒等证明）。
4. **三大外部源工程绝对只读终极审计日志**。
5. **`docs/mvp2/mvp2_step8_b08_real_projects_verification_report.md`** 终审报告。
6. **MVP2-B 整体结项与冷备份归档**。
