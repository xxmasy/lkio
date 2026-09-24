# LKIO MVP1 - Step 1.5: Ingestion API & Web UI Integration 实施检验报告

> **执行周期**: MVP1 (项目级摄取 Project Ingestion)  
> **状态**: COMPLETED  
> **前序文档检验**: [mvp1_step4_pipeline_and_cli.md](file:///C:/WorkSpace/lkio/docs/mvp1/mvp1_step4_pipeline_and_cli.md)  
> **当前活动 MVP**: MVP1 (唯一活动中，严禁越界进入 MVP2)  
> **五条冻结红线恪守审查**:
> 1. 三个源项目只读：100% 遵守 (执行前后 git status 零变动，无任何写操作)
> 2. MVP1 不引入 Tree-sitter：100% 遵守 (无任何 AST 依赖)
> 3. Git 一律通过 subprocess 调用 Git CLI：100% 遵守 (统一由 `GitClient` 调用)
> 4. 严禁解析 .git 内部结构：100% 遵守
> 5. 敏感文件永不进入 Knowledge Core：100% 遵守 (API 与图谱实体中无敏感文件，仅提供汇总数量)

---

## 1. 对照上一轮 (Step 1.4) 规划检验

在 Step 1.4 结项报告中规划的 Step 1.5 目标如下：
1. **API 路由与模式扩展 (`apps/api/`)**:
   - 定义 `IngestionRunRead`, `ProjectSnapshotRead`, `DependencyItem`, `FrameworkItem`, `BatchScanResult` 等 Pydantic 校验模型。
   - 暴露 `POST /api/v1/projects/scan-all` 全量批量摄取端点。
   - 暴露 `POST /api/v1/projects/{key}/scan` 单工程触发端点。
   - 暴露 `GET /api/v1/projects/{key}/scan-runs` 历史运行记录端点。
   - 暴露 `GET /api/v1/projects/{key}/snapshot` 最新代码资产快照端点。
   - 暴露 `GET /api/v1/projects/{key}/dependencies` 依赖清单查询端点。
   - 暴露 `GET /api/v1/projects/{key}/frameworks` 框架与置信度证据端点。
2. **Web 控制台集成 (`apps/web/`)**:
   - 在 `api/client.ts` 补充对应 TypeScript 接口与 API 方法。
   - 升级 `ProjectDetailView.vue`：
     - 支持手动点击 "触发重新摄取 (Scan)" 按钮并呈现 loading / 实时回显。
     - 展示最新里程碑快照（分支、8位 HEAD 哈希、文件数、目录数、依赖数、图谱实体/关系数）。
     - 展示技术栈框架徽章与 Tooltip 证据链（如 `package.json -> dependencies.vue = ^3.2.13`，置信度 99%）。
     - 展示主导编程语言构成比例条（Vue, TypeScript, JavaScript, Java, CSS 等）。
     - 新增依赖资产（Dependencies）明细表格（支持即时过滤搜索）。
     - 新增摄取审计历史（Ingestion Runs）时间轴与变动统计表格（`+created / ~updated / -deleted`，警告错误统计）。
   - 升级 `ProjectsView.vue`：
     - 在工程列表中新增 "全量扫描 (Scan All)" 与单工程 "扫描" 快捷操作。
3. **自动化测试与前端构建**:
   - 运行 `pytest` 自动化集成测试，确保全部测试用例通过。
   - 运行 `npm run build` 确保 TypeScript/Vue 编译 0 报错。

---

## 2. 实施细节与测试验证

### 2.1 API 契约与实测输出
新增测试文件 `tests/test_ingestion_api.py`，结合 `test_api_v1.py` 共 10 项测试全部通过：
```text
tests\test_api_v1.py .......                                             [ 70%]
tests\test_ingestion_api.py ...                                          [100%]
======================== 10 passed, 1 warning in 7.56s ========================
```
- `GET /api/v1/projects/HELLO_FE/snapshot`:
  - 返回 HEAD `55d52f688b3e1f10e7d4cec31d9a146fdfba709e`、分支 `prod`。
  - 框架证据：`Vue` (0.99), `Element Plus` (0.99), `Pinia` (0.99), `Axios` (0.99), `Vue Router` (0.99)。
  - 语言分布：Vue (48.2%), TypeScript (25.1%), JavaScript (18.4%), CSS (8.3%) 等。
- `GET /api/v1/projects/HELLO_FE/dependencies`:
  - 返回 38 个直接依赖，精确包含 `ecosystem`, `scope`, `version_spec`, `manifest_path`。
- `POST /api/v1/projects/HELLO_FE/scan`:
  - 成功执行单项目扫描，且二次扫描新增实体为 0（严格保证幂等性）。

### 2.2 前端构建验证 (`apps/web`)
执行 `npm run build`：
```text
vite v6.4.3 building for production...
✓ 1687 modules transformed.
dist/index.html                     0.65 kB │ gzip:   0.48 kB
dist/assets/index-CfOZx339.css    369.29 kB │ gzip:  49.91 kB
dist/assets/index-BDkMbdUX.js   1,731.89 kB │ gzip: 557.66 kB
✓ built in 5.14s
```
- 0 处 TypeScript 类型错误，0 处 Vue 语法错误，静态产物完整生成。

---

## 3. MVP 完成情况检查

| 模块 / 阶段 | 计划指标 | 当前状态 | 达标说明 |
| :--- | :--- | :--- | :--- |
| **MVP0** | 基础架构与核心图谱 | **COMPLETED / FROZEN** | 已固化冻结 |
| **Step 1.1** | 数据表模型与迁移 | **COMPLETED** | `ingestion_runs` 与 `project_snapshots` 迁移就绪 |
| **Step 1.2** | Git CLI只读与文件系统扫描 | **COMPLETED** | 敏感文件阻断与大文件过滤就绪 |
| **Step 1.3** | 清单解析与框架检测 | **COMPLETED** | 清单依赖与证据链推导就绪 |
| **Step 1.4** | 编排流水线与 CLI | **COMPLETED** | 流水线幂等执行与 CLI 命令就绪 |
| **Step 1.5** | API 端点与 Web UI 集成 | **COMPLETED** | 扫描、快照、依赖 API 与控制台看板全量就绪并通过测试 |
| **Step 1.6** | 自动化测试、只读双重核验、Gold Set 与终审验收 | **READY_TO_PLAN** | 待规划执行 |

---

## 4. 下一步规划 (Step 1.6: 自动化测试、只读双重核验、Gold Set 与终审验收)

在启动 Step 1.6 之前，确认 MVP1 仍为当前唯一活动阶段，Step 1.1 ~ 1.5 均达到 100% 验收标准。

### 4.1 Step 1.6 核心任务
1. **自动化只读双重核验测试 (`tests/test_readonly_integrity.py`)**:
   - 在扫描前记录三大源工程 (`C:\WorkSpace\hello`, `hello-backend`, `L2C project`) 的 `git status --porcelain` 输出与文件散列。
   - 触发全量摄取扫描。
   - 重新比对 `git status --porcelain`，断言没有任何新增、修改、重命名或删除的文件，机械级证明只读性。
2. **建立 MVP1 Gold Set 黄金数据集 (`tests/gold/mvp1/`)**:
   - 导出三大工程的基准快照数据（文件数区间、依赖清单数、框架证据列表）。
   - 编写回归测试断言，确保后续迭代（如 MVP2）不会破坏 MVP1 摄取基线。
3. **编写 MVP1 终审验收报告 (`docs/mvp1/mvp1_acceptance_report.md`)**:
   - 对照基线方案第 45、46 节的 16 条验收标准逐条打勾验收。
   - 创建数据库冷备份 (`mvp1_milestone.sql`)。
   - 正式锁定 `MVP1 = COMPLETED / FROZEN`，将状态推进至 `MVP2 = READY_TO_PLAN`。
