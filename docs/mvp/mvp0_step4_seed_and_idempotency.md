# MVP0 - Step 0.4 实施归档与对照核验报告

> **所属阶段**：**MVP0 (Environment & Knowledge Core)**  
> **步骤编号**：Step 0.4  
> **步骤名称**：三大真实项目种子数据注入与幂等性验证  
> **完成日期**：2026-09-24  
> **归档位置**：`docs/mvp/mvp0_step4_seed_and_idempotency.md`

---

## 1. 上一轮 Plan 目标对照检验

| 计划项 | 计划要求 | 实际执行结果 | 状态 | 检验说明 |
|---|---|---|---|---|
| **真实项目注册** | 从 `config/projects.yaml` 提取 `HELLO_FE`, `HELLO_BE`, `L2C_FE` | 3 个项目成功存入 `projects` 表 | **PASS** | 角色分别绑定为 `primary_frontend`, `paired_backend`, `future_frontend` |
| **数据源记录生成** | 为 3 个项目创建 `local_git_repository` Source | 3 条 Source 成功入库 | **PASS** | 严格配置 `read_only=True` 与 `enabled=True` |
| **实体层级结构** | 按 Section 11 生成 `PROJECT -> REPOSITORY -> FRONTEND/BACKEND` | 9 个 Entity 成功生成 | **PASS** | 统一采用 `PROJECT:{key}`, `REPO:{key}`, `{KIND}:{key}` 确定性键名 |
| **拓扑关系建立** | 包含项目内包含边以及跨项目 `paired_with` 边 | 7 条 Relation 记录入库 | **PASS** | 6 条内部 `contains` 边，1 条跨项目 `HELLO_FE -paired_with-> HELLO_BE`，L2C 保持独立 |
| **数据幂等性检验** | 脚本重复运行不新增数据、不产生重复实体与关联 | 多次重复运行数据完全一致 | **PASS** | `projects=3`, `sources=3`, `entities=9`, `relations=7`，计数与内容完全恒定 |
| **源项目只读性** | 整个过程不得写入或触碰 3 个源项目 | 3 个源项目无任何 LKIO 改动 | **PASS** | `git status` 检查证实源目录零写入 |

---

## 2. 成果物资产清单

1. `infra/scripts/seed.py`：幂等种子注入模块与 CLI 入口
2. 数据库落盘数据：
   - 3 个项目记录：`HELLO_FE`, `HELLO_BE`, `L2C_FE`
   - 3 个数据源：各自的本地工作区路径（只读模式）
   - 9 个核心实体：覆盖项目、仓库、前端/后端分层
   - 7 条拓扑关系：
     - `hello` -contains-> `hello_repo`
     - `hello_repo` -contains-> `hello_frontend`
     - `hello-backend` -contains-> `hello-backend_repo`
     - `hello-backend_repo` -contains-> `hello-backend_backend`
     - `L2C project` -contains-> `L2C project_repo`
     - `L2C project_repo` -contains-> `L2C project_frontend`
     - `hello` -paired_with-> `hello-backend`（跨项目连接）

---

## 3. 当前 MVP 完成情况评估

- **MVP0 整体进度**：Step 0.1, Step 0.2, Step 0.3, Step 0.4 已全部通过验收，Step 0.5 ~ Step 0.7 待启动。
- **状态评估**：知识核心已具备三个真实纳管项目的实体与关系数据，幂等性得到验证。
- **后续 MVP 状态**：MVP1 ~ MVP8 保持 **LOCKED**。

---

## 4. 下一任务规划与执行条件核查

- **下一任务**：**MVP0 - Step 0.5 后端 API 端点实现与单元测试通过**
- **执行前置条件检查**：
  - [x] Step 0.1: PostgreSQL 18 + pgvector 正常服务中
  - [x] Step 0.2: FastAPI 及依赖完整安装在 `.venv`
  - [x] Step 0.3: 数据模型与会话连接就绪
  - [x] Step 0.4: 真实项目与实体关系数据已入库
- **Step 0.5 实施目标**：
  1. 按照基线 Section 12 规范设计标准响应信封与统一错误处理（`data`, `meta`, `error`）
  2. 实现 FastAPI 主应用与路由层：
     - `GET /api/v1/health`
     - `GET /api/v1/projects`
     - `POST /api/v1/projects`
     - `GET /api/v1/projects/{project_id}`
     - `GET /api/v1/entities`
     - `POST /api/v1/entities`
     - `GET /api/v1/entities/{entity_id}`
     - `GET /api/v1/relations`
     - `POST /api/v1/relations`
     - `GET /api/v1/graph/projects/{project_id}`
     - `GET /api/v1/graph/entities/{entity_id}/neighbors`
  3. 配置 CORS 中间件（支持前端 `127.0.0.1:5173` 访问）
  4. 编写 `tests/test_api_v1.py` 单元与集成测试，执行 pytest 验证全部 PASS
