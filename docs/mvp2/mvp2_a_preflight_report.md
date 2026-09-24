# LKIO MVP2-A Preflight 终审准入报告 — Tree-sitter & Vue SFC 坐标金标准

> **执行周期**: MVP2 (Code Intelligence & Structural Graph) ➔ **子阶段 MVP2-A**  
> **状态**: **COMPLETED / FROZEN**  
> **前置阶段状态**:  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> **后续子阶段状态**: **MVP2-B = READY_TO_PLAN** (MVP2-C/D/E 保持 LOCKED)  
> **前序文档检验**: [mvp2_step0_planning_and_baseline.md](file:///C:/WorkSpace/lkio/docs/mvp2/mvp2_step0_planning_and_baseline.md)  
> **实施基线**: [MVP2实施基线LKIO — Code Intelligence & Structural Graph.md](file:///C:/WorkSpace/lkio/docs/mvp/MVP2实施基线LKIO%20—%20Code%20Intelligence%20&%20Structural%20Graph.md)

---

## 🛑 永久冻结的 6 大核心架构红线审查

| 红线编号 | 条款定义 | 审查结论 | 验证与实测依据 |
| :---: | :--- | :---: | :--- |
| **1** | **三个源项目只读** | **100% 遵从** | `test_real_projects_smoke.py::test_source_repos_strict_readonly` 机械核验三大仓库在多文件解析后 `git status --porcelain` 差异严格为 0。 |
| **2** | **严禁解析 .git 内部结构** | **100% 遵从** | 零对 `.git` 内部二进制对象的直接反序列化。 |
| **3** | **Git 一律通过 subprocess 调用 Git CLI** | **100% 遵从** | 统一由 `GitClient` 执行标准命令。 |
| **4** | **敏感文件永不进入 Knowledge Core** | **100% 遵从** | 保持物理阻断机制。 |
| **5** | **严禁伪置信度** | **100% 遵从** | 明确将 `call_site` (1.0 语法事实)、`calls` (1.0 静态确定目标) 与 `unresolved_call` (1.0 未确定目标) 区分，严禁虚构 0.7 置信度。 |
| **6** | **AST 是结构事实，不是业务推理** | **100% 遵从** | MVP2-A 仅提取客观 AST 与 SFC 块，0 处业务语义猜测。 |

---

## 🔒 3 条 Preflight 实施锁达标核验

### Lock 8: Grammar ABI 自动验收
- **要求**：不能只测 import，必须实际执行 `Language(grammar.language())` ➔ `Parser(language)` ➔ `parse(...)`，TS/TSX/JS/JSX/Java 全部通过 ABI 兼容检查。
- **验证**：[`tests/preflight/test_language_matrix.py`](file:///C:/WorkSpace/lkio/tests/preflight/test_language_matrix.py) 5 项独立语法测试全数通过，无 `ValueError: Incompatible Language version`，验证通过。

### Lock 9: Preflight 五大语法矩阵测试 (TS / TSX / JS / JSX / Java)
- **要求**：分别验证 TS, TSX (`language_tsx`), JS, JSX, Java 5 类语法解析。
- **验证**：在 `tests/gold/mvp2/preflight/` 中固化了 5 类最小语法基线样本（`sample.ts`, `sample.tsx`, `sample.js`, `sample.jsx`, `sample.java`），AST 根节点均为 `program` 且 `has_error == False`，全量测试通过。

### Lock 10: Vue SFC “坐标金标准”
- **要求**：建立包含 8 个经典 `.vue` 文件的黄金测试集，断言原 `.vue` 真实行号与解析后 AST 节点行号严格 100% 吻合。
- **验证**：在 [`tests/gold/mvp2/preflight/vue_coordinates/`](file:///C:/WorkSpace/lkio/tests/gold/mvp2/preflight/vue_coordinates/) 固化了 8 个测试用例：
  1. `01-options-api.vue`：验证 `methods.loadUser()` 位于原文件第 16 行；
  2. `02-script-setup.vue`：验证 `function increment()` 位于原文件第 11 行；
  3. `03-script-ts.vue`：验证 `interface Props` 位于第 8 行，`function getTitleLength()` 位于第 18 行；
  4. `04-script-js.vue`：验证 `export default` 位于第 6 行；
  5. `05-multi-block.vue`：验证 `<script>` 与 `<script setup>` 双块共存时 `function toggle()` 位于第 16 行；
  6. `06-template-heavy.vue`：验证深层模板下 `<script setup>` 打开于第 20 行，`handlePageChange()` 位于第 24 行；
  7. `07-style-scoped.vue`：验证样式块 `scoped` 与 `scss` 属性提取；
  8. `08-empty-script.vue`：验证空脚本块边界处理。
  [`tests/preflight/test_vue_coordinates.py`](file:///C:/WorkSpace/lkio/tests/preflight/test_vue_coordinates.py) 8 项断言 100% 通过！

---

## 📦 MVP2-A 冻结产物清单

根据规范要求，MVP2-A 严格产出并锁定以下独立构件：

```text
core/parsing/
  ├── models.py                     (LanguageType, SfcBlock, SfcParseResult 纯 DTO)
  ├── parser_factory.py             (单一职责：语言注册、Parser构建、线程本地缓存)
  └── sfc_block_slicer.py           (Vue SFC 块切片器，具备 100% 物理行号对齐)

tests/preflight/
  ├── test_parser_factory.py        (单例、线程安全、语言识别测试)
  ├── test_language_matrix.py       (Lock 8 & Lock 9 语法与 ABI 兼容测试)
  ├── test_vue_coordinates.py       (Lock 10 Vue 坐标金标准测试)
  └── test_real_projects_smoke.py   (三大源项目源码真实冒烟与只读测试)

tests/gold/mvp2/preflight/
  ├── sample.ts, sample.tsx, sample.js, sample.jsx, sample.java
  └── vue_coordinates/              (01 至 08 经典 .vue 样本集)

docs/mvp2/
  ├── mvp2_step0_planning_and_baseline.md
  ├── mvp2_step1_treesitter_infra.md
  ├── mvp2_a_preflight_report.md    (本报告)
  └── MVP2_STATUS.md

pyproject.toml & uv.lock            (tree-sitter==0.25.2 生产精确锁定)
```

---

## 🧪 自动化测试验证总汇 (43 项全绿)

运行全量测试套件 `uv run pytest`，耗时 556 秒，全量 43 项测试通过，0 项失败：

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\WorkSpace\lkio
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0
collected 43 items

tests\preflight\test_language_matrix.py .....                            [ 11%]
tests\preflight\test_parser_factory.py .....                             [ 23%]
tests\preflight\test_real_projects_smoke.py ....                         [ 32%]
tests\preflight\test_vue_coordinates.py ........                         [ 51%]
tests\test_api_v1.py .......                                             [ 67%]
tests\test_ingestion_api.py ...                                          [ 74%]
tests\test_mvp1_gold_regression.py ...                                   [ 81%]
tests\test_readonly_integrity.py ...                                     [ 88%]
tests\test_treesitter_preflight.py .....                                 [100%]

================== 43 passed, 1 warning in 556.06s (0:09:16) ==================
```

---

## 🔒 状态正式锁定与下阶段出口

根据实施基线约定，**MVP2-A 的唯一出口门禁（ParserFactory + TS/TSX/JS/JSX/Java + Vue SFC Slicer + Physical Line Mapping + 3 Projects Smoke Test + ABI Test + Readonly Test + Gold Preflight Set）已全部 100% PASS**。

当前正式状态切换为：

```text
MVP0   = COMPLETED / FROZEN
MVP1   = COMPLETED / FROZEN
MVP2   = IN_PROGRESS (PREFLIGHT_LOCKED, BASELINE_FROZEN)
  ├── MVP2-A (Tree-sitter Infra & Preflight)  ✅ COMPLETED / FROZEN
  ├── MVP2-B (Symbol Extraction)              🚀 READY_TO_PLAN
  ├── MVP2-C (Code Structural Graph)          🔒 LOCKED
  ├── MVP2-D (Cross-project Code Graph)       🔒 LOCKED
  └── MVP2-E (API to Backend Traceability)    🔒 LOCKED
```

**准入结论**：正式解封 **MVP2-B (Symbol Extraction 代码符号提取)**，下一步可按规范进行 Step 2.2 的详细规划与实施！
