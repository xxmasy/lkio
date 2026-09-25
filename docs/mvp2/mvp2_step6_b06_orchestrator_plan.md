# LKIO MVP2-B B-06 实施规划 — Symbol Extraction Orchestrator & Fallback Handling (Approved Baseline with 10 Architecture Locks)

> **阶段**：**MVP2-B (Step 2.2 — B-06: Symbol Extraction Orchestrator & Fallback Handling)**  
> **当前状态**：**READY_TO_EXECUTE (10 大架构锁已全部固化，实施前审查完全闭环，正式准入编码实施)**  
> **前置阶段状态终审核查**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2-A = COMPLETED / FROZEN**  
> - **B-00 (Schema 与边界锁) = COMPLETED / FROZEN**  
> - **B-01 (Database TEXT 迁移) = COMPLETED / FROZEN**  
> - **B-02 (符号身份与标准化体系) = COMPLETED / FROZEN**  
> - **B-03 (TypeScript/JavaScript Extractor) = COMPLETED / FROZEN**  
> - **B-04 (Java Extractor) = COMPLETED / FROZEN**  
> - **B-05 (Vue Extractor) = COMPLETED / FROZEN**  
> - **B-06 (Orchestrator & Fallback) = READY_TO_EXECUTE (本方案)**  
> - **B-07..B-10 = LOCKED (物理冻结)**  

---

## 📌 关键审计注记 (Auditing Lock)

> **B-05 的“6 大专项锁”与 16 Gates 已完整闭环。B-06 开始将首次把多个单语言 Extractor 接入统一 Orchestrator，在此正式锁定核心架构契约：**  
> **B-03/B-04/B-05 的单语言 Extractor 契约（`extract(code_bytes, file_path, file_rel_path, language) -> list[SymbolCandidate]`）不得因 B-06 的调度需求反向修改！**  
> **B-06 是纯粹的上层编排适配层（Upper Orchestration & Adaptation Layer），负责“选择谁来解析、如何容错隔离、如何汇总结果与修饰确定性 Key”，绝对不重新解释底层 Symbol 语义，绝对不倒逼下层 Extractor 变形。**

```text
                    ┌────────────────────────────┐
                    │    SymbolCandidate DTO     │
                    └─────────────▲──────────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
       TypeScript Extractor   Java Extractor    Vue SFC Extractor
       (B-03 FROZEN)          (B-04 FROZEN)      (B-05 FROZEN)
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │ (Strictly Preserved Contract)
                                  ▼
                    B-06 Extraction Orchestrator
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
             Language Routing          Failure Isolation
             & Normalization           & Discrete Fallback
                     │                         │
                     └────────────┬────────────┘
                                  ▼
                    FileExtractionResult DTO
                    (Deterministic Keys + Diagnostics)
```

---

## 一、B-06 职责边界护栏 (Owns vs Does Not Own)

```text
┌──────────────────────────────────────────────┐
│                 B-06 OWNS                    │
├──────────────────────────────────────────────┤
│ File extension routing                       │
│ Language dispatch                            │
│ Empty source detection                       │
│ Encoding preflight                           │
│ Parser availability handling                 │
│ Per-file exception isolation                 │
│ Failure normalization                        │
│ Project context propagation                  │
│ Symbol key generation invocation             │
│ Batch aggregation                            │
│ Statistics & Counter Integrity               │
│ Deterministic result ordering                │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│              B-06 DOES NOT OWN               │
├──────────────────────────────────────────────┤
│ AST traversal semantics                      │
│ Symbol classification                        │
│ Signature construction                       │
│ Vue semantic interpretation                  │
│ Java semantic interpretation                 │
│ JS/TS type inference                         │
│ Graph relation extraction (CALLS/IMPORTS...) │
│ Cross-file resolution                        │
│ Business semantics                           │
│ LLM inference                                │
│ Database persistence                         │
└──────────────────────────────────────────────┘
```

---

## 二、8 大架构锁 (The 8 Orchestrator Locks)

### 1. LOCK-ORCH-01: 确定性文件类型路由矩阵 (Deterministic File Routing)
Orchestrator 建立显式、受控的文件扩展名到语言提取器的映射，杜绝模糊推断：

