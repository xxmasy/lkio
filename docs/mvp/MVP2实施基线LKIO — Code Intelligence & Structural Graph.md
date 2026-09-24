# LKIO MVP2 实施基线 — Code Intelligence & Structural Graph (Preflight Lock v0.2)

> **阶段代号**：**MVP2**  
> **阶段全称**：**Code Intelligence & Structural Graph (代码智能与代码结构图谱)**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> **当前阶段状态**：**READY_TO_IMPLEMENT (PREFLIGHT_LOCKED)**  
> **核心使命**：让 LKIO 从 **“知道项目有哪些文件”** 进化到 **“知道代码里面有什么（Symbol / AST），以及代码之间是什么关系（Structural Relations）”**。

---

## 🛑 永久冻结的 6 大核心架构红线

后续任何 Agent 均**严禁擅自修改**以下 6 条架构红线：

1. **三个源项目只读**：`HELLO_FE`, `HELLO_BE`, `L2C_FE` 绝对物理只读，禁止写回、修改、临时生成或格式化任何源文件。
2. **严禁解析 .git 内部结构**：禁止任何针对 `.git/objects`、`refs`、`index` 等二进制内部结构的直接反序列化。
3. **Git 一律通过 subprocess 调用 Git CLI**：保持跨平台一致性、透明度与安全审计能力。
4. **敏感文件永不进入 Knowledge Core**：`.env`, 密钥 (`*.pem`, `*.key`), Token, 私钥, 证书等绝对物理阻断。
5. **严禁伪置信度**：所有关系必须绑定 `extraction_method` 与 `evidence`，禁止 AI 虚构无证据置信度。
6. **AST 是结构事实，不是业务推理 (MVP2 新增冻结)**：
   - `Tree-sitter / AST -> Structural Fact`（函数、类、导入、导出、调用是客观事实）。
   - **严禁**在 MVP2 中引入 LLM 猜测业务逻辑、业务语义、业务影响。业务推理归属 MVP3 (RAG)、MVP4 (Wiki)、MVP5 (Event)。

---

## 📌 MVP1 结项登记的架构债务

### 债务 1: Technology 分类规范化 (Ontology V0.2)
在 MVP1 中，框架与依赖存在概念混杂（如将 `Axios`、`Pinia`、`Spring Boot` 统称为 Framework）。MVP2 建立代码语义图后，将在本体层标准化为：
```text
Technology
├── Framework       (Vue, Spring Boot)
├── Runtime         (Node.js, JVM)
├── UI Library      (Element Plus)
├── State Management(Pinia)
├── Router          (Vue Router)
├── ORM             (MyBatis)
├── HTTP Client     (Axios)
├── Build Tool      (Vite, Maven)
└── Testing         (JUnit, Vitest)
```

### 债务 2: 前端 Bundle 体积指标 (Engineering Metric)
MVP1 结项时 Web 前端包体积为：
- `dist/assets/index.js`: ~1,731 kB
- `dist/assets/index.css`: ~369 kB  
此项作为工程技术债指标持续观测，**绝不提前在 MVP2 中引发过度优化或分散代码图谱的核心焦点**。

---

## 🔒 MVP2 Preflight Lock: 必须冻结的 6 个关键架构补丁

### 补丁 1: Tree-sitter 生产依赖“精确锁版”与 uv.lock 冻结
生产依赖**绝对禁止**使用宽松范围（如 `>= 0.23.0`），因 Tree-sitter 官方 grammar ABI 升级存在断代风险，必须严格锁定经过成熟验证的兼容矩阵：
```toml
tree-sitter == 0.25.2
tree-sitter-javascript == 0.25.0
tree-sitter-typescript == 0.23.2
tree-sitter-java == 0.23.5
```
- `uv.lock` 正式作为 MVP2 核心冻结产物纳管。
- **后续升级纪律**：必须新建 `Dependency Upgrade ADR` ➔ 兼容性测试 ➔ Gold Set Regression ➔ 性能测试 ➔ 人工批准。严禁直接 `uv lock --upgrade` 盲目提交。

