# LKIO — Local Knowledge Intelligence OS

# MVP1 Project Ingestion 实施基线 v0.1

> 阶段：MVP1
> 名称：Project Ingestion
> 前置阶段：MVP0 Environment & Knowledge Core
> 当前状态：READY_TO_IMPLEMENT
> 基线来源：MVP0 Acceptance Report + LKIO MVP v0.1
> 核心原则：只读、可追溯、幂等、可恢复、可验证

------

# 1. MVP1 的唯一目标

让 LKIO 第一次能够真正“读取”三个真实项目，并将项目结构稳定映射到 Knowledge Core。

三个固定数据源：

```
HELLO_FE
C:\WorkSpace\hello

HELLO_BE
C:\WorkSpace\hello-backend

L2C_FE
C:\WorkSpace\L2C project
```

MVP1 完成以后，LKIO 必须能够回答：

```
这个项目是什么？
是不是 Git Repository？
当前 Branch 是什么？
当前 HEAD 是什么？
有哪些 Commit？
有哪些 Directory？
有哪些 File？
使用什么语言？
使用什么 Framework？
使用什么 Package Manager？
有哪些显式 Dependency？
上次扫描是什么时候？
这次扫描发现了什么？
```

------

# 2. MVP1 明确不做什么

以下能力全部禁止提前进入 MVP1：

```
Tree-sitter
AST
Code Symbol
Function
Class
Component dependency
API call graph
RAG
Embedding
Vector Search
LLM Wiki
Laya
Agent
Impact Analysis
Business Rule inference
自动修改源项目
自动生成代码
自动修改源项目 README
自动生成源项目文档
```

MVP1 只负责：

```
Project Metadata
+
Git Metadata
+
Filesystem Metadata
+
Manifest Metadata
```

------

# 3. MVP1 依赖

## 3.1 必须依赖

```
MVP0
PostgreSQL
pgvector
FastAPI
SQLAlchemy
Alembic
Python 3.12.10
uv
Git CLI
Vue 3
Element Plus
```

## 3.2 MVP1 不新增基础设施

禁止新增：

```
Neo4j
Qdrant
Milvus
Elasticsearch
Redis
Kafka
Temporal
LangChain
LlamaIndex
CrewAI
```

MVP1 数据继续存放 PostgreSQL。

------

# 4. Source 项目保护策略

三个源项目属于：

```
READ_ONLY SOURCE
```

LKIO 永远不得：

```
写文件
删除文件
修改文件
创建配置
创建缓存
创建 node_modules
创建 Python 环境
执行 npm install
执行 pnpm install
执行 yarn install
执行 pip install
执行构建
执行格式化
执行 lint --fix
执行 git commit
执行 git checkout
执行 git switch
执行 git merge
执行 git pull
执行 git fetch
```

尤其禁止：

```
npm install
pnpm install
yarn install
git pull
git checkout
git switch
```

原因：

这些操作虽然表面上是“读取项目”，实际上可能改变源项目工作区或 `.git` 状态。

------

# 5. Git CLI 唯一原则

所有 Git 信息必须使用：

```
Python subprocess
        ↓
git CLI
```

禁止：

```
直接解析 .git 内部文件
直接读取 objects
直接读取 refs 文件并自行解释
第三方 Git 数据库作为 MVP1 核心依赖
```

允许：

```
git rev-parse
git branch
git log
git ls-files
git status
git diff
git remote
git show
git config --get
```

全部使用：

```
subprocess.run(
    [...],
    cwd=project_path,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=...
)
```

------

# 6. Scanner 架构

MVP1 使用统一的 Ingestion Pipeline：

```
Project
   ↓
Source Resolver
   ↓
Repository Detector
   ↓
Git Metadata Scanner
   ↓
Filesystem Scanner
   ↓
Manifest Scanner
   ↓
Normalizer
   ↓
Entity Upsert
   ↓
Relation Upsert
   ↓
Scan Snapshot
   ↓
Ingestion Run
```

------

# 7. Source Resolver

输入：

```
project.local_path
```

例如：

```
C:\WorkSpace\hello
```

首先执行：

```
git -C "C:\WorkSpace\hello" rev-parse --is-inside-work-tree
```

结果：

```
true
```

则：

```
source_kind = git_repository
```

否则：

```
source_kind = filesystem
```

MVP1 必须支持两种模式。

即：

```
Git Project
Filesystem Project
```

