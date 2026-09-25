# LKIO MVP2-B B-05 实施规划 — Vue SFC Symbol Extractor (Approved Baseline with 6 Boundary Patches)

> **阶段**：**MVP2-B (Step 2.2 — B-05: Vue SFC Symbol Extractor)**  
> **当前状态**：**READY_TO_IMPLEMENT (6 大边界锁补丁已固化，方案正式冻结)**  
> **前置阶段状态终审核查**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2-A = COMPLETED / FROZEN (SfcBlockSlicer & Vue SFC 坐标金标准闭环)**  
> - **B-00 (Schema 与边界锁) = COMPLETED / FROZEN**  
> - **B-01 (Database TEXT 迁移) = COMPLETED / FROZEN**  
> - **B-02 (符号身份与标准化体系) = COMPLETED / FROZEN (Criterion 5 多 script 隔离闭环)**  
> - **B-03 (TypeScript/JavaScript Extractor) = COMPLETED / FROZEN (16 门禁全绿，测试物理隔离)**  
> - **B-04 (Java Extractor) = COMPLETED / FROZEN (4 专项锁闭环，16 门禁全绿)**  
> - **B-05 (Vue Extractor) = READY_TO_IMPLEMENT (本方案)**  
> - **B-06..B-10 = LOCKED (物理冻结)**  
> **执行约束**：仅实现 Vue SFC 结构化切块与符号提取，输出 `SymbolCandidate` DTO；严禁触碰图谱关系 (B-06/MVP2-C)、Spring API Trace (MVP2-E) 或 DB 持久化。

---

## 一、对照前置阶段与测试报告纪律审查

在启动 B-05 实现前，严格落实测试与报告纪律：

### 1. 终审验收证据报告规范升级 (测试纪律锁定)
为杜绝用全量测试总数混淆阶段验收证据，B-05 终审报告证据必须分层陈述：
- **主要阶段验收证据**：必须且仅优先引用当前阶段独立隔离测试：
  ```bash
  uv run pytest tests/unit/b05 -q
  ```
- **历史回归测试独立陈述**：
  - `B-00/B-02 Regression` (`tests/unit/b00_b02`)
  - `B-03 Regression` (`tests/unit/b03`)
  - `B-04 Regression` (`tests/unit/b04`)
  - `Real Projects Smoke` (`tests/integration/test_real_projects_symbols_smoke.py`)

### 2. 前置资产完全就绪核验
- **MVP2-A 资产**：`core.parsing.sfc_block_slicer.SfcBlockSlicer` 已实现并已通过 Vue SFC 物理行号保真金标准（换行填充确保 100% 对齐）。
- **B-02 资产**：`normalizer.build_qualified_name(..., block_scope="script" | "script_setup")` 已通过 Criterion 5 单测验证。
- **B-03 资产**：`core.extraction.typescript.TypeScriptExtractor` 已完全稳定冻结，支持 TS/JS 全系符号提取与无类型保真。

---

## 二、B-05 核心流水线与架构复用原则

```text
.vue 源码
  │
  ▼
SfcBlockSlicer (preserve_physical_lines=True 保证换行填充物理坐标零漂移)
  │
  ├──────────────────────────────┐
  │                              │
  ▼                              ▼
普通 <script>              <script setup>
  │                              │
  ▼                              ▼
已有 B-03 TS/JS 提取器     已有 B-03 TS/JS 提取器
  │                              │
  └──────────────┬───────────────┘
                 ▼
         Block Scope 修饰
          (script::foo vs script_setup::foo)
                 │
                 ▼
          Vue Classifier
                 │
  ┌──────────────┼──────────────────────────────┐
  ▼              ▼                              ▼
Compiler Macros   Template 结构事实           Options API 结构事实
(metadata)       (组件引用/事件/属性)           (metadata)
  │              │                              │
  └──────────────┼──────────────────────────────┘
                 ▼
      Synthetic Component Context
      (name=Stem, QName=Stem, COMPONENT, synthetic=True, source_kind=vue_sfc_file_context)
                 │
                 ▼
      SymbolCandidate DTO 列表
```

