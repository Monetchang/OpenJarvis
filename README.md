# OpenJarvis

Smart writing workspace: RSS feeds, AI topic generation, and blog creation in one place.

**[中文文档](README.zh-CN.md)**

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

- 2026-03-07 Scheduler fix: `BackgroundScheduler` now initialized with `TIMEZONE` so cron fires at the correct local time regardless of container timezone (was UTC by default).
- 2026-03-07 title_zh split: original English title preserved in `title`; Chinese translation stored separately in `title_zh`; keyword filtering matches both; backfill skips already-translated items; summary translation removed.
- 2026-03-06 Feishu push: Digest push to Feishu (like email)—supports custom bot webhook and Flow webhook; `FEISHU_WEBHOOK_URL` in .env (semicolon-separated); `POST /subscribe/feishu` API; bilingual titles `中文 (English)`; rich formatting (sections, related articles); `scripts/test_feishu_push.py` and `scripts/test_email_push.py`.
- 2026-03-06 Email: HTML digest with gradient header, section blocks, topic cards; `title_zh` for bilingual display.
- 2026-03-06 Article Interpret: `POST /article/interpret/{articleId}`; structured interpretation cached in DB (`interpret_result`); `?force=1`; friendly error when site blocks crawling.
- 2026-03-06 History: pagination; IdeaGenerator hidden on history tab; bilingual title display.
- 2026-03-06 Scheduler: Cron uses `TIMEZONE`; scheduler in separate container; digest checks DB first.
- 2026-03-06 RSS: FeedParser UA; updated feed URLs; `scripts/diagnose_feeds.py`.
- 2025-03-05 AI RSS: RSS aggregation, RSSHub, Medium config; startup pre-fetch (15s after boot, disable via `STARTUP_PREFETCH_ENABLED=false`); decouple `/today` from auto-fetch; crawler lock + StaleDataError handling; init_db no longer creates DB; migration 005.
- 2025-03-05 Docker: backend + frontend only (no postgres); user manages DB separately; removed default RSS feeds and article domains; fixed oc_conversations IntegrityError, api.ts batchCreateFeeds type.
- 2025-03-04 Unified HTTP client for RSS fetch and fetch_url; proxy support (RSS_USE_PROXY, socks5h); feed create returns 200 when already exists; fixed logging middleware crash.
- 2025-03-04 RSS create/update supports fetchNow; batch import feeds; Demo GIF.
- 2025-03-03 Docker deployment support.
- 2025-03-02 Feeds management page and FeedManager component.
- 2025-03-01 Translation support (MT / LLM).
- 2025-02-28 LangGraph workflow for blog creation.
- 2025-02-25 Email push (Resend) and Feishu Webhook integration.

## 🌟 Key Features

- **RSS Feeds**: Multi-source subscription, keyword filtering, scheduled fetching
- **AI Topics**: Auto-generate blog ideas from news
- **Smart Writing**: LangGraph-driven flow (outline, drafting, quality validation)
- **Push & Share**: Email push (Resend), Feishu digest push (bot/Flow webhook)

## 🎬 Get Started

### Prerequisites

- Python 3.10+
- Node.js 18+ (frontend)
- PostgreSQL 14+
- Docker & Docker Compose (for Docker deployment)

## 🐳 Docker Deployment

### Before Starting

1. **Start PostgreSQL** (user-managed). Docker Compose does not include postgres. Run it locally or in a separate container. Ensure the DB exists and is reachable.

2. **Create `.env`** (required):
   ```bash
   cp .env.example .env
   ```
   Configure at minimum:
   - `POSTGRES_HOST`: DB host. Use `host.docker.internal` if postgres runs on your host machine (Mac/Win/Linux with Docker 20.10+).
   - `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Match your postgres.
   - `AI_API_KEY`: AI service key
   - Email push: `RESEND_API_KEY`, `RESEND_FROM` (register at [Resend](https://resend.com))

### Steps

1. Clone the repo:
   ```bash
   git clone https://github.com/your-org/OpenJarvis.git
   cd OpenJarvis
   ```

2. Configure `.env` per "Before Starting" above

3. Start services:
   ```bash
   docker compose up -d
   ```
   Services: `backend` (API, 4 workers), `scheduler` (RSS cron + digest), `frontend`.

4. Backend: http://localhost:12135  
   API docs: http://localhost:12135/docs  
   Frontend: http://localhost:5173 (included in `docker compose up`)

5. If backend fails: `docker compose logs backend`

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
| `RESEND_API_KEY` | Email push—register at [Resend](https://resend.com) for API key (100 free emails/day) |
| `RESEND_FROM` | Sender, e.g. `OpenJarvis <onboarding@resend.dev>` (quote the value) |
| `INVITE_CODES` | Invite codes for email binding |
| `STARTUP_PREFETCH_ENABLED` | Startup pre-fetch (set `false` when app restarts frequently in test) |
| `TIMEZONE` | Timezone for cron and "today" logic (default `Asia/Shanghai`) |
| `FEISHU_WEBHOOK_URL` | Feishu digest push—webhook URL(s), semicolon-separated (bot or Flow) |

## License

MIT
