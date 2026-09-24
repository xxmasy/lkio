# LKIO MVP2 - Step 2.1: Tree-sitter 基础设施与 Vue SFC 切片器实施检验报告 (MVP2-A Preflight)

> **执行周期**: MVP2 (Code Intelligence & Structural Graph)  
> **状态**: COMPLETED  
> **前序文档检验**: [mvp2_step0_planning_and_baseline.md](file:///C:/WorkSpace/lkio/docs/mvp2/mvp2_step0_planning_and_baseline.md)  
> **当前活动 MVP**: MVP2 (唯一活动中，严禁进入 MVP3)  
> **实施基线**: [MVP2实施基线LKIO — Code Intelligence & Structural Graph.md](file:///C:/WorkSpace/lkio/docs/mvp/MVP2实施基线LKIO%20—%20Code%20Intelligence%20&%20Structural%20Graph.md)  
> **六条冻结红线恪守审查**:
> 1. 三个源项目只读：100% 遵守 (`test_readonly_integrity_preflight` 验证扫描前后 git status 零变动)
> 2. 严禁解析 .git 内部结构：100% 遵守
> 3. Git 一律通过 subprocess 调用 Git CLI：100% 遵守
> 4. 敏感文件永不进入 Knowledge Core：100% 遵守
> 5. 严禁伪置信度：100% 遵守
> 6. AST 是结构事实，不是业务推理：100% 遵守 (仅输出客观语法树节点与切片块，无任何 LLM 猜测)

---

## 1. 对照上一轮 (Step 2.0) 规划检验

在 Step 2.0 规划报告中确定的 Step 2.1 (MVP2-A Preflight) 核心任务如下：
1. **Tree-sitter 生产依赖精确锁定**:
   - 锁定官方预编译 wheels：`tree-sitter==0.25.2`, `tree-sitter-javascript==0.25.0`, `tree-sitter-typescript==0.23.2`, `tree-sitter-java==0.23.5`。
   - 固化 `uv.lock`。
2. **构建解析层与持久层解耦的数据传输对象 (`ingestion/code/dto.py`)**:
   - 定义 `SymbolCandidate`, `CallSiteCandidate`, `RelationCandidate`, `SfcBlock`, `SfcParseResult`。
   - 符号实体解耦存储原生事实 (`base_symbol_type`) 与分类规约 (`classification_method`)。
3. **实现解析器抽象工厂 (`ingestion/code/parsers/factory.py`)**:
   - 统一初始化并管理 TS, TSX, JS, Java 语法树解析器，提供线程安全实例与多维缓存版本签名。
4. **实现 Vue SFC 切片提取器 (`ingestion/code/parsers/vue_sfc.py`)**:
   - 采用纯 Python 切片器提取 `<template>`, `<script>`, `<style>`，不绑定社区 Vue grammar；
   - 采用等量换行前置填充策略，确保提取出的脚本 AST 节点物理行号与 `.vue` 源文件 100% 绝对对齐。
5. **自动化 Preflight 测试与真实项目冒烟验证**:
   - 建立 `tests/test_treesitter_preflight.py`，全量执行通过。

---

## 2. 实施细节与成果

### 2.1 依赖安装与锁版
在 `pyproject.toml` 与 `uv.lock` 中精确锁定：
```toml
tree-sitter = "0.25.2"
tree-sitter-javascript = "0.25.0"
tree-sitter-typescript = "0.23.2"
tree-sitter-java = "0.23.5"
```
跨平台 0 编译依赖，在 Windows 11 环境下秒级安装成功。

### 2.2 解耦 DTO 架构 (`ingestion/code/dto.py`)
- `SymbolCandidate`: 包含物理行号 (`start_line`, `end_line`)、物理列号 (`start_column`, `end_column`)、代码签名 (`signature`)、`base_symbol_type` (如 FUNCTION) 与 `classification_method` (如 name_prefix_rule)。
- `CallSiteCandidate`: 记录调用点物理位置与接收者。
- `RelationCandidate`: 记录 `defines`, `imports`, `calls`, `unresolved_call` 等关系候选。
- `Parser` 模块绝不直接导入或依赖 SQLAlchemy 数据库 Model，完全保持纯函数与 DTO 流水线。

### 2.3 解析器工厂 (`ingestion/code/parsers/factory.py`)
- 使用现代 py-tree-sitter API `Language(grammar.language())` 与 `Parser(language)` 初始化；
- 支持根据扩展名自动路由到 `TYPESCRIPT`, `TSX`, `JAVASCRIPT`, `JAVA`, `VUE`；
- 输出确定性版本指纹 `PARSER_BUNDLE_VERSION`。

### 2.4 Vue SFC 块切片器 (`ingestion/code/parsers/vue_sfc.py`)
- 正则提取顶层 `<template>`, `<script>`, `<script setup>`, `<style>` 标签；
- **物理行号对齐黑科技**：通过在提取出的 script 块前补充等量 `\n`，保证 Tree-sitter 解析得到的 `node.start_point.row + 1` 恰好等于 `.vue` 文件的物理行号；
- 模板结构提取：提炼使用到的组件名（如 `ElButton`, `CallDetails`）、事件绑定（`@click="handleClick"`）、属性绑定（`:data="tableData"`），不深入复杂 AST 业务推理。

---

## 3. 实机测试验证记录

全量运行 `uv run pytest`（包含前序所有测试与新增 Preflight 测试），21 项测试全量通过：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\WorkSpace\lkio
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0
collected 21 items

tests\test_api_v1.py .......                                             [ 33%]
tests\test_ingestion_api.py ...                                          [ 47%]
tests\test_mvp1_gold_regression.py ...                                   [ 61%]
tests\test_readonly_integrity.py ...                                     [ 76%]
tests\test_treesitter_preflight.py .....                                 [100%]

================== 21 passed, 1 warning in 412.09s (0:06:52) ==================
```

### 3.1 关键测试断言记录
1. `test_treesitter_exact_pin_and_abi`: 验证 4 大 grammar 版本精确吻合，ABI 初始化正常。
2. `test_parse_snippets_basic`: 验证 TS, TSX, Java 合成代码块解析出有效的 `program` 语法树，`has_error == False`。
3. `test_vue_sfc_slicing_and_line_preservation`: 验证切片得到的 `handleClick()` 函数行号为 12，与源字符串物理行号完全一致。
4. `test_smoke_real_source_projects`: 实测真实文件：
   - `HELLO_FE`: `src/views/sales/components/CallDetails.vue`, `src/main.js`
   - `HELLO_BE`: Java 后端源文件（提取 Class 与 Program）
   - `L2C_FE`: Monorepo Vue 3 组件
   全部无异常成功解析。
5. `test_readonly_integrity_preflight`: 机械核验三大工程工作区 `git status --porcelain` 前后差异严格为 0。

---

## 4. MVP 完成情况检查

| 模块 / 阶段 | 计划指标 | 当前状态 | 达标说明 |
| :--- | :--- | :---: | :--- |
| **MVP0** | 基础架构与核心图谱 | **COMPLETED / FROZEN** | 已固化冻结 |
| **MVP1** | 项目只读摄取与快照 | **COMPLETED / FROZEN** | 已固化冻结，冷备份已归档 |
| **Step 2.0** | MVP2 规划与基线固化 | **COMPLETED** | 实施基线、6 大红线、Preflight Lock 均已冻结 |
| **Step 2.1 (MVP2-A)** | Tree-sitter 基础设施与 Vue SFC 切片 | **COMPLETED** | 依赖锁版、ParserFactory、SfcBlockSlicer、21项测试全过 |
| **Step 2.2 (MVP2-B)** | 代码符号提取 (Symbol Extraction) | **READY_TO_PLAN** | 待规划执行 |
| **Step 2.3 (MVP2-C)** | 代码结构图谱 (Code Structural Graph) | **QUEUED** | 待排期 |
| **Step 2.4 (MVP2-D)** | 跨工程代码图谱 (Cross-project Graph) | **QUEUED** | 待排期 |
| **Step 2.5 (MVP2-E)** | API 契约端到端追溯 | **QUEUED** | 待排期 |
| **Step 2.6** | 全量入库、Gold Set 与终审验收 | **QUEUED** | 待排期 |

---

## 5. 下一步规划 (Step 2.2: MVP2-B Symbol Extraction)

在启动 Step 2.2 之前，确认 MVP2 处于活动状态，且 Step 2.1 (MVP2-A) 全部通过验收。

### 5.2 核心任务
1. **实现多语言 AST 符号提取器 (`ingestion/code/extractors/`)**:
   - `ts_extractor.py`: 基于 Tree-sitter Queries 提取 Function, Class, Interface, Type, Variable, Enum, Hook (带有 `name_prefix_rule` 标记)。
   - `java_extractor.py`: 提取 Class, Interface, Method, Field, Annotation, Package。
   - `vue_extractor.py`: 结合 `SfcBlockSlicer` 提取 Component (标记为 `vue_sfc_rule`) 与内部脚本符号。
2. **实现确定性 Key 生成器 (`ingestion/code/key.py`)**:
   - 格式：`SYMBOL:<proj_key>:<file_rel_path>:<symbol_type>:<canonical_name>[:start_line]`。
3. **编写 Symbol 提取测试与真实项目符号抽样验证**:
   - 编写 `tests/test_symbol_extraction.py`，验证符号行号、代码签名、导出状态与分类标记。
