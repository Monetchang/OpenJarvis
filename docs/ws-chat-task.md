````markdown
# Cursor 分阶段执行脚本（后端）：WebSocket 交互与事件流（不含前端）

说明：
- 本脚本仅覆盖 **后端实现**（FastAPI + orchestration-core + event_logs + WebSocket）
- 前端实现将放在另一个项目里，另出独立文档（本脚本不涉及）
- 你每次只复制 **一个阶段** 给 Cursor 执行；完成后必须停下并给出变更与验证方式

全局约束（每个阶段都必须遵守）：
- 不允许删除文件
- 不允许重构/改动 orchestration_core 的核心逻辑与表结构（除非该阶段明确要求）
- 所有事件写入必须 **先落 event_logs**（commit 成功）再广播
- 事件 envelope 必须统一：`workflow_id + seq + type + payload + created_at`
- 遇到不确定字段：优先复用现有 schema/模型；不要自创多套

---

## Stage 0：任务理解与现状盘点（不写代码）
**复制给 Cursor：**
```text
请阅读 docs/ws-chat-mvp.md（后端相关部分）以及现有 orchestration-core 代码结构，输出：
1) 需要新增的后端路由清单（HTTP + WS）
2) 你将采用的 event 写入入口（event writer）设计：放在哪个模块、如何生成 seq
3) WebSocket 广播器（broadcaster）设计：订阅池结构与生命周期
4) 每一步实现顺序（必须与文档一致）
注意：此阶段不要写任何代码，不要修改任何文件。输出后停止。
````

验收点：

* 明确“写 DB -> commit -> broadcast”执行路径
* 清晰列出阶段拆分与文件改动范围

---

## Stage 1：POST /workflows（创建 workflow + workflow.created 事件写入）

**复制给 Cursor：**

```text
实现后端能力：创建 workflow 并写入 workflow.created 事件。

实现内容：
- 新增 POST /workflows
- 创建 workflows 记录（status=CREATED 即可）
- 写入 event_logs 一条 workflow.created 事件（必须生成 seq）
- 返回 workflow_id

要求：
- 不允许改动 orchestration_core 的表结构
- event 写入必须走统一入口（新增 event writer 模块/函数）
- 完成后输出：
  1) 修改/新增文件列表（删除文件必须为空）
  2) 如何用 curl 验证（请求与响应示例）
  3) event_logs 中应出现的记录示例（字段名必须与 envelope 一致）

完成后停止。
```

验收点：

* POST /workflows 可用
* event_logs 出现 workflow.created 且 seq 正常

---

## Stage 2：GET /workflows/{id}/events（断线补偿拉取）

**复制给 Cursor：**

```text
实现事件补偿接口：

- GET /workflows/{workflow_id}/events?after_seq=0&limit=200
- 返回 events（按 seq 升序）与 last_seq
- limit 最大 200，参数缺省给默认值

要求：
- 查询必须走 event_logs 表
- 返回 events 必须是统一 envelope（workflow_id/seq/type/payload/created_at）
- workflow 不存在要返回明确错误（例如 404）
- 完成后输出：
  1) 修改/新增文件列表
  2) curl 测试示例（after_seq=0 与 after_seq=last_seq）
  3) 边界条件说明（无事件、limit 超界）

完成后停止。
```

验收点：

* after_seq 补偿正确
* last_seq 正确反映最后一条事件的 seq

---

## Stage 3：WebSocket 订阅 /ws/workflows/{id}（连接与广播骨架）

**复制给 Cursor：**

```text
实现 WebSocket 订阅通道（仅连接与广播骨架）：

- WS /ws/workflows/{workflow_id}
- 连接时校验 workflow 是否存在（不存在则 close）
- 建立内存订阅池 subscribers[workflow_id]（Set of connections）
- 新增 EventBroadcaster（内存版）用于广播事件到订阅者
- 在 Stage 1 的 workflow.created 写入后，除了落库，还要广播给已订阅的客户端（如果此时有人订阅）

要求：
- 广播必须发生在 event_logs commit 成功之后
- 广播失败不能影响 DB 写入
- 断开连接要正确清理订阅池
- 完成后输出：
  1) 修改/新增文件列表
  2) 如何用 ws client 验证（例如 websocat 的命令或 python websocket-client 的最小用法描述）
  3) 连接/断开时的行为说明（日志或注释）

