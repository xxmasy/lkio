# LKIO: Open-source Repository Intelligence & Code Reasoning Engine

[ **English** | [简体中文](README_zh.md) ]

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![LKIO-Bench](https://img.shields.io/badge/LKIO--Bench-20%20Layers%20Passed-brightgreen)](#-lkio-bench-20-layer-reasoning-benchmark)
[![Test Suite](https://img.shields.io/badge/Tests-243%20Passed-success)](#-quick-start--verification)

> **Mission**: **LKIO = Open-source Repository Intelligence & Code Reasoning Engine**  
> LKIO provides an infrastructure-grade repository intelligence layer for autonomous coding agents (Claude Code, Cursor, Codex, etc.). It combines fine-grained Tree-sitter AST symbol indexing, cross-repository dependency topology, Git temporal reasoning, hybrid retrieval, and safety governance gates to enable deterministic, evidence-backed code reasoning.
> 
> **Origin & Provenance (AI-Native Production Heritage)**:  
> LKIO was not conceived in an academic vacuum or benchmarked against toy codebases. The target evaluation testbed is a **complete, full-scale production software system** (spanning Vue 3 SFC frontend, Pinia, Axios, Spring Boot microservices, DTO data lineage, and multi-repo RPC contracts). **Continuously developed since October 2025, 100% of this production codebase was written entirely by AI.**  
> It was precisely in this pure AI-driven software engineering environment that the foundational limits of coding agents were uncovered: context explosion, hallucinated cross-stack linkages, silent downstream breaks, and lack of repository topology awareness. **LKIO was forged directly out of the real-world operational necessities of maintaining and scaling a 100% AI-written production codebase.**

---

## ⚡ Why LKIO: Empirical Comparison

| Evaluation Dimension | Full Context Ingestion | Conventional Chunk RAG | LKIO (AST + Graph + Hybrid) | Key Architectural Mechanism |
|---|:---:|:---:|:---:|---|
| **Context & Token Efficiency** | | | | |
| ├─ Mean Task Tokens | 12,698 | 4,266 | **545** (↓95.7%) | Surgical AST symbol extraction vs raw files |
| ├─ P95 Peak Tokens | 24,012 | 5,000 | **590** (↓97.5%) | Bounded topological subgraph vs dumping entire files |
| ├─ Cost per 1,000 Agent Tasks [^cost] | $38.09 | $12.80 | **$1.64** (↓95.7%) | Sub-1k prompt budget preserves LLM window |
| **Retrieval & Topological Precision** | | | | |
| ├─ Cross-Stack E2E Lineage Recall ($n=12$) | — | 0/12 (0.0%) | **12/12 (100.0%)** [^ci1] | Vue SFC → Pinia → Axios → Controller → Service → DB |
| ├─ Call-Chain Precision (0 Spurious Hops, $n=72$) | — | 18.2% | **72/72 (100.0%)** [^ci2] | Deterministic AST symbol references eliminate hallucinations |
| ├─ 3-Hop Deep Traversal Recall | 10% | 0% | **100%*** | Cycle-safe BFS graph traversal prevents hop truncation |
| ├─ Noise Distractor Rejection ($n=46$) | 0.0% | 32.6% | **46/46 (100.0%)** [^ci3] | Strict entity URI filtering eliminates irrelevant matches |
| **System Latency & Responsiveness** | | | | |
| ├─ Write-to-Visibility Latency (Per-save) | — | ~30s (full re-index) | **56.4ms** | 50ms FS debounce buffer + 0.19ms COW pipeline |
| ├─ Impact Traversal Latency (Depth=2, 400 nodes) | — | — | **0.121ms** (121.5μs) | In-memory adjacency traversal, P95=0.306ms |
| ├─ Cold-Start Parsing Throughput | — | ~15 files/s | **94.3 files/s** (1.8 MB/s) | Tree-sitter CST parsing (1,000 files in 10.6s) |
| **Safety Governance & Calibration** | | | | |
| ├─ Expected Calibration Error (ECE, $n=120$) | 0.2300 | 0.1850 | **0.0469** (↓74.6%) | Temperature scaling prevents overconfident hallucinations |
| ├─ Adversarial Attack Defense ($n=8$) | 0/8 (0%) | 0/8 (0%) | **8/8 (100.0%)** [^ci4] | Enforces `Confidence != Permission` on payment/auth |
| ├─ Benign Refactoring Pass Rate ($n=32$) | — | — | **32/32 (100.0%)** [^ci5] | Overblocking rate bounded under $\le 10.7\%$ (95% CI) |
| ├─ 1,000-Cycle Soak Heap Overhead | O(N) leak | O(N) leak | **+11.6 MB** (Bounded) | Sliding-window snapshot retention (Ring Buffer = 50) |

[^cost]: Cost calculated using Claude 3.5 Sonnet standard pricing ($3/1M input tokens). Absolute dollar values fluctuate with provider pricing; the primary invariant is the **95.7% token reduction**.  
[^ci1]: Wilson 95% Confidence Interval: $[75.8\%, 100.0\%]$ across 12 full-stack real production traces.  
[^ci2]: Wilson 95% Confidence Interval: $[94.9\%, 100.0\%]$ with zero spurious/hallucinated hops across 72 links.  
[^ci3]: Wilson 95% Confidence Interval: $[92.3\%, 100.0\%]$ rejecting 46 cross-module distractor candidates.  
[^ci4]: Wilson 95% Confidence Interval: $[67.6\%, 100.0\%]$ intercepting 8 adversarial security condition injections.  
[^ci5]: Wilson 95% Confidence Interval: $[89.3\%, 100.0\%]$ allowing 32 standard daily developer operations (renaming, extracts, CSS, i18n, bumps). Mis-interception (false-positive) rate Wilson 95% upper bound: $\le 10.7\%$.

<details>
<summary><b>🔬 Methodology & Reproducibility Specifications</b></summary>

To guarantee scientific transparency and third-party reproducibility, all evaluation models, tokenizers, and system parameters are frozen and documented:

- **Tokenizer Standard**: Evaluated using OpenAI `tiktoken` with standard `cl100k_base` encoding for uniform cross-pipeline token accounting.
- **Embedding Model**: Local lightweight open-source `sentence-transformers/all-MiniLM-L6-v2` (dimension $d=384$, memory footprint ~90MB, enabling millisecond CPU execution without external API overhead).
- **Hybrid Retrieval & RRF Fusion**:
  - Sparse lexical retrieval: BM25Okapi ($k_1 = 1.5, b = 0.75$).
  - Rank fusion: Reciprocal Rank Fusion (RRF, $k=60$) combining lexical and dense semantic rankings with weights $w_{lex}=0.4, w_{sem}=0.6$; similarity cutoff threshold $\tau = 0.65$
- **Static CST/AST Parsing Engine**: `tree-sitter` (v0.21.3) with language grammars covering Java, TypeScript, JavaScript, Vue SFC, and Python.
- **Agent Reasoning & Governance Hyperparameters**:
  - Deterministic model evaluation: `Temperature = 0.0`, `Top-p = 0.95`, `Max Output Tokens = 4096`.
  - Calibration: Temperature Scaling ($T=0.55$) with numerical underflow clipping constant $\epsilon = 10^{-4}$.
- **Hardware & Benchmark Platform**:
  - CPU: Intel/AMD 8-Core x64 processor.
  - RAM: 32 GB DDR5.
  - OS: Windows 11 Enterprise (x64).
  - Runtime: Python 3.12.10 (CPython), locked with `uv`.
- **Target Repository Scale (3-Tier Transparent Taxonomy)**:
  - **Level 1 (Total Project Files)**: `4,899` files (raw filesystem scan excluding `.git`, `node_modules`, `dist`, `.venv`).
  - **Level 2 (AST-Indexable Source Code)**: `3,298` files (`36.16 MB`, code actively parsed by Tree-sitter CSTs: `.java`, `.vue`, `.ts`, `.js`).
  - **Level 3 (Cold-Start Empirical Active Set)**: `1,000` files (`19.07 MB`, 26,045 AST symbols parsed in $10.61\,\text{s}$ wall-clock time, peak RSS $128.94\,\text{MB}$).
- **Long-Term Soak Stability & Retention Policy**:
  - 1,000 continuous incremental update-query cycles; snapshot heap memory bounded by sliding window (`max_history_snapshots=50`) yielding $+11.6\,\text{MB}$ steady-state growth (eliminating unbounded memory leaks).
- **Full Empirical Reports & Audit Artifacts**:
  - Machine-readable benchmark results: [`benchmarks/production_acceptance_rigorous_results.json`](benchmarks/production_acceptance_rigorous_results.json)
  - Full production audit report: [`docs/benchmarks/production_acceptance_rigorous_report.md`](docs/benchmarks/production_acceptance_rigorous_report.md)

</details>

---

## 🐶 Real-World Production Dogfooding & Token Compression Audit

To advance beyond synthetic benchmarks, LKIO was deployed into **active daily developer dogfooding** on a live commercial multi-repo codebase spanning a **Vue 3 SFC frontend** (`market-bi`) and a **Spring Boot microservices backend** (`haha-market-cursor`).

Instead of piping thousands of raw Git diff tokens into Cursor's Cloud LLM (Claude 3.5 Sonnet / GPT-4o), LKIO operates as an **Edge-Local Subagent** backed by local Ollama (`qwen2.5vl:7b`). It intercepts incoming remote GitLab commits via zero-risk read-only fetches, executes AST impact filtering, and synthesizes 100-word high-density briefings directly into IDE rule context (`.cursor/rules/team-updates.mdc`).

### 📊 Empirical Dogfooding Performance (Real GitLab Traffic)

| Evaluation Dimension | Cloud-LLM Direct Ingestion | LKIO Edge-Local Subagent | Empirical Improvement |
| :--- | :---: | :---: | :---: |
| **Monitored Scope** | Multi-Repo (Frontend + Backend) | Multi-Repo (Frontend + Backend) | Commercial Full-Stack System |
| **Observation Window** | Multi-Day Active Team Iteration | Multi-Day Active Team Iteration | Verified 2026-09-30 ～ 2026-10-06 |
| **Incoming Commits Intercepted** | 89 commits (84 backend + 5 frontend) | 89 commits (84 backend + 5 frontend) | Multiple active team developers |
| **Gross Cloud Input Tokens Consumed** | 11,588 tokens | **310 tokens** | **↓ 97.32% Cloud Token Compression** |
| **Net Cloud Tokens Saved** | 0 tokens | **+11,278 tokens** | Saved context window budget |
| **Subagent Inference Latency** | Network-bound roundtrips | **1.0s ～ 5.3s** (Local Ollama) | Edge execution, zero cloud latency |
| **Marginal API Cost** | ~$0.0348 (Sonnet standard pricing) | **$0.0000** | **100% Free Edge Compute** |
| **Working Tree Collision / Dirty Rate** | High (risk of dirtying uncommitted work) | **0.0% (Zero-Dirtying)** | Isolated read-only `git fetch` |

### 📋 Chronological Audit Log (From Immutable Local Ledger)

The table below reflects real, unedited execution entries logged into the LKIO token audit ledger:

| Timestamp | Trigger Source | Target Repository | Scope (Commits/Files) | Raw Tokens Avoided | Delivered Tokens | Net Tokens Saved | Compression Ratio | Edge Model & Latency |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `10-06 13:58` | `DAEMON_WATCHER` | `backend` | 84 commits / 84 files | 3,623 | 58 | **+3,565** | **98.40%** | `qwen2.5vl:7b` (5,341ms) |
| `10-06 13:58` | `DAEMON_WATCHER` | `frontend` | 5 commits / 19 files | 976 | 56 | **+920** | **94.26%** | `deterministic_fallback` |
| `09-30 15:51` | `CURSOR_MCP` | `backend` | 22 commits / 22 files | 992 | 49 | **+943** | **95.06%** | `qwen2.5vl:7b` (1,329ms) |
| `09-30 15:51` | `CURSOR_MCP` | `backend` | 22 commits / 22 files | 992 | 40 | **+952** | **95.97%** | `qwen2.5vl:7b` (1,014ms) |
| `09-30 15:51` | `DAEMON_WATCHER` | `backend` | 22 commits / 84 files | 4,852 | 50 | **+4,802** | **98.97%** | `qwen2.5vl:7b` (1,286ms) |

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
| **Stage 3: MCP Infrastructure (Agent Gateway)** | `BENCHMARK VALIDATED` | ✅ Standard JSON-RPC 2.0 & Stdio transport loop (supporting 2024-11-05, 2025-11-25, 2026-07-28), 10 read-only tools strictly delegating to LKIO SDK, explicit mutation blocklists, 100 concurrent requests verified. |
| **Stage 4: Agent Refactoring Loop & Governance Gate** | `BENCHMARK VALIDATED` | ✅ 7-step closed-loop refactoring orchestrator, 8/8 adversarial attack defense (Wilson 95% CI: $[67.6\%, 100.0\%]$), 32/32 benign refactoring pass rate (overblock $\le 10.7\%$), dual-Oracle verification. Enforces `Confidence != Permission`. |
| **Production Scale Proof** | `PRODUCTION VALIDATED` | ✅ Multi-day commercial dogfooding completed across Vue 3 + Spring Boot repositories. Intercepted 89 incoming remote commits, achieved **97.32% Cloud Token compression** via Local-LLM edge subagents with 0.0% code dirtying. |

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
      "args": ["run_mcp.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### 10 Read-Only MCP Tools

All tools are strictly read-only and delegate directly to the `LKIO` SDK and edge subagents with zero direct database bypass:

1. `lkio_search`: Hybrid semantic and lexical code retrieval across repository files.
2. `lkio_symbol`: Locates symbol AST definitions (classes, methods, DTOs, interfaces).
3. `lkio_references`: Queries inbound and outbound references for an entity URI across repo boundaries.
4. `lkio_dependencies`: Retrieves bounded dependency subgraph rooted at the given seed entity.
5. `lkio_impact`: Computes cycle-safe shortest-hop impact blast radius for planned change seeds.
6. `lkio_history`: Traces Git commit evolution and symbol lifecycle changes.
7. `lkio_snapshot`: Reconstructs historical repository graph state at a specified commit.
8. `lkio_explain`: Explains architectural role, boundary relations, and business intent of an entity.
9. `lkio_decision`: Executes calibrated decision gate evaluation backed by graph and statistical evidence.
10. `lkio_remote_commits`: Monitors remote GitLab commits, detects branch divergence, and delivers edge-distilled briefings with 97%+ token compression.

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
