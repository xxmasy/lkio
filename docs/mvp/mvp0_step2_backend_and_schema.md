# MVP0 - Step 0.2 实施归档与对照核验报告

> **所属阶段**：**MVP0 (Environment & Knowledge Core)**  
> **步骤编号**：Step 0.2  
> **步骤名称**：目录规范与 Python 核心工程初始化  
> **完成日期**：2026-09-24  
> **归档位置**：`docs/mvp/mvp0_step2_backend_and_schema.md`

---

## 1. 上一轮 Plan 目标对照检验

| 计划项 | 计划要求 | 实际执行结果 | 状态 | 检验说明 |
|---|---|---|---|---|
| **Python 版本锁定** | 必须固定 Python 3.12.10 | `.python-version` 锁定 3.12.10 | **PASS** | `uv python pin 3.12.10` 完成 |
| **依赖锁定工具** | 使用 uv 统一管理环境并生成 `uv.lock` | 虚拟环境 `.venv` 与 `uv.lock` 生成 | **PASS** | 57 个基线包解析并安装完毕 |
| **基线依赖清单** | FastAPI, SQLAlchemy, Alembic, psycopg, pydantic-settings, etc. | 依赖全部按官方最新稳定版本锁定 | **PASS** | `fastapi` 0.141.1, `sqlalchemy` 2.0.54, `alembic` 1.20.0, `psycopg` 3.3.6 |
| **标准目录骨架** | 对照基线 Section 6 建立完整分层体系 | 建立 `core/`, `apps/`, `ingestion/`, `retrieval/`, `intelligence/`, `infra/`, `tests/` | **PASS** | 各层目录及 `__init__.py` 初始化完毕，杜绝临时目录污染 |
| **配置管理中心** | 基于 `pydantic-settings` 读取环境变量 | `core/config/settings.py` 实现并通过测试 | **PASS** | 准确加载 `.env.local`，数据库端口锁定 `54329`，`LKIO_SOURCE_READ_ONLY=True` |

---

## 2. 成果物资产清单

1. `pyproject.toml` & `uv.lock`：工程依赖定义与版本锁定清单
2. `.python-version`：Python 3.12.10 运行时版本锚点
3. 规范目录架构树：
   - `core/`（ontology, entity, relation, source, event, evidence, decision, config）
   - `apps/`（api, web, worker）
   - `ingestion/`（filesystem, git, manifests, code）
   - `retrieval/`（keyword, semantic, code, graph, rerank）
   - `intelligence/`（rag, wiki, impact, analytics）
   - `infra/`（compose.yaml, db, scripts）
   - `tests/`
4. `core/config/settings.py`：中央配置模型与连接串动态生成

---

## 3. 当前 MVP 完成情况评估

- **MVP0 整体进度**：Step 0.1 和 Step 0.2 均已通过验收，Step 0.3 ~ Step 0.7 待执行。
- **状态评估**：核心包环境运行稳定，配置读取无误，数据库连通性条件充分。
- **后续 MVP 状态**：MVP1 ~ MVP8 保持 **LOCKED**。

---

## 4. 下一任务规划与执行条件核查

- **下一任务**：**MVP0 - Step 0.3 数据库模型与 Alembic 迁移脚本**
- **执行前置条件检查**：
  - [x] Step 0.1: PostgreSQL 18 + pgvector 运行中
  - [x] Step 0.2: SQLAlchemy 2.x & Alembic 已安装并可在虚拟环境调用
- **Step 0.3 实施目标**：
  1. 建立数据库引擎与 Session 工厂 `core/db/session.py`
  2. 实现四大核心数据模型（`projects`, `sources`, `entities`, `relations`），完全遵循基线 Section 10 的字段规范与约束（UUID 主键、时间戳、JSONB metadata、唯一约束）
  3. 配置 Alembic 迁移环境（`infra/db/alembic`）
  4. 生成并执行 initial migration，在 PostgreSQL 中创建实体表结构
  5. 编写验证脚本确认四大表及索引、扩展结构就绪
