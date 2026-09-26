# LKIO MVP8 (Evaluation / Calibration / Learning Loop) 实施基线与架构规划

> **阶段代号**：**MVP8**  
> **阶段名称**：**Evaluation / Calibration / Learning Loop（评估校准与学习闭环）**  
> **前置依赖**：MVP0 (FROZEN), MVP1 (FROZEN), MVP2 (FROZEN), MVP3 (FROZEN), MVP4 (FROZEN), MVP5 (FROZEN), MVP6 (FROZEN), MVP7 (FROZEN)  
> **当前状态**：**IN_PROGRESS (ACTIVE)**  
> **基线依据**：`LKIO_本地知识智能操作系统_MVP实施基线_v0.1.md` 第 35 条（Laya Evaluation / Calibration）、第 36 条（Training & Data Policy）、第 3150 行（MVP8 验收条目）

---

## 一、MVP8 核心定位与设计原则

根据实施基线第 35 条与第 36 条：
> **“目标不是让 confidence 盲目最大化，而是让 confidence 越高的预测，实际正确率越高（预期校准误差 ECE 极小化）。必须建立基准数据集（Gold, Validation, Test, Boundary, Abstain, Conflict Cases），计算严谨的 Accuracy、Macro-F1、Brier Score、ECE，并通过真实 Outcome 反馈闭环驱动置信度自适应校准。”**

在 LKIO 架构中：
- MVP6 实现了结构化决策协议与首批 4 大任务。
- MVP7 实现了多跳影响链与全栈跨工程穿透。
- **MVP8 是全系统的质量守护者与学习演进闭环**：
  1. 建立覆盖 4 大决策任务的标准 Gold Dataset 基准集。
  2. 实现高精度的可解释置信度校准算法（Calibration & ECE）。
  3. 搭建真实 Outcome 结果反馈闭环（Outcome Loop），记录真实代码运行/人工审核结果并反馈调整历史准确率矩阵。

---

## 二、🛑 永久冻结架构红线 (Inviolable Redlines)

1. **源项目绝对物理只读**：
   - `HELLO_FE`、`HELLO_BE`、`L2C_FE` 绝对只读。
2. **严禁数据泄漏与随机交叉混淆**：
   - 依据基线第 36 条：“没有 training_manifest.json, validation_manifest.json, test_manifest.json, label_schema.json 不能进行评估。数据拆分必须按时间或工程维度隔离，不能随机拆分导致同一变更谱系同时出现在训练集和测试集。”
3. **校准目标第一法则 (Calibration First)**：
   - 核心优化目标是 **ECE (Expected Calibration Error) 最小化**与 **Brier Score 优化**，坚决反对盲目拉高置信度。高置信度低准确率被视为严重系统故障。
4. **真实 Outcome 闭环必须具备因果证据**：
   - 记录 Outcome 回调必须绑定决策 ID 与对应实体的 Git Commit SHA 或测试执行证据，严禁伪造反馈。
5. **严禁自动写操作**：
   - 学习闭环仅校准内存/持久化的模型置信度与路由策略权重，绝对不自动修改外部源代码。
6. **离线高可靠验证**：
   - 所有评估指标、校准算法与测试用例 100% 离线运行通过。

---

## 三、四大清单文件与指标体系 (Baseline Section 35 & 36)

### 1. 清单文件清单 (Manifests)
- `training_manifest.json`：历史事件与样本
- `validation_manifest.json`：近期基准样本
- `test_manifest.json`：未知盲测样本
- `label_schema.json`：4 大决策任务标准化标签空间

### 2. 核心评估指标
- **Accuracy**：整体命中率
- **Macro-F1**：多分类不平衡加权 F1-Score
- **Brier Score**：概率校准均方误差 $\frac{1}{N}\sum (p_i - y_i)^2$
- **ECE (Expected Calibration Error)**：10-bin 置信度与准确率的期望偏差
- **Abstain Rate**：拒答/转人工比例
- **Confusion Matrix**：混淆矩阵

---

## 四、实施细分步骤

| 步骤代号 | 任务目标 | 核心输出 |
|---|---|---|
| **Step 8.0** | MVP8 规划、架构基线固化与 6 大红线锁死 | `docs/mvp8/mvp8_step0_planning_and_baseline.md` |
| **Step 8.1 (MVP8-A)** | 基准数据集与 Manifest 管理体系 (`core/evaluation/models.py`, `dataset.py`) | 4 大任务 Gold/Validation/Test 集与 Manifest |
| **Step 8.2 (MVP8-B)** | 评估指标计算引擎 (`core/evaluation/metrics.py`) | Accuracy, Macro-F1, Brier, ECE, Confusion Matrix |
| **Step 8.3 (MVP8-C)** | 置信度校准引擎 (`core/evaluation/calibration.py`) | ECE 分箱分析与置信度平滑校准 |
| **Step 8.4 (MVP8-D)** | Outcome 结果学习闭环 (`core/evaluation/outcome_loop.py`) | 真实结果反馈记录与历史权重更新 |
| **Step 8.5 (MVP8-E)** | 全系统全量评测与 Gold Set 验收门禁 | `tests/integration/step8/test_mvp8_evaluation_acceptance.py` |
| **Step 8.6 (MVP8-F)** | LKIO 全系统终审结项与实施基线总冻结 | `docs/mvp8/mvp8_acceptance_report.md`, `MVP.md` |
