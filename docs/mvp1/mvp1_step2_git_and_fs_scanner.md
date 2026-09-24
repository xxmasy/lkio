# MVP1 - Step 1.2 实施归档与对照核验报告

> **所属阶段**：**MVP1 (Project Ingestion)**  
> **步骤编号**：Step 1.2  
> **步骤名称**：Git CLI 客户端与只读文件系统扫描器  
> **完成日期**：2026-09-24  
> **归档位置**：`docs/mvp1/mvp1_step2_git_and_fs_scanner.md`

---

## 1. 上一轮 Plan 目标对照检验

| 计划项 | 计划要求 | 实际执行结果 | 状态 | 检验说明 |
|---|---|---|---|---|
| **Git CLI 统一包装** | 仅通过 `subprocess.run(["git", ...])` 执行，杜绝读取 `.git` 二进制 | `ingestion/git/client.py` 实现 | **PASS** | 统一设置 `timeout=30s`, `cwd`, `text=True`, `errors="replace"`，全只读指令 |
| **Git 元数据提取验证** | 对真实源目录提取 worktree, branch, HEAD, commit, remotes, ls-files | 3 个真实项目验证通过 | **PASS** | `hello` (branch=prod, files=2076), `hello-backend` (branch=feat/..., files=2089), `L2C project` (branch=main, files=2142) |
| **凭据安全脱敏** | 远程 URL 中的内嵌密码必须脱敏 | 正则脱敏实现 | **PASS** | `https://user:pass@host` 自动脱敏为 `https://user:***@host` |
| **敏感文件强隔离** | `.env`, `*.key`, `*.pem`, `credentials.json` 等严禁进入数据流 | `is_sensitive_filename` 正则强校验 | **PASS** | 单元测试验证敏感文件自动识别，阻止生成存储实体 |
| **大文件 Hash 防爆** | 文件 > 10MB 跳过 SHA-256 计算 | `hash_status="skipped_large_file"` | **PASS** | 避免超大静态资源阻塞与耗尽内存 |
| **目录层次安全反推** | 从相对文件路径反推目录实体，严格以工程根为边界 | `extract_directory_hierarchy` 实现 | **PASS** | 绝不逃逸到操作系统的上一级磁盘路径 |

---

## 2. 成果物资产清单

1. `ingestion/git/client.py`：安全只读 Git CLI 封装器
2. `ingestion/filesystem/scanner.py`：文件扫描器、敏感过滤器、分块 Hash 与目录树反推器
3. 真实项目探测验证输出：三大源项目均确认具有标准 Git 工作树并成功提取当前 HEAD 与分支

---

## 3. 当前 MVP 完成情况评估

- **当前完成阶段**：MVP1 - Step 1.2 已通过。
- **状态评估**：Git 与文件系统的纯只读提取管道已打通，探测数据可信度达 100%，源项目未发生任何改动。
- **红线遵循核查**：
  - [x] 源项目纯只读（未执行任何 git checkout/pull/write 操作）
  - [x] 未引入 Tree-sitter
  - [x] Git 通过 subprocess 调用
  - [x] 严禁解析 .git 内部结构
  - [x] 敏感文件已在过滤层全部拦截

---

## 4. 下一任务规划与执行条件核查

- **下一任务**：**MVP1 - Step 1.3 清单解析、语言推导与框架检测器**
- **执行前置条件检查**：
  - [x] Step 1.2: Git 文件列表与文件元数据读取正常
  - [x] 5 大红线牢固遵守
- **Step 1.3 实施目标**：
  1. 实现 `ingestion/manifests/scanner.py`：
     - 解析 `package.json`（支持 npm/pnpm/yarn 生态，提取 dependencies, devDependencies）
     - 解析 `pom.xml`（Maven 生态依赖 groupId, artifactId, version 提取）
     - 解析 `pyproject.toml` / `requirements.txt`（Python 生态提取）
     - 检测包管理器类型（pnpm, yarn, npm, maven, uv, pip），多 lockfile 冲突标记 warning
  2. 实现 `ingestion/code/detector.py`：
     - 语言识别（基于扩展名映射与文件类型计数，支持 ts, tsx, vue, java, py, sql, json 等）
     - 框架与库检测器（Vue, React, Vite, Spring Boot, FastAPI），附带强证据链（例如 `package.json -> dependencies.vue`，置信度 0.99，检测方法 `package_manifest`）
     - 严格规则推导，严禁使用 LLM 幻觉生成
