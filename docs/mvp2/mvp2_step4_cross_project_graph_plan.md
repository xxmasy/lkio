# LKIO MVP2-D 主实施规划 — 跨工程代码图谱 (Cross-Project Graph Master Plan)

> **阶段代号**：**MVP2-D**  
> **阶段全称**：**Cross-Project Graph (跨工程代码图谱与依赖网络)**  
> **前置阶段状态**：  
> - **MVP2-A = COMPLETED / FROZEN**  
> - **MVP2-B = COMPLETED / FROZEN**  
> - **MVP2-C = COMPLETED / FROZEN**  
> **当前阶段状态**：**READY_TO_EXECUTE**  
> **核心使命**：跨越单个工程边界，基于工程清单（`package.json`, `pom.xml`, monorepo workspaces）与共享类型/模块，建立工程间的静态依赖、共享模块引用与跨工程结构图谱。

---

## 一、6 大跨工程架构锁 (Architecture Locks)

1. **`LOCK-CROSS-01` (MVP2-B & MVP2-C 基础不变锁)**：
   - MVP2-B 的符号抽取逻辑与持久化流水线 100% 保持只读冻结。
   - MVP2-C 的单工程结构图谱（`imports`, `exports`, `extends`, `implements`, `calls`）100% 保持只读冻结。
2. **`LOCK-CROSS-02` (跨工程边正交性锁)**：
   - 跨工程关系的主体 `subject_entity_id` 与客体 `object_entity_id` 分属不同工程（或跨 monorepo 子项目）。
   - 谓词明确为 `depends_on`, `cross_imports`, `provides`, `references_contract`。
3. **`LOCK-CROSS-03` (跨工程逻辑身份恒等锁)**：
   - 跨工程关系唯一键命名空间：
     `RELATION:CROSS:{src_project_key}:{tgt_project_key}:{subject_key}:{predicate}:{raw_target}:{kind}:{discriminator}`
   - 在任何更新、解析或扫描重跑中，`relation_key` 严格保持比特级不变。
4. **`LOCK-CROSS-04` (零虚构证据锁)**：
   - 跨工程关联必须基于明确的清单声明（`package.json`, `pom.xml`）、工作区包路径或完全匹配的共享类型 FQN。严禁无证据猜测。
5. **`LOCK-CROSS-05` (跨工程生命周期与双扫描幂等锁)**：
   - 当源端工程或宿主工程移除依赖声明时，跨工程关系转为 `status = 'DELETED'`，永不物理删除。
   - 连续两次全量扫描必须保证 3-Set（`id_set`, `key_set`, `triple_set`）100% 恒等。
6. **`LOCK-CROSS-06` (源工程物理只读红线)**：
   - 外部项目 `HELLO_FE`, `HELLO_BE`, `L2C_FE` 严格物理只读，`git status --porcelain` 恒为 0。

---

## 二、子阶段划分与验收门禁 (D-00 ~ D-05)

| 阶段 | 目标与交付物 | 核心门禁 (Gates) |
|---|---|---|
| **D-00** | 架构主规划与设计基线冻结 | Master Plan 审阅与 6 大架构锁冻结 |
| **D-01** | 跨工程清单与包注册表 (`CrossProjectManifestRegistry`) | `Gate D1`: 包与模块清单提取 (`package.json`, `pom.xml`, monorepo) |
| **D-02** | 跨工程依赖与引用解析器 (`CrossProjectDependencyResolver`) | `Gate D2`: 跨工程 `depends_on` 与 `cross_imports` 静态解析 |
| **D-03** | 跨工程共享类型与契约推断 (`CrossProjectContractLinker`) | `Gate D3`: 共享 DTO / Interface 引用连接与置信度标定 |
| **D-04** | 跨工程关系持久化与生命周期同步 (`CrossProjectPersistenceService`) | `Gate D4`: 跨工程关系原子入库、软删除与双扫描幂等性 |
| **D-05** | 三大真实工程系统集成验证门禁 (`test_cross_project_graph_d05.py`) | `Gate D5`: 真实多工程图谱构建与物理只读审计 |

---

## 三、数据模型扩展与跨工程关系谓词

- `CROSS_IMPORTS` (`cross_imports`): 工程 A 的文件导入了工程 B 导出的模块/包。
- `DEPENDS_ON` (`depends_on`): 工程 A 声明依赖工程 B 提供的库/包组件。
- `PROVIDES` (`provides`): 工程 B 对外提供特定包或公共模块。
- `REFERENCES_CONTRACT` (`references_contract`): 前端或消费端引用后端或公共契约定义的类型。
