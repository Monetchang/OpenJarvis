# OpenJarvis

Smart writing workspace: RSS feeds, AI topic generation, and blog creation in one place.

## 📕 Table of Contents

- [What is OpenJarvis?](#-what-is-openjarvis)
- [Latest Updates](#-latest-updates)
- [Key Features](#-key-features)
- [Get Started](#-get-started)
- [Docker Deployment](#-docker-deployment)
- [Launch from Source](#-launch-from-source)
- [Tech Stack](#-tech-stack)
- [Configuration](#-configuration)
- [License](#-license)

## 💡 What is OpenJarvis?

OpenJarvis is an intelligent writing assistant that combines RSS subscription, AI-powered topic generation, and LangGraph-driven blog creation. Subscribe to feeds, generate blog ideas from news, and write articles with AI assistance—all in one workflow.

## 🎮 Demo

![OpenJarvis Demo](web/assets/intro.gif)


## 🔥 Latest Updates

- 2025-03-04 统一 HTTP 客户端（`app/core/http_client.py`）：RSS 抓取与 fetch_url 共用，支持代理（RSS_USE_PROXY、RSS_PROXY_URL、socks5h）、超时、浏览器 UA；添加 RSS 源时「已存在」返回 200 而非 400；修复 logging_middleware 读取 body 导致 BaseHTTPMiddleware 崩溃。
- 2025-03-04 RSS 添加/更新支持 fetchNow 参数控制是否立即拉取（默认关闭）；批量导入 RSS 源（JSON 文件）；Demo GIF 展示。
- 2025-03-03 Added Docker deployment support.
- 2025-03-02 Feeds management page and FeedManager component.
- 2025-03-01 Translation support (MT / LLM).
- 2025-02-28 LangGraph workflow for blog creation (outline, section drafting, quality check).
- 2025-02-25 Email push (Resend) and Feishu Webhook integration.

## 🌟 Key Features

- **RSS Feeds**: Multi-source subscription, keyword filtering, scheduled fetching
- **AI Topics**: Auto-generate blog ideas from news
- **Smart Writing**: LangGraph-driven flow (outline confirmation, section drafting, quality validation)
- **Push & Share**: Email push (Resend), Feishu Webhook

## 🎬 Get Started

### Prerequisites

- Python 3.10+
- Node.js 18+ (frontend)
- PostgreSQL 14+
- Docker & Docker Compose (for Docker deployment)

## 🐳 Docker Deployment

1. Clone the repo:

   ```bash
   git clone https://github.com/your-org/OpenJarvis.git
   cd OpenJarvis
   ```

2. Create `.env` from example and configure:

   ```bash
   cp .env.example .env
   # Edit .env: set POSTGRES_PASSWORD, AI_API_KEY
   ```

3. Start services:

   ```bash
   docker compose up -d
   ```

4. Backend: http://localhost:12135  
   API docs: http://localhost:12135/docs

5. Run frontend locally (points to backend):

   ```bash
   cd web && npm install && npm run dev
   ```

   Frontend: http://localhost:5173

## 🔨 Launch from Source

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env: POSTGRES_PASSWORD, AI_API_KEY
```

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Initialize

```bash
./scripts/setup.sh
```

### 4. Start

```bash
./start.sh                    # Backend http://localhost:12135
cd web && npm install && npm run dev   # Frontend http://localhost:5173
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLAlchemy, LangGraph, LiteLLM |
| Frontend | React, TypeScript, Vite, Ant Design, Zustand |
| Database | PostgreSQL |

## Configuration

See `.env.example`. Main variables:

| Variable | Description |
|----------|-------------|
| `POSTGRES_*` | Database connection |
| `AI_API_KEY` | AI service key (DeepSeek/OpenAI etc.) |
| `AI_MODEL` | Model name |
| `RESEND_API_KEY` | Email push (Resend) |
| `INVITE_CODES` | Invite codes for email binding |

## License

MIT