| 扩展名 | 目标语言分类 | 分发目标 Extractor | 语言模式 / 参数 |
|---|---|---|---|
| `.ts` | `typescript` | `TypeScriptExtractor` | `language="typescript"` |
| `.tsx` | `tsx` | `TypeScriptExtractor` | `language="tsx"` |
| `.js` | `javascript` | `TypeScriptExtractor` | `language="javascript"` |
| `.jsx` | `jsx` | `TypeScriptExtractor` | `language="jsx"` |
| `.mjs` | `javascript` | `TypeScriptExtractor` | `language="javascript"` |
| `.cjs` | `javascript` | `TypeScriptExtractor` | `language="javascript"` |
| `.java` | `java` | `JavaExtractor` | `language="java"` |
| `.vue` | `vue` | `VueExtractor` | `language="vue"` |
| 其它扩展名 | `unsupported` | *不派发，直接记录失败分类* | `UNSUPPORTED_EXTENSION` |

---

### 2. LOCK-ORCH-02: Extractor 契约统一与无重新解释原则
- **输入契约**：所有 Extractor 均满足纯内存入参：
  `extract(code_bytes: bytes, file_path: str, file_rel_path: str, language: str) -> list[SymbolCandidate]`
- **输出契约**：仅输出不可变的 `list[SymbolCandidate]`。
- **职责边界**：
  - Orchestrator 负责将上层工程标识 `project_key` 注入每个 `SymbolCandidate`；
  - Orchestrator 负责调用 `candidate.compute_key()` 生成确定性主键；
  - Orchestrator **严禁重新解释、过滤或篡改** Extractor 返回的 `symbol_type`、`classification_method`、`evidence` 或坐标信息。

---

### 3. LOCK-ORCH-03: 单文件失败隔离流水线 (Strict Failure Isolation)
在工程级批量扫描中，任何单个文件的异常（畸形语法、未知字符集、解析异常）绝对不能拖垮整个项目的扫描流水线：

```text
File A (Normal)    ──► Route ──► Extractor ──► Success ──► Results A
File B (Corrupted) ──► Route ──► Exception ──► Catch   ──► Diagnostic Record B (Continue)
File C (Normal)    ──► Route ──► Extractor ──► Success ──► Results C
```

- **隔离单元**：文件级独立沙箱；
- **错误捕获**：捕获所有文件级解析异常与内部错误；
- **流水线保活**：捕获后输出结构化错误诊断记录，流水线无缝处理下一个文件。

---

### 4. LOCK-ORCH-04: 受控的离散失败分类法 (Controlled Fallback Taxonomy)
严禁将所有错误或跳过粗暴地标记为模糊的 `UNKNOWN`。B-06 强制引入离散错误分类字典：

```python
class ExtractionFailureReason(str, Enum):
    UNSUPPORTED_EXTENSION = "unsupported_extension"  # 不受支持的文件后缀（如 .css, .json, .py）
    PARSER_UNAVAILABLE    = "parser_unavailable"     # 目标语言 Tree-sitter Parser/Grammar 未能加载
    ENCODING_FAILURE      = "encoding_failure"       # 文件二进制乱码或无法按 UTF-8 安全解码
    MALFORMED_SOURCE      = "malformed_source"       # 源码严重残缺，AST 根节点或关键骨架解析失败
    EXTRACTOR_EXCEPTION   = "extractor_exception"    # 抽取器在遍历 AST 过程中抛出未预期的内部异常
    EMPTY_SOURCE          = "empty_source"           # 文件内容为 0 字节或纯空白
```

每个失败文件必须产出明确的 `error_reason` 与 `error_detail`，便于在前端可视化与诊断报告中精确呈现。

---

### 5. LOCK-ORCH-05: 绝对禁止偷渡图谱与业务逻辑 (Zero Graph / Trace Smuggling)
B-06 依然处于 **MVP2-B (Symbol Extraction)** 阶段，严格禁止跨越至后续阶段：
- ❌ **绝对禁止构建关系图谱边**：禁止生成 `CALLS`, `IMPORTS`, `EXPORTS`, `EXTENDS`, `IMPLEMENTS` 关系边（此为 **MVP2-C** 专属职责）；
- ❌ **绝对禁止跨层契约追溯**：禁止提取或推断 `Controller -> Service -> Mapper` 跨层调用链（此为 **MVP2-E** 专属职责）；
- ❌ **绝对禁止进行数据库持久化**：B-06 的输出是纯内存数据传输对象（DTO），DB 批量入库与幂等合并属于 **B-07** 专属职责；
- ❌ **绝对禁止引入 LLM 语义脑补**：保持 100% 静态事实，无虚构置信度。

