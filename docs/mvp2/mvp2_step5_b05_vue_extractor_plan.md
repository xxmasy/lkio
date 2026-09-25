# LKIO MVP2-B B-05 实施规划 — Vue SFC Symbol Extractor

> **阶段**：**MVP2-B (Step 2.2 — B-05: Vue SFC Symbol Extractor)**  
> **当前状态**：**READY_TO_PLAN (规划方案冻结阶段，严禁直接编写提取代码)**  
> **前置阶段状态终审核查**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2-A = COMPLETED / FROZEN (SfcBlockSlicer & Vue SFC 坐标金标准闭环)**  
> - **B-00 (Schema 与边界锁) = COMPLETED / FROZEN**  
> - **B-01 (Database TEXT 迁移) = COMPLETED / FROZEN**  
> - **B-02 (符号身份与标准化体系) = COMPLETED / FROZEN (Criterion 5 多 script 隔离闭环)**  
> - **B-03 (TypeScript/JavaScript Extractor) = COMPLETED / FROZEN (16 门禁全绿，测试物理隔离)**  
> - **B-04 (Java Extractor) = COMPLETED / FROZEN (4 专项锁闭环，16 门禁全绿)**  
> - **B-05 (Vue Extractor) = READY_TO_PLAN (本规划)**  
> - **B-06..B-10 = LOCKED (物理冻结)**  
> **执行约束**：本阶段为纯规划阶段。严禁修改或编写生产提取代码，严禁触碰图谱关系 (B-06/MVP2-C)、Spring API Trace (MVP2-E) 或 DB 持久化。

---

## 一、对照前置阶段与测试报告纪律审查

在启动 B-05 规划前，先锁定测试与报告纪律升级项：

### 1. 终审验收证据报告规范升级 (测试纪律锁定)
为杜绝用全量测试总数混淆阶段验收证据，从 B-05 开始，所有终审报告证据必须分层陈述：
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
- **MVP2-A 资产**：`core.parsing.sfc_block_slicer.SfcBlockSlicer` 已实现并已通过 Vue SFC 物理行号保真金标准（行号对齐 100%）。
- **B-02 资产**：`normalizer.build_qualified_name(..., block_scope="script" | "script_setup")` 已通过 Criterion 5 单测验证。
- **B-03 资产**：`core.extraction.typescript.TypeScriptExtractor` 已完全稳定冻结，支持 TS/JS 全系符号提取与无类型保真。

---

## 二、B-05 核心目标与定位

### 1. 唯一使命
对 Vue Single File Components（`.vue` 文件）进行结构化切块并提取代码符号，输出 `list[SymbolCandidate]` DTO。

核心提取产物包含：
1. **组件主符号 (COMPONENT)**：`.vue` 文件自身作为组件上下文，生成 `symbol_type = "COMPONENT"`，`base_symbol_type = "VARIABLE"`，`classification_method = "vue_sfc_rule_v1"`。
2. **脚本声明符号**：递归复用已冻结的 **B-03 TypeScriptExtractor**，提取 `<script>` 与 `<script setup>` 内声明的 `FUNCTION`、`VARIABLE`、`HOOK`、`CLASS`、`TYPE`、`INTERFACE`。
3. **模板结构事实**：从 `<template>` 中提取组件引用（`component_references`）、事件绑定（`event_bindings`）与属性绑定（`property_bindings`），存入组件符号的元数据中。
4. **样式元数据**：记录 `<style>` 的 `scoped`、`lang`、物理起止行号，存入组件符号的元数据中。

### 2. 核心架构复用原则 (严禁发明第二套 TS/JS 提取器)
B-05 的本质是**调度与组合**，而非重造轮子：
```text
.vue 源码
   ↓
SfcBlockSlicer (preserve_physical_lines=True 保证换行填充物理坐标零漂移)
   ↓
script_blocks (<script> / <script setup>)
   ↓
已有 B-03 TypeScriptExtractor (解析 TS/JS 语法树)
   ↓
Vue 专项作用域修饰 (注入 block_scope: "script" vs "script_setup")
   ↓
附加组件元数据 (Template 结构事实 + Style 范围 + Macros 声明)
   ↓
SymbolCandidate DTO 列表
```

---

