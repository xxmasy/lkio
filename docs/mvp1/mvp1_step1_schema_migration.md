# MVP1 - Step 1.1 实施归档与对照核验报告

> **所属阶段**：**MVP1 (Project Ingestion)**  
> **步骤编号**：Step 1.1  
> **步骤名称**：数据表扩展与 Alembic 迁移 (`ingestion_runs` & `project_snapshots`)  
> **完成日期**：2026-09-24  
> **归档位置**：`docs/mvp1/mvp1_step1_schema_migration.md`

---

## 1. 上一轮 Plan 目标对照检验

| 计划项 | 计划要求 | 实际执行结果 | 状态 | 检验说明 |
|---|---|---|---|---|
| **扫描运行记录表** | 按照基线 Section 28 定义 `ingestion_runs` | `core/models/ingestion_run.py` 完成 | **PASS** | 包含 status (PENDING, RUNNING, COMPLETED, PARTIAL, FAILED), head_before/after, 文件与实体增删计数, errors/warnings JSONB |
| **快照审计表** | 按照基线 Section 30 定义 `project_snapshots` | `core/models/project_snapshot.py` 完成 | **PASS** | 包含 head, branch, 文件/目录/依赖计数, frameworks/languages 数组与时区时间戳 |
| **模型导出与关联** | 在 `core/models/__init__.py` 统一导出并建立级联关系 | 全部关联绑定并导出 | **PASS** | `Project` 与 `Source` 级联外键索引化 |
| **Alembic 迁移生成** | 自动比对生成迁移文件 | 生成 `78079f581423_create_ingestion_runs_and_snapshots.py` | **PASS** | 字段定义、外键索引与 JSONB 类型校验无误 |
| **迁移执行与物理表核验** | `alembic upgrade head` 并通过 `psql` 验证物理表 | 物理库中 7 张表就绪 | **PASS** | `docker exec lkio-postgres psql -c '\dt'` 确认 7 表全部存在 |

---

## 2. 成果物资产清单

1. `core/models/ingestion_run.py`：扫描审计运行模型
2. `core/models/project_snapshot.py`：项目里程碑快照模型
3. `core/models/__init__.py`：模型层导出更新
4. `infra/db/alembic/versions/20260924_1326_78079f581423_create_ingestion_runs_and_snapshots.py`：迁移版本脚本
5. PostgreSQL 物理表：`ingestion_runs`, `project_snapshots`

---

## 3. 当前 MVP 完成情况评估

- **当前完成阶段**：MVP1 - Step 1.1 已通过。
- **状态评估**：MVP1 数据存储层基础设施已具备记录增量扫描、差异统计与快照追溯的能力。
- **红线遵循核查**：
  - [x] 未引入 Tree-sitter
  - [x] 未修改任何源项目
  - [x] 敏感文件过滤机制保持准备状态

---

## 4. 下一任务规划与执行条件核查

- **下一任务**：**MVP1 - Step 1.2 Git CLI 客户端与只读文件系统扫描器**
- **执行前置条件检查**：
  - [x] Step 1.1: 数据库与迁移已就绪
  - [x] Git CLI (2.54.0) 可用
  - [x] 5 大红线已确认
- **Step 1.2 实施目标**：
  1. 实现 `ingestion/git/client.py`：使用 `subprocess.run` 封装 Git CLI 探测方法（`is_inside_worktree`, `get_toplevel`, `get_branch`, `get_head`, `get_remotes` 带密码脱敏, `get_commits`, `ls_files`），强制 30s 超时控制与只读保证。
  2. 实现 `ingestion/filesystem/scanner.py`：
     - 文件绝对/相对路径计算、文件大小、mtime、扩展名
     - SHA-256 哈希计算（超过 10MB 自动标记 `skipped_large_file`）
     - 严格敏感文件排除（`.env`, `*.pem`, `*.key`, `credentials.json`, `secrets.*` 等）
     - 默认目录排除（`node_modules`, `.git`, `dist`, `.venv`, `__pycache__` 等）
     - 从规范相对路径安全反推目录实体树（严格以项目根为界，杜绝逃逸到操作系统根）