完成后停止。
```

验收点：

* WS 能连接并保持
* 服务端能向订阅者推送新 event

---

## Stage 4：WS 收消息 chat.send -> 写 event_logs chat.message -> 广播（后端 chat echo）

**复制给 Cursor：**

```text
实现 WS 收消息（最小 chat echo）：

前端将发送：
{ "type": "chat.send", "payload": { "text": "...", "client_msg_id": "...", "idempotency_key": "..." } }

后端收到后：
1) 写 event_logs：type="chat.message"，payload.role="user"
2) 写 event_logs：type="chat.message"，payload.role="assistant"，text 为 mock 回复（例如 "收到：xxx（mock）"）
3) 两条事件都必须广播给订阅者

幂等要求（MVP 最小）：
- 使用 idempotency_key 防止重复发送导致重复写入
- 优先复用 user_actions（或新增轻量表/字段），至少保证：
  同 workflow_id + idempotency_key 不会重复生成这两条 chat.message

要求：
- 仍然必须遵守：先落库再广播
- 完成后输出：
  1) 修改/新增文件列表
  2) WS 消息样例与期望收到的两条 event（含 seq 递增）
  3) 幂等实现说明（唯一约束/查询逻辑）

完成后停止。
```

验收点：

* chat.send 能产生两条 chat.message（user+assistant）
* 重复 idempotency_key 不会重复落库

---

## Stage 5：事件写入统一化与复用（清理重复逻辑）

**复制给 Cursor：**

```text
对前面实现进行一次“小范围整理”，目标是统一事件写入路径，避免散落多处重复逻辑：

实现内容：
- 提供一个统一函数/类：append_event(workflow_id, type, payload) -> event(envelope)
  - 内部负责生成 seq、写 event_logs、返回 envelope
- 广播应在 append_event 成功 commit 后触发（可由外部调用 broadcaster）
- 确保现有路由（POST /workflows、WS chat.send）都通过该统一入口写 event

要求：
- 不要做大重构；只允许小范围改动让写 event 更一致
- 完成后输出：
  1) 修改/新增文件列表
  2) 你统一后的调用路径说明（从路由到写库到广播）
  3) 回归测试步骤（curl + ws）

完成后停止。
```

验收点：

* 所有事件都由统一入口写入
* 功能不回退

---

## Stage 6：开发环境 mock 事件生成（验证非 chat 事件流）

**复制给 Cursor：**

```text
增加一个仅开发环境启用的 mock 事件发生器，用于验证事件流：

方式二选一（你自行选择更合适的）：
A) 创建 workflow 后后台异步写入一串事件（stage.started/progress/completed）
B) 新增一个测试 endpoint：POST /workflows/{id}/mock-events 触发写入

事件序列建议：
- stage.started {stage:"REF_PROCESS"}
- stage.progress {stage:"REF_PROCESS", percent:10}
- stage.progress {stage:"REF_PROCESS", percent:50}
- stage.completed {stage:"REF_PROCESS"}

要求：
- mock 必须可开关（例如 ENV=DEV 才启用）
- 所有事件必须写入 event_logs 并广播
- 完成后输出：
  1) 修改/新增文件列表
  2) 如何触发 mock
  3) 期望收到的事件序列与 seq 递增说明

完成后停止。
```

验收点：

* 能触发非 chat 事件写入与广播
* event_logs 可回放这些事件

---

## Stage 7（可选）：后端手动测试文档

**复制给 Cursor：**

```text
请新增 docs/ws-chat-backend-test.md，包含：
- 后端启动步骤（含环境变量）
- POST /workflows 的 curl 示例
- GET /events 的 curl 示例（after_seq 测试）
- websocat/ws 客户端订阅与发送 chat.send 的示例
- mock-events 的触发与验证
- 常见问题排查（seq 不递增、广播不触发、WS 连接被关闭）

只新增文档，不改代码。完成后停止。
```

---

# 快速 Review 清单（你每阶段都检查）

* 是否保持 envelope 字段名一致
* 是否严格先落库再广播（尤其 WS 收消息时）
* seq 是否同 workflow 递增且可回放
* 是否出现不必要的 core 重构（出现就中断）
* 幂等是否真的生效（workflow_id + idempotency_key 唯一）

