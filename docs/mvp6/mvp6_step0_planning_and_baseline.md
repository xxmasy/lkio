# LKIO MVP6 (Laya Decision Engine) 实施基线与架构规划

> **阶段代号**：**MVP6**  
> **阶段名称**：**Laya Decision Engine（Laya 结构化决策引擎）**  
> **前置依赖**：MVP0 (FROZEN), MVP1 (FROZEN), MVP2 (FROZEN), MVP3 (FROZEN), MVP4 (FROZEN), MVP5 (FROZEN)  
> **当前状态**：**IN_PROGRESS (ACTIVE)**  
> **基线依据**：`LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md` 第 29 条（Laya Decision Engine 接入方式与 4 大任务）、第 30 条（Decision Request 结构）、第 31 条（Decision Result）、第 32 条（Confidence Policy）、第 3130 行（MVP6 验收条目）

---

## 一、MVP6 核心定位与设计原则

根据实施基线第 29.1 与 29.2 条：
> **“LKIO 内部定义统一决策接口 DecisionEngine(Protocol)，Laya 只是其实现之一。首批只做 4 个核心决策任务，杜绝一开始训练几十种任务。Laya 只接收经过 Knowledge Core / Retrieval 处理的结构化 state，不直接扫描整个磁盘。”**

在 LKIO 架构中：
- MVP0~MVP2 提供客观代码与结构事实（Entities, Relations, AST, API Contracts）。
- MVP3~MVP4 提供混合检索与证据投影（Hybrid RAG, Evidence Wiki）。
- MVP5 提供时间轴与变更演化轨迹（Events, Timeline, First Appearance, Frequency）。
- **MVP6 将上述多源事实熔炼为决策判断能力**：
  1. 变更影响范围研判 (`CHANGE_IMPACT`)
  2. 事实证据充分性审计 (`EVIDENCE_SUFFICIENCY`)
  3. 智能问答路径路由 (`QUERY_ROUTE`)
  4. 自动化写操作安全放行闸门 (`ACTION_GATE`)

---

## 二、🛑 永久冻结架构红线 (Inviolable Redlines)

1. **源项目绝对物理只读**：
   - `HELLO_FE`、`HELLO_BE`、`L2C_FE` 绝对只读。
2. **严禁无状态全盘暴力扫描**：
   - 决策引擎必须只输入结构化的 `DecisionRequest.state`（已由 RAG/Graph/Event 精准召回），严禁在决策层直接遍历文件系统。
3. **No-Write Action Gate 强制死锁**：
   - 依据基线第 32 条：“0.95 置信度不是自动写代码许可证。MVP0~MVP6 全阶段严禁任何写回源项目操作。” Action Gate 对任何写操作必须严格拦截并返回 `DENIED_BY_READONLY_GATE`。
4. **统一可解释置信度模型 (Confidence Policy)**：
   - `final_confidence` 严格结合 `model_confidence`、`evidence_confidence`、`graph_confidence` 与 `historical_accuracy`。
   - 分级策略：
     - `< 0.65`：强制人工审核 (`HUMAN`)。
     - `0.65 <= c < 0.85`：需要复核 (`REVIEW`)。
     - `0.85 <= c < 0.95`：二次校验 (`SECOND_CHECK`)。
     - `>= 0.95`：严格经由 Action Policy 策略放行。
5. **接口协议与具体实现彻底解耦**：
   - 上层业务仅依赖 `DecisionEngine(Protocol)` 抽象协议，支持 `LayaDecisionEngine`、`RuleBasedDecisionEngine`、`LLMJudgeDecisionEngine` 随时平滑替换。
6. **离线高可靠验证**：
   - 所有决策逻辑与单元/集成测试在无网络、无付费外部 API 下 100% 离线确定性通过。

---

## 三、四大标准决策任务规范

### 1. `CHANGE_IMPACT` (变更影响度评估)
- **选项空间**：`["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]`
- **研判依据**：变更实体的图谱入度/出度（Page -> Component -> Service -> DB Table）、跨工程契约调用（Frontend API -> Backend Controller）、波及文件数量与历史故障敏感度。

### 2. `EVIDENCE_SUFFICIENCY` (证据充分性评估)
- **选项空间**：`["INSUFFICIENT", "PARTIAL", "SUFFICIENT", "STRONG"]`
- **研判依据**：事实依据的覆盖度（Source Entity Keys, Document Citations, Commit References）、图谱静态确定性（置信度 1.0 的关系链比例）。

### 3. `QUERY_ROUTE` (智能问答与请求路由)
- **选项空间**：`["ENTITY", "CODE", "GRAPH", "RAG", "EVENT", "WIKI", "HUMAN"]`
- **研判依据**：自然语言意图特征（符号定义/结构追溯/时序变更/综合文档架构）。

### 4. `ACTION_GATE` (动作执行准入门禁)
- **选项空间**：`["AUTO", "REVIEW", "ESCALATE", "REJECT"]`
- **研判依据**：置信度阈值、操作类型（READ / WRITE）、受影响资产安全性。当前全阶段写操作一律拦截。

---

## 四、实施细分步骤

| 步骤代号 | 任务目标 | 核心输出 |
|---|---|---|
| **Step 6.0** | MVP6 规划、架构基线固化与 6 大红线锁死 | `docs/mvp6/mvp6_step0_planning_and_baseline.md` |
| **Step 6.1 (MVP6-A)** | 决策请求与响应核心数据结构 (`core/decision/models.py`) | `DecisionRequest`, `DecisionResult`, `DecisionTask`, `DecisionState` |
| **Step 6.2 (MVP6-B)** | 置信度策略与 No-Write Action Gate (`core/decision/policy.py`) | `ConfidencePolicy`, `ActionGatePolicy` |
| **Step 6.3 (MVP6-C)** | 四大决策任务评估器 (`core/decision/tasks/`) | `ChangeImpactEvaluator`, `EvidenceSufficiencyEvaluator`, `QueryRouteEvaluator`, `ActionGateEvaluator` |
| **Step 6.4 (MVP6-D)** | Laya 决策引擎适配器与工厂 (`core/decision/`) | `DecisionEngine(Protocol)`, `LayaDecisionEngine`, `DecisionEngineFactory` |
| **Step 6.5 (MVP6-E)** | 三大工程全量真实决策测试门禁 | `tests/integration/step6/test_mvp6_decision_acceptance.py` |
| **Step 6.6 (MVP6-F)** | 终审结项报告与状态看板冻结 | `docs/mvp6/mvp6_acceptance_report.md`, `MVP.md` |
