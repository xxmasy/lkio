# LKIO: Open-source Repository Intelligence & Code Reasoning Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![LKIO-Bench](https://img.shields.io/badge/LKIO--Bench-20%20Layers%20Passed-brightgreen)](#-lkio-bench-20-layer-reasoning-benchmark)
[![Test Suite](https://img.shields.io/badge/Tests-243%20Passed-success)](#-quick-start--verification)

> **Mission**: **LKIO = Open-source Repository Intelligence & Code Reasoning Engine**  
> LKIO provides an infrastructure-grade repository intelligence layer for autonomous coding agents (Claude Code, Cursor, Codex, etc.). It combines fine-grained Tree-sitter AST symbol indexing, cross-repository dependency topology, Git temporal reasoning, hybrid retrieval, and safety governance gates to enable deterministic, evidence-backed code reasoning.

---

## 🚦 LKIO Status & Gate Matrix

LKIO operates under a foundational quality invariant:

$$\mathbf{Implementation\ Complete \neq Benchmark\ Validated \neq Production\ Gate\ Passed}$$

We strictly separate architectural completion, benchmark validation, and production-scale readiness:

| Subsystem / Stage | Status | Verification & Gate Status |
|---|:---:|---|
| **Stage 0: Baseline & Unified Identity** | `COMPLETE` | ✅ Full namespaced URI identity (`repo://<repo_id>/<path>#<symbol>`), Unified SDK client (`core.sdk.lkio.LKIO`), frozen baseline manifests. |
| **Stage 1: Incremental Indexing & COW Engine** | `BENCHMARK VALIDATED` | ✅ Copy-On-Write atomic snapshots, granular symbol diffs, stale edge pruning, transactional rollback, and an **Independent Oracle** direct-from-source verifier. |
| **Stage 2: Multi-Repo Topology & Contract Inference** | `BENCHMARK VALIDATED` | ✅ Cross-repo identity, REST/RPC contract matching, candidate ranking ($A \to [B: 0.97, C: 0.61]$), ambiguity detection, DTO field lineage, and cycle-safe multi-repo BFS. |
| **Stage 3: MCP Infrastructure (Agent Gateway)** | `BENCHMARK VALIDATED` | ✅ Standard JSON-RPC 2.0 & Stdio transport loop, 9 read-only tools strictly delegating to LKIO SDK, explicit mutation blocklists, 100 concurrent requests verified. |
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

LKIO exposes a fully compliant Model Context Protocol (MCP) server over standard input/output (`stdio`), allowing agents like Cursor, Claude Code, and Windsurf to directly invoke repository intelligence.

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

LKIO is powered by Python 3.12+ and managed via [`uv`](https://github.com/astral-sh/uv):

```bash
# Clone the repository
git clone https://github.com/xxmasy/lkio.git
cd lkio

# Install dependencies in isolated virtualenv
uv sync
```

### 2. Run Test Suite

Verify all 240+ unit and integration tests:

```bash
uv run pytest tests/unit tests/integration -q
```

### 3. Generate Machine-Verifiable Gate Audit Records

```bash
uv run python scripts/generate_audit_records.py
```

This generates `benchmarks/gate_audit_records.json`, capturing immutable cryptographic hashes, Git commit SHAs, command execution timestamps, exit codes, and stdout proofs.

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