------

# 8. Git Metadata

每一个 Repository 最低生成：

```
Repository
Branch
HEAD Commit
Remote
```

## 8.1 Repository

执行：

```
git -C "<path>" rev-parse --show-toplevel
```

保存：

```
repository_root
absolute_path
```

------

# 9. Branch

读取：

```
git -C "<path>" branch --show-current
```

如果处于 detached HEAD：

```
branch = null
branch_status = detached
```

不能假定一定存在 branch。

------

# 10. HEAD

执行：

```
git -C "<path>" rev-parse HEAD
```

保存：

```
commit_sha
```

这个值作为扫描版本的重要标识。

------

# 11. Remote

执行：

```
git -C "<path>" remote -v
```

只读取。

不允许：

```
git fetch
git pull
```

保存：

```
remote_name
remote_url
```

敏感信息处理：

如果 URL 包含：

```
https://username:password@
```

必须脱敏。

------

# 12. Commit Scan

MVP1 建议获取最近 N 个 Commit。

初始：

```
N = 100
```

后续配置化。

命令：

```
git -C "<path>" log -n 100 --date=iso-strict --pretty=format:%H%x1f%P%x1f%an%x1f%ae%x1f%ad%x1f%s%x1e
```

保存：

```
Commit
 ├── sha
 ├── parent_sha
 ├── author_name
 ├── author_email
 ├── authored_at
 └── subject
```

注意：

Commit 不应该存完整 patch。

MVP1 暂不存：

```
完整 diff
完整 patch
文件内容
```

------

# 13. Commit Entity

新增：

```
COMMIT
```

建议：

```
entity_key =
<project_key>:commit:<sha>
```

例如：

```
HELLO_FE:commit:8f12ab...
```

保证幂等。

------

# 14. Directory Scanner

Git 项目优先使用：

```
git ls-files -co --exclude-standard -z
```

然后从 file path 反推 Directory Entity。

例如：

```
src/components/lead/LeadList.vue
```

生成：

```
src
src/components
src/components/lead
```

但不生成：

```
C:\
C:\WorkSpace
```

Directory Root 必须以 Project Root 为边界。

------

# 15. File Scanner

File Entity：

```
FILE
```

核心字段：

```
project_id
relative_path
absolute_path
extension
size
mtime
sha256
is_binary
is_sensitive
```

其中：

```
relative_path
```

作为主要身份的一部分。

建议：

```
entity_key =
<project_key>:file:<normalized_relative_path>
```

------

# 16. File Hash

MVP1 默认计算：

```
SHA-256
```

但需要定义策略：

### 小文件

直接计算。

### 大文件

配置：

```
MAX_HASH_SIZE
```

超过后：

```
hash_status = skipped_large_file
```

不能因为某一个超大文件导致整个项目扫描失败。

------

# 17. 敏感文件保护

以下默认禁止进入：

```
.env
.env.*
*.pem
*.key
*.crt
*.p12
*.pfx
id_rsa
id_ed25519
credentials.json
service-account.json
secrets.*
secret.*
```

并且目录默认排除：

```
node_modules
.git
.vscode
.idea
dist
build
coverage
.next
.nuxt
target
vendor
.venv
__pycache__
.cache
tmp
temp
logs
```

必须允许项目级配置覆盖，但：

```
敏感文件禁止通过普通 include 重新启用
```

除非未来建立显式安全授权机制。

MVP1 不做该授权机制。

------

# 18. Lockfile 策略

以下文件允许读取：

```
package-lock.json
pnpm-lock.yaml
yarn.lock
npm-shrinkwrap.json
pom.xml
build.gradle
build.gradle.kts
go.mod
go.sum
requirements.txt
pyproject.toml
uv.lock
Cargo.toml
Cargo.lock
```

原因：

它们属于：

```
Dependency Metadata
```

而不是：

```
Secret
```

------

# 19. Language Detection

MVP1 不调用 LLM 判断语言。

通过：

```
extension
file signature
manifest
```

识别。

例如：

```
.ts       TypeScript
.tsx      TypeScript React
.js       JavaScript
.jsx      JavaScript React
.vue      Vue
.py       Python
.java     Java
.go       Go
.rs       Rust
.sql      SQL
.css      CSS
.scss     SCSS
.html     HTML
```

未知：

```
language = unknown
```

禁止猜测。

------

# 20. Framework Detection

Framework 采用：