## 三、5 大 Vue 关键架构边界锁定 (Frozen Boundaries)

### Boundary 1: `.vue` 文件本身作为 Component Symbol Context
- **设计规范**：每个 `.vue` 单文件组件天然具备 `component_context = True`。
- **符号生成**：
  - `name = <file_stem>`（如 `LeadList`、`BizStatusTag`、`UserIndex`）
  - `qualified_name = <file_stem>`
  - `symbol_type = "COMPONENT"`
  - `base_symbol_type = "VARIABLE"`（严格限制在 9 大受控 Native 枚举）
  - `classification_method = "vue_sfc_rule_v1"`
  - `start_line = 1`, `end_line = total_lines`（覆盖整个 SFC 文件物理范围）
  - `metadata`:
    ```json
    {
      "component_context": true,
      "sfc_blocks": ["template", "script_setup", "style"],
      "template": {
        "components": ["ElButton", "ElTable"],
        "events": ["click->handleQuery"],
        "props": ["model->form"]
      },
      "styles": [
        { "lang": "scss", "scoped": true, "start_line": 40, "end_line": 65 }
      ],
      "macros": {
        "props": "Props",
        "emits": "Emits",
        "options": { "name": "LeadList" }
      }
    }
    ```

### Boundary 2: `<script>` 与 `<script setup>` 声明复用 B-03 与双重块作用域隔离
- **复用机制**：
  - 直接调用 `self.ts_extractor.extract(code_bytes=script_block.content.encode('utf-8'), language="typescript" | "javascript")`。
  - 由于 `SfcBlockSlicer` 采用 `\n` 填充前导行，B-03 产出的符号物理行号已完全对齐原始 `.vue` 文件，无需繁琐且易错的二次行号累加！
- **B-02 Criterion 5 块作用域强制隔离**：
  同一 `.vue` 文件中，若同时存在 `<script>` 和 `<script setup>`，且两块中均声明了同名符号（如 `initComponent`），必须通过 `block_scope` 物理隔离：
  - `<script>` 块内符号：`block_scope = "script"` ➔ QName: `script::CompName::symbol`（或 `script::symbol`）
  - `<script setup>` 块内符号：`block_scope = "script_setup"` ➔ QName: `script_setup::CompName::symbol`（或 `script_setup::symbol`）
  - 严格调用 `build_qualified_name(sym_name, scope_chain=[comp_name], block_scope=block.block_type)`，保证 Key 绝对互不碰撞。

### Boundary 3: `<template>` 第一阶段仅提取客观结构事实
- **边界纪律**：严禁在此阶段推断业务语义、组件职责或业务流程，仅提取 AST/正则客观事实：
  - **组件引用**：`<el-button>`, `<LeadDetail>`, `<RouterView>` ➔ 提取为 `component_references = ["ElButton", "LeadDetail", "RouterView"]`。
  - **事件绑定**：`@click="handleQuery"`, `v-on:submit="onSubmit"` ➔ 提取为 `event_bindings = ["click->handleQuery", "submit->onSubmit"]`。
  - **属性绑定**：`:model="form"`, `v-model="queryParams.userName"` ➔ 提取为 `property_bindings = ["model->form", "queryParams.userName"]`。
  - **插槽与文本**：第一阶段暂不提取复杂插槽表达式与纯文本内容，避免数据爆炸。

### Boundary 4: `<style>` 仅保留元数据
- **边界纪律**：**严禁引入 CSS/SCSS/LESS 的 Tree-sitter AST 解析**（严重超出 MVP2-B 范围）。
- **保留事实**：仅记录标签属性与物理区间：
  ```python
  {
      "lang": block.lang,       # "css", "scss", "less"
      "scoped": block.is_scoped, # bool
      "start_line": block.start_line,
      "end_line": block.end_line,
  }
  ```

### Boundary 5: Vue 宏 (Compiler Macros) 仅作为组件元数据
- **涉及宏**：`defineProps`, `defineEmits`, `defineExpose`, `defineOptions`, `withDefaults`。
- **边界纪律**：
  - 编译器宏在 Vue 3 中是编译期语法糖，运行时不存在独立函数实体。
  - **严禁将 `defineProps` 等宏提取为独立可调用的 `FUNCTION` 或 `METHOD` 符号**！
  - 提取其类型参数或参数描述，归入主组件符号的 `metadata["macros"]`。

