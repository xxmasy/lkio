# LKIO MVP2-E 主实施规划 — API 契约端到端追溯 (API Traceability Master Plan)

> **阶段代号**：**MVP2-E**  
> **阶段全称**：**API to Backend Contract Traceability (前端 API 到后端控制器的契约端到端追溯)**  
> **前置阶段状态**：  
> - **MVP2-A ~ MVP2-D = COMPLETED / FROZEN**  
> **当前阶段状态**：**READY_TO_EXECUTE**  
> **核心使命**：打通代码智能的“任督二脉”——将前端 API 请求调用通过 HTTP Endpoint 准确连接到后端 Controller、进而延展至 Service 与 DB 操作，构建端到端全链路调用追溯。

---

## 一、5 大 API 追溯架构锁 (Architecture Locks)

1. **`LOCK-TRACE-01` (端点客观性锁)**：
   - HTTP Endpoint 是前后端交互的客观契约，由 `(HTTP_METHOD, NORMALIZED_PATH)` 确定。
   - 提取自 Tree-sitter AST（Spring Boot `@RequestMapping`, `@GetMapping`, 前端 `requestClient.get`, `axios.post` 等），严禁 LLM 幻觉生成。
2. **`LOCK-TRACE-02` (路径规格化锁)**：
   - 统一处理路径变量（`{id}` 与 `:id` 规范化为统一格式 `{param}`）、前后置斜杠与公共前缀。
3. **`LOCK-TRACE-03` (追溯链路分层锁)**：
   - 前端调用点 ──► `routes_to` ──► HTTP Endpoint
   - HTTP Endpoint ──► `handled_by` ──► 后端 Controller Method
   - Controller Method ──► `calls` ──► Backend Service Method
   - 每层关系独立锚定，置信度严格标定（完全匹配=1.00000，参数模糊匹配=0.90000）。
4. **`LOCK-TRACE-04` (幂等持久化与软删除锁)**：
   - 追溯关系采用确定性唯一键 `RELATION:TRACE:...`，连续重跑 3-Set 100% 恒等。
5. **`LOCK-TRACE-05` (源工程物理只读红线)**：
   - `HELLO_FE`, `HELLO_BE`, `L2C_FE` 严格物理只读，`git status --porcelain` 恒为 0。

---

## 二、子阶段划分 (E-00 ~ E-05)

| 阶段 | 交付物 | 核心门禁 |
|---|---|---|
| **E-00** | API 契约追溯主规划 | Master Plan 审阅与 5 大架构锁冻结 |
| **E-01** | 前端 API Client 路由抽取器 (`FrontendApiExtractor`) | `Gate E1`: TS/JS/Vue 前端请求路径与 Method 提取 |
| **E-02** | 后端 Controller 路由抽取器 (`BackendControllerExtractor`) | `Gate E2`: Spring Boot `@RequestMapping` 组合路由与服务调用提取 |
| **E-03** | 契约对齐与追溯链路生成引擎 (`ApiTraceabilityEngine`) | `Gate E3`: 前后端 Endpoint 精确与参数匹配、全链路图谱拼接 |
| **E-04** | API 追溯图谱持久化与生命周期 (`ApiTracePersistenceService`) | `Gate E4`: 追溯边入库、软删除与双扫描 3-Set 恒等证明 |
| **E-05** | 真实工程系统集成验证 (`test_api_traceability_e05.py`) | `Gate E5`: 覆盖真实 Controller 与 API 调用，源码只读审计 |
