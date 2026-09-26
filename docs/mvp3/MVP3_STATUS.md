# LKIO MVP3 (Hybrid RAG) 执行跟踪与状态总表

> **当前阶段**：**MVP3 (Hybrid RAG: Keyword + Vector + Graph)**  
> **前置阶段状态**：  
> - **MVP0 = COMPLETED / FROZEN**  
> - **MVP1 = COMPLETED / FROZEN**  
> - **MVP2 = COMPLETED / FROZEN**  
> **当前状态**：**MVP3 = 100% COMPLETED / FROZEN** ✅  
> **后续阶段状态**：**MVP4 = READY_TO_PLAN**  
> **实施基线**：`docs/mvp3/mvp3_step0_planning_and_baseline.md`  
> **核心原则**：多路互补检索、客观事实锚定、证据透明追溯、严禁直接让 LLM 面对原始库

---

## 🛑 永久冻结架构红线

1. **三大源工程绝对只读**：`HELLO_FE`, `HELLO_BE`, `L2C_FE` 物理只读，严禁写回或修改任何文件。
2. **严禁引入受限重型中间件**：禁止引入 Neo4j, Qdrant, Milvus, Elasticsearch, Kafka, Redis, Temporal。
3. **严禁伪置信度**：所有检索结果必须绑定证据与抽取方法，禁止虚构无依据置信度。
4. **代码实体不孤立依赖向量**：代码实体与函数定义优先通过 `entity_index` 和 `keyword_index` 定位。
5. **本地离线确定性保障**：核心检索与评估测试必须支持离线运行，严禁强依赖外部在线商用 LLM API。
6. **检索先行，未达标不进 LLM**：必须通过 100 个 Query Gold Set 验收门（Recall@5 >= 85%, 跨项目错配率 < 3%, 证据准确率 >= 95%）。

---

## MVP3 细分实施步骤规划

| 步骤代号 | 任务目标 | 核心输出 | 当前状态 | 归档文档 |
|---|---|---|---|---|
| **Step 3.0** | MVP3 规划、架构基线固化与红线锁死 | 冻结实施基线与 6 大红线 | **COMPLETED / FROZEN** | `docs/mvp3/mvp3_step0_planning_and_baseline.md` |
| **Step 3.1 (MVP3-A)** | 五大检索索引基础库构建 (`core/rag/indices/`) | `entity_index`, `keyword_index`, `vector_index`, `graph_index`, `temporal_index` | **COMPLETED / FROZEN** | `core/rag/indices/` |
| **Step 3.2 (MVP3-B)** | 语义切片与索引构建器 (`core/rag/chunking/`, `builder.py`) | 结构化语义 Chunk 切片与批量索引管道 | **COMPLETED / FROZEN** | `core/rag/builder.py` |
| **Step 3.3 (MVP3-C)** | 查询意图路由器 (`core/rag/router/`) | 8 大意图识别、实体抽词、路径过滤与动态权重 | **COMPLETED / FROZEN** | `core/rag/router/` |
| **Step 3.4 (MVP3-D)** | 多路融合重排与证据链包装 (`core/rag/fusion/`, `reranker.py`) | RRF 融合算法、置信度校准与完整证据链结构 | **COMPLETED / FROZEN** | `core/rag/fusion/` |
| **Step 3.5 (MVP3-E)** | Local LLM Gateway 抽象接口与离线适配器 (`core/rag/gateway/`) | `LLMProvider(Protocol)`、Mock/Local Embedder 与 Chat Gateway | **COMPLETED / FROZEN** | `core/rag/gateway/` |
| **Step 3.6 (MVP3-F)** | 100-Query Gold Set 系统验收与结项归档 | 101 个真实业务查询回归测试、Recall@5 94.06% 验证与结项报告 | **COMPLETED / FROZEN** ✅ | `docs/mvp3/mvp3_acceptance_report.md` |
