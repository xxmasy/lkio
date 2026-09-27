# LKIO-Bench v1.0 Baseline Freeze (Stage 0)

> **基线状态**：`FROZEN`  
> **冻结时间**：`2026-09-27T11:45:00Z`  
> **冻结依据**：[LKIO_持续基础设施演进开发规范.md](../../docs/LKIO_持续基础设施演进开发规范.md) Section 2 (Stage 0)

## 冻结清单
1. **15 层知识与推理基准指标**（Layer 1 ~ Layer 15 全部通过，详见 `metrics.json`）；
2. **8 大基线消融实验矩阵**（包括保留的真实劣势：Hybrid+Reranker 文本召回 0.9500 vs Full LKIO 0.9250，以及 BM25 极速延迟）；
3. **120 例盲测决策集**（宏平均 F1 = 0.8000，微平均 F1 = 0.9167，准确率 = 91.67%）；
4. **六大图遍历核心不变量**（I1 Cycle Safety, I2 Seed Isolation, I3 Depth Bound, I4 Shortest-Hop Preservation, I5 Monotonic Classification, I6 Evidence Accumulation）；
5. **数据集哈希完整性校验**：`manifests/` 下训练、验证、测试集 SHA-256 签名锁定。