```
manifest first
config second
file structure third
```

例如 package.json：

```
dependencies:
{
  "vue": "...",
  "react": "...",
  "next": "..."
}
```

得到：

```
Vue
React
Next.js
```

常见检测：

```
Vue
React
Next.js
Nuxt
Vite
Angular
Svelte
FastAPI
Django
Spring Boot
Gin
Fiber
Express
NestJS
```

检测结果必须携带：

```
detection_method
confidence
evidence
```

例如：

```
{
  "framework": "Vue",
  "confidence": 0.99,
  "method": "package_manifest",
  "evidence": "package.json -> dependencies.vue"
}
```

这里的 confidence 是：

```
Detection Confidence
```

不是 Laya Decision Confidence。

------

# 21. Package Manager Detection

规则：

```
pnpm-lock.yaml → pnpm
yarn.lock      → yarn
package-lock.json → npm
```

优先级：

```
pnpm
yarn
npm
```

如果同时存在多个 lockfile：

```
package_manager = conflict
```

不能自行选择。

同时创建：

```
warning
```

------

# 22. Dependency Entity

MVP1 生成：

```
DEPENDENCY
```

例如：

```
HELLO_FE
   ↓
Vue
   ↓
Element Plus
   ↓
Axios
```

不要在 MVP1 尝试理解：

```
这个依赖为什么被使用
这个依赖影响什么业务
这个依赖被哪个函数调用
```

那些属于 MVP2+。

------

# 23. Dependency 数据结构

建议：

```
dependency_name
version_spec
ecosystem
manifest_path
is_direct
```

例如：

```
axios
^1.8.0
npm
package.json
true
```

------

# 24. Manifest Entity

MVP1 建议增加：

```
MANIFEST
```

例如：

```
package.json
pnpm-lock.yaml
pom.xml
pyproject.toml
```

这样后续 Evidence 可以知道：

```
这个 Framework 是从哪个文件检测出来的
```

------

# 25. Relation

MVP1 新增：

```
PROJECT
 └── contains → REPOSITORY

REPOSITORY
 └── contains → BRANCH

REPOSITORY
 └── contains → COMMIT

REPOSITORY
 └── contains → DIRECTORY

DIRECTORY
 └── contains → FILE

PROJECT
 └── uses → LANGUAGE

PROJECT
 └── uses → FRAMEWORK

PROJECT
 └── depends_on → DEPENDENCY

PROJECT
 └── contains → MANIFEST
```

------

# 26. Relation Confidence

MVP1 所有关系统一：

```
confidence
extraction_method
evidence
```

例如：

```
{
  "confidence": 1.0,
  "extraction_method": "git_ls_files",
  "evidence": {
    "command": "git ls-files"
  }
}
```

因为这是确定事实。

Framework：

```
confidence = 0.99
```

Dependency：

```
confidence = 1.0
```

推断型关系：

```
confidence < 1
```

并明确：

```
inferred = true
```

------

# 27. 不允许伪置信度

MVP1 不允许：

```
LLM 给一个 0.87
```

然后保存成：

```
confidence = 0.87
```

confidence 必须与：

```
source
extraction method
evidence
```

绑定。

------

# 28. Ingestion Run

MVP1 必须新增：

```
ingestion_runs
```

用于记录每一次扫描。

字段：

```
id
project_id
source_id
status
started_at
finished_at
head_before
head_after
files_seen
files_created
files_updated
files_deleted
entities_created
entities_updated
relations_created
errors
warnings
metadata
```

状态：

```
PENDING
RUNNING
COMPLETED
PARTIAL
FAILED
```

------

# 29. 为什么必须有 Ingestion Run

因为后面会出现：

```
“为什么 Knowledge Graph 里有这个文件？”
```

必须能够回答：

```
这个 File 是由：
2026-09-24 20:31
HELLO_FE
Ingestion Run #1042
从 package.json / git ls-files
扫描出来的
```

这就是后续 Evidence / Audit 的基础。

------

# 30. Scan Snapshot

MVP1 建议加入：

```
project_snapshots
```

保存：

```
project
head
branch
file_count
directory_count
dependency_count
frameworks
languages
created_at
```

它不保存全部文件内容。

作用：

```
Snapshot A
      ↓
Snapshot B
      ↓
Change
```

为 MVP5 Event Store 提供基础。

------

# 31. 幂等规则

核心原则：

```
Same Source
+
Same Identity
=
Same Entity
```

