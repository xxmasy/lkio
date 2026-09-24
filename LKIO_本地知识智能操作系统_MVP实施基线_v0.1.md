# Local Knowledge Intelligence OS（LKIO）
## MVP 分阶段实施总方案 v0.1

> 目标：在 Windows 本地建立一套“项目知识 + 代码拓扑 + 业务逻辑 + 变更历史 + 跨项目关系 + RAG + Decision Model”的长期知识系统。
>
> 本版本是**实施基线**，不是概念稿。后续每个 MVP 必须依赖前一阶段的验收结果才能继续；任何新技术、数据库、模型、Agent 加入都必须符合本文件的“变更控制”规则。
>
> 基线日期：2026-09-24

---

# 0. 最终目标与第一阶段边界

## 0.1 第一批纳管项目

| Project Key | 类型 | 本地路径 | 初始角色 | 优先级 |
|---|---|---|---|---:|
| `HELLO_FE` | Frontend | `C:\WorkSpace\hello` | 首要前端项目 | P0 |
| `HELLO_BE` | Backend | `C:\WorkSpace\hello-backend` | HELLO_FE 配套后端 | P0 |
| `L2C_FE` | Frontend | `C:\WorkSpace\L2C project` | 即将开发的前端项目，已有框架 | P1 |

### 固定原则

1. LKIO 对这三个源项目默认是**只读**。
2. LKIO 第一阶段只读取，不修改源项目文件。
3. 源项目不会被复制进 LKIO 仓库；只保存元数据、结构化实体、关系、必要的索引和哈希。
4. `.env`、密钥、证书、token、私钥等敏感内容默认不入库。
5. Git 历史通过 Git CLI 读取；不直接解析 `.git` 内部文件。
6. 以后任何 AI Agent 想写入源项目，必须经过单独的 Action Gate，属于后续 MVP，不在 MVP0~MVP5 开放。

---

# 1. 系统定义

## 1.1 LKIO 不定义为普通 RAG

LKIO 的核心是：

```text
                Local Knowledge Intelligence OS
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

### 四个世界统一

```text
Code World
Business World
Runtime / Operation World
Decision / History World
```

最终希望回答：

- 这个功能是什么？
- 它在哪里实现？
- 前后端怎么联动？
- 它依赖什么？
- 为什么这么设计？
- 谁什么时候改过？
- 修改它会影响什么？
- 过去是否出现过类似问题？
- 当前证据有多可信？
- AI 应不应该自动执行？

---

# 2. 不允许方向漂移的“架构宪法”

## 2.1 必须遵守

### A. Knowledge Source 与 Knowledge Projection 分离

真实事实来源：

```text
Git
DB Schema
Source Code
Human Decision
Operational Event
Documents
```

Wiki / RAG / LLM 只能做投影和推理，不成为事实唯一来源。

### B. Graph 与 Vector 各司其职

```text
Graph  = 谁和谁是什么关系
Vector = 哪些内容在语义上相关
Keyword = 精确命中代码/ID/API/字段
Event = 什么时候发生过什么
```

禁止用 Vector DB 模拟 Graph。

### C. Confidence ≠ Truth

所有 Decision 必须区分：

```text
model_confidence
 evidence_confidence
graph_confidence
 historical_accuracy
 final_confidence
```

禁止直接把 Laya 的 confidence 当成“事实正确率”。

### D. 默认允许拒答

任何 Decision Model 都必须允许：

```text
UNKNOWN
INSUFFICIENT_EVIDENCE
NEED_HUMAN_REVIEW
```

### E. 先评测，再训练

没有 Gold Dataset 和 Evaluation Harness，不允许 fine-tune Laya。

### F. 第一阶段不做“超级 Agent”

Agent 只能在已有：

```text
Ontology
Graph
Evidence
RAG
Event
Decision Policy
```

之后再加入。

---

# 3. 第一版技术路线最终锁定

## 3.1 应用层

### Backend

- Python 3.12.10
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic
- psycopg
- uv

Python 3.12.10 是 3.12 系列最后一个提供传统 Windows binary installer 的完整 bugfix 版本；Python 3.12.14 已进入 security-only 且不再提供 Windows installer，因此当前基线固定 3.12.10，避免短期内因为 Python 3.14/3.13 的兼容性变化干扰 Laya/ML 依赖。  
官方：[Python 3.12.10](https://www.python.org/downloads/release/python-31210/)

### Frontend

- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router
- Cytoscape.js

Vue 官方当前推荐通过 `create-vue` 创建 Vite 项目；当前 Vue 文档要求 Node.js `^22.18.0 || >=24.12.0`。因此本基线选择 Node.js 24 LTS。  
官方：[Vue Quick Start](https://vuejs.org/guide/quick-start)

### Database

- PostgreSQL 18
- pgvector 0.8.x
- 第一阶段：普通 Relation Model
- 后续：在 PostgreSQL 内继续扩展 Graph / ltree 等能力；只有出现明确规模瓶颈时才考虑独立 Graph DB。

PostgreSQL 18 是当前稳定主版本，2026-08-13 已发布 18.6；pgvector 官方 Docker 镜像当前提供 `0.8.6-pg18`。  
官方：[PostgreSQL 18](https://www.postgresql.org/docs/18/)  
pgvector：[GitHub](https://github.com/pgvector/pgvector)  
Docker Image：[pgvector/pgvector](https://hub.docker.com/r/pgvector/pgvector)

### Code Parsing

- Tree-sitter
- Python bindings
- 各语言 grammar package
- Git CLI

Tree-sitter 是增量解析器/语法树工具，官方提供 Python、JavaScript、Go 等 bindings；Python package 提供主流平台预编译 wheel。  
官方：[Tree-sitter](https://tree-sitter.github.io/tree-sitter/)  
Python：[tree-sitter](https://pypi.org/project/tree-sitter/)

### Decision

第一阶段只预留接口，不接 Laya。

MVP6 才正式接：

- `laya`
- `convaiinnovations/laya-typed-decisions`
- 本地 CPU/GPU inference
- Calibration
- Decision Policy

Laya 当前公开架构包含 English、multilingual、typed-decisions 三个 checkpoint；typed-decisions checkpoint 为 421M ModernBERT-large，当前仓库提供 1024 token context 的 typed decision 模型。  
官方仓库：[he-jev/laya](https://github.com/he-jev/laya)  
模型：[convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya)  
Typed decisions：[convaiinnovations/laya-typed-decisions](https://huggingface.co/convaiinnovations/laya-typed-decisions)

### Local LLM

第一阶段不绑定任何 LLM。

MVP3/MVP4 再接入 Local LLM Gateway。

优先支持：

- Ollama
- LM Studio
- OpenAI-compatible local endpoint

Ollama 当前 Windows 版本原生支持 Windows，并提供 `localhost:11434` API；LM Studio 也支持 Windows、本地模型和 OpenAI-compatible API。  
Ollama：[Windows Download](https://ollama.com/download/windows)  
LM Studio：[Download](https://lmstudio.ai/download)

---

# 4. 外部软件 / 项目 / 插件安装清单

## 4.1 必装

### Docker Desktop

用途：只负责本地 PostgreSQL / pgvector 等基础设施，不承担业务代码。

官方下载：
https://docs.docker.com/desktop/setup/install/windows-install/

Windows 当前推荐 WSL2 backend；Docker Desktop 支持 per-user installation。大型商业组织的授权条件需要根据 Docker 当前订阅条款判断。  
来源：https://docs.docker.com/desktop/setup/install/windows-install/

### Node.js 24 LTS

官方下载：
https://nodejs.org/en/download/current

当前页面列出的 LTS 包括 24.21.0；Vue 当前文档要求 `^22.18.0 || >=24.12.0`。  
来源：https://nodejs.org/en/download/current

### Python 3.12.10

官方下载：
https://www.python.org/downloads/release/python-31210/

### uv

官方下载：
https://docs.astral.sh/uv/getting-started/installation/

Windows PowerShell 官方安装方式：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

也可以：

```powershell
winget install --id=astral-sh.uv -e
```

uv 会生成项目虚拟环境和 `uv.lock`，因此它作为 Python 依赖锁定工具。  
来源：https://docs.astral.sh/uv/getting-started/installation/

### Git

官方下载：
https://git-scm.com/download/win

---

# 5. VS Code / Cursor 扩展

只装必要项，禁止一开始安装一大堆扩展包。

## 必装

### Vue (Official)

Extension ID：

```text
Vue.volar
```

Marketplace：
https://marketplace.visualstudio.com/items?itemName=Vue.volar

官方扩展提供 Vue SFC 语言服务、类型推断、诊断、导航和重构能力。  
来源：https://marketplace.visualstudio.com/items?itemName=Vue.volar

### Python

Extension ID：

```text
ms-python.python
```

Marketplace：
https://marketplace.visualstudio.com/itemdetails?itemName=ms-python.python

### Container Tools

Extension ID：

```text
ms-azuretools.vscode-containers
```

Marketplace：
https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-containers

微软当前的 Container Tools 已覆盖 Dockerfile / Compose 编辑、Container Explorer、Compose 操作等。  
来源：https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-containers

## 可选

### Ruff

仅在 LKIO Python backend 稳定后安装。

### ESLint

只在 LKIO frontend 进入稳定开发后安装；不要先把 lint 规则复杂化。

---

# 6. LKIO 本身的目录约定

固定工作目录：

```text
C:\WorkSpace\lkio
```

数据目录：

```text
C:\WorkSpace\lkio-data
```

三套源项目保持原位置，不迁移：

```text
C:\WorkSpace\hello
C:\WorkSpace\hello-backend
C:\WorkSpace\L2C project
```

完整结构：

```text
C:\WorkSpace\
│
├── hello\                  # 源项目，只读
├── hello-backend\          # 源项目，只读
├── L2C project\            # 源项目，只读
│
├── lkio\                   # LKIO 自己的 Git Repository
│   ├── apps\
│   │   ├── api\
│   │   ├── web\
│   │   └── worker\
│   │
│   ├── core\
│   │   ├── ontology\
│   │   ├── entity\
│   │   ├── relation\
│   │   ├── source\
│   │   ├── event\
│   │   ├── evidence\
│   │   └── decision\
│   │
│   ├── ingestion\
│   │   ├── filesystem\
│   │   ├── git\
│   │   ├── manifests\
│   │   └── code\
│   │
│   ├── retrieval\
│   │   ├── keyword\
│   │   ├── semantic\
│   │   ├── code\
│   │   ├── graph\
│   │   └── rerank\
│   │
│   ├── intelligence\
│   │   ├── rag\
│   │   ├── wiki\
│   │   ├── impact\
│   │   └── analytics\
│   │
│   ├── decision\
│   │   ├── adapters\
│   │   ├── laya\
│   │   ├── calibration\
│   │   ├── policy\
│   │   └── evaluation\
│   │
│   ├── infra\
│   │   ├── compose.yaml
│   │   ├── db\
│   │   └── scripts\
│   │
│   ├── docs\
│   │   ├── architecture\
│   │   ├── ontology\
│   │   ├── mvp\
│   │   └── adr\
│   │
│   ├── tests\
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── MVP.md
│   └── CHANGELOG.md
│
└── lkio-data\
    ├── backups\
    ├── exports\
    ├── model-cache\
    └── logs\
