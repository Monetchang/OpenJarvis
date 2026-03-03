# UCreativity 后端 API 接口文档

## 文档说明

本文档详细描述了 UCreativity 智能写作工作台实际实现的后端 API 接口。

**基础信息：**
- API Base URL: `/api/v1`
- 数据格式: `application/json`
- 字符编码: `UTF-8`
- 服务端口: `12135`

**统一响应格式：**

成功响应：
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

错误响应：
```json
{
  "code": 错误码,
  "message": "错误描述",
  "data": null
}
```

**通用错误码：**
- `0`: 成功
- `400`: 请求参数错误
- `401`: 未授权
- `403`: 禁止访问
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 一、用户模块

**说明：** 以下接口供后端实现，前端已按此约定调用（邮箱绑定入口在注册弹窗）。当前可为「无登录态、仅邮箱绑定」的简化方案：用户只需完成一次邮箱+邀请码绑定，即可用该邮箱接收每日推送；如需后续扩展为 Token 登录、多设备同步，可在此基础上增加 1.2 / 1.3 等接口。

### 模块功能
- 邮箱注册/绑定：提交邮箱与邀请码，绑定成功后该邮箱用于接收每日推送
- （可选）获取当前用户/绑定状态：用于校验或恢复「已绑定」状态
- （可选）登出/解绑：清除服务端绑定关系（若采用无登录态方案可暂不实现）

### 1.1 邮箱注册/绑定（订阅每日推送）

**接口说明：** 用户提交邮箱与邀请码，校验通过后将该邮箱记为「已绑定」，并用于后续每日推送的接收。同一邮箱重复绑定可视为更新绑定（幂等）或返回「已绑定」提示，由后端约定。

**请求方法：** `POST`

**请求路径：** `/api/v1/subscribe/email`

**请求头：**
```
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| email | string | 是 | 用户邮箱，需符合邮箱格式 |
| inviteCode | string | 是 | 邀请码，后端校验合法性（如：DEMO2024、TEST2024 等） |

**请求示例：**
```json
{
  "email": "user@example.com",
  "inviteCode": "DEMO2024"
}
```

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否绑定成功 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "绑定成功",
  "data": {
    "success": true
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 400 | 邀请码错误 | inviteCode 不合法或已失效 |
| 400 | 邮箱格式不正确 | email 格式校验失败 |
| 400 | 该邮箱已被绑定 | 业务上不允许重复绑定时可返回 |
| 500 | 绑定失败 | 服务器内部错误 |

---

### 1.2 获取当前用户/绑定状态（可选）

**接口说明：** 用于校验当前请求是否已绑定邮箱（如通过 Cookie / Token 识别用户），或供前端恢复「已绑定」状态。若无登录态，可返回未绑定或由前端仅依赖本地存储；若后续接入 Token，可在此返回邮箱及基本信息。

**请求方法：** `GET`

**请求路径：** `/api/v1/user/me`

**请求头：**
```
Content-Type: application/json
（若采用 Token 认证，可补充：Authorization: Bearer <token>）
```

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| email | string \| null | 已绑定邮箱，未绑定时为 null |
| isEmailBound | boolean | 是否已绑定邮箱 |

**成功响应示例（已绑定）：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "email": "user@example.com",
    "isEmailBound": true
  }
}
```

**成功响应示例（未绑定）：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "email": null,
    "isEmailBound": false
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 401 | 未授权 | 若采用 Token 且未携带或已失效 |

---

### 1.3 解绑邮箱 / 登出（可选）

**接口说明：** 解除当前用户与邮箱的绑定关系（或登出），后续每日推送不再向该邮箱发送。无登录态方案下可暂不实现，或仅做「解绑」语义。

**请求方法：** `POST`

**请求路径：** `/api/v1/user/unbind`

**请求头：**
```
Content-Type: application/json
（若采用 Token 认证，可补充：Authorization: Bearer <token>）
```

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否解绑成功 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "解绑成功",
  "data": {
    "success": true
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 401 | 未授权 | 若采用 Token 且未携带或已失效 |
| 404 | 未绑定邮箱 | 当前无绑定关系可解除 |

---

### 1.4 邀请码说明（供后端实现参考）

当前前端已知的测试邀请码示例（可仅后端配置，不必与前端强一致）：
- `DEMO2024` — 开发/演示环境使用
- `TEST2024` — 自动化测试使用

邀请码的校验规则、有效期、次数限制等由后端统一实现。

---

## 二、RSS 订阅源管理模块

### 模块功能
- 获取订阅源列表
- 添加 RSS 订阅源
- 修改订阅源配置
- 删除订阅源
- 手动触发 RSS 抓取
- 切换订阅源信任状态（信任源文章跳过分类过滤）

### 2.1 获取订阅源列表

**接口说明：** 获取所有活跃的 RSS 订阅源

**请求方法：** `GET`

**请求路径：** `/api/v1/feed/list`

**请求头：**
```
Content-Type: application/json
```

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| feeds | array | 订阅源列表 |
| feeds[].id | string | 订阅源ID |
| feeds[].name | string | 订阅源名称 |
| feeds[].url | string | RSS URL |
| feeds[].pushCount | number | 每次推送数量 |
| feeds[].isTrusted | boolean | **[新增]** 是否为信任源 |
| feeds[].createdAt | string | 创建时间（ISO 8601格式） |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "feeds": [
      {
        "id": "feed_001",
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed",
        "pushCount": 10,
        "isTrusted": false,
        "createdAt": "2024-01-01T00:00:00"
      }
    ]
  }
}
```

### 2.2 添加订阅源

**接口说明：** 添加新的 RSS 订阅源

**请求方法：** `POST`

**请求路径：** `/api/v1/feed/create`

**请求头：**
```
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 订阅源名称 |
| url | string | 是 | RSS URL |
| pushCount | number | 是 | 每次推送数量（1-50） |
| isTrusted | boolean | 否 | **[新增]** 是否设为信任源（默认 false） |

