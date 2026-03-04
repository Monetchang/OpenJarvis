#!/bin/bash
# 一键初始化：创建数据库 + 执行迁移 + 初始化 AI 表 + 导入初始数据

set -e
cd "$(dirname "$0")/.."

echo "[1/4] 初始化数据库和表结构..."
./scripts/init_db.sh

echo "[2/4] 执行迁移..."
./scripts/run_migration.sh

echo "[3/4] 初始化 AI 选题表..."
python scripts/init_ai_tables.py

echo "[4/4] 导入初始 RSS 源..."
python scripts/add_feeds.py

echo "✅ 初始化完成，运行 ./start.sh 启动服务"