---

### 6. LOCK-ORCH-06: 失败分类可观测性边界 (Failure Classification Observability Boundary)
> **B-06 绝对禁止为了重新解释 Extractor 语义而自行独立解析源码或检查 AST 结构。**

B-06 仅可从以下 4 个受控源头归类失败：
1. **Orchestrator 自身拥有的确定性文件级前置条件**：扩展名不支持 (`UNSUPPORTED_EXTENSION`)、文件纯空 (`EMPTY_SOURCE`)、编码无法解码 (`ENCODING_FAILURE`)；
2. **在分发/启动边界可观测的解析器可用性故障**：目标语言 Parser 实例化失败 (`PARSER_UNAVAILABLE`)；
3. **被冻结的 Extractor 显式抛出的异常**：(`EXTRACTOR_EXCEPTION`)；
4. **在不改变 B-03/B-04/B-05 公共返回契约的前提下，Extractor 已经提供的失败信号**。

**B-06 绝不能仅仅为了归类 `MALFORMED_SOURCE` 就引入第二套 AST 解析路径。如果无法通过冻结的 Extractor 契约确定性观测到，实现严禁在 Orchestrator 层凭空捏造该分类。**

---

### 7. LOCK-ORCH-07: 符号语义不可变性与相对路径身份 (Candidate Semantic Immutability)
- **语义不可变**：Orchestrator 仅可为 `SymbolCandidate` 注入其拥有的编排上下文（`project_key` 与派生的 `symbol_key`）。Orchestrator **绝对禁止改写**以下 Extractor 拥有的语义字段：
  ```text
  symbol_type, base_symbol_type, name, qualified_name, signature,
  classification_method, evidence, coordinates (start/end line/col),
  metadata, source provenance
  ```
- **相对路径身份**：确定性主键 `compute_key()` 计算时，**必须且仅能使用 `file_rel_path`，绝对不能使用绝对路径 `file_path`**。确保同一仓库在 Windows、Linux、Docker、CI 环境下生成的 Key 严格位阶一致。

---

### 8. LOCK-ORCH-08: 批处理确定性排序 (Deterministic Batch Ordering)
- **文件排序确定性**：`extract_batch(files)` 在分发前，**必须显式按 `file_rel_path` 的字典序（lexical sort）标准化排序**。消除操作系统文件系统枚举差异（Windows NTFS vs Linux ext4），确保相同逻辑输入在任何平台产出排序完全一致的批处理结果；
- **文件内符号排序**：每个 `FileExtractionResult` 内部：
  - `symbols` 的顺序严格保持底层 Extractor 定义的 AST 确定性行号顺序；
  - `symbol_keys` 的顺序严格与 `symbols` 一一对应保持一致。

---

### 9. LOCK-ORCH-09: MALFORMED_SOURCE 成立规则与纯粹可观测性 (Malformed Source Observability Rule)
> **`MALFORMED_SOURCE` 仅在 Frozen Extractor 显式暴露该失败信号，或通过冻结契约明确约定的 parser failure signal 时成立；B-06 绝不根据源码内容、AST ERROR 节点或自身启发式规则自行推导 `MALFORMED_SOURCE`。**

- 若底层 Parser / Extractor 具备容错能力并能从包含语法残缺的源码中恢复出合法 AST 并正常返回 symbols，B-06 严格保留成功结果（`success=True`），绝不主观判定为 `MALFORMED_SOURCE`；
- 只有当底层 Extractor 明确抛出语法阻断异常或显式返回不可解析失败信号时，B-06 才将其归类为 `MALFORMED_SOURCE`；
- 此锁彻底杜绝 Orchestrator 演化为“第二套语法解析器”的架构坏味道。

---

