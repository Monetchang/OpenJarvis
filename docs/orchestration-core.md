# 多 Agent 内容生产系统：DB 与状态机设计（MVP 可落地）

面向：Python 后端（FastAPI + WebSocket + Celery/RQ）  
目标：支持 Chatbot 交互式流水线，阶段产物可推送展示、可暂停等待用户确认、可编辑并版本化、可按节重跑。

---

## 1. 设计目标

1. **可暂停 / 可恢复**
   - 生成大纲后进入 `WAITING_USER`，用户确认后继续。
   - Worker 异常可从 DB 状态恢复执行。

2. **产物版本化（Artifact Versioning）**
   - ReferenceCard、OutlinePlan、SectionDraft、FinalMarkdown 都要版本号。
   - 用户编辑大纲 => 产生 OutlinePlan v2，后续基于 v2 写作。

3. **可重跑粒度**
   - 重跑某个 URL 的 ref 处理
   - 重跑某一节的写作/校验
   - 重跑“从某阶段开始”（例如从大纲重新生成）

4. **对话与工作流解耦**
   - Chat 只是 UI 表达；核心系统以 workflow 为主。
   - 所有阶段产物与事件都与 workflow 绑定。

---

## 2. 核心概念与对象

### 2.1 Conversation（对话容器）
- 负责承载“聊天消息”与 UI 展示的事件流索引。
- 一个 conversation 可以对应多次 workflow（同一个话题多次生成）。

### 2.2 Workflow（一次内容生成任务）
- 代表一次完整流水线运行（从 URL 到终稿）。
- 有唯一状态、当前阶段、输入参数、当前选择的“基线版本”（如 active_outline_version）。

### 2.3 StageRun（阶段执行实例）
- 每个阶段一次执行对应一个 StageRun。
- 支持同一阶段多次运行（如 OUTLINE_PLAN v1 / v2）。
- 记录耗时、成本、错误、输入快照、输出 artifact 版本。

### 2.4 Artifact（阶段产物，版本化）
- 产物类型：reference_card / outline_plan / section_draft / verification_report / final_markdown
- 存储策略：**大文本上对象存储**，DB 存元数据 + URI + 预览。

### 2.5 EventLog（事件日志，用于前端回放与审计）
- 后端每一步产生事件：stage.started / artifact.created / stage.waiting_user 等。
- 前端 WebSocket “实时消费”，也可断线重连后按 cursor 拉取补偿。

### 2.6 UserAction（用户操作记录）
- 用户确认/编辑/重跑等操作必须落库，保证可追溯与幂等。

---

## 3. 状态机设计（Workflow FSM）

### 3.1 Workflow 状态（workflow.status）

- `CREATED`：已创建，未开始
- `RUNNING`：正在执行某阶段
- `WAITING_USER`：等待用户确认/编辑（例如大纲确认）
- `FAILED`：失败（可重试）
- `COMPLETED`：完成
- `CANCELED`：取消（可选）

### 3.2 阶段枚举（workflow.current_stage）

MVP 阶段建议：

1. `REF_PROCESS`：URL -> ReferenceCards（抓取/清洗/抽取/聚合）
2. `OUTLINE_PLAN`：ReferenceCards -> OutlinePlan
3. `WAIT_OUTLINE_CONFIRM`：等待用户确认/编辑大纲（逻辑阶段）
4. `SECTION_WRITE`：OutlinePlan -> SectionDraft（逐节）
5. `CITATION_VERIFY`：SectionDraft -> VerificationReport（逐节或汇总）
6. `EDIT_FINAL`：整合生成 FinalMarkdown
7. `DONE`：结束（逻辑阶段）

> 注意：`WAIT_OUTLINE_CONFIRM`、`DONE` 这类可被当作“逻辑阶段”，是否落为 StageRun 取决于你是否想统计与审计。建议落库（可追溯）。

### 3.3 状态转移（高层）

- `CREATED` -> `RUNNING(REF_PROCESS)`
- `RUNNING(REF_PROCESS)` -> `RUNNING(OUTLINE_PLAN)`
- `RUNNING(OUTLINE_PLAN)` -> `WAITING_USER(WAIT_OUTLINE_CONFIRM)`
- `WAITING_USER` + `user.confirm_outline` -> `RUNNING(SECTION_WRITE)`
- `RUNNING(SECTION_WRITE)` -> `RUNNING(CITATION_VERIFY)`
- `RUNNING(CITATION_VERIFY)` -> `RUNNING(EDIT_FINAL)`
- `RUNNING(EDIT_FINAL)` -> `COMPLETED(DONE)`

失败转移：

