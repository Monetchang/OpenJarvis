#!/bin/bash
# 执行数据库迁移脚本

set -e
cd "$(dirname "$0")/.."

# 读取环境变量
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 设置默认值
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-openjarvis}

echo "执行数据库迁移..."
echo "数据库: $POSTGRES_DB"
echo "主机: $POSTGRES_HOST:$POSTGRES_PORT"
echo "用户: $POSTGRES_USER"
echo ""

# 执行迁移文件
echo "执行迁移: 001_add_fields.sql"
psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $POSTGRES_DB -f app/migrations/001_add_fields.sql

echo "执行迁移: 002_add_filter_fields.sql"
psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $POSTGRES_DB -f app/migrations/002_add_filter_fields.sql

echo "执行迁移: 003_add_app_config.sql"
psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $POSTGRES_DB -f app/migrations/003_add_app_config.sql

echo "执行迁移: 004_add_email_subscribers.sql"
psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $POSTGRES_DB -f app/migrations/004_add_email_subscribers.sql

echo "执行迁移: 005_add_rss_agg_fields.sql"
psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $POSTGRES_DB -f app/migrations/005_add_rss_agg_fields.sql

echo "执行迁移: 006_add_title_zh.sql"
psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $POSTGRES_DB -f app/migrations/006_add_title_zh.sql

echo "执行迁移: 007_add_interpret_result.sql"
psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $POSTGRES_DB -f app/migrations/007_add_interpret_result.sql

echo "执行迁移: 008_add_feishu_subscribers.sql"
psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $POSTGRES_DB -f app/migrations/008_add_feishu_subscribers.sql

echo ""
echo "迁移完成！"

