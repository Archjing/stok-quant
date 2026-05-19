#!/bin/sh
# US Stock Quant - 后端启动脚本

set -e

echo "============================================"
echo "  US Stock Quant - 后端启动"
echo "============================================"
echo ""

cd "$(dirname "$0")"

echo "同步 uv 环境..."
uv sync

echo "启动中..."
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8777


