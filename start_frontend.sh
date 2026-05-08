#!/bin/sh
# US Stock Quant - 前端启动脚本 (Alpine Linux)

echo "============================================"
echo "  US Stock Quant - 前端启动"
echo "============================================"
echo ""

cd "$(dirname "$0")/frontend"

echo "启动中..."
npm run dev
