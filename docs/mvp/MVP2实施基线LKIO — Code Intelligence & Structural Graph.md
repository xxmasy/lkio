# LKIO MVP2 实施基线 — Code Intelligence & Structural Graph

> **阶段代号**：**MVP2**  
> **阶段全称**：**Code Intelligence & Structural Graph (代码智能与代码结构图谱)**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> **当前阶段状态**：**READY_TO_PLAN / BASELINE_FROZEN**  
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

## 📌 MVP1 结项登记的架构债务 (登记至基线)

以下两项为 MVP1 终审确认的非阻塞架构事项，正式登记在案：

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

## 一、MVP2 边界与阶段拆解

```text
MVP1 资产层 (已完成)
Project ── Repository ── Branch ── Commit ── Directory ── File ── Language ── Framework ── Dependency
                                                │
                                                ▼
MVP2 代码智能与结构图谱层 (当前规划)
File ── defines ──► Symbol (Class / Function / Method / Interface / Component / Hook / Variable)
                      │
                      ├── imports ──► Symbol / Module
                      ├── exports ──► Symbol
                      ├── calls ────► Symbol (静态确定 confidence=1.0 / 推断 confidence<1.0)
                      ├── extends ──► Class
                      └── implements► Interface
```

### MVP2 分步实施计划 (5 大阶段)

| 子阶段编号 | 阶段名称 | 核心目标与技术边界 |
|---|---|---|
| **MVP2-A** | **Tree-sitter 基础设施** | 引入现代化 Tree-sitter 运行时，支持 TS, JS, TSX, JSX, Java 以及 Vue SFC 切片解析，验证三大项目解析稳定性，零业务推理。 |
| **MVP2-B** | **Symbol Extraction (符号提取)** | 从 AST 提取精确代码符号（类、接口、函数、方法、变量、组件、Hook），固化精确行号/列号、代码签名与解析版本。 |
| **MVP2-C** | **Code Structural Graph (单工程结构图谱)** | 建立 `defines`, `imports`, `exports`, `calls`, `extends`, `implements`。严格区分静态确定事实 (1.0) 与动态推断关系 (<1.0)。 |
| **MVP2-D** | **Cross-project Code Graph (跨工程基础图谱)** | 建立跨项目静态确定关系（如共享包、公共模块、契约引用）。 |
| **MVP2-E** | **API to Backend Traceability (契约端到端追溯)** | **独立隔离**：前端 API Client 路由 ➔ HTTP Endpoint ➔ 后端 Controller ➔ Service ➔ DB 链路。不与基础 AST 混杂。 |

---

## 二、Tree-sitter 解析器架构与环境策略

### 2.1 依赖选型与版本锁定
- Python 绑定采用官方现代化预编译 Wheels，彻底避免 Windows 环境编译 C/C++ 依赖地狱：
  - `tree-sitter >= 0.23.0`
  - `tree-sitter-typescript >= 0.23.0` (内置 TypeScript 与 TSX 解析器)
  - `tree-sitter-javascript >= 0.23.0` (内置 JavaScript 与 JSX 解析器)
  - `tree-sitter-java >= 0.23.0` (Java 解析器)
- 解析器实例由单例工厂 `ParserFactory` 统一管理，支持线程安全与懒加载。

### 2.2 支持语言矩阵
1. **TypeScript / TSX**：`.ts`, `.tsx`, `.mts`, `.cts`
2. **JavaScript / JSX**：`.js`, `.jsx`, `.mjs`, `.cjs`
3. **Java**：`.java`
4. **Vue SFC**：`.vue`（专门切片解析）

---

## 三、Vue SFC 单文件组件解析方案

Vue SFC 并非普通纯文本文件，必须按语法块进行结构化解构：

```text
Component.vue
  ├── <template>       ──► HTML/Template 语法块 (提取子组件引用、事件绑定、双向绑定)
  ├── <script>         ──► 经典 Options API / 组合式脚本 (以 TS/JS 语法解析)
  ├── <script setup>   ──► Vue 3 Composition API setup 脚本 (以 TS/JS 语法解析)
  └── <style>          ──► CSS/SCSS/LESS 样式块 (暂不深入 AST，提取作用域标记)
```

### 3.1 坐标对齐原则 (Coordinate Preservation)
- 提取 `<script>` 或 `<script setup>` 时，采用**虚拟前置换行补齐**或**行偏移计算器 (Line Offset Map)**，确保解析出的符号在 `start_line` / `end_line` 上与原始 `.vue` 文件的物理行号**100% 绝对一致**。
- 绝不因代码提取导致行号错位，保证后续代码审查、证据追踪可精准定位。

---

## 四、Symbol 规范与确定性身份 (Schema)