### 10. LOCK-ORCH-10: 确定性逻辑等价域 (Deterministic Logical Equivalence Domain)
> **相同逻辑输入在不同平台必须产生确定的逻辑等价输出（Deterministic Logical Equivalence）。**

为避免将运行时耗时和操作系统路径混入确定性判定，明确界定比较域：
- **纳入确定性比较域 (Deterministic Equivalence Domain)**：
  - `project_key`
  - `file_rel_path` (严格统一使用正斜杠 `/`)
  - `language`
  - `success`
  - `symbols` 原生语义字段（按行号顺序）
  - `symbol_keys`（与 `symbols` 一一对应）
  - `error_reason` (受控枚举)
  - `error_detail` (归一化错误信息)
  - 统计计数器（`total_files`, `scanned_files`, `successful_files`, `failed_files`, `unsupported_files`, `total_symbols`, `symbols_by_type`, `failures_by_reason`）
  - 批处理文件输出顺序（严格按 `file_rel_path` 字典序）
- **排除出确定性比较域 (Runtime & Host Specific - Excluded)**：
  - `file_path`（操作系统本地绝对路径，Windows 反斜杠 vs Linux 正斜杠）
  - `duration_ms`（受 CPU 负载与 GC 抖动影响的运行时计时）
  - 宿主机专属的临时运行时元数据

---

## 三、B-06 数据结构与统计完整性契约 (DTOs & Integrity)

### 1. `FileExtractionResult` (单文件结果与诊断)
```python
@dataclass
class FileExtractionResult:
    file_rel_path: str
    file_path: str
    language: str
    success: bool
    symbols: list[SymbolCandidate] = field(default_factory=list)
    symbol_keys: list[str] = field(default_factory=list)
    error_reason: str | None = None   # 来自 ExtractionFailureReason
    error_detail: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 2. `BatchExtractionSummary` (批处理扫描摘要与统计完整性)
```python
@dataclass
class BatchExtractionSummary:
    project_key: str
    total_files: int
    scanned_files: int
    successful_files: int
    failed_files: int
    unsupported_files: int
    total_symbols: int
    symbols_by_type: dict[str, int]
    failures_by_reason: dict[str, int]
    duration_ms: float
    results: list[FileExtractionResult] = field(default_factory=list)
