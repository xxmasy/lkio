# LKIO MVP2-B 阶段性结项审查报告 — B-00 / B-01 / B-02 (符号身份与标准化体系)

> **当前阶段**：**MVP2-B (Code Intelligence — Symbol Extraction Identity Subsystem)**  
> **状态宣告**：**B-00 / B-01 / B-02 COMPLETED / FROZEN ➔ 等待用户确认开启 B-03**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2-A = COMPLETED / FROZEN**  
> **执行纪律**：严守顺序锁（B-00 边界锁 ➔ B-01 数据库 TEXT 迁移 ➔ B-02 符号身份测试 100% 通过后，严禁提前推进 Extractor B-03..B-10）。

---

## 一、对照上一轮规划与指令的闭环核验

| 任务代号 | 任务目标 | 核心产出与工程证据 | 检验结论 |
|---|---|---|---|
| **B-00** | Schema 与抽取边界锁定 | 固化 5 大红线：9 大受控 Native 类型（含 `ANNOTATION`）、Hook 仅识别定义不涉调用（调用划入 MVP2-C）、Component 组合规则分类（`jsx_function_component_v1` / `vue_sfc_rule_v1`）、`qualified_name` 词法作用域。归档于 `docs/mvp2/mvp2_step2_symbol_extraction_locked_baseline.md`。 | **PASSED** |
| **B-01** | Database Schema 迁移至 TEXT | 生成并执行 Alembic 迁移 `c5cab8886f85`，修改 `entities.entity_key` 为 `TEXT NOT NULL`，保留唯一索引 `ix_entities_entity_key`。实机 PostgreSQL 验证类型为 `TEXT`，彻底杜绝 VARCHAR 长度截断风险。 | **PASSED** |
| **B-02** | 符号标准化、词法作用域与确定性 Key | 在 `core/extraction/normalizer.py` 中实现语言分化签名（TS/JS 与 Java）、词法作用域构造器 `build_qualified_name`、Key 生成器 `build_symbol_key`、逆向解析器 `parse_symbol_key`；在 `SymbolCandidate` DTO 中绑定 `compute_key()`。编写 13 项单元测试全部绿标通过（0.04s）。 | **PASSED** |

---

## 二、用户 5 项确定性 Key 准入判据严格验证

本阶段严格对照用户提出的 5 项准入判据编写了端到端单元测试（见 `tests/unit/test_symbol_key.py`），实机验证全部通过：

### 1. 判据 1：同一符号 + 插入任意行 ➔ Key 绝对不变 (Line Shift Invariance)
- **原理验证**：Symbol Key 完全由 `(project_key, file_rel_path, base_symbol_type, qualified_name, signature_discriminator)` 构成，物理行号仅作为坐标元数据存在，绝对不进入 Key 字符串。
- **实测证据**：
  ```python
  # 符号处于第 10 行
  cand_10 = SymbolCandidate(..., start_line=10, end_line=25, ...)
  # 上方插入 200 行注释/代码后移动到第 210 行
  cand_210 = SymbolCandidate(..., start_line=210, end_line=225, ...)
  assert cand_10.compute_key() == cand_210.compute_key()
  # 验证通过：两个 Key 100% 一致，且 Key 中无任何行号泄露
  ```

### 2. 判据 2：同名符号 + 不同词法作用域 ➔ Key 绝对不同 (Lexical Scope Isolation)
- **原理验证**：通过 `build_qualified_name` 强制包含作用域链（以 `::` 连接）。
- **实测证据**（同文件 `src/services/data.ts`，同名 `loadData`）：
  - 顶层函数：`loadData` ➔ Key: `...:loadData:e3b0c44298fc1c14`
  - 嵌套函数：`outer::loadData` ➔ Key: `...:outer::loadData:e3b0c44298fc1c14`
  - 类方法：`DataLoader::loadData` ➔ Key: `...:DataLoader::loadData:e3b0c44298fc1c14`
  - 内部类方法：`DataLoader::InnerHelper::loadData` ➔ Key: `...:DataLoader::InnerHelper::loadData:e3b0c44298fc1c14`
  - **断言结果**：4 个 Key 互不相同，`len(keys) == 4`。

