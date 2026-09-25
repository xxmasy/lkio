# LKIO MVP2-B 阶段性检查报告 — B-00/B-01/B-02 (Schema & Deterministic Key)

> **当前阶段**：**MVP2-B (Symbol Extraction - B-00 / B-01 / B-02 Checkpoint)**  
> **状态宣告**：**B-00/B-01/B-02 COMPLETED / FROZEN ➔ B-03 READY_TO_IMPLEMENT**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2-A = COMPLETED / FROZEN**  
> **基线锁标准**：`docs/mvp2/mvp2_step2_symbol_extraction_locked_baseline.md`  
> **核心原则**：严守顺序锁（B-00/01/02 验收全绿方可开启 B-03），AST 客观事实、0 业务推理、0 Key 截断、语言分化规范签名。

---

## 一、对照上一轮指令的检验与闭环证据

| 任务代号 | 任务目标 | 实施动作与工程证据 | 检验结论 |
|---|---|---|---|
| **B-00** | Schema 与抽取边界锁定 | 固化 4 大边界：Hook 仅识别定义不涉调用（调用归 MVP2-C）、Component 组合规则分类、语言分化规范签名、`entity_key TEXT` 无截断。形成文档 `docs/mvp2/mvp2_step2_symbol_extraction_locked_baseline.md`。 | **PASSED** |
| **B-01** | Database Schema 迁移至 TEXT | 生成并执行 Alembic 迁移 `c5cab8886f85`，将 `entities.entity_key` 修改为 `TEXT NOT NULL`，保留唯一索引 `ix_entities_entity_key`。实机 `inspect(engine)` 确认类型为 `TEXT`，消除任何截断碰撞隐患。 | **PASSED** |
| **B-02** | 语言分化 Normalizer 与 Key Builder | 在 `core/extraction/normalizer.py` 中分别实现 `canonicalize_ts_signature` 与 `canonicalize_java_signature`；实现 `compute_signature_discriminator` 与 `build_symbol_key`；更新 `SymbolCandidate` DTO。编写 7 项单元测试全部绿标（0.02s）。 | **PASSED** |

---

## 二、4 大 Schema / Boundary Lock 详细落地核查

### 1. Lock 1: `entities.entity_key` 升级为 TEXT NOT NULL UNIQUE (0 截断)
- **迁移记录**：`infra/db/alembic/versions/20260925_0554_c5cab8886f85_alter_entity_key_to_text.py`
- **Postgres 表结构验证**：
  ```python
  [(c['name'], str(c['type'])) for c in insp.get_columns('entities') if c['name'] == 'entity_key']
  # Output: [('entity_key', 'TEXT')]
  ```
- **唯一性索引验证**：
  `ix_entities_entity_key` 保持 `unique=True`。测试用例 `test_zero_truncation_long_key` 证明 > 250 字符且带多级深包路径的长 Key 完全无截断持久保留。

### 2. Lock 2: Hook 抽取边界明确
- MVP2-B 仅负责识别 Hook 符号定义：
  - `symbol_type = "HOOK"`
  - `base_symbol_type = "FUNCTION"`
  - `classification_method = "name_prefix_rule_v1"`
- 严禁在 MVP2-B 识别 Hook 调用（`useAuth()`），该调用事实严格划入 MVP2-C (`CALL_SITE / CALLS`)。

### 3. Lock 3: Component 组合规则分类
- 严禁单凭“返回 JSX”认定组件。
- 组合判断条件：
  1. JSX 元素包含或返回
  2. 命名符合严格 PascalCase
  3. 函数/组件结构形态
  方法标识：`jsx_function_component_v1`。Vue 单文件组件标识：`vue_sfc_rule_v1`。

### 4. Lock 4: 语言分化的规范签名 (Language-Specific Canonical Signature)
- **TypeScript / JavaScript (`canonicalize_ts_signature`)**：
  - 保留参数个数（arity）、形参类型。
  - 保留可选修饰符：`(id?: string)` ➔ `(string?)`，与必填 `(string)` 严格区分，特征码不同。
  - 保留 Rest 修饰符：`(...ids: string[])` ➔ `(...string[])`。
  - 剔除默认赋值干扰：`(limit: number = 20)` ➔ `(number)`。
  - 保留多层泛型：`(map: Map<string, number>)` ➔ `(Map<string,number>)`。
- **Java (`canonicalize_java_signature`)**：
  - 精确保留类型序列以区分重载：
    - `list(String)` ➔ `(String)`
    - `list(String, Integer)` ➔ `(String,Integer)`
    - `list(Long)` ➔ `(Long)`
    三者生成的 `signature_discriminator` 完全不同。
  - 自动剥离形参级注解（如 `@PathVariable("id")`, `@NotNull`）与 `final` 关键字。
  - 支持 Varargs：`(String... lines)` ➔ `(String...)`。
- **无参数/无签名符号**：
  - `canonical_signature = ""`
  - `signature_discriminator = "e3b0c44298fc1c14"` (SHA-256("")[:16])

---

## 三、单元测试执行与证据

执行命令：`uv run pytest tests/unit/test_symbol_key.py`  
执行结果：**7 passed in 0.02s**

```text
tests\unit\test_symbol_key.py .......                                    [100%]
============================== 7 passed in 0.02s ==============================
```

测试覆盖清单：
1. `test_empty_signature_discriminator`：空签名与 None 恒等于锁定常数 `e3b0c44298fc1c14`。
2. `test_ts_signature_canonicalization`：TS/JS 形参类型、可选（`?`）、Rest（`...`）、默认值与泛型清洗。
3. `test_java_signature_canonicalization`：Java 重载区分、注解剥离、Varargs、泛型清洗。
4. `test_build_symbol_key_format`：标准 Key 格式及正斜杠路径规范。
5. `test_symbol_key_line_shift_immunity`：行号第 10 行移动至第 85 行，Key 100% 相同（行漂移免疫）。
6. `test_zero_truncation_long_key`：长 Key 0 截断与完备性验证。
7. `test_reject_invalid_base_symbol_type`：拦截非原生 `OBJECT` 或 `CUSTOM_NODE` 等未受控类型。

---

## 四、永久架构红线核实

- **三个源项目只读**：`git -C ... status --porcelain` 比对，`HELLO_FE`, `HELLO_BE`, `L2C_FE` 差异严格为 0。
- **无业务推理**：0 LLM、0 业务语义猜测。

---

## 🔒 状态宣告与下一步计划

```text
MVP0   = COMPLETED / FROZEN
MVP1   = COMPLETED / FROZEN
MVP2-A = COMPLETED / FROZEN
MVP2-B (B-00, B-01, B-02) = COMPLETED / FROZEN
MVP2-B (B-03: TypeScript/JS Extractor) = READY_TO_IMPLEMENT
```

根据顺序锁纪律，已完成 B-00/B-01/B-02，后续将进入 **B-03 (TypeScript / JavaScript Extractor: 适配语言分化签名与 Hook/Component 组合规则分类)**。