- `RUNNING(any)` -> `FAILED`（保存错误与上下文）
- `FAILED` + `user.retry` -> `RUNNING(from_stage)`（可选择从失败阶段或指定阶段重跑）

取消转移：

- `RUNNING/WAITING_USER/FAILED` + `user.cancel` -> `CANCELED`

### 3.4 幂等与并发控制

**约束：同一个 workflow 同时只能有一个 active StageRun 处于 RUNNING。**

实现建议：

- `workflow.lock_version`（乐观锁）
- 或在 StageRun 创建时做 DB 事务检查：
  - 若存在 `status=RUNNING` 的 StageRun，则拒绝新建
- 用户动作触发重跑时：
  - 先写 UserAction，再由 orchestrator 消费动作并创建新的 StageRun

---

## 4. 数据库表结构（PostgreSQL 参考）

下面以 PostgreSQL 为例，字段类型仅建议（可按你项目规范调整）。

### 4.1 conversations

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid (pk) | conversation_id |
| title | text | 可选：对话标题 |
| created_at | timestamptz |  |
| updated_at | timestamptz |  |

> conversation 只是“容器”，不要把 workflow 状态塞这里。

---

### 4.2 messages（可选，但推荐）

用于存储 Chat 展示的消息（用户输入 / 系统摘要 / agent 文本），与事件日志互补。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid (pk) | message_id |
| conversation_id | uuid (fk) |  |
| role | text | user / assistant / system |
| content | text | markdown or plain |
| meta | jsonb | 可存 stage、artifact_id 引用等 |
| created_at | timestamptz |  |

---

### 4.3 workflows

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid (pk) | workflow_id |
| conversation_id | uuid (fk) |  |
| status | text | CREATED/RUNNING/WAITING_USER/FAILED/COMPLETED/CANCELED |
| current_stage | text | REF_PROCESS/OUTLINE_PLAN/... |
| input_params | jsonb | ideaTitle/style/audience/length/language/refs 等原始输入 |
| active_reference_set_version | int | 当前使用的 reference cards 版本集（可选） |
| active_outline_version | int | 当前大纲版本（关键） |
| active_draft_version | int | 当前草稿版本（可选） |
| error_code | text | 失败码（可选） |
| error_message | text | 失败信息（可选） |
| lock_version | int | 乐观锁版本号 |
| created_at | timestamptz |  |
| updated_at | timestamptz |  |

**说明**
- `active_outline_version`：SECTION_WRITE 等后续阶段必须明确引用哪一版大纲。
- 也可用 `active_artifact_refs`（jsonb）统一存“当前基线产物”。

---

### 4.4 stage_runs（阶段执行记录）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid (pk) | stage_run_id |
| workflow_id | uuid (fk) |  |
| stage | text | REF_PROCESS/OUTLINE_PLAN/... |
| status | text | CREATED/RUNNING/SUCCEEDED/FAILED/CANCELED |
| attempt | int | 同阶段第几次（从1开始） |
| input_snapshot | jsonb | 本次执行输入快照（引用 artifact version） |
| output_artifact_ids | uuid[] | 本次产生的 artifact ids（或另建映射表） |
| started_at | timestamptz |  |
| finished_at | timestamptz |  |
| cost_meta | jsonb | token/cost/latency/model 等 |
| error_message | text | 失败信息 |
| created_at | timestamptz |  |

**建议**
- `attempt` 与 `stage` 组合（workflow_id, stage, attempt）便于定位版本。
- 如果你不喜欢 uuid[]，可用 `stage_run_artifacts` 映射表（更规范）。

---

### 4.5 artifacts（产物元数据，版本化）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid (pk) | artifact_id |
| workflow_id | uuid (fk) |  |
| stage_run_id | uuid (fk) | 由哪个 stage_run 产生 |
| type | text | reference_card / outline_plan / section_draft / verification_report / final_markdown |
| version | int | 同 type 的版本号（从1开始） |
| title | text | 可选：产物标题 |
| content_uri | text | 对象存储地址（或本地文件 path） |
| content_preview | text | 适合 UI 快速展示的摘要（<=2KB） |
| content_json | jsonb | 小型结构化内容可直接放这里（如 outline JSON） |
| created_by | text | agent / user |
| meta | jsonb | 质量分、引用覆盖率、section_id 等 |
| created_at | timestamptz |  |

**版本规则建议**
- version 按 `(workflow_id, type)` 递增。
- 对 section_draft：建议在 meta 里加 `section_id`，并以 `(workflow_id, type, section_id)` 单独做版本递增（更好重跑单节）。

---

### 4.6 artifact_versions（可选增强）

如果你希望强一致地做版本递增（避免并发写入冲突），可以加一个计数表：