### 4.1 符号类型 (Symbol Types)
```text
CLASS          类定义 (class LeadController, class UserService)
INTERFACE      接口定义 (interface LeadDTO, interface TableProps)
FUNCTION       独立函数 / 导出函数 (function formatAmount, const calculateTax)
METHOD         类方法 / 对象方法 (listLeads(), executeQuery())
VARIABLE       顶层常量 / 导出变量 (const API_BASE_URL, const statusMap)
COMPONENT      Vue / React 前端组件 (LeadList.vue, UserAvatar)
HOOK           前端 Vue/React 组合式函数 (useAuth, useTablePagination)
ENUM           枚举定义 (enum LeadStatus, enum UserRole)
TYPE           类型别名 (type LeadId = string, type QueryParams)
```

### 4.2 符号唯一业务身份 (Deterministic Entity Key)
严禁仅依赖自增 ID 或随机 UUID，统一采用物理确定性 Key：
```text
SYMBOL:<project_key>:<file_rel_path>:<symbol_type>:<canonical_symbol_name>[:start_line]
```
例如：
- `SYMBOL:HELLO_FE:src/views/sales/LeadList.vue:COMPONENT:LeadList`
- `SYMBOL:HELLO_FE:src/views/sales/LeadList.vue:FUNCTION:loadLeads:48`
- `SYMBOL:HELLO_BE:src/main/java/com/demo/LeadController.java:CLASS:LeadController`
- `SYMBOL:HELLO_BE:src/main/java/com/demo/LeadController.java:METHOD:list:32`

### 4.3 符号实体核心属性 (Attributes)
```json
{
  "file_id": "uuid-of-file-entity",
  "symbol_type": "METHOD",
  "symbol_name": "list",
  "canonical_name": "LeadController.list",
  "start_line": 32,
  "end_line": 45,
  "start_column": 4,
  "end_column": 5,
  "signature": "public ResponseEntity<List<LeadDTO>> list(@RequestParam LeadQuery query)",
  "language": "Java",
  "parser_version": "tree-sitter-java@0.23.5",
  "modifiers": ["public"],
  "is_exported": true
}
```

---

## 五、Relation 关系规范与置信度纪律

### 5.1 代码关系类型
```text
FILE   ── defines    ──► SYMBOL   (文件定义了某个符号)
SYMBOL ── imports    ──► SYMBOL   (符号引入了模块或具体符号)
SYMBOL ── exports    ──► SYMBOL   (模块对外导出了符号)
SYMBOL ── calls      ──► SYMBOL   (符号内部调用了另一个符号)
SYMBOL ── extends    ──► CLASS    (类继承了父类)
SYMBOL ── implements ──► INTERFACE(类实现了接口)
SYMBOL ── uses       ──► SYMBOL   (函数引用了类型、变量或常量)
```

### 5.2 置信度强弱分离纪律 (Inviolable Discipline)
1. **静态确定事实 (Static Deterministic Facts)**：
   - 包含关系：`defines`, `extends`, `implements`, 明确的 `imports`。
   - `confidence = 1.00000`
   - `metadata.inferred = false`
   - `metadata.method = "static_ast"`
   - `metadata.evidence = { "node_type": "import_specifier", "line": 12 }`
2. **推断关系 (Inferred / Dynamic Relations)**：
   - 动态调用、动态属性分发、未解构上下文的 `this.foo()`。
   - `confidence < 1.00000` (如 `0.70000`)
   - `metadata.inferred = true`
   - `metadata.reason = "dynamic_property_resolution"`

---

## 六、增量解析与 AST 缓存策略 (Incremental Engine)

针对三大源项目共 6,000+ 个文件的解析效率要求：

```text
File Scan (Step 1.2)
       │
       ├── File SHA-256 == Previous Snapshot SHA-256 ?
       │         │
       │         ├── YES ──► SKIP AST Parsing (保留原有 Symbol 实体与关系)
       │         │
       │         └── NO  ──► Parse via Tree-sitter (提取 Symbol 并原子更新)
       │
       └── File vanished ──► Mark existing Symbols status = "deleted"
```

### 6.1 缓存性能指标
- **冷启动全量解析**：全量 6,000+ 文件解析总时长 ≤ 45 秒。
- **增量重扫解析**：未改动代码时，增量解析耗时 ≤ 2 秒，AST 调用次数为 0。

---

## 七、容错隔离与降级策略 (Fault Tolerance)

1. **语法错误宽容 (Syntax Error Tolerance)**：
   - 当遇到开发中的不完整代码或语法错误文件时，Tree-sitter 内置 `ERROR` 节点容错机制。
   - 提取合法部分符号，不可丢弃整个文件的全部符号。
   - 将异常记录于 `ingestion_run.warnings`（例如 `syntax_warning_at_line_45`），绝不崩溃流水线。