---

## 三、6 大 Vue 关键架构边界锁补丁 (Lock Patches)

### LOCK-VUE-01: Synthetic Component 必须与 AST Native Symbol 物理区分
- **问题与挑战**：Vue SFC 文件（如 `LeadList.vue`）的主组件符号并不是 Tree-sitter AST 中的原生节点，而是 LKIO 构建出的组件上下文实体。若混入 `extraction_method = "static_ast"`，会导致 Provenance 链条失真。
- **实施规范**：
  主组件符号必须显式标注合成属性与 SFC 上下文来源：
  ```json
  {
    "symbol_type": "COMPONENT",
    "base_symbol_type": "VARIABLE",
    "classification_method": "vue_sfc_rule_v1",
    "metadata": {
      "synthetic": true,
      "source_kind": "vue_sfc_file_context",
      "component_context": true,
      "extraction_method": "sfc_structure",
      "confidence": 1.0,
      "evidence": {
        "method": "sfc_structure",
        "file": "LeadList.vue",
        "file_stem": "LeadList"
      }
    }
  }
  ```
  - AST 原生提取符号：`extraction_method = "static_ast"`
  - SFC 主组件符号：`extraction_method = "sfc_structure"`
  - 两者均 `confidence = 1.0`，但来源清晰可审计。

### LOCK-VUE-02: Template 证据体系独立于 JS AST
- **实施规范**：
  明确三类独立的证据方法标识：
  1. TS/JS 语法树提取：`extraction_method = "static_ast"`
  2. Template 结构提取：`extraction_method = "static_template"`
  3. Style 元数据提取：`extraction_method = "static_sfc_metadata"`
  在 `metadata["template"]["component_references"]` 中保留明确的模板证据节点，避免后续 MVP2-C 将模板组件引用误判为 JS 调用。

### LOCK-VUE-03: Template Binding 保留原始结构，严禁提前序列化
- **问题与挑战**：严禁将 `@click="handleQuery"` 或 `@click="handleQuery(id)"` 序列化为 `"click->handleQuery"`（过早推测函数调用）。
- **实施规范**：
  保存原始结构事实：
  - **事件绑定**：
    ```json
    {
      "directive": "on",
      "event": "click",
      "expression": "handleQuery",
      "modifiers": [],
      "start_line": 12,
      "start_column": 8
    }
    ```
  - **属性绑定**：
    ```json
    {
      "directive": "bind",
      "argument": "model",
      "expression": "form",
      "modifiers": []
    }
    ```
  - **v-model**：
    ```json
    {
      "directive": "model",
      "argument": null,
      "expression": "queryParams.userName",
      "modifiers": ["trim"]
    }
    ```
  - 组件标签同时保留原始标签与 PascalCase 归一化名：
    `{"tag_name": "el-button", "normalized_name": "ElButton"}`
    `{"tag_name": "LeadDetail", "normalized_name": "LeadDetail"}`
    `{"tag_name": "router-view", "normalized_name": "RouterView"}`

### LOCK-VUE-04: Options API 独立作为元数据，严禁破坏 B-03
- **问题与挑战**：B-03 规定对象字面量方法不作为 `METHOD` 符号。Vue Options API 采用 `export default { data() {}, methods: {} }`，严禁偷偷在 B-03 中把 Options API 方法提升为原生 METHOD 实体。
- **实施规范**：
  建立 Vue 专用结构事实存入主组件元数据，**不生成独立 Symbol 实体**：
  ```json
  {
    "options_api": {
      "data": [],
      "computed": [],
      "methods": [
        { "name": "loadData", "start_line": 12, "end_line": 18 }
      ],
      "watch": [],
      "props": [],
      "emits": [],
      "components": [],
      "directives": []
    }
  }
  ```
  等待未来 MVP2-C 再统一决定是否建立图谱。