| 字段 | 类型 | 说明 |
|---|---|---|
| workflow_id | uuid |  |
| artifact_type | text |  |
| scope_key | text | 可选：section_id 或 "global" |
| current_version | int | 当前版本 |
| updated_at | timestamptz |  |

写 artifact 时事务内 `SELECT FOR UPDATE` 取版本 +1。

---

### 4.7 event_logs（事件日志：回放 + 断线补偿）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid (pk) | event_id |
| workflow_id | uuid (fk) |  |
| conversation_id | uuid (fk) | 方便查询 |
| type | text | stage.started / stage.progress / artifact.created / stage.waiting_user / ... |
| payload | jsonb | 事件内容（与 WS 推送一致） |
| seq | bigint | 单 workflow 递增序号（用于前端游标拉取） |
| created_at | timestamptz |  |

**重要**
- `seq` 用于 “客户端断线后按 last_seq 补偿拉取”。
- seq 可用 DB 序列或在事务内自增。

---

### 4.8 user_actions（用户操作：确认/编辑/重跑）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid (pk) | action_id |
| workflow_id | uuid (fk) |  |
| type | text | confirm_outline / edit_outline / retry_stage / rerun_section / cancel |
| payload | jsonb | 例如新的 outline_plan 内容 |
| idempotency_key | text | 防重复提交（前端生成） |
| status | text | RECEIVED/APPLIED/REJECTED |
| created_at | timestamptz |  |
| applied_at | timestamptz |  |

---

## 5. 关键索引与约束（强烈建议）

1. `workflows(conversation_id, created_at desc)`
2. `stage_runs(workflow_id, stage, attempt)`
3. `artifacts(workflow_id, type, version)`
4. `event_logs(workflow_id, seq)`（唯一索引：workflow_id + seq）
5. 幂等：
   - `user_actions(workflow_id, idempotency_key)` 唯一
6. 并发控制：
   - 可选：`stage_runs(workflow_id) WHERE status='RUNNING'` 部分唯一索引（Postgres 支持 partial unique index）

示例（语义）：
- 同一 workflow 同时最多一个 RUNNING stage_run
- 同一 workflow 同一 type 同一 scope_key 的 version 唯一

---

## 6. Orchestrator 逻辑（状态机执行策略）

### 6.1 推荐：事件驱动 + 拉式调度

- 用户发起 workflow：创建 workflow + 写入事件 `workflow.created`
- orchestrator/worker 拉取 DB 中待执行的 stage_run：
  - `stage_run.status=CREATED` -> 执行 -> 更新为 RUNNING -> 产物落库 -> SUCCEEDED/FAILED
- 每次 stage_run 完成后，由 orchestrator 决定下一步：
  - 如果下一步是 WAITING_USER：更新 workflow.status=WAITING_USER，并写事件 `stage.waiting_user`
  - 否则创建下一个 stage_run（status=CREATED）并写事件 `stage.scheduled`

### 6.2 每个阶段的输入输出“引用基线”

在 stage_run.input_snapshot 中必须记录依赖：

- REF_PROCESS：
  - input: refs urls + 处理策略
  - output: reference_card artifacts（global version set）

- OUTLINE_PLAN：
  - input: reference_set_version
  - output: outline_plan vN

- WAIT_OUTLINE_CONFIRM：
  - input: outline_plan vN
  - output: user edit => outline_plan vN+1（created_by=user）

- SECTION_WRITE：
  - input: outline_plan vK + reference_set_version
  - output: section_draft（按 section_id 产生）

- CITATION_VERIFY：
  - input: section_draft version(s) + reference_set_version + outline_plan vK（required_sources）
  - output: verification_report（按 section_id 或汇总）

- EDIT_FINAL：
  - input: all section drafts（指定版本）+ outline vK
  - output: final_markdown v1

---

## 7. “大纲确认”人在回路的落库流程（关键路径）

### 7.1 系统生成大纲 v1
1. OUTLINE_PLAN stage_run SUCCEEDED
2. 写入 artifact：outline_plan v1（created_by=agent）
3. workflow 更新：
   - status = WAITING_USER
   - current_stage = WAIT_OUTLINE_CONFIRM
   - active_outline_version = 1
4. 写 event：
   - `artifact.created`（outline_plan v1）
   - `stage.waiting_user`（action_required = confirm_outline，携带 outline v1）

### 7.2 用户编辑并确认
1. 前端提交 `user_actions`：
   - type = confirm_outline
   - payload = 修改后的 outline JSON
   - idempotency_key = 前端生成
2. 后端消费 user_action（事务内）：
   - 写入 artifact：outline_plan v2（created_by=user）
   - 更新 workflow.active_outline_version = 2
   - 更新 workflow.status = RUNNING，current_stage = SECTION_WRITE
   - 创建 stage_run：SECTION_WRITE（CREATED）
   - user_action.status = APPLIED