2. **大文件防卡死**：
   - 超过 2MB 的超大自动生成代码（如巨大 mock 数据文件、打包产物）自动跳过 AST 解析，打上 `skip_ast_reason: "oversized"` 标签。
3. **超时保护**：
   - 单文件 AST 解析超时设为 5 秒，防止极端正则或嵌套语法引发 CPU 假死。

---

## 八、MVP2 验收门 (16 项 Acceptance Gates)

| 门编号 | 验收门名称 | 达标判定标准 |
| :---: | :--- | :--- |
| **A** | **解析器安装与集成** | Tree-sitter 现代化 wheels 安装就绪，跨平台 0 编译报错。 |
| **B** | **三大项目解析无损** | `HELLO_FE`, `HELLO_BE`, `L2C_FE` 全部有效代码文件完成 AST 解析。 |
| **C** | **Vue SFC 切片精度** | `.vue` 文件准确切分 `<template>` 与 `<script>`，符号行号与物理文件完全一致。 |
| **D** | **Java 符号完整性** | `hello-backend` 提取出完整的 Class, Method, Field, Annotation 元数据。 |
| **E** | **TypeScript 符号完整性**| 前端项目完整提取 Interface, Type, Function, Component, Hook。 |
| **F** | **组件与 Hook 识别** | 正确识别 Vue 组件定义与 `useXxx` 自定义 Hook 符号。 |
| **G** | **Defines 关系构建** | 建立 `FILE contains/defines SYMBOL` 基础包含图谱。 |
| **H** | **Imports 静态推导** | 正确解析相对路径与模块 import，连接符号之间的依赖边。 |
| **I** | **静态/推断置信度隔离**| 严格区分 1.0 确定事实与 <1.0 推断关系，证据链字段完备。 |
| **J** | **增量缓存生效** | 二次扫描实测基于 SHA-256 命中跳过，解析耗时下降 90% 以上。 |
| **K** | **符号软删除支持** | 删除文件时，关联的 Symbol 实体联动标记为 `deleted`。 |
| **L** | **超大文件与语法容错** | 面对异常语法文件正常跳过或部分提取，流水线不崩溃。 |
| **M** | **源项目绝对只读** | 解析前后三大工作区 `git status --porcelain` 差异严格为 0。 |
| **N** | **API2-E 明确隔离** | 前端 API ➔ 后端 Controller 追溯链明确留至 MVP2-E，不提前破坏 MVP2 核心。 |
| **O** | **Web UI 符号浏览** | 前端支持在项目详情中按文件浏览代码符号树与结构关系。 |
| **P** | **MVP2 Gold Set 回归** | 建立 `tests/gold/mvp2/` 黄金测试集，回归断言 100% 通过。 |

---

## 九、MVP2 Definition of Done (DoD)

```text
[ ] Tree-sitter 预编译依赖就绪 (TS, JS, Java)
[ ] Vue SFC 切片解析器与物理行号无损对齐
[ ] Java AST 提取器 (Class, Interface, Method, Field, Annotation)
[ ] TypeScript / JavaScript AST 提取器 (Function, Component, Hook, Class)
[ ] 符号数据表实体扩展与确定性 Key (SYMBOL)
[ ] 静态导入与导出关系连接器 (imports / exports)
[ ] 静态与推断置信度严格分离与证据记录
[ ] 增量解析 SHA-256 缓存网关
[ ] 异常语法与超大文件容错降级
[ ] 三大项目全量代码符号图谱入库验证
[ ] 源项目机械级只读核验通过 (0 git changes)
[ ] MVP2-E (API 跨工程端到端追溯) 保持边界独立
[ ] Web 控制台代码符号看板与图谱下钻
[ ] 黄金回归数据集 (tests/gold/mvp2/) 建立并通过
[ ] 数据库冷备份生成 (mvp2_milestone.sql)
[ ] 终审验收报告归档于 docs/mvp2/
```

---

## 十、阶段演进路线

```text
MVP0 (Environment & Knowledge Core) ──► ✅ COMPLETED / FROZEN
MVP1 (Project Ingestion)            ──► ✅ COMPLETED / FROZEN
MVP2 (Code Intelligence & Graph)    ──► 🚀 BASELINE FROZEN / READY_TO_IMPLEMENT
  ├── MVP2-A: Tree-sitter 基础设施
  ├── MVP2-B: Symbol Extraction
  ├── MVP2-C: Code Structural Graph
  ├── MVP2-D: Cross-project Code Graph
  └── MVP2-E: API to Backend Traceability (独立链路)
MVP3 (Hybrid RAG)                   ──► 🔒 LOCKED
MVP4 (LLM Wiki)                     ──► 🔒 LOCKED
```
