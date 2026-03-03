```markdown
# WebSocket 事件流 MVP（后端实现文档）

版本：v1.0  
适用范围：Python 后端（FastAPI + orchestration-core）  
不包含：前端实现（前端在独立项目中实现）

---

# 一、目标

在现有 orchestration-core 基础上，实现一个稳定、可扩展的：

- ✅ WebSocket 实时事件推送
- ✅ 事件持久化（event_logs）
- ✅ HTTP 断线补偿拉取
- ✅ 后端最小 chat echo 流程（用于验证链路）
- ✅ 可扩展的事件广播机制

本阶段目标是打通：

> Workflow 创建 → 事件写入 → WebSocket 推送 → HTTP 补偿

不涉及：
- Outline 编辑
- WAITING_USER 逻辑
- LLM 调用
- 真实业务 handler

---

# 二、设计原则

## 2.1 事件优先持久化

所有事件必须遵循顺序：

```

生成事件 → 写入 event_logs → commit → 广播

```

严禁：

```

广播成功后再写库

````

原因：
- 必须支持断线重连补偿
- 必须支持审计与回放

---

## 2.2 统一事件 Envelope

所有事件结构必须统一：

```json
{
  "workflow_id": "uuid",
  "seq": 123,
  "type": "string",
  "payload": {},
  "created_at": "ISO8601"
}
````

字段约束：

| 字段          | 说明               |
| ----------- | ---------------- |
| workflow_id | 所属 workflow      |
| seq         | 单 workflow 内严格递增 |
| type        | 事件类型（字符串，可扩展）    |
| payload     | 业务内容             |
| created_at  | 生成时间             |

---

## 2.3 单一事件写入入口

必须提供统一方法：

```
append_event(workflow_id, type, payload) -> event_envelope
```

该方法负责：

* 生成 seq
* 写入 event_logs
* 返回完整 envelope

广播由外层调用。

---

# 三、功能实现范围

---

# 1️⃣ 创建 Workflow

## 路由

```
POST /workflows
```

## 行为

* 创建 workflows 记录
* 写入一条事件：

```
type = "workflow.created"
payload = {}
```

* 返回：

```json
{
  "workflow_id": "uuid"
}
```

---

# 2️⃣ 事件补偿接口

## 路由

```
GET /workflows/{workflow_id}/events?after_seq=0&limit=200
```

## 参数

| 参数        | 默认  | 说明                  |
| --------- | --- | ------------------- |
| after_seq | 0   | 只返回 seq > after_seq |
| limit     | 200 | 最大 200              |

## 行为

* 查询 event_logs
* 条件：

  * workflow_id
  * seq > after_seq
  * 升序排序
  * limit <= 200

返回：

```json
{
  "events": [ ... ],
  "last_seq": 123
}
```

---

# 3️⃣ WebSocket 订阅

## 路由

```
WS /ws/workflows/{workflow_id}
```

---

## 连接逻辑

1. 校验 workflow 是否存在
2. 加入订阅池：

```
subscribers[workflow_id].add(connection)
```

3. 连接断开时移除订阅

---

## 事件广播机制

实现：

```
EventBroadcaster
```

结构：

```
Dict[workflow_id, Set[WebSocket]]
```

功能：

```
broadcast(event_envelope)
```

广播规则：

* 广播失败不能影响 DB
* 对异常连接立即移除

---

# 4️⃣ WebSocket 收消息（最小 Chat Echo）

用于验证链路。

---

## 前端发送格式

```json
{
  "type": "chat.send",
  "payload": {
    "text": "用户输入",
    "client_msg_id": "uuid",
    "idempotency_key": "uuid"
  }
}
```

---

## 后端处理逻辑

1. 幂等校验（workflow_id + idempotency_key）
2. 写入事件：

```
type = "chat.message"
payload = { role: "user", text: "..." }
```

3. 写入事件：

```
type = "chat.message"
payload = { role: "assistant", text: "收到：xxx（mock）" }
```

4. 两条事件均广播

---

## 幂等要求（MVP）

至少保证：

```
同 workflow_id + idempotency_key 不重复生成消息
```

推荐方式：

* 使用 user_actions 表
* 或单独建立 idempotency 记录

---

# 5️⃣ Mock 进度事件（开发环境）

用于验证非 chat 事件流。

---

## 可选实现方式

方式 A：创建 workflow 后自动触发
方式 B：新增测试接口：

```
POST /workflows/{id}/mock-events
```

---

## 模拟事件序列

```
stage.started
stage.progress (10%)
stage.progress (50%)
stage.progress (100%)
stage.completed
```

---

# 四、事件类型（本阶段最小集合）

| type             | 说明          |
| ---------------- | ----------- |
| workflow.created | workflow 创建 |
| chat.message     | 聊天消息        |
| stage.started    | 阶段开始（mock）  |
| stage.progress   | 阶段进度（mock）  |
| stage.completed  | 阶段结束（mock）  |

---

# 五、并发与幂等

## 5.1 seq 生成

* 必须保证：

  ```
  同 workflow 内 seq 单调递增
  ```
* 推荐：

  * 在事务内查询 max(seq) + 1
  * 或使用单独 sequence 表

---

## 5.2 幂等

* chat.send 必须支持 idempotency_key
* 重复提交不产生重复 event

---

# 六、错误处理

| 场景                    | 行为   |
| --------------------- | ---- |
| workflow 不存在          | 404  |
| after_seq 非法          | 400  |
| WebSocket 无效 workflow | 关闭连接 |
| DB 写入失败               | 不广播  |

---

# 七、验收标准

必须满足：

* [ ] 创建 workflow 后 event_logs 出现 workflow.created
* [ ] GET /events 能补偿历史
* [ ] WS 能接收实时事件
* [ ] chat.send 能产生两条 chat.message
* [ ] idempotency_key 生效
* [ ] mock 事件可广播
* [ ] 重启服务后 GET /events 仍可回放历史

---

# 八、本阶段完成后系统能力

你将拥有：

* 可持久化的事件流
* 可实时推送的 WebSocket 通道
* 可补偿的断线机制
* 可扩展的事件系统

这将成为：

> 所有未来 AI 工作流的实时交互基础设施

---

# 九、下一阶段（不在本文档实现）

* Outline WAITING_USER 阶段
* 用户操作事件推进 workflow
* 单节重跑
* Citation 校验
* 并行 stage 执行
