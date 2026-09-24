# MVP0 - Step 0.3 实施归档与对照核验报告

> **所属阶段**：**MVP0 (Environment & Knowledge Core)**  
> **步骤编号**：Step 0.3  
> **步骤名称**：数据库模型与 Alembic 迁移脚本  
> **完成日期**：2026-09-24  
> **归档位置**：`docs/mvp/mvp0_step3_db_models_migration.md`

---

## 1. 上一轮 Plan 目标对照检验

| 计划项 | 计划要求 | 实际执行结果 | 状态 | 检验说明 |
|---|---|---|---|---|
| **SQLAlchemy 2.x 模型定义** | 严格按基线 Section 10 实现 4 大核心表 | 已创建 `Project`, `Source`, `Entity`, `Relation` | **PASS** | `core/models/` 模块全部采用 Mapped 强类型注解 |
| **UUID 主键与时间戳混入** | 所有核心表使用 UUID PK 与带时区的 TIMESTAMPTZ | 实现了 `UUIDPrimaryKeyMixin` 与 `TimestampMixin` | **PASS** | 统一命名约束规则已注入 DeclarativeBase |
| **三元组唯一约束** | `relations` 表必须满足 `(subject_entity_id, predicate, object_entity_id)` 唯一 | `uq_relations_triple` 约束已生效 | **PASS** | 杜绝图谱中重复边定义 |
| **Alembic 迁移环境** | 结构化配置迁移环境并绑定中央配置 | `alembic.ini`, `infra/db/alembic/env.py` | **PASS** | `env.py` 动态加载 `settings.database_url` 并保障 `vector` 扩展 |
| **迁移执行与 DB 核验** | 生成 initial migration 并 upgrade head | migration `ccd8457d185d` 执行成功 | **PASS** | PostgreSQL 中通过 `\dt` 验证 5 张表结构全部就绪 |

---

## 2. 成果物资产清单

1. `core/db/base.py`：声明式基类、UUID 主键与时间戳 Mixin、Postgres 约束命名规范
2. `core/db/session.py`：数据库引擎池化与 SessionLocal 会话工厂、FastAPI 依赖注入生成器
3. `core/models/`：
   - `project.py`（projects 表定义）
   - `source.py`（sources 表定义，外键级联）
   - `entity.py`（entities 表定义，支持项目关联与类型索引）
   - `relation.py`（relations 表定义，支持置信度与三元组唯一性）
   - `__init__.py`（模型统一导出）
4. `alembic.ini` & `infra/db/alembic/`：迁移配置文件、模板与 `env.py`
5. `infra/db/alembic/versions/20260924_1231_ccd8457d185d_create_knowledge_core_tables.py`：初始全量数据表迁移脚本
6. PostgreSQL 物理表：`projects`, `sources`, `entities`, `relations`, `alembic_version`

---

## 3. 当前 MVP 完成情况评估

- **MVP0 整体进度**：Step 0.1, Step 0.2, Step 0.3 全部通过验收，Step 0.4 ~ Step 0.7 待启动。
- **状态评估**：知识核心 Schema 已落库，具备强类型约束和幂等性支持。
- **后续 MVP 状态**：MVP1 ~ MVP8 保持 **LOCKED**。

---

## 4. 下一任务规划与执行条件核查

- **下一任务**：**MVP0 - Step 0.4 三大真实项目种子数据注入与幂等性验证**
- **执行前置条件检查**：
  - [x] Step 0.1: Docker 与 PostgreSQL 18 healthy
  - [x] Step 0.2: uv 虚拟环境与配置就绪
  - [x] Step 0.3: `projects`, `sources`, `entities`, `relations` 表在 PostgreSQL 中已建立
  - [x] 源项目目录（`C:\WorkSpace\hello`, `hello-backend`, `L2C project`）状态正常，保持只读
- **Step 0.4 实施目标**：
  1. 编写种子数据注入器 `infra/scripts/seed.py`
  2. 从 `config/projects.yaml` 读取 `HELLO_FE`, `HELLO_BE`, `L2C_FE` 注册为 Project 记录
  3. 为 3 个项目分别建立 `local_git_repository` Source 记录（`read_only=True`）
  4. 按照基线 Section 11 生成层级 Entity：
     - `HELLO_FE`: `PROJECT:HELLO_FE` -> `REPO:HELLO_FE` -> `FRONTEND:HELLO_FE`
     - `HELLO_BE`: `PROJECT:HELLO_BE` -> `REPO:HELLO_BE` -> `BACKEND:HELLO_BE`
     - `L2C_FE`: `PROJECT:L2C_FE` -> `REPO:L2C_FE` -> `FRONTEND:L2C_FE`
  5. 按照基线 Section 11 生成跨项目关系：`HELLO_FE -paired_with-> HELLO_BE`（L2C_FE 暂不关联）
  6. 严格实现幂等性检查机制（多次运行 `seed.py` 计数与数据均不改变）
  7. 编写自动化幂等性核验并输出断言报告