### LOCK-VUE-05: Vue 编译器宏集合扩充 (Compiler Macros v1)
- **支持集合**：
  - `defineProps`
  - `defineEmits`
  - `defineExpose`
  - `defineOptions`
  - `defineModel` (Vue 3.4+)
  - `defineSlots` (Vue 3.3+)
- **辅助函数分离**：
  `withDefaults` 归入 `metadata["macro_helpers"]`，不与编译器宏混淆。
- **实体隔离**：宏调用绝对不生成独立 Symbol。

### LOCK-VUE-06: Template Parser 不得仅依赖简单正则 & 前置 Strategy Preflight
- **问题与挑战**：Vue Template 允许复杂三元表达式、多重指令、修饰符与自闭合标签，简单正则极易崩溃或提取残缺。
- **实施规范**：
  1. 增加 `B-05-00 Template Parser Preflight` 步骤，实现健壮的词法解析机制。
  2. 支持标准 HTML/Template，针对 `<template lang="pug">` 等预处理器，标注 `metadata.template.unsupported_language = "pug"` 并跳过，不做主观猜测。

---

## 四、词法作用域与双 Script 块隔离 (B-02 Criterion 5 精确对齐)

Vue 官方规定一个 SFC 最多一个普通 `<script>` 和一个 `<script setup>`。
符号命名规范严格保持干净：
- 主组件自己：`LeadList`（无前缀）
- 普通 `<script>` 内顶层声明：`script::foo`（不人为硬塞组件名）
- `<script setup>` 内顶层声明：`script_setup::foo`
- 内部作用域嵌套遵循已有链条：`script_setup::outer::inner`
- 完美契合 B-02 Criterion 5 判据，零 Key 冲突。

---

## 五、16 项 Acceptance Gates (Gate A ~ P for B-05 Vue)

- **Gate A: Vue SFC Slicing Integration**: 结构化切分 template、script、script_setup、style 各块。
- **Gate B: Synthetic Component Context**: 生成主 `COMPONENT` 符号，标记 `synthetic=True`, `source_kind="vue_sfc_file_context"`, `extraction_method="sfc_structure"` (LOCK-VUE-01)。
- **Gate C: Script Setup TS Parsing**: `<script setup lang="ts">` 声明复用 B-03 提取 TS 类型、函数、变量、接口。
- **Gate D: Script Setup JS Parsing**: `<script setup>` (JS) 声明复用 B-03 提取，无类型参数真实标记为 `?`。
- **Gate E: Options API Structural Metadata**: 普通 `<script>` Options API 提取为专用结构事实，不篡改 B-03 (LOCK-VUE-04)。
- **Gate F: Script + Script Setup Scope Isolation**: 双块共存时，符号严格通过 `script::` 与 `script_setup::` 作用域隔离，Key 绝对不重。
- **Gate G: Hook Classification in Vue**: 内部符合 `^use[A-Z0-9].*` 的声明正确分类为 `HOOK` (`name_prefix_rule_v1`)。
- **Gate H: Template Component References**: 提取组件引用，同时保留 `tag_name` 与 `normalized_name` (LOCK-VUE-03)。
- **Gate I: Template Structured Bindings**: 提取 `@event`, `:prop`, `v-model` 结构化对象（包含 directive, argument, expression, modifiers），拒绝字符串拼接 (LOCK-VUE-03)。
- **Gate J: Style Metadata Extraction**: 准确记录 style 块的 `scoped`, `lang`, `start_line`, `end_line`，不解析 CSS AST。
- **Gate K: Vue Macros v1 Metadata**: `defineProps`, `defineEmits`, `defineExpose`, `defineOptions`, `defineModel`, `defineSlots` 进入元数据，不造假符号 (LOCK-VUE-05)。
- **Gate L: Scope & Qualified Name Consistency**: 统一使用 `::` 词法连接符，严格遵循 `build_qualified_name`。
- **Gate M: Deterministic Symbol Key**: 所有符号统一调用 `build_symbol_key`，0 行号依赖，TEXT 全长支持。
- **Gate N: Physical Coordinate Integrity**: 利用换行填充确保行号与原始 `.vue` 物理行号 0 误差。
- **Gate O: Fault Tolerance & Evidence Taxonomy**: 独立标识 `static_ast`, `static_template`, `static_sfc_metadata`, `sfc_structure` (LOCK-VUE-02)。
- **Gate P: Gold Set 100% PASS**: 4 组 Vue 金标准用例全部全绿，独立测试套件耗时 < 5 秒。