---

## 四、16 项 Acceptance Gates (Gate A ~ P for B-05 Vue)

B-05 实施完成后必须 100% 满足以下 16 项准入门禁：

- **Gate A: Vue SFC Slicing Integration**: 适配 `.vue` 文件，通过 `SfcBlockSlicer` 正确分离 template、script、style 各块。
- **Gate B: Component Symbol Extraction**: 必须生成 SFC 顶层组件符号（`symbol_type=COMPONENT`, `base_symbol_type=VARIABLE`, `classification_method=vue_sfc_rule_v1`）。
- **Gate C: Script Setup TS Parsing**: `<script setup lang="ts">` 声明复用 B-03 正确提取 TS 类型、函数、变量、接口。
- **Gate D: Script Setup JS Parsing**: `<script setup>` (无 lang 或 lang="js") 声明复用 B-03 正确提取，无类型参数真实标记为 `?`。
- **Gate E: Plain Script (Options API)**: `<script>` (Options API 或通用导出) 正确提取顶层导出与成员。
- **Gate F: Multi-Script Block Isolation**: 同时包含 `<script>` 与 `<script setup>` 时，符号严格通过 `script::` 与 `script_setup::` 作用域隔离，Key 绝对不重。
- **Gate G: Hook Classification in Vue**: 内部符合 `^use[A-Z0-9].*` 的声明正确分类为 `HOOK` (`name_prefix_rule_v1`)，保留底层 `base_symbol_type`。
- **Gate H: Template Component References**: 正确提取模板中引用的自定义组件与 UI 组件标签（如 `ElButton`, `BizTag`）。
- **Gate I: Template Event & Prop Bindings**: 正确提取模板中的 `@click`, `v-model`, `:prop` 绑定至组件元数据。
- **Gate J: Style Metadata Extraction**: 准确记录所有 style 块的 `scoped`, `lang`, `start_line`, `end_line`，不碰 CSS AST。
- **Gate K: Vue Macros Metadata**: `defineProps`, `defineEmits`, `defineExpose` 结构化进入组件元数据，严禁生成独立 Symbol。
- **Gate L: Scope & Qualified Name Consistency**: 统一遵循 `::` 分隔符体系，严格匹配 `build_qualified_name`。
- **Gate M: Deterministic Symbol Key**: 所有符号统一调用 `build_symbol_key`，0 行号依赖，支持 TEXT 列全长无截断。
- **Gate N: Physical Coordinate Integrity**: 利用前导换行填充技术，确保提取出的所有符号行号与原始 `.vue` 文件的物理行号严格一致（误差为 0）。
- **Gate O: Fault Tolerance & AST Evidence**: 局部块语法异常安全捕获，全系符号携带置信度 1.0 与客观证据。
- **Gate P: Gold Set 100% PASS**: 4 组 Vue 金标准测试用例 100% 绿标通过，独立套件耗时 < 5 秒。

---

## 五、Gold Standard 数据集规划 (4 大测试场景)

在 `tests/gold/mvp2/symbols/vue/` 下创建 4 个专用金标准文件：

### 1. `tests/gold/mvp2/symbols/vue/basic_setup.vue`
- 覆盖场景：
  - 标准 Vue 3 `<script setup lang="ts">`
  - 声明 `title = ref("...")`, `loading = ref(false)`
  - 声明内部 Hook：`export function useLeadState() { ... }`
  - 声明方法：`function handleRefresh() { ... }`
  - `<template>` 包含 `<ElButton @click="handleRefresh">`、`<h1>{{ title }}</h1>`
  - `<style scoped lang="scss">`

### 2. `tests/gold/mvp2/symbols/vue/options_api.vue`
- 覆盖场景：
  - Vue 2 / Vue 3 Options API `<script lang="ts">`
  - `export default defineComponent({ name: "UserOptions", data() {}, methods: {} })`
  - 验证组件名称、Options 导出与内部方法的提取。

