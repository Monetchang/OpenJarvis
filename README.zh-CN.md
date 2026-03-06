# OpenJarvis

智能写作工作台：RSS 订阅、AI 选题、博客创作一体化。

**[English](README.md)**

## 📕 目录

- [项目介绍](#-项目介绍)
- [最新更新](#-最新更新)
- [核心功能](#-核心功能)
- [快速开始](#-快速开始)
- [Docker 部署](#-docker-部署)
- [源码启动](#-源码启动)
- [技术栈](#-技术栈)
- [配置说明](#-配置说明)
- [License](#license)

## 💡 项目介绍

OpenJarvis 是智能写作助手，整合 RSS 订阅、AI 选题生成与 LangGraph 驱动的博客创作。订阅资讯源、从新闻生成选题、在 AI 辅助下完成文章，全流程一站式完成。

## 🎮 演示

![OpenJarvis Demo](web/assets/intro.gif)

## 🔥 最新更新

- 2026-03-06 定时任务：Cron 使用 `.env` 中的 `TIMEZONE`（修复 Docker UTC 时区问题）；scheduler 独立容器运行（backend + scheduler + frontend）；推送前先查库，有今日文章和选题则直接用，否则抓取并生成。
- 2026-03-06 RSS：改用 FeedParser UA 规避 403（MarkTechPost、AI News）；更新 Google AI Blog、Sebastian Raschka 地址；禁用 Papers with Code（Cloudflare）；新增 `scripts/diagnose_feeds.py` 诊断脚本。
- 2026-03-06 时区：crawler、API、scheduler 的「今日」逻辑统一使用 `get_configured_time()`。
- 2025-03-05 AI RSS：RSS 聚合、RSSHub、Medium 配置；启动预抓取（启动 15 秒后执行，测试环境可设 `STARTUP_PREFETCH_ENABLED=false` 关闭）；解耦 `/today` 与自动抓取；crawler 进程锁与 StaleDataError 处理；init_db 不再自动建库；迁移 005。
- 2025-03-05 Docker：仅 backend + frontend，不含 postgres，数据库由用户自行管理；移除默认 RSS 源与关键领域数据；修复 oc_conversations IntegrityError、api.ts batchCreateFeeds 类型错误。
- 2025-03-04 统一 HTTP 客户端（`app/core/http_client.py`）：RSS 抓取与 fetch_url 共用，支持代理（RSS_USE_PROXY、RSS_PROXY_URL、socks5h）、超时、浏览器 UA；添加 RSS 源时「已存在」返回 200 而非 400；修复 logging_middleware 读取 body 导致 BaseHTTPMiddleware 崩溃。
- 2025-03-04 RSS 添加/更新支持 fetchNow 参数控制是否立即拉取；批量导入 RSS 源（JSON 文件）；Demo GIF 展示。
- 2025-03-03 Docker 部署支持。
- 2025-03-02 订阅源管理页与 FeedManager 组件。
- 2025-03-01 翻译支持（MT / LLM）。
- 2025-02-28 LangGraph 博客创作流程（大纲、分段撰写、质量校验）。
- 2025-02-25 邮件推送（Resend）与飞书 Webhook 集成。

## 🌟 核心功能

- **RSS 订阅**：多源订阅、关键词过滤、定时抓取
- **AI 选题**：从新闻自动生成博客选题
- **智能写作**：LangGraph 流程（大纲确认、分段撰写、质量校验）
- **推送与分享**：邮件推送（Resend）、飞书 Webhook

## 🎬 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（前端）
- PostgreSQL 14+
- Docker & Docker Compose（Docker 部署时）

## 🐳 Docker 部署

### 启动前准备

1. **自行启动 PostgreSQL**。Docker Compose 不包含 postgres，需在本地或独立容器中运行，并确保数据库可访问。

2. **创建 `.env`**（必须）：
   ```bash
   cp .env.example .env
   ```
   至少配置：
   - `POSTGRES_HOST`：数据库主机。若 postgres 在本机运行，使用 `host.docker.internal`（Mac/Win/Linux Docker 20.10+ 支持）。
   - `POSTGRES_PORT`、`POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`：与你的 postgres 一致。
   - `AI_API_KEY`：AI 服务密钥
   - 邮件推送：`RESEND_API_KEY`、`RESEND_FROM`（需在 [Resend](https://resend.com) 注册）

### 启动步骤

1. 克隆仓库：
   ```bash
   git clone https://github.com/your-org/OpenJarvis.git
   cd OpenJarvis
   ```

2. 按上述「启动前准备」配置 `.env`

3. 启动服务：
   ```bash
   docker compose up -d
   ```
   服务：`backend`（API，4 workers）、`scheduler`（RSS 定时抓取与推送）、`frontend`。

4. 后端：http://localhost:12135  
   API 文档：http://localhost:12135/docs  
   前端：http://localhost:5173（已包含在 `docker compose up` 中）

5. 若 backend 启动失败，查看日志：`docker compose logs backend`

## 🔨 源码启动

### 1. 配置环境

```bash
cp .env.example .env
# 编辑 .env：POSTGRES_PASSWORD、AI_API_KEY
```

### 2. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 初始化

```bash
./scripts/setup.sh
```

### 4. 启动

```bash
./start.sh                    # 后端 http://localhost:12135
cd web && npm install && npm run dev   # 前端 http://localhost:5173
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, SQLAlchemy, LangGraph, LiteLLM |
| 前端 | React, TypeScript, Vite, Ant Design, Zustand |
| 数据库 | PostgreSQL |

## 配置说明

参见 `.env.example`。主要变量：

| 变量 | 说明 |
|------|------|
| `POSTGRES_*` | 数据库连接 |
| `AI_API_KEY` | AI 服务密钥（DeepSeek/OpenAI 等） |
| `AI_MODEL` | 模型名称 |
| `RESEND_API_KEY` | 邮件推送需自行在 [Resend](https://resend.com) 注册获取 API Key，免费 100 封/天 |
| `RESEND_FROM` | 发件人，如 `OpenJarvis <onboarding@resend.dev>`（测试可用该地址） |
| `INVITE_CODES` | 邀请码，逗号分隔，邮箱绑定时校验 |
| `STARTUP_PREFETCH_ENABLED` | 启动预抓取，测试环境频繁重启时设为 `false` |
| `TIMEZONE` | 定时任务与「今日」逻辑的时区（默认 `Asia/Shanghai`） |

## License

MIT