---

## 六、Gold Standard 数据集规划 (4 大测试场景)

在 `tests/gold/mvp2/symbols/vue/` 下建立：

### 1. `tests/gold/mvp2/symbols/vue/basic_setup.vue`
- Vue 3 `<script setup lang="ts">`
- 响应式变量、内部 Hook (`export function useLeadState()`)、普通函数
- `<template>` 包含 `<ElButton @click="handleRefresh">`、`<h1>{{ title }}</h1>`
- `<style scoped lang="scss">`

### 2. `tests/gold/mvp2/symbols/vue/options_api.vue`
- Options API (`<script lang="ts">`)
- `export default defineComponent({ name: "UserOptions", data() {}, computed: {}, methods: { loadData() {} } })`
- 验证 Options API 结构元数据完整抽取，且不产生伪造的 METHOD 实体。

### 3. `tests/gold/mvp2/symbols/vue/multi_script.vue`
- 同时拥有 `<script>` 与 `<script setup lang="ts">`
- `<script>` 声明 `const initConfig = { timeout: 3000 };`
- `<script setup>` 声明 `const initConfig = ref({ timeout: 5000 });`
- 验证两者 QName 分别为 `script::initConfig` 与 `script_setup::initConfig`。

### 4. `tests/gold/mvp2/symbols/vue/macros_and_bindings.vue`
- 覆盖 `defineProps<Props>()`, `defineEmits()`, `defineExpose()`, `defineModel()`, `defineOptions()`
- 模板绑定：`<el-input v-model.trim="form.name" :disabled="form.status === 1" @change="handleChange(row)" />`
- 验证结构化指令对象（directive, argument, expression, modifiers）。

---

## 七、实施路线图 (B-05-00 ~ B-05-11)

```text
B-05-00: Template Parser 词法与结构化解析器预检实现 (LOCK-VUE-03, LOCK-VUE-06)
   ↓
B-05-01: SFC Block / 物理换行填充坐标对齐复核
   ↓
B-05-02: Synthetic Component 上下文生成与证据体系隔离 (LOCK-VUE-01, LOCK-VUE-02)
   ↓
B-05-03: <script setup lang="ts"> ➔ 复用 B-03 提取
   ↓
B-05-04: <script setup> (JS) ➔ 复用 B-03 提取与无类型事实保真
   ↓
B-05-05: Options API 结构元数据提取 (LOCK-VUE-04)
   ↓
B-05-06: 块作用域修饰 (script:: vs script_setup::)
   ↓
B-05-07: Vue Compiler Macros v1 集合抽取 (LOCK-VUE-05)
   ↓
B-05-08: Template 结构事实 (raw tag + normalized, 结构化绑定) 抽取
   ↓
B-05-09: 4 大 Vue 金标准文件创建与 tests/unit/b05/ 独立断言编写
   ↓
B-05-10: HELLO_FE 与 L2C_FE 真实工程全量 Smoke Test
   ↓
B-05-11: 16 项 Acceptance Gates 终审验收与结项归档
```

---

## 八、结论与当前就绪状态

本规划已将 6 大边界锁补丁与测试纪律完全固化：
- `LOCK-VUE-01`: Synthetic Component 与 AST Native 区分
- `LOCK-VUE-02`: Template Evidence 独立
- `LOCK-VUE-03`: Template 结构化绑定与 raw/normalized tag
- `LOCK-VUE-04`: Options API 独立元数据（不改 B-03）
- `LOCK-VUE-05`: Compiler Macros v1 完整集合
- `LOCK-VUE-06`: Template Parser Preflight 与 Pug 降级保护

**当前状态**：**READY_TO_IMPLEMENT**。规划审查通过，立即进入代码与测试落地。