### 3. 判据 3：Java Overload ➔ Key 绝对不同 (Java Overload Differentiation)
- **原理验证**：`canonicalize_java_signature` 剥离注解与形参名，提炼类型签名并计算 16 位 SHA-256 特征码。
- **实测证据**（同类同方法 `LeadController::list`）：
  - `list(String query)` ➔ 规范签名 `(String)` ➔ 特征码 `f7e9140df9491a13`
  - `list(String query, Integer page)` ➔ 规范签名 `(String,Integer)` ➔ 特征码 `0dbdff529731aa2e`
  - `list(Long id)` ➔ 规范签名 `(Long)` ➔ 特征码 `d03da4d7328bf380`
  - `list()` ➔ 规范签名 `()` ➔ 特征码 `e3b0c44298fc1c14`
  - **断言结果**：4 个 Overload 方法生成的 Key 完全独立，不发生任何碰撞覆盖。

### 4. 判据 4：TS 可选参数与 Rest 参数 ➔ Key 绝对不同 (TypeScript Optional & Rest)
- **原理验证**：`canonicalize_ts_signature` 保留必填、可选 `?` 与 Rest `...` 状态，不进行任意压平。
- **实测证据**（同名 `batchFetch`）：
  - `(id: string)` ➔ `(string)` ➔ 特征码 `86e2ea4da53ecf30`
  - `(id?: string)` ➔ `(string?)` ➔ 特征码 `48227b953835eec0`
  - `(...ids: string[])` ➔ `(...string[])` ➔ 特征码 `8cba67837095c2f5`
  - `()` ➔ `()` ➔ 特征码 `e3b0c44298fc1c14`
  - **断言结果**：4 种签名形态生成 4 个互斥 Key。

### 5. 判据 5：不同 Vue Script Block ➔ Key 绝对不同 (Vue Multi-Script Block Isolation)
- **原理验证**：SFC 多 script 块通过 `block_scope` 显式区隔：
  - 普通 `<script>`：`block_scope = "script"` ➔ 作用域为 `script::foo`
  - Setup `<script setup>`：`block_scope = "script_setup"` ➔ 作用域为 `script_setup::foo`
- **实测证据**（同文件 `MultiScriptView.vue`，同名 `initComponent`）：
  - Key A: `SYMBOL:HELLO_FE:src/views/MultiScriptView.vue:FUNCTION:script::initComponent:e3b0c44298fc1c14`
  - Key B: `SYMBOL:HELLO_FE:src/views/MultiScriptView.vue:FUNCTION:script_setup::initComponent:e3b0c44298fc1c14`
  - **断言结果**：`key_plain != key_setup`，作用域清晰，永不冲突。

---

## 三、架构锁定 (Lock 1 ~ Lock 5) 与落地实现清单

1. **Lock 1: 9 大受控 Native Symbol Types**
   - 原生受控枚举：`CLASS`, `INTERFACE`, `FUNCTION`, `METHOD`, `VARIABLE`, `FIELD`, `ENUM`, `TYPE`, `ANNOTATION`。
   - Java `@interface Foo` 作为 `ANNOTATION` 符号入库；类/方法上的使用（`@RestController`, `@Autowired`）作为符号元数据 `metadata["annotations"]` 存储，不作为独立符号节点。
2. **Lock 2: 受控 base_symbol_type**
   - `COMPONENT` 与 `HOOK` 作为高层规则分类，其底层 `base_symbol_type` 必须继承自 9 大原生类型（如 `FUNCTION` 或 `VARIABLE`）。
   - `test_reject_invalid_base_symbol_type` 验证：传入 `OBJECT` 或 `CUSTOM_NODE` 时直接抛出 `ValueError`。