3. 写 event：
   - `artifact.created`（outline_plan v2）
   - `stage.started`（SECTION_WRITE scheduled/started）

---

## 8. 重跑与回滚策略（MVP）

### 8.1 重跑某一节（rerun_section）
- 前端传：workflow_id + section_id + 可选：rewrite_instruction
- 后端：
  1. 写 user_action
  2. 创建新的 SECTION_WRITE stage_run（scope=section_id）
  3. 生成新的 section_draft version+1（该 section_id scope）
  4. 标记该 section 的 verification_report 需要重算（可立即触发）

### 8.2 从大纲重新生成（regenerate_outline）
- 创建新的 OUTLINE_PLAN stage_run（attempt+1）
- 生成 outline_plan vN
- workflow 进入 WAITING_USER（仍需确认）
- 后续章节基于新的 active_outline_version

### 8.3 从 REF_PROCESS 重跑
- 重新抓取/抽取生成 reference_card version set v2
- 注意：这会影响后续所有阶段，建议：
  - 自动将 active_outline_version 标记为“过期”
  - 或直接要求用户重新确认大纲（推荐）

---

## 9. 失败与恢复（必须明确）

### 9.1 失败记录
当某个 stage_run FAILED：
- stage_runs.status=FAILED，填 error_message/cost_meta
- workflows.status=FAILED，填 error_message/current_stage
- 写 event：`stage.failed`

### 9.2 恢复策略
- 用户点击“重试”：
  - 写 user_action: retry_stage（指定 stage）
  - orchestrator 创建新的 stage_run attempt+1
- 系统自动重试（可选）：
  - 对 REF_PROCESS 的抓取失败可自动重试 N 次（短退避）
  - 对 LLM 调用可在可控范围重试（注意幂等）

---

## 10. 事件日志与前端断线补偿（与 DB 强相关）

### 10.1 事件写入原则
- **所有 WS 推送必须先落 event_logs 再推送**
- 断线时前端记录 last_seq
- 重连后 HTTP 拉取：
  - `GET /workflows/{id}/events?after_seq=xxx&limit=200`
- 前端补齐渲染后继续走 WS 实时流

### 10.2 事件最小集合（建议）
- workflow.created
- stage.scheduled
- stage.started
- stage.progress
- artifact.created
- artifact.updated
- stage.waiting_user
- stage.completed
- stage.failed
- user_action.applied

---

## 11. 最小实现建议（Cursor 开发指引）

### 11.1 先做 DB + 状态机闭环（不接 LLM 也能跑通）
1. migrations：建表 + 索引 + 约束
2. workflow create API：写入 workflows + stage_run(REF_PROCESS CREATED) + event
3. worker：拉取 CREATED stage_run，模拟执行，写 artifact，推进下一阶段
4. WAITING_USER：模拟生成 outline，停住，推送等待
5. confirm_outline API：写 user_action + artifact v2 + 推进 SECTION_WRITE
6. 最终产物：final_markdown v1，workflow COMPLETED

### 11.2 再逐步替换“模拟执行”为真实 Agent
- REF_PROCESS：接入抓取/清洗/抽取/聚合
- OUTLINE_PLAN：接入 LLM
- SECTION_WRITE：逐节写（并行可以后置）
- CITATION_VERIFY：先做规则校验，再上 LLM 校验
- EDIT_FINAL：合稿与脚注生成

---

## 12. 决策点（你需要在实现前定死的 3 件事）

1. **Artifact 大文本存储策略**
   - DB 只存 preview + uri，全文放对象存储（推荐）

2. **section_draft 的版本范围**
   - 版本按 (workflow_id, section_id) 递增（推荐）
   - 不要只用全局 version，否则重跑单节会难管理

3. **“active 基线”如何表示**
   - 简单方案：workflows.active_outline_version + active_reference_set_version
   - 泛化方案：workflows.active_artifacts（jsonb：type->artifact_id/version）

---

## 13. 你可以直接用的最小表单（MVP）

必选（最少 5 张表）：
- workflows
- stage_runs
- artifacts
- event_logs
- user_actions

可选增强：
- conversations / messages（UI 体验更好）
- artifact_versions（版本递增更稳）
- stage_run_artifacts（更规范映射）

---

## 14. 验收标准（开发完成后你应该能做到）

1. 一个 workflow 从 CREATED 跑到 COMPLETED，全程可在前端看到阶段进度与产物
2. 大纲生成后系统进入 WAITING_USER，用户编辑确认后继续
3. 用户能重跑某节并产生新版本 section_draft
4. 断线重连后能通过 event_logs 回放完整过程

---