```

---

# 7. 多项目身份固定规则

在第一批项目注册时，不允许依赖目录名猜业务身份；项目 Identity 必须显式配置。

`config/projects.yaml`：

```yaml
projects:
  - key: HELLO_FE
    name: hello
    kind: frontend
    role: primary_frontend
    local_path: C:\\WorkSpace\\hello
    enabled: true

  - key: HELLO_BE
    name: hello-backend
    kind: backend
    role: paired_backend
    local_path: C:\\WorkSpace\\hello-backend
    enabled: true
    related_projects:
      - HELLO_FE

  - key: L2C_FE
    name: L2C project
    kind: frontend
    role: future_frontend
    local_path: C:\\WorkSpace\\L2C project
    enabled: true
```

后续项目的 `kind / role / relation` 必须从配置进入系统，不能让 LLM 自由猜。

---

# 8. MVP 总依赖图

```text
MVP0 Environment + Knowledge Core
        │
        ▼
MVP1 Project Ingestion
        │
        ▼
MVP2 Code / AST / Cross-project Graph
        │
        ├──────────────┐
        ▼              ▼
MVP3 Hybrid RAG     MVP5 Event & Change
        │              │
        └──────┬───────┘
               ▼
          MVP4 LLM Wiki
               │
               ▼
        MVP6 Laya Decision
               │
               ▼
        MVP7 Impact Engine
               │
               ▼
        MVP8 Evaluation / Learning Loop
```

### 严格依赖关系

| MVP | 依赖 | 核心产物 | 可否提前做后续 |
|---|---|---|---|
| MVP0 | 环境 | Knowledge Core | 不可 |
| MVP1 | MVP0 | 三项目真实数据 | 不可 |
| MVP2 | MVP1 | Code Graph | 部分可 |
| MVP3 | MVP1，推荐 MVP2 | Hybrid RAG | 不建议跳过 Graph |
| MVP4 | MVP3 + Source/Evidence | Wiki | 不可 |
| MVP5 | MVP1 | Event/Change | 可与 MVP3 并行 |
| MVP6 | MVP4 + MVP5 | Decision Engine | 不可 |
| MVP7 | MVP2 + MVP5 + MVP6 | Impact Analysis | 不可 |
| MVP8 | MVP6 + 真实 Outcome | Calibration/Fine-tune | 不可 |

---

# 9. MVP0 —— Knowledge Core

## 9.1 MVP0 目标

系统第一次可以：

```text
认识项目
认识实体
认识关系
看到图
```

不做：

```text
RAG
LLM
Laya
AST
Agent
自动扫描完整代码
自动写代码
```

## 9.2 MVP0 技术依赖

```text
Windows
Docker Desktop
PostgreSQL/pgvector
Python 3.12.10
uv
FastAPI
SQLAlchemy
Alembic
Node 24 LTS
Vue 3
Cytoscape.js
Element Plus
```

## 9.3 初始化 LKIO

PowerShell：

```powershell
cd C:\WorkSpace
mkdir lkio
cd lkio
git init
```

初始化 Python：

```powershell
uv init --bare
uv python pin 3.12.10
uv add "fastapi[standard]"
uv add sqlalchemy
uv add alembic
uv add "psycopg[binary]"
uv add pydantic-settings
uv add python-dotenv
uv add orjson
uv add httpx
uv add rich
uv add pyyaml
uv add typer
uv add pytest
uv add pytest-asyncio
```

FastAPI 当前官方教程直接推荐 `uv init`、`uv add "fastapi[standard]"`，并利用 `uv.lock` 锁定环境。  
来源：https://fastapi.tiangolo.com/tutorial/

SQLAlchemy 2.0 是当前稳定主线；Alembic 用于数据库 schema migration。  
来源：https://docs.sqlalchemy.org/en/20/  
来源：https://alembic.sqlalchemy.org/en/latest/tutorial.html

## 9.4 初始化 Frontend

```powershell
cd C:\WorkSpace\lkio
npm create vue@latest web
```

选择：

```text
TypeScript        Yes
JSX               No
Vue Router        Yes
Pinia             Yes
Vitest            Yes
E2E               No（MVP0 暂不需要）
ESLint            Yes
Prettier           Yes
```

安装：

```powershell
cd web
npm install
npm install element-plus
npm install cytoscape
npm install axios
npm run dev
```

Vue 官方 `create-vue` 会创建 Vite 项目，并可选 TypeScript / Router / Pinia / Vitest / ESLint / Prettier。  
来源：https://vuejs.org/guide/quick-start

Element Plus 官方安装方式使用 npm/pnpm；当前兼容 Vue 3。  
来源：https://element-plus.org/en-US/guide/installation

Cytoscape.js 用于后续实体关系图展示。  
来源：https://js.cytoscape.org/

---

# 10. MVP0 数据模型

第一版不要搞复杂 Ontology DB。

## 10.1 `projects`

字段：

```text
id UUID PK
key VARCHAR(64) UNIQUE
name VARCHAR(255)
kind VARCHAR(32)
role VARCHAR(64)
local_path TEXT
status VARCHAR(32)
description TEXT
metadata JSONB
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### `kind` 初始枚举