3. **Lock 3: 确定性 Key 无行号依赖**
   - Key 结构：`SYMBOL:<project_key>:<file_rel_path>:<base_symbol_type>:<qualified_name>:<signature_discriminator>`。
   - 正斜杠标准化（`normalize_rel_path`）。
4. **Lock 4: 语言分化规范签名与空特征码锁定**
   - TS: `canonicalize_ts_signature`（处理参数、可选、Rest、默认值、泛型）。
   - Java: `canonicalize_java_signature`（处理重载、泛型、Varargs、注解与 final 清洗）。
   - 空参数/无签名：固定输出 `e3b0c44298fc1c14`（SHA-256("")[:16]）。
5. **Lock 5: 词法作用域链（Lexical Scope Path）与逆向解析安全**
   - `build_qualified_name` 统一使用 `::` 作为分隔符。
   - 提供 `parse_symbol_key` 辅助函数，采用右侧切分与左侧限长，安全解析携带 `::` 的 qualified_name。

---

## 四、自动化测试证据 (13/13 PASSED)

执行命令：
```powershell
uv run pytest tests/unit/test_symbol_key.py -v
```

执行输出结果：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0 -- C:\WorkSpace\lkio\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\WorkSpace\lkio
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 13 items

tests/unit/test_symbol_key.py::test_criterion_1_line_shift_invariance PASSED [  7%]
tests/unit/test_symbol_key.py::test_criterion_2_lexical_scope_isolation PASSED [ 15%]
tests/unit/test_symbol_key.py::test_criterion_3_java_overload_differentiation PASSED [ 23%]
tests/unit/test_symbol_key.py::test_criterion_4_ts_optional_and_rest_differentiation PASSED [ 30%]
tests/unit/test_symbol_key.py::test_criterion_5_vue_script_block_isolation PASSED [ 38%]
tests/unit/test_symbol_key.py::test_build_qualified_name_variations PASSED [ 46%]
tests/unit/test_symbol_key.py::test_empty_signature_discriminator PASSED [ 53%]
tests/unit/test_symbol_key.py::test_ts_signature_canonicalization_matrix PASSED [ 61%]
tests/unit/test_symbol_key.py::test_java_signature_canonicalization_matrix PASSED [ 69%]
tests/unit/test_symbol_key.py::test_build_symbol_key_format PASSED       [ 76%]
tests/unit/test_symbol_key.py::test_zero_truncation_long_key PASSED      [ 84%]
tests/unit/test_symbol_key.py::test_reject_invalid_base_symbol_type PASSED [ 92%]
tests/unit/test_symbol_key.py::test_symbol_candidate_compute_key_integration PASSED [100%]

============================= 13 passed in 0.04s ==============================
```

---

## 五、源项目物理只读性审查

- 执行命令：`git -C "C:\WorkSpace\hello" status --porcelain; git -C "C:\WorkSpace\hello-backend" status --porcelain; git -C "C:\WorkSpace\L2C project" status --porcelain`
- 审查结论：三个源项目工作区无任何由 LKIO 引入的修改、增加或删除，物理只读红线 100% 遵守。

---

## 🔒 当前里程碑状态与下一步行动

```text
MVP0   = COMPLETED / FROZEN
MVP1   = COMPLETED / FROZEN
MVP2-A = COMPLETED / FROZEN
MVP2-B:
  B-00 (Schema/Boundary Lock)       = COMPLETED / FROZEN
  B-01 (Database Migration to TEXT) = COMPLETED / FROZEN
  B-02 (Identity & Key Normalizer)  = COMPLETED / FROZEN
  B-03..B-10 (Extractors & Beyond)  = READY_TO_PLAN / WAITING_USER_CONFIRMATION
```

B-00、B-01、B-02 身份子系统与 5 项判据已全部闭环固化。等待用户复核与指令确认后，正式解锁 **B-03 (TypeScript/JavaScript Extractor 实施与金标准回归)**。