### 3. `tests/gold/mvp2/symbols/vue/multi_script.vue`
- 覆盖场景：
  - 同一组件同时拥有 `<script>` 与 `<script setup lang="ts">`
  - `<script>` 中声明 `const initConfig = { timeout: 3000 };`
  - `<script setup>` 中声明 `const initConfig = ref({ timeout: 5000 });`
  - 验证两者的 qualified_name 分别为：
    - `MultiScript::script::initConfig`
    - `MultiScript::script_setup::initConfig`
  - 彻底验证 B-02 Criterion 5 的隔离性。

### 4. `tests/gold/mvp2/symbols/vue/macros_and_bindings.vue`
- 覆盖场景：
  - 复杂编译期宏：
    - `interface Props { modelValue: string; disabled?: boolean; }`
    - `const props = withDefaults(defineProps<Props>(), { disabled: false });`
    - `const emit = defineEmits<{ (e: 'update:modelValue', val: string): void }>();`
    - `defineExpose({ reset: () => {} });`
  - 复杂模板绑定：
    - `<el-input v-model="props.modelValue" :disabled="props.disabled" @change="handleChange" />`
  - 验证宏不产生独立 Symbol，仅进入 metadata。

---

## 六、测试体系与独立隔离规划

落实测试报告纪律升级要求：

```text
tests/
├── unit/
│   ├── b00_b02/                          # 已冻结 (13 passed)
│   ├── b03/                              # 已冻结 (7 passed)
│   ├── b04/                              # 已冻结 (5 passed)
│   └── b05/                              # [本次规划] Vue 专用独立目录
│       └── test_vue_extractor_b05.py     # 覆盖 16 项 Gates 独立断言
└── gold/mvp2/symbols/vue/                # [本次规划] 4 大 Vue 金标准文件
    ├── basic_setup.vue
    ├── options_api.vue
    ├── multi_script.vue
    └── macros_and_bindings.vue
```

### 自动化验证指令规范
- **B-05 独立准入测试（核心依据）**：
  ```bash
  uv run pytest tests/unit/b05 -q
  ```
- **全量单元回归套件**：
  ```bash
  uv run pytest tests/unit/b00_b02 tests/unit/b03 tests/unit/b04 tests/unit/b05 -q
  ```
- **真实工程 Smoke Test（针对 `HELLO_FE` 与 `L2C_FE` 真实 `.vue` 文件）**：
  ```bash
  uv run pytest tests/integration/test_real_projects_symbols_smoke.py -k "vue or hello_fe or l2c_fe" -q
  ```

---

## 七、实施路线图 (B-05-01 ~ B-05-11)

```text
B-05-01: SfcBlockSlicer 物理行对齐机制复核与接口就绪
   ↓
B-05-02: COMPONENT 主符号生成与组件上下文标记 (Boundary 1)
   ↓
B-05-03: <script setup lang="ts"> 复用 B-03 提取 (Gate C)
   ↓
B-05-04: <script setup> (JS) 复用 B-03 提取与无类型事实保真 (Gate D)
   ↓
B-05-05: <script> (Options API / 库导出) 提取 (Gate E)
   ↓
B-05-06: 双 script 块作用域隔离机制实现 (Boundary 2, Gate F)
   ↓
B-05-07: Vue Compiler Macros 元数据抽取 (Boundary 5, Gate K)
   ↓
B-05-08: <template> 结构事实 (组件/事件/属性) 抽取 (Boundary 3, Gate H/I)
   ↓
B-05-09: 4 大 Vue 金标准数据集创建与 tests/unit/b05/ 独立断言编写
   ↓
B-05-10: HELLO_FE 与 L2C_FE 真实工程全量 Smoke Test (验证 0 污染只读性)
   ↓
B-05-11: 16 项 Acceptance Gates 终审验收与结项归档
```

---

## 八、结论与当前就绪状态

本规划已将用户指出的 Vue 核心边界完全冻结：
1. **复用 B-03**：坚决不编写第二套 TS/JS 解析系统。
2. **5 大边界锁定**：组件上下文、双 script 块作用域隔离、模板仅客观事实、样式仅元数据、宏不造假符号。
3. **测试报告纪律升级**：主要证据严格锁定单阶段 `tests/unit/b05`。

**当前状态**：`docs/mvp2/mvp2_step5_b05_vue_extractor_plan.md` 编制完成。进入 **READY_TO_PLAN** 等待用户审查，**绝不擅自编写提取代码**。