```text
frontend
backend
fullstack
service
library
unknown
```

### `role` 初始值

```text
primary_frontend
paired_backend
future_frontend
supporting_service
unknown
```

---

## 10.2 `sources`

```text
id UUID PK
project_id UUID FK
source_type VARCHAR(64)
uri TEXT
read_only BOOLEAN
enabled BOOLEAN
config JSONB
last_scan_at TIMESTAMPTZ
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

第一种 source：

```text
local_git_repository
```

---

## 10.3 `entities`

```text
id UUID PK
project_id UUID NULL FK
entity_type VARCHAR(64)
entity_key VARCHAR(255)
name VARCHAR(255)
canonical_name VARCHAR(255)
path TEXT NULL
status VARCHAR(32)
metadata JSONB
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

初始 Entity Types：

```text
PROJECT
REPOSITORY
FRONTEND
BACKEND
DIRECTORY
FILE
MODULE
PAGE
COMPONENT
SERVICE
API
DATABASE
TABLE
BUSINESS_DOMAIN
BUSINESS_PROCESS
BUSINESS_RULE
DOCUMENT
EXTERNAL_SERVICE
```

---

## 10.4 `relations`

```text
id UUID PK
subject_entity_id UUID FK
predicate VARCHAR(128)
object_entity_id UUID FK
confidence NUMERIC(6,5)
source_id UUID NULL FK
metadata JSONB
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

唯一约束：

```text
(subject_entity_id, predicate, object_entity_id)
```

第一阶段关系：

```text
contains
belongs_to
paired_with
depends_on
uses
implements
calls
reads
writes
affects
owned_by
related_to
```

---

# 11. MVP0 Seed：三个真实项目

第一次不扫描代码，先用注册信息创建实体。

### HELLO_FE

```text
PROJECT
  └── REPOSITORY
       └── FRONTEND
```

### HELLO_BE

```text
PROJECT
  └── REPOSITORY
       └── BACKEND
```

### L2C_FE

```text
PROJECT
  └── REPOSITORY
       └── FRONTEND
```

### 跨项目关系

```text
HELLO_FE
   │
   └── paired_with → HELLO_BE
```

暂时不要人为给 L2C 添加和 HELLO 的关系。

---

# 12. MVP0 Backend API

第一版只实现：

```http
GET  /api/v1/health
GET  /api/v1/projects
POST /api/v1/projects
GET  /api/v1/projects/{project_id}
GET  /api/v1/entities
POST /api/v1/entities
GET  /api/v1/entities/{entity_id}
GET  /api/v1/relations
POST /api/v1/relations
GET  /api/v1/graph/projects/{project_id}
GET  /api/v1/graph/entities/{entity_id}/neighbors
```

全部返回标准：

```json
{
  "data": {},
  "meta": {
    "request_id": "..."
  },
  "error": null
}
```

错误统一：

```text
400 validation_error
404 not_found
409 conflict
500 internal_error
```

---

# 13. MVP0 Frontend

## 页面

```text
/overview
/projects
/projects/:id
/graph
```

## Sidebar

第一阶段只显示已实现功能：

```text
Overview
Projects
Graph
```

不要提前显示：

```text
RAG
Wiki
Agent
Decision
Impact
```

避免产品方向漂移。

## Overview

显示：

```text
Projects: 3
Frontend: 2
Backend: 1
Entities: x
Relations: x
Sources: 3
```

## Project Detail

显示：

```text
Name
Type
Role
Local Path
Status
Related Projects
Entity Count
Relation Count
```

## Graph

Cytoscape：

- 节点：Entity
- 边：Relation
- 节点颜色按 entity_type
- 点击节点打开详情
- 点击边显示 predicate
- 双击节点进入 neighborhood view

禁止在 MVP0 做 3D Graph。

---

# 14. MVP0 验收标准

全部通过才进入 MVP1。

### A. 环境

```powershell
docker version
node -v
npm -v
python --version
uv --version
git --version
```

### B. DB

```powershell
docker compose -f infra/compose.yaml up -d postgres
```

验证：

```powershell
docker ps
```

必须能看到 PostgreSQL healthy。

### C. API

```powershell
uv run fastapi dev apps/api/main.py
```

访问：

```text
http://127.0.0.1:8000/api/v1/health
```

返回：

```json
{
  "status": "ok"
}
```

### D. Frontend

```powershell
cd apps/web
npm run dev
```

打开：

```text
http://127.0.0.1:5173
```

### E. 三项目

必须显示：

```text
hello
hello-backend
L2C project
```

### F. Graph

至少显示：

```text
HELLO_FE → paired_with → HELLO_BE
```

### G. 数据幂等

重复执行 seed：

```text
不能重复产生项目
不能重复产生 Entity
不能重复产生 Relation
```

---

# 15. MVP1 —— Project Ingestion

## 15.1 目标

从这三个真实目录中读取结构：

```text
Git
Filesystem
package manifests
project metadata
```

自动产生：

```text
Repository
Branch
Commit
Directory
File
Language
Framework
Package Manager
Dependency
```

## 15.2 依赖

```text
MVP0
Python subprocess
Git CLI
```

暂不需要 Tree-sitter。

## 15.3 Git 检测

对每个项目：

```powershell
git -C "C:\WorkSpace\hello" rev-parse --is-inside-work-tree
git -C "C:\WorkSpace\hello" rev-parse HEAD
git -C "C:\WorkSpace\hello" branch --show-current
```

如果不是 Git repository：

```text
source_type = local_filesystem
```

但系统仍可继续运行。

## 15.4 文件清单

优先使用：

```text
git ls-files -co --exclude-standard -z
```

否则退化到 filesystem scanner。

默认排除：

```text
node_modules
.git
.vscode
.idea
dist
build
coverage
.next
.nuxt
output
out
target
vendor
.venv
__pycache__
logs
tmp
cache
```

敏感文件排除：

```text
.env
.env.*
*.pem
*.key
*.p12
*.pfx
id_rsa
credentials.json
secrets.*
```

但：

```text
package-lock.json
pnpm-lock.yaml
yarn.lock
pom.xml
build.gradle
pyproject.toml
requirements.txt
go.mod
go.sum
```

可以读取，用于依赖分析。

## 15.5 Framework Detection

不要硬编码 `hello` 是什么框架。

按 manifest / config 判断：

```text
package.json
vite.config.*
next.config.*
nuxt.config.*
tsconfig.json
pom.xml
build.gradle
go.mod
pyproject.toml
requirements.txt
```

结果存入：

```text
entities.metadata.framework
entities.metadata.language
entities.metadata.package_manager
```

必须允许：

```text
unknown
```

## 15.6 MVP1 输出

每个项目自动生成：

```text
Project
Repository
Directories
Files
Languages
Framework
Dependencies
Current Commit
Current Branch
```

---

# 16. MVP1 增量同步机制

每次扫描之前读取：

```text
previous_head
current_head
```

若：

```text
previous_head == current_head
```

不重新扫描所有 Git metadata。

若 HEAD 改变：

```text
compute diff
→ affected files
→ update only affected entities
```

第一阶段可以先做到全量扫描 + 增量架构预留；不要因为过早优化复杂化代码。

---

# 17. MVP1 验收门

三个项目必须完成：

```text
HELLO_FE
HELLO_BE
L2C_FE
```

全部可以：

```text
Register
Scan
Re-scan
```

且：

1. 源项目没有任何文件被修改。
2. 同一个文件不会出现多个 Entity。
3. 重复扫描不会产生重复实体。
4. HEAD 变化后只更新受影响数据。
5. 扫描失败只影响对应项目，不拖死整个 Worker。
6. 所有 ingestion run 都有日志。

---

# 18. MVP2 —— AST / Code Graph / Cross-project Graph

## 18.1 目标

从“文件树”进入“代码结构”。

例如：

```text
LeadPage.vue
  ↓
