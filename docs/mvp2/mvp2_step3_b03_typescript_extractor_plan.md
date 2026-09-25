# LKIO MVP2-B B-03 实施规划 — TypeScript / JavaScript Symbol Extractor

> **阶段**：**MVP2-B (Step 2.2 — B-03)**  
> **状态**：**READY_TO_IMPLEMENT**  
> **前置阶段状态核查**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2-A = COMPLETED / FROZEN**  
> - **B-00 (Schema & 边界锁) = COMPLETED / FROZEN**  
> - **B-01 (Database TEXT 迁移) = COMPLETED / FROZEN**  
> - **B-02 (符号身份与标准化体系) = COMPLETED / FROZEN (5/5 判据闭环，13 项单测 0.02s 全绿)**  
> **执行约束**：仅实现 TS/JS/TSX/JSX 符号提取并输出 `SymbolCandidate` DTO；严禁触碰 Java、Vue SFC 主流程、DB 持久化、Call/Import/Export 关系图谱或任何业务推理。

---

## 一、对照上一轮 (B-00 ~ B-02) 完成情况核验

1. **B-00 边界规范**：已锁定 9 大受控 Native 类型与 HOOK/COMPONENT 规则分类机制。
2. **B-01 存储规范**：已完成 PostgreSQL `entities.entity_key` 升级为 `TEXT NOT NULL UNIQUE`，杜绝长 Key 截断风险。
3. **B-02 身份规范**：
   - 语言分化签名：`canonicalize_ts_signature` 与 `canonicalize_java_signature`。
   - 词法作用域：`build_qualified_name` 统一采用 `::` 分隔符。
   - 5 大准入判据通过：行漂移免疫、词法作用域隔离、Java 重载分化、TS 可选/Rest 分化、Vue 多 script 隔离。

---

## 二、B-03 核心目标与 Acceptance Gates

### 1. 唯一使命
从 Tree-sitter `typescript`, `tsx`, `javascript` 语法树中，提取原生符号及分类符号：
- `CLASS`
- `INTERFACE`
- `FUNCTION`
- `METHOD`
- `VARIABLE`
- `ENUM`
- `TYPE`
- `COMPONENT` (规则分类: `jsx_function_component_v1`)
- `HOOK` (规则分类: `name_prefix_rule_v1`)

完成：原生符号 + 词法作用域 (`qualified_name`) + 规范签名 (`canonicalize_ts_signature`) + 物理坐标 (1-based line, 0-based col) + 修饰符 + 导出元数据 + 分类元数据 + AST 证据，输出 `list[SymbolCandidate]`。

### 2. 16 项 Acceptance Gates (A ~ P)
- **Gate A: TS Parser Integration**: 适配 `.ts`, `.mts`, `.cts`。
- **Gate B: JS Parser Integration**: 适配 `.js`, `.mjs`, `.cjs`。
- **Gate C: CLASS**: 提取类名、词法路径、extends/implements 元数据、修饰符。
- **Gate D: INTERFACE**: 提取接口顶层符号，B-03 不展开成员符号。
- **Gate E: FUNCTION**: 函数声明提取名称、签名、参数、异步/生成器、导出状态。
- **Gate F: METHOD**: 类方法提取 `ClassName::methodName`，包含签名与特征码。
- **Gate G: VARIABLE**: 顶层 `const`, `let`, `var`；Arrow Function 标记 `function_kind="arrow", is_callable=true`，`base_symbol_type=VARIABLE`。
- **Gate H: ENUM**: TS 枚举提取，成员存入 `metadata["enum_members"]`。
- **Gate I: TYPE**: TS 类型别名提取，复杂类型存入 `metadata["type_shape"]`。
- **Gate J: COMPONENT Classification**: PascalCase + JSX/Fragment 元素 + 可调用形态 ➔ `COMPONENT` (`jsx_function_component_v1`)。
- **Gate K: HOOK Classification**: `^use[A-Z0-9].*` 命名 ➔ `HOOK` (`name_prefix_rule_v1`)，保留 `base_symbol_type`。
- **Gate L: Export Metadata**: 准确记录 `is_exported: bool` 与 `export_kind` (`"named"`, `"default"`, `"none"`)。
- **Gate M: Scope / Qualified Name**: 严格遵循 B-02 的 `[scope::]symbol` 词法作用域链。
- **Gate N: Signature Normalization**: 必须调用 B-02 的 `canonicalize_ts_signature()` 及 16 位特征码。
- **Gate O: Physical Coordinates**: 严格统一 `1-based line` 与 `0-based column`。
- **Gate P: Gold Set 100% PASS**: 6 组金标准测试用例 100% 绿标（< 5s）。

---

## 三、实施步骤与节奏

1. **Step 1: 完善 `SymbolCandidate` DTO 与 Extractor 核心重构**
   - 增加 `export_kind` (`named` / `default` / `none`)。
   - 重构 `core/extraction/typescript.py`：
     - 实现多层词法作用域栈管理（支持顶级、类内部、嵌套函数等 `outer::inner`）。
     - 接入 B-02 的 `canonicalize_ts_signature()` 与 `build_qualified_name()`（统一 `::` 分隔符）。
     - 严格落实 Arrow Function 规则：`base_symbol_type = VARIABLE`，`function_kind = "arrow"`，`is_callable = true`；若为 Hook/Component 则分类提升。
     - 严格落实 React/JSX Component 规则（`jsx_function_component_v1`，PascalCase + JSX 包含检测）。
     - 严格落实 Enum 成员收集与 Type Alias 收集。
     - 附带可信度证据：`confidence = 1.0`, `extraction_method = "static_ast"`, `evidence = {...}`。
     - 容错保护：遇到 AST `ERROR` 节点，局部告警而不打断全文件提取。
2. **Step 2: 创建 Gold Dataset 目录与用例**
   - `tests/gold/mvp2/symbols/typescript/basic.ts`
   - `tests/gold/mvp2/symbols/typescript/advanced.ts`
   - `tests/gold/mvp2/symbols/javascript/basic.js`
   - `tests/gold/mvp2/symbols/tsx/basic.tsx`
   - `tests/gold/mvp2/symbols/tsx/classification.tsx`
   - `tests/gold/mvp2/symbols/jsx/basic.jsx`
3. **Step 3: 编写严格断言的单元测试与 Gold 回归**
   - 针对 16 项 Acceptance Gates 编写详尽断言（断言符号类型、基类类型、QName、签名、特征码、物理行号列号、分类方法、导出状态）。
   - 验证运行时间 < 5 秒。
4. **Step 4: 审查与结项报告**
   - 审查源项目物理只读性。
   - 形成 `docs/mvp2/mvp2_step3_b03_typescript_extractor_report.md`。
   - 冻结 B-03 状态，等待用户确认后进入 B-04。