### 补丁 2: calls 关系统一拆分为两层（调用事实 vs 目标解析）
在 AST 中，“明确出现 CallExpression”与“确定调用的是哪个目标 SYMBOL”是完全不同的两件事：
1. **第一层：调用点事实 (CALL_SITE)**
   - 提取代码中的调用位置：`loadLeads ── call_site ──► "getLeadList()"`
   - 置信度：`confidence = 1.0`, `method = "static_ast"`
2. **第二层：符号解析关系 (CALLS / UNRESOLVED_CALL)**
   - 若静态解析器通过 import、作用域链或类内方法**明确确定目标**：
     `loadLeads ── calls ──► src/api/lead.ts::getLeadList`
     `confidence = 1.0`, `method = "static_symbol_resolution"`
   - 若存在动态别名、注入、动态分发等**无法 100% 静态确立目标**时：
     `loadLeads ── unresolved_call ──► "getLeadList"`
     `confidence = 1.0`, `method = "unresolved_identifier"`
   - **红线**：严禁把未确定的调用猜成某个符号并附上 `confidence = 0.7`！

### 补丁 3: Component 与 Hook 的“原生事实”与“规则分类”严格解耦
- **AST 原生结构事实 (Native Facts)**：
  `Function`, `Class`, `Method`, `Variable`, `Interface`, `Type`, `Enum`
- **规则分类结果 (Rule-based Classifications)**：
  `Component`, `Hook`
- **存储模型规约**：
  符号实体必须同时记录 `symbol_type`、`base_symbol_type` 与 `classification_method`：
  ```json
  {
    "symbol_type": "HOOK",
    "base_symbol_type": "FUNCTION",
    "classification_method": "name_prefix_rule",
    "name": "useLeadState"
  }
  ```
  ```json
  {
    "symbol_type": "COMPONENT",
    "base_symbol_type": "OBJECT",
    "classification_method": "vue_sfc_block_rule",
    "name": "LeadDetails"
  }
  ```

### 补丁 4: 多维 AST 缓存键 (AST Cache Key)
缓存有效性**绝不能仅依赖 File SHA-256**，必须包含所有影响解析产出的上游参数：
```text
AST_CACHE_KEY = hash(
    file_sha256 + 
    parser_bundle_version + 
    extractor_version + 
    schema_version + 
    language_config_hash
)
```
- 当且仅当全部键值吻合时触发 `CACHE HIT`；只要 Extractor 代码变更或 Tree-sitter 版本升级，自动失效重算。

### 补丁 5: Vue SFC 采用 Block Slicer，不绑定社区 Vue Grammar
不引入社区维护的第三方 `tree-sitter-vue`，避免其破坏整体生态兼容性：
```text
.vue 单文件组件
   │
   ▼
[SFC Block Slicer]
   ├── <script> / <script setup> ──► tree-sitter-typescript / javascript (代码符号主干)
   ├── <template>                ──► Template Tag Slicer (提取子组件引用、属性、事件绑定、v-model、slot)
   └── <style>                   ──► Metadata Slicer (仅记录 scoped, lang, 行范围，不深入 CSS AST)
```

### 补丁 6: 性能指标基准固定“硬件与软件环境”
性能门槛必须绑定具体物理机与运行时基准：
- **基准环境 (Benchmark Env)**：
  - OS: Windows 11 64-bit
  - CPU: 多核 x86_64
  - RAM: 32 GB
  - Storage: NVMe SSD
  - Python: 3.12.10
  - Tree-sitter: 0.25.2
- **性能门槛**：
  - **冷启动全量解析 (Cold Parse)**：三大项目 6,000+ 文件 ≤ 45 秒。
  - **增量重扫解析 (Warm Parse)**：无改动时 ≤ 2 秒，AST 调用次数 = 0。