function loadLeads()
  ↓
leadStore
  ↓
GET /api/leads
  ↓
LeadController
  ↓
LeadService
```

## 18.2 核心依赖

```text
MVP1
Tree-sitter
language grammars
```

## 18.3 Tree-sitter 解析对象

第一阶段统一抽象：

```text
CodeSymbol
```

symbol_type：

```text
function
class
interface
type
variable
constant
component
route
api
sql
method
```

保存：

```text
file_entity_id
name
symbol_type
start_line
end_line
signature
language
ast_hash
```

## 18.4 Vue SFC

`.vue` 文件需要特殊处理：

```text
<template>
<script>
<script setup>
<style>
```

第一阶段重点解析：

```text
<script>
<script setup>
```

采用 TypeScript / JavaScript grammar。

不要第一期建立完整 HTML AST → Business Graph。

## 18.5 API Relationship Discovery

按框架适配器实现：

```text
Vue / Axios / Fetch
React / Fetch / Axios
OpenAPI
Java Spring
Go HTTP
FastAPI
```

第一阶段只识别显式模式。

例如：

```text
axios.get('/api/leads')
fetch('/api/leads')
```

而复杂动态拼接：

```text
baseUrl + routeMap[key]
```

标记：

```text
relation_confidence = inferred
```

而不是当成确定关系。

---

# 19. Cross-project Graph

这里第一次出现真正的跨项目拓扑。

例如：

```text
HELLO_FE
    │
    ├── calls → API
    │              │
    │              ▼
    │          HELLO_BE
    │              │
    │              └── reads/writes → database
    │
    └── depends_on → shared library
```

L2C 暂时独立：

```text
L2C_FE
```

除非扫描证据发现它与 hello 有共享包/API/代码依赖，不主动建立关系。

---

# 20. MVP2 图谱的数据可信度

每一条关系必须带：

```text
source_type
source_id
confidence
extraction_method
```

例如：

```json
{
  "predicate": "calls",
  "confidence": 0.99,
  "extraction_method": "AST_LITERAL_HTTP_CALL",
  "source_type": "CODE"
}
```

推测：

```json
{
  "confidence": 0.62,
  "extraction_method": "LLM_INFERENCE"
}
```

---

# 21. MVP3 —— Hybrid RAG

## 21.1 目标

开始允许自然语言查询，但不让 LLM 直接面对整个数据库。

## 21.2 检索层

```text
                 Query
                   │
            Query Classifier
                   │
        ┌──────────┼──────────┐
        │          │          │
     Keyword     Vector     Graph
        │          │          │
        └──────────┼──────────┘
                   ▼
                 Merge
                   ▼
                Rerank
                   ▼
                Evidence
```

## 21.3 Embedding

V1 推荐：

```text
BAAI/bge-m3
```

原因：支持 100+ languages、dense/sparse/multi-granularity，1024 dimension、最长 8192 tokens，适合中文 + 英文代码/文档混合场景。  
模型参考：https://huggingface.co/BAAI/bge-m3

注意：代码符号本身不应该依赖 embedding 检索；代码实体优先通过 keyword + symbol index。

## 21.4 pgvector

第一阶段：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

向量只用于：

```text
document_chunk
code_semantic_chunk
business_rule
wiki_section
decision_evidence
```

不要给每一个小变量生成 embedding。

---

# 22. MVP3 Retrieval Index 设计

至少建立五个索引概念：

```text
1. entity_index
2. keyword_index
3. vector_index
4. graph_index
5. temporal_index
```

实际第一阶段落地：

```text
PostgreSQL B-Tree/GIN
pgvector
Relation tables
Event table（MVP5 才真正启用）
```

不引入 Elasticsearch / Qdrant / Milvus。

### 何时允许拆分？

只有满足之一：

```text
PostgreSQL retrieval latency consistently > target

OR

vector count > ~5M and profiling proves separate vector engine is justified

OR

full-text needs exceed PostgreSQL FTS capability
```

届时再评估 Qdrant / Elasticsearch。

---

# 23. MVP3 Query Router

基础 Query Type：

```text
ENTITY_LOOKUP
CODE_LOOKUP
RELATION_QUERY
BUSINESS_QUERY
HISTORY_QUERY
SEMANTIC_QUERY
IMPACT_QUERY
UNKNOWN
```

例如：

```text
“LeadService 在哪里？”
→ ENTITY_LOOKUP

“哪些页面调用 /api/leads？”
→ RELATION_QUERY

“为什么 Lead 分配这么设计？”
→ BUSINESS_QUERY

“上周是谁改了它？”
→ HISTORY_QUERY
```

第一版 Query Router 不需要 LLM，先使用规则 + keyword。

LLM Router 后续加入。

---

# 24. MVP3 RAG 验收门

建立至少 100 个 Query Gold Set，覆盖：

```text
代码定位
实体定位
关系查询
业务解释
历史查询
跨项目查询
```

指标：

```text
Recall@5
MRR
source correctness
wrong-project rate
unsupported-answer rate
```

初始目标：

```text
Recall@5 >= 85%
wrong-project rate < 3%
source correctness >= 95%
```

没有达到目标：

```text
不进入 LLM Wiki
不进入 Agent
```

先修 Retrieval。

---

# 25. MVP4 —— LLM Wiki

## 25.1 Wiki 定义

Wiki = Knowledge Projection。

不是 Source of Truth。

## 25.2 Project Wiki

页面固定：

```text
Project Overview
Architecture
Frontend
Backend
API
Database
Business Domain
Business Process
Business Rules
Dependencies
Recent Changes
Known Risks
Open Decisions
```

## 25.3 每个章节必须带 Evidence

例：

```text
Lead Allocation

Summary:
系统根据销售规则分配 Lead。

