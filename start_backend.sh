#!/bin/sh
# US Stock Quant - 后端启动脚本 (Alpine Linux)

echo "============================================"
echo "  US Stock Quant - 后端启动"
echo "============================================"
echo ""

cd "$(dirname "$0")"

echo "启动中..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8777 --reload