### 补丁 7: Parser 与持久层解耦（DTO 候选层）
**Parser 结果严禁直接耦合并写入 SQLAlchemy 数据库模型**：
```text
Source File ──► Parser ──► Normalized AST ──► Extractor ──► SymbolCandidate (DTO) ──► Persistence (DB)
```
通过纯 Python `@dataclass` 隔离 AST 解析与数据库存储，保证未来可无损替换解析后端。

---

## 一、MVP2 总体数据处理流水线

```text
Project File
   │
   ▼
[Sensitive Filter] ──────► 阻断敏感配置
   │
   ▼
[AST Cache Key Gate] ────► HIT: 复用上期 Symbol (0 AST 调用)
   │ (MISS)
   ▼
[Parser Router]
   ├── .ts / .tsx / .js / .jsx ──► Tree-sitter TS/JS
   ├── .java                   ──► Tree-sitter Java
   └── .vue                    ──► SFC Block Slicer ──► TS/JS Parser + Template Slicer
   │
   ▼
[Normalized AST Output]
   │
   ▼
[Symbol Extractor] ────────────► 生成 SymbolCandidate DTO (含物理行号对齐)
   │
   ▼
[Symbol Classifier] ───────────► 标记 base_symbol_type 与 classification_method
   │
   ▼
[Relation Resolver]
   ├── STATIC (1.0) ───────────► defines, extends, implements, 明确 imports
   ├── RESOLVED_CALL (1.0) ────► 明确对应到目标的 calls
   └── UNRESOLVED (1.0) ───────► 无法静态确定目标的 unresolved_call (记录字面量)
   │
   ▼
[Graph Persistence] ───────────► 原子写入 / 更新 Entity & Relation，增量淘汰旧符号
```

---

## 二、MVP2 实施阶段拆解 (5 大阶段)

| 阶段代号 | 阶段名称 | 核心产出与验证目标 |
|---|---|---|
| **MVP2-A (Preflight)** | **Tree-sitter 基础设施与 Vue 切片器** | 精确锁版依赖、`ParserFactory`、`SfcBlockSlicer`、物理行号映射、三大项目冒烟测试 (0 业务推理)。 |
| **MVP2-B** | **代码符号提取 (Symbol Extraction)** | DTO 提取器、`SYMBOL` 确定性 Key、AST 结构事实与规则分类解耦、数据库模型适配。 |
| **MVP2-C** | **代码结构图谱 (Code Structural Graph)** | `defines`, `imports`, `call_site`, `calls`, `unresolved_call`, `extends`，多维 AST 缓存网关。 |
| **MVP2-D** | **跨工程代码图谱 (Cross-project Graph)** | 跨工程公共模块、共享组件与契约引用静态连接。 |
| **MVP2-E** | **API 端到端契约追溯 (独立隔离)** | 前端 API Client 路由 ➔ HTTP Endpoint ➔ 后端 Controller ➔ Service ➔ DB 追溯链路。 |
| **MVP2-Acceptance** | **全量入库、Gold Set 与终审验收** | 全量扫描无报错、只读核验通过、Gold Set 回归通过、冷备份固化。 |

---

## 三、MVP2-A (Preflight) 验收标准

在进入 MVP2-B 之前，必须通过 MVP2-A Preflight 门禁：
1. `tree-sitter==0.25.2` 及对应 grammar 正确安装，0 编译错误。
2. `ParserFactory` 能够无损返回 TS, TSX, JS, Java 解析器实例。
3. `SfcBlockSlicer` 正确切分 `.vue` 文件，且提取出的 `<script>` 块与原始物理行号绝对一致。
4. 对三大真实源项目核心样本文件执行 AST 冒烟解析，解析成功率 100%。
5. 三大源工程 `git status --porcelain` 差异严格为 0。

---

## 🔒 状态宣告

```text
MVP0 = COMPLETED / FROZEN
MVP1 = COMPLETED / FROZEN
MVP2 = READY_TO_IMPLEMENT (PREFLIGHT_LOCKED)
```