Evidence:
[BusinessRule #104]
[LeadAllocationService.java]
[/api/leads/allocate]
[Commit abc123]

Confidence:
0.91
```

禁止生成没有 Evidence 的事实性段落。

---

# 26. Wiki 更新策略

不要每次扫描都让 LLM 重写整个 Wiki。

正确流程：

```text
Source Change
    ↓
Affected Entity
    ↓
Affected Wiki Sections
    ↓
Regenerate only affected sections
```

每个 Wiki Section 保存：

```text
content
source_entity_ids
source_event_ids
source_document_ids
model
prompt_version
generated_at
verified_at
status
```

status：

```text
GENERATED
VERIFIED
STALE
CONFLICTED
```

---

# 27. MVP5 —— Event / Change Intelligence

## 27.1 Event 是整个系统的时间骨架

基础 Event Types：

```text
CODE_CHANGE
REQUIREMENT_CHANGE
BUSINESS_RULE_CHANGE
API_CHANGE
DATABASE_CHANGE
CONFIG_CHANGE
DEPLOYMENT
INCIDENT
OPERATION
DOCUMENT_CHANGE
AI_DECISION
HUMAN_DECISION
METRIC_CHANGE
```

## 27.2 `events`

```text
id UUID PK
event_type VARCHAR(64)
project_id UUID
entity_id UUID NULL
actor_type VARCHAR(32)
actor_id VARCHAR(255)
timestamp TIMESTAMPTZ
before_state JSONB
after_state JSONB
reason TEXT NULL
source_type VARCHAR(64)
source_id UUID NULL
confidence NUMERIC(6,5)
metadata JSONB
created_at TIMESTAMPTZ
```

## 27.3 Git Change

每个 commit 可以产生：

```text
COMMIT event
FILE_CHANGED events
ENTITY_CHANGED events
```

保存：

```text
commit_sha
author
author_email
message
authored_at
changed_files
insertions
deletions
```

第一版不要全文保存所有 patch；只保存：

```text
commit SHA
changed file
diff summary
hash
```

必要时再读取 Git 原始 diff。

---

# 28. Temporal Query

以后支持：

```text
“9 月以前 LeadService 是什么状态？”

“这个 API 什么时候第一次出现？”

“这个业务规则改过几次？”

“某次部署之后发生了什么？”
```

这是 Event Store + Snapshot 的职责，而不是普通 RAG。

---

# 29. MVP6 —— Laya Decision Engine

## 29.1 接入方式

LKIO 内部定义统一接口：

```python
class DecisionEngine(Protocol):
    def decide(self, request: DecisionRequest) -> DecisionResult:
        ...
```

Laya 只是：

```text
LayaDecisionEngine(DecisionEngine)
```

未来可以替换：

```text
JevDecisionEngine
LLMJudgeDecisionEngine
RuleEngine
CustomClassifier
```

## 29.2 第一批 Decision Tasks

只做 4 个：

```text
CHANGE_IMPACT
EVIDENCE_SUFFICIENCY
QUERY_ROUTE
ACTION_GATE
```

不要一开始训练几十种任务。

## 29.3 示例

### CHANGE_IMPACT

```text
NONE
LOW
MEDIUM
HIGH
CRITICAL
```

### EVIDENCE_SUFFICIENCY

```text
INSUFFICIENT
PARTIAL
SUFFICIENT
STRONG
```

### QUERY_ROUTE

```text
ENTITY
CODE
GRAPH
RAG
EVENT
WIKI
HUMAN
```

### ACTION_GATE

```text
AUTO
REVIEW
ESCALATE
REJECT
```

---

# 30. Decision Request 结构

```json
{
  "task": "CHANGE_IMPACT",
  "project_scope": ["HELLO_FE", "HELLO_BE"],
  "state": {
    "changed_entities": [],
    "relations": [],
    "business_rules": [],
    "recent_events": [],
    "evidence": []
  },
  "question": {
    "type": "choice",
    "options": ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
  }
}
```

Laya 只接收经过 Knowledge Core / Retrieval 处理的结构化 state，不直接扫描整个磁盘。

---

# 31. Decision Result

```json
{
  "decision": "HIGH",
  "probability": 0.91,
  "model_confidence": 0.91,
  "evidence_confidence": 0.95,
  "graph_confidence": 0.94,
  "historical_accuracy": 0.88,
  "final_confidence": 0.92,
  "requires_human_review": true,
  "model_version": "laya-typed-decisions",
  "policy_version": "impact-v1"
}
```

注意：`final_confidence` 不等于简单平均；V1 可先实现可解释加权规则，后续通过真实 Outcome calibration 替换。

---

# 32. MVP6 Confidence Policy

第一版只定义策略，不允许自动执行写操作。

```text
final_confidence < 0.65
→ HUMAN

0.65 <= c < 0.85
→ REVIEW

0.85 <= c < 0.95
→ SECOND_CHECK

c >= 0.95
→ 仍然必须经过 ACTION POLICY
```

重要：

> 0.95 不是自动写代码许可证。

自动执行必须同时满足：

```text
confidence
AND
trusted source
AND
allowed action
AND
scope safe
AND
policy approved
```

---

# 33. MVP7 —— Impact Analysis Engine

## 输入

```text
Changed Entity
```

## Graph Traversal

```text
changed entity
  ↓
1-hop
  ↓
2-hop
  ↓
3-hop
  ↓
Business / Metric / Project
```

## 分类

```text
DIRECT
INDIRECT
POTENTIAL
HISTORICAL
```

例如：

```text
HELLO_FE Page
    ↓ calls
API
    ↓ implemented_by
HELLO_BE Service
    ↓ implements
BusinessRule
```

输出：

```text
Affected Projects
Affected APIs
Affected Pages
Affected Services
Affected Business Rules
Affected Metrics
```

---

# 34. MVP7 Impact Confidence

每条影响链必须有 evidence：

```text
CODE_RELATION
DOCUMENT_RELATION
HUMAN_VERIFIED
INFERRED
HISTORICAL
```

然后系统输出：

```text
Impact Confidence
Evidence Count
Shortest Path
Critical Path
```

不能只输出一个“AI 判断高风险”。

---

# 35. MVP8 —— Laya Evaluation / Calibration / Fine-tuning

这一步才开始真正“调教 Laya”。

## 35.1 Dataset

至少建立：

```text
300 Gold Cases
100 Boundary Cases
100 Abstain Cases
100 Conflict Cases
```

第一阶段建议 >= 600 cases；质量优先于数量。

## 35.2 数据来源

```text
Human Decisions
Git Change History
Known Bug
Deployment Result
Incident
Impact Review
Agent Proposal
Actual Outcome
```

## 35.3 样本格式

```json
{
  "task": "CHANGE_IMPACT",
  "state": {},
  "question": {},
  "expected": "HIGH",
  "evidence": [],
  "label_source": "HUMAN_VERIFIED",
  "outcome": "FRONTEND_REGRESSION",
  "created_at": "..."
}
```

## 35.4 Evaluation Metrics

必须记录：

```text
Accuracy
Macro-F1
Brier Score
ECE
NLL
Confusion Matrix
Abstain Rate
False Positive Rate
False Negative Rate
```

目标不是“confidence 最大”。

目标：

```text
confidence 越高，实际正确率越高
```

---

# 36. Training Policy

没有以下文件不能训练：

```text
training_manifest.json
validation_manifest.json
test_manifest.json
label_schema.json
```

数据拆分必须按时间或项目维度避免泄漏。

例如：

```text
旧项目 / 旧事件 → train
新事件 → validation
未来事件 → test
```

不能随机拆分导致同一 Git change lineage 同时出现在 train/test。

---

# 37. RAG 与 Laya 的关系

最终：

```text
User Query
   ↓
Query Router
   ↓
RAG / Graph / Event
   ↓
Evidence Pack
   ↓
Laya
   ↓
Decision
   ↓
LLM Explanation
```

不是：

```text
User Query
 ↓
LLM
 ↓
Laya 猜
```

Laya 应该基于 Evidence Pack 决策。

LLM 负责把结果解释成人能理解的语言。

---

# 38. Local LLM Gateway

MVP3 先定义接口，不绑定供应商：

```python
class LLMProvider(Protocol):
    def chat(...): ...
    def structured(...): ...
    def embed(...): ...
```

MVP4 后再实现：

```text
OllamaProvider
LMStudioProvider
OpenAICompatibleProvider
```

这样未来换模型不影响业务层。

---

# 39. Agent 层最终形态

后续支持：

```text
Architect Agent
Developer Agent
Product Agent
Analyst Agent
Review Agent
```

但 Agent 只能调用能力：

```text
search_entities
search_code
query_graph
search_events
read_wiki
get_evidence
run_decision
build_impact_report
```

而不是直接访问 PostgreSQL。

这样可以统一审计。

---

# 40. MCP 设计

后续可以提供：

```text
lkio.search
lkio.entity
lkio.graph
lkio.event
lkio.wiki
lkio.decision
lkio.impact
```

Cursor / Claude Code / Codex 等 Agent 可以通过 MCP 使用 LKIO。

但 MCP Write 工具第一阶段必须关闭。

后期分：

```text
READ
PLAN
REVIEW
WRITE
```

四种权限。

---

# 41. Source Access Policy

## READ_ONLY

```text
HELLO_FE
HELLO_BE
L2C_FE
```

## WRITE_DISABLED

所有：

```text
code
config
database
build
```

直到 MVP7 之后才允许进入 action pipeline。

## WRITE_ALLOWED

未来由：

```text
Action Policy
Human Approval
Audit Event
```

共同决定。

---

# 42. Evidence Hierarchy

冲突时的默认可信度顺序：

```text
1. Live Structured Source
   Git / DB schema / runtime event

2. Human Verified Decision

3. AST / Static Analysis

4. Human-authored Document

5. Generated Wiki

6. LLM Inference
```

这不是绝对真理，而是 V1 默认 Policy。

若存在冲突：

```text
CONFLICT
```

不能静默覆盖。

---

# 43. Change Management

以后任何修改 LKIO 核心架构必须填写 ADR：

```text
ADR-0001
ADR-0002
...
```

格式：

```text
Context
Decision
Alternatives
Consequences
Migration
```

例如：

```text
ADR-0001
为什么不用 Neo4j
```

结论：

```text
因为 MVP0~MVP3 PostgreSQL relation model 足够。
```

只有指标证明不够，才推翻。

---

# 44. 不允许提前引入的组件

MVP0~MVP3 禁止：

```text
Neo4j
Qdrant
Milvus
Elasticsearch
Kafka
Redis
Temporal
Kubernetes
Airflow
LangChain
LlamaIndex
AutoGen
CrewAI
多 Agent Framework
```

除非出现明确工程问题并有 ADR。

原因不是这些项目不好，而是当前阶段它们会让系统边界膨胀。

---

# 45. 为什么第一版不用 Neo4j

因为当前只有三个项目。

关系主要是：

```text
Entity
Relation
```

PostgreSQL 足够：

```text
JOIN
CTE
recursive CTE
GIN
JSONB
vector
transaction
```

以后如果：

```text
实体 > 1,000,000
关系 > 10,000,000
复杂多跳查询成为主要瓶颈
```

才重新评估 Graph DB。

---

# 46. 为什么第一版不用 Qdrant

当前数据量太小。

PostgreSQL + pgvector 的优势：

```text
Entity
Relation
Metadata
Vector
Transaction
```

都在同一数据库。

pgvector 官方支持 exact / approximate nearest neighbor、cosine / inner product / L2，以及 ACID / JOIN / point-in-time recovery。  
来源：https://github.com/pgvector/pgvector

---

# 47. 为什么不把 Wiki 放到 Git

Wiki 是 Projection。

如果直接把 Wiki 当源文件：

```text
代码变了
↓
Wiki 可能过期
↓
RAG 继续相信 Wiki
```

正确是：

```text
Source changed
↓
Evidence changed
↓
Wiki stale
↓
regenerate
```

---

# 48. Initial Docker Compose

`infra/compose.yaml` 固定类似：

```yaml
services:
  postgres:
    image: pgvector/pgvector:0.8.6-pg18
    container_name: lkio-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: lkio
      POSTGRES_USER: lkio
      POSTGRES_PASSWORD: change-me-local-only
    ports:
      - "127.0.0.1:54329:5432"
    volumes:
      - lkio_pgdata:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lkio -d lkio"]
      interval: 5s
      timeout: 5s
      retries: 20

volumes:
  lkio_pgdata:
```

说明：

- 只绑定 localhost。
- 不暴露到局域网。
- 不把数据库密码提交进 Git。
- 正式版本使用 `.env.local` / secret file。

当前 pgvector Docker Hub 提供 `0.8.6-pg18` 标签，并支持 linux/amd64 与 linux/arm64。  
来源：https://hub.docker.com/r/pgvector/pgvector/tags?name=pg18

---

# 49. 数据库环境变量

`.env.local`：

```env
LKIO_ENV=local

POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=54329
POSTGRES_DB=lkio
POSTGRES_USER=lkio
POSTGRES_PASSWORD=change-me-local-only

LKIO_SOURCE_READ_ONLY=true
LKIO_ALLOW_WRITE_TO_SOURCE=false

LLM_PROVIDER=none
DECISION_ENGINE=none
```

`.env.example`：

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=54329
POSTGRES_DB=lkio
POSTGRES_USER=lkio
POSTGRES_PASSWORD=

LKIO_SOURCE_READ_ONLY=true
LKIO_ALLOW_WRITE_TO_SOURCE=false

LLM_PROVIDER=none
DECISION_ENGINE=none
```

`.env.local` 永远不提交 Git。

---

# 50. Git 安全

`.gitignore` 必须至少包括：

```text
.env
.env.*
!.env.example

.venv/
__pycache__/
.pytest_cache/

node_modules/
dist/

.idea/
.vscode/

logs/
tmp/

lkio-data/
```

---

# 51. Logging

日志必须结构化 JSON：

```json
{
  "timestamp": "...",
  "level": "INFO",
  "service": "ingestion",
  "run_id": "...",
  "project_key": "HELLO_FE",
  "event": "SCAN_COMPLETE",
  "duration_ms": 1820
}
```

后续所有：

```text
ingestion
retrieval
wiki
decision
agent
```

都必须带 `run_id`。

---

# 52. Idempotency

任何 ingestion 都必须支持：

```text
same input
→ same entity identity
→ no duplicates
```

Entity key 推荐：

```text
PROJECT:{project_key}
REPO:{project_key}
FILE:{project_key}:{relative_path}
SYMBOL:{file_hash}:{qualified_name}:{start_line}
```

未来如果代码移动：

```text
rename/move detection
```

再单独做，不在 MVP0。

---

# 53. Entity Identity 原则

不要使用随机 UUID 作为唯一逻辑身份。

UUID 只是 DB PK。

逻辑身份必须可计算：

```text
entity_key
```

这样才能实现：

```text
re-scan
merge
versioning
cross-project relation
```

---

# 54. Project / Repository / Application 区别

必须从一开始分开：

```text
Project
= 业务项目

Repository
= Git repo

Application
= 可以运行/部署的应用
```

例：

```text
Project: HELLO
├── Repository: hello
├── Repository: hello-backend
├── Application: hello-web
└── Application: hello-api
```

当前因用户只提供三个目录，第一阶段可以让 Project 与 Repository 近似映射，但模型不能因此绑定死。

---

# 55. Business Ontology 第一版

业务实体不要马上全部自动抽取。

第一版只保留：

```text
BusinessDomain
BusinessProcess
BusinessRule
Feature
Metric
Decision
```

这些实体优先通过：

```text
Human input
Documents
Later LLM extraction
```

代码扫描只能提供候选，不直接宣布业务事实。

---

# 56. AI 推理标签

所有 LLM/AI 推理出的实体关系都必须带：

```text
extraction_method=LLM_INFERENCE
confidence=<score>
verified=false
```

人工确认之后：

```text
verified=true
verified_by=<user>
verified_at=<time>
```

---

# 57. Future Business Twin

后续的最终图可以长这样：

```text
Business Domain
      ↓
Business Process
      ↓
Business Rule
      ↓
Feature
      ↓
Frontend Page
      ↓
API
      ↓
Backend Service
      ↓
Database
      ↓
Metric
```

这就是我们真正需要的跨项目 Knowledge Graph。

---

# 58. “三个项目”的特殊策略

## HELLO_FE

第一优先级。

所有第一批解析器都优先保证它。

必须最终达到：

```text
Project
→ Repo
→ Framework
→ Files
→ Vue/React components
→ Stores
→ Routes
→ API calls
→ Dependencies
```

## HELLO_BE

作为配套后端。

重点是：

```text
API
Controller
Service
Repository
Database
```

具体技术栈必须由扫描结果确定，不预设 Java/Go/Python。

## L2C_FE

作为第二个前端项目，验证：

```text
独立项目
跨项目大盘
未来项目
```

它的价值不是“功能多”，而是验证系统能否管理一个尚未进入生产的项目。

---

# 59. L2C 的特殊标签

`role = future_frontend`

后续可以支持：

```text
planned
in_development
development
production
maintenance
archived
```

这样未来可以出现：

```text
Current Projects
Upcoming Projects
Archived Projects
```

---

# 60. Project Lifecycle

最终统一：

```text
IDEA
PLANNED
ACTIVE
PRODUCTION
MAINTENANCE
ARCHIVED
```

但 MVP0 只做：

```text
ACTIVE
PLANNED
```

---

# 61. 后期“操作记录”设计

真正的操作记录不能只记录 Git。

未来统一为：

```text
Actor
Action
Target
Timestamp
Before
After
Reason
Result
Evidence
```

例如：

```text
Actor: Developer
Action: UPDATE_BUSINESS_RULE
Target: LeadAllocationRule
Reason: Sales team requested tier-based routing
Result: deployed
```

AI 操作也必须使用同一 schema。

---

# 62. 后期 Decision Record

核心实体：

```text
Decision
```

字段建议：

```text
id
question
context
options
selected_option
rationale
decider_type
decider_id
evidence_ids
confidence
status
created_at
```

status：

```text
PROPOSED
APPROVED
REJECTED
SUPERSEDED
```

这会成为业务逻辑长期沉淀的重要来源。

---

# 63. Agent Memory 不作为事实库

Agent 的短期上下文：

```text
Conversation State
Task State
Current Plan
```

长期知识：

```text
Knowledge Core
```

不要把 agent memory 与 organization knowledge 混为一谈。

---

# 64. 备份策略

MVP0 起就做：

```powershell
docker exec lkio-postgres pg_dump -U lkio -d lkio > C:\WorkSpace\lkio-data\backups\lkio.sql
```

以后每天自动备份，但 MVP0 暂不做 Automations。

数据至少保留：

```text
latest.sql
last-7-days
milestone snapshots
```

---

# 65. 版本管理

LKIO 自身：

```text
Git
```

MVP：

```text
mvp/0.1
mvp/0.2
...
```

架构版本：

```text
ontology-v0.1
ontology-v0.2
```

Decision model：

```text
decision-policy-v1
laya-adapter-v1
calibration-v1
```

禁止用“latest”作为不可追溯模型版本。

---

# 66. Definition of Done 总表

## MVP0

```text
[ ] Docker 可运行
[ ] PostgreSQL 可运行
[ ] pgvector 可启用
[ ] FastAPI 可运行
[ ] Vue 可运行
[ ] 3 Projects 已注册
[ ] Entity 可创建
[ ] Relation 可创建
[ ] Graph 可显示
[ ] 数据幂等
```

## MVP1

```text
[ ] 3 个项目均可扫描
[ ] Git HEAD 可识别
[ ] Framework 可识别
[ ] File tree 可生成
[ ] Dependency 可识别
[ ] 重扫不产生重复数据
[ ] 全程只读
```

## MVP2

```text
[ ] AST 解析
[ ] Symbol entity
[ ] API relation
[ ] Cross-project graph
[ ] Confidence + Evidence
```

## MVP3

```text
[ ] Keyword Search
[ ] Vector Search
[ ] Graph Search
[ ] Rerank
[ ] 100 Query Gold Set
[ ] Recall@5 >= 85%
```

## MVP4

```text
[ ] Wiki
[ ] Evidence
[ ] Stale detection
[ ] Section-level regeneration
```

## MVP5

```text
[ ] Commit Event
[ ] File Change Event
[ ] Timeline
[ ] Historical Query
```

## MVP6

```text
[ ] Decision API
[ ] Laya Adapter
[ ] 4 Decision Tasks
[ ] Confidence Policy
[ ] No-write Action Gate
```

## MVP7

```text
[ ] Impact Graph
[ ] Affected project
[ ] Affected frontend/backend
[ ] Evidence chain
[ ] Human Review flow
```

## MVP8

```text
[ ] Gold Dataset
[ ] Validation
[ ] Test set
[ ] Calibration
[ ] Outcome loop
[ ] Optional fine-tune
```

---

# 67. 第一阶段最容易犯的错误

## 错误 1：一开始装 10 个基础设施

禁止。

## 错误 2：一开始训练 Laya

禁止。

## 错误 3：一开始做 Agent

禁止。

## 错误 4：把所有代码都 embedding

禁止。

## 错误 5：让 LLM 决定 Entity Identity

禁止。

## 错误 6：把 Wiki 当真相

禁止。

## 错误 7：confidence 越高就越可信

禁止。

## 错误 8：先做漂亮的大盘，后做数据正确性

禁止。

---

# 68. 当前唯一允许的第一条开发路线

```text
Step 1
安装 Docker / Node / Python / uv / Git

↓
Step 2
创建 C:\WorkSpace\lkio

↓
Step 3
创建 PostgreSQL + pgvector

↓
Step 4
创建 FastAPI + SQLAlchemy + Alembic

↓
Step 5
建立 projects / sources / entities / relations

↓
Step 6
注册 HELLO_FE / HELLO_BE / L2C_FE

↓
Step 7
建立 Graph API

↓
Step 8
建立 Vue + Cytoscape Graph

↓
Step 9
MVP0 验收

↓
Step 10
才进入 MVP1
```

---

# 69. 初次安装的 PowerShell 指令清单

## 基础检查

```powershell
node -v
npm -v
python --version
uv --version
git --version
docker --version
```

## 创建项目

```powershell
cd C:\WorkSpace
mkdir lkio
cd lkio
git init
```

## Python

```powershell
uv python pin 3.12.10
uv sync
```

## 前端

```powershell
npm create vue@latest apps-web
```

之后将目录整理到最终结构，不要长期保留临时项目名。

## Docker

```powershell
docker compose -f infra/compose.yaml up -d postgres
docker ps
```

---

# 70. 第一阶段建议的 `compose.yaml` 端口

```text
PostgreSQL
127.0.0.1:54329 → 5432

FastAPI
127.0.0.1:8000 → 8000

Vue
127.0.0.1:5173 → 5173
```

以后：

```text
Ollama
127.0.0.1:11434
```

Laya 不是 HTTP 服务时由 FastAPI/Worker 本地加载；后续也可以封装成独立 inference service。

---

# 71. 第一阶段开发顺序建议

### Day/Step A — Infrastructure

完成：

```text
Docker
Postgres
uv
Node
Git
```

### Step B — Backend Kernel

完成：

```text
settings
DB
migration
models
repositories
API
health
```

### Step C — Ontology Core

完成：

```text
Project
Source
Entity
Relation
```

### Step D — Seed

注册：

```text
HELLO_FE
HELLO_BE
L2C_FE
```

### Step E — Graph UI

完成：

```text
Project list
Entity list
Relation list
Graph
```

### Step F — MVP0 Gate

通过才允许进入 ingestion。

---

# 72. Cursor / VS Code 工作区

建议创建：

```text
C:\WorkSpace\lkio\LKIO.code-workspace
```

workspace 可以包含：

```json
{
  "folders": [
    { "path": "." },
    { "path": "..\\hello" },
    { "path": "..\\hello-backend" },
    { "path": "..\\L2C project" }
  ]
}
```

但是：

> 代码 Agent 默认只能对 `.`（LKIO）写入。

三个源项目在 workspace 中只作为参考代码。

---

# 73. Agent Rule 建议

在 LKIO 中建立：

```text
AGENTS.md
CLAUDE.md
CURSOR_RULES.md
```

核心规则统一：

```text
1. Never modify source projects unless explicitly authorized.
2. Never invent graph relations without evidence.
3. Every inferred relation must carry confidence + extraction_method.
4. Never treat generated Wiki as source of truth.
5. Do not add infrastructure without ADR.
6. Do not add new MVP scope without updating MVP.md.
7. Preserve backward compatibility of core schema.
8. Keep ingestion idempotent.
9. Keep project identity stable.
10. All AI actions must be auditable.
```

---

# 74. 以后真正有价值的数据闭环

最终系统会形成：

```text
          Source Projects
                ↓
            Ingestion
                ↓
       Entity / Relation / Event
                ↓
        Graph + RAG + Wiki
                ↓
          Evidence Pack
                ↓
              Laya
                ↓
         Decision / Confidence
                ↓
        Human Review / Action
                ↓
            Real Outcome
                ↓
           Evaluation Set
                ↓
         Calibration / FT
                ↓
              Laya
```

这就是系统真正的学习闭环。

---

# 75. 最终系统不是“会聊天的知识库”

最终目标定义为：

> **让 AI 理解整个软件系统和业务系统，并能对结构、依赖、历史、影响和行动风险给出带证据的判断。**

最终能力矩阵：

| 能力 | 来源 |
|---|---|
| 找代码 | Code Index |
| 找业务 | Wiki/RAG |
| 看依赖 | Graph |
| 看历史 | Event |
| 看变更 | Git/Event |
| 看跨项目 | Cross-project Graph |
| 判断影响 | Laya + Graph |
| 判断证据 | Evidence Model |
| 解释原因 | LLM |
| 决定是否执行 | Policy + Laya |
| 学习历史结果 | Evaluation / Outcome |

---

# 76. 变更控制：以后如果发现当前架构需要改变

必须先写一份：

```text
ADR
```

包含：

```text
Problem
Current Limitation
Measured Evidence
Options
Decision
Trade-offs
Migration Cost
Rollback Plan
```

不能因为“感觉 Neo4j / Qdrant / Agent Framework 很强”就引入。

---

# 77. 第一阶段最终冻结结论

### 底座

```text
自研 Knowledge Core
```

### 数据库

```text
PostgreSQL 18
```

### Vector

```text
pgvector
```

### Code Parser

```text
Tree-sitter
```

### Backend

```text
Python 3.12.10
FastAPI
SQLAlchemy
Alembic
uv
```

### Frontend

```text
Vue 3
TypeScript
Vite
Element Plus
Pinia
Cytoscape.js
```

### RAG

```text
Hybrid Retrieval
Keyword + Vector + Graph
```

### LLM

```text
Local Provider abstraction
Ollama / LM Studio
```

### Decision

```text
Laya Adapter
```

### Training

```text
先 Evaluation
后 Calibration
最后 Fine-tune
```

### First projects

```text
HELLO_FE → C:\WorkSpace\hello
HELLO_BE → C:\WorkSpace\hello-backend
L2C_FE   → C:\WorkSpace\L2C project
```

---

# 78. 当前只执行 MVP0

MVP0 的唯一任务：

```text
把系统搭起来
让它认识三个项目
让它画出第一张关系图
```

不提前做：

```text
RAG
LLM
Laya
Agent
自动改代码
```

**当且仅当 MVP0 的验收清单全部通过，进入 MVP1。**

---

# 79. 官方资源汇总

## Runtime / Tooling

- Docker Desktop Windows: https://docs.docker.com/desktop/setup/install/windows-install/
- Node.js: https://nodejs.org/en/download/current
- Python 3.12.10: https://www.python.org/downloads/release/python-31210/
- uv: https://docs.astral.sh/uv/getting-started/installation/
- Git: https://git-scm.com/download/win

## Backend

- FastAPI: https://fastapi.tiangolo.com/tutorial/
- SQLAlchemy: https://docs.sqlalchemy.org/en/20/
- Alembic: https://alembic.sqlalchemy.org/en/latest/tutorial.html

## Database

- PostgreSQL: https://www.postgresql.org/docs/18/
- PostgreSQL Windows installers: https://www.postgresql.org/download/windows/
- pgvector: https://github.com/pgvector/pgvector
- pgvector Docker: https://hub.docker.com/r/pgvector/pgvector

## Parsing

- Tree-sitter: https://tree-sitter.github.io/tree-sitter/
- Tree-sitter GitHub: https://github.com/tree-sitter/tree-sitter
- Python bindings: https://pypi.org/project/tree-sitter/

## Frontend

- Vue: https://vuejs.org/guide/quick-start
- Vue TypeScript: https://vuejs.org/guide/typescript/overview
- Element Plus: https://element-plus.org/en-US/guide/installation
- Cytoscape.js: https://js.cytoscape.org/

## AI

- Laya GitHub: https://github.com/he-jev/laya
- Laya Hugging Face: https://huggingface.co/convaiinnovations/laya
- Laya typed-decisions: https://huggingface.co/convaiinnovations/laya-typed-decisions
- BGE-M3: https://huggingface.co/BAAI/bge-m3
- Ollama Windows: https://ollama.com/download/windows
- LM Studio: https://lmstudio.ai/download

## Editor Plugins

- Vue Official: https://marketplace.visualstudio.com/items?itemName=Vue.volar
- Python: https://marketplace.visualstudio.com/itemdetails?itemName=ms-python.python
- Container Tools: https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-containers

---

# 80. 当前执行状态模板

每次开发只维护本表：

| MVP | 状态 | 开始 | 完成 | 阻塞项 | 验收 |
|---|---|---|---|---|---|
| MVP0 | TODO | | | | 未验收 |
| MVP1 | LOCKED | | | MVP0 | 未开始 |
| MVP2 | LOCKED | | | MVP1 | 未开始 |
| MVP3 | LOCKED | | | MVP1/2 | 未开始 |
| MVP4 | LOCKED | | | MVP3 | 未开始 |
| MVP5 | LOCKED | | | MVP1 | 未开始 |
| MVP6 | LOCKED | | | MVP4/5 | 未开始 |
| MVP7 | LOCKED | | | MVP2/5/6 | 未开始 |
| MVP8 | LOCKED | | | MVP6/7 | 未开始 |

**任何时候最多只有一个 ACTIVE MVP。**

---

# 81. 本文件的优先级

当后续聊天、Agent、代码实现与本文件冲突时，默认：

```text
Architecture Baseline
    >
MVP Definition
    >
ADR
    >
Implementation Detail
    >
Agent Suggestion
```

需要改变架构时，先更新 ADR 和 MVP.md，再改代码。

---

# 82. 下一开发动作

下一步只执行：

```text
MVP0 / Step 1

1. 安装并验证基础环境
2. 创建 C:\WorkSpace\lkio
3. 初始化 Git
4. 创建 Python 项目
5. 创建 Vue 项目
6. 创建 PostgreSQL/pgvector Compose
7. 完成 Alembic 初始迁移
8. 建立 projects/sources/entities/relations
9. Seed 三个真实项目
10. 完成第一版 Graph
11. 跑通 MVP0 验收
```

此阶段完成之前，不进入任何 AI / RAG / Laya 开发。
