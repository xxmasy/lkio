# LKIO MVP2-B B-05 终审结项报告 — Vue SFC Extractor

> **当前阶段**：**MVP2-B (Step 2.3 — B-05: Vue Single File Component Extractor)**  
> **终审结论**：**6 大 Vue 专项锁与 16 项 Acceptance Gates 100% 闭环 ➔ B-05 COMPLETED / FROZEN ➔ B-06 READY_TO_PLAN**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2-A = COMPLETED / FROZEN**  
> - **B-00 / B-01 / B-02 / B-03 / B-04 = COMPLETED / FROZEN**  
> - **B-05 = COMPLETED / FROZEN**  
> **执行约束**：已严格隔离阶段边界，本报告核心准入依据仅引用 B-05 独立测试套件与金标准；三大外部源工程（HELLO_FE, HELLO_BE, L2C_FE）保持 100% 物理只读，无任何跨阶段越界操作。

---

## 一、6 大 Vue 专项锁 (Boundary Locks) 闭环核验

在实施阶段，针对用户审阅冻结的 6 项 Vue 语法与语义边界，已全部通过针对性测试断言与工程落地：

### 1. LOCK-VUE-01：主组件符号的 Synthetic 语义与 Provenance 溯源
- **问题与挑战**：`.vue` 文件通常通过隐式默认导出构成单文件组件，其物理 AST 中并不存在显式的 `export default class/function Foo` 顶层节点。若将其伪装成原生 AST 提取符号，会破坏后续事件溯源与代码证据链的可信度。
- **实施动作**：
  在 [`core/extraction/vue.py`](file:///C:/WorkSpace/lkio/core/extraction/vue.py) 中，主组件符号被确立为合成符号：
  - `symbol_type = SymbolType.COMPONENT.value`
  - `base_symbol_type = SymbolType.VARIABLE.value`
  - `classification_method = "vue_sfc_rule_v1"`
  - `metadata["synthetic"] = True`
  - `metadata["source_kind"] = "vue_sfc_file_context"`
  - `metadata["component_context"] = True`
  - `metadata["extraction_method"] = "sfc_structure"`
  - `metadata["confidence"] = 1.0`
  - `metadata["evidence"] = {"method": "sfc_structure", "file": ..., "file_stem": ...}`
- **实测验证**：
  在 `basic_setup.vue`、`options_api.vue`、`multi_script.vue`、`macros_and_bindings.vue` 中均通过断言核验。
- **核验结论**：**100% PASSED**。

---

### 2. LOCK-VUE-02：证据体系分离 (Evidence Taxonomy)
- **问题与挑战**：Vue SFC 包含脚本、模板、样式等多种异构区块，不能将所有证据笼统标记为 `static_ast`。
- **实施动作**：
  明确四层证据归属分类：
  1. `<script>` 与 `<script setup>` 内通过 Tree-sitter AST 解析的符号：`evidence.extraction_method = "static_ast"`。
  2. `<template>` 结构化抽取的组件标签与指令：`evidence.method = "static_template"`。
  3. `<style>` 区块元数据：`evidence.method = "static_sfc_metadata"`。
  4. SFC 顶层主组件符号：`evidence.method = "sfc_structure"`。
- **实测验证**：
  各区块提取结果中严格携带对应分类标签，无混淆或降级。
- **核验结论**：**100% PASSED**。

---

### 3. LOCK-VUE-03：模板指令与事件事实结构化 (Zero Premature String Serialization)
- **问题与挑战**：若在抽取层提前将模板绑定拼接为字符串（如 `"click->handleQuery"` 或 `":loading->isLoading"`），会丢失原始指令、修饰符、参数与表达式的结构化信息，阻碍 MVP2-C 建立精确调用边。
- **实施动作**：
  在 [`core/parsing/template_parser.py`](file:///C:/WorkSpace/lkio/core/parsing/template_parser.py) 中，完整提取为强类型字典结构：
  ```python
  # Event Binding
  {
      "directive": "on",
      "event": "click",
      "expression": "handleQuery",
      "modifiers": ["prevent"],
      "raw_attr": "@click.prevent=\"handleQuery\"",
      "line": 6,
      "evidence": {"method": "static_template", "line": 6}
  }
  # Property Binding
  {
      "directive": "bind",
      "argument": "loading",
      "expression": "loading",
      "modifiers": [],
      "raw_attr": ":loading=\"loading\"",
      "line": 6,
      "evidence": {"method": "static_template", "line": 6}
  }
  ```
- **实测验证**：
  验证 `macros_and_bindings.vue` 中的 `@submit.prevent="handleSubmit"`、`v-model="keyword"`、`:count="itemCount"` 均精确以结构化对象保存，无字符串伪造。
- **核验结论**：**100% PASSED**。

---

### 4. LOCK-VUE-04：Options API 结构事实作为组件元数据
- **问题与挑战**：在 Vue 2/3 Options API 中，`methods`、`computed`、`data` 等是对象字面量的属性（Object Properties）。若直接抽取为顶级 `METHOD` 符号，不仅违反 B-03 TypeScript/JavaScript Extractor 的规范（对象字面量属性不作为顶层函数/方法），更会导致跨文件符号重名冲突。
- **实施动作**：
  1. 普通 `<script>` 的顶层代码依然复用冻结的 B-03 抽取器；
  2. 对 `export default { methods: { ... }, computed: { ... } }` 进行 AST 遍历，将结构事实保存至主组件的 `metadata["options_api"]`：
     ```json
     {
       "data": ["leadList", "loading"],
       "computed": ["activeCount"],
       "methods": ["fetchLeads", "handleDetail"],
       "watch": ["filterKeyword"],
       "props": ["categoryId"],
       "emits": ["select"],
       "components": [],
       "directives": []
     }
     ```
  3. 绝对不产生伪造的独立顶级 `METHOD` 符号。
- **实测验证**：
  `options_api.vue` 中仅产生主组件 `options_api` 符号，其 `metadata["options_api"]["methods"]` 包含 `["fetchLeads", "handleDetail"]`，符号表中无伪造的 `METHOD`。
- **核验结论**：**100% PASSED**。

---

### 5. LOCK-VUE-05：Compiler Macros v1 显式受控范围
- **问题与挑战**：Vue 3 `<script setup>` 拥有特定的编译期宏（Compiler Macros）。如果不设定封闭范围，会发生规则泛化或误报。
- **实施动作**：
  严格限定 Compiler Macros v1 的 6 个核心宏与 1 个辅助宏：
  - 核心宏：`defineProps`, `defineEmits`, `defineExpose`, `defineOptions`, `defineModel`, `defineSlots`
  - 辅助宏：`withDefaults`
  结构化存入主组件 `metadata["macros"]` 与 `metadata["macro_helpers"]`。
- **实测验证**：
  `macros_and_bindings.vue` 中成功识别 `defineProps`, `defineEmits`, `defineExpose`, `defineOptions`, `defineModel`，并成功识别 `withDefaults` 为辅助宏。
- **核验结论**：**100% PASSED**。

---

### 6. LOCK-VUE-06：SfcBlockSlicer HTML 注释掩码与物理行号零漂移
- **问题与挑战**：若 Vue 文件的注释（如文件头部声明 `<!-- (<script> + <script setup>) -->`）中包含标签名，正则若无保护会将其误判为顶层区块，导致 AST 解析语法报错与坐标漂移。
- **实施动作**：
  在 [`core/parsing/sfc_block_slicer.py`](file:///C:/WorkSpace/lkio/core/parsing/sfc_block_slicer.py) 中，使用等长空格与换行符替换 HTML 注释内容 (`re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), ...)`）。
  - 字符串总长度保持绝对一致；
  - 每一个 `\n` 的索引与物理行号 100% 保留；
  - 彻底杜绝注释内伪区块匹配；
  - 内部代码内容仍从原始文本中准确截取。
- **实测验证**：
  `multi_script.vue` 头部携带注释标签，依然准确切分出第 9 行的 `<script>` 与第 18 行的 `<script setup>`，零语法报错，行号 100% 对齐。
- **核验结论**：**100% PASSED**。

---

## 二、多维度指标严格分层宣告

为遵循阶段度量纪律，本次终审报告严格拆分四套独立度量体系：

```text
1. 验收门禁 (Acceptance Gates)    : 16 项 (Gate A ~ P 全部通过)
2. 黄金样本文件 (Gold Fixtures)     : 4 个 (basic_setup.vue, options_api.vue, multi_script.vue, macros_and_bindings.vue)
3. 阶段测试套件 (Test Suites)      : 5 个测试函数 (tests/unit/b05/test_vue_extractor_b05.py)
4. 细粒度断言用例 (Assertion Cases) : 38 项 (覆盖 Synthetic Provenance、模板事实、样式、宏、双Script作用域、Hook识别、确定性Key等)
```

---

## 三、16 项 Acceptance Gates (Gate A ~ P) 细目核验

| Gate 代号 | 准入要求与设计规格 | 实施动作与工程证据 | 检验结论 |
|---|---|---|---|
| **Gate A** | **File Recognition & Routing** | Orchestrator 准确将 `.vue` 文件分发至 `VueExtractor`，支持 `code_bytes` 与 UTF-8 容错解码。 | **PASSED** |
| **Gate B** | **Component Classification** | 提取的主组件符号类型为 `COMPONENT`，`base_symbol_type="VARIABLE"`，分类算法为 `vue_sfc_rule_v1`。 | **PASSED** |
| **Gate C** | **Script Setup Extractor** | 直接复用冻结的 B-03 `TypeScriptExtractor`，完全提取 `<script setup>` 内声明的变量、函数、类、接口。 | **PASSED** |
| **Gate D** | **Dual Script Blocks Isolation** | 支持一个 SFC 内共存 `<script>` 与 `<script setup>`，双方符号分别隔离提取。 | **PASSED** |
| **Gate E** | **Options API Structural Facts** | Options API 的 `data/computed/methods/watch/props/emits` 结构化存入 `metadata["options_api"]`，不伪造顶层 `METHOD`。 | **PASSED** |
| **Gate F** | **Block Scope Delimiter** | 严格遵循 B-02 Criterion 5 规范：普通脚本块符号前缀为 `script::`，Setup 块符号前缀为 `script_setup::`。 | **PASSED** |
| **Gate G** | **Hook Recognition inside Vue** | 脚本块内以 `use` 开头的函数成功分类为 `HOOK`，`base_symbol_type="FUNCTION"`，算法为 `name_prefix_rule_v1`。 | **PASSED** |
| **Gate H** | **Template Structural Facts** | 结构化提取 `component_references`，支持 PascalCase 规范化与原始 Tag，记录 `evidence.method="static_template"`。 | **PASSED** |
| **Gate I** | **Directive & Event Bindings** | 结构化提取事件与属性绑定（保留 directive, event, argument, expression, modifiers），坚决不提前字符串伪造。 | **PASSED** |
| **Gate J** | **Style Block Metadata** | 提取 `<style>` 区块的 `scoped`、`lang`、行号范围，记录 `evidence.method="static_sfc_metadata"`。 | **PASSED** |
| **Gate K** | **Compiler Macros v1** | 显式识别 Vue 3 核心编译期宏（`defineProps`, `defineEmits`, `defineExpose`, `defineOptions`, `defineModel`, `defineSlots`）与 `withDefaults`。 | **PASSED** |
| **Gate L** | **Zero Premature Graph** | 严格禁止构建 CALLS / IMPORTS / EXTENDS / IMPLEMENTS 等图谱边，输出严格限制为 `SymbolCandidate` DTO。 | **PASSED** |
| **Gate M** | **Source Project Strict Read-Only** | 真实项目（`HELLO_FE`, `HELLO_BE`, `L2C_FE`）在全量扫描前后 `git status --porcelain` 严格不变，0 字节改动。 | **PASSED** |
| **Gate N** | **Physical Line Number Accuracy** | 采用行号对齐填充技术，AST 节点提取的行号与 `.vue` 源文件行号 100% 绝对一致（0 漂移）。 | **PASSED** |
| **Gate O** | **Deterministic Key Invariance** | 提取的全部符号均通过 B-02 确定性 Key 计算，5 大不变量（行漂移、词法作用域、重载、可选参数、Vue 脚本块）全部闭环。 | **PASSED** |
| **Gate P** | **Gold Set 100% PASS** | 4 大 Vue 金标准用例全部全绿，测试耗时 0.04 秒（远优于 `< 5s` 门禁）。 | **PASSED** |

---

## 四、测试证据隔离呈现 (严格执行测试汇报纪律)

### 1. 本阶段核心准入证据 (B-05 Primary Acceptance)
严格执行阶段隔离，绝不以全量或混杂测试数伪造本阶段验收结论：

```powershell
$ uv run pytest tests/unit/b05 -q
.....                                                                    [100%]
5 passed in 0.04s
```

详细用例清单（100% PASSED，耗时 0.05 秒）：
- `test_gold_vue_basic_setup`: PASSED
- `test_gold_vue_options_api`: PASSED
- `test_gold_vue_multi_script`: PASSED
- `test_gold_vue_macros_and_bindings`: PASSED
- `test_vue_deterministic_key_integrity`: PASSED

---

### 2. 历史阶段独立回归证据 (Historical Regression Suites - Separately Reported)
各历史阶段均保持独立目录并可单独执行全绿：

| 回归套件路径 | 对应阶段 | 测试命令 | 执行结果 | 执行耗时 |
|---|---|---|---|---|
| `tests/unit/b00_b02` | B-00 ~ B-02 (Schema, Migration, Key) | `uv run pytest tests/unit/b00_b02 -q` | **13 passed** | 0.03s |
| `tests/unit/b03` | B-03 (TS/JS/TSX/JSX Extractor) | `uv run pytest tests/unit/b03 -q` | **7 passed** | 0.04s |
| `tests/unit/b04` | B-04 (Java Extractor) | `uv run pytest tests/unit/b04 -q` | **5 passed** | 0.03s |
| `tests/unit/b05` | B-05 (Vue Extractor) | `uv run pytest tests/unit/b05 -q` | **5 passed** | 0.04s |
| `tests/unit/unreleased_stubs` | 历史桩兼容套件 (AUDIT-01) | `uv run pytest tests/unit/unreleased_stubs -q` | **5 passed** | 0.03s |
| `tests/preflight/test_vue_coordinates.py` | MVP2-A 8组坐标金标准 | `uv run pytest tests/preflight/test_vue_coordinates.py -q` | **8 passed** | 0.35s |
| `tests/preflight/test_real_projects_smoke.py` | MVP2-A 真实工程 Smoke | `uv run pytest tests/preflight/test_real_projects_smoke.py -q` | **4 passed** | 0.46s |
| `tests/integration/test_real_projects_symbols_smoke.py` | MVP2-B 跨工程只读 Smoke | `uv run pytest tests/integration/test_real_projects_symbols_smoke.py -q` | **4 passed** | 0.77s |

---

## 五、三大外部源项目 100% 物理只读核验

执行跨工程符号提取后，三大源码仓库的 Git 状态严格保持不变：

```powershell
$ git -C "C:\WorkSpace\hello" status --porcelain
(与扫描前完全一致，0 新增改动，0 临时文件污染)

$ git -C "C:\WorkSpace\hello-backend" status --porcelain
(与扫描前完全一致，0 新增改动，0 临时文件污染)

$ git -C "C:\WorkSpace\L2C project" status --porcelain
(与扫描前完全一致，0 新增改动，0 临时文件污染)
```
并在 `tests/integration/test_real_projects_symbols_smoke.py::test_source_repositories_strict_readonly_after_symbols` 自动化用例中完成了执行前与执行后的精确比对（**PASSED**）。

---

## 六、阶段交付物清单 (Artifacts)

```text
lkio/
├── core/
│   ├── parsing/
│   │   ├── sfc_block_slicer.py        # [Enhanced] HTML 注释等长掩码，杜绝注释内标签误判
│   │   └── template_parser.py         # [New] Vue 模板结构化解析器，提取标签与指令绑定
│   └── extraction/
│       └── vue.py                     # [Enhanced] Vue 抽取器，集成 6 大专项锁与 B-03 抽取器
├── tests/
│   ├── gold/mvp2/symbols/vue/
│   │   ├── basic_setup.vue            # [New] Setup + TS + Hook + Template + Scoped CSS
│   │   ├── options_api.vue            # [New] Options API (methods, computed, data)
│   │   ├── multi_script.vue           # [New] 双 Script 块隔离与作用域核验
│   │   └── macros_and_bindings.vue    # [New] Compiler Macros v1 与结构化指令绑定
│   ├── unit/
│   │   ├── b05/
│   │   │   └── test_vue_extractor_b05.py  # [New] B-05 独立专属单元测试套件 (5 项全部通过)
│   │   └── unreleased_stubs/
│   │       └── test_unreleased_stubs.py   # [Updated] 对齐 B-02/B-05 冻结的 vue_sfc_rule_v1 规范
│   └── integration/
│       └── test_real_projects_symbols_smoke.py # [Verified] 真实项目扫描与只读验证
└── docs/mvp2/
    ├── mvp2_step5_b05_vue_extractor_plan.md   # [Committed] B-05 实施规划文档
    ├── mvp2_step5_b05_vue_extractor_report.md # [Current] B-05 终审结项报告
    └── MVP2_STATUS.md                         # [Updated] 里程碑状态追踪表
```

---

## 七、结项结论与后续规划

根据既定实施纪律：
1. **B-05 6 大专项锁、16 项门禁、4 个金标准样本、5 项专属单元测试、三大真实工程 Smoke 测试及只读验证全部闭环**。
2. 标志着 **LKIO MVP2-B 核心代码语言符号抽取器（TS/JS/TSX/JSX、Java、Vue SFC）全部研发完成并达到冻结标准**。
3. 当前状态正式推进为：
   - **B-05: COMPLETED / FROZEN**
   - **B-06: READY_TO_PLAN**（Orchestrator 跨语言统一调度与容错整合，或根据全局路线进入 Symbol Persistence / MVP2-C）。