Entity Key：

```
PROJECT
project.key

REPOSITORY
project.key + repository.root

FILE
project.key + normalized_relative_path

COMMIT
project.key + commit.sha

DEPENDENCY
project.key + ecosystem + dependency.name

MANIFEST
project.key + relative_path
```

禁止使用：

```
UUID only
```

作为唯一业务身份。

UUID 是数据库 ID。

Entity Key 才是逻辑身份。

------

# 32. 删除策略

如果第二次扫描发现：

```
旧文件不存在
```

不要直接：

```
DELETE
```

MVP1 推荐：

```
status = deleted
```

保留历史实体。

这样未来：

```
Event
Historical Graph
Impact Analysis
```

都可以使用。

------

# 33. Partial Failure

三个项目扫描必须隔离。

例如：

```
HELLO_FE       SUCCESS
HELLO_BE       SUCCESS
L2C_FE         FAILED
```

整个 ingestion batch：

```
PARTIAL
```

不能：

```
全部 rollback
```

一个项目坏掉不能污染其他项目。

------

# 34. Timeout

单个命令必须有：

```
timeout
```

建议初始：

```
Git command: 30s
Filesystem scan: 120s
Hashing: 120s
```

后续配置化。

------

# 35. Worker

MVP1 可以采用：

```
FastAPI
  +
Background Task / CLI Worker
```

暂时不要：

```
Celery
Kafka
Temporal
```

推荐：

```
lkio ingest scan --project HELLO_FE
```

以及：

```
lkio ingest scan-all
```

这样本地开发容易测试。

------

# 36. CLI

MVP1 建议建立：

```
lkio project list
lkio project scan HELLO_FE
lkio project scan HELLO_BE
lkio project scan L2C_FE
lkio project scan-all
lkio ingestion list
lkio ingestion show <run_id>
```

API：

```
POST /api/v1/projects/{project_key}/scan
GET  /api/v1/projects/{project_key}/scan-runs
GET  /api/v1/ingestion-runs/{run_id}
```

------

# 37. 前端 MVP1

在现有 MVP0 UI 基础上，只增加：

```
Project Detail
```

页面：

```
Project Overview

Repository
Current Branch
Current HEAD
Last Scan
Frameworks
Languages
Dependencies
Files
Directories
Recent Commits
Scan History
```

禁止增加：

```
RAG
Wiki
Agent
Decision
Impact
Chat
```

------

# 38. Project Overview

例如：

```
HELLO_FE

Path:
C:\WorkSpace\hello

Type:
Frontend

Git:
✓

Branch:
main

HEAD:
8f12ab3

Framework:
Vue 3
Vite

Languages:
TypeScript
Vue
CSS

Dependencies:
127

Files:
241

Last Scan:
2026-09-24 21:32

Status:
Healthy
```

------

# 39. Scan UI

点击：

```
Scan
```

显示：

```
Scanning HELLO_FE...

Repository        ✓
Git Metadata      ✓
Branches          ✓
Commits           ✓
Directories       ✓
Files             ✓
Languages         ✓
Framework         ✓
Dependencies      ✓
```

结束：

```
Completed

Files: +12 ~8 -2
Dependencies: 43
Warnings: 1
Errors: 0
```

------

# 40. Evidence UI

MVP1 虽然还没有完整 Evidence 系统，但至少显示：

```
Framework: Vue

Detected from:
package.json

Method:
package_manifest
```

这样从第一天开始就不允许：

```
“AI 猜出来的结论”
```

伪装成：

```
“事实”
```

------

# 41. 测试

MVP1 测试必须包含：

```
Git detection
Branch detection
HEAD detection
Commit parsing
File scan
Directory scan
Language detection
Framework detection
Dependency detection
Sensitive file exclusion
Manifest detection
Idempotency
Deleted file
Partial failure
Timeout
Read-only guarantee
```

------

# 42. Read-only 自动测试

这是 MVP1 的核心测试。

扫描之前记录：

```
git status --porcelain
```

扫描结束再次：

```
git status --porcelain
```

必须一致。

并对工作区做文件树 hash：

```
before_tree_hash
after_tree_hash
```

必须一致。

------

# 43. 三项目固定验收

## HELLO_FE

必须能够识别：

```
Git
Branch
HEAD
Files
Directories
Framework
Languages
Dependencies
```

## HELLO_BE

同上。

## L2C_FE

