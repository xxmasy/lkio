# LKIO 系统架构与治理规范 (ARCHITECTURE.md)

> **版本**：v0.1  
> **基线准则**：[LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md](file:///C:/WorkSpace/lkio/LKIO_%E6%9C%AC%E5%9C%B0%E7%9F%A5%E8%AF%86%E6%99%BA%E8%83%BD%E6%93%8D%E4%BD%9C%E7%B3%BB%E7%BB%9F_MVP%E5%AE%9E%E6%96%BD%E5%9F%BA%E7%BA%BF_v0.1.md)

---

## 1. 架构总览

```text
                Local Knowledge Intelligence OS (LKIO)
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
     Knowledge Core       Decision Core       Experience
           │                   │                   │
     ┌─────┼─────┐         ┌───┴────┐        ┌─────┼─────┐
     │     │     │         │ Laya   │        │ Wiki│Graph│
    Entity Relation Event  │ Policy │        │Dash │Chat │
     │     │     │         └────────┘        └─────┴─────┘
     └─────┼─────┘
           │
       RAG / Search
           │
       Code / Docs / Git
```

---

## 2. 核心技术栈锁定

- **后端应用**：Python 3.12.10 + uv + FastAPI + SQLAlchemy 2.x + Alembic + `psycopg[binary]`
- **数据底座**：PostgreSQL 18.6 + pgvector 0.8.6 (Docker 镜像 `pgvector/pgvector:0.8.6-pg18`)，端口 `127.0.0.1:54329`
- **前端系统**：Node 24 LTS + Vue 3 + TypeScript + Vite + Element Plus + Pinia + Cytoscape.js
- **解析层 (MVP2)**：Tree-sitter（统一 CodeSymbol 实体）
- **向量检索 (MVP3)**：BAAI/bge-m3 + pgvector
- **决策引擎 (MVP6)**：Laya Adapter (`convaiinnovations/laya-typed-decisions` ModernBERT-large 421M)

---

## 3. 治理宪法与红线约束

1. **源项目只读**：`HELLO_FE`, `HELLO_BE`, `L2C_FE` 绝对只读，禁止写回或修改。
2. **唯一激活 MVP 纪律**：任何时候最多只有一个 ACTIVE MVP，必须对照验收门逐项通过方可流转。
3. **真相与投影分离**：Git、DB、代码为真实事实（Source of Truth）；Wiki 与 LLM 推理仅为投影（Projection）。
4. **置信度可解释性**：`Confidence ≠ Truth`，所有关系与决策标注 `source_type`, `extraction_method` 与 `confidence`。
5. **禁用过早组件**：严禁在前期引入 Neo4j、Qdrant、Milvus、Kafka、Redis、LangChain、CrewAI 等多余框架。
