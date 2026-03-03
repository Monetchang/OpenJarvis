你将为本项目实现一个可复用的“工作流编排核心（orchestration-core）”，它是公共基础设施，不绑定具体业务（例如博客生成）。请严格基于仓库中的《多 Agent 内容生产系统：DB 与状态机设计（MVP 可落地）》文档实现，并做通用化抽象。

总体目标：
- 提供一个通用的 Workflow 状态机 + StageRun 执行记录 + Artifact 版本化 + EventLog 事件回放 + UserAction 人在回路交互的核心能力。
- 允许上层业务（博客生成、报告生成、爬虫摘要、评测流水线等）通过“注册 Stage 处理器（handlers）”接入，而无需修改核心逻辑。
- 核心需要支持：暂停等待用户、恢复、重跑某阶段/某 scope（如 section_id）、幂等、断线回放。

实现边界（非常重要）：
1) 核心模块不得包含任何“博客/RAG/Agent 写作”等业务字段或枚举；stage 名称、artifact 类型应可扩展（可用字符串+约束，而不是写死 enum）。
2) 核心模块只负责：状态机推进、持久化、事件记录、调度触发；业务逻辑由上层以 handler 的形式实现。
3) 在不实现具体 LLM/抓取逻辑的情况下，也必须提供可运行的最小 demo：用 mock handlers 走通 workflow 从 CREATED -> WAITING_USER -> RUNNING -> COMPLETED，并能重跑某个 stage/scope。
4) 必须按文档建表（workflows, stage_runs, artifacts, event_logs, user_actions），并实现关键索引/约束（幂等 key、单 workflow 单 RUNNING stage_run 等）。

架构要求：
- 新增一个包：orchestration_core/
  - models/（SQLAlchemy ORM 或你项目现有 ORM）
  - repository/（DB 访问层）
  - fsm/（状态机与转移规则）
  - dispatcher/（stage handler 注册与调用）
  - events/（event schema 与 event writer）
  - api/（对外 API：create workflow、submit user action、query events、get artifacts 等）
- 核心对外提供清晰的接口：
  - create_workflow(input_params) -> workflow_id
  - submit_user_action(workflow_id, action_type, payload, idempotency_key)
  - list_events(workflow_id, after_seq, limit)
  - get_artifact(artifact_id) / list_artifacts(workflow_id, type, scope)
  - (internal) schedule_next_stage(workflow_id) / run_stage(stage_run_id)

扩展点（必须实现）：
- Stage Handler 注册机制：
  - handler(stage_name) -> (artifacts_created, next_directive)
  - next_directive 支持：CONTINUE / WAIT_USER(action_required) / STOP / FAIL
- 支持 scope_key（可选）：用于 section_id 等细粒度重跑
- Artifact type 与 stage name 使用字符串，但要有最小校验（例如长度、字符集、黑名单）避免脏数据

事件与回放：
- 所有推送事件必须先落 event_logs，再推送（后续前端 WS 会用）。
- seq 必须在单 workflow 内递增，用于断线补偿：GET /workflows/{id}/events?after_seq=xxx

验收标准（必须通过）：
- 提供一套 mock workflow（2-3个 stages + 一个 WAIT_USER checkpoint）：
  1) stageA 产出 artifactA
  2) stageB 产出 artifactB 并进入 WAITING_USER（action_required=confirm）
  3) 用户提交 action 后进入 stageC，产出 final artifact，workflow COMPLETED
- 支持 rerun：重跑 stageC（或某 scope）会生成新 artifact version，并记录新的 stage_run attempt
- 支持恢复：服务重启后可继续执行 CREATED 的 stage_run
- 所有关键事件在 event_logs 中可查询回放

开发方式：
- 先实现 DB 与 repository + 事件写入
- 再实现 FSM 与 stage 调度器
- 最后补齐 API（HTTP 端点即可，WebSocket 推送可留 TODO，但 event_logs 必须完整）
- 全程补充 README：说明如何注册 stage handlers、如何运行 demo、如何扩展业务

禁止事项：
- 不要把业务 prompt、LLM 调用、网页抓取写进核心模块
- 不要把 stage 列表写死成博客生成专用枚举
- 不要省略幂等与并发约束（尤其是单 workflow 单 RUNNING stage_run）

请在实现过程中持续自检以下约束：
- [ ] 核心模块中不出现 “blog / rag / outline / section” 等业务词（可出现在 demo 里，但 demo 与 core 必须隔离）
- [ ] stage 与 artifact type 可扩展（字符串化 + 校验），而不是固定枚举
- [ ] artifact 版本递增在并发下安全（至少用事务或专门的 version 表）
- [ ] user_actions 幂等（workflow_id + idempotency_key 唯一）
- [ ] event_logs 顺序可回放（workflow_id + seq 唯一递增）
- [ ] 重跑会产生新的 stage_run attempt 与新的 artifact version（不覆盖旧版本）
- [ ] WAITING_USER 能正确阻塞流程，用户 action 后能继续推进

扩展性要求（未来要支持更多能力）：
- 允许同一个 workflow 存在多个分支 stage_run（例如并行处理多个 items），但 MVP 只需支持串行；请预留字段：scope_key、parent_stage_run_id（可选）
- 允许上层业务定义自己的 artifact schema：artifact.content_json 存结构化内容；content_uri 存大文本
- 允许 handler 返回 progress events（stage.progress），核心负责落库与广播
- 允许 workflow 定义“运行计划”（例如 stage 顺序配置），MVP 可先用代码里简单规则，但请把规则封装在 fsm/ 便于替换成配置驱动