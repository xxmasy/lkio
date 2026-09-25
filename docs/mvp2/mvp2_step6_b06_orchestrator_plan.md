# LKIO MVP2-B B-06 实施规划 — Symbol Extraction Orchestrator & Fallback Handling

> **阶段**：**MVP2-B (Step 2.2 — B-06: Symbol Extraction Orchestrator & Fallback Handling)**  
> **当前状态**：**READY_TO_PLAN (规划、契约审查与门禁设计阶段，严禁直接编写生产代码)**  
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
> - **B-06 (Orchestrator & Fallback) = READY_TO_PLAN (本方案)**  
> - **B-07..B-10 = LOCKED (物理冻结)**  

---

## 📌 关键审计注记 (Auditing Lock)

> **B-05 的“6 大专项锁”与 16 Gates 已完整闭环。B-06 开始将首次把多个单语言 Extractor 接入统一 Orchestrator，因此在此正式锁定核心架构契约：**  
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

## 一、B-06 必须锁死的 5 大架构问题 (The 5 Orchestrator Locks)

为确保工程纯洁性与架构健壮性，B-06 方案严格锁死以下 5 大问题：

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

- **隔离单元**：文件级 `try-except` 沙箱；
- **错误捕获**：不仅捕获通用异常，更捕获 Tree-sitter 特殊异常；
- **流水线保活**：捕获后输出结构化错误诊断记录，流水线无缝处理下一个文件。

---

### 4. LOCK-ORCH-04: 受控的离散失败分类法 (Controlled Fallback Taxonomy)
严禁将所有错误或跳过粗暴地标记为模糊的 `UNKNOWN`。B-06 强制引入离散错误分类字典：

```python
class ExtractionFailureReason(str, Enum):
    UNSUPPORTED_EXTENSION = "unsupported_extension"  # 不受支持的文件后缀（如 .css, .json, .py）
    PARSER_UNAVAILABLE    = "parser_unavailable"     # 目标语言 Tree-sitter Parser/Grammar 未能加载
    ENCODING_FAILURE      = "encoding_failure"       # 文件二进制乱码或无法按 UTF-8/指定编码安全解码
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

## 二、B-06 数据结构契约设计 (DTOs)

为实现结果汇总与失败隔离，定义两个无状态结构化 DTO：

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

### 2. `BatchExtractionSummary` (批处理扫描摘要)
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

---

## 三、16 项 Acceptance Gates (Gate A ~ P) 设计

| Gate 代号 | 准入要求与设计规格 | 验证方式与测试目标 |
|---|---|---|
| **Gate A** | **Complete File Type Routing** | 验证 `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.java`, `.vue` 均被路由到正确的提取器。 |
| **Gate B** | **Unsupported Extension Handling** | 验证 `.css`, `.json`, `.py`, `.md` 被标记为 `UNSUPPORTED_EXTENSION`，不发生崩溃。 |
| **Gate C** | **Extractor Contract Invariance** | 验证 B-03, B-04, B-05 的入参与出参契约 100% 保持不变，未被 Orchestrator 篡改。 |
| **Gate D** | **Single-File Failure Isolation** | 构造一个故意抛出异常的文件，批处理时该文件记录失败，其余 N 个有效文件 100% 正常产出。 |
| **Gate E** | **Controlled Failure Taxonomy** | 针对不同异常场景，准确产出 6 种预定义 `ExtractionFailureReason`，拒绝模糊 `UNKNOWN`。 |
| **Gate F** | **Malformed Source Tolerance** | 面对语法碎裂或不完整的源文件，在记录诊断的同时尽最大努力提取合法 AST 片段。 |
| **Gate G** | **Encoding Robustness** | 面对包含畸形字节、BOM 或非标准 UTF-8 编码的文件，能够平稳容错降级或明确报告。 |
| **Gate H** | **Empty File Handling** | 面对 0 字节文件，明确报告 `EMPTY_SOURCE`，耗时接近 0，不触发 AST 解析。 |
| **Gate I** | **Deterministic Key Generation** | 验证 Orchestrator 输出的每个 Symbol 均携带全局唯一、符合 5 大不变量的确定性 Key。 |
| **Gate J** | **Project Key Propagation** | 验证调用方传入的 `project_key` 准确注入到下属每一个 `SymbolCandidate` 中。 |
| **Gate K** | **Batch Extraction API** | 提供统一的 `extract_batch(files: list[...], project_key: str)` 方法，返回结构化摘要。 |
| **Gate L** | **Zero Premature Graph** | 严格审查输出，断言无任何关系边（CALLS/IMPORTS/EXTENDS）渗入。 |
| **Gate M** | **Zero Database Persistence** | B-06 内部绝对无 SQLAlchemy、Session、INSERT 或 UPDATE 调用，纯内存计算。 |
| **Gate N** | **Source Project Strict Read-Only** | 针对 `HELLO_FE`, `HELLO_BE`, `L2C_FE` 真实工程扫描前后 Git 状态完全一致，0 改动。 |
| **Gate O** | **High Throughput Performance** | 单核单文件抽取调度均摊耗时小于 10ms，满足大规模代码仓库高吞吐需求。 |
| **Gate P** | **All Gold Suites Integration** | 覆盖 TS/JS/Java/Vue 黄金样本文件，验证 100% 正确抽取且分类准确。 |

---

## 四、金标准夹具与测试规划 (Gold Fixtures & Test Plan)

为验证 B-06 的跨语言统合与容错隔离，将在 `tests/gold/mvp2/symbols/orchestrator/` 建立 4 类专属夹具：

1. **`valid_multi_lang/`**：跨语言混编包，包含 TypeScript、JavaScript、Java、Vue 各 1 个标准文件，验证统一路由与确定性 Key；
2. **`malformed_syntax/`**：包含残缺代码片段的文件（如缺少闭合大括号、非法标记），验证 AST 容错与 `MALFORMED_SOURCE` 报告；
3. **`unsupported_files/`**：包含 `.css`、`.json`、`.yaml` 等非代码文件，验证 `UNSUPPORTED_EXTENSION` 快速过滤；
4. **`corrupted_binary/`**：伪造的非法二进制文件，验证 `ENCODING_FAILURE` 隔离保护。

### 阶段专属测试目录
```text
tests/unit/b06/
└── test_orchestrator_b06.py  # B-06 专属单元测试（路由、多语言统合、失败隔离、错误分类、批处理摘要）
```

---

## 五、实施纪律与测试报告准则

1. **测试隔离报告纪律**：
   在 B-06 结项报告中，核心准入依据必须为且仅为：
   ```bash
   uv run pytest tests/unit/b06 -q
   ```
   历史阶段回归（B-00~B-05）继续作为独立的独立表格分层陈述，严禁混合计数。
2. **物理只读保证**：
   继续通过 `tests/integration/test_real_projects_symbols_smoke.py` 严格保持三大真实仓库 0 修改。
3. **分阶段结项红线**：
   B-06 仅交付内存级 Orchestration 与 Failure Isolation。通过验收后，方可解锁 **B-07 (Database Persistence & Idempotency Pipeline)**。
