#!/bin/bash
# OpenJarvis Backend 停止脚本

PORT=12135

echo "🛑 停止 OpenJarvis Backend..."

if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    echo "✅ 服务已停止"
else
    echo "ℹ️  服务未运行"
fi

