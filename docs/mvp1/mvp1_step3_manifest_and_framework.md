# MVP1 - Step 1.3 实施归档与对照核验报告

> **所属阶段**：**MVP1 (Project Ingestion)**  
> **步骤编号**：Step 1.3  
> **步骤名称**：清单解析、语言推导与框架检测器  
> **完成日期**：2026-09-24  
> **归档位置**：`docs/mvp1/mvp1_step3_manifest_and_framework.md`

---

## 1. 上一轮 Plan 目标对照检验

| 计划项 | 计划要求 | 实际执行结果 | 状态 | 检验说明 |
|---|---|---|---|---|
| **包清单解析** | 支持 `package.json`, `pom.xml` 依赖与作用域提取 | `ingestion/manifests/scanner.py` 实现 | **PASS** | 提取 `HELLO_FE` (38 依赖), `HELLO_BE` (66 依赖), `L2C_FE` (169 依赖) |
| **包管理器判定** | 按 Section 21 支持 pnpm, yarn, npm, maven 并检测冲突 | `detect_package_manager` 实现 | **PASS** | `hello` -> npm, `hello-backend` -> maven, `L2C` -> pnpm，锁文件冲突可预警 |
| **语言分布统计** | 统计全项目扩展名分布并确定主要开发语言 | `ingestion/code/detector.py` 实现 | **PASS** | 成功识别 `HELLO_FE`: Vue, `HELLO_BE`: Java, `L2C_FE`: TypeScript |
| **框架检测与强证据** | 识别 Vue, React, Spring Boot, MyBatis 等，带置信度与证据链 | `detect_frameworks` 实现 | **PASS** | 成功提取框架置信度 0.99 及 `package.json -> dependencies.vue` 确凿证据 |
| **红线遵守审查** | 严禁使用 LLM 幻觉生成，严禁引入 Tree-sitter | 100% 规则推导 | **PASS** | 零 LLM 调用、零 Tree-sitter 依赖，纯确定性解析 |

---

## 2. 成果物资产清单

1. `ingestion/manifests/scanner.py`：清单提取器，支持 NPM/Maven/PyPI 依赖提取与包管理器判定
2. `ingestion/code/detector.py`：语言统计与框架特征检测器（带置信度与证据锚点）
3. 三大项目识别实测结果：
   - `HELLO_FE`：包管理器 `npm`，主语言 `Vue`，框架群 `['Vue', 'Vue Router', 'Pinia', 'Element Plus', 'Axios']`
   - `HELLO_BE`：包管理器 `maven`，主语言 `Java`，框架群 `['Spring Boot', 'MyBatis', 'MySQL Connector']`
   - `L2C_FE`：包管理器 `pnpm`，主语言 `TypeScript`，框架群 `['Vite', 'Vue', 'Pinia', 'Vue Router', 'Element Plus']`

---

## 3. 当前 MVP 完成情况评估

- **当前完成阶段**：MVP1 - Step 1.3 已通过。
- **状态评估**：已具备项目元数据、代码语言、框架生态及依赖项的全量自动提取能力。
- **红线遵循核查**：
  - [x] 源项目纯只读（仅读取清单文本，零写入）
  - [x] 未引入 Tree-sitter
  - [x] 敏感文件无进入
  - [x] 检测结果均携带可追溯 evidence

---

## 4. 下一任务规划与执行条件核查

- **下一任务**：**MVP1 - Step 1.4 完整 Ingestion Pipeline、幂等入库与 CLI 工具**
- **执行前置条件检查**：
  - [x] Step 1.1: 数据库表 (`ingestion_runs`, `project_snapshots`) 就绪
  - [x] Step 1.2: Git CLI 与文件系统只读扫描器就绪
  - [x] Step 1.3: 清单解析与框架检测器就绪
  - [x] 5 大红线牢固遵守
- **Step 1.4 实施目标**：
  1. 编写核心编排器 `ingestion/pipeline.py`：
     - 单项目扫描运行记录：生成 `IngestionRun` (状态流转 PENDING -> RUNNING -> COMPLETED / PARTIAL / FAILED)
     - 差异比对：记录 `head_before` 与 `head_after`
     - 实体生成与幂等入库：
       - `PROJECT:<key>`
       - `REPO:<key>`
       - `BRANCH:<key>:<branch>`
       - `COMMIT:<key>:<sha>` (最近 100 个)
       - `DIR:<key>:<rel_dir>`
       - `FILE:<key>:<rel_file>`
       - `LANG:<key>:<lang>`
       - `FRAMEWORK:<key>:<framework>`
       - `DEP:<key>:<ecosystem>:<name>`
       - `MANIFEST:<key>:<rel_path>`
     - 关系生成：`contains`, `uses`, `depends_on`
     - 软删除检测：标记上次存在而当前丢失的文件为 `status='deleted'`
     - 自动持久化 `ProjectSnapshot` 里程碑快照
     - 异常捕获与局部失败（Partial Failure）隔离机制
  2. 编写管理 CLI 工具 `infra/scripts/ingest.py`：
     - `scan --project <KEY>`
     - `scan-all`
     - `list-runs`
