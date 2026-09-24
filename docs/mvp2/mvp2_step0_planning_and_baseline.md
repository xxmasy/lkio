# LKIO MVP2 - Step 2.0: 规划、架构基线固化与前置审查报告

> **执行周期**: MVP2 (Code Intelligence & Structural Graph)  
> **状态**: BASELINE_FROZEN / READY_TO_IMPLEMENT  
> **前序文档检验**: [mvp1_acceptance_report.md](file:///C:/WorkSpace/lkio/docs/mvp1/mvp1_acceptance_report.md)  
> **当前活动 MVP**: MVP2 (唯一活动阶段，禁止越界至 MVP3 及后续阶段)  
> **实施基线**: [MVP2实施基线LKIO — Code Intelligence & Structural Graph.md](file:///C:/WorkSpace/lkio/docs/mvp/MVP2实施基线LKIO%20—%20Code%20Intelligence%20&%20Structural%20Graph.md)

---

## 1. 对照上一轮 (MVP1) 终审结项与完成情况检验

在启动 MVP2 规划之前，对前序阶段进行严谨的阶段门复核：

1. **MVP0 状态核查**:
   - 状态：**COMPLETED / FROZEN**
   - 基础环境、PostgreSQL 18 + pgvector 0.8.6、SQLAlchemy 基础模型、FastAPI 脚手架、Vue 3 前端拓扑看板全部固化，冷备份归档为 `mvp0_milestone.sql`。
2. **MVP1 状态核查**:
   - 状态：**COMPLETED / FROZEN**
   - 16 项 Acceptance Gates 全部达成；19 项 DoD 全部勾选；16 项自动化测试全量通过；三大工程只读性得到机械级证明；
   - 建立 `tests/gold/mvp1/` 黄金基线测试集；冷备份归档为 `mvp1_milestone.sql` (12.4 MB，8,115 实体，8,112 关系)；
   - 代码完全提交至 Git (`32b58ea` / `9e08865`)，工作树保持 100% 干净。
3. **准入判定**:
   - 前序 MVP0 与 MVP1 全部稳固封箱，无未决阻塞问题，**满足进入 MVP2 的全部准入条件**。

---

## 2. MVP1 非阻塞架构债务正式登记

根据 MVP1 终审决议，以下两项正式登记为系统技术债务与演进指标：

### 2.1 债务 1: Technology 分类规范化 (Ontology V0.2)
- **现状**: MVP1 中 `FRAMEWORK` 实体混合了不同层次的技术概念（如 Vue、Element Plus、Pinia、Axios、Spring Boot 均标记为 Framework）。
- **规划**: MVP2 将在代码图谱建立后统一技术分类，收敛为 `Technology` 及其子类：
  `Framework`, `Runtime`, `UI Library`, `State Management`, `Router`, `ORM`, `HTTP Client`, `Build Tool`, `Testing`。
- **纪律**: MVP1 保持现状，不破坏已有摄取基线。

### 2.2 债务 2: 前端 Bundle 体积指标 (Engineering Metric)
- **现状**: Web 端产物为 `dist/assets/index.js` (1.73 MB), `dist/assets/index.css` (369 kB)。
- **规划**: 作为工程技术债指标持续监测，未来作为项目健康度指标纳入演化分析，**绝不提前占用 MVP2 核心资源进行过早优化**。

---

## 3. 永久冻结的 6 大核心架构红线

在原有 5 条红线基础上，新增第 6 条红线并永久冻结：

1. **三个源项目只读**：`HELLO_FE`, `HELLO_BE`, `L2C_FE` 绝对只读。
2. **严禁解析 .git 内部结构**：禁止任何针对 `.git` 内部二进制文件的直接读取。
3. **Git 一律通过 subprocess 调用 Git CLI**：统一使用标准 CLI 工具。
4. **敏感文件永不进入 Knowledge Core**：物理隔离密钥与私钥资产。
5. **严禁伪置信度**：所有关系必须绑定证据与抽取方法。
6. **AST 是结构事实，不是业务推理 (MVP2 新增冻结)**：
   - `Tree-sitter / AST -> Structural Fact`（客观静态事实）。
   - 严禁引入 LLM 猜测业务逻辑；业务语义留待 MVP3 (RAG) / MVP4 (Wiki) / MVP5 (Event)。

---

## 4. MVP2 核心目标与实施步骤拆解

### 核心定位
**让 LKIO 从“知道有哪些文件”升级到“知道代码里面有什么（Symbol / AST），以及代码之间是什么关系（Structural Relations）”。**

### 细分子阶段规划
```text
MVP2-A: Tree-sitter 基础设施
   │    • 引入 tree-sitter, tree-sitter-typescript, tree-sitter-javascript, tree-sitter-java
   │    • 建立 Vue SFC 切片解析器 (template / script / style)，保持原始行号 100% 对齐
   │    • 验证三大源工程基础 AST 解析稳定性，零业务推理
   ▼
MVP2-B: Symbol Extraction (符号提取)
   │    • 提取 Class, Interface, Function, Method, Variable, Component, Hook, Enum, Type
   │    • 规范确定性 Key: SYMBOL:<proj>:<file>:<type>:<name>[:line]
   │    • 固化属性：行号、列号、代码签名、修饰符、解析器版本
   ▼
MVP2-C: Code Structural Graph (单工程代码图谱)
   │    • 建立 FILE defines SYMBOL, imports, exports, calls, extends, implements, uses
   │    • 严格区分静态确定事实 (confidence=1.0) 与动态推断关系 (confidence<1.0)
   ▼
MVP2-D: Cross-project Code Graph (跨工程代码图谱)
   │    • 建立跨工程公共包、公共模块与确定性契约关联
   ▼
MVP2-E: API to Backend Traceability (契约端到端追溯 - 明确独立隔离)
        • 前端 API 路由 ➔ HTTP Endpoint ➔ 后端 Controller ➔ Service ➔ DB
        • 独立作为后续专题执行，不污染基础 AST 阶段
```

---

## 5. 下一步行动 (Step 2.1: MVP2-A 基础设施启动)

### 核心任务
1. **安装现代化 Tree-sitter 预编译依赖**:
   - `uv add tree-sitter tree-sitter-typescript tree-sitter-javascript tree-sitter-java`
2. **实现解析器抽象工厂 (`code/parsers/factory.py`)**:
   - 统一初始化并管理 TS, JS, Java 语法树解析器。
3. **实现 Vue SFC 切片提取器 (`code/parsers/vue_sfc.py`)**:
   - 精确提取 `<script>` 与 `<script setup>` 块，保留物理行号对齐。
4. **解析冒烟测试与三大工程实测**:
   - 验证对 `HELLO_FE`, `HELLO_BE`, `L2C_FE` 真实代码文件（含 Vue, TS, Java）的解析无报错。
5. **撰写 Step 2.1 实施检验报告**:
   - 归档于 `docs/mvp2/mvp2_step1_treesitter_infra.md`。