**请求示例：**
```json
{
  "name": "Hacker News",
  "url": "https://news.ycombinator.com/rss",
  "pushCount": 15,
  "isTrusted": false
}
```

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| id | string | 订阅源ID |
| name | string | 订阅源名称 |
| url | string | RSS URL |
| pushCount | number | 推送数量 |
| isTrusted | boolean | **[新增]** 是否为信任源 |
| createdAt | string | 创建时间 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "添加成功",
  "data": {
    "id": "feed_a1b2c3d4",
    "name": "Hacker News",
    "url": "https://news.ycombinator.com/rss",
    "pushCount": 15,
    "isTrusted": false,
    "createdAt": "2024-02-14T10:30:00"
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 400 | RSS URL 格式不正确 | URL格式验证失败 |
| 400 | 无法访问该RSS源 | RSS源无法访问或解析失败 |
| 400 | 该订阅源已存在 | 相同URL的订阅源已存在 |

### 2.3 修改订阅源

**接口说明：** 修改已有订阅源的配置

**请求方法：** `PUT`

**请求路径：** `/api/v1/feed/update/{feedId}`

**请求头：**
```
Content-Type: application/json
```

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| feedId | string | 订阅源ID |

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 否 | 订阅源名称 |
| url | string | 否 | RSS URL |
| pushCount | number | 否 | 推送数量 |
| isTrusted | boolean | 否 | **[新增]** 是否设为信任源 |

**请求示例：**
```json
{
  "pushCount": 20,
  "isTrusted": true
}
```

**响应参数：**

返回更新后的订阅源完整信息（格式同 2.2，含 `isTrusted`）

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 订阅源不存在 | 指定的feedId不存在 |

### 2.4 删除订阅源

**接口说明：** 删除指定的订阅源（软删除）

**请求方法：** `DELETE`

**请求路径：** `/api/v1/feed/delete/{feedId}`

**请求头：**
```
Content-Type: application/json
```

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| feedId | string | 订阅源ID |

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否删除成功 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "删除成功",
  "data": {
    "success": true
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 订阅源不存在 | 指定的feedId不存在 |

### 2.5 手动触发 RSS 抓取

**接口说明：** 立即触发所有活跃订阅源的 RSS 抓取，无需等待定时任务。

**请求方法：** `POST`

**请求路径：** `/api/v1/feed/fetch`

**请求头：** 无

**请求参数：** 无

**成功响应示例：**
```json
{
  "code": 0,
  "message": "抓取完成",
  "data": {}
}
```

### 2.6 切换信任源状态 🆕

**接口说明：** 切换指定订阅源的信任状态（每次调用取反）。被标记为信任源的订阅源，其文章在两阶段过滤管道中直接保留，不受分类关键词匹配限制。

**请求方法：** `PUT`

**请求路径：** `/api/v1/feed/trust/{feedId}`

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| feedId | string | 订阅源ID |

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| id | string | 订阅源ID |
| isTrusted | boolean | 切换后的信任状态 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "已设为信任源",
  "data": {
    "id": "feed_a1b2c3d4",
    "isTrusted": true
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 订阅源不存在 | 指定的feedId不存在 |

---

## 三、全局配置管理模块

### 模块功能

管理应用全局配置，包括 RSS 定时时间和 AI 翻译开关。所有 RSS 源共享这些全局配置。

### 3.1 获取全局配置

**接口说明：** 获取当前全局配置（RSS 定时时间和 AI 翻译开关）

**请求方法：** `GET`

**请求路径：** `/api/v1/config/global`

**请求头：** 无

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| rssSchedule | string | RSS 定时规则（cron表达式） |
| translationEnabled | boolean | 是否启用AI翻译 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "rssSchedule": "0 9 * * *",
    "translationEnabled": true
  }
}
```

### 3.2 更新全局配置

**接口说明：** 更新全局配置（RSS 定时时间和 AI 翻译开关）

**请求方法：** `PUT`

**请求路径：** `/api/v1/config/global`

**请求头：**
```
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| rssSchedule | string | 否 | RSS 定时规则（cron表达式，如：0 9 * * *） |
| translationEnabled | boolean | 否 | 是否启用AI翻译 |

**请求示例：**
```json
{
  "rssSchedule": "0 10 * * *",
  "translationEnabled": false
}
```

**响应参数：**

返回更新后的全局配置（格式同 3.1）

**成功响应示例：**
```json
{
  "code": 0,
  "message": "更新成功",
  "data": {
    "rssSchedule": "0 10 * * *",
    "translationEnabled": false
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 400 | cron 表达式格式错误 | cron表达式验证失败 |
| 500 | 更新配置失败 | 服务器内部错误 |

---

## 四、文章推送模块

### 模块功能
- 获取今日推送文章列表
- 获取历史推送文章
- 标记文章已读

### 3.1 获取今日推送

**接口说明：** 获取当天推送的文章列表，支持按关键领域和关键词过滤。采用两阶段管道过滤策略（v1.2 升级）。

**查询策略（按优先级）：**
1. 每个来源取 3 天内文章，再按各源 `push_count` 截取，最后按发布时间倒序合并

**过滤策略（两阶段管道）：** _(v1.2 更新，替代原三级降级策略)_

- **Phase 1 — 负向过滤**：对所有文章（包括信任源）应用负向关键词，命中则剔除
- **Phase 2 — 打分分桶**：
  - **普通源**：按 6 大分类规则（必须词全匹配 + 关键词打分）归入对应桶，每桶按得分降序取 TopN；未进任何分类的文章进「其他桶」保底取 2 条
  - **信任源**：跳过分类匹配，直接合入结果，不占分类名额
- **兜底**：Phase 1 全部被过滤时，返回原始列表（`filterTier=fallback`）

**6 大分类上限：**

| 分类 | 最多条数 |
|------|---------|
| AI模型架构与算法 | 3 |
| AI大模型技术 | 3 |
| AI应用与工具 | 5 |
| AI基础设施 | 2 |
| 机器学习前沿 | 2 |
| AI落地应用 | 2 |
| 其他（兜底） | 2 |

**请求方法：** `GET`

**请求路径：** `/api/v1/article/today`

**请求头：**
```
Content-Type: application/json
```

**请求参数（Query）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| domain_id | integer | 否 | 关键领域ID，按领域过滤 |
| keywords | string | 否 | 正向关键词，逗号分隔（如：AI,机器学习） |
| exclude_keywords | string | 否 | 负向关键词，逗号分隔（如：股价,融资） |
| apply_filter | boolean | 否 | 是否应用默认过滤规则（默认 true） |

**请求示例：**
```
GET /api/v1/article/today?domain_id=1&keywords=AI,机器学习&exclude_keywords=股价,融资
```

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| articles | array | 文章列表 |
| articles[].id | integer | 文章ID |
| articles[].title | string | 文章标题 |
| articles[].source | string | 来源（订阅源名称） |
| articles[].feedName | string | 订阅源名称 |
| articles[].summary | string | 文章摘要 |
| articles[].url | string | 原文链接 |
| articles[].publishedAt | string | 发布时间 |
| articles[].pushedAt | string | 推送时间 |
| articles[].isRead | boolean | 是否已读 |
| articles[].isNew | boolean | 是否为今日新增（首次抓取时间为今天） |
| total | integer | 返回文章总数 |
| filterTier | string | 过滤级别：`strict`=有分类命中或信任源；`soft`=仅负向过滤；`fallback`=负向过滤后无结果，返回全部；`none`=未过滤 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "articles": [
      {
        "id": 1234,
        "title": "AI 技术的未来发展趋势",
        "source": "TechCrunch",
        "feedName": "TechCrunch",
        "summary": "探讨人工智能在未来十年的发展方向...",
        "url": "https://techcrunch.com/article-1",
        "publishedAt": "2024-02-14T08:00:00",
        "pushedAt": "09:00",
        "isRead": false,
        "isNew": true
      }
    ],
    "total": 15,
    "usedFallback": false,
    "queryMethod": "first_crawl_time",
    "filterTier": "soft"
  }
}
```

### 3.2 今日推送诊断

**接口说明：** 诊断 `/today` 接口为什么没有返回文章，返回系统时间、各查询策略命中数、来源统计、过滤域配置等信息

**请求方法：** `GET`

**请求路径：** `/api/v1/article/today/debug`

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| systemTime | object | Python 系统时间信息 |
| queries | object | 各查询策略命中的文章数量 |
| queries.first_crawl_time_today | integer | first_crawl_time 匹配今日的数量 |
| queries.created_at_date_today | integer | created_at 匹配今日的数量 |
| queries.total_articles | integer | 数据库文章总数 |
| feeds | array | 各来源的文章统计 |
| feeds[].feedId | string | 来源ID |
| feeds[].feedName | string | 来源名称 |
| feeds[].totalArticles | integer | 总文章数 |
| feeds[].todayArticles | integer | 今日文章数 |
| filterDomains | array | 过滤域配置信息 |
| sampleArticles | array | 最新 5 篇文章样本 |

**请求示例：**
```
GET /api/v1/article/today/debug
```

### 3.3 获取历史推送

**接口说明：** 获取历史推送的文章列表，支持日期筛选和分页

**请求方法：** `GET`

**请求路径：** `/api/v1/article/history`

**请求头：**
```
Content-Type: application/json
```

**请求参数（Query）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| date | string | 否 | 指定日期（YYYY-MM-DD格式） |
| page | number | 否 | 页码（默认1） |
| pageSize | number | 否 | 每页数量（默认20，最大100） |
| domain_id | integer | 否 | 关键领域ID，按领域过滤 |
| keywords | string | 否 | 正向关键词，逗号分隔（如：AI,机器学习） |
| exclude_keywords | string | 否 | 负向关键词，逗号分隔（如：股价,融资） |

**请求示例：**
```
GET /api/v1/article/history?date=2024-02-14&page=1&pageSize=20
```

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| articles | array | 文章列表（格式同3.1） |
| total | number | 总数 |
| page | number | 当前页码 |
| pageSize | number | 每页数量 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "articles": [
      {
        "id": 1234,
        "title": "AI 技术的未来发展趋势",
        "source": "TechCrunch",
        "feedName": "TechCrunch",
        "summary": "探讨人工智能在未来十年的发展方向...",
        "url": "https://techcrunch.com/article-1",
        "publishedAt": "2024-02-14T08:00:00",
        "pushedAt": "2024-02-14T09:00:00",
        "isRead": false
      }
    ],
    "total": 150,
    "page": 1,
    "pageSize": 20
  }
}
```

### 3.4 标记文章已读

**接口说明：** 将指定文章标记为已读

**请求方法：** `POST`

**请求路径：** `/api/v1/article/mark-read/{articleId}`

**请求头：**
```
Content-Type: application/json
```

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| articleId | integer | 文章ID |

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否成功 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "标记成功",
  "data": {
    "success": true
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 文章不存在 | 指定的articleId不存在 |

---

## 五、文章过滤模块

### 模块功能
- 管理关键领域（如：AI模型架构、RAG技术等）
- 管理关键词规则（支持正则表达式、必须词、过滤词）
- 在文章查询时应用过滤规则

### 4.1 获取关键领域列表

**接口说明：** 获取所有关键领域列表

**请求方法：** `GET`

**请求路径：** `/api/v1/filter/domains`

**请求头：**
```
Content-Type: application/json
```

**请求参数（Query）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| enabled | boolean | 否 | 是否只返回启用的领域 |

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 领域ID |
| name | string | 领域名称 |
| description | string | 领域描述 |
| enabled | boolean | 是否启用 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

**成功响应示例：**
```json
[
  {
    "id": 1,
    "name": "AI模型架构与算法创新",
    "description": "AI模型架构与算法创新相关领域",
    "enabled": true,
    "created_at": "2024-02-14T00:00:00",
    "updated_at": "2024-02-14T00:00:00"
  }
]
```

### 4.2 创建关键领域

**接口说明：** 创建新的关键领域

**请求方法：** `POST`

**请求路径：** `/api/v1/filter/domains`

**请求头：**
```
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 领域名称（唯一） |
| description | string | 否 | 领域描述 |
| enabled | boolean | 否 | 是否启用（默认true） |

