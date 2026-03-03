# Action 协议改造任务（分阶段执行）

⚠️ 每个阶段完成后必须停止并输出：

- 修改文件列表
- 手动验证步骤
- 预期事件序列

---

# Stage 1：服务端支持 action.dispatch（不改现有行为）

目标：

- 解析 action.dispatch
- 返回 action.ack
- 仍保留 chat.send 与 workflow.start 兼容

验收：

- 发送 action.dispatch(workflow.start) 能收到 action.ack(status=ACCEPTED)

---

# Stage 2：接入幂等约束

目标：

- 新增 user_actions 表或扩展现有表
- 添加 UNIQUE(workflow_id, idempotency_key)
- 重发相同 idempotency_key 返回 DUPLICATE

验收：

- 同 key 发送两次，第二次返回 DUPLICATE
- 不会触发两次 graph.started

---

# Stage 3：替换 workflow.start 为 action.dispatch

目标：

- 前端开始生成改为 action.dispatch
- 服务端内部统一转发到 workflow.start 处理逻辑

验收：

- 旧 workflow.start 仍可用（兼容层）
- 新协议成功触发 rungraph

---

# Stage 4：为 outline.confirm / section.rerun 接入协议

目标：

- 所有用户动作统一 action.dispatch
- 不再新增裸 type

---

# Stage 5：移除兼容层（可选）

在确认所有客户端升级后：

- 下线裸 workflow.start
- 强制使用 action.dispatch

---
