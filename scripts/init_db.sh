#!/bin/bash
# 初始化数据库：创建用户、数据库、表结构（从 .env 读取配置）

set -e
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-openjarvis}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASS="${POSTGRES_PASSWORD:-}"
SUPERUSER="${PGUSER:-$DB_USER}"

if [ "$DB_USER" != "$SUPERUSER" ] && [ -n "$DB_PASS" ]; then
  echo "==> 创建用户 $DB_USER"
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$SUPERUSER" -d postgres <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS';
  ELSE
    ALTER ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS';
  END IF;
END
\$\$;
SQL
fi

# 不自动创建数据库，请用户根据 .env 配置自行创建，例如：createdb -U postgres $DB_NAME
echo "==> 检查数据库 $DB_NAME 是否存在（若不存在请先创建：createdb -U $SUPERUSER $DB_NAME）"
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$SUPERUSER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
  echo "错误: 数据库 $DB_NAME 不存在，请先创建数据库"
  exit 1
fi

echo "==> 授权"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$SUPERUSER" -d "$DB_NAME" <<SQL
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
SQL

echo "==> 创建基础表"
export PGPASSWORD="$DB_PASS"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<SQL
-- rss_feeds
CREATE TABLE IF NOT EXISTS rss_feeds (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    feed_url VARCHAR DEFAULT '',
    is_active INTEGER DEFAULT 1,
    last_fetch_time VARCHAR,
    last_fetch_status VARCHAR,
    item_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    schedule VARCHAR(255) DEFAULT '0 9 * * *',
    push_count INTEGER DEFAULT 10,
    enable_translation INTEGER DEFAULT 0,
    is_trusted INTEGER DEFAULT 0
);

-- article_domains
CREATE TABLE IF NOT EXISTS article_domains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    max_results INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- rss_items
CREATE TABLE IF NOT EXISTS rss_items (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    feed_id VARCHAR NOT NULL REFERENCES rss_feeds(id),
    url TEXT NOT NULL,
    published_at VARCHAR,
    summary TEXT,
    author VARCHAR,
    first_crawl_time VARCHAR NOT NULL,
    last_crawl_time VARCHAR NOT NULL,
    crawl_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    domain_id INTEGER REFERENCES article_domains(id) ON DELETE SET NULL,
    matched_keywords JSONB
);

-- article_keywords
CREATE TABLE IF NOT EXISTS article_keywords (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES article_domains(id) ON DELETE CASCADE,
    keyword_type VARCHAR(20) NOT NULL DEFAULT 'positive',
    keyword_text TEXT NOT NULL,
    is_regex BOOLEAN DEFAULT FALSE,
    is_required BOOLEAN DEFAULT FALSE,
    alias VARCHAR(255),
    priority INTEGER DEFAULT 0,
    max_results INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- email_subscribers
CREATE TABLE IF NOT EXISTS email_subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_email_subscribers_active ON email_subscribers(is_active);

-- app_config
CREATE TABLE IF NOT EXISTS app_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_rss_items_is_read ON rss_items(is_read);
CREATE INDEX IF NOT EXISTS idx_rss_items_first_crawl_time ON rss_items(first_crawl_time);
CREATE INDEX IF NOT EXISTS idx_rss_items_domain_id ON rss_items(domain_id);
CREATE INDEX IF NOT EXISTS idx_article_keywords_domain_id ON article_keywords(domain_id);
CREATE INDEX IF NOT EXISTS idx_article_keywords_type ON article_keywords(keyword_type);
CREATE INDEX IF NOT EXISTS idx_article_domains_enabled ON article_domains(enabled);
CREATE INDEX IF NOT EXISTS idx_app_config_key ON app_config(key);
SQL

echo "==> 初始化完成"
