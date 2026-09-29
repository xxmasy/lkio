# LKIO: Open-source Repository Intelligence & Code Reasoning Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![LKIO-Bench](https://img.shields.io/badge/LKIO--Bench-20%20Layers%20Passed-brightgreen)](#-lkio-bench-20-layer-reasoning-benchmark)
[![Test Suite](https://img.shields.io/badge/Tests-243%20Passed-success)](#-quick-start--verification)

> **Mission**: **LKIO = Open-source Repository Intelligence & Code Reasoning Engine**  
> LKIO provides an infrastructure-grade repository intelligence layer for autonomous coding agents (Claude Code, Cursor, Codex, etc.). It combines fine-grained Tree-sitter AST symbol indexing, cross-repository dependency topology, Git temporal reasoning, hybrid retrieval, and safety governance gates to enable deterministic, evidence-backed code reasoning.

---

## ⚡ Why LKIO: Empirical Comparison

| 维度 (Dimension) | 全量投喂 (Full Context) | 传统 Chunk RAG | LKIO (AST + Graph + Hybrid) |
|---|:---:|:---:|:---:|
| **任务 Token 均值** | 12,698 | 4,266 | **545** (↓95.7%) |
| **P95 Token 峰值** | 24,012 | 5,000 | **590** (↓97.5%) |
| **千次任务成本** [^cost] | $38.09 | $12.80 | **$1.64** (↓95.7%) |
| **跨栈链路召回 ($n=12$)** | — | 0/12 | **12/12** |
| **3-Hop 深层拓扑召回** | 10% | 0% | **100%*** |
| **置信度校准误差 ECE ($n=120$)** | 0.2300 | 0.1850 | **0.0469** (↓74.6%) |
| **高危对抗场景拦截 ($n=8$)** | 0/8 | 0/8 | **8/8** |

[^cost]: **成本折算基准**：按 Claude 3.5 Sonnet 定价 $3/1M input tokens 折算。绝对美元数会随模型定价演进浮动，关键在于相对上下文瘦身与开销降幅达 **↓95.7%**。  
> - **样本量与测试集标注**：每个指标均带明确样本规模 $n$（如 12/12 真实跨端调用链、8/8 攻防对抗）。日常良性重构放行率达 **32/32**，误拦截率 Wilson 95% 置信区间上限为 **$\le 10.7\%$**。  
> - **基线客观性说明**：全量投喂为未优化原始代码上下文投喂；传统 RAG 为固定分块嵌入、top-k=10 的标准语义基线。LKIO 的 3-Hop 深层召回依赖 AST 符号引用与跨仓拓扑推理。

<details>
<summary><b>🔬 评测方法与可复现性规范 (Methodology & Reproducibility Specs)</b></summary>

为确保学术严谨与第三方可复现，上述基准的所有模型、分词器与底层参数全部公开：

- **分词器规范 (Tokenizer)**：采用 OpenAI `tiktoken` 标准 `cl100k_base` 编码器统一统计各管线 Token 开销。
- **检索模型 (Embedding)**：采用开源本地轻量模型 `sentence-transformers/all-MiniLM-L6-v2`（向量维度 $d=384$，显存/内存开销约 90MB，极大减轻端侧推理压力）。
- **混合重排引擎 (Hybrid Retrieval)**：
  - 稀疏词法引擎：BM25Okapi ($k_1 = 1.5, b = 0.75$)；
  - 融合算法：Reciprocal Rank Fusion (RRF, $k=60$)，词法与语义权重分别为 $w_{lex}=0.4, w_{sem}=0.6$；相似度截断 $\tau = 0.65$。
- **静态 AST/CST 语法树引擎**：`tree-sitter` (v0.21.3)，覆盖 Java、TypeScript、JavaScript、Vue SFC、Python 等主语言语法。
- **Agent 推理与决策超参数**：
  - 评测中大模型推理采用严格确定性配置：`Temperature = 0.0`，`Top-p = 0.95`，`Max Output Tokens = 4096`；
  - 决策校准采用温度缩放（Temperature Scaling, $T=0.55$），防数值下溢截断常数 $\epsilon = 10^{-4}$。
- **硬件环境与基准平台**：
  - CPU: Intel/AMD 8-Core x64 处理器；
  - RAM: 32 GB DDR5；
  - OS: Windows 11 Enterprise (x64)；
  - Runtime: Python 3.12.10 (CPython)，通过 `uv` 严格环境锁定。
- **被测代码库规模 (三级透明口径)**：
  - **Level 1 (全工程物理文件数)**：`4,899` 个（排除 `.git`、`node_modules`、`dist` 等衍生目录后的工程物理文件）；
  - **Level 2 (核心 AST 语法树索引文件数)**：`3,298` 个（`36.16 MB`，进入 Tree-sitter CST 深度解析的主业务代码）；
  - **Level 3 (冷启动实测基准样本集)**：`1,000` 个（`19.07 MB`，完整提取 26,045 个符号，实测 Wall-Clock 耗时 $10.61\,\text{s}$，内存峰值 $128.94\,\text{MB}$）。
- **长稳压测与快照策略**：
  - 连续 1,000 轮写入与查询 Soak 压测，常驻快照通过滑动窗口（`max_history_snapshots=50`）定额回收，稳态内存净增受控在 $+11.6\,\text{MB}$（彻底消除无界内存泄漏）。
- **完整独立审计报告与机器可读证明**：
  - 机器可读实测指标：[`benchmarks/production_acceptance_rigorous_results.json`](benchmarks/production_acceptance_rigorous_results.json)
  - 完整生产审计底稿：[`docs/benchmarks/production_acceptance_rigorous_report.md`](docs/benchmarks/production_acceptance_rigorous_report.md)

</details>

---

## 🚦 LKIO Status & Gate Matrix

LKIO operates under a foundational quality invariant:

$$\mathbf{Implementation\ Complete \neq Benchmark\ Validated \neq Production\ Gate\ Passed}$$

We strictly separate architectural completion, benchmark validation, and production-scale readiness:

| Subsystem / Stage | Status | Verification & Gate Status |
|---|:---:|---|
| **Stage 0: Baseline & Unified Identity** | `COMPLETE` | ✅ Full namespaced URI identity (`repo://<repo_id>/<path>#<symbol>`), Unified SDK client (`core.sdk.lkio.LKIO`), frozen baseline manifests. |
| **Stage 1: Incremental Indexing & COW Engine** | `BENCHMARK VALIDATED` | ✅ Copy-On-Write atomic snapshots, granular symbol diffs, stale edge pruning, transactional rollback, and an **Independent Oracle** (validating canonical structural subset: `FILE`, `CLASS`, `INTERFACE`, `METHOD`, `CONTAINS`). |
| **Stage 2: Multi-Repo Topology & Contract Inference** | `BENCHMARK VALIDATED` | ✅ Cross-repo identity, REST/RPC contract matching, candidate ranking ($A \to [B: 0.97, C: 0.61]$), ambiguity detection, DTO field lineage, and cycle-safe multi-repo BFS. |
| **Stage 3: MCP Infrastructure (Agent Gateway)** | `BENCHMARK VALIDATED` | ✅ Standard JSON-RPC 2.0 & Stdio transport loop (2024-11-05 tool lifecycle with protocol negotiation for 2025-11-25 and 2026-07-28), 9 read-only tools strictly delegating to LKIO SDK, explicit mutation blocklists, 100 concurrent requests verified. |
| **Stage 4: Agent Refactoring Loop & Governance Gate** | `FRAMEWORK COMPLETE` | ⚠️ 7-step closed-loop refactoring orchestrator & 8-scenario adversarial stress suite. Enforces `Confidence != Permission`. Framework complete; **not claimed production-proven**. |
| **Production Scale Proof** | `PENDING` | ⏳ Monitored and suspended pending large-scale distributed deployments and real-world enterprise load validation. |

---

## 📐 System Architecture

```text
               Target Code Repositories (Multi-Repo)
                                 │
                Continuous COW Incremental Indexing
                (Tree-sitter AST: TS / JS / Java / Vue)
                                 │
                Granular Symbol & Relation Delta Engine
                                 │
             ┌───────────────────┼───────────────────┐
             │                   │                   │
        Code Structural        Git Temporal        Hybrid
        Topology Graph         History Trace      Retrieval
      (Bounded BFS Impact)   (Commit Diffs)     (Vector + BM25)
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 │
                        Unified LKIO SDK
                     (core.sdk.lkio.LKIO)
                                 │
               Model Context Protocol (MCP) Server
                 (JSON-RPC 2.0 / Stdio Transport)
                                 │
             Coding Agents (Cursor / Claude Code / Codex)
                                 │
                Agent Refactoring & Feedback Loop
                                 │
             Automated Tests & Hot Snapshot Re-Index
                                 │
        Production Governance Gate (`Confidence != Permission`)
                                 │
                     Evidence-backed Decision
```

---

## 🔌 Model Context Protocol (MCP) Setup

LKIO exposes a fully compliant Model Context Protocol (MCP) server over standard input/output (`stdio`), implementing the 2024-11-05 tool lifecycle with dynamic protocol version negotiation (supporting `2024-11-05`, `2025-11-25`, and `2026-07-28`). External AI coding agents (Claude Code, Cursor, Codex, Windsurf) can seamlessly query and reason over repository intelligence without raw database access.

### Configuration for Cursor / Claude Code

Add LKIO to your `mcp.json` or `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lkio": {
      "command": "python",
      "args": ["-m", "core.mcp.server"]
    }
  }
}
```

### 9 Read-Only MCP Tools

All tools are read-only and strictly delegate to the `LKIO` SDK with zero direct database bypass:

1. `repo_overview`: Retrieve project summary, languages, active entity counts, and topology health.
2. `list_entities`: Paginate and filter code entities (Classes, Methods, Interfaces, Components).
3. `get_entity_detail`: Fetch complete symbol signatures, source code snippets, and metadata.
4. `search_knowledge`: Hybrid vector + lexical search across symbols, docs, and code.
5. `analyze_impact`: Compute blast radius and affected downstream components via cycle-safe BFS.
6. `evaluate_decision`: Query rule-based and calibrated decision policies with evidence chains.
7. `get_timeline`: Inspect Git commit history, file-level additions/deletions, and authors.
8. `incremental_index`: Hot-sync file modifications into an atomic COW snapshot.
9. `export_graph`: Export structural subgraph nodes and edges in JSON format.

---

## 🛡️ Production Governance & Adversarial Stress Testing

LKIO enforces the inviolable security principle:

$$\mathbf{Confidence \neq Permission}$$

Even if a model exhibits near-perfect confidence ($0.999$), high-risk architectural actions (core payment modules, authorization middleware, framework configuration) **strictly require human sign-off**.

```text
Confidence Score ──> Risk Classification ──> Security Policy ──> Permission Decision
                                                                 (ALLOW / REVIEW / BLOCK)
```

The governance engine is fortified by an **8-scenario adversarial stress suite** (`tests/unit/stage4/test_governance_adversarial_stress.py`):

| Scenario | Adversarial Condition | Defense Policy | Decision Output | Status |
|---|---|---|:---:|:---:|
| `STRESS-001` | High confidence ($0.999$) on critical payment core | `MANDATORY_HUMAN_SIGNOFF` | `REVIEW` | **PASSED** |
| `STRESS-002` | Low confidence ($0.68$) on non-critical logging | `MODERATE_CONFIDENCE_PEER_REVIEW` | `REVIEW` | **PASSED** |
| `STRESS-003` | Benign model claim, but test regression detected | `ZERO_REGRESSION_POLICY` | `BLOCK` | **PASSED** |
| `STRESS-004` | Tests pass, but blast radius spills into critical scope | `CRITICAL_SCOPE_STRICT_BLOCK` | `BLOCK` | **PASSED** |
| `STRESS-OOD` | Out-of-distribution artifact (unrecognized binary plugin) | `OUT_OF_DISTRIBUTION_HUMAN_TRIAGE` | `REVIEW` | **PASSED** |
| `STRESS-006` | Anomalous model output ($\text{NaN}$, negative confidence) | `ANOMALOUS_MODEL_OUTPUT_BLOCK` | `BLOCK` | **PASSED** |
| `STRESS-007` | Insufficient graph evidence (empty citation chains) | `INSUFFICIENT_EVIDENCE_BLOCK` | `BLOCK` | **PASSED** |
| `STRESS-008` | Unregistered / orphan entity targeting | `INCOMPLETE_TOPOLOGY_BLOCK` | `BLOCK` | **PASSED** |

---

## 🔬 LKIO-Bench: 20-Layer Reasoning Benchmark

LKIO comes with an extensive 20-layer benchmark suite validating retrieval, topological graph reasoning, Git temporal states, calibrated decisions, and multi-repo contracts:

- **Layer 1**: Semantic Retrieval MRR & NDCG
- **Layer 2**: Symbol Retrieval Precision & Recall
- **Layer 3**: Dependency Hop-1/Hop-2/Hop-3 Accuracy
- **Layer 4**: Topological Cycle Safety (Self-loops, mutual cycles, cross-cycles)
- **Layer 5**: Shortest-Hop Preservation (Preventing path depth inflation)
- **Layer 6**: Bounded Search Radius & Strict Depth Containment
- **Layer 7**: Git Commit Attribution & Temporal Diff Reconstruction
- **Layer 8**: Historical Architectural State Reconstruction
- **Layer 9**: Direct & Indirect Impact Radius Precision
- **Layer 10**: False-Positive Cross-Module Blast Suppression
- **Layer 11**: Multi-Path Ground-Truth Evidence Accumulation
- **Layer 12**: Cross-Stack Lineage (Vue SFC $\to$ API $\to$ Spring Controller $\to$ DB)
- **Layer 13**: Decision Accuracy & F1 Across 4 Policy Categories
- **Layer 14**: Temperature-Scaling Calibration Ablation (ECE reduced by 60.52%)
- **Layer 15**: 8-Way Architectural System Baseline Ablations
- **Layer 16**: Granular AST Symbol Diff & Signature Change Invariance
- **Layer 17**: Cascade Pruning of Stale Topological Edges
- **Layer 18**: Multi-Repo Ambiguity Detection & Route Candidate Ranking
- **Layer 19**: DTO Field-Level Cross-Stack Semantic Matching
- **Layer 20**: Cycle-Safe Multi-Repo Cross-Project Impact Propagation

```bash
# Execute LKIO-Bench
uv run pytest tests/unit/benchmarks/test_lkio_bench.py -q
```

---

## 🚀 Quick Start & Verification

### 1. Installation

LKIO requires Python 3.12+ and is managed via [`uv`](https://github.com/astral-sh/uv):

```bash
# Clone the repository
git clone https://github.com/xxmasy/lkio.git
cd lkio

# Install dependencies and project console scripts
uv sync
```

### 2. Live Zero-Trust Evidence Verification (11 Gates)

LKIO provides a unified mathematical evidence verification CLI command that computes on-the-fly proofs across 11 verification gates without mockups or hardcoded metrics:

```bash
uv run lkio verify --all
```

Or invoke as a standard Python module:
```bash
uv run python -m core.cli verify --all
```

The 11 verification gates enforce:
- **G01 Runtime & Parsers**: Python $\ge 3.12$ and pinned Tree-sitter parsers (Java, TS, JS).
- **G02 Integrity**: SHA-256 code/dataset checksums against frozen benchmark manifests.
- **G03 Independent Oracle**: Clean-room AST canonical state equivalence proof (`FILE`, `CLASS`, `INTERFACE`, `METHOD`, `CONTAINS`).
- **G04 Retrieval**: Hybrid BM25 + Vector semantic retrieval (Recall@10, MRR) and symbol lookup.
- **G05 Graph Topology**: Cycle-safe BFS, shortest-hop preservation, and multi-tier blast radius F1.
- **G06 Temporal Git**: Commit attribution, symbol evolution, and historical state reconstruction.
- **G07 Multi-Repo & Stack**: Vue $\to$ Pinia $\to$ Axios $\to$ Controller $\to$ Service $\to$ DTO $\to$ Repo chains and cross-repo API contracts.
- **G08 Decision Engine**: Decision accuracy ($\ge 0.85$) and macro-F1 ($\ge 0.75$).
- **G09 Calibration**: Expected Calibration Error reduction via Temperature Scaling ($\Delta\text{ECE} \ge 50\%$).
- **G10 Governance Adversarial**: 8 stress injection attacks (STRESS-001 ~ 008) defending `Confidence != Permission`.
- **G11 MCP Protocol**: MCP 2024-11-05 tool lifecycle, version negotiation, and tool registry.

To output an immutable, machine-readable JSON proof bundle:
```bash
uv run lkio verify --all --json
```

### 3. Run Pytest Test Suite

Verify all 286 unit, integration, and preflight tests:

```bash
uv run pytest tests/unit tests/integration -q
```

### 4. Docker Deployment

LKIO includes multi-stage containerization for both backend and web visualization:

```bash
# Start PostgreSQL with pgvector, FastAPI backend, and Vue web dashboard
docker compose up -d
```

- API Server: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Web Dashboard: `http://localhost:5173`

---

## 📄 License & Academic Rigor

LKIO is open-sourced under the [Apache License 2.0](LICENSE).

LKIO commits to scientific transparency: all benchmark data, baseline comparisons, and gate verifications are reproducible directly from source without reliance on closed APIs or proprietary weights.
