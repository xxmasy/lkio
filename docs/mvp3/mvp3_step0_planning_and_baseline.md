# LKIO MVP3 (Hybrid RAG: Keyword + Vector + Graph) 实施基线与主规划

> **阶段代号**：**MVP3 (Hybrid RAG)**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN** (基础环境与模型底座)  
> - **MVP1 = COMPLETED / FROZEN** (三大项目只读摄取、快照与 Git 历史)  
> - **MVP2 = COMPLETED / FROZEN** (代码符号、单工程图谱、跨工程依赖、API端到端追溯)  
> **当前状态**：**IN_PROGRESS**  
> **基线规范**：`LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md` 第 21 ~ 24 节、第 38 节、第 44 节  
> **核心原则**：多路互补检索、客观事实锚定、证据透明追溯、严禁直接让 LLM 面对原始库

---

## 一、🛑 永久冻结架构红线 (MVP3 强制约束)

1. **源项目绝对只读**：`HELLO_FE`、`HELLO_BE`、`L2C_FE` 绝对物理只读，严禁任何写操作或生成临时文件。
2. **严禁引入受限重型中间件**：基线第 44 节明令禁止在 MVP0~MVP3 引入 Neo4j、Qdrant、Milvus、Elasticsearch、Kafka、Redis、Temporal。全部索引基于本地存储（PostgreSQL / SQLite）与内存倒排/向量计算。
3. **严禁伪置信度与无证据答案**：所有检索出的候选结果与证据必须绑定物理实体、源码坐标（File + Line）、关联 Predicate 或 Commit ID，禁止虚构无依据的置信度。
4. **代码符号绝不孤立依赖向量**：代码实体与函数定义优先通过 `entity_index` 和 `keyword_index` 定位，向量主要用于非结构化文档、业务描述、语义注释及 API 意图匹配。
5. **本地离线确定性保障**：核心检索与评估测试必须支持离线运行，严禁强依赖外部在线商用 LLM API 导致 CI 不稳定或数据外泄。
6. **检索先行，未达标不进 LLM**：必须通过 100 个 Query Gold Set 验收门（Recall@5 >= 85%, 跨项目错配率 < 3%, 证据准确率 >= 95%），否则禁止进入 MVP4 (LLM Wiki)。

---

## 二、MVP3 核心架构设计

### 1. 检索流水线拓扑

```text
                           User Natural Query
                                   │
                                   ▼
                        Query Intent Router
            (ENTITY / CODE / RELATION / BUSINESS / HISTORY / SEMANTIC / IMPACT)
                                   │
         ┌──────────────┬──────────┴──────────┬──────────────┐
         ▼              ▼                     ▼              ▼
    Entity Index   Keyword Index         Vector Index    Graph Index
    (B-tree/Hash)   (BM25/FTS)            (Dense Embed)   (K-hop Topology)
         │              │                     │              │
         └──────────────┼─────────────────────┴──────────────┘
                        │
                        ▼
             Hybrid Fusion & Merge (RRF)
                        ▼
                Cross-Channel Reranker
                        ▼
             Evidence Packaging & Citation
         (File, Line, EntityKey, RelationKey, Confidence)
```

### 2. 五大检索索引矩阵 (Retrieval Indices)

| 索引名称 | 索引对象 | 底层技术 | 核心适用场景 |
|---|---|---|---|
| **entity_index** | Symbol Key, Entity Key, Canonical Name, Class/Method/File | 精确哈希 + 前缀 B-Tree | 确定性符号定位、类名/文件名直查、全限定名查找 |
| **keyword_index** | 代码标识符、代码注释、Docstring、文件路径、文档段落 | 词法分词 + 倒排索引 (BM25) | 文本关键词搜索、报错信息定位、复合命名匹配 |
| **vector_index** | 文档 Chunk、代码语义块、API 契约描述、业务规则 | Dense Vector Embedding + 余弦相似度 | 模糊自然语言意图、跨语义匹配、概念提问 |
| **graph_index** | MVP2 图谱边 (imports, calls, extends, routes_to, traces_to) | 图邻接索引 + K-hop 拓扑遍历 | 调用链追溯、谁调用了我、影响分析、前后端契约链 |
| **temporal_index** | Git Commit 日志、文件修改历史、变更作者、提交时间 | 时间序列有序倒排 | “最近改了什么”、“某文件由谁修改”、“变更演进” |

---

## 三、MVP3 细分子步骤规划

| 步骤代号 | 任务目标 | 核心输出 | 状态 |
|---|---|---|---|
| **Step 3.0** | MVP3 规划、架构基线固化与 6 大红线锁死 | `docs/mvp3/mvp3_step0_planning_and_baseline.md` | **COMPLETED** |
| **Step 3.1 (MVP3-A)** | 五大检索索引基础库构建 (`core/rag/indices/`) | `entity_index`, `keyword_index`, `vector_index`, `graph_index`, `temporal_index` | **READY_TO_IMPLEMENT** |
| **Step 3.2 (MVP3-B)** | 语义切片与索引构建器 (`core/rag/chunking/`, `builder.py`) | 代码块/文档/API 语义 Chunk 切片与批量索引管道 | **TODO** |
| **Step 3.3 (MVP3-C)** | 查询意图路由器 (`core/rag/router/`) | 8 大意图识别、实体抽词、路径过滤与动态权重分配 | **TODO** |
| **Step 3.4 (MVP3-D)** | 多路融合重排与证据链包装 (`core/rag/fusion/`, `reranker.py`) | RRF 融合算法、置信度校准与完整证据链结构 | **TODO** |
| **Step 3.5 (MVP3-E)** | Local LLM Gateway 抽象接口与离线适配器 (`core/rag/gateway/`) | `LLMProvider(Protocol)`、Mock/Local Embedder 与 Chat Gateway | **TODO** |
| **Step 3.6 (MVP3-F)** | 100-Query Gold Set 系统验收与结项归档 | 100 个真实业务查询回归测试、Recall@5 >= 85% 验证与验收报告 | **TODO** |

---

## 四、MVP3 终审验收门禁 (Verification Gates)

1. **GATE-RAG-01 (Five-Index Completeness)**: 五大索引必须全部独立可用且具有确定性查询接口。
2. **GATE-RAG-02 (Zero-External Dependency CI)**: 所有单测与集成测试在无网络、无外部商用 API Key 状态下 100% 通过。
3. **GATE-RAG-03 (Evidence Transparency)**: 检索结果中每一个 Item 必须包含明确的证据（`project_key`, `file_path`, `line_range`, `evidence_type`）。
4. **GATE-RAG-04 (100-Query Gold Set Pass)**:
   - `Recall@5 >= 85%`
   - `Wrong-project Rate < 3%`
   - `Source Correctness >= 95%`
5. **GATE-RAG-05 (Read-only Invariance)**: 保持三大外部工程物理只读，文件变更数为 0。