**请求示例：**
```json
{
  "name": "AI模型架构与算法创新",
  "description": "AI模型架构与算法创新相关领域",
  "enabled": true
}
```

**响应参数：**

返回创建后的领域完整信息（格式同 4.1）

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 400 | 领域名称已存在 | 指定的name已存在 |

### 4.3 更新关键领域

**接口说明：** 更新指定的关键领域

**请求方法：** `PUT`

**请求路径：** `/api/v1/filter/domains/{domainId}`

**请求头：**
```
Content-Type: application/json
```

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| domainId | integer | 领域ID |

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 否 | 领域名称 |
| description | string | 否 | 领域描述 |
| enabled | boolean | 否 | 是否启用 |

**请求示例：**
```json
{
  "name": "AI模型架构与算法创新（更新）",
  "description": "更新后的描述",
  "enabled": true
}
```

**响应参数：**

返回更新后的领域完整信息（格式同 4.1）

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 领域不存在 | 指定的domainId不存在 |
| 400 | 领域名称已存在 | 指定的name与其他领域冲突 |

### 4.4 删除关键领域

**接口说明：** 删除指定的关键领域（会级联删除该领域下的所有关键词）

**请求方法：** `DELETE`

**请求路径：** `/api/v1/filter/domains/{domainId}`

