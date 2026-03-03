```markdown
# 选择 2 设计方案：LangGraph 负责业务编排，orchestration-core 负责产品级运行与可观测

面向：Python 后端（你已有 orchestration-core + WS 事件流）  
目标：让 **LangGraph 成为“业务流程编排的唯一真相”**，而 orchestration-core 退到“操作系统/运行平台”层：记录、回放、WS、产物版本、人机交互幂等、恢复重跑。

---

## 1. 核心思想

### 1.1 从“多 Stage 编排”降级为“单图运行”
当前（你觉得不值的原因）：
- orchestration-core 决定 REF_PROCESS → OUTLINE → SECTION → FINAL
- LangGraph 只在每个 stage 内跑几步

选择 2（目标状态）：
- orchestration-core 只负责启动/恢复 **一次 GraphRun**
- 业务步骤（抓取、抽取、大纲、等待确认、写作、校验、合稿）全部写在 **一个 LangGraph 图**里
- core 只关心：
  - 运行记录（run / node_run）
  - event_logs（seq 回放）
  - artifacts（版本化）
  - user_actions（幂等）
  - WS 推送与补偿

一句话：
> **Graph 是业务流程；core 是运行与数据一致性层。**

---

## 2. 数据模型与对象（与现有 core 的映射）

### 2.1 保留并继续使用（现有 core）
- `workflow`：一次业务任务实例（仍然需要，用于对外 API 与事件流归属）
- `stage_run`：改名不必改表，但其语义收敛为 **GraphRun**（一个 workflow 通常只有 1 个主 stage_run）
- `event_logs`：graph/node 事件都写入，作为前端回放事实源
- `artifacts`：graph 中间与最终产物都落库版本化
- `user_actions`：用于 WAITING_USER 的幂等与审计

### 2.2 stage 的新语义（关键）
把 workflow 的 stage 简化为极少数（建议 2 个）：
- `GRAPH_RUN`：正在运行 LangGraph
- `WAITING_USER`：图执行中断，等待用户操作（例如确认大纲）

> 也可以保留你原有 stage 字符串，但不再用于决定流程顺序，只作为“展示标签”。推荐尽快收敛为 `GRAPH_RUN`，减少重复编排。

---

## 3. LangGraph 图设计（博客生成全流程）

### 3.1 图的输入状态（Graph State）
由 `workflow.input_params` + 现有 artifacts（若有）构成，推荐结构：

- `idea`: { title, style, audience, length, language }
- `refs`: [url...]
- `ref_cards`:（可空）结构化引用卡列表
- `outline`:（可空）大纲 JSON
- `outline_confirmed`: bool
- `sections`:（可空）按 section_id 的草稿 map
- `verification`:（可空）校验报告
- `final_md`:（可空）最终 Markdown
- `control`: { request_id, retry_hint, scope_key? }（可选）

### 3.2 图的节点（Nodes）
推荐最小节点集合（先 MVP）：

1) `fetch_and_extract_refs`
- 输入：refs
- 输出：ref_cards（并落 artifact：reference_card，scope_key=url_hash）

2) `propose_outline`
- 输入：idea + ref_cards
- 输出：outline（并落 artifact：outline_plan vN）

3) `interrupt_for_outline_confirm`（中断节点）
- 逻辑：如果 outline 未确认 → 触发 WAITING_USER
- 输出：无（只发起中断）

4) `write_sections`
- 输入：outline + ref_cards
- 输出：sections（并落 artifact：section_draft，scope_key=section_id）

5) `verify_citations`
- 输入：sections + ref_cards
- 输出：verification_report（artifact）

6) `finalize_markdown`
- 输入：outline + sections + verification
- 输出：final_md（artifact: final_markdown）

### 3.3 图的边（Edges）
- fetch_and_extract_refs → propose_outline → interrupt_for_outline_confirm
- interrupt_for_outline_confirm（确认后）→ write_sections → verify_citations → finalize_markdown → END

---

## 4. “中断/恢复”策略（重点：让 LangGraph 真正成为编排）

你有两种实现方式，建议 **先用轻量可落地的方式**，不用追求 LangGraph 原生 checkpoint 的全部能力。

### 4.1 MVP 推荐：外部化中断（core 作为中断管理器）
- 图运行到 `interrupt_for_outline_confirm` 时：
  - GraphRunner 返回 `WAITING_USER(action_required="confirm_outline", payload={outline_artifact_id})`
- orchestration-core 负责：
  - workflow.status = WAITING_USER
  - 写 event：`stage.waiting_user`
- 用户确认后：
  - 前端 `POST /workflows/{id}/actions`（confirm_outline + 新 outline）
  - core 写 user_actions（幂等），并保存新 outline artifact（created_by=user）
  - 再创建一个新的 stage_run（或复用同一 stage_run 的 attempt+1）并重新运行 graph，但带入：
    - `outline_confirmed=true`
    - `outline` 读取最新 artifact
  - graph 从 interrupt 节点之后继续（实现方式：图的入口检查 outline_confirmed，决定从哪个节点开始；或在 runner 内“跳过已完成节点”）

优点：实现快、与你现有 core 完美契合  
缺点：不是严格意义的“原地 resume”，但对产品体验足够

### 4.2 进阶：原生 checkpoint/resume（后续再做）
- 将 LangGraph 的 checkpoint state 存到 artifact：`graph_checkpoint`
- 用户 action 后从 checkpoint resume  
这需要更复杂的状态序列化与 runner 支持，建议第二期再上。

---

## 5. 核心适配层：GraphRuntimeContext（LangGraph ↔ core 的唯一接口）

> 这层决定了你能否把 LangGraph 的优势“产品化”。

GraphRuntimeContext 必须由 orchestration-core 创建并注入给 GraphRunner，提供：

### 5.1 必需接口
- `append_event(type, payload, *, persist=True)`
  - persist=True：写 event_logs + broadcast（用于 node started/completed）
  - persist=False：只 WS 推送不落库（用于心跳等控制消息）

- `save_artifact(type, content_json=None, content_uri=None, scope_key=None, meta=None, created_by="agent")`
  - 内部保证版本递增与事务一致性

- `load_artifacts(type, scope_key=None, latest=True)` / `get_active_outline()` 等辅助
  - 让图能从“当前最新版本”取输入

- `request_user_action(action_required, payload)`
  - 将 workflow 置 WAITING_USER 并写入 `stage.waiting_user` 事件（由 core 完成）
  - GraphRunner 返回 WAITING_USER

### 5.2 强约束
- 图内不得直接写 DB
- 图内不得直接 WS 广播
- 所有持久化都走 runtime 提供的方法（可审计、可回放、可幂等）

---

## 6. 事件规范（图/节点 → event_logs）

### 6.1 必写（用于回放/审计）
- `graph.started` / `graph.completed` / `graph.failed`
- `node.started` / `node.completed` / `node.failed`
- `artifact.created`（由 save_artifact 自动产生）

payload 最小字段建议：
- graph.*: { graph, workflow_id, stage_run_id }
- node.*: { graph, node, message?, scope_key? }

### 6.2 不写入 event_logs（只 WS 推送）
- 心跳：`ws.ping/pong`
- 过于频繁的 token 级输出

---

## 7. API 交互流程（前端视角保持不变）

1) `POST /workflows`（input_params）
- core 创建 workflow + stage_run(GRAPH_RUN) + 触发 graph 执行

2) 前端：
- `GET /workflows/{id}/events?after_seq=0` + `WS /ws/workflows/{id}`

3) 运行中，前端收到：
- node started/completed
- artifact created
- 如果需要确认大纲：stage.waiting_user

4) 用户确认：
- `POST /workflows/{id}/actions`（confirm_outline + edited outline artifact）
- core 触发 graph 继续运行

---

## 8. 重跑与局部重做（scope_key 与图的结合）

你现有 core 已支持 rerun 概念，选择 2 下建议这样落地：

- 对“重写某一节”：
  - user_action: `rerun_section(section_id, instruction?)`
  - core 保存 action
  - graph 以 `scope_key=section_id` 运行一个“局部子图”或在同一图中选择性执行 `write_sections` 的单节路径
  - artifacts: section_draft 的该 section_id 版本递增

> LangGraph 的优势在这里更明显：局部路径是图的一部分，而不是你在 core 里塞一堆 if/else。

---

## 9. 迁移策略（不推翻现有系统）

### 9.1 迁移目标
- 逐步把你原先各 stage 的业务逻辑迁移到一个统一 graph
- core 的 stage 数量收敛为 GRAPH_RUN / WAITING_USER

### 9.2 推荐步骤
1) 新增 graph runner 与 demo graph（只发事件，不做真实 LLM）
2) 把一个真实业务链路迁移进 graph（比如 outline 生成 + waiting_user）
3) 再迁移 sections/verify/final
4) 最后把老的多 stage 推进逻辑下线（或变成兼容层）

---

## 10. 验收标准（选择 2 是否成功）

- [ ] workflow 的推进不再依赖“多 stage 顺序”，graph 内决定业务路径
- [ ] node 级事件能回放（event_logs）
- [ ] artifacts 与版本化仍由 core 管理
- [ ] WAITING_USER 由 graph 触发、core 承接，确认后能继续
- [ ] 重跑某 section 不需要 core 改流程，只需图选择性执行

---
```

---