```

### 3. 统计计数完整性硬约束 (Counter Integrity Rule)
> **`unsupported_files` 是一种“不参与 Extractor 处理”的独立终态，绝不计入 `failed_files`！**

在任何批处理结果中，必须无条件满足恒等式：
$$\text{total\_files} = \text{successful\_files} + \text{failed\_files} + \text{unsupported\_files}$$
并且：
$$\text{scanned\_files} = \text{successful\_files} + \text{failed\_files}$$

---

## 四、16 项 Acceptance Gates (Gate A ~ P) 细目设计

| Gate 代号 | 准入要求与设计规格 | 验证方式与测试目标 |
|---|---|---|
| **Gate A** | **Complete File Type Routing** | 验证 `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.java`, `.vue` 均被路由到正确的提取器。 |
| **Gate B** | **Unsupported Extension Handling** | 验证 `.css`, `.json`, `.py`, `.md` 被标记为 `UNSUPPORTED_EXTENSION`，计入 `unsupported_files`，不发生异常。 |
| **Gate C** | **Extractor Contract Invariance** | 编写 `assert_symbol_semantic_equivalence(...)`，机械化证明被 Orchestrator 包装后的 Extractor 语义字段 100% 保持未变。 |
| **Gate D** | **Single-File Failure Isolation** | 构造 `valid -> bad (RuntimeError) -> valid -> bad -> valid` 交替序列，证明第 1、3、5 个文件提取完全不受异常影响。 |
| **Gate E** | **Controlled Failure Taxonomy** | 验证 Orchestrator 拥有的错误条件严格映射到预定义 6 大枚举；Extractor 内部错误基于可观测行为分类，禁止 UNKNOWN 漫灌，禁止二次 AST 解析。 |
| **Gate F** | **Malformed Source Tolerance** | 面对语法残缺源文件，完全继承冻结 Extractor 的 AST 容错恢复行为；B-06 仅负责隔离与记录，绝不实现第二套 AST 算法。 |
| **Gate G** | **Encoding Robustness** | 面对畸形字节或无法解码的二进制文件，平稳记录为 `ENCODING_FAILURE`，不抛出未捕获异常。 |
| **Gate H** | **Empty File Handling** | 面对 0 字节或纯空白文件，明确记录为 `EMPTY_SOURCE`，耗时接近 0，不触发 AST 解析。 |
| **Gate I** | **Deterministic Key Generation** | 验证 Orchestrator 输出的每个 Symbol 均携带基于 `file_rel_path` 计算的全局唯一确定性 Key。 |
| **Gate J** | **Project Key Propagation** | 验证调用方传入的 `project_key` 准确注入到下属每一个 `SymbolCandidate` 中。 |
| **Gate K** | **Batch API & Counter Integrity** | 验证 `extract_batch` 正常工作，且严格满足 `successful + failed + unsupported == total`。 |
| **Gate L** | **Zero Premature Graph** | 机械化扫描输出对象结构，断言无任何 `calls`, `imports`, `extends`, `implements`, `edges`, `relations`, `graph` 字段。 |
| **Gate M** | **Zero Database Persistence** | 代码静态扫描证明 B-06 模块内绝对未 import `sqlalchemy`, `Session`, `engine`, `transaction`, `repository`。 |
| **Gate N** | **Source Project Strict Read-Only** | 针对 `HELLO_FE`, `HELLO_BE`, `L2C_FE` 真实工程扫描前后 Git 状态完全一致，0 改动。 |
| **Gate O** | **Benchmark Contract (< 10ms Baseline)** | 固定硬件、温启动 Parser、固定 4 语言样本集（N=100：TS 25, JS 25, Java 25, Vue 25），均摊耗时目标 < 10ms 作为性能基线记录（产出 mean/median/p95/throughput，CI 机器抖动不作为语义正确性阻断项）。 |
| **Gate P** | **Deterministic Ordering & Gold Suite** | 包含 5 组金标准夹具（含 `deterministic_order` 验证乱序文件名输入产出字典序等价结果），100% 通过。 |

---

## 五、金标准夹具规划 (5 类 Gold Fixtures)

在 `tests/gold/mvp2/symbols/orchestrator/` 建立 5 类专属夹具：

1. **`valid_multi_lang/`**：跨语言混编包，包含 TS、JS、Java、Vue 各 1 个标准文件，验证统一路由与确定性 Key；
2. **`malformed_syntax/`**：包含语法残缺代码文件，验证 AST 容错与优雅恢复；
3. **`unsupported_files/`**：包含 `.css`、`.json`、`.yaml` 等非代码文件，验证 `UNSUPPORTED_EXTENSION` 快速过滤；
4. **`corrupted_binary/`**：包含非法字节序列的文件，验证 `ENCODING_FAILURE` 隔离保护；
5. **`deterministic_order/`**：人为命名乱序文件（如 `z.ts`, `a.java`, `m.vue`, `b.js`），验证批处理字典序归一化与多次运行幂等性。

### 阶段专属测试目录
```text
tests/unit/b06/
└── test_orchestrator_b06.py  # B-06 专属单元测试（路由、多语言统合、失败隔离、错误分类、批处理摘要、排序与基准合约）
```

---

## 六、实施步骤规划 (Execution Steps B-06-01 ~ B-06-08)

```text
B-06-01: 确定性文件路由矩阵与前置检查 (Routing Matrix, Empty Source, Unsupported Extension, Encoding)
B-06-02: 数据传输对象 (FileExtractionResult, BatchExtractionSummary, ExtractionFailureReason)
B-06-03: 单文件独立沙箱与失败隔离实现 (File Sandbox, Exception Catching, Provenance Protection)
B-06-04: 批处理编排器与字典序排序归一化 (Batch Pipeline, Lexical Sort, Counter Integrity)
B-06-05: 5 大金标准测试夹具构建 (valid_multi_lang, malformed, unsupported, binary, order)
B-06-06: 16 项 Acceptance Gates 自动化验证 (test_orchestrator_b06.py 100% 闭环)
B-06-07: 全阶段回归隔离测试 (B-00~B-05 独立全绿验证)
B-06-08: 三大源工程只读 Smoke 核验、编写结项报告并冻结
```
