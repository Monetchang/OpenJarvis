# OpenJarvis

智能写作工作台：RSS 订阅、AI 选题、博客创作一体化。

## 功能特性

- **RSS 订阅**：多源订阅、关键词过滤、定时抓取
- **AI 选题**：基于新闻自动生成博客选题
- **智能创作**：LangGraph 驱动的博客写作流程（大纲确认、分节撰写、质量校验）
- **推送与分享**：邮件推送、飞书 Webhook

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（前端）
- PostgreSQL 14+

### 后端

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 配置数据库、AI 等
```

### 数据库

```bash
# 执行迁移
./scripts/run_migration.sh
# 或手动执行 app/migrations/*.sql
```

### 前端

```bash
cd web
npm install
npm run dev
```

### 启动服务

```bash
# 后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 12135

# 前端开发 (web 目录)
npm run dev
```

- API 文档：http://localhost:12135/docs
- 前端：http://localhost:5173

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, SQLAlchemy, LangGraph, LiteLLM |
| 前端 | React, TypeScript, Vite, Ant Design, Zustand |
| 数据库 | PostgreSQL |

## 项目结构

```
├── app/                    # 后端
│   ├── api/v1/endpoints/   # REST API
│   ├── core/               # 配置、AI、爬虫
│   ├── models/             # ORM 模型
│   ├── orchestration/      # 工作流编排 (LangGraph)
│   ├── services/           # 业务服务
│   └── migrations/         # SQL 迁移
├── web/                    # 前端
│   └── src/
│       ├── pages/          # 页面（创作、设置等）
│       ├── components/     # 组件
│       └── services/       # API 调用
├── scripts/                # 脚本工具
├── .env.example
├── requirements.txt
└── Dockerfile
```

## 配置说明

参考 `.env.example`，主要配置项：

| 变量 | 说明 |
|------|------|
| `POSTGRES_*` | 数据库连接 |
| `AI_API_KEY` | AI 服务密钥（DeepSeek/OpenAI 等） |
| `AI_MODEL` | 模型名称 |
| `RESEND_API_KEY` | 邮件推送（Resend） |
| `INVITE_CODES` | 邮箱绑定邀请码 |

## 许可证

MIT