同上。

其中 L2C 项目即使尚未开始业务开发，也必须被正常识别为：

```
Framework / Repository / File Tree
```

不得因为“业务内容少”而判定异常。

------

# 44. MVP1 Gold Data

在正式验收前，人工确认：

```
HELLO_FE
HELLO_BE
L2C_FE
```

各自：

```
Repository Root
Current Branch
HEAD
Top-level directories
Framework
Package Manager
Top-level dependencies
```

将这些结果保存为：

```
tests/gold/mvp1/
```

后续每次改 ingestion engine 都必须跑 regression。

------

# 45. MVP1 验收门

只有全部通过才能进入 MVP2。

```
A. 三项目全部扫描成功
B. Git metadata 正确
C. Branch 正确
D. HEAD 正确
E. File Tree 正确
F. Framework 正确
G. Language 正确
H. Dependency 正确
I. 敏感文件全部排除
J. 重扫幂等
K. Deleted File 正确标记
L. Partial Failure 正常
M. Ingestion Run 可追踪
N. Source Project 内容零修改
O. UI 可以查看扫描结果
P. Gold Set Regression 全通过
```

------

# 46. MVP1 DoD

必须同时满足：

```
[ ] 三项目扫描
[ ] Git Repository Detection
[ ] Branch
[ ] HEAD
[ ] Commit
[ ] Directory
[ ] File
[ ] Language
[ ] Framework
[ ] Package Manager
[ ] Dependency
[ ] Manifest
[ ] Ingestion Run
[ ] Snapshot
[ ] Read-only
[ ] Sensitive File Protection
[ ] Idempotency
[ ] Partial Failure
[ ] Regression Gold Set
```

------

# 47. MVP1 禁止改变的架构原则

后续 Agent 不得擅自：

```
把 PostgreSQL 换成 Neo4j
把 pgvector 换成 Qdrant
引入 Elasticsearch
引入 Redis
引入 Kafka
引入 LangChain
引入 LlamaIndex
引入 Tree-sitter
引入 Laya
```

除非：

```
ADR
+
技术验证
+
明确影响分析
+
人工批准
```

------

# 48. MVP1 完成后得到什么

系统将从：

```
“有三个项目”
```

进化到：

```
“系统已经知道三个项目是什么”
```

Knowledge Graph 第一阶段：

```
HELLO_FE
 ├── Repository
 ├── Branch
 ├── Commit
 ├── Directory
 ├── File
 ├── Language
 ├── Framework
 └── Dependency

HELLO_BE
 ├── Repository
 ├── Branch
 ├── Commit
 ├── Directory
 ├── File
 ├── Language
 ├── Framework
 └── Dependency

L2C_FE
 ├── Repository
 ├── Branch
 ├── Commit
 ├── Directory
 ├── File
 ├── Language
 ├── Framework
 └── Dependency
```

到这里，MVP2 才可以开始做：

```
Code Symbol
AST
Frontend → API
API → Backend
Backend → DB
Cross-project Code Graph
```

------

# 49. MVP1 → MVP2 的阶段门

MVP1 结束以后不得直接开发任何业务智能能力。

必须先确认：

```
项目身份稳定
文件身份稳定
扫描幂等稳定
Evidence 稳定
Source 只读稳定
Ingestion Run 稳定
Gold Dataset 稳定
```

确认以后才允许：

```
Tree-sitter
AST
Code Symbol
API Detection
Cross-project Code Graph
```

------

# 50. LKIO 长期演进路线

```
MVP0
Environment + Knowledge Core
        ↓
MVP1
Project Ingestion
        ↓
MVP2
Code Intelligence + Cross Project Graph
        ↓
MVP3
Hybrid RAG
        ↓
MVP4
LLM Wiki
        ↓
MVP5
Event / Change Intelligence
        ↓
MVP6
Laya Decision Engine
        ↓
MVP7
Impact Analysis
        ↓
MVP8
Evaluation / Calibration / Fine-tuning
```

长期目标：

```
Source
  ↓
Knowledge
  ↓
Graph
  ↓
Evidence
  ↓
RAG
  ↓
Decision
  ↓
Action
  ↓
Outcome
  ↓
Learning
```

任何新增功能，都必须能够回答：

```
它属于哪个 MVP？
它依赖什么？
它产出什么？
谁消费这个产出？
有没有提前越过阶段边界？
```

如果不能回答，则不得进入主干。