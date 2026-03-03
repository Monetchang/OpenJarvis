# Action 协议规范（长期工程化版）

版本：v1  
适用范围：前端 Web 客户端 + Python 后端 orchestration-core  
目标：统一所有“用户触发动作”的输入协议，实现幂等、安全重试、可审计、可回放。

---

# 1. 设计原则

1. 所有用户触发操作统一为 Action
2. 幂等只依赖 idempotency_key（数据库唯一约束）
3. 状态合法性由状态机控制（不参与幂等）
4. 所有业务进度必须通过 event_logs 推送
5. 控制类响应（ack）与业务事件（event）分离

---

# 2. Action 消息结构（前端 → 服务端）

统一消息格式：

```json
{
  "type": "action.dispatch",
  "payload": {
    "action": "workflow.start",
    "input": {}
  },
  "meta": {
    "idempotency_key": "uuid",
    "client_action_id": "uuid",
    "client_ts_ms": 1700000000000,
    "source": "web",
    "schema_version": 1
  }
}
````

## 字段说明

| 字段               | 必填 | 说明              |
| ---------------- | -- | --------------- |
| action           | 是  | 动作名称            |
| input            | 是  | 动作参数            |
| idempotency_key  | 是  | 幂等键（同一用户意图必须固定） |
| client_action_id | 否  | 前端追踪用           |
| client_ts_ms     | 否  | 客户端时间戳          |
| schema_version   | 否  | 协议版本            |

---

# 3. ACK 响应协议（服务端 → 前端）

服务端收到 action.dispatch 后必须立即回一条 ack：

```json
{
  "workflow_id": "uuid",
  "seq": 10,
  "type": "action.ack",
  "payload": {
    "action": "workflow.start",
    "idempotency_key": "uuid",
    "status": "ACCEPTED",
    "action_id": "server_action_uuid",
    "reason": null
  },
  "created_at": "..."
}
```

## status 枚举

* ACCEPTED
* DUPLICATE
* REJECTED
* FAILED

---

# 4. 幂等规则（强约束）

数据库必须存在唯一约束：

```
UNIQUE(workflow_id, idempotency_key)
```

处理流程：

1. 状态门禁（合法性判断）
2. 尝试插入 action 记录
3. 冲突 → DUPLICATE
4. 成功 → ACCEPTED 并触发执行

---

# 5. 状态门禁（示例）

| workflow.status | 允许 workflow.start |
| --------------- | ----------------- |
| CREATED         | 是                 |
| CONFIGURED      | 是                 |
| WAITING_USER    | 是（视业务）            |
| RUNNING         | 否                 |
| COMPLETED       | 否                 |

---

# 6. Action 列表示例

* workflow.start
* workflow.update_config
* workflow.cancel
* outline.confirm
* section.rerun

---

# 7. 事件规范

业务事件仍使用：

```json
{
  "workflow_id": "...",
  "seq": 123,
  "type": "graph.started",
  "payload": {},
  "created_at": "..."
}
```

推荐所有事件 payload 增加：

* action_id
* idempotency_key

---

# 8. 枚举定义（单一事实来源）

## 写作风格

* 专业报告
* 博客随笔
* 营销文案
* 技术教程
* 新闻资讯

## 目标人群

* 技术从业者
* 普通消费者
* 学生群体
* 企业管理者
* 创业者

---

# 9. 调试建议

* Chrome → Network → WS → Frames 查看 action.dispatch 与 action.ack
* 重发相同 idempotency_key 应返回 DUPLICATE
* event_logs seq 必须单调递增