# LKIO: Open-source Repository Intelligence & Code Reasoning Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Benchmarks](https://img.shields.io/badge/LKIO--Bench-v1.0_Passing-brightgreen)](docs/benchmarks/lkio_bench_v1_report.md)
[![Tests](https://img.shields.io/badge/Tests-207_Passed-success)](tests/)

> **定位声明**：**LKIO = Open-source Repository Intelligence / Code Reasoning Engine**  
> LKIO 并非“已经彻底解决 Repository Intelligence”的终极黑盒，而是一个**将结构化代码语法树（AST）、跨技术栈拓扑依赖图、Git 时序演进、以及后验校准决策机制结合的确定性推理引擎**。

---

## 🎯 核心原则：从“宣称能做什么”到“公开 Benchmark 自己跑”

任何代码智能系统最容易陷入的误区是自吹自擂。LKIO 采取彻底不同的开源策略：**将完整可复现的评测套件 [LKIO-Bench](benchmarks/lkio_bench/) 与系统源码一同开源**。

```
git clone https://github.com/xxmasy/lkio.git
      ↓
uv run pytest tests/unit/benchmarks/test_lkio_bench.py
      ↓
换上你自己的 Retriever / 图遍历算法 / 大语言模型
      ↓
跑同一套 15 层基准测试并生成报告
      ↓
客观对比优劣与边界
```

### ⚠️ 客观局限性与泛化边界声明 (Scientific Honesty Disclaimer)

> **重要提示**：  
> **LKIO 的当前 benchmark 主要验证结构化 repository reasoning 能力，不代表跨项目、跨组织、跨领域的生产泛化性能。Decision layer 的结果尤其受到训练/校准数据规模和分布漂移（Distribution Drift）影响。**

---

## 📐 系统架构全景

```text
LKIO
├── AST / Symbol Index          # 树分析器 (Tree-sitter TS/Java/Vue SFC)
├── Dependency Graph            # 跨栈依赖图 (Cross-Stack: Vue ↔ API ↔ Spring ↔ DB)
├── Bounded Impact Analysis     # 有界无环最短路径影响面分析器 (Cycle-Safe BFS)
├── Git Temporal Reasoning      # Git 提交时序演进与快照重构
├── Hybrid Retrieval            # 融合 AST 符号与倒排索引的高阶检索
├── Decision Engine             # 可插拔决策引擎 (Pluggable Decision Backends)
│   ├── Laya                    # 默认参考实现 (Apache 2.0 开源结构化决策模型)
│   ├── LLM                     # 外部大模型适配层 (OpenAI / Anthropic / Local API)
│   ├── LocalClassifier         # 轻量级本地规则与统计分类器
│   └── CustomModel             # 用户自定义可扩展决策函数
├── Confidence / Calibration    # 温度缩放后验校准 (ECE 优化与防过拟合)
└── LKIO-Bench                  # 15 层标准化评测集与 8 大基线消融套件
```

---

## 🔌 解耦的决策后端架构 (Pluggable Decision Engine)

LKIO 拒绝将系统与任何单一模型深度绑定。**LKIO 是代码推理与知识计算系统，而 Laya 是当前推荐的最佳适配决策后端**。系统接口设计为完全可插拔：

```text
DecisionEngine (Protocol)
├── Laya (LayaDecisionBackend, Apache 2.0 open-weight model)
├── LLM (LLMDecisionBackend, gpt-4o / Claude / DeepSeek)
├── LocalClassifier (LocalClassifierDecisionBackend, 规则/轻量模型)
└── CustomModel (CustomDecisionBackend, 用户函数即插即用)
```

### 切换后端示例

```python
from core.decision import DecisionEngineFactory

# 1. 使用默认开箱即用的 Laya 结构化决策后端
laya_engine = DecisionEngineFactory.create("laya")

# 2. 切换为外部 LLM 决策后端
llm_engine = DecisionEngineFactory.create("llm", model_name="gpt-4o")

# 3. 注入完全自定义的决策逻辑
def my_custom_agent(request):
    # 自定义仲裁
    ...

custom_engine = DecisionEngineFactory.create("custom", handler=my_custom_agent)
```

---

## 📊 LKIO-Bench v1.0 评测结果与基线消融

详细评测大表记录于 [docs/benchmarks/lkio_bench_v1_report.md](docs/benchmarks/lkio_bench_v1_report.md)。

| 架构基线 (Baseline System) | Recall@10 | Impact F1 | Temporal Acc | Decision Acc | Macro-F1 | ECE (校准误差) | 核心机制特征 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **1. Vector RAG** | 0.8250 | 0.0000 | 0.0000 | 0.6500 | 0.5200 | 0.2150 | 纯语义向量相似度匹配，无法进行图遍历与 Git 历史追踪 |
| **2. BM25** | 0.8750 | 0.0000 | 0.0000 | 0.6000 | 0.4800 | 0.2300 | 纯词法 Token 倒排索引，无上下文结构感知能力 |
| **3. BM25 + Vector** | 0.9250 | 0.0000 | 0.0000 | 0.7000 | 0.5900 | 0.1850 | 词法与向量简单交错融合，缺少精确语法树与拓扑依赖 |
| **4. Hybrid + Reranker** | **0.9500** | 0.0000 | 0.0000 | 0.7500 | 0.6400 | 0.1620 | 交叉编码器重排序（文本召回极强，但无推理与决策能力） |
| **5. Graph only** | 0.2500 | 0.6667 | 0.0000 | 0.6000 | 0.5000 | 0.2400 | 纯拓扑遍历（缺失语义引导导致冷启动与孤岛节点失联） |
| **6. AST + Graph** | 0.8750 | 1.0000 | 0.0000 | 0.7800 | 0.6800 | 0.1550 | 结构化语法树+有界最短路径拓扑（精准影响分析，但无时序） |
| **7. AST + Graph + Git** | 0.9000 | 1.0000 | 1.0000 | 0.8800 | 0.7500 | 0.1188 | 引入 Commit 时序演进分析，但决策置信度未经后验校准 |
| **8. Full LKIO** | 0.9250 | **1.0000** | **1.0000** | **0.9167** | **0.8000** | **0.0469** | **全栈融合 + 环安全有界最短路径 + 温度缩放自适应校准** |

### 🛑 真实劣势与诚实保留说明 (Honest Loss Disclosures)

- **劣势 1：纯文档段落召回 (Recall@10) 劣于 `Hybrid + Reranker`**  
  `Hybrid + Reranker` 达到 **0.9500**，高于 LKIO 的 **0.9250**。LKIO 在混合检索时主动抑制对纯自然语言余弦相似度的过拟合，并引入语法树符号与图拓扑惩罚，因此在纯文本相似度排名中略低。
- **劣势 2：纯 Token 查找的延迟劣于 `BM25`**  
  纯 `BM25` 针对单一符号的精确字符串匹配具有纳秒级开销（$<1\text{ms}$），而 LKIO 执行端到端推理必须消耗解析拓扑与最短路径松弛的计算量。

---

## 🚀 快速上手 (Quick Start)

### 1. 安装依赖

推荐使用 [`uv`](https://github.com/astral-sh/uv) 极速安装环境：

```bash
git clone https://github.com/xxmasy/lkio.git
cd lkio

# 创建虚拟环境并同步依赖
uv sync
```

### 2. 运行完整测试套件

```bash
# 验证 200+ 单元测试与端到端集成测试
uv run pytest tests/unit tests/integration -q
```

### 3. 一键运行 LKIO-Bench 评测套件并输出报告

```bash
# 运行 15 层基准评测并生成消融大表
uv run python -c "from benchmarks.lkio_bench.runner import LKIOBenchRunner; r = LKIOBenchRunner(); r.run_all_layers(); print('Report generated at docs/benchmarks/lkio_bench_v1_report.md')"
```

---

## 🗂️ 15 层评测维度速查

1. **Semantic Retrieval**: 针对自然语言业务语义检索准确度与 MRR / NDCG。
2. **Symbol Retrieval (AST)**: 基于语法树的定义、类、函数和行级精准召回。
3. **Dependency Retrieval**: 跨模块、跨前后端的 1-hop、2-hop、3-hop 依赖感知。
4. **Cycle Safety**: 验证自环、互环、多入度交叉环与嵌套重入下的安全终止与 0 死循环。
5. **Shortest-Hop Preservation**: 验证多路径触达下严格保持最短深度不被较深路径污染。
6. **Depth Boundary**: 有界搜索的硬截断与零超界泄露。
7. **Temporal Git Reasoning**: 提交历史归因与行级变更时序分析。
8. **Historical State Reconstruction**: 基于特定 Commit 的历史架构拓扑快照重构。
9. **Impact Analysis**: 变更直接（DIRECT）、间接（INDIRECT）与潜在（POTENTIAL）影响面划分。
10. **False Positive Suppression**: 抑制内部局部重构引发的跨模块假阳性过度传播。
11. **Multi-Path Evidence**: 跨路径证据链完整沉淀与溯源。
12. **Cross-Frontend/Backend Reasoning**: 穿透 Vue SFC $\rightarrow$ Pinia $\rightarrow$ Axios $\rightarrow$ Spring Controller $\rightarrow$ Service $\rightarrow$ DB 表。
13. **Decision Layer**: 四类关键决策（变更影响、证据充要性、查询路由、操作门禁）准确率与 F1。
14. **Calibration Ablation**: 温度缩放参数仅在 Calibration 集拟合，验证 ECE 降低 60.52%。
15. **Ablation Study**: 8 大系统基准全景对比。

---

## 📄 开源许可证

本项目基于 [Apache License 2.0](LICENSE) 开源。欢迎社区基于 LKIO-Bench 接入新的代码分析器与决策模型并提交评测对比。
