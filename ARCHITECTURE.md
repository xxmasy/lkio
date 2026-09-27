# LKIO System Architecture & Governance Specification (ARCHITECTURE.md)

> **Role**: Open-source Repository Intelligence & Code Reasoning Engine  
> **Core Quality Invariant**: `Implementation Complete ≠ Benchmark Validated ≠ Production Gate Passed`

---

## 1. Architectural Overview

LKIO provides a continuous repository intelligence and code reasoning layer for autonomous coding agents (Claude Code, Cursor, Codex, etc.). It continuously parses codebases into fine-grained AST symbols, resolves call and dependency relations, tracks historical Git diffs, and enforces safety governance gates.

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
Code Structural Graph  Git Temporal History  Hybrid Retrieval
 (Bounded Impact BFS)   (Commit / Diffs)    (Vector + Lexical)
     │                   │                   │
     └───────────────────┼───────────────────┘
                         │
                  Unified LKIO SDK
                         │
          Model Context Protocol (MCP) Server
          (Stdio / JSON-RPC 2.0 Transport)
                         │
       Coding Agents (Cursor / Claude Code / Codex)
                         │
          Agent Refactoring & Feedback Loop
                         │
          Safety & Governance Gate (`Confidence != Permission`)
```

---

## 2. Core Subsystems

### 2.1 Incremental Indexing & COW Snapshot Engine (`core/state/`, `core/indexing/`)
- **Copy-On-Write (COW) Snapshots**: Atomic state versioning guarantees that read-only queries are never blocked during indexing.
- **Granular Symbol Diffing**: AST-level symbol signatures and hashes are compared per file change, pruning stale edges automatically.
- **Independent Oracle (`core/indexing/independent_oracle.py`)**: Ground-truth validation independently extracts canonical AST symbols directly from source text without relying on delta pipelines.

### 2.2 Multi-Repo Topology & Ambiguity Detection (`core/multirepo/`)
- **Namespaced URI Identity**: All symbols adhere to `repo://<repo_id>/<relative_path>#<symbol_name>`.
- **Contract & Route Matching**: Automatically maps REST/RPC endpoints across frontend and backend boundaries.
- **Ambiguity Detection**: Ranks competing service candidates with confidence scoring and penalizes legacy/mock endpoints.
- **Bounded Impact Analysis**: Cycle-safe BFS traverses dependency and call chains up to configurable max depths.

### 2.3 Model Context Protocol (MCP) Infrastructure (`core/mcp/`)
- **JSON-RPC 2.0 & Stdio Transport**: Standard MCP compliance for direct integration into Cursor, Claude Code, and terminal agents.
- **9 Read-Only Intelligence Tools**: `repo_overview`, `list_entities`, `get_entity_detail`, `search_knowledge`, `analyze_impact`, `evaluate_decision`, `get_timeline`, `incremental_index`, `export_graph`.
- **Mutation Safety**: Explicit blocklists prevent unauthorized write operations through the MCP channel.

### 2.4 Agent Closed Loop & Safety Governance (`core/agent_loop/`)
- **7-Stage Refactoring Lifecycle**:
  `1. Explore -> 2. Pre-change Impact -> 3. Diff Detection -> 4. Automated Tests -> 5. Hot Re-index -> 6. Topology Validation -> 7. Governance Gate`
- **Governance Invariant**: `Confidence != Permission`. High model confidence never overrides human review requirements on high-risk, critical-scope components.
- **Adversarial Hardening**: Defends against zero regressions, out-of-distribution code, corrupted ASTs, and NaN model outputs.

---

## 3. Technology Stack

- **Runtime**: Python 3.12+ (managed via `uv`), FastAPI, SQLAlchemy 2.x, Alembic, `psycopg[binary]`
- **Storage Layer**: PostgreSQL 18+ with `pgvector` (vector similarity search)
- **Syntax Parsing**: Multi-language Tree-sitter (`tree-sitter`, TS, JS, Java) & SFC Block Slicer (Vue 3)
- **Embedding & Decision**: ModernBERT & BAAI/bge-m3 compatible vector pipelines
- **Testing & Benchmarks**: Pytest suite (240+ tests) & LKIO-Bench (20 validation layers)

---

## 4. Fundamental Invariants & Safety Constraints

1. **Source Repository Read-Only Invariance**: Target repositories inspected by LKIO are strictly read-only. Zero working-tree modifications occur during indexing or analysis.
2. **Git Subprocess Standard**: Git operations invoke the standard `git` CLI via subprocess. Direct deserialization of `.git` binary objects is prohibited.
3. **Sensitive File Quarantine**: Secrets, credentials, private keys (`*.pem`, `*.key`), `.env` files, and authentication tokens are quarantined and never indexed.
4. **Identity Determinism**: Symbols and relations must have reproducible identifiers across re-indexing cycles.
5. **Separation of Proof**: `Implementation Complete` must not be equated with `Benchmark Validated`, and benchmark passing must not be equated with `Production Gate Passed`.
