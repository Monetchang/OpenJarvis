#!/bin/bash
# OpenJarvis Backend 启动脚本

PORT=12135
HOST=0.0.0.0

echo "🚀 启动 OpenJarvis Backend..."
echo "📍 端口: $PORT"
echo "🌐 地址: http://localhost:$PORT"
echo ""

# 检查端口占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 $PORT 已被占用，正在停止旧进程..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

# 启动服务
cd "$(dirname "$0")"
uvicorn app.main:app --host $HOST --port $PORT --reload