**请求头：**
```
Content-Type: application/json
```

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| domainId | integer | 领域ID |

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否删除成功 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "删除成功",
  "data": {
    "success": true
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 领域不存在 | 指定的domainId不存在 |

### 4.5 获取关键词列表

**接口说明：** 获取关键词规则列表，可按领域和类型筛选

**请求方法：** `GET`

**请求路径：** `/api/v1/filter/keywords`

**请求头：**
```
Content-Type: application/json
```

**请求参数（Query）：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| domain_id | integer | 否 | 领域ID，筛选指定领域的关键词 |
| keyword_type | string | 否 | 关键词类型：positive（正向）或 negative（负向） |

**请求示例：**
```
GET /api/v1/filter/keywords?domain_id=1&keyword_type=positive
```

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 关键词ID |
| domain_id | integer | 所属领域ID |
| keyword_type | string | 关键词类型（positive/negative） |
| keyword_text | string | 关键词文本 |
| is_regex | boolean | 是否为正则表达式 |
| is_required | boolean | 是否为必须词（+前缀） |
| alias | string | 别名 |
| priority | integer | 优先级 |
| max_results | integer | 限制数量（@N） |
| created_at | string | 创建时间 |

**成功响应示例：**
```json
[
  {
    "id": 1,
    "domain_id": 1,
    "keyword_type": "positive",
    "keyword_text": "/AI|人工智能|机器学习/",
    "is_regex": true,
    "is_required": false,
    "alias": "AI相关",
    "priority": 0,
    "max_results": null,
    "created_at": "2024-02-14T00:00:00"
  }
]
```

### 4.6 创建关键词

**接口说明：** 创建新的关键词规则

**请求方法：** `POST`

**请求路径：** `/api/v1/filter/keywords`

**请求头：**
```
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| domain_id | integer | 是 | 所属领域ID |
| keyword_type | string | 否 | 关键词类型：positive（正向）或 negative（负向/过滤词），默认 positive |
| keyword_text | string | 是 | 关键词文本（正则表达式需用 /.../ 包裹） |
| is_regex | boolean | 否 | 是否为正则表达式，默认 false |
| is_required | boolean | 否 | 是否为必须词（+前缀），默认 false |
| alias | string | 否 | 别名 |
| priority | integer | 否 | 优先级，默认 0 |
| max_results | integer | 否 | 限制该关键词组最多显示多少条（@N），默认 null（不限制） |

**请求示例：**
```json
{
  "domain_id": 1,
  "keyword_type": "positive",
  "keyword_text": "/AI|人工智能|机器学习/",
  "is_regex": true,
  "is_required": false,
  "alias": "AI相关",
  "priority": 0,
  "max_results": null
}
```

**关键词规则说明：**

1. **普通关键词**：直接匹配文本，如 `"keyword_text": "AI"`
2. **正则表达式**：用 `/.../` 包裹，如 `"keyword_text": "/AI|人工智能/"`，需设置 `is_regex: true`
3. **必须词（+前缀）**：所有必须词都要匹配才算匹配，设置 `is_required: true`
4. **过滤词（!前缀）**：匹配则排除该条文章，设置 `keyword_type: "negative"`
5. **限制数量（@N）**：设置 `max_results` 限制该词组最多显示多少条

**响应参数：**

返回创建后的关键词完整信息（格式同 4.5）

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 领域不存在 | 指定的domain_id不存在 |

### 4.7 删除关键词

**接口说明：** 删除指定的关键词

**请求方法：** `DELETE`

**请求路径：** `/api/v1/filter/keywords/{keywordId}`

**请求头：**
```
Content-Type: application/json
```

**路径参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| keywordId | integer | 关键词ID |

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否删除成功 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "删除成功",
  "data": {
    "success": true
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 关键词不存在 | 指定的keywordId不存在 |

---

## 六、AI 灵感选题模块

### 模块功能
- 基于订阅的文章，生成写作选题建议
- 从存储中获取当日选题；生成选题时先清除当日选题再重新生成并存储

### 4.0 获取当日选题

**接口说明：** 从存储中获取当日选题数据

**请求方法：** `GET`

**请求路径：** `/api/v1/ai/ideas`

**请求参数：** 无

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| ideas | array | 当日选题列表（无则为空数组） |
| ideas[].id | string | 选题ID（格式：idea_{数字ID}） |
| ideas[].title | string | 选题标题 |
| ideas[].relatedArticles | array | 相关文章列表 `[{title, source, url}]` |
| ideas[].reason | string | 推荐理由/描述 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "ideas": [
      {
        "id": "idea_123",
        "title": "如何利用 AI 提升开发效率",
        "relatedArticles": [{"title": "文章标题", "source": "来源", "url": "https://..."}],
        "reason": "结合最新 AI 工具和实际开发场景，对开发者有实用价值"
      }
    ]
  }
}
```

---

### 4.1 生成选题

**接口说明：** 先清除存储中当日选题数据，再根据文章内容生成写作选题并存储（默认5个）

**请求方法：** `POST`

**请求路径：** `/api/v1/ai/generate-ideas`

**请求头：**
```
Content-Type: application/json
```

**请求体：** 可选。不传或传空对象 `{}` 时，使用默认参数（基于最新 100 篇文章生成 5 个选题）。

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| articleIds | array[integer] | 否 | 基于指定文章生成（不传则基于最新100篇文章） |
| count | number | 否 | 生成数量，3-10，默认 5 |

**请求示例：**
```json
{}
```
或
```json
{
  "articleIds": [1234, 5678],
  "count": 5
}
```

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| ideas | array | 选题列表 |
| ideas[].id | string | 选题ID（格式：idea_{数字ID}） |
| ideas[].title | string | 选题标题 |
| ideas[].relatedArticles | array | 相关文章列表，格式 `[{title, source, url}]`，已持久化供 generate-article 使用 |
| ideas[].reason | string | 推荐理由/描述 |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "生成成功",
  "data": {
    "ideas": [
      {
        "id": "idea_123",
        "title": "如何利用 AI 提升开发效率",
        "relatedArticles": [{"title": "文章标题", "source": "来源", "url": "https://..."}],
        "reason": "结合最新 AI 工具和实际开发场景，对开发者有实用价值"
      }
    ]
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 400 | 没有足够的文章数据生成选题 | 数据库中没有文章数据 |
| 500 | AI服务暂时不可用 | AI生成失败 |

**行为说明：** 每次调用会先删除当日（按服务器日期）已存储的选题，再基于文章生成新选题并写入存储。

---

## 七、AI 文章创作模块

### 模块功能
- 根据选题、写作风格、目标人群生成完整文章

### 5.1 生成文章

**接口说明：** AI 生成 Markdown 格式的完整文章

**请求方法：** `POST`

**请求路径：** `/api/v1/ai/generate-article`

**请求头：**
```
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| ideaId | string | 是 | 选题ID（格式：idea_{id}），用于获取选题关联的参考文章并融入生成内容 |
| ideaTitle | string | 是 | 选题标题 |
| style | string | 是 | 写作风格（专业报告/博客随笔/营销文案/技术教程/新闻资讯） |
| audience | string | 是 | 目标人群（技术从业者/普通消费者/学生群体/企业管理者/创业者） |
| length | string | 否 | 文章长度（short/medium/long，默认medium） |
| language | string | 否 | 输出语言（zh-CN/en-US，默认zh-CN） |

**请求示例：**
```json
{
  "ideaId": "idea_123",
  "ideaTitle": "如何利用 AI 提升开发效率",
  "style": "技术教程",
  "audience": "技术从业者",
  "length": "medium",
  "language": "zh-CN"
}
```

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| articleId | string | 文章ID（格式：gen_article_{时间戳}） |
| title | string | 文章标题 |
| content | string | 文章内容（Markdown格式） |
| wordCount | number | 字数统计 |
| generatedAt | string | 生成时间（ISO 8601格式） |

**成功响应示例：**
```json
{
  "code": 0,
  "message": "生成成功",
  "data": {
    "articleId": "gen_article_20240214103000",
    "title": "如何利用 AI 提升开发效率",
    "content": "# 如何利用 AI 提升开发效率\n\n## 引言\n\n这是一篇关于...",
    "wordCount": 2500,
    "generatedAt": "2024-02-14T10:30:00"
  }
}
```

**错误响应：**

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 500 | AI未返回响应 | AI服务未返回内容 |
| 500 | 生成失败: {错误详情} | AI生成过程出错 |

**行为说明：** `ideaId` 需与 `generate-ideas` 返回的 `ideas[].id` 一致。后端会根据 `ideaId` 查询该选题的参考文章（`topic_references`），并将参考资料融入生成 prompt，提升文章质量。前端无需额外传参。

### 5.2 保存草稿

**⚠️ 当前版本暂未实现此功能，为预留接口。**

---

## 八、工作流编排模块

**说明：** 多阶段工作流（Workflow）的创建、推进、人在回路确认、事件回放与产物查询。用于内容生产流水线等可暂停/恢复、产物版本化的场景。

**基础路径：** `/api/v1/orchestration`

### 8.1 创建工作流

**请求方法：** `POST`

**请求路径：** `/api/v1/orchestration/workflows`

**请求体：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| conversation_id | string (UUID) | 否 | 对话 ID，可选 |
| input_params | object | 否 | 工作流输入参数，如 ideaTitle、style 等 |

**成功响应：** `200`

| 参数名 | 类型 | 说明 |
|--------|------|------|
| workflow_id | string | 工作流 ID |
| stage_run_id | string | 首个阶段执行 ID |

---

### 8.2 处理待执行阶段

**请求方法：** `POST`

**请求路径：** `/api/v1/orchestration/workflows/{workflow_id}/process`

**路径参数：** `workflow_id` — 工作流 UUID

**成功响应：** `200`

| 参数名 | 类型 | 说明 |
|--------|------|------|
| processed | number | 本次执行的 stage_run 数量 |
| status | string | 执行后工作流状态：CREATED / RUNNING / WAITING_USER / COMPLETED / FAILED |

**错误：** `404` — workflow not found

---

### 8.3 提交用户操作（人在回路）

**请求方法：** `POST`

**请求路径：** `/api/v1/orchestration/workflows/{workflow_id}/user-actions`

**路径参数：** `workflow_id` — 工作流 UUID

**请求体：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type | string | 是 | 操作类型，如 confirm、edit_outline、retry_stage、cancel |
| payload | object | 否 | 操作载荷（如编辑后的大纲） |
| idempotency_key | string | 是 | 幂等键，防重复提交 |

**成功响应：** `200`

| 参数名 | 类型 | 说明 |
|--------|------|------|
| action_id | string | 用户操作 ID |
| status | string | RECEIVED / APPLIED |

同一 `idempotency_key` 重复请求返回已有记录，不重复执行。

**错误：** `404` — workflow not found；`400` — workflow not waiting for user action

---

### 8.4 获取工作流事件（断线补偿/回放）

**请求方法：** `GET`

**请求路径：** `/api/v1/orchestration/workflows/{workflow_id}/events`

**路径参数：** `workflow_id` — 工作流 UUID

**查询参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| after_seq | number | 否 | 仅返回 seq 大于该值的事件，默认 0 |
| limit | number | 否 | 最多返回条数，默认 200 |

**成功响应：** `200`

| 参数名 | 类型 | 说明 |
|--------|------|------|
| workflow_id | string | 工作流 ID |
| events | array | 事件列表，每项含 seq、type、payload、created_at |

**错误：** `404` — workflow not found

---

### 8.5 获取工作流产物列表

**请求方法：** `GET`

**请求路径：** `/api/v1/orchestration/workflows/{workflow_id}/artifacts`

**路径参数：** `workflow_id` — 工作流 UUID

**查询参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type | string | 否 | 按产物类型筛选 |
| scope | string | 否 | 按 scope_key 筛选 |

**成功响应：** `200`

| 参数名 | 类型 | 说明 |
|--------|------|------|
| workflow_id | string | 工作流 ID |
| artifacts | array | 产物列表，每项含 id、type、version、scope_key、title、content_preview、content_json、created_by |

**错误：** `404` — workflow not found

---

### 8.6 获取工作流详情

**请求方法：** `GET`

**请求路径：** `/api/v1/orchestration/workflows/{workflow_id}`

**路径参数：** `workflow_id` — 工作流 UUID

**成功响应：** `200`

| 参数名 | 类型 | 说明 |
|--------|------|------|
| workflow_id | string | 工作流 ID |
| status | string | CREATED / RUNNING / WAITING_USER / FAILED / COMPLETED / CANCELED |
| current_stage | string | 当前阶段 |
| input_params | object | 输入参数 |
| error_message | string \| null | 失败时的错误信息 |
| created_at | string (ISO8601) \| null | 创建时间 |

**错误：** `404` — workflow not found

---

### 8.7 重跑某阶段

**请求方法：** `POST`

**请求路径：** `/api/v1/orchestration/workflows/{workflow_id}/rerun`

**路径参数：** `workflow_id` — 工作流 UUID

**请求体：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| stage | string | 是 | 要重跑的阶段名 |
| scope_key | string | 否 | 细粒度范围，如 section_id |

**成功响应：** `200`

| 参数名 | 类型 | 说明 |
|--------|------|------|
| stage_run_id | string | 新阶段执行 ID |
| stage | string | 阶段名 |
| attempt | number | 该阶段第几次执行 |

**错误：** `404` — workflow not found

---

### 8.8 工作流事件类型说明（含 LLM Thinking）

**说明：** 通过 WebSocket `ws://host/ws/workflows/{workflow_id}` 或 `GET /api/v1/workflows/{workflow_id}/events` 获取的事件流中，`type` 与 `payload` 结构如下。前端需根据 `type` 做对应渲染。

| type | 说明 | payload 结构 |
|------|------|--------------|
| `stage.scheduled` | 阶段已调度 | `stage_run_id`, `stage`, `attempt` |
| `stage.started` | 阶段开始执行 | `stage_run_id`, `stage` |
| `stage.completed` | 阶段完成 | `stage_run_id`, `stage` |
| `stage.waiting_user` | 等待用户操作 | `action_required`, `payload` |
| `artifact.created` | 产物创建 | `artifact_id`, `type`, `version` |
| `node.started` | 图节点开始 | `graph`, `node` |
| `node.completed` | 图节点完成 | `graph`, `node` |
| **`llm.thinking`** | **LLM 思维链内容** | 见下表 |

**`llm.thinking` 事件 payload：**

| 字段 | 类型 | 说明 |
|------|------|------|
| node | string | 产生 thinking 的节点：`propose_outline`（生成大纲）或 `write_sections`（生成小节） |
| section_id | string | 仅当 `node=write_sections` 时存在，表示当前撰写的小节 ID |
| **chunk** | string | **流式输出**：每次收到即追加到当前 thinking 展示区（仅 WebSocket 实时推送，不落库） |
| **thinking** | string | **完整内容**：一次性返回的完整 thinking（落库，用于断线回放） |

**流式输出：** 后端通过 WebSocket 实时推送 `payload.chunk`，前端逐块追加渲染；完成后会再推送一条 `payload.thinking` 的完整事件（含 seq，可回放）。

**流式 chunk 示例：**

```json
{
  "workflow_id": "uuid",
  "type": "llm.thinking",
  "payload": {
    "node": "propose_outline",
    "chunk": "首先，用户要求我作为专业的内容策划，"
  },
  "created_at": "2024-03-02T11:42:54.029Z"
}
```

**完整 thinking 示例：**

```json
{
  "workflow_id": "uuid",
  "seq": 15,
  "type": "llm.thinking",
  "payload": {
    "node": "propose_outline",
    "thinking": "首先，用户要求我作为专业的内容策划，根据给定的文章标题和参考资料，生成一篇博客的大纲..."
  },
  "created_at": "2024-03-02T11:42:54.029Z"
}
```

**前端改造建议：**

1. 在 WebSocket 或轮询 `GET /events` 的处理逻辑中，增加对 `type === "llm.thinking"` 的分支。
2. 若 `payload.chunk` 存在：流式追加到当前 node/section 的 thinking 展示区。
3. 若 `payload.thinking` 存在：一次性展示完整内容（或用于断线回放时替换）。
4. 根据 `payload.node` 决定展示位置：`propose_outline` 可在大纲生成阶段展示；`write_sections` 可结合 `section_id` 在对应小节写作时展示。
5. 将 thinking 以可折叠、只读区域渲染（如 `<details>` 或折叠面板），避免干扰主流程。
6. 使用 `deepseek/deepseek-reasoner` 等推理模型时才有 thinking 内容；`deepseek-chat` 等非推理模型该事件 `thinking` 为空，前端可忽略或隐藏该区域。
7. **流式 chunk 仅通过 WebSocket 实时推送**，不落库；`GET /events` 仅能回放含 `payload.thinking` 的完整事件。

---

## 九、认证与授权

**⚠️ 当前版本暂未实现用户认证功能。**

所有API接口当前无需认证即可访问，后续版本将添加 Token 认证机制。

---

## 十、数据模型补充说明

### 7.1 Cron 表达式格式

支持标准的 5 位 cron 表达式：`分 时 日 月 周`

示例：
- `0 9 * * *` - 每天上午 9:00
- `0 */6 * * *` - 每 6 小时
- `0 9,18 * * *` - 每天 9:00 和 18:00

### 7.2 文章长度定义

- `short`: 800-1500 字
- `medium`: 1500-3000 字
- `long`: 3000-5000 字

### 7.3 写作风格枚举值

- `专业报告`
- `博客随笔`
- `营销文案`
- `技术教程`
- `新闻资讯`

### 7.4 目标人群枚举值

- `技术从业者`
- `普通消费者`
- `学生群体`
- `企业管理者`
- `创业者`

---

## 十一、性能要求

### 8.1 响应时间

- 普通查询接口：< 500ms
- RSS 抓取相关：< 3s
- AI 生成选题：< 10s
- AI 生成文章：< 30s

### 8.2 并发要求

- 支持至少 100 并发用户
- AI 生成接口需要排队机制，避免资源耗尽

---

## 十二、安全要求

### 9.1 数据验证

- 所有用户输入必须进行验证和过滤
- 防止 SQL 注入、XSS 攻击
- RSS URL 需要验证合法性

### 9.2 API 限流

建议对以下接口进行限流：

- 注册接口：同一 IP 每天最多 10 次
- AI 生成选题：每用户每小时最多 10 次
- AI 生成文章：每用户每小时最多 5 次

### 9.3 内容审核

AI 生成的内容需要进行基础的内容安全审核，过滤敏感信息。

---

## 十三、开发优先级建议

**P0 (核心功能，优先开发)：**
1. 用户注册（1.1）
2. Token 认证机制（6.1）
3. RSS 订阅源管理（2.1-2.4）
4. 获取今日推送（3.1）
5. AI 生成文章（5.1）

**P1 (重要功能)：**
1. 获取历史推送（3.2）
2. 标记文章已读（3.3）
3. AI 生成选题（4.1）

**P2 (可选功能)：**
1. 保存草稿（5.2）
2. Token 刷新（6.2）

---

## 十四、测试数据建议

### 测试邀请码
- `DEMO2024` - 用于开发测试
- `TEST2024` - 用于自动化测试

### 测试 RSS 源
```
https://techcrunch.com/feed
https://news.ycombinator.com/rss
https://www.reddit.com/r/programming/.rss
```

---

## 附录：前端代码参考

前端 API 调用代码位置：
- `/src/services/api.ts` - API 方法定义
- `/src/services/request.ts` - axios 封装
- `/src/types/index.ts` - 类型定义

---

## 附录：文章过滤功能前端接入指南

### 功能概述

文章过滤功能允许用户通过**关键领域**和**关键词规则**来筛选文章，支持：
- 按关键领域过滤（如：AI模型架构、RAG技术等）
- 正向关键词匹配（包含指定关键词）
- 负向关键词过滤（排除指定关键词）
- 正则表达式匹配
- 必须词匹配（所有必须词都要匹配）
- 结果数量限制

### 使用场景

1. **设置页面**：管理关键领域和关键词规则
2. **文章列表页面**：应用过滤条件查看文章
3. **个性化推荐**：根据用户关注的领域自动过滤

### 前端实现步骤

#### 1. 获取关键领域列表

在设置页面加载时，获取所有可用的关键领域：

```typescript
// 获取所有启用的关键领域
const response = await fetch('/api/v1/filter/domains?enabled=true');
const domains = await response.json();

// 渲染领域选择器
domains.forEach(domain => {
  // 显示领域名称和描述
  // 允许用户选择/取消选择
});
```

#### 2. 管理关键词规则

为每个领域管理关键词规则：

```typescript
// 获取某个领域的关键词列表
const keywords = await fetch(`/api/v1/filter/keywords?domain_id=${domainId}`)
  .then(res => res.json());

// 创建新关键词
await fetch('/api/v1/filter/keywords', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    domain_id: 1,
    keyword_type: 'positive',  // 或 'negative'
    keyword_text: '/AI|人工智能|机器学习/',
    is_regex: true,
    is_required: false,
    alias: 'AI相关',
    priority: 0,
    max_results: null
  })
});
```

#### 3. 在文章列表应用过滤

在获取文章列表时，传递过滤参数：

```typescript
// 获取今日推送（按领域过滤）
const articles = await fetch(
  `/api/v1/article/today?domain_id=${selectedDomainId}`
).then(res => res.json());

// 获取历史推送（组合过滤）
const articles = await fetch(
  `/api/v1/article/history?domain_id=${domainId}&keywords=AI,机器学习&exclude_keywords=股价,融资&page=1&pageSize=20`
).then(res => res.json());
```

### 关键词规则配置说明

#### 规则类型

1. **普通关键词**
   ```json
   {
     "keyword_text": "AI",
     "is_regex": false
   }
   ```
   匹配包含 "AI" 的文章标题或摘要

2. **正则表达式**
   ```json
   {
     "keyword_text": "/AI|人工智能|机器学习/",
     "is_regex": true
   }
   ```
   匹配包含 "AI"、"人工智能" 或 "机器学习" 任一关键词

3. **必须词（+前缀）**
   ```json
   {
     "keyword_text": "AI",
     "is_required": true
   }
   ```
   所有标记为 `is_required: true` 的关键词都必须匹配

4. **过滤词（!前缀）**
   ```json
   {
     "keyword_type": "negative",
     "keyword_text": "股价"
   }
   ```
   匹配到该关键词的文章会被排除

5. **限制数量（@N）**
   ```json
   {
     "max_results": 10
   }
   ```
   该关键词组最多返回 10 条结果

### UI 设计建议

#### 设置页面布局

```
┌─────────────────────────────────────┐
│  文章过滤设置                        │
├─────────────────────────────────────┤
│                                     │
│  [关键领域管理]                      │
│  ┌───────────────────────────────┐  │
│  │ ☑ AI模型架构与算法创新        │  │
│  │   └─ 关键词规则 (5条)          │  │
│  │ ☑ RAG技术与知识库构建         │  │
│  │   └─ 关键词规则 (3条)          │  │
│  │ ☐ 具身智能与自动驾驶          │  │
│  └───────────────────────────────┘  │
│                                     │
│  [+ 添加新领域]                      │
│                                     │
└─────────────────────────────────────┘
```

#### 关键词规则编辑界面

```
┌─────────────────────────────────────┐
│  领域：AI模型架构与算法创新          │
├─────────────────────────────────────┤
│                                     │
│  正向关键词：                        │
│  ┌───────────────────────────────┐ │
│  │ /AI|人工智能|机器学习/ [正则]   │ │
│  │ [+必须] [别名: AI相关]          │ │
│  │ [删除]                          │ │
│  └───────────────────────────────┘ │
│                                     │
│  负向关键词（过滤词）：              │
│  ┌───────────────────────────────┐ │
│  │ 股价 [!过滤]                   │ │
│  │ [删除]                          │ │
│  └───────────────────────────────┘ │
│                                     │
│  [+ 添加关键词]                      │
│                                     │
└─────────────────────────────────────┘
```

### 前端代码示例

#### TypeScript 类型定义

```typescript
interface RSSFeed {
  id: string;
  name: string;
  url: string;
  pushCount: number;
  isTrusted: boolean; // [新增] 是否为信任源
  createdAt: string;
}

interface ArticleDomain {
  id: number;
  name: string;
  description?: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface ArticleKeyword {
  id: number;
  domain_id: number;
  keyword_type: 'positive' | 'negative';
  keyword_text: string;
  is_regex: boolean;
  is_required: boolean;
  alias?: string;
  priority: number;
  max_results?: number;
  created_at: string;
}

interface Article {
  id: number;
  title: string;
  source: string;
  feedName: string;
  summary: string;
  url: string;
  publishedAt: string;
  pushedAt: string;
  isRead: boolean;
}
```

#### API 服务封装

```typescript
// services/filterService.ts
export const filterService = {
  // 获取领域列表
  getDomains: async (enabled?: boolean) => {
    const url = enabled !== undefined 
      ? `/api/v1/filter/domains?enabled=${enabled}`
      : '/api/v1/filter/domains';
    return fetch(url).then(res => res.json());
  },

  // 创建领域
  createDomain: async (data: { name: string; description?: string; enabled?: boolean }) => {
    return fetch('/api/v1/filter/domains', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => res.json());
  },

  // 获取关键词列表
  getKeywords: async (domainId?: number, keywordType?: string) => {
    const params = new URLSearchParams();
    if (domainId) params.append('domain_id', domainId.toString());
    if (keywordType) params.append('keyword_type', keywordType);
    return fetch(`/api/v1/filter/keywords?${params}`).then(res => res.json());
  },

  // 创建关键词
  createKeyword: async (data: ArticleKeyword) => {
    return fetch('/api/v1/filter/keywords', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => res.json());
  },

  // 删除关键词
  deleteKeyword: async (keywordId: number) => {
    return fetch(`/api/v1/filter/keywords/${keywordId}`, {
      method: 'DELETE'
    }).then(res => res.json());
  }
};

// services/articleService.ts
export const articleService = {
  // 获取今日推送（支持过滤）
  getTodayArticles: async (filters?: {
    domain_id?: number;
    keywords?: string;
    exclude_keywords?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.domain_id) params.append('domain_id', filters.domain_id.toString());
    if (filters?.keywords) params.append('keywords', filters.keywords);
    if (filters?.exclude_keywords) params.append('exclude_keywords', filters.exclude_keywords);
    
    const url = params.toString() 
      ? `/api/v1/article/today?${params}`
      : '/api/v1/article/today';
    
    return fetch(url).then(res => res.json());
  },

  // 获取历史推送（支持过滤和分页）
  getHistoryArticles: async (options?: {
    date?: string;
    page?: number;
    pageSize?: number;
    domain_id?: number;
    keywords?: string;
    exclude_keywords?: string;
  }) => {
    const params = new URLSearchParams();
    if (options?.date) params.append('date', options.date);
    if (options?.page) params.append('page', options.page.toString());
    if (options?.pageSize) params.append('pageSize', options.pageSize.toString());
    if (options?.domain_id) params.append('domain_id', options.domain_id.toString());
    if (options?.keywords) params.append('keywords', options.keywords);
    if (options?.exclude_keywords) params.append('exclude_keywords', options.exclude_keywords);
    
    return fetch(`/api/v1/article/history?${params}`).then(res => res.json());
  }
};
```

#### React 组件示例

```typescript
// components/FilterSettings.tsx
import { useState, useEffect } from 'react';
import { filterService } from '@/services/filterService';

export const FilterSettings = () => {
  const [domains, setDomains] = useState<ArticleDomain[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<number | null>(null);
  const [keywords, setKeywords] = useState<ArticleKeyword[]>([]);

  useEffect(() => {
    loadDomains();
  }, []);

  useEffect(() => {
    if (selectedDomain) {
      loadKeywords(selectedDomain);
    }
  }, [selectedDomain]);

  const loadDomains = async () => {
    const data = await filterService.getDomains(true);
    setDomains(data);
  };

  const loadKeywords = async (domainId: number) => {
    const data = await filterService.getKeywords(domainId);
    setKeywords(data);
  };

  const handleAddKeyword = async () => {
    if (!selectedDomain) return;
    
    const newKeyword = {
      domain_id: selectedDomain,
      keyword_type: 'positive' as const,
      keyword_text: '',
      is_regex: false,
      is_required: false,
      priority: 0
    };
    
    const result = await filterService.createKeyword(newKeyword);
    setKeywords([...keywords, result]);
  };

  return (
    <div className="filter-settings">
      <h2>文章过滤设置</h2>
      
      <div className="domains-list">
        {domains.map(domain => (
          <div key={domain.id} className="domain-item">
            <input
              type="checkbox"
              checked={selectedDomain === domain.id}
              onChange={() => setSelectedDomain(domain.id)}
            />
            <label>{domain.name}</label>
            {selectedDomain === domain.id && (
              <div className="keywords-list">
                {keywords.map(keyword => (
                  <div key={keyword.id} className="keyword-item">
                    <span>{keyword.keyword_text}</span>
                    {keyword.is_regex && <span className="badge">正则</span>}
                    {keyword.is_required && <span className="badge">必须</span>}
                    {keyword.keyword_type === 'negative' && <span className="badge">过滤</span>}
                  </div>
                ))}
                <button onClick={handleAddKeyword}>+ 添加关键词</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 注意事项

1. **性能优化**：关键词过滤在服务端进行，避免前端处理大量数据
2. **缓存策略**：领域列表和关键词规则可以缓存，减少 API 调用
3. **用户体验**：提供"保存并应用"按钮，让用户确认后再应用过滤
4. **错误处理**：正则表达式可能无效，需要前端验证或后端返回错误信息
5. **默认值**：系统已预置 8 个关键领域，可直接使用

### 测试建议

使用 Postman 集合中的"文章过滤"部分进行接口测试：
- 获取关键领域列表
- 创建/更新/删除领域
- 创建/删除关键词
- 测试文章查询接口的过滤功能

---

**文档版本：** v1.2  
**更新日期：** 2026-02-22  
**维护者：** UCreativity Team

---

## 变更记录

### v1.2（2026-02-22）

**新增接口**
- `POST /api/v1/feed/fetch` — 手动触发 RSS 抓取（见 2.5，补充文档）
- `PUT /api/v1/feed/trust/{feedId}` — 切换订阅源信任状态（见 2.6）

**接口变更**
- `GET /api/v1/feed/list` — 响应新增 `isTrusted` 字段
- `POST /api/v1/feed/create` — 请求参数新增 `isTrusted`，响应新增 `isTrusted`
- `PUT /api/v1/feed/update/{feedId}` — 请求参数新增 `isTrusted`，响应新增 `isTrusted`
- `GET /api/v1/article/today` — 过滤策略由「三级降级」改为「两阶段管道」，`filterTier` 取值更新

**过滤策略升级（两阶段管道）**
- Phase 1：负向关键词过滤（对所有文章生效，包括信任源）
- Phase 2：普通源文章按 6 大分类规则打分分桶、每类 TopN；信任源文章直接保留，不受分类匹配限制，不占分类名额

### v1.3（2026-02-25）

**新增模块：工作流编排（八、工作流编排模块）**

- `POST /api/v1/orchestration/workflows` — 创建工作流
- `POST /api/v1/orchestration/workflows/{workflow_id}/process` — 处理待执行阶段
- `POST /api/v1/orchestration/workflows/{workflow_id}/user-actions` — 提交用户操作（人在回路，幂等）
- `GET /api/v1/orchestration/workflows/{workflow_id}/events` — 获取事件流（断线补偿/回放）
- `GET /api/v1/orchestration/workflows/{workflow_id}/artifacts` — 获取工作流产物列表
- `GET /api/v1/orchestration/workflows/{workflow_id}` — 获取工作流详情
- `POST /api/v1/orchestration/workflows/{workflow_id}/rerun` — 重跑某阶段

