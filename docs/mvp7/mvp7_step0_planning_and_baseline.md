# LKIO MVP7 (Impact Analysis Engine) 实施基线与架构规划

> **阶段代号**：**MVP7**  
> **阶段名称**：**Impact Analysis Engine（影响链分析引擎）**  
> **前置依赖**：MVP0 (FROZEN), MVP1 (FROZEN), MVP2 (FROZEN), MVP3 (FROZEN), MVP4 (FROZEN), MVP5 (FROZEN), MVP6 (FROZEN)  
> **当前状态**：**IN_PROGRESS (ACTIVE)**  
> **基线依据**：`LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md` 第 33 条（Impact Analysis Engine）、第 34 条（Impact Confidence）、第 3140 行（MVP7 验收条目）

---

## 一、MVP7 核心定位与设计原则

根据实施基线第 33 条与第 34 条：
> **“影响链分析绝不能只输出一个模糊的‘AI 判断高风险’，而是必须基于多跳图谱遍历 (Multi-hop Graph Traversal)，输出确凿的 Affected Projects、Affected APIs、Affected Pages、Affected Services、Affected Business Rules，且每条影响路径必须附带 Shortest Path、Critical Path、Evidence Count 与计算置信度。”**

在 LKIO 架构中：
- MVP2 提取了静态代码关系（imports, calls, defines, extends, implements, api_calls）。
- MVP5 提供了时序变更历史与实体修改事件。
- MVP6 确立了 4 大决策任务与置信度策略分级。
- **MVP7 构建全系统端到端影响链穿透能力**：
  从任意变更实体（类、函数、组件、接口、文件）出发，沿关系图谱向前/向后遍历 1-hop（直接影响）、2-hop（间接影响）、3-hop（潜在系统/业务波及），精准计算波及项目、端到端接口链条，并自动生成结构化的人工复核工作流（Human Review Flow）。

---

## 二、🛑 永久冻结架构红线 (Inviolable Redlines)

1. **源项目绝对物理只读**：
   - `HELLO_FE`、`HELLO_BE`、`L2C_FE` 绝对只读。
2. **严禁无图谱证据的虚构影响分析**：
   - 每一个受影响实体与传播路径必须绑定明确的证据源（`CODE_RELATION`, `DOCUMENT_RELATION`, `HUMAN_VERIFIED`, `INFERRED`, `HISTORICAL`）。严禁无证据猜测。
3. **严格多跳拓扑深度限制与环路截断 (Cycle-Safe BFS/DFS)**：
   - 最大遍历深度固定为 3-hop（1-hop DIRECT, 2-hop INDIRECT, 3-hop POTENTIAL），必须内建 visited 集合，杜绝循环依赖导致的死循环与指数爆炸。
4. **全栈跨工程双向穿透**：
   - 必须支持前端页面/组件 ➔ API Client ➔ HTTP Endpoint ➔ 后端 Controller ➔ Service ➔ Database Table 的全栈穿透，反向亦可从数据表变更向上追溯受波及页面。
5. **严禁写操作与自动代码修改**：
   - 影响分析输出只面向分析与人工复核，严禁向外部工程写回补丁。
6. **离线高可靠验证**：
   - 所有算法与集成测试在无外网依赖、无商用 API Key 状态下 100% 离线确定性通过。

---

## 三、影响分类与数据模型 (Baseline Section 33 & 34)

### 1. 影响级别分类 (Impact Hop Level)
- `DIRECT` (1-hop)：直接调用、直接导入或同文件定义的紧密实体。
- `INDIRECT` (2-hop)：二级传递依赖（例如 Component A ➔ Service B ➔ Controller C）。
- `POTENTIAL` (3-hop)：三级及以上波及的业务规则、监控指标或跨项目边缘端点。
- `HISTORICAL`：基于历史变更事件频繁共现（Co-change Frequency）关联的实体。

### 2. 核心输出字段
- `affected_projects: list[str]`
- `affected_pages: list[dict]`
- `affected_components: list[dict]`
- `affected_apis: list[dict]`
- `affected_services: list[dict]`
- `affected_business_rules: list[dict]`
- `impact_paths: list[ImpactPath]` (包含 nodes, edges, hops, evidence, confidence)
- `critical_path: ImpactPath`
- `shortest_path: ImpactPath`
- `overall_impact_level: str` (`NONE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `requires_human_review: bool`

---

## 四、实施细分步骤

| 步骤代号 | 任务目标 | 核心输出 |
|---|---|---|
| **Step 7.0** | MVP7 规划、架构基线固化与 6 大红线锁死 | `docs/mvp7/mvp7_step0_planning_and_baseline.md` |
| **Step 7.1 (MVP7-A)** | 影响链数据模型与多跳图谱遍历核心 (`core/impact/models.py`, `graph_traversal.py`) | `ImpactGraphTraversal`, 1~3 hop BFS |
| **Step 7.2 (MVP7-B)** | 跨工程与全栈影响传播器 (`core/impact/propagator.py`) | 页面 ➔ API ➔ Service ➔ 规则全栈分类 |
| **Step 7.3 (MVP7-C)** | 证据链与关键路径分析器 (`core/impact/path_analyzer.py`) | Shortest Path, Critical Path, Confidence |
| **Step 7.4 (MVP7-D)** | 人工复核工作流与审计报告生成 (`core/impact/review_flow.py`) | 结构化 Human Review Payload 生成 |
| **Step 7.5 (MVP7-E)** | 三大工程全量真实影响分析测试门禁 | `tests/integration/step7/test_mvp7_impact_acceptance.py` |
| **Step 7.6 (MVP7-F)** | 终审结项报告与状态看板冻结 | `docs/mvp7/mvp7_acceptance_report.md`, `MVP.md` |
