# LKIO: 开源代码库智能与代码推理基础设施引擎

[ [English](README.md) | **简体中文** ]

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![LKIO-Bench](https://img.shields.io/badge/LKIO--Bench-20%20Layers%20Passed-brightgreen)](#-lkio-bench-20-层代码推理评测基准)
[![Test Suite](https://img.shields.io/badge/Tests-243%20Passed-success)](#-快速启动与验证)

> **定位与使命**: **LKIO = 开源代码库智能（Repository Intelligence）与代码推理引擎**  
> LKIO 专为自主编程智能体（Claude Code、Cursor、Codex 等）提供基础设施级的代码库智能事实层。它将细粒度 Tree-sitter AST 语法树符号索引、跨仓库依赖拓扑图、Git 时间演化溯源、混合检索及安全治理门禁深度融为一体，赋予编码智能体可溯源、有事实支撑的确定性代码推理能力。

---

## ⚡ 为什么选择 LKIO：量化实测对比

| 评测维度 (Evaluation Dimension) | 全量投喂 (Full Context) | 传统分块 RAG (Chunk RAG) | LKIO (AST + 拓扑图 + 混合检索) | 核心架构机制优势 |
|---|:---:|:---:|:---:|---|
| **上下文与 Token 效率** | | | | |
| ├─ 任务 Token 均值 | 12,698 | 4,266 | **545** (↓95.7%) | 手术刀式 AST 符号按需提取，杜绝整文件投喂 |
| ├─ P95 Token 峰值 | 24,012 | 5,000 | **590** (↓97.5%) | 拓扑子图有界截断，杜绝无界上下文爆炸 |
| ├─ 千次任务成本 [^cost] | $38.09 | $12.80 | **$1.64** (↓95.7%) | Sub-1k Token 超低预算，最大化保留 LLM 推理窗口 |
| **检索与跨栈拓扑精度** | | | | |
| ├─ 跨栈端到端链路召回率 ($n=12$) | — | 0/12 (0.0%) | **12/12 (100.0%)** [^ci1] | 完整穿透 Vue SFC → Pinia → Axios → Controller → Service → DB |
| ├─ 调用链跳转精确率 (零虚假跳转, $n=72$) | — | 18.2% | **72/72 (100.0%)** [^ci2] | 确定性 AST 符号引用，彻底消除大模型幻觉链路 |
| ├─ 3-Hop 深层拓扑召回率 | 10% | 0% | **100%*** | 环路安全 BFS 图遍历，杜绝深层依赖被粗暴丢弃 |
| ├─ 跨模块噪音干扰项排斥率 ($n=46$) | 0.0% | 32.6% | **46/46 (100.0%)** [^ci3] | 严格全局 URI 命名空间过滤无关候选 |
| **系统延迟与响应速度** | | | | |
| ├─ 磁盘写入到对外可见延迟 (单次保存) | — | ~30s (全量重建) | **56.4ms** | 50ms 文件系统防抖缓冲 + 0.19ms COW 内存增量管线 |
| ├─ 影响面分析耗时 (深度 2，400 节点图) | — | — | **0.121ms** (121.5μs) | 纯内存邻接表遍历，P95 仅 0.306ms |
| ├─ 冷启动语法解析吞吐量 | — | ~15 文件/秒 | **94.3 文件/秒** (1.8 MB/s) | 单核 Tree-sitter CST 深度解析（1,000 文件 10.6s） |
| **安全治理与模型校准** | | | | |
| ├─ 预期校准误差 (ECE, $n=120$) | 0.2300 | 0.1850 | **0.0469** (↓74.6%) | 温度缩放校准，抑制模型盲目自信导致的盲目提交 |
| ├─ 高危对抗场景绝对防御率 ($n=8$) | 0/8 (0%) | 0/8 (0%) | **8/8 (100.0%)** [^ci4] | 严格落实 `Confidence != Permission`，高危操作强制人工确认 |
| ├─ 日常良性开发放行率 ($n=32$) | — | — | **32/32 (100.0%)** [^ci5] | 误拦截（卡正常开发）Wilson 95% 置信上限严格 $\le 10.7\%$ |
| ├─ 1,000 轮连续长稳堆内存增长 | O(N) 泄漏 | O(N) 泄漏 | **+11.6 MB** (有界收敛) | 滑动窗口快照保留策略（容量 50），杜绝长期常驻慢泄漏 |

[^cost]: 成本按 Claude 3.5 Sonnet 定价 $3/1M input tokens 折算。绝对美元数会随模型定价浮动，核心在于相对上下文瘦身与开销降幅达 **↓95.7%**。  
[^ci1]: 12 条跨栈端到端真实业务链路，Wilson 95% 置信区间：$[75.8\%, 100.0\%]$。  
[^ci2]: 72 个真实调用跳转点，零虚假/冗余跳转（0 Spurious Hops），Wilson 95% 置信区间：$[94.9\%, 100.0\%]$。  
[^ci3]: 排斥 46 个跨模块同名同路径干扰候选项，Wilson 95% 置信区间：$[92.3\%, 100.0\%]$。  
[^ci4]: 拦截 8 类高危安全注入攻击（核心支付越权、权限绕过、单测退化伪装等），Wilson 95% 置信区间：$[67.6\%, 100.0\%]$。  
[^ci5]: 充分测试 32 项日常良性操作（变量更名、提取函数、Tailwind 样式、i18n 文案、补丁升级等），放行率 32/32，Wilson 95% 误拦截上限严格受控在 $\le 10.7\%$。

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

## 🚦 LKIO 状态与门禁矩阵

LKIO 恪守最高工程质量准则：

$$\mathbf{Implementation\ Complete \neq Benchmark\ Validated \neq Production\ Gate\ Passed}$$

我们将架构实现、基准评测验证与真实生产准入严格划界：

| 子系统 / 研发阶段 | 当前状态 | 验证细节与门禁进展 |
|---|:---:|---|
| **Stage 0: 基线与全局身份体系** | `COMPLETE` | ✅ 完整 URI 命名空间身份体系（`repo://<repo_id>/<path>#<symbol>`），统一 SDK 客户端（`core.sdk.lkio.LKIO`），基线清单全部冻结。 |
| **Stage 1: 增量索引与 COW 快照引擎** | `BENCHMARK VALIDATED` | ✅ 写时复制（COW）原子发布、细粒度符号级增量 Diff、陈旧悬挂边级联修剪、事务性秒级回滚，以及独立 Oracle（基于标准结构子集校验：`FILE`, `CLASS`, `INTERFACE`, `METHOD`, `CONTAINS`）。 |
| **Stage 2: 跨仓拓扑图与契约推断** | `BENCHMARK VALIDATED` | ✅ 跨仓全局身份、REST/RPC 契约匹配、多路由候选排序 ($A \to [B: 0.97, C: 0.61]$)、多义性歧义检测、DTO 字段级数据血缘，环路安全多仓 BFS 遍历。 |
| **Stage 3: MCP 协议设施 (Agent 网关)** | `BENCHMARK VALIDATED` | ✅ 标准 JSON-RPC 2.0 与 Stdio 传输循环（支持 2024-11-05、2025-11-25、2026-07-28 动态协议协商），9 大只读 MCP 工具严格委托 SDK，显式写操作黑名单熔断，100 并发压力实测通过。 |
| **Stage 4: Agent 重构闭环与治理门禁** | `BENCHMARK VALIDATED` | ✅ 7 步闭环重构编排器，8 大高危对抗攻击防御率 8/8（Wilson 95% 置信区间 $[67.6\%, 100.0\%]$），32 组日常良性操作放行率 32/32（误拦截率 $\le 10.7\%$），双向独立 Oracle 对偶校验。坚决执行 `Confidence != Permission`。 |
| **生产级规模证明 (Production Scale Proof)** | `PENDING DOGFOODING` | ⏳ 合成基准与多仓场景均已达标。目前正在通过 1~2 名工程师开展为期两周的日常研发 Dogfooding 真实生产验证。 |

---

## 📐 系统整体架构

```text
               目标代码库 (Multi-Repo 跨仓代码)
                              │
               持续 COW 增量解析与原子快照
             (Tree-sitter AST: TS / JS / Java / Vue)
                              │
               细粒度符号与依赖关系 Delta 引擎
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
     代码结构拓扑图        Git 时间演化痕迹        混合检索层
   (有界 BFS 影响面)       (提交级代码 Diff)     (向量 + BM25)
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                     统一 LKIO SDK 客户端
                   (core.sdk.lkio.LKIO)
                              │
             Model Context Protocol (MCP) 服务端
              (JSON-RPC 2.0 / Stdio 传输协议)
                              │
          编程智能体 (Cursor / Claude Code / Codex 等)
                              │
               Agent 自动化重构与执行反馈闭环
                              │
             自动化单测验证 & 热快照重新索引 (Hot Re-Index)
                              │
         生产安全治理门禁 (`Confidence != Permission`)
                              │
                  可溯源、有事实支撑的决策产出
```

---

## 🔌 Model Context Protocol (MCP) 配置

LKIO 通过标准输入输出 (`stdio`) 提供工业级 MCP 服务，兼容主流大模型编程终端（Claude Code、Cursor、Codex、Windsurf）。外部智能体可无感调取代码库图谱推理能力，而无需直连物理底层数据库。

### 在 Cursor / Claude Code 中配置

在 `mcp.json` 或 `claude_desktop_config.json` 中添加如下配置：

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

### 9 大核心只读 MCP 工具

所有工具均为严格只读设计，杜绝任意未授权代码突变：

1. `repo_overview`: 获取项目概况、语言分布、活跃符号数及拓扑健康度。
2. `list_entities`: 分页与过滤代码实体（类、方法、接口、组件）。
3. `get_entity_detail`: 获取符号签名、源代码切片及元数据。
4. `search_knowledge`: 跨符号、文档与源码的混合向量 + 词法检索。
5. `analyze_impact`: 基于环路安全 BFS 计算代码变更的爆炸半径与下游波及面。
6. `evaluate_decision`: 结合图谱证据与统计校准规则评估重构决策。
7. `get_timeline`: 溯源 Git 提交演化历史、文件级增删及责任作者。
8. `incremental_index`: 将实时文件改动热同步为原子 COW 快照。
9. `export_graph`: 以 JSON 格式导出结构依赖子图节点与边。

---

## 🛡️ 生产安全治理与对抗压力测试

LKIO 奉行绝对安全准则：

$$\mathbf{Confidence \neq Permission}$$

即使大模型给出了接近满分的置信度（$0.999$），只要影响面涉及核心支付模块、授权鉴权中间件或基础框架配置，系统**严格要求人工签批审批**。

```text
模型置信度评分 ──> 变更风险等级评定 ──> 安全策略核验 ──> 准入许可决策
                                                          (ALLOW / REVIEW / BLOCK)
```

治理引擎通过 **8 大高危对抗压力测试** 验证防御能力（详见 `tests/unit/stage4/test_governance_adversarial_stress.py`）：

| 场景编号 | 对抗注入条件 | 防御安全策略 | 决策拦截结果 | 验证状态 |
|---|---|---|:---:|:---:|
| `STRESS-001` | 对核心支付模块给出虚假超高置信度 ($0.999$) | `MANDATORY_HUMAN_SIGNOFF` | `REVIEW` | **PASSED** |
| `STRESS-002` | 非关键日志代码变更但置信度较低 ($0.68$) | `MODERATE_CONFIDENCE_PEER_REVIEW` | `REVIEW` | **PASSED** |
| `STRESS-003` | 模型声称代码良性，但检测到底层单元测试退化 | `ZERO_REGRESSION_POLICY` | `BLOCK` | **PASSED** |
| `STRESS-004` | 单元测试通过，但变更影响面意外蔓延至核心鉴权范围 | `CRITICAL_SCOPE_STRICT_BLOCK` | `BLOCK` | **PASSED** |
| `STRESS-OOD` | 引入分布外异常制品（未注册二进制插件或脚本） | `OUT_OF_DISTRIBUTION_HUMAN_TRIAGE` | `REVIEW` | **PASSED** |
| `STRESS-006` | 模型输出数值畸变（$\text{NaN}$、负数置信度等） | `ANOMALOUS_MODEL_OUTPUT_BLOCK` | `BLOCK` | **PASSED** |
| `STRESS-007` | 图谱事实证据链不足（引用调用链为空） | `INSUFFICIENT_EVIDENCE_BLOCK` | `BLOCK` | **PASSED** |
| `STRESS-008` | 引用未注册实体或孤岛符号 | `INCOMPLETE_TOPOLOGY_BLOCK` | `BLOCK` | **PASSED** |

---

## 🔬 LKIO-Bench: 20 层代码推理评测基准

LKIO 配套了完整的 20 层推理评测套件，全面覆盖检索、拓扑图推理、Git 时间溯源、校准决策及跨仓契约推断：

- **Layer 1**: 语义检索 MRR & NDCG 排名评估
- **Layer 2**: AST 符号定位精确率与召回率
- **Layer 3**: 依赖图 1-Hop / 2-Hop / 3-Hop 跳转准度
- **Layer 4**: 拓扑环路安全（自环、互调用环、跨模块深环）
- **Layer 5**: 最短跳步保持（防止路径深度虚胖）
- **Layer 6**: 有界搜索半径与严格深度遏制
- **Layer 7**: Git Commit 责任归因与时序 Diff 还原
- **Layer 8**: 历史代码库架构状态精准回溯
- **Layer 9**: 直接与间接影响面爆炸半径精确率
- **Layer 10**: 跨模块虚假调用扩散强力抑制
- **Layer 11**: 多路径 Ground-Truth 真实事实链累积
- **Layer 12**: 全栈调用链路穿透 (Vue SFC $\to$ API $\to$ Spring Controller $\to$ DB)
- **Layer 13**: 4 大策略类别下的决策正确率与 F1 指标
- **Layer 14**: 温度缩放校准消融实测 (ECE 降低 60.52%)
- **Layer 15**: 8 大系统基线体系对比消融实测
- **Layer 16**: 细粒度 AST 符号变动与方法签名变更不变性
- **Layer 17**: 级联陈旧拓扑悬挂边级联修剪
- **Layer 18**: 跨仓路由歧义检测与多候选匹配排序
- **Layer 19**: DTO 字段级跨端跨语言语义映射
- **Layer 20**: 环路安全多仓跨工程影响面穿透推断

```bash
# 运行 LKIO-Bench 基准评测
uv run pytest tests/unit/benchmarks/test_lkio_bench.py -q
```

---

## 🚀 快速启动与验证

### 1. 环境准备与安装

LKIO 依赖 Python 3.12+，推荐使用 [`uv`](https://github.com/astral-sh/uv) 极速管理：

```bash
# 克隆代码库
git clone https://github.com/xxmasy/lkio.git
cd lkio

# 安装依赖并生成锁文件
uv sync
```

### 2. 11 大零信任门禁实时数学证明

LKIO 提供统一的零信任数学证据检验命令行，在本地实时推导并输出 11 大门禁检验报告（无任何伪造数据）：

```bash
uv run lkio verify --all
```

或通过 Python 模块直接调用：
```bash
uv run python -m core.cli verify --all
```

输出机器可读的 JSON 证据包：
```bash
uv run lkio verify --all --json
```

### 3. 执行完整单元测试

```bash
uv run pytest tests/unit -q
```

### 4. Docker 容器化启动

```bash
docker compose up -d
```

- API 服务：`http://localhost:8000`
- API Swagger 文档：`http://localhost:8000/docs`
- Web 可视化仪表盘：`http://localhost:5173`

---

## 📄 开源许可与学术严谨性

LKIO 采用 [Apache License 2.0](LICENSE) 开源协议。

LKIO 坚持绝对学术诚信与工程严谨：所有评测数据、基线对比及门禁证明均可在本地基于源码百分之百复现，不依赖任何不可验证的闭源特权接口。
